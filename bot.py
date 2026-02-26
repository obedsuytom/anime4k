from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand, InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from aiogram.utils import executor
import requests
from decimal import Decimal
from datetime import datetime, timedelta
import sqlite3
from uuid import uuid4
import urllib.parse
import aiohttp
from aiohttp import web
import hashlib
import time
import os
from io import BytesIO
import re
import asyncio
import logging
import threading

EPISODES_PER_ROW = 5
ROWS_PER_PAGE = 10
ANIME_PER_PAGE = 10  # сколько аниме на странице
MAX_TITLE_LEN = 30   # максимум символов в кнопке
EPISODES_PER_PAGE = EPISODES_PER_ROW * ROWS_PER_PAGE  # 50
WAITING_CHECK = set()
PENDING_PAYMENTS = {}
SHIKI_CACHE = {}
BURMALDOD_EDIT = {}
LAST_SEARCH_MSG = {}
CURRENT_EDIT_ANIME = {}
USER_MESSAGES = {}
ADMIN_EDIT_ANIME = {}
SEARCH_USERS = set()
CRYPTO_MARGIN = 0.30
CRYPTO_CURRENCIES = ["ton", "btc", "usdt"]
COINGECKO_API = "https://api.coingecko.com/api/v3/simple/price"
CRYPTOBOT_CREATE = "https://pay.crypt.bot/api/createInvoice"
URL_RE = re.compile(r'https?://\S+')
ANILIST_API = "https://graphql.anilist.co"
TARIFFS = {
    "7": {"title": "7 дней", "days": 7},
    "30": {"title": "30 дней", "days": 30},
    "180": {"title": "180 дней", "days": 180},
    "360": {"title": "360 дней", "days": 360},
    "lifetime": {"title": "Навсегда", "days": None}
}
RUB_PRICES = {
    "7_days": 39,
    "30_days": 99,
    "180_days": 499,
    "360_days": 899,
    "forever": 1499
}

# =========================
# Настройки
# =========================
API_TOKEN = os.getenv("BOT_TOKEN")
CRYPTOBOT_TOKEN = os.getenv("CRYPTO_TOKEN")
ADMINS = [6265184966]

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# =========================
# База данных
# =========================
db = sqlite3.connect("anime.db")
cursor = db.cursor()

cursor.execute("DROP TABLE IF EXISTS pending_videos")
cursor.execute("""
CREATE TABLE pending_videos (
    message_id INTEGER PRIMARY KEY,
    file_id TEXT NOT NULL,
    date TEXT
)
""")
db.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS subscriptions (
    user_id INTEGER PRIMARY KEY,
    type TEXT,
    expire_date TEXT
)
""")
db.commit()


cursor.execute("""
CREATE TABLE IF NOT EXISTS videos (
    anime TEXT,
    dub TEXT,
    season INTEGER,
    episode INTEGER,
    file_id TEXT
)
""")
db.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    first_start INTEGER,
    paid_until INTEGER
)
""")
db.commit()

cursor.execute("PRAGMA table_info(videos)")
columns = [col[1] for col in cursor.fetchall()]

if "title_en" not in columns:
    cursor.execute("ALTER TABLE videos ADD COLUMN title_en TEXT")
    conn.commit()
    print("✅ Колонка title_en создана в таблице videos")

def cut_title(title: str, max_len: int = MAX_TITLE_LEN) -> str:
    """Обрезаем длинные названия аниме для кнопок"""
    return title if len(title) <= max_len else title[:max_len - 3] + "..."



# =========================
# Вспомогательные функции
# =========================

def has_active_sub(user_id: int) -> bool:
    """Проверяет, есть ли у пользователя активная подписка."""
    cursor.execute("SELECT expire_date FROM subscriptions WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if not row or not row[0]:
        return False
    expire_date = datetime.fromisoformat(row[0])
    return expire_date > datetime.now()

async def send_and_track(user_id, send_func, *args, **kwargs):
    """Отправка сообщения/фото/видео с отслеживанием ID"""
    msg = await send_func(*args, **kwargs)
    USER_MESSAGES.setdefault(user_id, []).append(msg.message_id)
    return msg

async def delete_bot_messages(user_id, chat_id):
    """Удаляет все сообщения бота пользователя"""
    for msg_id in USER_MESSAGES.get(user_id, []):
        try:
            await bot.delete_message(chat_id, msg_id)
        except:
            pass
    USER_MESSAGES[user_id] = []

def make_cb_id(*args):
    s = "|".join(args)
    return hashlib.md5(s.encode()).hexdigest()

def has_access(user_id: int) -> bool:
    now = int(time.time())
    cursor.execute("SELECT paid_until FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if not row:
        return False
    return row[0] > now

def clean_shikimori_description(text: str) -> str:
    if not text:
        return "Описание отсутствует"

    # Удаляем HTML теги
    text = re.sub(r"<.*?>", "", text)

    # Удаляем BB-коды вида [spoiler], [/spoiler], [quote], [b], [i] и т.д.
    text = re.sub(r"\[/?[a-zA-Z0-9_= \"'-]+\]", "", text)

    # Удаляем конструкции вида [character=123], [anime=456] и т.д.
    text = re.sub(r"\[[^\]]+\]", "", text)

    # Убираем лишние пробелы
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()



# =========================
# Shikimori API
# =========================

async def get_anilist_poster(title: str) -> str | None:
    query = """
    query ($search: String) {
      Media (search: $search, type: ANIME) {
        coverImage {
          extraLarge
          large
        }
      }
    }
    """

    variables = {"search": title}

    async with aiohttp.ClientSession() as session:
        async with session.post(
            ANILIST_API,
            json={"query": query, "variables": variables},
            headers={"Content-Type": "application/json"}
        ) as resp:
            if resp.status != 200:
                return None

            data = await resp.json()
            media = data.get("data", {}).get("Media")
            if not media:
                return None

            cover = media.get("coverImage", {})
            return cover.get("extraLarge") or cover.get("large")

async def get_anime_info(title: str):
    if title in SHIKI_CACHE:
        return SHIKI_CACHE[title]

    url = "https://shikimori.one/api/animes"
    params = {"search": title, "limit": 1, "order": "ranked"}
    headers = {"User-Agent": "Mozilla/5.0 (Telegram Bot)"}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, headers=headers) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            if not data:
                return None
            anime = data[0]
            anime_id = anime["id"]

        async with session.get(f"https://shikimori.one/api/animes/{anime_id}", headers=headers) as resp:
            if resp.status != 200:
                return None
            full = await resp.json()

    # Преобразуем статус
    shiki_status = full.get("status", "").lower()
    if shiki_status == "released":
        status_text = "Вышло"
    elif shiki_status == "ongoing":
        status_text = "Онгоинг"
    elif shiki_status == "anons":
        status_text = "Анонс"
    else:
        status_text = "Неизвестно"

    info = {
        "title": full.get("russian") or full.get("name") or title,
        "score": full.get("score") or "—",
        "year": (full.get("aired_on") or "—")[:4],
        "genres": ", ".join(g.get("russian", g.get("name", "")) for g in full.get("genres", [])) or "—",
        "description": full.get("description") or "Описание отсутствует",
        "poster": f"https://shikimori.one{full['image']['original']}" if full.get("image") else None,
        "status_text": status_text
    }
    SHIKI_CACHE[title] = info
    return info
# =========================
# Стартап
# =========================
async def on_startup(dp):
    await bot.set_my_commands([BotCommand(command="/start", description="Перезапуск бота")])
    print("Бот запущен ✅")

# =========================
# /start
# =========================
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    args = message.get_args()

    await delete_bot_messages(user_id, chat_id)

    # ===== ЕСЛИ ПРИШЁЛ DEEP LINK =====
    if args.startswith("anime_"):
        anime_name = urllib.parse.unquote(args.replace("anime_", "", 1))

        # Проверка подписки
        if not has_active_sub(user_id):
            kb = InlineKeyboardMarkup().add(
                InlineKeyboardButton("💳 Купить подписку", callback_data="buy_sub"),
                InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_menu")
            )

            await send_and_track(
                user_id,
                message.answer,
                "⛔ Доступ закрыт. Подписка закончилась.",
                reply_markup=kb
            )
            return

        # Открываем конкретное аниме
        await show_anime_page(message, anime_name)
        return

    # ===== ОБЫЧНЫЙ START =====

    photo_id = "AgACAgIAAxkBAAIBKGmKXnQ3GN0fEp0gZvlZ-e05w14kAALGE2sbUvNRSB8Eq4CFt69-AQADAgADeQADOgQ"
    text = (
        "🌠 Привет!\n"
        "Я бот для просмотра аниме в 4К качестве👘.\n"
        "Первые 7 дней можно будет опробовать меня абсолютно бесплатно!"
    )

    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    exists = cursor.fetchone()

    kb = InlineKeyboardMarkup(row_width=1)
    if not exists:
        kb.add(InlineKeyboardButton("📝 Регистрация", callback_data="register"))
    else:
        kb.add(InlineKeyboardButton("▶️ Смотреть аниме в 4K", callback_data="back_menu"))

    await send_and_track(
        user_id,
        bot.send_photo,
        chat_id=chat_id,
        photo=photo_id,
        caption=text,
        reply_markup=kb
    )

@dp.message_handler(commands=["name"])
async def edit_name_cmd(message: types.Message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        await message.reply("❌ У вас нет прав на редактирование.")
        return

    # Получаем список аниме из базы
    cursor.execute("SELECT DISTINCT anime FROM videos ORDER BY anime")
    animes = [row[0] for row in cursor.fetchall()]

    kb = InlineKeyboardMarkup(row_width=2)
    for anime in animes:
        kb.add(InlineKeyboardButton(text=anime, callback_data=f"edit_name|{anime}"))

    await message.answer("Выберите аниме для редактирования английского названия:", reply_markup=kb)

async def add_subscription(user_id: int, plan_type: str, days: int):
    """
    Добавляет подписку пользователю. Если старая подписка ещё активна, прибавляет дни.
    plan_type: '7 дней', '30 дней' и т.д.
    days: количество дней подписки
    """
    cursor.execute("SELECT expire_date FROM subscriptions WHERE user_id=?", (user_id,))
    row = cursor.fetchone()

    now = datetime.now()
    if row:
        old_expire = datetime.fromisoformat(row[0])
        # Если старая подписка ещё активна, прибавляем дни
        if old_expire > now:
            new_expire = old_expire + timedelta(days=days)
        else:
            new_expire = now + timedelta(days=days)
        cursor.execute(
            "UPDATE subscriptions SET type=?, expire_date=? WHERE user_id=?",
            (plan_type, new_expire.isoformat(), user_id)
        )
    else:
        new_expire = now + timedelta(days=days)
        cursor.execute(
            "INSERT INTO subscriptions (user_id, type, expire_date) VALUES (?, ?, ?)",
            (user_id, plan_type, new_expire.isoformat())
        )
    db.commit()
    return new_expire
# =========================
# /sub
# =========================

@dp.callback_query_handler(lambda c: c.data == "choose_plan")
async def choose_plan(call):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("7 дней — 39₽", callback_data="buy_7"),
        InlineKeyboardButton("30 дней — 99₽", callback_data="buy_30"),
        InlineKeyboardButton("180 дней — 499₽", callback_data="buy_180"),
        InlineKeyboardButton("360 дней — 899₽", callback_data="buy_360"),
        InlineKeyboardButton("Навсегда (только 100 чел.) — 1499₽", callback_data="buy_forever"),
        InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_menu")
    )

    try:
        await send_and_track(
            call.from_user.id,
            call.message.edit_text,
            "💳 Покупка подписок:",
            reply_markup=kb
        )
    except:
        await send_and_track(
            call.from_user.id,
            call.message.answer,
            "💳 Покупка подписок:",
            reply_markup=kb
        )
    await call.answer()

def get_crypto_amount(rub_amount: int, crypto: str) -> str:
    try:
        headers = {
            "Crypto-Pay-API-Token": CRYPTOBOT_TOKEN
        }

        response = requests.get(
            "https://pay.crypt.bot/api/getExchangeRates",
            headers=headers,
            timeout=5
        )

        data = response.json()

        if not data.get("ok"):
            print("Ошибка получения курсов:", data)
            return "0.00000000"

        rates = data["result"]

        usd_rub = None
        crypto_usd = None

        for rate in rates:
            # USD → RUB
            if rate["source"] == "USD" and rate["target"] == "RUB":
                usd_rub = Decimal(rate["rate"])

            # CRYPTO → USD
            if rate["source"] == crypto.upper() and rate["target"] == "USD":
                crypto_usd = Decimal(rate["rate"])

        if not usd_rub or not crypto_usd:
            print(f"Не найден курс для {crypto}")
            return "0.00000000"

        # RUB → USD
        usd_amount = Decimal(rub_amount * (1 + CRYPTO_MARGIN)) / usd_rub

        # USD → CRYPTO
        crypto_amount = usd_amount / crypto_usd

        return f"{crypto_amount:.8f}"

    except Exception as e:
        print(f"[get_crypto_amount] Ошибка: {e}")
        return "0.00000000"

# ===== Генерация счета Crypto.bot =====
def create_crypto_invoice(user_id: int, rub_amount: int, period_key: str) -> str:
    try:
        headers = {
            "Crypto-Pay-API-Token": CRYPTOBOT_TOKEN
        }

        payload = {
            "currency_type": "fiat",
            "fiat": "RUB",
            "amount": rub_amount,
            "description": f"Subscription:{period_key}",
            "hidden_message": f"user:{user_id}|period:{period_key}"
        }

        response = requests.post(
            "https://pay.crypt.bot/api/createInvoice",
            headers=headers,
            json=payload,
            timeout=10
        )

        data = response.json()

        if data.get("ok"):
            return data["result"]["pay_url"]
        else:
            print("Ошибка createInvoice:", data)
            return None

    except Exception as e:
        print("CryptoBot exception:", e)
        return None

# =========================
# /give
# =========================
@dp.message_handler(commands=["give"])
async def give_subscription_cmd(message: types.Message):
    if message.from_user.id not in ADMINS:
        return

    args = message.get_args().split()

    if len(args) != 2:
        await message.answer(
            "Использование:\n"
            "/give user_id дни\n\n"
            "Примеры:\n"
            "/give 123456789 30\n"
            "/give 123456789 forever"
        )
        return

    # Проверяем ID
    try:
        target_id = int(args[0])
    except ValueError:
        await message.answer("❌ ID должен быть числом.")
        return

    # Проверяем срок
    if args[1].lower() == "forever":
        days = None
    else:
        try:
            days = int(args[1])
            if days <= 0:
                raise ValueError
        except ValueError:
            await message.answer("❌ Дни должны быть положительным числом или 'forever'.")
            return

    # Выдаём подписку
    give_subscription(target_id, days)

    # Ответ админу
    if days is None:
        text = f"✅ Пользователю {target_id} выдана подписка НАВСЕГДА."
    else:
        text = f"✅ Пользователю {target_id} выдана подписка на {days} дней."

    await message.answer(text)

    # Уведомление пользователю
    try:
        if days is None:
            await bot.send_message(target_id, "🎉 Вам выдана подписка НАВСЕГДА!")
        else:
            await bot.send_message(
                target_id,
                f"🎉 Вам выдана подписка на {days} дней!"
            )
    except:
        pass

@dp.message_handler(commands=["darling"])
async def darling_add_from_pending(message: types.Message):
    user_id = message.from_user.id

    if user_id not in ADMINS:
        await message.answer("❌ У тебя нет прав для этой команды.")
        return

    try:
        args = message.get_args()
        anime, dub, season_raw, start_episode, num_episodes = [
            x.strip() for x in args.split(";")
        ]

        # 🎬 Обработка сезона
        if season_raw.lower() in ["фильм", "film", "movie"]:
            season = "Фильм"
        else:
            season = int(season_raw)

        start_episode = int(start_episode)
        num_episodes = int(num_episodes)

    except:
        await message.answer(
            "❌ Неверный формат команды.\n\n"
            "Используй:\n"
            "/darling Название ; Озвучка ; Сезон/Фильм ; С какой серии ; Сколько серий\n\n"
            "Пример:\n"
            "/darling One Piece ; Anilibria ; 1 ; 1 ; 12\n"
            "/darling Your Name ; AniDub ; Фильм ; 1 ; 1"
        )
        return

    cursor.execute(
        "SELECT message_id, file_id FROM pending_videos ORDER BY date ASC LIMIT ?",
        (num_episodes,)
    )
    videos = cursor.fetchall()

    if not videos:
        await message.answer("❌ Нет видео для добавления!")
        return

    for i, (msg_id, file_id) in enumerate(videos, start=start_episode):
        cursor.execute(
            "INSERT INTO videos (anime, dub, season, episode, file_id) VALUES (?, ?, ?, ?, ?)",
            (anime.lower(), dub, season, i, file_id)
        )

    video_ids = [v[0] for v in videos]
    cursor.execute(
        f"DELETE FROM pending_videos WHERE message_id IN ({','.join(['?']*len(video_ids))})",
        video_ids
    )

    db.commit()

    season_display = "🎬 Фильм" if season == "Фильм" else f"📺 Сезон: {season}"

    await message.answer(
        f"✅ Успешно добавлено {len(videos)} серий\n\n"
        f"🎬 {anime.title()}\n"
        f"🎙 Озвучка: {dub}\n"
        f"{season_display}\n"
        f"▶️ Серии: {start_episode}-{start_episode + len(videos) - 1}"
    )

def give_subscription(user_id: int, days: int | None):
    now = datetime.now()

    cursor.execute(
        "SELECT expire_date FROM subscriptions WHERE user_id=?",
        (user_id,)
    )
    row = cursor.fetchone()

    # 🔥 FOREVER
    if days is None:
        if row:
            cursor.execute(
                "UPDATE subscriptions SET type=?, expire_date=? WHERE user_id=?",
                ("forever", "forever", user_id)
            )
        else:
            cursor.execute(
                "INSERT INTO subscriptions (user_id, type, expire_date) VALUES (?, ?, ?)",
                (user_id, "forever", "forever")
            )

        db.commit()
        return

    # 🔥 Если есть запись
    if row and row[0] != "forever":
        old_expire = datetime.fromisoformat(row[0])

        if old_expire > now:
            new_expire = old_expire + timedelta(days=days)
        else:
            new_expire = now + timedelta(days=days)

        cursor.execute(
            "UPDATE subscriptions SET type=?, expire_date=? WHERE user_id=?",
            (f"{days}_days", new_expire.isoformat(), user_id)
        )

    else:
        new_expire = now + timedelta(days=days)

        cursor.execute(
            "INSERT INTO subscriptions (user_id, type, expire_date) VALUES (?, ?, ?)",
            (user_id, f"{days}_days", new_expire.isoformat())
        )

    db.commit()

# =========================
# /remove_sub
# =========================
@dp.message_handler(commands=["remove_sub"])
async def remove_sub(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if user_id not in ADMINS:
        await message.reply("❌ У тебя нет прав для этой команды")
        return

    if not message.reply_to_message:
        await message.reply("Ответь на сообщение пользователя командой /remove_sub")
        return

    target_id = message.reply_to_message.from_user.id

    # Удаляем подписку полностью
    cursor.execute("DELETE FROM subscriptions WHERE user_id=?", (target_id,))
    db.commit()

    await message.reply(f"✅ Подписка у пользователя {target_id} успешно удалена")

@dp.message_handler(commands=["burmaldod"])
async def burmaldod_start(message: types.Message):
    if message.from_user.id not in ADMINS:
        return

    cursor.execute("SELECT DISTINCT anime FROM videos ORDER BY anime")
    animes = [row[0] for row in cursor.fetchall()]

    kb = InlineKeyboardMarkup(row_width=1)

    for idx, anime in enumerate(animes):
        short_name = anime if len(anime) <= 40 else anime[:40] + "..."

        kb.add(
            InlineKeyboardButton(
                text=short_name,
                callback_data=f"burmal_edit|{idx}"   # ✅ теперь совпадает
            )
        )

    await message.answer("📋 Выберите аниме:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("burmal_edit|"))
async def burmaldod_choose(call: types.CallbackQuery):
    if call.from_user.id not in ADMINS:
        return

    _, idx_str = call.data.split("|")
    idx = int(idx_str)

    cursor.execute("SELECT DISTINCT anime FROM videos ORDER BY anime")
    animes = [row[0] for row in cursor.fetchall()]

    if idx < 0 or idx >= len(animes):
        await call.answer("❌ Аниме не найдено", show_alert=True)
        return

    anime = animes[idx]

    BURMALDOD_EDIT[call.from_user.id] = anime

    await call.message.answer(
        f"✏ Введите новое английское название для:\n\n<b>{anime}</b>",
        parse_mode="HTML"
    )

    await call.answer()

@dp.message_handler(lambda m: m.from_user.id in BURMALDOD_EDIT)
async def burmaldod_save(message: types.Message):
    user_id = message.from_user.id
    anime = BURMALDOD_EDIT.get(user_id)

    if not anime:
        return

    new_name = message.text.strip()

    if not new_name:
        await message.answer("⚠ Название не может быть пустым")
        return

    cursor.execute(
        "UPDATE videos SET english_name=? WHERE anime=?",
        (new_name, anime)
    )
    db.commit()

    BURMALDOD_EDIT.pop(user_id, None)

    await message.answer(
        f"✅ English название обновлено:\n\n"
        f"<b>{anime}</b> → <b>{new_name}</b>",
        parse_mode="HTML"
    )

@dp.message_handler(content_types=types.ContentType.VIDEO)
async def get_video(message: types.Message):
    cursor.execute(
        "INSERT OR IGNORE INTO pending_videos (message_id, file_id, date) VALUES (?, ?, ?)",
        (message.message_id, message.video.file_id, str(message.date))
    )
    db.commit()
    await send_and_track(message.from_user.id, message.answer, "✅ Видео сохранено и готово для добавления в базу")

@dp.message_handler(lambda m: m.text and URL_RE.search(m.text))
async def get_video_link(message: types.Message):
    url = URL_RE.search(message.text).group(0)

    cursor.execute(
        "INSERT OR IGNORE INTO pending_videos (message_id, file_id, date) VALUES (?, ?, ?)",
        (message.message_id, url, str(message.date))
    )
    db.commit()

    await send_and_track(
        message.from_user.id,
        message.answer,
        "✅ Ссылка сохранена и готова для добавления в базу"
    )

async def send_video_or_link(chat_id, video_value, caption=None, reply_markup=None):
    # Если это ссылка — шлём кнопкой
    if isinstance(video_value, str) and URL_RE.match(video_value):
        kb = reply_markup or InlineKeyboardMarkup()

        return await bot.send_message(
            chat_id,
            caption or "🎬 Видео по ссылке:",
            reply_markup=kb,
            disable_web_page_preview=True
        )

    # Иначе — это file_id телеги
    return await bot.send_video(
        chat_id,
        video=video_value,
        caption=caption,
        reply_markup=reply_markup
    )

async def get_anime_poster(anime_name):
    """
    Получает постер аниме через Shikimori -> AniList.
    Сначала ищем английское название, если пустое — оригинальное.
    """
    # 1️⃣ Получаем инфо с Shikimori
    info = await get_anime_info(anime_name)
    if not info:
        return None

    # 2️⃣ Берём английское название
    title_en = info.get("title_en")
    if title_en:
        search_name = title_en
    else:
        search_name = info.get("title")  # оригинальное название

    # 3️⃣ Очищаем название от спецсимволов для стабильного поиска
    search_name = re.sub(r"[:!\"'‘’]", "", search_name).strip()

    # 4️⃣ Поиск на AniList
    poster_url = await search_anilist_poster(search_name)
    return poster_url


@dp.callback_query_handler(lambda c: c.data == "back_menu")
async def back_to_menu(call: types.CallbackQuery):
    user_id = call.from_user.id
    SEARCH_USERS.discard(user_id)
    LAST_SEARCH_MSG.pop(user_id, None)

    # Клавиатура с кнопкой вставки тега
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("▶️ Смотреть аниме", callback_data="open_anime"),
        # Кнопка вставки тега в поле ввода при нажатии
        InlineKeyboardButton(
            "🔍 Поиск", 
            switch_inline_query_current_chat=""
        ),
        InlineKeyboardButton("💳 Купить подписку", callback_data="choose_plan"),
        InlineKeyboardButton("ℹ️ Статус подписки", callback_data="sub_status")
    )

    try:
        await call.message.delete()
    except:
        pass

    await send_and_track(user_id, call.message.answer, "📋 Главное меню:", reply_markup=kb)
    await call.answer()


@dp.callback_query_handler(lambda c: c.data == "register")
async def register_user(call: types.CallbackQuery):
    import time
    from datetime import datetime, timedelta

    user_id = call.from_user.id

    # Проверяем, зарегистрирован ли пользователь в users
    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if cursor.fetchone():
        await call.answer("Ты уже зарегистрирован 😉", show_alert=True)
        return

    now_ts = int(time.time())
    trial_days = 7
    trial_until = now_ts + trial_days * 24 * 60 * 60  # 7 дней в секундах

    # Сохраняем в старой таблице (users)
    cursor.execute(
        "INSERT INTO users (user_id, first_start, paid_until) VALUES (?, ?, ?)",
        (user_id, now_ts, trial_until)
    )
    db.commit()

    # Сохраняем в новой таблице (subscriptions)
    expire_date = (datetime.now() + timedelta(days=trial_days)).isoformat()
    cursor.execute(
        "INSERT INTO subscriptions (user_id, type, expire_date) VALUES (?, ?, ?)",
        (user_id, "trial", expire_date)
    )
    db.commit()

    # Кнопка на список аниме
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("▶️ Смотреть аниме в 4K", callback_data="open_anime"))

    try:
        await call.message.delete()
    except:
        pass

    await send_and_track(
        user_id,
        call.message.answer,
        "✅ Регистрация завершена!\n\n"
        "🎁 Тебе доступна 1 неделя бесплатного просмотра.\n"
        "Приятного просмотра 🍿",
        reply_markup=kb
    )
    await call.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("open_anime"))
async def open_anime(call: types.CallbackQuery):
    user_id = call.from_user.id

    # Проверка подписки
    if not has_active_sub(user_id):
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("💳 Купить подписку", callback_data="buy_sub"),
            InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_menu")
        )
        try:
            await call.message.delete()
        except:
            pass
        await send_and_track(
            user_id,
            call.message.answer,
            "⛔ Доступ закрыт. Подписка закончилась.",
            reply_markup=kb
        )
        await call.answer("⛔ Подписка закончилась", show_alert=True)
        return

    # Получаем страницу
    page = 0
    if "|" in call.data:
        page = int(call.data.split("|")[1])

    cursor.execute("SELECT DISTINCT anime FROM videos ORDER BY anime")
    animes = [row[0] for row in cursor.fetchall()]

    total_pages = (len(animes) - 1) // ANIME_PER_PAGE + 1
    start = page * ANIME_PER_PAGE
    end = start + ANIME_PER_PAGE
    current_animes = animes[start:end]

    kb = InlineKeyboardMarkup(row_width=1)  # одна колонка

    # Добавляем аниме в кнопки
    for i, anime in enumerate(current_animes, start=start):
        title = anime.title()
        if len(title) > MAX_TITLE_LEN:
            title = title[:MAX_TITLE_LEN - 3] + "..."
        kb.add(
            InlineKeyboardButton(
                text=title,
                callback_data=f"anime_index|{i}"  # короткий callback
            )
        )

    # Кнопки пагинации
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton("⬅️ Назад", callback_data=f"open_anime|{page - 1}")
        )
    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton("➡️ Вперёд", callback_data=f"open_anime|{page + 1}")
        )
    if nav_buttons:
        kb.row(*nav_buttons)

    # Назад в меню
    kb.add(InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_menu"))

    try:
        await call.message.delete()
    except:
        pass

    await send_and_track(
        user_id,
        call.message.answer,
        f"🎌 Выбери аниме:",
        reply_markup=kb
    )
    await call.answer()

async def show_anime_page(message_or_call, anime_name):
    cursor.execute("""
        SELECT episode, file_id
        FROM videos
        WHERE anime=?
        ORDER BY episode
    """, (anime_name,))

    episodes = cursor.fetchall()

    if not episodes:
        await message_or_call.answer("❌ Аниме не найдено.")
        return

    kb = InlineKeyboardMarkup(row_width=4)
    for ep, file_id in episodes:
        kb.insert(
            InlineKeyboardButton(
                text=str(ep),
                callback_data=f"watch|{anime_name}|{ep}"
            )
        )

    kb.add(InlineKeyboardButton("⬅️ Назад к списку", callback_data="open_anime"))

    await message_or_call.answer(
        f"🎬 {anime_name}",
        reply_markup=kb
    )

# =========================
# Добавление видео (админ)
# =========================
@dp.message_handler(commands=['add'])
async def add_video(message: types.Message):
    if message.from_user.id not in ADMINS:
        await message.answer("❌ У тебя нет прав на добавление серий")
        return

    if not message.reply_to_message or not message.reply_to_message.video:
        await message.answer("❌ Команда должна быть в ответ на видео!")
        return

    try:
        cmd = message.text[5:].strip()
        anime, dub, season, episode = [x.strip() for x in cmd.split(";")]
    except ValueError:
        await message.answer(
            "❌ Неверный формат команды.\n"
            "Используй так:\n"
            "/add Название аниме ; Озвучка ; Сезон ; Серия\n"
            "Пример:\n"
            "/add One Piece ; Anilibria ; 1 ; 1"
        )
        return

    file_id = message.reply_to_message.video.file_id

    cursor.execute(
        "INSERT INTO videos (anime, dub, season, episode, file_id) VALUES (?, ?, ?, ?, ?)",
        (anime.lower(), dub, int(season), int(episode), file_id)
    )
    db.commit()

    await message.answer(f"✅ Серия добавлена:\n{anime.title()} | {dub} | Сезон {season} Серия {episode}")

# =========================
# Главное меню / Меню аниме
# =========================

@dp.callback_query_handler(lambda c: c.data == "search_menu")
async def search_menu(call: types.CallbackQuery):
    user_id = call.from_user.id
    SEARCH_USERS.add(user_id)

    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_menu")
    )

    try:
        await call.message.delete()
    except:
        pass

    msg = await send_and_track(
        user_id,
        call.message.answer,
        "🔎 Введи название аниме для поиска:",
        reply_markup=kb
    )

    if msg:
        LAST_SEARCH_MSG[user_id] = msg.message_id
    await call.answer()

@dp.callback_query_handler(lambda c: c.data == "sub_status")
async def sub_status(call: types.CallbackQuery):
    user_id = call.from_user.id

    cursor.execute("SELECT type, expire_date FROM subscriptions WHERE user_id=?", (user_id,))
    row = cursor.fetchone()

    if row:
        sub_type, expire_date_str = row
        expire_date = datetime.fromisoformat(expire_date_str)
        if expire_date > datetime.now():
            status_text = f"✅ Активная подписка:\n📅 До: {expire_date.strftime('%d.%m.%Y %H:%M')}"
        else:
            status_text = "❌ Подписка неактивна"
    else:
        status_text = "❌ Подписка неактивна"

    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_menu")
    )

    try:
        await call.message.delete()
    except:
        pass

    await send_and_track(
        user_id,
        call.message.answer,
        status_text,
        reply_markup=kb
    )
    await call.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("buy_") and c.data != "buy_sub")
async def process_tariff(call):
    user_id = call.from_user.id

    tariffs_map = {
        "buy_7": "7_days",
        "buy_30": "30_days",
        "buy_180": "180_days",
        "buy_360": "360_days",
        "buy_forever": "forever"
    }

    period_key = tariffs_map.get(call.data)
    if not period_key:
        return

    rub_amount = RUB_PRICES[period_key]
    PENDING_PAYMENTS[user_id] = period_key

    text = (
        f"💳 Вы выбрали подписку: <b>{period_key.replace('_', ' ')}</b>\n\n"
        f"💵 Цена: <b>{rub_amount}₽</b>\n\n"
        "Выберите способ оплаты:"
    )

    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("💎 Оплатить криптовалютой", callback_data="pay_crypto"),
        InlineKeyboardButton("💵 Оплатить рублями", callback_data="pay_rub"),
        InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_menu")
    )

    try:
        await send_and_track(user_id, call.message.edit_text, text, parse_mode="HTML", reply_markup=kb)
    except:
        await send_and_track(user_id, call.message.answer, text, parse_mode="HTML", reply_markup=kb)

    await call.answer()

# ===== Рублевая оплата =====
@dp.callback_query_handler(lambda c: c.data == "pay_rub")
async def pay_rub_handler(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    period_key = PENDING_PAYMENTS.get(user_id)
    rub_amount = RUB_PRICES.get(period_key, 0)

    # Удаляем предыдущее сообщение с выбором оплаты
    await delete_bot_messages(user_id, chat_id)

    text = (
        f"📌 Переведите <b>{rub_amount}₽</b> на номер:\n"
        "<b>79133295900</b>\n🏦 Почта Банк / Ozon Банк\n\n"
        "После оплаты нажмите кнопку ниже для подтверждения."
    )
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("✅ Подтвердить оплату", callback_data="confirm_payment"),
        InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_menu")
    )

    await send_and_track(user_id, call.message.answer, text, reply_markup=kb)
    await call.answer()

# ===== Криптооплата =====

def create_crypto_invoice(user_id, rub_amount, period_key):
    invoice = crypto.create_invoice(
        asset="USDT",
        amount=rub_amount,
        description="Оплата подписки",
        payload=f"{user_id}|{period_key}"
    )

    return invoice["pay_url"]

@dp.callback_query_handler(lambda c: c.data.startswith("pay_") and c.data != "pay_rub")
async def pay_crypto_handler(call: types.CallbackQuery):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    period_key = PENDING_PAYMENTS.get(user_id)

    if not period_key:
        await call.answer("Ошибка периода", show_alert=True)
        return

    rub_amount = RUB_PRICES.get(period_key, 0)

    # Удаляем предыдущее сообщение с выбором оплаты
    await delete_bot_messages(user_id, chat_id)

    # Создаём invoice в RUB через CryptoBot
    invoice_url = create_crypto_invoice(user_id, rub_amount, period_key)

    if not invoice_url:
        await call.answer("Ошибка создания счета", show_alert=True)
        return

    text = (
        f"💰 Оплата подписки\n"
        f"Сумма: {rub_amount}₽\n\n"
        "После нажатия кнопки вы перейдёте в CryptoBot, "
        "где сможете выбрать любую криптовалюту для оплаты.\n\n"
        "При оплате со стороннего кошелька нажмите кнопку 'Перейти к оплате' "
        "и переводите на указанный кошелек указанную стоимость в выбранной вами валюте.\n\n"
        "Если вы переводите криптовалюту со стороннего кошелька или вам не пришла подписка автоматически, "
        "то нажмите кнопку 'Подтвердить оплату' и действуйте по инструкциям.\n\n"
        "После успешной оплаты подписка активируется автоматически."
    )

    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("💳 Перейти к оплате", url=invoice_url),
        InlineKeyboardButton("✅ Подтвердить оплату", callback_data="confirm_payment"),
        InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_menu")
    )

    await send_and_track(user_id, call.message.answer, text, reply_markup=kb)
    await call.answer()

# ===== Вебхук Crypto.bot =====
# ===== Вебхук Crypto.bot с минимальной защитой =====
async def handle_crypto_webhook(request):
    try:
        # Проверяем User-Agent
        user_agent = request.headers.get("User-Agent", "")
        if "bothost" not in user_agent.lower():
            return web.Response(text="Unauthorized", status=401)

        # Получаем JSON
        data = await request.json()

        # Проверяем событие оплаты
        if data.get("update_type") != "invoice_paid":
            return web.Response(text="Ignored")

        invoice = data.get("payload", {})
        if invoice.get("status") != "paid":
            return web.Response(text="Not paid")

        payload_data = invoice.get("payload")
        user_id_str, period_key = payload_data.split("|")
        user_id = int(user_id_str)

        # Вычисляем дни подписки
        days = None if period_key == "forever" else int(period_key.split("_")[0])

        # Выдаём подписку
        give_subscription(user_id, days)

        # Сообщение пользователю
        if days is None:
            await bot.send_message(user_id, "🎉 Ваша подписка НАВСЕГДА активирована!")
        else:
            await bot.send_message(user_id, f"🎉 Ваша подписка на {days} дней активирована!")

        return web.Response(text="OK")

    except Exception as e:
        print(f"[Webhook] Ошибка: {e}")
        return web.Response(text="Error", status=500)


app = web.Application()
WEBHOOK_URL = "/webhook"
app.router.add_post(WEBHOOK_URL, handle_crypto_webhook)

@dp.callback_query_handler(lambda c: c.data == "confirm_payment")
async def confirm_payment(call: types.CallbackQuery):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    await delete_bot_messages(user_id, chat_id)

    WAITING_CHECK.add(user_id)

    await send_and_track(
        user_id,
        call.message.answer,
        "📎 Отправьте скрин или файл чека перевода"
    )

    await call.answer()

@dp.message_handler(content_types=["photo", "document"])
async def handle_check(message: types.Message):
    user_id = message.from_user.id

    if user_id not in WAITING_CHECK:
        return

    WAITING_CHECK.remove(user_id)
    period = PENDING_PAYMENTS.get(user_id, "не указан")

    # Сообщение пользователю
    text_user = (
        "⏳ Ожидайте выдачи подписки.\n\n"
        "🕓 По будням: 04:00–21:00 МСК\n"
        "🕙 По выходным: 10:00–01:00 МСК\n\n"
        "Выдача обычно от нескольких минут до 3 часов\n"
        "(иногда дольше)"
    )

    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_menu")
    )

    await send_and_track(
        user_id,
        message.answer,
        text_user,
        reply_markup=kb
    )

    # 🔔 Отправка админам
    admin_text = (
        f"💰 Новая заявка на подписку\n\n"
        f"👤 ID: {user_id}\n"
        f"📅 Тариф: {period}"
    )

    for admin_id in ADMINS:
        if message.photo:
            await bot.send_photo(
                admin_id,
                message.photo[-1].file_id,
                caption=admin_text
            )
        else:
            await bot.send_document(
                admin_id,
                message.document.file_id,
                caption=admin_text
            )



@dp.message_handler(content_types=["text"])
async def live_search(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    query = message.text.lower().strip()

    if not query:
        return

    await delete_bot_messages(user_id, chat_id)

    # Ищем максимум 5 совпадений
    cursor.execute(
        "SELECT DISTINCT anime FROM videos WHERE LOWER(anime) LIKE ? LIMIT 5",
        (f"%{query}%",)
    )
    found_animes = [row[0] for row in cursor.fetchall()]

    if not found_animes:
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_menu")
        )
        await send_and_track(
            user_id,
            message.answer,
            "❌ Ничего не найдено",
            reply_markup=kb
        )
        return

    # Получаем полный список (для индексов!)
    cursor.execute("SELECT DISTINCT anime FROM videos ORDER BY anime")
    all_animes = [row[0] for row in cursor.fetchall()]

    for anime in found_animes:

        # Получаем индекс аниме
        try:
            anime_idx = all_animes.index(anime)
        except ValueError:
            continue  # если вдруг не найдено — пропускаем

        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(
            InlineKeyboardButton("▶️ Открыть", callback_data=f"anime_index|{anime_idx}"),
            InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_menu")
        )

        # Получаем инфу
        info = None
        poster_url = None

        try:
            info = await get_anime_info(anime)
        except:
            info = None

        if info:
            cursor.execute(
                "SELECT english_name FROM videos WHERE anime=? LIMIT 1",
                (anime,)
            )
            row = cursor.fetchone()
            title_for_poster = (
                row[0] if row and row[0]
                else info.get("english")
                or info.get("title")
                or anime
            )

            try:
                poster_url = await search_anilist_poster(title_for_poster)
            except:
                poster_url = info.get("poster")

        text = anime.title()
        if info:
            text = (
                f"<b>{info.get('title', anime)}</b>\n"
                f"⭐ Рейтинг: {info.get('score', '—')}\n"
                f"📅 Год: {info.get('year', '—')}\n"
                f"🎭 Жанры: {info.get('genres', '—')}"
            )

        try:
            if poster_url:
                await send_and_track(
                    user_id,
                    message.answer_photo,
                    photo=poster_url,
                    caption=text,
                    parse_mode="HTML",
                    reply_markup=kb,
                    protect_content=True
                )
            elif info and info.get("poster"):
                await send_and_track(
                    user_id,
                    message.answer_photo,
                    photo=info["poster"],
                    caption=text,
                    parse_mode="HTML",
                    reply_markup=kb,
                    protect_content=True
                )
            else:
                await send_and_track(
                    user_id,
                    message.answer,
                    text,
                    parse_mode="HTML",
                    reply_markup=kb,
                    protect_content=True
                )
        except Exception as e:
            print(f"Ошибка отправки сообщения для {anime}: {e}")



# =========================
# Выбор аниме
# =========================
# =========================
# Выбор аниме
# =========================

async def search_anilist_poster(title_en: str) -> str | None:
    """
    Поиск постера на AniList по английскому названию.
    Возвращает URL постера в максимально доступном качестве или None, если не найден.
    """
    query = '''
    query ($search: String) {
      Media(search: $search, type: ANIME) {
        coverImage {
          extraLarge
          large
        }
      }
    }
    '''
    variables = {"search": title_en}

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://graphql.anilist.co",
            json={"query": query, "variables": variables}
        ) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            media = data.get("data", {}).get("Media")
            if media and media.get("coverImage"):
                # Сначала пробуем extraLarge, если нет — large
                return media["coverImage"].get("extraLarge") or media["coverImage"].get("large")
    return None

@dp.inline_handler()
async def inline_search(query: types.InlineQuery):
    search_text = query.query.strip()
    if not search_text:
        return

    cursor.execute(
        "SELECT DISTINCT anime, english_name FROM videos WHERE LOWER(anime) LIKE ? GROUP BY anime LIMIT 5",
        (f"%{search_text.lower()}%",)
    )
    rows = cursor.fetchall()
    if not rows:
        return

    results = []

    for anime_name, english_name in rows:
        info = await get_anime_info(anime_name)
        if not info:
            continue

        poster_url = await search_anilist_poster(english_name or anime_name) or info.get("poster")

        # Рейтинг
        score = info.get("score", "—")

        # Жанры
        genres_data = info.get("genres", "—")
        if isinstance(genres_data, list):
            genres = ", ".join(genres_data)
        else:
            genres = genres_data

        # Год и статус
        year = info.get("year", "—")
        status = info.get("status", "—")

        # Красивое описание
        description = f"⭐ {score} | 🎭 {genres} | 📅 {year}"

        results.append(InlineQueryResultArticle(
            id=str(uuid4()),
            title=anime_name,
            description=description,
            input_message_content=InputTextMessageContent(
                message_text=f"{anime_name}"
            ),
            thumb_url=poster_url
        ))

    if results:
        await query.answer(results=results, cache_time=1, is_personal=True)




# =========================
# Перехватываем выбор из inline и вызываем твой callback
# =========================
@dp.message_handler(lambda m: True)
async def inline_trigger_to_search(message: types.Message):
    # Проверяем, что сообщение не команда и не видео
    if message.text and not message.text.startswith("/"):
        user_id = message.from_user.id
        chat_id = message.chat.id
        query = message.text.strip()

        # Вызываем live_search напрямую
        await live_search(message)

# =========================
# Твой существующий callback без изменений
# =========================
@dp.callback_query_handler(lambda c: c.data.startswith("anime_index|"))
async def anime_selected(call: types.CallbackQuery):
    user_id = call.from_user.id

    # Берём индекс из callback_data
    _, idx_str = call.data.split("|")
    idx = int(idx_str)

    # Получаем список всех аниме из базы
    cursor.execute("SELECT DISTINCT anime FROM videos ORDER BY anime")
    animes = [row[0] for row in cursor.fetchall()]

    if idx < 0 or idx >= len(animes):
        await call.answer("❌ Ошибка: аниме не найдено", show_alert=True)
        return

    # Берём реальное название аниме
    anime = animes[idx]

    # === Дальше идёт твой оригинальный код ===
    # Получаем информацию с Shikimori
    info = await get_anime_info(anime)
    if not info:
        await send_and_track(user_id, call.message.answer, "❌ Не удалось получить информацию об аниме с Shikimori")
        return

    cursor.execute("SELECT english_name FROM videos WHERE anime=? LIMIT 1", (anime,))
    row = cursor.fetchone()
    title_for_poster = row[0] if row and row[0] else info.get("english") or info.get("name") or anime

    poster_url = await search_anilist_poster(title_for_poster)
    if not poster_url:
        poster_url = info.get("poster")

    description = info.get("description", "Описание отсутствует")

# 🧼 Полная очистка
    description = clean_shikimori_description(description)

# Берём только первый абзац
    first_paragraph = description.split("\n\n")[0].strip()

    MAX_LEN = 800

    if len(first_paragraph) > MAX_LEN:
        cut_text = first_paragraph[:MAX_LEN]

    # Ищем последнюю точку / ! / ?
        match = re.search(r'[.!?](?!.*[.!?])', cut_text)

        if match:
            first_paragraph = cut_text[:match.end()]
        else:
            first_paragraph = cut_text.rstrip() + "…"

    shiki_status = info.get("status", "").lower()
    status_text = {"released": "Вышло", "ongoing": "Онгоинг", "anons": "Анонс"}.get(shiki_status, "Неизвестно")

    text = (
        f"<b>{info.get('title', anime)}</b>\n"
        f"⭐ Рейтинг: <b>{info.get('score', 'N/A')}</b>\n"
        f"🎭 Жанры: {info.get('genres', 'Неизвестно')}\n"
        f"📅 Год: {info.get('year', 'N/A')}\n"
        f"📝 {first_paragraph}"
    )

    cursor.execute("SELECT DISTINCT season FROM videos WHERE anime=? ORDER BY season", (anime,))
    seasons = [row[0] for row in cursor.fetchall()]

    kb = InlineKeyboardMarkup(row_width=2)

    for season in seasons:
        season_str = str(season).lower()

        if season_str in ["film", "фильм", "movie"]:
            button_text = "🎬 Фильм"
        else:
            button_text = f"Сезон {season}"

        cb_id = make_cb_id(anime, str(season))
        kb.add(
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"season|{cb_id}"
            )
        )

    kb.add(
        InlineKeyboardButton("⬅️ Назад к списку аниме", callback_data="back_anime"),
        InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_menu")
    )

    try:
        await call.message.delete()
    except:
        pass

    if poster_url:
        await send_and_track(
            user_id,
            call.message.answer_photo,
            photo=poster_url,
            caption=text,
            parse_mode="HTML",
            reply_markup=kb,
            protect_content=True
        )
    else:
        await send_and_track(
            user_id,
            call.message.answer,
            text,
            parse_mode="HTML",
            reply_markup=kb,
            protect_content=True
        )

    await call.answer()






# =========================
# Назад к списку аниме
# =========================
@dp.callback_query_handler(lambda c: c.data.startswith("back_anime"))
async def back_to_anime(call: types.CallbackQuery):
    user_id = call.from_user.id

    # Получаем страницу
    page = 0
    if "|" in call.data:
        page = int(call.data.split("|")[1])

    cursor.execute("SELECT DISTINCT anime FROM videos ORDER BY anime")
    animes = [row[0] for row in cursor.fetchall()]

    total_pages = (len(animes) - 1) // ANIME_PER_PAGE + 1
    start = page * ANIME_PER_PAGE
    end = start + ANIME_PER_PAGE
    current_animes = animes[start:end]

    kb = InlineKeyboardMarkup(row_width=1)  # одна колонка

    # Добавляем аниме в кнопки с обрезкой
    for i, anime in enumerate(current_animes, start=start):
        title = anime.title()
        if len(title) > MAX_TITLE_LEN:
            title = title[:MAX_TITLE_LEN - 3] + "..."
        kb.add(
            InlineKeyboardButton(
                text=title,
                callback_data=f"anime_index|{i}"  # короткий callback
            )
        )

    # Кнопки пагинации
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton("⬅️ Назад", callback_data=f"back_anime|{page - 1}")
        )
    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton("➡️ Вперёд", callback_data=f"back_anime|{page + 1}")
        )
    if nav_buttons:
        kb.row(*nav_buttons)

    # Назад в меню
    kb.add(InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_menu"))

    try:
        await call.message.delete()
    except:
        pass

    await send_and_track(
        user_id,
        call.message.answer,
        f"🎌 Выбери аниме:",
        reply_markup=kb
    )
    await call.answer()


# =========================
# Выбор сезона после аниме
# =========================
@dp.callback_query_handler(lambda c: c.data.startswith("season|") or c.data.startswith("back_season|"))
async def choose_dub_after_season(call: types.CallbackQuery):
    user_id = call.from_user.id
    parts = call.data.split("|")

    if parts[0] == "back_season":
        season_hash, anime_name = parts[1], parts[2]
    else:
        season_hash = parts[1]
        anime_name = None

    # Находим anime и season по хэшу
    cursor.execute("SELECT anime, season FROM videos")
    rows = cursor.fetchall()
    season = None
    for a, s in rows:
        if make_cb_id(a, str(s)) == season_hash:
            anime_name, season = a, s
            break
    if not anime_name or not season:
        await call.answer("❌ Ошибка данных", show_alert=True)
        return

    # Получаем доступные озвучки для выбранного сезона
    cursor.execute(
        "SELECT DISTINCT dub FROM videos WHERE anime=? AND season=? ORDER BY dub",
        (anime_name, season)
    )
    dubs = [row[0] for row in cursor.fetchall()]
    if not dubs:
        await call.answer("❌ Озвучек нет", show_alert=True)
        return

    kb = InlineKeyboardMarkup(row_width=1)
    for dub in dubs:
        cb_id = make_cb_id(anime_name, dub, str(season))
        kb.add(InlineKeyboardButton(text=f"▶️ Озвучка: {dub}", callback_data=f"dub|{cb_id}"))

    # Получаем индекс аниме для безопасного callback_data
    cursor.execute("SELECT DISTINCT anime FROM videos ORDER BY anime")
    all_animes = [row[0] for row in cursor.fetchall()]
    try:
        anime_idx = all_animes.index(anime_name)
    except ValueError:
        await call.answer("❌ Ошибка данных", show_alert=True)
        return

    kb.add(
        InlineKeyboardButton("⬅️ Назад к аниме", callback_data=f"anime_index|{anime_idx}"),
        InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_menu")
    )

    try:
        await call.message.delete()
    except:
        pass

    await send_and_track(user_id, call.message.answer, f"📺 Выбор озвучки:", reply_markup=kb)
    await call.answer()


# =========================
# Выбор серии после озвучки
# =========================
@dp.callback_query_handler(lambda c: c.data.startswith("dub|"))
async def show_episodes_after_dub(call: types.CallbackQuery):
    user_id = call.from_user.id
    parts = call.data.split("|")
    dub_hash = parts[1]
    page = int(parts[2]) if len(parts) > 2 else 0

    # Определяем anime, dub, season
    cursor.execute("SELECT anime, dub, season FROM videos")
    rows = cursor.fetchall()
    anime = dub = season = None
    for a, d, s in rows:
        if make_cb_id(a, d, str(s)) == dub_hash:
            anime, dub, season = a, d, s
            break
    if not anime:
        await call.answer("❌ Ошибка данных", show_alert=True)
        return

    # Получаем все серии
    cursor.execute(
        "SELECT episode, file_id FROM videos WHERE anime=? AND dub=? AND season=? ORDER BY episode",
        (anime, dub, season)
    )
    rows = cursor.fetchall()
    episodes = [(r[0], r[1]) for r in rows]
    if not episodes:
        await call.answer("❌ Серий нет", show_alert=True)
        return

    start = page * EPISODES_PER_PAGE
    end = start + EPISODES_PER_PAGE
    page_episodes = episodes[start:end]

    kb = InlineKeyboardMarkup(row_width=EPISODES_PER_ROW)
    for i in range(0, len(page_episodes), EPISODES_PER_ROW):
        row = [
            InlineKeyboardButton(
                text=str(ep),
                callback_data=f"ep|{make_cb_id(anime, dub, str(season), str(ep))}|{page}"
            ) for ep, _ in page_episodes[i:i + EPISODES_PER_ROW]
        ]
        kb.row(*row)

    # Навигация по страницам
    nav_buttons = []
    if start > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"dub|{dub_hash}|{page-1}"))
    if end < len(episodes):
        nav_buttons.append(InlineKeyboardButton("➡️ Далее", callback_data=f"dub|{dub_hash}|{page+1}"))
    if nav_buttons:
        kb.row(*nav_buttons)

    kb.add(
        InlineKeyboardButton("⬅️ Назад к озвучкам", callback_data=f"season|{make_cb_id(anime, str(season))}"),
        InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_menu")
    )

    try:
        await call.message.delete()
    except:
        pass

    await send_and_track(user_id, call.message.answer, f"🎬 Выбор серии:", reply_markup=kb)
    await call.answer()

# =========================
# Отправка видео с send_and_track
# =========================
@dp.callback_query_handler(lambda c: c.data.startswith("ep|"))
async def send_video(call: types.CallbackQuery):
    user_id = call.from_user.id

    # Проверка подписки через новую таблицу
    cursor.execute("SELECT expire_date FROM subscriptions WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    from datetime import datetime
    has_sub = False
    if row:
        expire_date = datetime.fromisoformat(row[0])
        if expire_date > datetime.now():
            has_sub = True

    if not has_sub:
        kb = InlineKeyboardMarkup(row_width=1).add(
            InlineKeyboardButton("💳 Купить подписку", callback_data="buy_sub"),
            InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_menu")
        )
        try:
            await call.message.delete()
        except:
            pass
        await send_and_track(user_id, call.message.answer, "⛔ Для просмотра серии нужна подписка", reply_markup=kb)
        await call.answer("⛔ Подписка закончилась", show_alert=True)
        return

    # Разбираем данные серии
    _, ep_hash, page = call.data.split("|")
    page = int(page)

    # Находим серию в базе
    cursor.execute("SELECT anime, dub, season, episode, file_id FROM videos")
    rows = cursor.fetchall()
    anime = dub = season = ep = file_id = None
    for a, d, s, e, f in rows:
        if make_cb_id(a, d, str(s), str(e)) == ep_hash:
            anime, dub, season, ep, file_id = a, d, s, e, f
            break

    if not file_id:
        await call.answer("❌ Видео не найдено", show_alert=True)
        return

    caption = f"<b>{anime.title()}</b>\n<b><i>{dub}</i></b>\n<i>{season} сезон {ep} серия</i>"

    # Формируем клавиатуру
    kb = InlineKeyboardMarkup(row_width=2)

    # Проверяем предыдущую и следующую серии
    cursor.execute("SELECT 1 FROM videos WHERE anime=? AND dub=? AND season=? AND episode=?", (anime, dub, season, ep - 1))
    prev_exists = cursor.fetchone()
    cursor.execute("SELECT 1 FROM videos WHERE anime=? AND dub=? AND season=? AND episode=?", (anime, dub, season, ep + 1))
    next_exists = cursor.fetchone()

    nav_buttons = []
    if prev_exists:
        nav_buttons.append(InlineKeyboardButton("⬅️ Предыдущая серия", callback_data=f"ep|{make_cb_id(anime, dub, str(season), str(ep - 1))}|{page}"))
    if next_exists:
        nav_buttons.append(InlineKeyboardButton("➡️ Следующая серия", callback_data=f"ep|{make_cb_id(anime, dub, str(season), str(ep + 1))}|{page}"))
    if nav_buttons:
        kb.row(*nav_buttons)

    kb.add(
        InlineKeyboardButton("⬅️ Вернуться к сериям", callback_data=f"dub|{make_cb_id(anime, dub, str(season))}|{page}"),
        InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_menu")
    )

    try:
        await call.message.delete()  # удаляем старое сообщение один раз
    except:
        pass

    if isinstance(file_id, str) and file_id.startswith("http"):
        kb.add(InlineKeyboardButton("🌐 Скачать серию из облака", url=file_id))
        await send_and_track(user_id, call.message.answer, caption, parse_mode="HTML", reply_markup=kb, protect_content=True)
    else:
        await send_and_track(user_id, bot.send_video, chat_id=call.message.chat.id, video=file_id, caption=caption, parse_mode="HTML", reply_markup=kb, protect_content=True)

    await call.answer()


def start_webhook():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    runner = web.AppRunner(app)
    loop.run_until_complete(runner.setup())
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    loop.run_until_complete(site.start())
    print("Webhook сервер запущен на порту 8080")
    loop.run_forever()

if __name__ == "__main__":
    # Запускаем aiohttp вебхук в фоне
    threading.Thread(target=start_webhook, daemon=True).start()

    # Запускаем polling бота aiogram 2.25
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)