from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ContentType,
    BotCommand,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineQueryResultPhoto
)

import requests
import random
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
import ssl
import random
import string

PAGE_SIZE = 50
EPISODES_PER_ROW = 5
ROWS_PER_PAGE = 10
ANIME_PER_PAGE = 10
MAX_TITLE_LEN = 30
EPISODES_PER_PAGE = EPISODES_PER_ROW * ROWS_PER_PAGE
WAITING_CHECK = set()
PENDING_PAYMENTS = {}
SHIKI_CACHE = {}
PROCESSED_INVOICES = set()
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
CRYPTOBOT_API_CREATE = "https://pay.crypt.bot/api/createInvoice"
URL_RE = re.compile(r'https?://\S+')
ANILIST_API = "https://graphql.anilist.co"

TARIFFS = {
    "7": {"title": "7 дней", "days": 7},
    "30": {"title": "30 дней", "days": 30},
    "180": {"title": "180 дней", "days": 180},
    "360": {"title": "360 дней", "days": 360},
    "forever": {"title": "Навсегда", "days": None}
}

RUB_PRICES = {
    "7_days": 39,
    "30_days": 99,
    "180_days": 499,
    "360_days": 899,
    "forever": 1499
}

PERIOD_KEY_MAP = {
    "buy_7": "7_days",
    "buy_30": "30_days",
    "buy_180": "180_days",
    "buy_360": "360_days",
    "buy_forever": "forever"
}


tariffs_map = {
        "buy_7": "7_days",
        "buy_30": "30_days",
        "buy_180": "180_days",
        "buy_360": "360_days",
        "buy_forever": "forever"
    }


# =========================
# Настройки
# =========================
API_TOKEN = os.getenv("BOT_TOKEN")
CRYPTOBOT_TOKEN = os.getenv("CRYPTOBOT_TOKEN")
WEBHOOK_FULL_URL = os.getenv("WEBHOOK_FULL_URL")

ADMINS = [6265184966]
ADMIN_CHAT_ID = ADMINS[0]

bot = Bot(token=API_TOKEN)

dp = Dispatcher()
router = Router()
dp.include_router(router)

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

cursor.execute("""
CREATE TABLE IF NOT EXISTS processed_invoices (
    invoice_id TEXT PRIMARY KEY,
    user_id INTEGER,
    period_key TEXT,
    created_at TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS referrals (
    user_id INTEGER PRIMARY KEY,
    my_code TEXT UNIQUE,
    used_code TEXT,
    referred_by INTEGER,
    bonus_given INTEGER DEFAULT 0,
    months_awarded INTEGER DEFAULT 0,
    first_name TEXT,
    username TEXT,
    created_at TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS watch_history (
    user_id INTEGER,
    anime TEXT,
    dub TEXT,
    season INTEGER,
    episode INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, anime, dub, season)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS pending_payments (
    user_id INTEGER PRIMARY KEY,
    invoice_id TEXT,
    period_key TEXT,
    created_at TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS anime_info (
    anime TEXT PRIMARY KEY,
    poster TEXT,
    poster_file_id TEXT,
    score TEXT,
    genres TEXT,
    year TEXT
)
""")

db.commit()


# --- Безопасно добавляем pay_url (если её нет) ---
cursor.execute("PRAGMA table_info(pending_payments)")
columns = [col[1] for col in cursor.fetchall()]

if "pay_url" not in columns:
    cursor.execute("ALTER TABLE pending_payments ADD COLUMN pay_url TEXT")
    db.commit()

cursor.execute("PRAGMA table_info(videos)")
columns = [col[1] for col in cursor.fetchall()]

if "title_en" not in columns:
    cursor.execute("ALTER TABLE videos ADD COLUMN title_en TEXT")
    db.commit()
    print("✅ Колонка title_en создана в таблице videos")


def cut_title(title: str, max_len: int = MAX_TITLE_LEN) -> str:
    """Обрезаем длинные названия аниме для кнопок"""
    return title if len(title) <= max_len else title[:max_len - 3] + "..."


r = requests.get(f"https://api.telegram.org/bot{API_TOKEN}/setWebhook?url={WEBHOOK_FULL_URL}")
print(r.text)  # должен вернуть {"ok":true,...}


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


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

    # Удаляем BB-коды
    text = re.sub(r"\[/?[a-zA-Z0-9_= \"'-]+\]", "", text)

    # Удаляем конструкции вида [character=123]
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

        async with session.get(
            f"https://shikimori.one/api/animes/{anime_id}",
            headers=headers
        ) as resp:

            if resp.status != 200:
                return None

            full = await resp.json()

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
        "genres": ", ".join(
            g.get("russian", g.get("name", "")) for g in full.get("genres", [])
        ) or "—",
        "description": full.get("description") or "Описание отсутствует",
        "poster": f"https://shikimori.one{full['image']['original']}" if full.get("image") else None,
        "status_text": status_text
    }

    SHIKI_CACHE[title] = info
    return info
# =========================
# Стартап
# =========================
async def on_startup():
    await bot.set_my_commands([
        BotCommand(command="/start", description="Перезапуск бота")
    ])
    print("Бот запущен ✅")


# =========================
# /start
# =========================

class ReferralState(StatesGroup):
    waiting_ref_code = State()

@router.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    args = ""
    if message.text and len(message.text.split()) > 1:
        args = message.text.split(maxsplit=1)[1]

    await delete_bot_messages(user_id, chat_id)

    # ===== ЕСЛИ ПРИШЁЛ DEEP LINK =====
    if args.startswith("anime_"):
        anime_name = urllib.parse.unquote(args.replace("anime_", "", 1))

        if not has_active_sub(user_id):
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=" Купить подписку", callback_data="choose_plan",style="success",icon_custom_emoji_id="5418115271267197333")],
                    [InlineKeyboardButton(text=" Назад в меню", callback_data="back_menu",style="primary",icon_custom_emoji_id="5352759161945867747")]
                ]
            )

            await send_and_track(
                user_id,
                message.answer,
                "<tg-emoji emoji-id=\"5260293700088511294\">👍</tg-emoji> Доступ закрыт. Подписка закончилась.",
                parse_mode="HTML",
                reply_markup=kb
            )
            return

        await show_anime_page(message, anime_name)
        return

    # ===== ОБЫЧНЫЙ START =====

    photo_id = "AgACAgIAAxkBAAIBKGmKXnQ3GN0fEp0gZvlZ-e05w14kAALGE2sbUvNRSB8Eq4CFt69-AQADAgADeQADOgQ"

    text = (
        "🌠 Привет!\n"
        "Я бот для просмотра аниме в 4К качестве.👘\n"
        "Первые 7 дней можно будет опробовать меня абсолютно бесплатно!\n"
        "Также переходите в наш новостной канал t.me/Aniimes4K"
    )

    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    exists = cursor.fetchone()

    if not exists:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=" Регистрация",callback_data="register",style="success",icon_custom_emoji_id="5373251851074415873")]
            ]
        )
    else:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=" Смотреть аниме в 4K", callback_data="back_menu",style="danger",icon_custom_emoji_id="5348125953090403204")]
            ]
        )

    await send_and_track(
        user_id,
        bot.send_photo,
        chat_id=chat_id,
        photo=photo_id,
        parse_mode="HTML",
        caption=text,
        reply_markup=kb
    )

def generate_ref_code():
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=6))

def create_user_referral(user_id: int):
    # генерируем уникальный код
    while True:
        my_code = generate_ref_code()

        cursor.execute(
            "SELECT 1 FROM referrals WHERE my_code=?",
            (my_code,)
        )

        if not cursor.fetchone():
            break

    # сохраняем
    cursor.execute("""
        INSERT INTO referrals (user_id, my_code)
        VALUES (?, ?)
    """, (user_id, my_code))

    db.commit()

async def process_referral_bonus(user_id: int, period_key: str):

    # бонус только для 30+ дней
    if period_key not in ("30_days", "180_days", "360_days", "forever"):
        return

    # получаем данные пользователя
    cursor.execute("""
        SELECT referred_by, bonus_given
        FROM referrals
        WHERE user_id = ?
    """, (user_id,))
    row = cursor.fetchone()

    if not row:
        return

    referred_by, bonus_given = row

    if not referred_by:
        return

    # если бонус уже выдан — выходим
    if bonus_given == 1:
        return

    inviter_id = referred_by

    # ==============================
    # 🎁 1 неделя обоим
    # ==============================

    give_subscription(user_id, 7)
    give_subscription(inviter_id, 7)

    # отмечаем бонус как использованный
    cursor.execute("""
        UPDATE referrals
        SET bonus_given = 1
        WHERE user_id = ?
    """, (user_id,))

    # ==============================
    # 🏆 Логика каждого 5-го реферала
    # ==============================

    # сколько рефералов выполнили условие
    cursor.execute("""
        SELECT COUNT(*)
        FROM referrals
        WHERE referred_by = ?
          AND bonus_given = 1
    """, (inviter_id,))

    count = cursor.fetchone()[0]

    # сколько месяцев уже выдано
    cursor.execute("""
        SELECT months_awarded
        FROM referrals
        WHERE user_id = ?
    """, (inviter_id,))

    row_months = cursor.fetchone()
    months_awarded = row_months[0] if row_months else 0

    # сколько месяцев должно быть
    should_have_months = count // 5

    month_awarded = False

    if should_have_months > months_awarded:
        give_subscription(inviter_id, 30)

        cursor.execute("""
            UPDATE referrals
            SET months_awarded = ?
            WHERE user_id = ?
        """, (should_have_months, inviter_id))

        month_awarded = True

    db.commit()

    # ==============================
    # 📩 Уведомления
    # ==============================

    try:
        # уведомление пользователю
        await bot.send_message(
            user_id,
            "<tg-emoji emoji-id=\"5461151367559141950\">👍</tg-emoji> <b>Бонус активирован!</b>\n\n"
            "Вы получили <b>7 дней подписки</b> <tg-emoji emoji-id=\"5424972470023104089\">👍</tg-emoji>",
            parse_mode="HTML"
        )

        # уведомление пригласившему
        if month_awarded:
            await bot.send_message(
                inviter_id,
                "<tg-emoji emoji-id=\"5312315739842026755\">👍</tg-emoji> <b>Поздравляем!</b>\n\n"
                "Каждые 5 рефералов = 1 месяц <tg-emoji emoji-id=\"5424972470023104089\">👍</tg-emoji>\n"
                "Вам начислен <b>1 месяц подписки</b>!",
                parse_mode="HTML"
            )
        else:
            await bot.send_message(
                inviter_id,
                "<tg-emoji emoji-id=\"5366355709850045324\">👍</tg-emoji> <b>Новый реферал!</b>\n\n"
                "Вам начислено <b>+7 дней</b> <tg-emoji emoji-id=\"5449800250032143374\">👍</tg-emoji>",
                parse_mode="HTML"
            )

    except Exception:
        pass

@router.callback_query(F.data == "ref_menu")
async def referral_menu(call: types.CallbackQuery):
    user_id = call.from_user.id

    # ==============================
    # 🔹 Получаем или создаём код
    # ==============================

    cursor.execute(
        "SELECT my_code FROM referrals WHERE user_id = ?",
        (user_id,)
    )
    row = cursor.fetchone()

    if not row:
        create_user_referral(user_id)

        cursor.execute(
            "SELECT my_code FROM referrals WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()

    my_code = row[0]

    # ==============================
    # 🔹 Получаем список рефералов
    # ==============================

    cursor.execute("""
        SELECT user_id
        FROM referrals
        WHERE referred_by = ?
          AND bonus_given = 1
    """, (user_id,))

    invited_users = cursor.fetchall()

    # ==============================
    # 🔹 Формируем текст
    # ==============================

    text = (
        "<tg-emoji emoji-id=\"5366355709850045324\">👍</tg-emoji> <b>Реферальная программа</b>\n\n"
        f"🔑 Ваш код: <b>{my_code}</b>\n\n"
        "<tg-emoji emoji-id=\"5397782960512444700\">👍</tg-emoji> <b>Условия:</b>\n"
        "• Если друг купит подписку на 30 дней и больше — "
        "оба получают <b>1 неделю бесплатно</b> <tg-emoji emoji-id=\"5449800250032143374\">👍</tg-emoji>\n"
        "• За каждого <b>5-го приглашённого</b> вы получаете "
        "<b>1 месяц бесплатно</b> <tg-emoji emoji-id=\"5424972470023104089\">👍</tg-emoji>\n\n"
    )

    # ==============================
    # 🔹 Список выполнивших условие
    # ==============================

    if invited_users:
        text += "\n<tg-emoji emoji-id=\"5366355709850045324\">👍</tg-emoji> <b>Выполнили условие:</b>\n"

        for (uid,) in invited_users:
            try:
                chat = await call.bot.get_chat(uid)
                name = chat.first_name or "Пользователь"
            except:
                name = "Пользователь"

            link = f"tg://user?id={uid}"

            text += f'• <a href="{link}">{name}</a>\n'
    else:
        text += "\n<tg-emoji emoji-id=\"5366355709850045324\">👍</tg-emoji> Пока никто не выполнил условие.\n"

    text += "\nОтправьте другу ваш код и получайте бонусы! <tg-emoji emoji-id=\"5276032951342088188\">👍</tg-emoji>"

    # ==============================
    # 🔹 Клавиатура
    # ==============================

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=" Активировать код друга",
                    callback_data="activate_ref",
                    style="success",
                    icon_custom_emoji_id="5377624166436445368"
                )
            ],
            [
                InlineKeyboardButton(
                    text=" Назад",
                    callback_data="choose_plan",
                    style="primary",
                    icon_custom_emoji_id="5352759161945867747"
                )
            ]
        ]
    )

    await call.message.edit_text(
        text,
        reply_markup=kb,
        parse_mode="HTML"
    )

    await call.answer()

@router.callback_query(F.data == "activate_ref")
async def ask_ref_code(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(ReferralState.waiting_ref_code)

    await call.message.answer("🔑 Введите код друга:")
    await call.answer()

@router.message(StateFilter(ReferralState.waiting_ref_code))
async def enter_ref_code(message: types.Message, state: FSMContext):

    user_id = message.from_user.id
    code = message.text.strip().upper()

    # Проверяем существует ли код
    cursor.execute(
        "SELECT user_id FROM referrals WHERE my_code = ?",
        (code,)
    )
    result = cursor.fetchone()

    if not result:
        return await message.answer("<tg-emoji emoji-id=\"5210952531676504517\">👍</tg-emoji> Неверный код")

    inviter_id = result[0]

    # Нельзя использовать свой код
    if inviter_id == user_id:
        return await message.answer("<tg-emoji emoji-id=\"5210952531676504517\">👍</tg-emoji> Нельзя использовать свой код")

    # Проверяем использовал ли уже
    cursor.execute(
        "SELECT used_code FROM referrals WHERE user_id = ?",
        (user_id,)
    )
    row = cursor.fetchone()

    if row and row[0]:
        return await message.answer("<tg-emoji emoji-id=\"5210952531676504517\">👍</tg-emoji> Вы уже использовали реферальный код")

    # Сохраняем связь
    cursor.execute("""
        UPDATE referrals
        SET used_code = ?, referred_by = ?
        WHERE user_id = ?
    """, (code, inviter_id, user_id))

    db.commit()

    # Очищаем состояние 🔥
    await state.clear()

    await message.answer("<tg-emoji emoji-id=\"5461151367559141950\"> Код успешно активирован!")

@router.message(Command("mycode"))
async def my_code(message: types.Message):
    user_id = message.from_user.id

    cursor.execute("SELECT my_code FROM referrals WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    if not row:
        return await message.answer("Код не найден.")

    await message.answer(f"Ваш реферальный код: <b>{row[0]}</b>", parse_mode="HTML")


@router.message(Command("name"))
async def edit_name_cmd(message: types.Message):
    user_id = message.from_user.id

    if user_id not in ADMINS:
        await message.reply("❌ У вас нет прав на редактирование.")
        return

    cursor.execute("SELECT DISTINCT anime FROM videos ORDER BY anime")
    animes = [row[0] for row in cursor.fetchall()]

    buttons = []
    row = []

    for i, anime in enumerate(animes, 1):
        row.append(InlineKeyboardButton(text=anime, callback_data=f"edit_name|{anime}"))
        if i % 2 == 0:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await message.answer(
        "Выберите аниме для редактирования английского названия:",
        reply_markup=kb
    )


async def add_subscription(user_id: int, plan_type: str, days: int):
    cursor.execute("SELECT expire_date FROM subscriptions WHERE user_id=?", (user_id,))
    row = cursor.fetchone()

    now = datetime.now()

    if row:
        old_expire = datetime.fromisoformat(row[0])

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
# выбор тарифа
# =========================

@router.callback_query(F.data == "choose_plan")
async def choose_plan(call: types.CallbackQuery):

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="7 дней — 39₽", callback_data="buy_7")],
            [InlineKeyboardButton(text="30 дней — 99₽", callback_data="buy_30")],
            [InlineKeyboardButton(text="180 дней — 499₽", callback_data="buy_180")],
            [InlineKeyboardButton(text="360 дней — 899₽", callback_data="buy_360")],
            [InlineKeyboardButton(text="Навсегда (только 100 чел.) — 1499₽", callback_data="buy_forever")],

            [InlineKeyboardButton(text=" Приведи друга", callback_data="ref_menu",style="success",icon_custom_emoji_id="5366355709850045324")],

            [InlineKeyboardButton(text=" Назад в меню", callback_data="back_menu",style="primary",icon_custom_emoji_id="5352759161945867747")]
        ]
    )

    try:
        await send_and_track(
            call.from_user.id,
            call.message.edit_text,
            "<tg-emoji emoji-id=\"5418115271267197333\">👍</tg-emoji> Покупка подписок:",
            parse_mode="HTML",
            reply_markup=kb
        )
    except:
        await send_and_track(
            call.from_user.id,
            call.message.answer,
            "<tg-emoji emoji-id=\"5418115271267197333\">👍</tg-emoji> Покупка подписок:",
            parse_mode="HTML",
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
            if rate["source"] == "USD" and rate["target"] == "RUB":
                usd_rub = Decimal(rate["rate"])

            if rate["source"] == crypto.upper() and rate["target"] == "USD":
                crypto_usd = Decimal(rate["rate"])

        if not usd_rub or not crypto_usd:
            print(f"Не найден курс для {crypto}")
            return "0.00000000"

        usd_amount = Decimal(rub_amount * (1 + CRYPTO_MARGIN)) / usd_rub
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
@router.message(Command("give"))
async def give_subscription_cmd(message: types.Message):

    if message.from_user.id not in ADMINS:
        return

    args = message.text.split(maxsplit=2)

    if len(args) != 3:
        await message.answer(
            "Использование:\n"
            "/give user_id дни\n"
            "/give user_id forever"
        )
        return

    try:
        target_id = int(args[1])
    except ValueError:
        await message.answer("❌ ID должен быть числом.")
        return

    if args[2].lower() == "forever":
        days = None
        period_key = "forever"
    else:
        try:
            days = int(args[2])
            if days <= 0:
                raise ValueError
        except ValueError:
            await message.answer("❌ Неверный формат дней.")
            return

        # учитываем рефералку только если подписка 30+
        if days >= 30:
            period_key = "30_days"
        else:
            period_key = None

    # 🔹 выдаём подписку
    give_subscription(target_id, days)

    # 🔥 вызываем реферальную систему
    if period_key:
        await process_referral_bonus(target_id, period_key)

    # ==============================
    # 📩 Уведомление пользователю
    # ==============================
    try:
        if days is None:
            await bot.send_message(
                target_id,
                "<tg-emoji emoji-id=\"5461151367559141950\">👍</tg-emoji> Вам выдана подписка НАВСЕГДА!",
                parse_mode="HTML"
            )
        else:
            await bot.send_message(
                target_id,
                f"<tg-emoji emoji-id=\"5461151367559141950\">👍</tg-emoji> Вам выдана подписка на {days} дней!",
                parse_mode="HTML"
            )
    except:
        pass

    await message.answer(f"✅ Подписка выдана пользователю {target_id}")

@router.message(Command("darling"))
async def darling_add_from_pending(message: types.Message):

    user_id = message.from_user.id

    if user_id not in ADMINS:
        await message.answer("❌ У тебя нет прав для этой команды.")
        return

    try:
        args = ""
        if message.text and len(message.text.split()) > 1:
            args = message.text.split(maxsplit=1)[1]

        anime, dub, season_raw, start_episode, num_episodes = [
            x.strip() for x in args.split(";")
        ]

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

    # ===== FOREVER покупка =====
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

    # ===== Если уже FOREVER — ничего не делаем =====
    if row and row[0] == "forever":
        return

    # ===== Обычная подписка =====
    if row:
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


@router.message(Command("remove_sub"))
async def remove_sub(message: types.Message):
    user_id = message.from_user.id

    if user_id not in ADMINS:
        await message.reply("❌ У тебя нет прав для этой команды")
        return

    if not message.reply_to_message:
        await message.reply("Ответь на сообщение пользователя командой /remove_sub")
        return

    target_id = message.reply_to_message.from_user.id

    cursor.execute("DELETE FROM subscriptions WHERE user_id=?", (target_id,))
    db.commit()

    await message.reply(f"✅ Подписка у пользователя {target_id} успешно удалена")


@router.message(Command("burmaldod"))
async def burmaldod_start(message: types.Message):

    if message.from_user.id not in ADMINS:
        return

    cursor.execute("SELECT DISTINCT anime FROM videos ORDER BY anime")
    animes = [row[0] for row in cursor.fetchall()]

    buttons = []

    for idx, anime in enumerate(animes):
        short_name = anime if len(anime) <= 40 else anime[:40] + "..."

        buttons.append([
            InlineKeyboardButton(
                text=short_name,
                callback_data=f"burmal_edit|{idx}"
            )
        ])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await message.answer("📋 Выберите аниме:", reply_markup=kb)


@router.callback_query(F.data.startswith("burmal_edit|"))
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


@router.message(lambda m: m.from_user.id in BURMALDOD_EDIT)
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


@router.message(F.video)
async def get_video(message: types.Message):

    if message.from_user.id not in ADMINS:
        return

    cursor.execute(
        "INSERT OR IGNORE INTO pending_videos (message_id, file_id, date) VALUES (?, ?, ?)",
        (message.message_id, message.video.file_id, str(message.date))
    )

    db.commit()

    await send_and_track(
        message.from_user.id,
        message.answer,
        "✅ Видео сохранено и готово для добавления в базу"
    )

@router.message(lambda m: m.text and URL_RE.search(m.text))
async def get_video_link(message: types.Message):

    if message.from_user.id not in ADMINS:
        return

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

    # Если это ссылка
    if isinstance(video_value, str) and URL_RE.match(video_value):

        kb = reply_markup or InlineKeyboardMarkup(inline_keyboard=[])

        return await bot.send_message(
            chat_id,
            caption or "🎬 Видео по ссылке:",
            reply_markup=kb,
            disable_web_page_preview=True
        )

    # Если file_id
    return await bot.send_video(
        chat_id,
        video=video_value,
        caption=caption,
        reply_markup=reply_markup
    )


def save_watch_progress(user_id, anime, dub, season, episode):
    cursor.execute("""
        INSERT INTO watch_history (user_id, anime, dub, season, episode)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id, anime, dub, season)
        DO UPDATE SET
            episode=excluded.episode,
            updated_at=CURRENT_TIMESTAMP
    """, (user_id, anime, dub, season, episode))

    db.commit()  # ✅ ВАЖНО: db, а не conn

async def get_anime_poster(anime_name):

    info = await get_anime_info(anime_name)

    if not info:
        return None

    title_en = info.get("title_en")

    if title_en:
        search_name = title_en
    else:
        search_name = info.get("title")

    search_name = re.sub(r"[:!\"'‘’]", "", search_name).strip()

    poster_url = await search_anilist_poster(search_name)

    return poster_url

async def send_video_by_params(call: types.CallbackQuery, anime, dub, season, ep):
    cursor.execute("SELECT file_id FROM videos WHERE anime=? AND dub=? AND season=? AND episode=?",
                   (anime, dub, season, ep))
    row = cursor.fetchone()
    if not row:
        await call.answer("❌ Видео не найдено", show_alert=True)
        return

    file_id = row[0]
    caption = f"<b>{anime}</b>\n<b><i>{dub}</i></b>\n<i>{season} сезон {ep} серия</i>"

    builder = InlineKeyboardBuilder()

    # Навигация
    nav_buttons = []
    cursor.execute("SELECT 1 FROM videos WHERE anime=? AND dub=? AND season=? AND episode=?", (anime, dub, season, ep - 1))
    if cursor.fetchone():
        nav_buttons.append(InlineKeyboardButton(text=f" {ep-1} серия",
                                                callback_data=f"ep|{make_cb_id(anime,dub,str(season),str(ep-1))}|0",
                                                style="primary"))
    cursor.execute("SELECT 1 FROM videos WHERE anime=? AND dub=? AND season=? AND episode=?", (anime, dub, season, ep + 1))
    if cursor.fetchone():
        nav_buttons.append(InlineKeyboardButton(text=f"{ep+1} серия ",
                                                callback_data=f"ep|{make_cb_id(anime,dub,str(season),str(ep+1))}|0",
                                                style="primary"))
    if nav_buttons:
        builder.row(*nav_buttons)

    # Кнопки назад
    builder.row(InlineKeyboardButton(text="Вернуться к сериям",
                                     callback_data=f"dub|{make_cb_id(anime, dub, str(season))}|0",
                                     style="primary"))
    builder.row(InlineKeyboardButton(text="Меню", callback_data="back_menu", style="success"))

    kb = builder.as_markup(row_width=2)

    if isinstance(file_id, str) and file_id.startswith("http"):
        await call.message.answer(caption, parse_mode="HTML", reply_markup=kb)
    else:
        await call.message.answer_video(file_id, caption=caption, parse_mode="HTML", reply_markup=kb)

    # Сохраняем прогресс
    save_watch_progress(call.from_user.id, anime, dub, season, ep)
    await call.answer()

@router.callback_query(F.data == "clear_history")
async def clear_history(call: types.CallbackQuery):
    user_id = call.from_user.id

    # Удаляем все записи истории пользователя
    cursor.execute("DELETE FROM watch_history WHERE user_id = ?", (user_id,))
    db.commit()

    # Формируем пустое меню истории
    buttons = [
        [InlineKeyboardButton(
            text=" Назад",
            callback_data="profile_menu",
            style="success",
            icon_custom_emoji_id="5352759161945867747"
        )]
    ]

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    try:
        # Редактируем текущее сообщение, показываем пустую историю
        await call.message.edit_text(
            "<b><tg-emoji emoji-id=\"5350513667144163474\">👍</tg-emoji> История просмотров пуста</b>",
            parse_mode="HTML",
            reply_markup=kb
        )
    except:
        pass

    await call.answer()

@router.callback_query(F.data.startswith("watch_history"))
async def watch_history(call: types.CallbackQuery):
    user_id = call.from_user.id

    parts = call.data.split("|")
    page = int(parts[1]) if len(parts) > 1 else 0

    limit = 10
    offset = page * limit

    cursor.execute("""
        SELECT anime, dub, season, episode
        FROM watch_history
        WHERE user_id = ?
        ORDER BY updated_at DESC
        LIMIT ? OFFSET ?
    """, (user_id, limit, offset))
    rows = cursor.fetchall()

    if not rows and page == 0:
        await call.answer("История пуста", show_alert=True)
        return

    cursor.execute("""
        SELECT COUNT(*)
        FROM watch_history
        WHERE user_id = ?
    """, (user_id,))
    total = cursor.fetchone()[0]

    buttons = []

    for anime, dub, season, episode in rows:
        # Название аниме с заглавной буквы
        anime_title = anime.title()

        text = f"{anime_title} — {episode} серия"

        # Формируем callback_data точно как для send_video
        ep_hash = make_cb_id(anime, dub, str(season), str(episode))
        cb = f"ep|{ep_hash}|0"  # page=0, чтобы всегда открывалась с начала

        buttons.append([InlineKeyboardButton(text=text, callback_data=cb)])

    # Пагинация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text=" ", callback_data=f"watch_history|{page - 1}", style="primary",icon_custom_emoji_id="5352759161945867747"))
    if offset + limit < total:
        nav_buttons.append(InlineKeyboardButton(text=" ", callback_data=f"watch_history|{page + 1}", style="primary",icon_custom_emoji_id="5355075407743826720"))
    if nav_buttons:
        buttons.append(nav_buttons)

    # Кнопка очистки
    buttons.append([InlineKeyboardButton(text=" Очистить историю", callback_data="clear_history", style="danger",icon_custom_emoji_id="5445267414562389170")])

    # Назад
    buttons.append([InlineKeyboardButton(text=" Назад", callback_data="profile_menu", style="success",icon_custom_emoji_id="5352759161945867747")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    try:
        await call.message.edit_text(
            f"<b><tg-emoji emoji-id=\"5350513667144163474\">👍</tg-emoji> История просмотров:</b>",
            parse_mode="HTML",
            reply_markup=kb
        )
    except:
        pass

    await call.answer()

@router.callback_query(F.data == "profile_menu")
async def profile_menu(call: types.CallbackQuery):
    user_id = call.from_user.id

    # Удаляем предыдущее сообщение
    try:
        await call.message.delete()
    except:
        pass

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=" История просмотров",
                    callback_data="watch_history|0",
                    style="danger",
                    icon_custom_emoji_id="5350513667144163474"
                )
            ],
            [
                InlineKeyboardButton(
                    text=" Статус подписки",
                    callback_data="sub_status",
                    style="primary",
                    icon_custom_emoji_id="5334544901428229844"
                )
            ],
            [
                InlineKeyboardButton(
                    text=" Назад",
                    callback_data="back_menu",
                    style="success",
                    icon_custom_emoji_id="5352759161945867747"
                )
            ]
        ]
    )

    # Отправляем новое меню
    await call.message.answer(
        "<b><tg-emoji emoji-id=\"5416015487525988007\">👍</tg-emoji> Личное меню:</b>",
        parse_mode="HTML",
        reply_markup=kb
    )

    await call.answer()

@router.callback_query(F.data == "back_menu")
async def back_to_menu(call: types.CallbackQuery):

    user_id = call.from_user.id

    SEARCH_USERS.discard(user_id)
    LAST_SEARCH_MSG.pop(user_id, None)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Все аниме",
                    switch_inline_query_current_chat="all",
                    icon_custom_emoji_id="5282843764451195532"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Поиск",
                    switch_inline_query_current_chat="",
                    style="danger",
                    icon_custom_emoji_id="5231012545799666522"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Купить подписку",
                    callback_data="choose_plan",
                    style="success",
                    icon_custom_emoji_id="5409048419211682843"
                )
            ],
            [
                InlineKeyboardButton(
                    text=" Личное",
                    callback_data="profile_menu",
                    style="primary",
                     icon_custom_emoji_id="5416015487525988007"
                )
            ]
        ]
    )

    try:
        await call.message.delete()
    except:
        pass

    await send_and_track(
        user_id,
        call.message.answer,
        "<tg-emoji emoji-id=\"5461117441612462242\">👍</tg-emoji> Главное меню:",
        parse_mode="HTML",  # 🔥 на будущее
        reply_markup=kb
    )

    await call.answer()

@router.callback_query(F.data == "register")
async def register_user(call: types.CallbackQuery):

    import time
    import random
    import string
    from datetime import datetime, timedelta

    user_id = call.from_user.id

    cursor.execute(
        "SELECT user_id FROM users WHERE user_id=?",
        (user_id,)
    )

    if cursor.fetchone():
        await call.answer("Ты уже зарегистрирован 😉", show_alert=True)
        return

    # ==============================
    # 🔹 Создаём пользователя
    # ==============================

    now_ts = int(time.time())
    trial_days = 7
    trial_until = now_ts + trial_days * 24 * 60 * 60

    cursor.execute(
        "INSERT INTO users (user_id, first_start, paid_until) VALUES (?, ?, ?)",
        (user_id, now_ts, trial_until)
    )

    db.commit()

    # ==============================
    # 🔹 Trial подписка
    # ==============================

    expire_date = (datetime.now() + timedelta(days=trial_days)).isoformat()

    cursor.execute(
        "INSERT INTO subscriptions (user_id, type, expire_date) VALUES (?, ?, ?)",
        (user_id, "trial", expire_date)
    )

    db.commit()

    # ==============================
    # 🔥 СОЗДАНИЕ РЕФЕРАЛЬНОГО КОДА
    # ==============================

    # генерируем уникальный код
    chars = string.ascii_uppercase + string.digits

    while True:
        my_code = ''.join(random.choices(chars, k=6))

        cursor.execute(
            "SELECT 1 FROM referrals WHERE my_code=?",
            (my_code,)
        )

        if not cursor.fetchone():
            break

    # сохраняем код пользователю
    cursor.execute("""
        INSERT INTO referrals (user_id, my_code)
        VALUES (?, ?)
    """, (user_id, my_code))

    db.commit()

    # ==============================

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Смотреть аниме в 4K",
                    callback_data="back_menu",
                    style="primary",
                    icon_custom_emoji_id="5348125953090403204"
                )
            ]
        ]
    )

    try:
        await call.message.delete()
    except:
        pass

    await send_and_track(
        user_id,
        call.message.answer,
        "<tg-emoji emoji-id=\"5206607081334906820\">👍</tg-emoji> Регистрация завершена!\n\n"
        "<tg-emoji emoji-id=\"5449800250032143374\"> Тебе доступна 1 неделя бесплатного просмотра.\n\n"
        "Приятного просмотра 🍿",
        reply_markup=kb
    )

    await call.answer()

# =========================
# Добавление видео (админ)
# =========================
@router.message(Command(commands=["add"]))
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
@router.callback_query(F.data == "search_menu")
async def search_menu(call: types.CallbackQuery):
    user_id = call.from_user.id
    SEARCH_USERS.add(user_id)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_menu")]
        ]
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


# =========================
# Проверка статуса подписки
# =========================
@router.message(Command("getid"))
async def get_file_id(message: types.Message):

    # 🔒 Проверка на админа
    if message.from_user.id not in ADMINS:
        await message.answer("❌ У вас нет доступа к этой команде.")
        return

    msg = message.reply_to_message or message

    if msg.photo:
        file_id = msg.photo[-1].file_id
        await message.answer(f"📸 PHOTO:\n<code>{file_id}</code>", parse_mode="HTML")
        return

    if msg.video:
        file_id = msg.video.file_id
        await message.answer(f"🎬 VIDEO:\n<code>{file_id}</code>", parse_mode="HTML")
        return

    if msg.document:
        file_id = msg.document.file_id
        await message.answer(f"📁 DOC:\n<code>{file_id}</code>", parse_mode="HTML")
        return

    await message.answer("❌ Ответь на сообщение с файлом или отправь его с /getid")

@router.callback_query(F.data == "sub_status")
async def sub_status(call: types.CallbackQuery):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    cursor.execute(
        "SELECT type, expire_date FROM subscriptions WHERE user_id=?",
        (user_id,)
    )
    row = cursor.fetchone()

    # Кнопка назад
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=" Назад",
                    callback_data="profile_menu",
                    style="primary",
                    icon_custom_emoji_id="5352759161945867747"
                )
            ]
        ]
    )

    status_text = None
    photo_id = None

    if row:
        sub_type, expire_date_str = row

        if expire_date_str == "forever":
            status_text = "<tg-emoji emoji-id=\"5206607081334906820\">👍</tg-emoji> Подписка навсегда активна"

        else:
            expire_date = datetime.fromisoformat(expire_date_str)

            if expire_date > datetime.now():
                status_text = (
                    f"<tg-emoji emoji-id=\"5206607081334906820\">👍</tg-emoji>"
                    f" Активная подписка\n"
                    f"<tg-emoji emoji-id=\"5413879192267805083\">👍</tg-emoji> "
                    f"До: {expire_date.strftime('%d.%m.%Y %H:%M')}"
                )
            else:
                status_text = "<tg-emoji emoji-id=\"5210952531676504517\">👍</tg-emoji> Подписка неактивна"

    else:
        status_text = "<tg-emoji emoji-id=\"5210952531676504517\">👍</tg-emoji> Подписка неактивна"

    # ==========================
    # 🎲 Новая логика фото
    # ==========================
    if "неактивна" in status_text:
        first_photo = "AgACAgIAAxkBAAJXMWm6kz5G0tr82X6n8Aq7DP_uAz-bAAKhFmsbPLjYSU4BdI8ZXkOIAQADAgADeAADOgQ"
        second_photo = "AgACAgIAAxkBAAJXUmm6lwgiNVTEUwhtCGjgctgo6uA0AALhFmsbPLjYSXuuc90GKBBDAQADAgADeAADOgQ"

        if random.random() < 0.95:
            photo_id = first_photo
        else:
            photo_id = second_photo

    # Удаляем старое сообщение
    try:
        await call.message.delete()
    except:
        pass

    # ==========================
    # Отправка
    # ==========================
    if photo_id:
        await send_and_track(
            user_id,
            bot.send_photo,
            chat_id,
            photo=photo_id,
            caption=status_text,
            parse_mode="HTML",
            reply_markup=kb
        )
    else:
        await send_and_track(
            user_id,
            bot.send_message,
            chat_id,
            status_text,
            parse_mode="HTML",
            reply_markup=kb
        )

    await call.answer()
# ===== Выбор тарифа =====
@router.callback_query(F.data.startswith("buy_") & (F.data != "buy_sub"))
async def process_tariff(call: types.CallbackQuery):
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

    text = (
        f"<tg-emoji emoji-id=\"5418115271267197333\">👍</tg-emoji> Вы выбрали подписку: <b>{period_key.replace('_', ' ')}</b>\n\n"
        f"<tg-emoji emoji-id=\"5231449120635370684\">👍</tg-emoji> Цена: <b>{rub_amount}₽</b>\n\n"
        "Выберите способ оплаты:"
    )

    builder = InlineKeyboardBuilder()

    crypto_callback = f"pay_crypto|{period_key}"

    builder.row(
        InlineKeyboardButton(
            text=" Оплатить криптовалютой",
            callback_data=crypto_callback,
            style="danger",
            icon_custom_emoji_id="5231005931550030290"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text=" Оплатить рублями",
            callback_data=f"pay_rub|{period_key}",
            style="success",
            icon_custom_emoji_id="5231449120635370684"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text=" Назад в меню",
            callback_data="back_menu",
            style="primary",
            icon_custom_emoji_id="5352759161945867747"
        )
    )

    kb = builder.as_markup()

    import logging
    logging.info(f"[process_tariff] Пользователь {user_id} выбрал тариф {period_key}")
    logging.info(f"[process_tariff] Callback_data кнопки 'Оплатить криптовалютой': {crypto_callback}")

    try:
        await send_and_track(user_id, call.message.edit_text, text, parse_mode="HTML", reply_markup=kb)
    except:
        await send_and_track(user_id, call.message.answer, text, parse_mode="HTML", reply_markup=kb)

    await call.answer()

# ===== Рублевая оплата =====
@router.callback_query(F.data.startswith("pay_rub|"))
async def pay_rub_handler(call: types.CallbackQuery):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    try:
        _, period_key = call.data.split("|")
    except ValueError:
        await call.answer("Ошибка тарифа", show_alert=True)
        return

    rub_amount = RUB_PRICES.get(period_key, 0)

    # Сохраняем платеж
    PENDING_PAYMENTS[user_id] = {
        "period_key": period_key,
        "invoice_id": None
    }

    await delete_bot_messages(user_id, chat_id)

    text = (
        f"<tg-emoji emoji-id=\"5397782960512444700\">👍</tg-emoji> Переведите <b>{rub_amount}₽</b> на номер:\n"
        "<b>79133295900</b>\nПочта Банк / Ozon Банк\n\n"
        "После оплаты нажмите кнопку ниже для подтверждения."
    )

    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text=" Подтвердить оплату",
            callback_data="confirm_payment",
            style="success",
            icon_custom_emoji_id="5206607081334906820"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text=" Назад в меню",
            callback_data="back_menu",
            style="primary",
            icon_custom_emoji_id="5352759161945867747"
        )
    )

    kb = builder.as_markup()

    await send_and_track(user_id, call.message.answer, text, parse_mode="HTML", reply_markup=kb)

    await call.answer()

# ===== Криптооплата =====
async def create_crypto_invoice_async(user_id, rub_amount, period_key):
    url = "https://pay.crypt.bot/api/createInvoice"
    headers = {"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN, "Content-Type": "application/json"}
    payload = {"currency_type":"fiat","fiat":"RUB","amount":rub_amount,
               "description":f"Subscription:{period_key}","payload":f"{user_id}|{period_key}"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                result = await resp.json()
                if result.get("ok"):
                    invoice = result["result"]
                    invoice_id = invoice["invoice_id"]
                    pay_url = invoice["pay_url"]
                    # Сохраняем в БД
                    cursor.execute(
                        "INSERT OR REPLACE INTO pending_payments (user_id, period_key, invoice_id, pay_url, created_at) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (user_id, period_key, invoice_id, pay_url, datetime.now().isoformat())
                    )
                    db.commit()
                    return pay_url
                return None
    except Exception as e:
        logging.error(f"[CryptoInvoice] Ошибка: {e}")
        return None


@router.callback_query(F.data.startswith("pay_crypto|"))
async def pay_crypto_handler(call: types.CallbackQuery):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    logging.info(f"[pay_crypto_handler] Нажата кнопка пользователем {user_id}, callback_data={call.data}")

    # Получаем тариф
    try:
        _, period_key = call.data.split("|")
        logging.info(f"[pay_crypto_handler] Выбран тариф: {period_key}")
    except ValueError:
        await call.answer("Ошибка тарифа", show_alert=True)
        return

    rub_amount = RUB_PRICES.get(period_key, 0)
    if rub_amount == 0:
        await call.answer("Ошибка тарифа", show_alert=True)
        return

    # ✅ Сохраняем платеж (как в pay_rub_handler)
    PENDING_PAYMENTS[user_id] = {
        "period_key": period_key,
        "invoice_id": None
    }

    # Удаляем старое сообщение
    try:
        await delete_bot_messages(user_id, chat_id)
        logging.info(f"[pay_crypto_handler] Старое сообщение удалено для пользователя {user_id}")
    except Exception as e:
        logging.error(f"[pay_crypto_handler] Ошибка при удалении старого сообщения: {e}")

    # Создаём invoice
    invoice_url = await create_crypto_invoice_async(user_id, rub_amount, period_key)
    if not invoice_url:
        await call.answer("Ошибка создания счета", show_alert=True)
        return

    text = (
        f"<tg-emoji emoji-id=\"5350452584119279096\">👍</tg-emoji> <b>Оплата подписки</b>\n\n"
        f"Сумма: <b>{rub_amount}₽</b>\n\n"
        "После нажатия кнопки вы перейдёте в CryptoBot, "
        "где сможете выбрать любую криптовалюту для оплаты.\n\n"
        "Если вы переводите криптовалюту со стороннего кошелька или подписка не пришла автоматически, "
        "нажмите кнопку <tg-emoji emoji-id=\"5206607081334906820\">👍</tg-emoji> <b>Подтвердить оплату</b>.\n\n"
        "После успешной оплаты подписка активируется автоматически."
    )

    # Клавиатура
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text=" Перейти к оплате",
            url=invoice_url,
            icon_custom_emoji_id="5449683594425410231"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text=" Подтвердить оплату",
            callback_data="confirm_payment",
            style="success",
            icon_custom_emoji_id="5206607081334906820"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text=" Назад в меню",
            callback_data="back_menu",
            style="primary",
            icon_custom_emoji_id="5352759161945867747"
        )
    )

    kb = builder.as_markup()

    # Отправляем сообщение
    try:
        await call.message.answer(
            text,
            parse_mode="HTML",
            reply_markup=kb
        )
        logging.info(f"[pay_crypto_handler] Сообщение с кнопками отправлено пользователю {user_id}")
    except Exception as e:
        logging.error(f"[pay_crypto_handler] Ошибка при отправке сообщения: {e}")

    await call.answer()

# ===== Вебхук Crypto.bot с минимальной защитой =====
async def handle_crypto_webhook(request):
    try:
        data = await request.json()
        logging.info(f"[CRYPTO_WEBHOOK] Получены данные: {data}")

        # Проверяем тип события
        if data.get("update_type") != "invoice_paid":
            logging.info("[CRYPTO_WEBHOOK] Игнорируем update_type")
            return web.Response(text="Ignored")

        payload = data.get("payload", {})

        invoice_id = payload.get("invoice_id")
        payload_data = payload.get("payload")  # user_id|period_key

        if not invoice_id or not payload_data:
            logging.error("[CRYPTO_WEBHOOK] Нет invoice_id или payload")
            return web.Response(text="Invalid data", status=400)

        # Проверка на уже обработанный invoice
        cursor.execute(
            "SELECT 1 FROM processed_invoices WHERE invoice_id=?",
            (invoice_id,)
        )
        if cursor.fetchone():
            logging.warning(f"[CRYPTO_WEBHOOK] Invoice {invoice_id} уже обработан")
            return web.Response(text="Already processed")

        # Разбираем payload
        try:
            user_id_str, period_key = payload_data.split("|")
            user_id = int(user_id_str)
        except Exception as e:
            logging.error(f"[CRYPTO_WEBHOOK] Ошибка payload: {e}")
            return web.Response(text="Invalid payload", status=400)

        # Проверяем совпадение invoice с pending_payments
        cursor.execute(
            "SELECT invoice_id FROM pending_payments WHERE user_id=?",
            (user_id,)
        )
        row = cursor.fetchone()

        if not row or row[0] != invoice_id:
            logging.error(f"[CRYPTO_WEBHOOK] Invoice mismatch для user {user_id}")
            return web.Response(text="Invoice mismatch", status=400)

        # Добавляем в processed_invoices
        cursor.execute(
            """
            INSERT INTO processed_invoices (invoice_id, user_id, period_key, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (invoice_id, user_id, period_key, datetime.now().isoformat())
        )

        # Удаляем из pending
        cursor.execute(
            "DELETE FROM pending_payments WHERE user_id=?",
            (user_id,)
        )

        db.commit()

        logging.info(f"[CRYPTO_WEBHOOK] Оплата подтверждена user={user_id}, тариф={period_key}")

        # Активируем подписку
        days = None if period_key == "forever" else int(period_key.split("_")[0])

        give_subscription(user_id, days)
        process_referral_bonus(user_id, tariffs_map[call.data])
        # Сообщение пользователю
        if days is None:
            await bot.send_message(
                user_id,
                "<tg-emoji emoji-id=\"5461151367559141950\">👍</tg-emoji> Ваша подписка НАВСЕГДА активирована!"
            )
        else:
            await bot.send_message(
                user_id,
                f"<tg-emoji emoji-id=\"5461151367559141950\">👍</tg-emoji> Ваша подписка на {days} дней активирована!"
            )

        # Уведомление админу
        try:
            await bot.send_message(
                ADMIN_ID,
                f"💰 Новая оплата\n\n"
                f"👤 User: {user_id}\n"
                f"📦 Тариф: {period_key}\n"
                f"🧾 Invoice: {invoice_id}"
            )
        except Exception as e:
            logging.error(f"[CRYPTO_WEBHOOK] Ошибка отправки админу: {e}")

        return web.Response(text="OK")

    except Exception as e:
        logging.error(f"[CRYPTO_WEBHOOK] Критическая ошибка: {e}")
        return web.Response(text="Server error", status=500)

async def test(request):
    return web.Response(text="Server OK")

# ===== Регистрация вебхука =====
app = web.Application()
WEBHOOK_URL = "/webhook"
app.router.add_post(WEBHOOK_URL, handle_crypto_webhook)

@router.callback_query(F.data == "confirm_payment")
async def confirm_payment(call: types.CallbackQuery):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    await delete_bot_messages(user_id, chat_id)

    WAITING_CHECK.add(user_id)

    await send_and_track(
        user_id,
        call.message.answer,
        "<tg-emoji emoji-id=\"5305265301917549162\">👍</tg-emoji> Отправьте скрин или файл чека перевода",
        parse_mode="HTML"
    )

    await call.answer()


# ===== Получение чека =====
@router.message(F.content_type.in_([ContentType.PHOTO, ContentType.DOCUMENT]))
async def handle_check(message: types.Message):
    user_id = message.from_user.id

    if user_id not in WAITING_CHECK:
        return

    WAITING_CHECK.remove(user_id)
    payment_data = PENDING_PAYMENTS.get(user_id)
    period = payment_data["period_key"] if payment_data else "не указан"

    # Сообщение пользователю
    text_user = (
        "<tg-emoji emoji-id=\"5386367538735104399\">👍</tg-emoji> Ожидайте выдачи подписки.\n\n"
        "<tg-emoji emoji-id=\"5440621591387980068\">👍</tg-emoji> По будням: 04:00–21:00 МСК\n"
        "<tg-emoji emoji-id=\"5440621591387980068\">👍</tg-emoji> По выходным: 10:00–01:00 МСК\n\n"
        "Выдача обычно от нескольких минут до 3 часов\n"
        "(иногда дольше)"
    )

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=" Назад в меню",callback_data="back_menu",style="primary",icon_custom_emoji_id="5352759161945867747"))
    kb = builder.as_markup()

    await send_and_track(
        user_id,
        message.answer,
        text_user,
        parse_mode="HTML",
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
        elif message.document:
            await bot.send_document(
                admin_id,
                message.document.file_id,
                caption=admin_text
            )


@router.message(F.content_type == ContentType.TEXT)
async def live_search(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    query = message.text.lower().strip()

    if not query:
        return

    await delete_bot_messages(user_id, chat_id)

    # Поиск аниме по запросу
    cursor.execute(
        "SELECT DISTINCT anime FROM videos WHERE LOWER(anime) LIKE ? LIMIT 1",
        (f"%{query}%",)
    )
    found_animes = [row[0] for row in cursor.fetchall()]

    if not found_animes:
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_menu"))
        kb = builder.as_markup()
        await send_and_track(
            user_id,
            message.answer,
            "❌ Ничего не найдено",
            reply_markup=kb
        )
        return

    # Получаем все аниме для индекса
    cursor.execute("SELECT DISTINCT anime FROM videos ORDER BY anime")
    all_animes = [row[0] for row in cursor.fetchall()]

    for anime in found_animes:
        try:
            anime_idx = all_animes.index(anime)
        except ValueError:
            continue

        # Создаём клавиатуру — каждая кнопка в отдельном ряду
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text=" Открыть", callback_data=f"anime_index|{anime_idx}",style="danger",icon_custom_emoji_id="5348125953090403204"))
        builder.row(InlineKeyboardButton(text=" Назад в меню", callback_data="back_menu",style="primary",icon_custom_emoji_id="5352759161945867747"))
        kb = builder.as_markup()

        # Получаем информацию и постер
        info, poster_url = None, None
        try:
            info = await get_anime_info(anime)
        except:
            info = None

        if info:
            cursor.execute(
                "SELECT english_name FROM videos WHERE anime=? LIMIT 1", (anime,)
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

        # Формируем текст
        text = anime.title()
        if info:
            text = (
                f"<b>{info.get('title', anime)}</b>\n"
                f"<tg-emoji emoji-id=\"5438496463044752972\">👍</tg-emoji> Рейтинг: {info.get('score', '—')}\n"
                f"<tg-emoji emoji-id=\"5413879192267805083\">👍</tg-emoji> Год: {info.get('year', '—')}\n"
                f"<tg-emoji emoji-id=\"5350658016700013471\">👍</tg-emoji> Жанры: {info.get('genres', '—')}"
            )

        # Отправка пользователю
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


def fix_shiki_poster(url: str | None) -> str | None:
    """Фиксируем URL постера с Shikimori, получаем оригинальное качество"""
    if not url:
        return None
    if url.startswith("/"):
        url = "https://shikimori.one" + url
    url = url.replace("/preview/", "/original/")
    url = url.replace("/poster/", "/original/")
    return url


async def load_anime_info(anime_name: str):
    """Загрузка информации о аниме из базы и внешних источников"""
    # Проверка базы
    cursor.execute(
        "SELECT poster, score, genres, year FROM anime_info WHERE anime=?",
        (anime_name,)
    )
    row = cursor.fetchone()

    # Получаем английское название из videos
    cursor.execute(
        "SELECT english_name FROM videos WHERE anime=? LIMIT 1",
        (anime_name,)
    )
    r = cursor.fetchone()
    english_name = r[0] if r and r[0] else anime_name

    # ---------- ЕСЛИ АНИМЕ УЖЕ В БАЗЕ ----------
    if row:
        poster_url, score, genres, year = row

        if not poster_url:
            info = await get_anime_info(anime_name)
            if not info:
                return anime_name, None, score, genres, year

            poster_url = await search_anilist_poster(english_name)
            if not poster_url:
                poster_url = fix_shiki_poster(info.get("poster"))

            if poster_url:
                cursor.execute(
                    "UPDATE anime_info SET poster=? WHERE anime=?",
                    (poster_url, anime_name)
                )
                db.commit()

        return anime_name, poster_url, score, genres, year

    # ---------- ЕСЛИ АНИМЕ НЕТ В БАЗЕ ----------
    info = await get_anime_info(anime_name)
    if not info:
        return None

    poster_url = await search_anilist_poster(english_name)
    if not poster_url:
        poster_url = fix_shiki_poster(info.get("poster"))

    genres = ", ".join(info.get("genres", [])) if isinstance(info.get("genres"), list) else info.get("genres", "—")
    score = str(info.get("score", "—"))
    year = str(info.get("year", "—"))

    # Сохраняем в базе
    cursor.execute(
        "INSERT OR IGNORE INTO anime_info (anime, poster, score, genres, year) VALUES (?, ?, ?, ?, ?)",
        (anime_name, poster_url, score, genres, year)
    )
    db.commit()

    return anime_name, poster_url, score, genres, year

@router.inline_query(F.query)
async def inline_search(query: types.InlineQuery):
    search_text = query.query.strip().lower()
    if not search_text:
        return

    offset = int(query.offset) if query.offset else 0

    if search_text == "all":
        cursor.execute(
            "SELECT DISTINCT anime FROM videos ORDER BY anime LIMIT ? OFFSET ?",
            (PAGE_SIZE, offset)
        )
    else:
        cursor.execute(
            "SELECT DISTINCT anime FROM videos WHERE LOWER(anime) LIKE ? ORDER BY anime LIMIT ? OFFSET ?",
            (f"%{search_text}%", PAGE_SIZE, offset)
        )

    rows = cursor.fetchall()
    if not rows:
        await query.answer([], cache_time=1)
        return

    results = []
    for (anime_name,) in rows:
        data = await load_anime_info(anime_name)
        if not data:
            continue

        anime_name, poster_url, score, genres, year = data

        # Преобразуем название аниме в Title Case
        anime_name = string.capwords(anime_name)

        description = f"⭐ {score} | 🎭 {genres} | 📅 {year}"

        results.append(
            InlineQueryResultArticle(
                id=str(uuid4()),
                title=anime_name,
                description=description,
                thumb_url=poster_url,
                input_message_content=InputTextMessageContent(
                    message_text=anime_name
                )
            )
        )

    next_offset = str(offset + PAGE_SIZE) if len(rows) == PAGE_SIZE else ""

    await query.answer(
        results=results,
        cache_time=1,
        is_personal=True,
        next_offset=next_offset
    )

# ===== Выбор диапазона серий =====
@router.callback_query(F.data.startswith("ranges|"))
async def show_ranges(call: types.CallbackQuery):
    user_id = call.from_user.id
    _, dub_hash = call.data.split("|")

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

    cursor.execute(
        "SELECT episode FROM videos WHERE anime=? AND dub=? AND season=? ORDER BY episode",
        (anime, dub, season)
    )
    episodes = [row[0] for row in cursor.fetchall()]
    if not episodes:
        await call.answer("❌ Серий нет", show_alert=True)
        return

    EPISODES_PER_BLOCK = 50
    total_blocks = (len(episodes) + EPISODES_PER_BLOCK - 1) // EPISODES_PER_BLOCK

    builder = InlineKeyboardBuilder()

    for block in range(total_blocks):
        start_ep = block * EPISODES_PER_BLOCK + 1
        end_ep = min((block + 1) * EPISODES_PER_BLOCK, len(episodes))

        builder.add(
            InlineKeyboardButton(
                text=f"{start_ep}–{end_ep}",
                callback_data=f"dub|{dub_hash}|{block}"
            )
        )

# Делаем по 3 кнопки в строке
    builder.adjust(3)

# Кнопка назад отдельной строкой
    builder.row(
        InlineKeyboardButton(
            text=" К сериям",
            callback_data=f"dub|{dub_hash}|0",
            style="primary",
            icon_custom_emoji_id="5352759161945867747"
        )
    )

    kb = builder.as_markup()

    try:
        await call.message.delete()
    except:
        pass

    await send_and_track(
        user_id,
        call.message.answer,
        "<tg-emoji emoji-id=\"5357315181649076022\">👍</tg-emoji> Выберите диапазон:",
        parse_mode="HTML",
        reply_markup=kb
    )

    await call.answer()



# =========================
# Перехватываем выбор из inline и вызываем твой callback
# =========================
@router.message(lambda message: True)
async def inline_trigger_to_search(message: types.Message):
    """
    Перехватываем любое текстовое сообщение и вызываем live_search.
    Игнорируем команды и сообщения без текста.
    """
    if message.text and not message.text.startswith("/"):
        await live_search(message)

# =========================
# Твой существующий callback без изменений
# =========================
@router.callback_query(lambda c: c.data.startswith("anime_index|"))
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
    description = clean_shikimori_description(description)
    first_paragraph = description.split("\n\n")[0].strip()

    MAX_LEN = 800
    if len(first_paragraph) > MAX_LEN:
        cut_text = first_paragraph[:MAX_LEN]
        match = re.search(r'[.!?](?!.*[.!?])', cut_text)
        if match:
            first_paragraph = cut_text[:match.end()]
        else:
            first_paragraph = cut_text.rstrip() + "…"

    text = (
        f"<b>{info.get('title', anime)}</b>\n"
        f"<tg-emoji emoji-id=\"5438496463044752972\">👍</tg-emoji> Рейтинг: <b>{info.get('score', 'N/A')}</b>\n"
        f"<tg-emoji emoji-id=\"5350658016700013471\">👍</tg-emoji> Жанры: {info.get('genres', 'Неизвестно')}\n"
        f"<tg-emoji emoji-id=\"5413879192267805083\">👍</tg-emoji> Год: {info.get('year', 'N/A')}\n"
        f"<tg-emoji emoji-id=\"5253742260054409879\">👍</tg-emoji> {first_paragraph}"
    )

    cursor.execute("SELECT DISTINCT season FROM videos WHERE anime=? ORDER BY season", (anime,))
    seasons = [row[0] for row in cursor.fetchall()]

    # --- Клавиатура через InlineKeyboardBuilder ---
    # --- Клавиатура через InlineKeyboardBuilder ---
    builder = InlineKeyboardBuilder()

# Добавляем кнопки сезонов по 2 в ряд
    season_buttons = []
    for season in seasons:
        season_str = str(season).lower()
        button_text = "🎬 Фильм" if season_str in ["film", "фильм", "movie"] else f"Сезон {season}"
        cb_id = make_cb_id(anime, str(season))
        season_buttons.append(InlineKeyboardButton(text=button_text, callback_data=f"season|{cb_id}",style="primary"))

# раскладываем кнопки рядами по 2
    for i in range(0, len(season_buttons), 2):
        builder.row(*season_buttons[i:i+2])

# Отдельный ряд для кнопки "Меню"
    builder.row(InlineKeyboardButton(text=" Меню", callback_data="back_menu",style="success",icon_custom_emoji_id="5312486108309757006"))

# Получаем готовый InlineKeyboardMarkup
    kb = builder.as_markup()

    try:
        await call.message.delete()
    except:
        pass

    # Отправка сообщения с постером или без
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
@router.callback_query(lambda c: c.data.startswith("back_anime"))
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

    builder = InlineKeyboardBuilder()

    # --- Кнопки аниме по одной ---
    for i, anime in enumerate(current_animes, start=start):
        title = anime.title()
        if len(title) > MAX_TITLE_LEN:
            title = title[:MAX_TITLE_LEN - 3] + "..."
        builder.row(InlineKeyboardButton(text=title, callback_data=f"anime_index|{i}"))

    # --- Навигационные кнопки на одной строке ---
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"back_anime|{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="➡️ Вперёд", callback_data=f"back_anime|{page + 1}"))
    if nav_buttons:
        builder.row(*nav_buttons)

    # --- Кнопка выхода в меню ---
    builder.row(InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_menu"))

    kb = builder.as_markup(row_width=1)

    try:
        await call.message.delete()
    except:
        pass

    await send_and_track(user_id, call.message.answer, "🎌 Выбери аниме:", reply_markup=kb)
    await call.answer()

# ===== Выбор сезона после аниме =====
@router.callback_query(lambda c: c.data.startswith("season|") or c.data.startswith("back_season|"))
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

    cursor.execute(
        "SELECT DISTINCT dub FROM videos WHERE anime=? AND season=? ORDER BY dub",
        (anime_name, season)
    )
    dubs = [row[0] for row in cursor.fetchall()]

    if not dubs:
        await call.answer("❌ Озвучек нет", show_alert=True)
        return

    builder = InlineKeyboardBuilder()

    # --- Кнопки озвучек по одной ---
    for dub in dubs:
        cb_id = make_cb_id(anime_name, dub, str(season))
        builder.row(InlineKeyboardButton(text=f" {dub}", callback_data=f"dub|{cb_id}", style="primary"))

    # Получаем индекс аниме для кнопки "К аниме"
    cursor.execute("SELECT DISTINCT anime FROM videos ORDER BY anime")
    all_animes = [row[0] for row in cursor.fetchall()]

    try:
        anime_idx = all_animes.index(anime_name)
    except ValueError:
        await call.answer("❌ Ошибка данных", show_alert=True)
        return

    # --- Кнопки возврата на отдельных строках ---
    builder.row(InlineKeyboardButton(text=" К аниме", callback_data=f"anime_index|{anime_idx}",style="danger",icon_custom_emoji_id="5352759161945867747"))
    builder.row(InlineKeyboardButton(text=" Меню", callback_data="back_menu",style="success",icon_custom_emoji_id="5312486108309757006"))

    kb = builder.as_markup(row_width=1)

    try:
        await call.message.delete()
    except:
        pass

    await send_and_track(user_id, call.message.answer, "<tg-emoji emoji-id=\"5388632425314140043\">👍</tg-emoji> Выбор озвучки:",parse_mode="HTML", reply_markup=kb)
    await call.answer()

# =========================
# Выбор серии после озвучки
# =========================
@router.callback_query(lambda c: c.data.startswith("dub|"))
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

    # Получаем серии
    cursor.execute(
        "SELECT episode, file_id FROM videos WHERE anime=? AND dub=? AND season=? ORDER BY episode",
        (anime, dub, season)
    )
    episodes = [(r[0], r[1]) for r in cursor.fetchall()]

    if not episodes:
        await call.answer("❌ Серий нет", show_alert=True)
        return

    EPISODES_PER_PAGE = 50
    EPISODES_PER_ROW = 5

    start = page * EPISODES_PER_PAGE
    end = start + EPISODES_PER_PAGE
    page_episodes = episodes[start:end]

    builder = InlineKeyboardBuilder()

    # --- Кнопки серий ---
    for i in range(0, len(page_episodes), EPISODES_PER_ROW):
        row_buttons = [
            InlineKeyboardButton(
                text=str(ep),
                callback_data=f"ep|{make_cb_id(anime, dub, str(season), str(ep))}|{page}"
            )
            for ep, _ in page_episodes[i:i + EPISODES_PER_ROW]
        ]
        builder.row(*row_buttons)

    # --- Навигация вперед/назад на одной строке ---
    nav_buttons = []
    if start > 0:
        nav_buttons.append(InlineKeyboardButton(text=" ", callback_data=f"dub|{dub_hash}|{page-1}",style="primary",icon_custom_emoji_id="5352759161945867747"))
    if end < len(episodes):
        nav_buttons.append(InlineKeyboardButton(text=" ", callback_data=f"dub|{dub_hash}|{page+1}",style="primary",icon_custom_emoji_id="5355075407743826720"))
    if nav_buttons:
        builder.row(*nav_buttons)

    # --- Нижние кнопки по одной ---
    builder.row(InlineKeyboardButton(text=" Быстрый переход", callback_data=f"ranges|{dub_hash}",style="primary",icon_custom_emoji_id="5357315181649076022"))
    builder.row(InlineKeyboardButton(text=" К озвучкам", callback_data=f"season|{make_cb_id(anime, str(season))}",style="danger",icon_custom_emoji_id="5388632425314140043"))
    builder.row(InlineKeyboardButton(text=" Меню", callback_data="back_menu",style="success",icon_custom_emoji_id="5312486108309757006"))

    kb = builder.as_markup(row_width=EPISODES_PER_ROW)

    try:
        await call.message.delete()
    except:
        pass

    await send_and_track(user_id, call.message.answer, "<tg-emoji emoji-id=\"5368653135101310687\">👍</tg-emoji> Выбор серии:",parse_mode="HTML", reply_markup=kb)
    await call.answer()

# ===== Отправка видео серии =====
@router.callback_query(lambda c: c.data.startswith("ep|"))
async def send_video(call: types.CallbackQuery):
    user_id = call.from_user.id

    try:
        await call.message.delete()
    except:
        pass

    # Проверка подписки
    cursor.execute("SELECT expire_date FROM subscriptions WHERE user_id=?", (user_id,))
    row = cursor.fetchone()

    has_sub = False

    if row:
        expire_date_str = row[0]

        if expire_date_str == "forever":
            has_sub = True
        else:
            try:
                expire_date = datetime.fromisoformat(expire_date_str)
                if expire_date > datetime.now():
                    has_sub = True
            except:
                has_sub = False  # на случай битых данных

    if not has_sub:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text=" Купить подписку",
                callback_data="choose_plan",
                style="success",
                icon_custom_emoji_id="5418115271267197333"
            ),
            InlineKeyboardButton(
                text=" Назад в меню",
                callback_data="back_menu",
                style="primary",
                icon_custom_emoji_id="5352759161945867747"
            )
        )

        kb = builder.as_markup()

        await send_and_track(
            user_id,
            call.message.answer,
            "<tg-emoji emoji-id=\"5260293700088511294\">👍</tg-emoji> Для просмотра серии нужна подписка",
            parse_mode="HTML",
            reply_markup=kb
        )

        await call.answer(
            "<tg-emoji emoji-id=\"5260293700088511294\">👍</tg-emoji> Подписка закончилась",
            show_alert=True
        )
        return

    _, ep_hash, page = call.data.split("|")
    page = int(page)

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
      
    # 🔥 СОХРАНЯЕМ ПРОГРЕСС
    save_watch_progress(user_id, anime, dub, season, ep)

    caption = f"<b>{anime.title()}</b>\n<b><i>{dub}</i></b>\n<i>{season} сезон {ep} серия</i>"

    # Навигация вперед/назад на одной строке
    builder = InlineKeyboardBuilder()
    nav_buttons = []

    cursor.execute("SELECT 1 FROM videos WHERE anime=? AND dub=? AND season=? AND episode=?", (anime, dub, season, ep - 1))
    prev_exists = cursor.fetchone()
    cursor.execute("SELECT 1 FROM videos WHERE anime=? AND dub=? AND season=? AND episode=?", (anime, dub, season, ep + 1))
    next_exists = cursor.fetchone()

    if prev_exists:
        nav_buttons.append(
            InlineKeyboardButton(
                text=f" {ep-1} серия",
                callback_data=f"ep|{make_cb_id(anime, dub, str(season), str(ep - 1))}|{page}",
                style="primary"
            )
        )

    if next_exists:
        nav_buttons.append(
            InlineKeyboardButton(
                text=f"{ep+1} серия ",
                callback_data=f"ep|{make_cb_id(anime, dub, str(season), str(ep + 1))}|{page}",
                style="primary"
            )
        )

    if nav_buttons:
        builder.row(*nav_buttons)

    # Кнопка скачивания (отдельная строка)
    if isinstance(file_id, str) and file_id.startswith("http"):
        builder.row(InlineKeyboardButton(text=" Скачать серию", url=file_id,style="danger",icon_custom_emoji_id="5447410659077661506"))

    # Кнопки назад по отдельным строкам
    builder.row(InlineKeyboardButton(text=" Вернуться к сериям",callback_data=f"dub|{make_cb_id(anime, dub, str(season))}|{page}",style="primary",icon_custom_emoji_id="5352759161945867747"))
    builder.row(InlineKeyboardButton(text=" К озвучкам", callback_data=f"season|{make_cb_id(anime, str(season))}",style="danger",icon_custom_emoji_id="5388632425314140043"))
    builder.row(InlineKeyboardButton(text=" Меню", callback_data="back_menu",style="success",icon_custom_emoji_id="5312486108309757006"))

    kb = builder.as_markup(row_width=2)

    # Отправка
    if isinstance(file_id, str) and file_id.startswith("http"):
        await send_and_track(user_id, call.message.answer, caption, parse_mode="HTML", reply_markup=kb, protect_content=True)
    else:
        await send_and_track(user_id, call.message.answer_video, video=file_id, caption=caption, parse_mode="HTML", reply_markup=kb, protect_content=True)

    await call.answer()

async def on_startup(dp: Dispatcher):
    print("Бот стартовал!")

async def start_webhook():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 3000)
    await site.start()
    print("Webhook сервер запущен на порту 3000")

async def cleanup_old_records():
    while True:
        try:
            print("[Cleanup] Начинаем очистку старых invoice...")
            cursor.execute(
                "DELETE FROM processed_invoices WHERE created_at < datetime('now', '-7 days')"
            )
            db.commit()
            print("[Cleanup] Очистка завершена.")
        except Exception as e:
            print(f"[Cleanup] Ошибка при очистке: {e}")
        await asyncio.sleep(24 * 60 * 60)  # 1 день

async def on_startup(dp: Dispatcher):
    print("Бот стартовал!")

async def start_webhook():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 3000)
    await site.start()
    print("Webhook сервер запущен на порту 3000")

async def cleanup_old_records():
    while True:
        try:
            print("[Cleanup] Начинаем очистку старых invoice...")
            cursor.execute(
                "DELETE FROM processed_invoices WHERE created_at < datetime('now', '-7 days')"
            )
            db.commit()
            print("[Cleanup] Очистка завершена.")
        except Exception as e:
            print(f"[Cleanup] Ошибка при очистке: {e}")
        await asyncio.sleep(24 * 60 * 60)  # 1 день

async def main():
    # Удаляем webhook Telegram (если он был установлен)
    await bot.delete_webhook(drop_pending_updates=True)

    # Запускаем вебхук сервер для CryptoBot
    await start_webhook()

    # Запускаем очистку invoice
    asyncio.create_task(cleanup_old_records())

    # Запускаем polling Telegram бота
    await dp.start_polling(bot, skip_updates=True, on_startup=on_startup)

if __name__ == "__main__":
    asyncio.run(main())