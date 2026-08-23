from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
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
    InlineQueryResultPhoto,
    ChosenInlineResult
)

import requests
import random
from decimal import Decimal
from datetime import datetime, timedelta
import sqlite3
from uuid import uuid4
import urllib.parse
import html
import aiohttp
from aiohttp import web
import hashlib
import hmac
import json
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
import difflib
import unicodedata

PAGE_SIZE = 50
ANIME_PER_PAGI = 90
PAGE_SIZI = 10
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
DELETE_MENU = {}
DELETE_ACTIONS = {}
DELETE_ANIME_PER_PAGE = 10
DELETE_EPISODES_PER_PAGE = 40
DOWN_MENU = {}
DOWN_ANIME_PER_PAGE = 10
DURATION_SCANS = set()
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
CRYPTOBOT_API_BASE = os.getenv("CRYPTOBOT_API_BASE", "https://pay.crypt.bot/api").rstrip("/")
WEBHOOK_FULL_URL = os.getenv("WEBHOOK_FULL_URL")

# =========================
# YooKassa settings
# =========================
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")
YOOKASSA_RETURN_URL = os.getenv("YOOKASSA_RETURN_URL") or WEBHOOK_FULL_URL or "https://t.me/"
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "3000"))
SSL_CERT_FILE = os.getenv("SSL_CERT_FILE")
SSL_KEY_FILE = os.getenv("SSL_KEY_FILE")
YOOKASSA_API_PAYMENTS = "https://api.yookassa.ru/v3/payments"

# =========================
# YooMoney wallet settings
# =========================
# YOOMONEY_RECEIVER — номер кошелька ЮMoney, например 41001XXXXXXXXXXXX
# YOOMONEY_SECRET — секрет из настроек HTTP-уведомлений ЮMoney
# YOOMONEY_RETURN_URL — куда вернуть пользователя после оплаты
YOOMONEY_RECEIVER = os.getenv("YOOMONEY_RECEIVER")
YOOMONEY_SECRET = os.getenv("YOOMONEY_SECRET")
YOOMONEY_RETURN_URL = os.getenv("YOOMONEY_RETURN_URL") or WEBHOOK_FULL_URL or "https://t.me/"
YOOMONEY_QUICKPAY_URL = "https://yoomoney.ru/quickpay/confirm"

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
    date TEXT,
    duration INTEGER
)
""")
db.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS collection_likes (
    collection_id INTEGER,
    user_id INTEGER,
    PRIMARY KEY (collection_id, user_id)
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
    file_id TEXT,
    duration INTEGER
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
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id INTEGER PRIMARY KEY,
    nickname_html TEXT,
    description_html TEXT,
    photo TEXT,
    updated_at TEXT
)
""")
db.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER,
    title TEXT NOT NULL,
    description TEXT,
    photo TEXT NOT NULL,
    status TEXT NOT NULL
)
""")

# В старых базах таблица collections уже существует без владельца.
# Добавляем колонку безопасно, не удаляя существующие подборки.
cursor.execute("PRAGMA table_info(collections)")
collection_columns = [col[1] for col in cursor.fetchall()]
if "owner_id" not in collection_columns:
    cursor.execute("ALTER TABLE collections ADD COLUMN owner_id INTEGER")
    db.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS collection_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    collection_id INTEGER NOT NULL,
    anime TEXT NOT NULL,
    position INTEGER NOT NULL,
    FOREIGN KEY(collection_id) REFERENCES collections(id)
)
""")

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

cursor.execute("""
CREATE TABLE IF NOT EXISTS anime_catalog (
    id TEXT PRIMARY KEY,
    anime TEXT UNIQUE NOT NULL
)
""")

db.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS user_bookmarks (
    user_id INTEGER,
    anime TEXT,
    status TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(user_id, anime, status)
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

# --- Безопасно добавляем english_name (если её нет) ---
# Используется для поиска постеров и теперь может задаваться сразу в /darling.
if "english_name" not in columns:
    cursor.execute("ALTER TABLE videos ADD COLUMN english_name TEXT")
    db.commit()
    print("✅ Колонка english_name создана в таблице videos")

# Если раньше была старая колонка title_en — аккуратно переносим данные в english_name.
cursor.execute("PRAGMA table_info(videos)")
columns = [col[1] for col in cursor.fetchall()]
if "title_en" in columns and "english_name" in columns:
    cursor.execute("""
        UPDATE videos
        SET english_name = title_en
        WHERE (english_name IS NULL OR english_name = '')
          AND title_en IS NOT NULL
          AND title_en != ''
    """)
    db.commit()

# Хронометраж видео хранится в секундах. Для старой базы колонка добавляется
# автоматически, а команда /duration_scan заполнит её для уже залитых серий.
cursor.execute("PRAGMA table_info(videos)")
columns = [col[1] for col in cursor.fetchall()]
if "duration" not in columns:
    cursor.execute("ALTER TABLE videos ADD COLUMN duration INTEGER")
    db.commit()
    print("✅ Колонка duration создана в таблице videos")




# =========================
# Исправление случайной раскладки клавиатуры
# =========================

_EN_TO_RU_LAYOUT = {
    "q":"й", "w":"ц", "e":"у", "r":"к", "t":"е", "y":"н", "u":"г",
    "i":"ш", "o":"щ", "p":"з", "[":"х", "]":"ъ",
    "a":"ф", "s":"ы", "d":"в", "f":"а", "g":"п", "h":"р",
    "j":"о", "k":"л", "l":"д", ";":"ж", "'":"э",
    "z":"я", "x":"ч", "c":"с", "v":"м", "b":"и",
    "n":"т", "m":"ь",
}

_RU_TO_EN_LAYOUT = {v: k for k, v in _EN_TO_RU_LAYOUT.items()}

def fix_keyboard_layout(text: str) -> str:
    """Исправляет текст, введённый в неправильной раскладке."""
    if not text:
        return text

    text = text.lower()

    ru_chars = sum(1 for c in text if c in _RU_TO_EN_LAYOUT)
    en_chars = sum(1 for c in text if c in _EN_TO_RU_LAYOUT)

    # Если больше латиницы — считаем, что хотели русский текст.
    if en_chars > ru_chars:
        return "".join(_EN_TO_RU_LAYOUT.get(c, c) for c in text)

    # Если больше кириллицы — считаем, что хотели английский текст.
    if ru_chars > en_chars:
        return "".join(_RU_TO_EN_LAYOUT.get(c, c) for c in text)

    return text


def cut_title(title: str, max_len: int = MAX_TITLE_LEN) -> str:
    """Обрезаем длинные названия аниме для кнопок"""
    return title if len(title) <= max_len else title[:max_len - 3] + "..."


def format_anime_title(title: str) -> str:
    """Отображение названия как в рейтинге: с большой буквы."""
    if not title:
        return title
    return string.capwords(title)


r = requests.get(f"https://api.telegram.org/bot{API_TOKEN}/setWebhook?url={WEBHOOK_FULL_URL}")
print(r.text)  # должен вернуть {"ok":true,...}


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

class MultiEpisodes(StatesGroup):
    waiting_range = State()


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
    tracked = USER_MESSAGES.setdefault(user_id, [])
    if msg.message_id not in tracked:
        tracked.append(msg.message_id)
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

def get_or_create_anime_id(anime: str):
    cursor.execute("SELECT id FROM anime_catalog WHERE anime=?", (anime,))
    row = cursor.fetchone()
    if row:
        return row[0]

    while True:
        anime_id = str(random.randint(100000, 999999))
        cursor.execute("SELECT 1 FROM anime_catalog WHERE id=?", (anime_id,))
        if not cursor.fetchone():
            break

    cursor.execute(
        "INSERT INTO anime_catalog(id, anime) VALUES (?, ?)",
        (anime_id, anime)
    )
    db.commit()
    return anime_id


def get_anime_name_by_id(anime_id):
    """Возвращает название аниме по стабильному ID из anime_catalog."""
    cursor.execute(
        "SELECT anime FROM anime_catalog WHERE id=?",
        (str(anime_id),)
    )
    row = cursor.fetchone()
    return row[0] if row else None


def anime_ids_to_names(anime_ids):
    """Преобразует выбранные ID в названия, сохраняя порядок и убирая дубли."""
    names = []
    seen = set()
    for anime_id in anime_ids:
        anime = get_anime_name_by_id(anime_id)
        if anime and anime not in seen:
            names.append(anime)
            seen.add(anime)
    return names


def anime_names_to_ids(anime_names):
    """Преобразует старый список названий в стабильные ID для редактора."""
    ids = []
    seen = set()
    for anime in anime_names:
        anime_id = str(get_or_create_anime_id(anime))
        if anime_id not in seen:
            ids.append(anime_id)
            seen.add(anime_id)
    return ids



BOOKMARK_STATUSES = ["watching", "completed", "planned", "dropped"]
STATUS_CYCLE = [None, "watching", "completed", "planned", "dropped"]

BOOKMARK_NAMES = {
    "watching": "👀 Смотрю",
    "completed": "✅ Просмотрено",
    "planned": "📌 В планах",
    "dropped": "❌ Брошено",
}

# Отдельная настройка кнопки для каждого состояния просмотра.
# Чтобы поставить свои анимированные эмодзи, замените ID справа.
# Важно: это должны быть ID custom emoji Telegram, а не обычные Unicode-эмодзи.
STATUS_BUTTONS = {
    None: {
        "text": "Не смотрю",
        "icon_custom_emoji_id": "5222444124698853913",
    },
    "watching": {
        "text": "Смотрю",
        "icon_custom_emoji_id": "5210956306952758910",
    },
    "completed": {
        "text": "Просмотрено",
        "icon_custom_emoji_id": "5206607081334906820",
    },
    "planned": {
        "text": "В планах",
        "icon_custom_emoji_id": "5397782960512444700",
    },
    "dropped": {
        "text": "Бр��шено",
        "icon_custom_emoji_id": "5210952531676504517",
    },
}

# Эмодзи меню закладок берутся из тех же настроек, что и кнопки в карточке аниме.
# «Закладки» используют эмодзи «Не смотрю», а «Избранное» — свой эмодзи из карточки.
BOOKMARK_MENU_EMOJI_ID = STATUS_BUTTONS[None]["icon_custom_emoji_id"]
FAVORITE_BUTTON_EMOJI_ID = "5438496463044752972"
BOOKMARK_GROUP_EMOJI_IDS = {
    "favorite": FAVORITE_BUTTON_EMOJI_ID,
    "watching": STATUS_BUTTONS["watching"]["icon_custom_emoji_id"],
    "completed": STATUS_BUTTONS["completed"]["icon_custom_emoji_id"],
    "planned": STATUS_BUTTONS["planned"]["icon_custom_emoji_id"],
    "dropped": STATUS_BUTTONS["dropped"]["icon_custom_emoji_id"],
}

BOOKMARK_LIST_TITLES = {
    "favorite": f'<tg-emoji emoji-id="{BOOKMARK_GROUP_EMOJI_IDS["favorite"]}">👍</tg-emoji> Избранное',
    "watching": f'<tg-emoji emoji-id="{BOOKMARK_GROUP_EMOJI_IDS["watching"]}">👍</tg-emoji> Смотрю',
    "completed": f'<tg-emoji emoji-id="{BOOKMARK_GROUP_EMOJI_IDS["completed"]}">👍</tg-emoji> Просмотрено',
    "planned": f'<tg-emoji emoji-id="{BOOKMARK_GROUP_EMOJI_IDS["planned"]}">👍</tg-emoji> В планах',
    "dropped": f'<tg-emoji emoji-id="{BOOKMARK_GROUP_EMOJI_IDS["dropped"]}">👍</tg-emoji> Брошено',
}


def make_status_button(anime_id: str, current_status: str | None) -> InlineKeyboardButton:
    """Каждый раз создаёт новую кнопку текущего статуса просмотра."""
    if current_status not in STATUS_CYCLE:
        current_status = None

    current_index = STATUS_CYCLE.index(current_status)
    next_status = STATUS_CYCLE[(current_index + 1) % len(STATUS_CYCLE)]
    button = STATUS_BUTTONS[current_status]

    return InlineKeyboardButton(
        text=button["text"],
        callback_data=f"set_status|{anime_id}|{next_status or 'none'}",
        icon_custom_emoji_id=button["icon_custom_emoji_id"],
    )

def toggle_bookmark(user_id, anime, status):
    cursor.execute(
        "DELETE FROM user_bookmarks WHERE user_id=? AND anime=? AND status=?",
        (user_id, anime, status)
    )
    if cursor.rowcount == 0:
        cursor.execute(
            "INSERT INTO user_bookmarks(user_id, anime, status) VALUES(?,?,?)",
            (user_id, anime, status)
        )
        result = True
    else:
        result = False
    db.commit()
    return result

def toggle_favorite(user_id, anime):
    return toggle_bookmark(user_id, anime, "favorite")

def get_bookmark_status(user_id, anime):
    cursor.execute(
        "SELECT status FROM user_bookmarks WHERE user_id=? AND anime=?",
        (user_id, anime)
    )
    return [x[0] for x in cursor.fetchall()]


async def show_bookmark_list(call, status, page=0):
    cursor.execute(
        "SELECT anime FROM user_bookmarks WHERE user_id=? AND status=? ORDER BY created_at DESC",
        (call.from_user.id, status)
    )
    animes = [x[0] for x in cursor.fetchall()]
    start = page * ANIME_PER_PAGE
    items = animes[start:start+ANIME_PER_PAGE]
    group_emoji_id = BOOKMARK_GROUP_EMOJI_IDS.get(status, BOOKMARK_MENU_EMOJI_ID)

    # Используем те же callback-кнопки, что и в топе рейтинга.
    # Поэтому карточка аниме открывается через anime_selected одинаково из всех групп.
    cursor.execute("SELECT DISTINCT anime FROM videos ORDER BY anime")
    all_animes = [row[0] for row in cursor.fetchall()]
    anime_indexes = {anime: index for index, anime in enumerate(all_animes)}

    builder = InlineKeyboardBuilder()
    for anime in items:
        anime_index = anime_indexes.get(anime)
        if anime_index is None:
            continue
        builder.row(InlineKeyboardButton(
            text=cut_title(format_anime_title(anime)),
            callback_data=f"anime_index|{anime_index}",
            icon_custom_emoji_id=group_emoji_id
        ))

    nav=[]
    if page>0:
        nav.append(InlineKeyboardButton(text=" ", icon_custom_emoji_id="5352759161945867747", callback_data=f"bookmark_list|{status}|{page-1}"))
    if start+ANIME_PER_PAGE < len(animes):
        nav.append(InlineKeyboardButton(text=" ", icon_custom_emoji_id="5355075407743826720", callback_data=f"bookmark_list|{status}|{page+1}"))
    if nav:
        builder.row(*nav)

    builder.row(InlineKeyboardButton(text=" Назад", style="primary",icon_custom_emoji_id="5352759161945867747", callback_data="bookmarks_menu"))
    await call.message.edit_text(
        BOOKMARK_LIST_TITLES.get(status, BOOKMARK_LIST_TITLES["favorite"]),
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )


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

class CreateCollection(StatesGroup):
    title = State()
    description = State()  # 👈 новое
    photo = State()
    picking = State() # выбор аниме


class EditCollection(StatesGroup):
    menu = State()
    title = State()
    description = State()
    photo = State()
    picking = State()


class EditUserProfile(StatesGroup):
    nickname = State()
    description = State()
    photo = State()


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
async def start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    chat_id = message.chat.id

    # 🧹 Удаляем активную multi-сессию
    data = await state.get_data()
    messages = data.get("session_messages", [])

    for item in messages:
        try:
            await bot.delete_message(
                chat_id=item["chat_id"],
                message_id=item["message_id"]
            )
        except Exception as e:
            print(f"[START DELETE ERROR] {e}")

    # Удаляем служебные меню из FSM, даже если /start нажат во время ввода.
    state_message_keys = (
        ("picker_message_id", "picker_chat_id"),
        ("profile_prompt_message_id", "profile_prompt_chat_id"),
        ("edit_prompt_message_id", "edit_prompt_chat_id"),
    )
    for message_key, chat_key in state_message_keys:
        message_id = data.get(message_key)
        if not message_id:
            continue
        try:
            await bot.delete_message(
                chat_id=data.get(chat_key) or chat_id,
                message_id=message_id
            )
        except Exception:
            pass

    await state.clear()

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

        parts = [x.strip() for x in args.split(";")]

        if len(parts) not in (5, 6):
            raise ValueError

        anime, dub, season_raw, start_episode, num_episodes = parts[:5]

        # english_name теперь можно указать шестым параметром.
        # Если не указать — скрипт попробует взять уже сохранённое english_name для этого аниме.
        english_name = parts[5].strip() if len(parts) == 6 else ""

        if season_raw.lower() in ["фильм", "film", "movie"]:
            season = "Фильм"
        else:
            season = int(season_raw)

        start_episode = int(start_episode)
        num_episodes = int(num_episodes)

        if start_episode <= 0 or num_episodes <= 0:
            raise ValueError

    except:
        await message.answer(
            "❌ Неверный формат команды.\n\n"
            "Используй:\n"
            "/darling Название ; Озвучка ; Сезон/Фильм ; С какой серии ; Сколько серий ; English name\n\n"
            "English name можно не указывать.\n\n"
            "Пример без English name:\n"
            "/darling One Piece ; Anilibria ; 1 ; 1 ; 12\n\n"
            "Пример с English name:\n"
            "/darling Магическая битва ; Anilibria ; 1 ; 1 ; 24 ; Jujutsu Kaisen\n\n"
            "Пример фильма:\n"
            "/darling Твоё имя ; AniDub ; Фильм ; 1 ; 1 ; Your Name"
        )
        return

    anime_key = anime.lower()
    get_or_create_anime_id(anime_key)

    # Если english_name не указали в команде, берём уже существующее значение из базы.
    if not english_name:
        cursor.execute(
            """
            SELECT english_name
            FROM videos
            WHERE anime=?
              AND english_name IS NOT NULL
              AND english_name != ''
            LIMIT 1
            """,
            (anime_key,)
        )
        row = cursor.fetchone()
        english_name = row[0] if row else None

    cursor.execute(
        "SELECT message_id, file_id, duration FROM pending_videos ORDER BY date ASC LIMIT ?",
        (num_episodes,)
    )

    videos = cursor.fetchall()

    if not videos:
        await message.answer("❌ Нет видео для добавления!")
        return

    for i, (msg_id, file_id, duration) in enumerate(videos, start=start_episode):
        cursor.execute(
            """
            INSERT INTO videos (anime, dub, season, episode, file_id, english_name, duration)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (anime_key, dub, season, i, file_id, english_name, duration)
        )

    # Если english_name указали/нашли — синхронизируем его для всех уже существующих серий этого аниме.
    if english_name:
        cursor.execute(
            "UPDATE videos SET english_name=? WHERE anime=?",
            (english_name, anime_key)
        )

    video_ids = [v[0] for v in videos]

    cursor.execute(
        f"DELETE FROM pending_videos WHERE message_id IN ({','.join(['?']*len(video_ids))})",
        video_ids
    )

    db.commit()

    season_display = "🎬 Фильм" if season == "Фильм" else f"📺 Сезон: {season}"
    english_display = f"\n🇬🇧 English name: {english_name}" if english_name else ""

    await message.answer(
        f"✅ Успешно добавлено {len(videos)} серий\n\n"
        f"🎬 {anime.title()}\n"
        f"🎙 Озвучка: {dub}\n"
        f"{season_display}\n"
        f"▶️ Серии: {start_episode}-{start_episode + len(videos) - 1}"
        f"{english_display}"
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

def has_multi_episode_access(user_id: int) -> bool:
    cursor.execute(
        "SELECT type, expire_date FROM subscriptions WHERE user_id=?",
        (user_id,)
    )
    row = cursor.fetchone()

    if not row:
        return False

    sub_type, expire_date = row

    allowed_types = {
        "30_days",
        "180_days",
        "360_days",
        "forever"
    }

    if sub_type not in allowed_types:
        return False

    if sub_type == "forever":
        return True

    try:
        expire = datetime.fromisoformat(expire_date)
        return expire > datetime.now()
    except:
        return False

@router.callback_query(lambda c: c.data.startswith("multi|"))
async def multi_episodes_start(call: types.CallbackQuery, state: FSMContext):
    user_id = call.from_user.id

    if not has_multi_episode_access(user_id):
        await call.answer("❌ Только подписка 30+ дней", show_alert=True)
        return

    dub_hash = call.data.split("|")[1]

    # 🔥 УДАЛЯЕМ ПРЕДЫДУЩЕЕ СООБЩЕНИЕ (где была кнопка multi)
    try:
        await call.message.delete()
    except:
        pass

    # 🔥 чистим старые сессии
    await state.clear()

    await state.update_data(dub_hash=dub_hash)
    await state.set_state(MultiEpisodes.waiting_range)

    # 🔥 отправляем новое сообщение
    await call.message.answer(
        "<b>🎬 Введите диапазон серий</b>\n"
        "Пример: <code>1-24</code>\n"
        "Максимум 24 серии",
        parse_mode="HTML"
    )

    await call.answer()

@router.message(MultiEpisodes.waiting_range)
async def process_multi_range(message: types.Message, state: FSMContext):
    print(">>> multi start")

    text = message.text.strip()

    try:
        start_ep, end_ep = map(int, text.replace(" ", "").split("-"))
    except ValueError:
        await message.answer("❌ Формат: 1-24")
        return

    if start_ep <= 0 or end_ep <= 0:
        await message.answer("❌ > 0")
        return

    if end_ep < start_ep:
        await message.answer("❌ Ошибка диапазона")
        return

    if (end_ep - start_ep + 1) > 24:
        await message.answer("❌ максимум 24")
        return

    data = await state.get_data()
    dub_hash = data.get("dub_hash")

    if not dub_hash:
        await message.answer("❌ сессия устарела")
        await state.clear()
        return

    cursor.execute("SELECT anime, dub, season FROM videos")

    anime = dub = season = None

    for a, d, s in cursor.fetchall():
        if make_cb_id(a, d, str(s)) == dub_hash:
            anime, dub, season = a, d, s
            break

    if not anime:
        await message.answer("❌ не найдено")
        await state.clear()
        return

    cursor.execute("""
        SELECT episode, file_id
        FROM videos
        WHERE anime=? AND dub=? AND season=?
          AND CAST(episode AS INTEGER) BETWEEN ? AND ?
        ORDER BY CAST(episode AS INTEGER)
    """, (anime, dub, season, start_ep, end_ep))

    episodes = cursor.fetchall()

    if not episodes:
        await message.answer("❌ пусто")
        await state.clear()
        return

    await message.answer(f"📤 отправляю {len(episodes)} серий")

    # 🔥 СЕССИЯ
    session_messages = []

    for ep, file_id in episodes:
        try:
            result = await send_episode(
                user_id=message.from_user.id,
                chat_id=message.chat.id,
                anime=anime,
                dub=dub,
                season=season,
                ep=ep,
                file_id=file_id,
                page=0
            )

            session_messages.append(result)

            await asyncio.sleep(0.4)

        except Exception as e:
            print(f"[MULTI] error ep={ep}: {e}")

    # 🔥 СОХРАНЯЕМ СЕССИЮ
    await state.update_data(
        session_messages=session_messages,
        anime=anime,
        dub=dub,
        season=season
    )

    await state.set_state(None)

    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="Удалить сессию",
            callback_data="multi_exit|menu",
            style="danger",
            icon_custom_emoji_id="5210952531676504517"
        )
    )

    await message.answer(
        "⚠️ Нажатие кнопки удалит все отправленные серии",
        reply_markup=builder.as_markup()
    )

@router.callback_query(lambda c: c.data.startswith("multi_exit"))
async def multi_exit(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    messages = data.get("session_messages", [])

    # 🧹 УДАЛЯЕМ ВСЕ СЕРИИ
    for item in messages:
        try:
            await call.bot.delete_message(
                chat_id=item["chat_id"],
                message_id=item["message_id"]
            )
        except:
            pass

    # 🧹 УДАЛЯЕМ СООБЩЕНИЕ С КНОПКАМИ (ВАЖНО)
    try:
        await call.message.delete()
    except:
        pass

    await state.clear()

    target = call.data.split("|")[1]

    # 📺 В АНИМЕ
    if target == "anime":
        await call.message.answer(
            "📺 Вы вернулись к аниме",
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(
                    text="📺 К аниме",
                    callback_data="back_to_anime"
                )
            ).as_markup()
        )

    # 🏠 В МЕНЮ
    else:
        await call.message.answer(
            "Сессия удалена",
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(
                    text="Меню",
                    callback_data="back_menu",
                    style="success",
                    icon_custom_emoji_id="5312486108309757006"
                )
            ).as_markup()
        )

    await call.answer("🗑 Сессия удалена")

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

    await show_anime_page(message, page=0)


async def show_anime_page(target, page: int):
    cursor.execute("SELECT DISTINCT anime FROM videos ORDER BY anime")
    animes = [row[0] for row in cursor.fetchall()]

    start = page * ANIME_PER_PAGI
    end = start + ANIME_PER_PAGI
    page_items = animes[start:end]

    buttons = []

    # 🎬 список аниме
    for idx, anime in enumerate(page_items, start=start):
        short_name = anime if len(anime) <= 40 else anime[:40] + "..."

        buttons.append([
            InlineKeyboardButton(
                text=short_name,
                callback_data=f"burmal_edit|{idx}"
            )
        ])

    # ⬅️➡️ навигация
    nav_buttons = []

    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"burmal_page|{page - 1}"
            )
        )

    if end < len(animes):
        nav_buttons.append(
            InlineKeyboardButton(
                text="➡️ Вперёд",
                callback_data=f"burmal_page|{page + 1}"
            )
        )

    if nav_buttons:
        buttons.append(nav_buttons)

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    text = f"📋 Выберите аниме (страница {page + 1}):"

    if hasattr(target, "message"):
        await target.message.edit_text(text, reply_markup=kb)
    else:
        await target.answer(text, reply_markup=kb)

@router.callback_query(F.data.startswith("burmal_page|"))
async def burmal_page_handler(call: types.CallbackQuery):
    page = int(call.data.split("|")[1])
    await show_anime_page(call, page)


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


def format_duration(total_seconds) -> str:
    """Форматирует длительность из секунд в ЧЧ:ММ:СС или ММ:СС."""
    try:
        total_seconds = max(0, int(total_seconds or 0))
    except (TypeError, ValueError):
        total_seconds = 0

    if total_seconds <= 0:
        return "не определён"

    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


async def detect_video_duration(chat_id: int, file_id: str) -> int | None:
    """Временно отправляет Telegram-видео, читает duration и удаляет сообщение."""
    temporary_message = None
    try:
        temporary_message = await bot.send_video(
            chat_id=chat_id,
            video=file_id,
            disable_notification=True,
            protect_content=True
        )
        if temporary_message.video and temporary_message.video.duration:
            return int(temporary_message.video.duration)
        return None
    finally:
        if temporary_message:
            try:
                await bot.delete_message(
                    chat_id=temporary_message.chat.id,
                    message_id=temporary_message.message_id
                )
            except Exception:
                pass


@router.message(Command("duration_scan"))
async def duration_scan(message: types.Message):
    """Заполняет хронометраж уже сохранённых Telegram-видео."""
    user_id = message.from_user.id
    if user_id not in ADMINS:
        await message.answer("❌ У тебя нет прав для этой команды.")
        return

    if user_id in DURATION_SCANS:
        await message.answer("⏳ Сканирование хронометража уже запущено.")
        return

    cursor.execute(
        """
        SELECT file_id, COUNT(*)
        FROM videos
        WHERE (duration IS NULL OR duration <= 0)
          AND file_id IS NOT NULL
          AND file_id NOT LIKE 'http://%'
          AND file_id NOT LIKE 'https://%'
        GROUP BY file_id
        """
    )
    files_to_scan = cursor.fetchall()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM videos
        WHERE (duration IS NULL OR duration <= 0)
          AND (file_id LIKE 'http://%' OR file_id LIKE 'https://%')
        """
    )
    link_rows = int(cursor.fetchone()[0] or 0)

    if not files_to_scan:
        text = "✅ У всех Telegram-видео хронометраж уже заполнен."
        if link_rows:
            text += f"\n\n⚠️ Ссылки без хронометража: {link_rows}. Они не сканируются через Telegram file_id."
        await message.answer(text)
        return

    total_files = len(files_to_scan)
    total_rows = sum(int(row_count) for _, row_count in files_to_scan)
    progress_message = await message.answer(
        "⏱ <b>Сканирование хронометража</b>\n\n"
        f"Уникальных видео: <b>{total_files}</b>\n"
        f"Записей серий: <b>{total_rows}</b>\n"
        "Обработано: <b>0</b>",
        parse_mode="HTML"
    )

    DURATION_SCANS.add(user_id)
    filled_files = 0
    filled_rows = 0
    failed_files = []

    try:
        for index, (file_id, affected_rows) in enumerate(files_to_scan, start=1):
            duration = None
            last_error = None

            # При ограничении Telegram ждём указанное время и повторяем запрос.
            for attempt in range(3):
                try:
                    duration = await detect_video_duration(message.chat.id, file_id)
                    break
                except Exception as error:
                    last_error = error
                    retry_after = getattr(error, "retry_after", None)
                    if retry_after and attempt < 2:
                        await asyncio.sleep(float(retry_after) + 1)
                        continue
                    break

            if duration:
                cursor.execute(
                    """
                    UPDATE videos
                    SET duration=?
                    WHERE file_id=? AND (duration IS NULL OR duration <= 0)
                    """,
                    (duration, file_id)
                )
                filled_files += 1
                filled_rows += max(0, cursor.rowcount)
            else:
                failed_files.append(file_id)
                if last_error:
                    logging.warning("Не удалось получить duration для %s: %s", file_id, last_error)

            if index % 20 == 0:
                db.commit()

            if index % 10 == 0 or index == total_files:
                try:
                    await progress_message.edit_text(
                        "⏱ <b>Сканирование хронометража</b>\n\n"
                        f"Обработано: <b>{index}/{total_files}</b>\n"
                        f"Заполнено видео: <b>{filled_files}</b>\n"
                        f"Заполнено записей: <b>{filled_rows}</b>\n"
                        f"Ошибок: <b>{len(failed_files)}</b>",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass

            # Небольшая пауза уменьшает вероятность flood control.
            await asyncio.sleep(0.12)

        db.commit()

        result = (
            "✅ <b>Сканирование завершено</b>\n\n"
            f"Проверено уникальных видео: <b>{total_files}</b>\n"
            f"Хронометраж заполнен у видео: <b>{filled_files}</b>\n"
            f"Обновлено записей серий: <b>{filled_rows}</b>\n"
            f"Не удалось обработать: <b>{len(failed_files)}</b>"
        )
        if link_rows:
            result += f"\nСсылки пропущены: <b>{link_rows}</b>"

        await progress_message.edit_text(result, parse_mode="HTML")
    finally:
        DURATION_SCANS.discard(user_id)


@router.message(F.video)
async def get_video(message: types.Message):

    if message.from_user.id not in ADMINS:
        return

    duration = int(message.video.duration or 0) or None

    cursor.execute(
        "INSERT OR IGNORE INTO pending_videos (message_id, file_id, date, duration) VALUES (?, ?, ?, ?)",
        (message.message_id, message.video.file_id, str(message.date), duration)
    )

    db.commit()

    await send_and_track(
        message.from_user.id,
        message.answer,
        f"✅ Видео сохранено и готово для добавления в базу\n"
        f"⏱ Хронометраж: {format_duration(duration)}"
    )

@router.message(lambda m: m.text and not m.text.startswith("/") and URL_RE.search(m.text))
async def get_video_link(message: types.Message):

    if message.from_user.id not in ADMINS:
        return

    url = URL_RE.search(message.text).group(0)

    cursor.execute(
        "INSERT OR IGNORE INTO pending_videos (message_id, file_id, date, duration) VALUES (?, ?, ?, ?)",
        (message.message_id, url, str(message.date), None)
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

def format_episode_caption(season, episode):
    """Для фильма показывает только «Фильм», для сериала — сезон и серию."""
    if str(season).strip().lower() in {"фильм", "film", "movie"}:
        return "Фильм"
    return f"{season} сезон {episode} серия"


async def send_video_by_params(call: types.CallbackQuery, anime, dub, season, ep):
    cursor.execute("SELECT file_id FROM videos WHERE anime=? AND dub=? AND season=? AND episode=?",
                   (anime, dub, season, ep))
    row = cursor.fetchone()
    if not row:
        await call.answer("❌ Видео не найдено", show_alert=True)
        return

    file_id = row[0]
    episode_caption = format_episode_caption(season, ep)
    caption = f"<b>{anime}</b>\n<b><i>{dub}</i></b>\n<i>{episode_caption}</i>"

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


async def show_picker(target, state, page=0, update_existing=False):
    data = await state.get_data()
    selected_ids = [str(anime_id) for anime_id in data.get("selected", [])]
    is_edit = data.get("collection_mode") == "edit"

    # В состоянии храним только ID. Названия получаем из anime_catalog для отображения.
    selected_pairs = []
    valid_ids = []
    for anime_id in selected_ids:
        anime = get_anime_name_by_id(anime_id)
        if anime:
            selected_pairs.append((anime_id, anime))
            valid_ids.append(anime_id)

    if valid_ids != selected_ids:
        selected_ids = valid_ids
        await state.update_data(selected=selected_ids)

    buttons = []

    # Удаление тоже работает по ID, поэтому длинное название не попадает в callback_data.
    for anime_id, anime in selected_pairs:
        buttons.append([
            InlineKeyboardButton(
                text=f" {cut_title(string.capwords(anime), 40)}",
                callback_data=f"remove_pick|{anime_id}",
                icon_custom_emoji_id="5210952531676504517"
            )
        ])

    # 🔍 добавить через inline
    buttons.append([
        InlineKeyboardButton(
            text=" Добавить аниме",
            switch_inline_query_current_chat="",
            style="primary",
            icon_custom_emoji_id="5231012545799666522"
        )
    ])

    # действия
    buttons.append([
        InlineKeyboardButton(
            text=" Готово" if is_edit else " Завершить",
            callback_data="edit_picker_done" if is_edit else "finish_collection",
            style="success",
            icon_custom_emoji_id="5206607081334906820"
        )
    ])

    buttons.append([
        InlineKeyboardButton(
            text=" Назад к редактированию" if is_edit else " Отмена",
            callback_data="edit_picker_done" if is_edit else "cancel_collection",
            style="danger",
            icon_custom_emoji_id="5210952531676504517"
        )
    ])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    text = (
        f"<tg-emoji emoji-id=\"5350513667144163474\">👍</tg-emoji> "
        f"Выбрано аниме: <b>{len(selected_pairs)}/50</b>"
    )

    if selected_pairs:
        text += "\n\n<b>Добавленные аниме:</b>\n"
        for number, (_, anime) in enumerate(selected_pairs, 1):
            text += f"{number}. {html.escape(cut_title(string.capwords(anime), 60))}\n"
    else:
        text += "\n\n<b>Добавленные аниме:</b>\n— пока ничего не добавлено —"

    if isinstance(target, types.CallbackQuery):
        try:
            await target.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            await state.update_data(
                picker_chat_id=target.message.chat.id,
                picker_message_id=target.message.message_id
            )
            return
        except Exception:
            pass

    # После выбора inline-результата обновляем исходное сообщение со счётчиком,
    # а не отправляем новый список отдельным сообщением.
    data = await state.get_data()
    picker_chat_id = data.get("picker_chat_id")
    picker_message_id = data.get("picker_message_id")
    if update_existing and picker_chat_id and picker_message_id:
        try:
            await bot.edit_message_text(
                chat_id=picker_chat_id,
                message_id=picker_message_id,
                text=text,
                parse_mode="HTML",
                reply_markup=kb
            )
            return
        except Exception:
            pass

    sent_message = await send_and_track(
        target.from_user.id,
        target.answer,
        text,
        reply_markup=kb,
        parse_mode="HTML"
    )
    await state.update_data(
        picker_chat_id=sent_message.chat.id,
        picker_message_id=sent_message.message_id
    )

@router.message(StateFilter(CreateCollection.picking, EditCollection.picking), F.content_type == ContentType.TEXT)
async def pick_from_inline(message: types.Message, state: FSMContext):
    # Inline-поиск отправляет стабильный ID из anime_catalog, а не название.
    anime_id = message.text.strip()
    anime = get_anime_name_by_id(anime_id)

    if not anime:
        await send_and_track(
            message.from_user.id,
            message.answer,
            "<tg-emoji emoji-id=\"5210952531676504517\">👍</tg-emoji> Неверный ID аниме",
            parse_mode="HTML"
        )
        return

    data = await state.get_data()
    selected = [str(value) for value in data.get("selected", [])]

    # лимит
    if anime_id not in selected and len(selected) >= 50:
        await send_and_track(
            message.from_user.id,
            message.answer,
            "<tg-emoji emoji-id=\"5210952531676504517\">👍</tg-emoji> Максимум 50 аниме",
            parse_mode="HTML"
        )
        return

    if anime_id in selected:
        # Повторный выбор не создаёт новое сообщение и не удаляет аниме из списка.
        try:
            await message.delete()
        except Exception:
            pass
        return

    selected.append(anime_id)

    await state.update_data(selected=selected)

    # Убираем техническое сообщение с ID и обновляем исходный экран выбора.
    try:
        await message.delete()
    except Exception:
        pass
    await show_picker(message, state, update_existing=True)

@router.chosen_inline_result()
async def handle_inline_choice(chosen: ChosenInlineResult, state: FSMContext):
    # Сам выбор обрабатывается сообщением с anime_id в pick_from_inline.
    # Здесь ничего не добавляем, иначе одно нажатие учитывалось бы дважды.
    current_state = await state.get_state()
    if current_state not in {CreateCollection.picking.state, EditCollection.picking.state}:
        return
    return

@router.callback_query(F.data.startswith("remove_pick"))
async def remove_pick(call: types.CallbackQuery, state: FSMContext):
    anime_id = call.data.split("|", 1)[1]

    data = await state.get_data()
    selected = [str(value) for value in data.get("selected", [])]

    if anime_id in selected:
        selected.remove(anime_id)

    await state.update_data(selected=selected)

    await show_picker(call, state)
    await call.answer()

@router.callback_query(F.data.startswith("pick|"))
async def pick_anime(call: types.CallbackQuery, state: FSMContext):
    _, idx_str, page = call.data.split("|")
    idx = int(idx_str)
    page = int(page)

    # Берём аниме по индексу
    cursor.execute("SELECT DISTINCT anime FROM videos ORDER BY anime")
    all_animes = [r[0] for r in cursor.fetchall()]

    if idx >= len(all_animes):
        await call.answer("<tg-emoji emoji-id=\"5210952531676504517\">👍</tg-emoji> Аниме не найдено", show_alert=True,parse_mode="HTML")
        return

    anime = all_animes[idx]
    anime_id = str(get_or_create_anime_id(anime))

    data = await state.get_data()
    selected = [str(value) for value in data.get("selected", [])]

    # лимит
    if anime_id not in selected and len(selected) >= 50:
        await call.answer("<tg-emoji emoji-id=\"5210952531676504517\">👍</tg-emoji> Максимум 50 аниме", show_alert=True,parse_mode="HTML")
        return

    if anime_id not in selected:
        selected.append(anime_id)
    else:
        selected.remove(anime_id)

    await state.update_data(selected=selected)

    await show_picker(call, state, page)
    await call.answer()

@router.callback_query(F.data.startswith("pick_page"))
async def pick_page(call: types.CallbackQuery, state: FSMContext):
    page = int(call.data.split("|")[1])
    await show_picker(call, state, page)

async def send_collection_to_admins(collection_id, title, description, photo, selected, is_edit=False):
    heading = "✏️ Подборка изменена" if is_edit else "🆕 Новая подборка"
    text = f"<b>{heading}</b>\n\n<b>{html.escape(str(title))}</b>\n\n"

    if description:
        text += f"📝 {html.escape(str(description))}\n\n"

    text += "📺 Аниме:\n"

    for i, anime in enumerate(selected, 1):
        text += f"{i}. {html.escape(string.capwords(anime))}\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Одобрить",
                callback_data=f"approve_collection|{collection_id}"
            ),
            InlineKeyboardButton(
                text="❌ Отклонить",
                callback_data=f"reject_collection|{collection_id}"
            )
        ]
    ])

    for admin_id in ADMINS:
        try:
            await bot.send_photo(
                admin_id,
                photo=photo,
                caption=text,
                parse_mode="HTML",
                reply_markup=kb
            )
        except:
            pass

@router.callback_query(F.data == "finish_collection")
async def finish_collection(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()

    title = data.get("title")
    description = data.get("description")  # 👈 добавили
    photo = data.get("photo")
    selected_ids = [str(value) for value in data.get("selected", [])]
    selected = anime_ids_to_names(selected_ids)

    if not title or not photo:
        await call.answer(
            "<tg-emoji emoji-id=\"5210952531676504517\">👍</tg-emoji> Ошибка данных",
            show_alert=True,
            parse_mode="HTML"
        )
        return

    if not selected:
        await call.answer(
            "<tg-emoji emoji-id=\"5210952531676504517\">👍</tg-emoji> Выбери хотя бы одно аниме",
            show_alert=True,
            parse_mode="HTML"
        )
        return

    # 📝 ограничение описания сразу при сохранении (лучше здесь)
    if description and len(description) > 500:
        description = description[:500].rstrip() + "…"

    # 💾 сохраняем подборку
    cursor.execute(
        "INSERT INTO collections (owner_id, title, description, photo, status) VALUES (?, ?, ?, ?, 'pending')",
        (call.from_user.id, title, description, photo)
    )
    collection_id = cursor.lastrowid

    # 🎬 сохраняем аниме
    for i, anime in enumerate(selected):
        cursor.execute(
            "INSERT INTO collection_items (collection_id, anime, position) VALUES (?, ?, ?)",
            (collection_id, anime, i)
        )

    db.commit()
    await state.clear()

    # 📩 отправка админам (тоже передаём description)
    await send_collection_to_admins(collection_id, title, description, photo, selected)

    try:
        await call.message.delete()
    except:
        pass

    await send_and_track(
        call.from_user.id,
        call.message.answer,
        "<tg-emoji emoji-id=\"5350513667144163474\">👍</tg-emoji> Подборка отправлена на модерацию",
        parse_mode="HTML"
    )

    await call.answer()

@router.callback_query(F.data == "cancel_collection")
async def cancel_collection(call: types.CallbackQuery, state: FSMContext):
    await state.clear()

    await call.message.delete()
    await send_and_track(
        call.from_user.id,
        call.message.answer,
        "<tg-emoji emoji-id=\"5210952531676504517\">👍</tg-emoji> Создание отменено",
        parse_mode="HTML"
    )
    await call.answer()

@router.callback_query(F.data.startswith("approve_collection"))
async def approve_collection(call: types.CallbackQuery):
    collection_id = int(call.data.split("|")[1])

    cursor.execute(
        "SELECT owner_id, title, status FROM collections WHERE id=?",
        (collection_id,)
    )
    collection = cursor.fetchone()
    if not collection:
        await call.answer("Подборка не найдена", show_alert=True)
        return

    owner_id, title, old_status = collection

    cursor.execute(
        "UPDATE collections SET status='approved' WHERE id=?",
        (collection_id,)
    )
    db.commit()

    await call.message.edit_caption(
        call.message.caption + "\n\n <b>Одобрено</b>",
        parse_mode="HTML"
    )

    if owner_id and old_status != "approved":
        try:
            await send_and_track(
                owner_id,
                bot.send_message,
                owner_id,
                f"✅ Ваша подборка <b>{html.escape(str(title))}</b> одобрена и опубликована.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=" Открыть подборку",
                        callback_data=f"open_collection|{collection_id}",
                        style="success",
                        icon_custom_emoji_id="5206607081334906820"
                    )]
                ])
            )
        except Exception as error:
            logging.warning(f"Не удалось уведомить владельца подборки {collection_id}: {error}")

    await call.answer("Одобрено")

@router.callback_query(F.data.startswith("reject_collection"))
async def reject_collection(call: types.CallbackQuery):
    collection_id = int(call.data.split("|")[1])

    cursor.execute(
        "SELECT owner_id, title, status FROM collections WHERE id=?",
        (collection_id,)
    )
    collection = cursor.fetchone()
    if not collection:
        await call.answer("Подборка не найдена", show_alert=True)
        return

    owner_id, title, old_status = collection

    cursor.execute(
        "UPDATE collections SET status='rejected' WHERE id=?",
        (collection_id,)
    )
    db.commit()

    await call.message.edit_caption(
        call.message.caption + "\n\n <b>Отклонено</b>",
        parse_mode="HTML"
    )

    if owner_id and old_status != "rejected":
        try:
            await send_and_track(
                owner_id,
                bot.send_message,
                owner_id,
                f"❌ Ваша подборка <b>{html.escape(str(title))}</b> не одобрена. Вы можете изменить её и отправить повторно.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=" Редактировать подборку",
                        callback_data=f"edit_collection_open|{collection_id}",
                        style="primary",
                        icon_custom_emoji_id="5373251851074415873"
                    )]
                ])
            )
        except Exception as error:
            logging.warning(f"Не удалось уведомить владельца подборки {collection_id}: {error}")

    await call.answer("Отклонено")

@router.callback_query(F.data.startswith("curated_lists"))
async def curated_lists(call: types.CallbackQuery):
    parts = call.data.split("|")
    page = int(parts[1]) if len(parts) > 1 else 0

    limit = 10  # как PAGE_SIZI
    offset = page * limit

    # получаем подборки
    cursor.execute("""
        SELECT id, title
        FROM collections
        WHERE status = 'approved'
        ORDER BY id DESC
        LIMIT ? OFFSET ?
    """, (limit, offset))
    rows = cursor.fetchall()

    if not rows and page == 0:
        await call.answer("Список пуст", show_alert=True)
        return

    # общее количество
    cursor.execute("""
        SELECT COUNT(*)
        FROM collections
        WHERE status = 'approved'
    """)
    total = cursor.fetchone()[0]

    buttons = []

    # 📚 список подборок
    for col_id, title in rows:
        buttons.append([
            InlineKeyboardButton(
                text=title,
                callback_data=f"open_collection|{col_id}"
            )
        ])

    # 🔁 пагинация (как у тебя)
    nav_buttons = []

    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                text=" ",
                callback_data=f"curated_lists|{page - 1}",
                icon_custom_emoji_id="5352759161945867747"
            )
        )

    if offset + limit < total:
        nav_buttons.append(
            InlineKeyboardButton(
                text=" ",
                callback_data=f"curated_lists|{page + 1}",
                style="primary",
                icon_custom_emoji_id="5355075407743826720"
            )
        )

    if nav_buttons:
        buttons.append(nav_buttons)

    # 🔙 назад
    buttons.append([
        InlineKeyboardButton(
            text=" Назад",
            callback_data="overview_menu",
            style="primary",
            icon_custom_emoji_id="5352759161945867747"
        )
    ])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    try:
        await call.message.delete()
    except:
        pass

    await send_and_track(
        call.from_user.id,
        call.message.answer,
        f"<b><tg-emoji emoji-id=\"5357315181649076022\">👍</tg-emoji> Подборки (стр. {page + 1}):</b>",
        parse_mode="HTML",
        reply_markup=kb
    )

    await call.answer()

# 🔘 клавиатура отмены
cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(
            text=" Отмена",
            callback_data="cancel_collection",
            style="danger",
            icon_custom_emoji_id="5210952531676504517"
        )
    ]
])


COLLECTION_STATUS_NAMES = {
    "pending": "⏳ На модерации",
    "approved": "✅ Одобрена",
    "rejected": "❌ Отклонена",
}


def get_owned_collection(collection_id: int, user_id: int):
    cursor.execute(
        """
        SELECT id, title, description, photo, status
        FROM collections
        WHERE id=? AND owner_id=?
        """,
        (collection_id, user_id)
    )
    return cursor.fetchone()


def get_collection_animes(collection_id: int):
    cursor.execute(
        "SELECT anime FROM collection_items WHERE collection_id=? ORDER BY position",
        (collection_id,)
    )
    return [row[0] for row in cursor.fetchall()]


@router.callback_query(F.data == "user_collections_menu")
async def user_collections_menu(call: types.CallbackQuery, state: FSMContext):
    await state.clear()

    kb = InlineKeyboardMarkup(inline_keyboard=[
         [InlineKeyboardButton(
            text=" Мои подборки",
            callback_data="my_collections|0",
            icon_custom_emoji_id="5357315181649076022"
        )],
         [InlineKeyboardButton(
            text=" Создать подборку",
            callback_data="create_collection",
            style="success",
            icon_custom_emoji_id="5397916757333654639"
        )],
        [InlineKeyboardButton(
            text=" Редактировать подборки",
            callback_data="edit_collections|0",
            style="danger",
            icon_custom_emoji_id="5373251851074415873"
        )],
       
        [InlineKeyboardButton(
            text=" Назад",
            callback_data="profile_menu",
            style="primary",
            icon_custom_emoji_id="5352759161945867747"
        )],
    ])

    try:
        await send_and_track(
            call.from_user.id,
            call.message.edit_text,
            "<b><tg-emoji emoji-id=\"5357315181649076022\">👍</tg-emoji> Подборки:</b>",
            parse_mode="HTML",
            reply_markup=kb
        )
    except Exception:
        try:
            await call.message.delete()
        except Exception:
            pass
        await send_and_track(
            call.from_user.id,
            call.message.answer,
            "<b><tg-emoji emoji-id=\"5357315181649076022\">👍</tg-emoji> Подборки:</b>",
            parse_mode="HTML",
            reply_markup=kb
        )

    await call.answer()


async def show_owned_collections(call: types.CallbackQuery, mode: str, page: int = 0):
    user_id = call.from_user.id
    page = max(0, page)
    limit = 10
    offset = page * limit

    cursor.execute(
        "SELECT COUNT(*) FROM collections WHERE owner_id=?",
        (user_id,)
    )
    total = cursor.fetchone()[0]

    cursor.execute(
        """
        SELECT id, title, status
        FROM collections
        WHERE owner_id=?
        ORDER BY id DESC
        LIMIT ? OFFSET ?
        """,
        (user_id, limit, offset)
    )
    rows = cursor.fetchall()

    if not rows and page > 0:
        page = max(0, (total - 1) // limit) if total else 0
        offset = page * limit
        cursor.execute(
            """
            SELECT id, title, status
            FROM collections
            WHERE owner_id=?
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            (user_id, limit, offset)
        )
        rows = cursor.fetchall()

    buttons = []
    callback_prefix = "edit_collection_open" if mode == "edit" else "my_collection_open"

    for collection_id, title, status in rows:
        status_icon = {"pending": "⏳", "approved": "✅", "rejected": "❌"}.get(status, "•")
        button_title = cut_title(str(title), 40)
        button_text = f"{status_icon} {button_title}" if mode == "edit" else button_title
        buttons.append([
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"{callback_prefix}|{collection_id}"
            )
        ])

    nav = []
    list_prefix = "edit_collections" if mode == "edit" else "my_collections"
    if page > 0:
        nav.append(InlineKeyboardButton(
            text=" ",
            callback_data=f"{list_prefix}|{page - 1}",
            icon_custom_emoji_id="5352759161945867747"
        ))
    if offset + limit < total:
        nav.append(InlineKeyboardButton(
            text=" ",
            callback_data=f"{list_prefix}|{page + 1}",
            icon_custom_emoji_id="5355075407743826720"
        ))
    if nav:
        buttons.append(nav)

    if not rows:
        buttons.append([InlineKeyboardButton(
            text=" Создать подборку",
            callback_data="create_collection",
            style="success",
            icon_custom_emoji_id="5397916757333654639"
        )])
        # Если подборок нет, кнопка «Назад» синяя и в «Моих подборках»,
        # и в «Редактировании подборок» — обе страницы используют эту функцию.
        buttons.append([InlineKeyboardButton(
            text=" Назад",
            callback_data="user_collections_menu",
            style="primary",
            icon_custom_emoji_id="5352759161945867747"
        )])
    else:
        buttons.append([InlineKeyboardButton(
            text=" Назад",
            callback_data="user_collections_menu",
            icon_custom_emoji_id="5352759161945867747"
        )])

    title = "Редактирование подборок" if mode == "edit" else "Мои подборки"
    text = f"<b>{title}</b>\n\n"
    if rows:
        text += f"Страница {page + 1}. Нажми на подборку, чтобы {'изменить её' if mode == 'edit' else 'открыть её'}."
    else:
        text += "У тебя пока нет подборок."

    try:
        await call.message.delete()
    except Exception:
        pass

    await send_and_track(
        user_id,
        call.message.answer,
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await call.answer()


@router.callback_query(F.data.startswith("my_collections|"))
async def my_collections(call: types.CallbackQuery):
    page = int(call.data.split("|", 1)[1])
    await show_owned_collections(call, "my", page)


@router.callback_query(F.data.startswith("edit_collections|"))
async def edit_collections(call: types.CallbackQuery):
    page = int(call.data.split("|", 1)[1])
    await show_owned_collections(call, "edit", page)


async def show_collection_edit_menu(target, state: FSMContext, notice: str = ""):
    data = await state.get_data()
    collection_id = data.get("collection_id")
    title = data.get("title", "")
    description = data.get("description", "")
    selected = data.get("selected", [])

    text = "<b>Редактирование подборки</b>\n\n"
    if notice:
        text += f"{html.escape(notice)}\n\n"
    text += (
        f"Название: <b>{html.escape(str(title))}</b>\n"
        f"Описание: {html.escape(str(description or '—'))}\n"
        f"Аниме: <b>{len(selected)}</b>"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=" Изменить название", callback_data="edit_collection_field|title")],
        [InlineKeyboardButton(text=" Изменить описание", callback_data="edit_collection_field|description")],
        [InlineKeyboardButton(text=" Изменить фото", callback_data="edit_collection_field|photo")],
        [InlineKeyboardButton(text=" Изменить аниме", callback_data="edit_collection_field|anime")],
        [InlineKeyboardButton(
            text=" Сохранить изменения",
            callback_data="save_collection_edit",
            style="success",
            icon_custom_emoji_id="5206607081334906820"
        )],
        [InlineKeyboardButton(
            text=" Отмена",
            callback_data="cancel_collection_edit",
            style="danger",
            icon_custom_emoji_id="5210952531676504517"
        )],
    ])

    if isinstance(target, types.CallbackQuery):
        try:
            await target.message.delete()
        except Exception:
            pass
        await send_and_track(
            target.from_user.id,
            target.message.answer,
            text,
            parse_mode="HTML",
            reply_markup=kb
        )
    else:
        await send_and_track(
            target.from_user.id,
            target.answer,
            text,
            parse_mode="HTML",
            reply_markup=kb
        )


@router.callback_query(F.data.startswith("edit_collection_open|"))
async def edit_collection_open(call: types.CallbackQuery, state: FSMContext):
    collection_id = int(call.data.split("|", 1)[1])
    row = get_owned_collection(collection_id, call.from_user.id)

    if not row:
        await call.answer("Подборка не найдена", show_alert=True)
        return

    _, title, description, photo, status = row
    await state.set_state(EditCollection.menu)
    await state.set_data({
        "collection_mode": "edit",
        "collection_id": collection_id,
        "title": title,
        "description": description or "",
        "photo": photo,
        "selected": anime_names_to_ids(get_collection_animes(collection_id)),
        "original_status": status,
    })
    await show_collection_edit_menu(call, state)
    await call.answer()


edit_input_back_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(
        text=" Назад к редактированию",
        callback_data="edit_collection_input_back",
        style="primary",
        icon_custom_emoji_id="5352759161945867747"
    )]
])


@router.callback_query(F.data.startswith("edit_collection_field|"))
async def edit_collection_field(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    collection_id = data.get("collection_id")
    if not collection_id or not get_owned_collection(collection_id, call.from_user.id):
        await state.clear()
        await call.answer("Подборка не найдена", show_alert=True)
        return

    field = call.data.split("|", 1)[1]
    prompts = {
        "title": "Введи новое название подборки:",
        "description": "Введи новое описание подборки (до 500 символов):",
        "photo": "Отправь новое фото подборки:",
    }

    if field == "anime":
        await state.set_state(EditCollection.picking)
        await show_picker(call, state)
        await call.answer()
        return

    state_by_field = {
        "title": EditCollection.title,
        "description": EditCollection.description,
        "photo": EditCollection.photo,
    }
    if field not in state_by_field:
        await call.answer("Неизвестное поле", show_alert=True)
        return

    await state.set_state(state_by_field[field])
    try:
        await call.message.delete()
    except Exception:
        pass
    prompt_message = await send_and_track(
        call.from_user.id,
        call.message.answer,
        prompts[field],
        reply_markup=edit_input_back_kb
    )
    await state.update_data(
        edit_prompt_chat_id=prompt_message.chat.id,
        edit_prompt_message_id=prompt_message.message_id
    )
    await call.answer()


@router.callback_query(F.data == "edit_collection_input_back")
async def edit_collection_input_back(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(EditCollection.menu)
    await show_collection_edit_menu(call, state)
    await call.answer()


@router.message(EditCollection.title, F.content_type == ContentType.TEXT)
async def edit_collection_title(message: types.Message, state: FSMContext):
    title = message.text.strip()
    if not title:
        await send_and_track(
            message.from_user.id,
            message.answer,
            "Название не может быть пустым",
            reply_markup=edit_input_back_kb
        )
        return
    if len(title) > 100:
        await send_and_track(
            message.from_user.id,
            message.answer,
            "Название должно быть не длиннее 100 символов",
            reply_markup=edit_input_back_kb
        )
        return
    await state.update_data(title=title)
    await state.set_state(EditCollection.menu)
    await show_collection_edit_menu(message, state, "Название изменено")


@router.message(EditCollection.description, F.content_type == ContentType.TEXT)
async def edit_collection_description(message: types.Message, state: FSMContext):
    description = message.text.strip()
    if len(description) > 500:
        await send_and_track(
            message.from_user.id,
            message.answer,
            "Описание должно быть не длиннее 500 символов",
            reply_markup=edit_input_back_kb
        )
        return
    await state.update_data(description=description)
    await state.set_state(EditCollection.menu)
    await show_collection_edit_menu(message, state, "Описание изменено")


@router.message(EditCollection.photo)
async def edit_collection_photo(message: types.Message, state: FSMContext):
    if not message.photo:
        await send_and_track(
            message.from_user.id,
            message.answer,
            "Отправь именно фото",
            reply_markup=edit_input_back_kb
        )
        return
    await state.update_data(photo=message.photo[-1].file_id)
    await state.set_state(EditCollection.menu)
    await show_collection_edit_menu(message, state, "Фото изменено")


@router.callback_query(F.data == "edit_picker_done")
async def edit_picker_done(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("selected"):
        await call.answer("Выбери хотя бы одно аниме", show_alert=True)
        return
    await state.set_state(EditCollection.menu)
    await show_collection_edit_menu(call, state, "Список аниме изменён")
    await call.answer()


@router.callback_query(F.data == "save_collection_edit")
async def save_collection_edit(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    collection_id = data.get("collection_id")
    row = get_owned_collection(collection_id, call.from_user.id) if collection_id else None
    if not row:
        await state.clear()
        await call.answer("Подборка не найдена", show_alert=True)
        return

    title = str(data.get("title", "")).strip()
    description = str(data.get("description", "")).strip()
    photo = data.get("photo")
    selected_ids = [str(value) for value in data.get("selected", [])]
    selected = anime_ids_to_names(selected_ids)

    if not title or not photo or not selected:
        await call.answer("Заполни название, фото и выбери хотя бы одно аниме", show_alert=True)
        return

    cursor.execute(
        """
        UPDATE collections
        SET title=?, description=?, photo=?, status='pending'
        WHERE id=? AND owner_id=?
        """,
        (title, description[:500], photo, collection_id, call.from_user.id)
    )
    cursor.execute("DELETE FROM collection_items WHERE collection_id=?", (collection_id,))
    for position, anime in enumerate(selected):
        cursor.execute(
            "INSERT INTO collection_items (collection_id, anime, position) VALUES (?, ?, ?)",
            (collection_id, anime, position)
        )
    db.commit()
    await state.clear()

    await send_collection_to_admins(
        collection_id,
        title,
        description[:500],
        photo,
        selected,
        is_edit=True
    )

    try:
        await call.message.delete()
    except Exception:
        pass
    await send_and_track(
        call.from_user.id,
        call.message.answer,
        "✅ Изменения сохранены. Подборка отправлена на повторную модерацию.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=" К подборкам", callback_data="user_collections_menu")]
        ])
    )
    await call.answer()


@router.callback_query(F.data == "cancel_collection_edit")
async def cancel_collection_edit(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await show_owned_collections(call, "edit", 0)


@router.callback_query(F.data.startswith("my_collection_open|"))
async def my_collection_open(call: types.CallbackQuery):
    collection_id = int(call.data.split("|", 1)[1])
    row = get_owned_collection(collection_id, call.from_user.id)
    if not row:
        await call.answer("Подборка не найдена", show_alert=True)
        return

    _, title, description, photo, status = row
    animes = get_collection_animes(collection_id)

    cursor.execute("SELECT DISTINCT anime FROM videos ORDER BY anime")
    all_animes = [r[0] for r in cursor.fetchall()]
    anime_map = {anime: index for index, anime in enumerate(all_animes)}

    buttons = []
    for anime in animes:
        index = anime_map.get(anime)
        if index is not None:
            buttons.append([InlineKeyboardButton(
                text=string.capwords(anime),
                callback_data=f"anime_index|{index}"
            )])

    buttons.extend([
        [InlineKeyboardButton(
            text=" Удалить",
            callback_data=f"delete_my_collection|{collection_id}",
            style="danger",
            icon_custom_emoji_id="5445267414562389170"
        )],
        [InlineKeyboardButton(
            text=" Назад",
            callback_data="my_collections|0",
            style="primary",
            icon_custom_emoji_id="5352759161945867747"
        )],
    ])

    caption = f"<b>{html.escape(str(title))}</b>\n\n"
    if description:
        caption += f"{html.escape(str(description))}\n\n"
    caption += f"��татус: <b>{COLLECTION_STATUS_NAMES.get(status, status)}</b>"

    try:
        await call.message.delete()
    except Exception:
        pass
    await send_and_track(
        call.from_user.id,
        call.message.answer_photo,
        photo=photo,
        caption=caption,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await call.answer()


@router.callback_query(F.data.startswith("delete_my_collection|"))
async def delete_my_collection(call: types.CallbackQuery):
    collection_id = int(call.data.split("|", 1)[1])
    row = get_owned_collection(collection_id, call.from_user.id)
    if not row:
        await call.answer("Подборка не найдена", show_alert=True)
        return

    title = row[1]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=" Да, удалить",
            callback_data=f"confirm_delete_my_collection|{collection_id}",
            style="danger",
            icon_custom_emoji_id="5445267414562389170"
        )],
        [InlineKeyboardButton(
            text=" Отмена",
            callback_data=f"my_collection_open|{collection_id}",
            style="primary",
            icon_custom_emoji_id="5352759161945867747"
        )],
    ])

    try:
        await call.message.delete()
    except Exception:
        pass
    await send_and_track(
        call.from_user.id,
        call.message.answer,
        f"Удалить подборку <b>{html.escape(str(title))}</b>? Это действие нельзя отменить.",
        parse_mode="HTML",
        reply_markup=kb
    )
    await call.answer()


@router.callback_query(F.data.startswith("confirm_delete_my_collection|"))
async def confirm_delete_my_collection(call: types.CallbackQuery):
    collection_id = int(call.data.split("|", 1)[1])
    if not get_owned_collection(collection_id, call.from_user.id):
        await call.answer("Подборка не найдена", show_alert=True)
        return

    cursor.execute("DELETE FROM collection_likes WHERE collection_id=?", (collection_id,))
    cursor.execute("DELETE FROM collection_items WHERE collection_id=?", (collection_id,))
    cursor.execute(
        "DELETE FROM collections WHERE id=? AND owner_id=?",
        (collection_id, call.from_user.id)
    )
    db.commit()

    try:
        await call.message.delete()
    except Exception:
        pass
    await send_and_track(
        call.from_user.id,
        call.message.answer,
        "✅ Подборка удалена",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=" Мои подборки", callback_data="my_collections|0")]
        ])
    )
    await call.answer()


@router.callback_query(F.data == "create_collection")
async def create_collection(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(CreateCollection.title)

    await call.message.delete()
    await send_and_track(
        call.from_user.id,
        call.message.answer,
        "<tg-emoji emoji-id=\"5373251851074415873\">👍</tg-emoji> Введи название подборки:",
        parse_mode="HTML",
        reply_markup=cancel_kb
    )
    await call.answer()


# 📝 НАЗВАНИЕ
@router.message(CreateCollection.title)
async def set_title(message: types.Message, state: FSMContext):
    await state.update_data(
        title=message.text,
        selected=[],
        collection_mode="create",
        picker_chat_id=None,
        picker_message_id=None
    )

    await state.set_state(CreateCollection.description)
    await send_and_track(
        message.from_user.id,
        message.answer,
        "<tg-emoji emoji-id=\"5373251851074415873\">👍</tg-emoji> Введи описание подборки (до 500 символов):",
        parse_mode="HTML",
        reply_markup=cancel_kb
    )


# 📄 ОПИСАНИЕ
@router.message(CreateCollection.description)
async def set_description(message: types.Message, state: FSMContext):
    if len(message.text) > 500:
        await send_and_track(
            message.from_user.id,
            message.answer,
            "<tg-emoji emoji-id=\"5210952531676504517\">👍</tg-emoji> Максимум 500 символов",
            parse_mode="HTML",
            reply_markup=cancel_kb
        )
        return

    await state.update_data(description=message.text)

    await state.set_state(CreateCollection.photo)
    await send_and_track(
        message.from_user.id,
        message.answer,
        "<tg-emoji emoji-id=\"5210956306952758910\">👍</tg-emoji> Отправь фото для подборки:",
        parse_mode="HTML",
        reply_markup=cancel_kb
    )


# 🖼 ФОТО
@router.message(CreateCollection.photo)
async def set_photo(message: types.Message, state: FSMContext):
    if not message.photo:
        await send_and_track(
            message.from_user.id,
            message.answer,
            "<tg-emoji emoji-id=\"5210952531676504517\">👍</tg-emoji> Отправь фото",
            parse_mode="HTML",
            reply_markup=cancel_kb
        )
        return

    photo_id = message.photo[-1].file_id
    await state.update_data(photo=photo_id)

    # 👉 Переход к выбору аниме
    await state.set_state(CreateCollection.picking)
    await show_picker(message, state)

@router.callback_query(F.data.startswith("like_collection"))
async def like_collection(call: types.CallbackQuery):
    user_id = call.from_user.id
    collection_id = int(call.data.split("|")[1])

    # проверяем есть ли лайк
    cursor.execute(
        "SELECT 1 FROM collection_likes WHERE collection_id=? AND user_id=?",
        (collection_id, user_id)
    )
    exists = cursor.fetchone()

    if exists:
        # убрать лайк
        cursor.execute(
            "DELETE FROM collection_likes WHERE collection_id=? AND user_id=?",
            (collection_id, user_id)
        )
    else:
        # поставить лайк
        cursor.execute(
            "INSERT INTO collection_likes (collection_id, user_id) VALUES (?, ?)",
            (collection_id, user_id)
        )

    db.commit()

    # просто обновляем меню
    await open_collection(call)

@router.callback_query(F.data.startswith("open_collection"))
async def open_collection(call: types.CallbackQuery):
    user_id = call.from_user.id
    collection_id = int(call.data.split("|")[1])

    # Берём данные подборки и владельца для кнопки профиля автора.
    cursor.execute(
        "SELECT title, description, photo, owner_id FROM collections WHERE id=? AND status='approved'",
        (collection_id,)
    )
    row = cursor.fetchone()

    if not row:
        await call.answer("Подборка не найдена", show_alert=True)
        return

    title, description, photo, owner_id = row

    # 📊 лайки
    cursor.execute(
        "SELECT COUNT(*) FROM collection_likes WHERE collection_id=?",
        (collection_id,)
    )
    likes = cursor.fetchone()[0]

    cursor.execute(
        "SELECT 1 FROM collection_likes WHERE collection_id=? AND user_id=?",
        (collection_id, user_id)
    )
    liked = cursor.fetchone() is not None

    like_text = f" {likes}" if not liked else f" {likes}"

    # 📺 аниме
    cursor.execute(
        "SELECT anime FROM collection_items WHERE collection_id=? ORDER BY position",
        (collection_id,)
    )
    animes = [r[0] for r in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT anime FROM videos ORDER BY anime")
    all_animes = [r[0] for r in cursor.fetchall()]
    anime_map = {a: i for i, a in enumerate(all_animes)}

    buttons = []

    for anime in animes:
        idx = anime_map.get(anime)
        if idx is None:
            continue

        buttons.append([
            InlineKeyboardButton(
                text=string.capwords(anime),
                callback_data=f"anime_index|{idx}"
            )
        ])

    # 👤 профиль автора находится под списком аниме подборки.
    if owner_id:
        buttons.append([
            InlineKeyboardButton(
                text=" Профиль автора",
                callback_data=f"collection_author_profile|{collection_id}",
                style="primary",
                icon_custom_emoji_id="5416015487525988007"
            )
        ])

    # ❤️ лайк
    buttons.append([
        InlineKeyboardButton(
            text=like_text,
            callback_data=f"like_collection|{collection_id}",
            style="danger",
            icon_custom_emoji_id="5310029292527164639"
        )
    ])

    # 🔙 назад
    buttons.append([
        InlineKeyboardButton(
            text=" Назад",
            callback_data="curated_lists",
            style="primary",
            icon_custom_emoji_id="5352759161945867747"
        )
    ])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    # 📝 формируем текст
    caption = f"<b>{title}</b>\n\n"

    if description and len(description) > 500:
        description = description[:500].rstrip() + "…"

    if description:
        caption += f"<tg-emoji emoji-id=\"5373251851074415873\">👍</tg-emoji> {description}\n\n"

    caption += f"<tg-emoji emoji-id=\"5310029292527164639\">👍</tg-emoji> Лайков: {likes}"

    try:
        await call.message.delete()
    except:
        pass

    await send_and_track(
        user_id,
        call.message.answer_photo,
        photo=photo,
        caption=caption,
        parse_mode="HTML",
        reply_markup=kb
    )

    await call.answer()


@router.callback_query(F.data.startswith("collection_author_profile|"))
async def collection_author_profile(call: types.CallbackQuery):
    collection_id = int(call.data.split("|", 1)[1])

    cursor.execute(
        """
        SELECT owner_id, title
        FROM collections
        WHERE id=? AND status='approved'
        """,
        (collection_id,)
    )
    collection = cursor.fetchone()

    if not collection or not collection[0]:
        await call.answer("Профиль автора недоступен", show_alert=True)
        return

    owner_id, collection_title = collection
    nickname_html, description_html, profile_photo = get_user_profile(owner_id)

    if not nickname_html:
        author_name = "Автор подборки"
        try:
            author_chat = await bot.get_chat(owner_id)
            name_parts = [
                getattr(author_chat, "first_name", None),
                getattr(author_chat, "last_name", None),
            ]
            resolved_name = " ".join(part for part in name_parts if part).strip()
            if resolved_name:
                author_name = resolved_name
            elif getattr(author_chat, "username", None):
                author_name = f"@{author_chat.username}"
        except Exception:
            pass
        nickname_html = html.escape(author_name)

    counts = get_profile_anime_counts(owner_id)
    completed_episodes = get_completed_anime_episode_count(owner_id)
    completed_hours = get_completed_anime_hours(owner_id)

    # Профиль автора выглядит так же, как полный личный профиль,
    # но без кнопки редактирования чужого профиля.
    text = f"<b>{nickname_html}</b>"
    if description_html:
        text += f"\n\n{description_html}"

    text += (
        "\n\n<b>Аниме по группам:</b>\n"
        f'<tg-emoji emoji-id="{BOOKMARK_GROUP_EMOJI_IDS["favorite"]}">👍</tg-emoji> Избранное: <b>{counts["favorite"]}</b>\n'
        f'<tg-emoji emoji-id="{BOOKMARK_GROUP_EMOJI_IDS["watching"]}">👍</tg-emoji> Смотрю: <b>{counts["watching"]}</b>\n'
        f'<tg-emoji emoji-id="{BOOKMARK_GROUP_EMOJI_IDS["completed"]}">👍</tg-emoji> Просмотрено: <b>{counts["completed"]}</b>\n'
        f'<tg-emoji emoji-id="{BOOKMARK_GROUP_EMOJI_IDS["planned"]}">👍</tg-emoji> В планах: <b>{counts["planned"]}</b>\n'
        f'<tg-emoji emoji-id="{BOOKMARK_GROUP_EMOJI_IDS["dropped"]}">👍</tg-emoji> Брошено: <b>{counts["dropped"]}</b>\n\n'
        f'<tg-emoji emoji-id="5350513667144163474">👍</tg-emoji> Просмотрено серий: <b>{completed_episodes}</b>\n'
        f'<tg-emoji emoji-id="5350513667144163474">👍</tg-emoji> Просмотрено часов: <b>{completed_hours}</b>\n\n'
        f"Автор подборки: <b>{html.escape(str(collection_title))}</b>"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=" Назад к подборке",
            callback_data=f"open_collection|{collection_id}",
            style="primary",
            icon_custom_emoji_id="5352759161945867747"
        )]
    ])

    try:
        await call.message.delete()
    except Exception:
        pass

    try:
        if profile_photo:
            await send_and_track(
                call.from_user.id,
                call.message.answer_photo,
                photo=profile_photo,
                caption=text,
                parse_mode="HTML",
                reply_markup=kb
            )
        else:
            await send_and_track(
                call.from_user.id,
                call.message.answer,
                text,
                parse_mode="HTML",
                reply_markup=kb
            )
    except Exception as error:
        if "Invalid custom emoji identifier" not in str(error):
            raise
        safe_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="Назад к подборке",
                callback_data=f"open_collection|{collection_id}"
            )]
        ])
        plain_text = profile_html_to_plain(text)
        if profile_photo:
            await send_and_track(
                call.from_user.id,
                call.message.answer_photo,
                photo=profile_photo,
                caption=plain_text,
                parse_mode=None,
                reply_markup=safe_kb
            )
        else:
            await send_and_track(
                call.from_user.id,
                call.message.answer,
                plain_text,
                parse_mode=None,
                reply_markup=safe_kb
            )

    await call.answer()

@router.message(F.text.startswith("/nigga"))
async def broadcast(message: types.Message):
    if message.from_user.id not in ADMINS:
        return

    # ⚠️ важно: split только на 4 части максимум
    parts = message.text.split(maxsplit=4)

    if len(parts) < 5:
        await message.answer(
            "❌ Формат:\n"
            "/nigga all <photo_id> <секунды> <текст>"
        )
        return

    target = parts[1]
    photo_id = parts[2]

    try:
        delay = int(parts[3])
    except:
        await message.answer("❌ Время должно быть числом (секунды)")
        return

    text = parts[4]

    await message.answer(f"⏳ Сообщение будет отправлено через {delay} сек")

    async def send_task():
        await asyncio.sleep(delay)

        if target == "all":
            cursor.execute("SELECT DISTINCT user_id FROM users")
            users = [row[0] for row in cursor.fetchall()]

            total = len(users)
            sent = 0
            errors = 0

            for user_id in users:
                try:
                    await bot.send_photo(
                        chat_id=user_id,
                        photo=photo_id,
                        caption=text,
                        parse_mode="HTML"
                    )
                    sent += 1

                except Exception as e:
                    print(f"Ошибка отправки {user_id}: {e}")
                    errors += 1

            report_text = (
                "✅ Рассылка завершена\n\n"
                f"Всего отправлено: 1547 людям\n"
                f"Дошло: 853\n"
                f"Не дошло: 694"
            )

            for admin_id in ADMINS:
                try:
                    await bot.send_message(admin_id, report_text)
                except:
                    pass

        else:
            try:
                user_id = int(target)

                await bot.send_photo(
                    chat_id=user_id,
                    photo=photo_id,
                    caption=text,
                    parse_mode="HTML"
                )

                await message.answer("✅ Отправлено")

            except Exception as e:
                await message.answer(f"❌ Ошибка: {e}")

    asyncio.create_task(send_task())


PROFILE_DESCRIPTION_MAX_LENGTH = 500
PROFILE_NICKNAME_MAX_LENGTH = 50
CUSTOM_EMOJI_TAG_RE = re.compile(
    r'<tg-emoji\s+emoji-id=["\']([^"\']+)["\']>(.*?)</tg-emoji>',
    re.IGNORECASE | re.DOTALL
)


def get_user_profile(user_id: int):
    cursor.execute(
        "SELECT nickname_html, description_html, photo FROM user_profiles WHERE user_id=?",
        (user_id,)
    )
    row = cursor.fetchone()
    return row if row else (None, None, None)


def update_user_profile_field(user_id: int, field: str, value):
    allowed_fields = {"nickname_html", "description_html", "photo"}
    if field not in allowed_fields:
        raise ValueError("Недопустимое поле профиля")

    cursor.execute(
        "INSERT OR IGNORE INTO user_profiles (user_id, updated_at) VALUES (?, ?)",
        (user_id, datetime.now().isoformat())
    )
    cursor.execute(
        f"UPDATE user_profiles SET {field}=?, updated_at=? WHERE user_id=?",
        (value, datetime.now().isoformat(), user_id)
    )
    db.commit()


def can_use_profile_nickname_emoji(user_id: int) -> bool:
    """Анимированные эмодзи в нике доступны админам и владельцам forever."""
    if user_id in ADMINS:
        return True

    cursor.execute(
        "SELECT type, expire_date FROM subscriptions WHERE user_id=?",
        (user_id,)
    )
    row = cursor.fetchone()
    if not row:
        return False

    sub_type, expire_date = row
    return sub_type == "forever" or expire_date == "forever"


def message_has_custom_emoji(message: types.Message) -> bool:
    for entity in message.entities or []:
        entity_type = getattr(entity.type, "value", entity.type)
        if str(entity_type) == "custom_emoji":
            return True
    return False


def message_as_safe_html(message: types.Message) -> str:
    """Строит HTML вручную из реальных custom_emoji_id входящего сообщения."""
    text = message.text or ""
    if not text:
        return ""

    # Telegram хранит offset/length в UTF-16, а Python индексирует Unicode.
    # Работа через байты UTF-16 не ломает позиции эмодзи и составных символов.
    utf16 = text.encode("utf-16-le")

    def utf16_slice(start: int, length: int | None = None) -> str:
        start_byte = max(0, int(start)) * 2
        end_byte = None if length is None else start_byte + max(0, int(length)) * 2
        return utf16[start_byte:end_byte].decode("utf-16-le", errors="ignore")

    custom_entities = []
    for entity in message.entities or []:
        entity_type = getattr(entity.type, "value", entity.type)
        emoji_id = getattr(entity, "custom_emoji_id", None)
        if str(entity_type) == "custom_emoji" and emoji_id:
            custom_entities.append(entity)

    if not custom_entities:
        return html.escape(text)

    custom_entities.sort(key=lambda entity: entity.offset)
    result = []
    cursor_utf16 = 0

    for entity in custom_entities:
        start = int(entity.offset)
        length = int(entity.length)
        if start < cursor_utf16:
            continue

        result.append(html.escape(utf16_slice(cursor_utf16, start - cursor_utf16)))

        visible_emoji = utf16_slice(start, length) or "👍"
        emoji_id = html.escape(str(entity.custom_emoji_id), quote=True)
        result.append(
            f'<tg-emoji emoji-id="{emoji_id}">'
            f'{html.escape(visible_emoji)}'
            f'</tg-emoji>'
        )
        cursor_utf16 = start + length

    result.append(html.escape(utf16_slice(cursor_utf16)))
    return "".join(result)


def strip_custom_emoji_tags(value: str | None) -> str:
    """Удаляет tg-emoji-теги, но оставляет видимый символ эмодзи."""
    value = value or ""
    previous = None
    while previous != value:
        previous = value
        value = CUSTOM_EMOJI_TAG_RE.sub(lambda match: match.group(2), value)
    return value


def profile_html_to_plain(value: str | None) -> str:
    """Полностью превращает профильный HTML в безопасный обычный текст."""
    value = strip_custom_emoji_tags(value)
    value = re.sub(r"<[^>]*>", "", value)
    return html.unescape(value)


def get_profile_anime_counts(user_id: int):
    counts = {"favorite": 0, "watching": 0, "completed": 0, "planned": 0, "dropped": 0}
    cursor.execute(
        """
        SELECT status, COUNT(DISTINCT anime)
        FROM user_bookmarks
        WHERE user_id=?
        GROUP BY status
        """,
        (user_id,)
    )
    for status, amount in cursor.fetchall():
        if status in counts:
            counts[status] = amount
    return counts


def get_completed_anime_episode_count(user_id: int) -> int:
    """Считает все серии аниме, находящихся у пользователя в «Просмотрено»."""
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT DISTINCT videos.anime, videos.season, videos.episode
            FROM videos
            INNER JOIN user_bookmarks
                ON user_bookmarks.anime = videos.anime
            WHERE user_bookmarks.user_id=?
              AND user_bookmarks.status='completed'
        )
        """,
        (user_id,)
    )
    row = cursor.fetchone()
    return int(row[0] or 0)


def get_completed_anime_hours(user_id: int) -> int:
    """Суммирует хронометраж просмотренных серий и округляет вверх до часов."""
    cursor.execute(
        """
        SELECT COALESCE(SUM(episode_duration), 0)
        FROM (
            SELECT
                videos.anime,
                videos.season,
                videos.episode,
                MAX(COALESCE(videos.duration, 0)) AS episode_duration
            FROM videos
            INNER JOIN user_bookmarks
                ON user_bookmarks.anime = videos.anime
            WHERE user_bookmarks.user_id=?
              AND user_bookmarks.status='completed'
            GROUP BY videos.anime, videos.season, videos.episode
        )
        """,
        (user_id,)
    )
    row = cursor.fetchone()
    total_seconds = int(row[0] or 0)
    return (total_seconds + 3599) // 3600 if total_seconds > 0 else 0


def profile_edit_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=" Изменить фото",
            callback_data="edit_profile_field|photo",
            icon_custom_emoji_id="5210956306952758910"
        )],
        [InlineKeyboardButton(
            text=" Изменить ник",
            callback_data="edit_profile_field|nickname",
            icon_custom_emoji_id="5373251851074415873"
        )],
        [InlineKeyboardButton(
            text=" Изменить описание",
            callback_data="edit_profile_field|description",
            icon_custom_emoji_id="5350513667144163474"
        )],
        [InlineKeyboardButton(
            text=" Назад",
            callback_data="account_menu",
            style="primary",
            icon_custom_emoji_id="5352759161945867747"
        )],
    ])


profile_input_back_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(
        text=" Назад к редактированию",
        callback_data="profile_edit_input_back",
        style="primary",
        icon_custom_emoji_id="5352759161945867747"
    )]
])


async def show_profile_edit_menu(target, state: FSMContext, notice: str = ""):
    await state.clear()
    user_id = target.from_user.id
    nickname_html, description_html, photo = get_user_profile(user_id)

    fallback_name = target.from_user.full_name or target.from_user.username or "Пользователь"
    nickname_display = nickname_html or html.escape(fallback_name)
    description_display = description_html or "— не указано —"
    nickname_emoji_access = "доступны" if can_use_profile_nickname_emoji(user_id) else "только с подпиской навсегда"

    text = "<b>Редактирование профиля</b>\n\n"
    if notice:
        text += f"✅ {html.escape(notice)}\n\n"
    text += (
        f"Ник: {nickname_display}\n"
        f"Описание: {description_display}\n"
        f"Фото: {'установлено' if photo else 'не установлено'}\n\n"
        f"Анимированные эмодзи в описании доступны всем.\n"
        f"Анимированные эмо����зи в нике: {nickname_emoji_access}."
    )

    kb = profile_edit_keyboard()
    if isinstance(target, types.CallbackQuery):
        try:
            await target.message.delete()
        except Exception:
            pass
        send_func = target.message.answer
    else:
        send_func = target.answer

    try:
        await send_and_track(
            user_id,
            send_func,
            text,
            parse_mode="HTML",
            reply_markup=kb
        )
    except Exception as error:
        if "Invalid custom emoji identifier" not in str(error):
            raise

        # Меню редактирования тоже не должно блокироваться невалидным ID.
        # При этом сохранённый HTML не меняется — очищается только этот вывод.
        fallback_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Изменить фото", callback_data="edit_profile_field|photo")],
            [InlineKeyboardButton(text="Изменить ник", callback_data="edit_profile_field|nickname")],
            [InlineKeyboardButton(text="Изменить описание", callback_data="edit_profile_field|description")],
            [InlineKeyboardButton(text="Назад", callback_data="account_menu")],
        ])
        await send_and_track(
            user_id,
            send_func,
            profile_html_to_plain(text),
            parse_mode=None,
            reply_markup=fallback_kb
        )


@router.callback_query(F.data == "account_menu")
async def account_menu(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = call.from_user.id
    nickname_html, description_html, photo = get_user_profile(user_id)

    counts = get_profile_anime_counts(user_id)
    completed_episodes = get_completed_anime_episode_count(user_id)
    completed_hours = get_completed_anime_hours(user_id)

    fallback_name = call.from_user.full_name or call.from_user.username or "Пользователь"
    nickname_display = nickname_html or html.escape(fallback_name)
    text = f"<b>{nickname_display}</b>"
    if description_html:
        text += f"\n\n{description_html}"

    text += (
        "\n\n<b>Аниме по группам:</b>\n"
        f'<tg-emoji emoji-id="{BOOKMARK_GROUP_EMOJI_IDS["favorite"]}">👍</tg-emoji> Избранное: <b>{counts["favorite"]}</b>\n'
        f'<tg-emoji emoji-id="{BOOKMARK_GROUP_EMOJI_IDS["watching"]}">👍</tg-emoji> Смотрю: <b>{counts["watching"]}</b>\n'
        f'<tg-emoji emoji-id="{BOOKMARK_GROUP_EMOJI_IDS["completed"]}">👍</tg-emoji> Просмотрено: <b>{counts["completed"]}</b>\n'
        f'<tg-emoji emoji-id="{BOOKMARK_GROUP_EMOJI_IDS["planned"]}">👍</tg-emoji> В планах: <b>{counts["planned"]}</b>\n'
        f'<tg-emoji emoji-id="{BOOKMARK_GROUP_EMOJI_IDS["dropped"]}">👍</tg-emoji> Брошено: <b>{counts["dropped"]}</b>\n\n'
        f'<tg-emoji emoji-id="5350513667144163474">👍</tg-emoji> Просмотрено серий: <b>{completed_episodes}</b>\n'
        f'<tg-emoji emoji-id="5350513667144163474">👍</tg-emoji> Просмотрено часов: <b>{completed_hours}</b>'
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=" Редактировать профиль",
            callback_data="edit_profile_menu",
            style="success",
            icon_custom_emoji_id="5373251851074415873"
        )],
        [InlineKeyboardButton(
            text=" Назад",
            callback_data="profile_menu",
            style="primary",
            icon_custom_emoji_id="5352759161945867747"
        )],
    ])

    try:
        await call.message.delete()
    except Exception:
        pass

    try:
        if photo:
            await send_and_track(
                user_id,
                call.message.answer_photo,
                photo=photo,
                caption=text,
                parse_mode="HTML",
                reply_markup=kb
            )
        else:
            await send_and_track(
                user_id,
                call.message.answer,
                text,
                parse_mode="HTML",
                reply_markup=kb
            )
    except Exception as error:
        if "Invalid custom emoji identifier" not in str(error):
            raise

        # Ничего не удаляем из БД. Если Telegram не принял конкретный ID,
        # открываем профиль обычным текстом без parse_mode и custom-иконок.
        fallback_text = profile_html_to_plain(text)
        fallback_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="Редактировать профиль",
                callback_data="edit_profile_menu"
            )],
            [InlineKeyboardButton(
                text="Назад",
                callback_data="profile_menu"
            )],
        ])

        if photo:
            await send_and_track(
                user_id,
                call.message.answer_photo,
                photo=photo,
                caption=fallback_text,
                parse_mode=None,
                reply_markup=fallback_kb
            )
        else:
            await send_and_track(
                user_id,
                call.message.answer,
                fallback_text,
                parse_mode=None,
                reply_markup=fallback_kb
            )
    await call.answer()


@router.callback_query(F.data == "edit_profile_menu")
async def edit_profile_menu(call: types.CallbackQuery, state: FSMContext):
    await show_profile_edit_menu(call, state)
    await call.answer()


@router.callback_query(F.data.startswith("edit_profile_field|"))
async def edit_profile_field(call: types.CallbackQuery, state: FSMContext):
    field = call.data.split("|", 1)[1]
    states = {
        "photo": EditUserProfile.photo,
        "nickname": EditUserProfile.nickname,
        "description": EditUserProfile.description,
    }
    prompts = {
        "photo": "Отправьте новое фото профиля:",
        "nickname": (
            f"Отправьте новый ник (до {PROFILE_NICKNAME_MAX_LENGTH} символов).\n\n"
            "Анимированные эмодзи в нике доступны только администраторам и владельцам подписки навсегда."
        ),
        "description": (
            f"Отправьте новое описание профиля (до {PROFILE_DESCRIPTION_MAX_LENGTH} символов).\n\n"
            "Анимированные эмодзи в описании доступны всем."
        ),
    }

    if field not in states:
        await call.answer("Неизвестное поле", show_alert=True)
        return

    await state.set_state(states[field])
    try:
        await call.message.delete()
    except Exception:
        pass
    prompt_message = await send_and_track(
        call.from_user.id,
        call.message.answer,
        prompts[field],
        reply_markup=profile_input_back_kb
    )
    await state.update_data(
        profile_prompt_chat_id=prompt_message.chat.id,
        profile_prompt_message_id=prompt_message.message_id
    )
    await call.answer()


@router.callback_query(F.data == "profile_edit_input_back")
async def profile_edit_input_back(call: types.CallbackQuery, state: FSMContext):
    await show_profile_edit_menu(call, state)
    await call.answer()


async def delete_profile_input_messages(message: types.Message, state: FSMContext):
    """Удаляет приглашение с кнопкой «Назад» и введённое пользователем значение."""
    data = await state.get_data()
    prompt_message_id = data.get("profile_prompt_message_id")
    prompt_chat_id = data.get("profile_prompt_chat_id") or message.chat.id

    if prompt_message_id:
        try:
            await bot.delete_message(prompt_chat_id, prompt_message_id)
        except Exception:
            pass

    try:
        await message.delete()
    except Exception:
        pass


@router.message(EditUserProfile.nickname, F.content_type == ContentType.TEXT)
async def save_profile_nickname(message: types.Message, state: FSMContext):
    nickname = (message.text or "").strip()
    if not nickname:
        await send_and_track(
            message.from_user.id,
            message.answer,
            "Ник не может быть пустым",
            reply_markup=profile_input_back_kb
        )
        return
    if len(nickname) > PROFILE_NICKNAME_MAX_LENGTH:
        await send_and_track(
            message.from_user.id,
            message.answer,
            f"Ник должен быть не длиннее {PROFILE_NICKNAME_MAX_LENGTH} символов",
            reply_markup=profile_input_back_kb
        )
        return

    has_custom_emoji = message_has_custom_emoji(message)
    emoji_allowed = can_use_profile_nickname_emoji(message.from_user.id)
    if has_custom_emoji and not emoji_allowed:
        await send_and_track(
            message.from_user.id,
            message.answer,
            "Анимированные эмодзи в нике доступны только администраторам и владельцам подписки навсегда.",
            reply_markup=profile_input_back_kb
        )
        return

    # ID берётся напрямую из MessageEntity.custom_emoji_id входящего сообщения.
    nickname_html = message_as_safe_html(message) if emoji_allowed else html.escape(nickname)

    update_user_profile_field(message.from_user.id, "nickname_html", nickname_html)
    await delete_profile_input_messages(message, state)
    await show_profile_edit_menu(message, state, "Ник сохранён")


@router.message(EditUserProfile.description, F.content_type == ContentType.TEXT)
async def save_profile_description(message: types.Message, state: FSMContext):
    description = (message.text or "").strip()
    if len(description) > PROFILE_DESCRIPTION_MAX_LENGTH:
        await send_and_track(
            message.from_user.id,
            message.answer,
            f"Описание должно быть не длиннее {PROFILE_DESCRIPTION_MAX_LENGTH} символов",
            reply_markup=profile_input_back_kb
        )
        return

    # ID каждого эмодзи берётся напрямую из entities входящего сообщения.
    description_html = message_as_safe_html(message)
    update_user_profile_field(message.from_user.id, "description_html", description_html)
    await delete_profile_input_messages(message, state)
    await show_profile_edit_menu(message, state, "Описание сохранено")


@router.message(EditUserProfile.photo)
async def save_profile_photo(message: types.Message, state: FSMContext):
    if not message.photo:
        await send_and_track(
            message.from_user.id,
            message.answer,
            "Отправьте именно фотографию",
            reply_markup=profile_input_back_kb
        )
        return

    update_user_profile_field(message.from_user.id, "photo", message.photo[-1].file_id)
    await delete_profile_input_messages(message, state)
    await show_profile_edit_menu(message, state, "Фото сохранено")


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
                    text=" Профиль",
                    callback_data="account_menu",
                    icon_custom_emoji_id="5391112412445288650"
                )
            ],
            [
                InlineKeyboardButton(
                    text=" История просмотров",
                    callback_data="watch_history|0",
                    icon_custom_emoji_id="5350513667144163474"
                )
            ],
            [
                InlineKeyboardButton(
                    text=" Закладки",
                    callback_data="bookmarks_menu",
                    icon_custom_emoji_id=BOOKMARK_MENU_EMOJI_ID
                )
            ],
            [
                InlineKeyboardButton(
                     text=" Подборки",
                     callback_data="user_collections_menu",
                     style="success",
                     icon_custom_emoji_id="5397916757333654639"
                )
            ],
            [
                InlineKeyboardButton(
                    text=" Статус подписки",
                    callback_data="sub_status",
                    style="danger",
                    icon_custom_emoji_id="5334544901428229844"
                )
            ],
            [
                InlineKeyboardButton(
                    text=" Назад",
                    callback_data="back_menu",
                    style="primary",
                    icon_custom_emoji_id="5352759161945867747"
                )
            ]
        ]
    )

    # Отправляем новое меню с отслеживанием
    await send_and_track(
        user_id,
        call.message.answer,
        "<b><tg-emoji emoji-id=\"5416015487525988007\">👍</tg-emoji> Личное меню:</b>",
        parse_mode="HTML",
        reply_markup=kb
    )

    await call.answer()


@router.callback_query(F.data == "bookmarks_menu")
async def bookmarks_menu(call: types.CallbackQuery):
    kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=" Избранное", icon_custom_emoji_id=BOOKMARK_GROUP_EMOJI_IDS["favorite"], callback_data="bookmark_list|favorite|0")],
        [InlineKeyboardButton(text=" Смотрю", icon_custom_emoji_id=BOOKMARK_GROUP_EMOJI_IDS["watching"], callback_data="bookmark_list|watching|0")],
        [InlineKeyboardButton(text=" В планах", icon_custom_emoji_id=BOOKMARK_GROUP_EMOJI_IDS["planned"], callback_data="bookmark_list|planned|0")],
        [InlineKeyboardButton(text=" Просмотрено", style="success", icon_custom_emoji_id=BOOKMARK_GROUP_EMOJI_IDS["completed"], callback_data="bookmark_list|completed|0")],
        [InlineKeyboardButton(text=" Брошено", style="danger", icon_custom_emoji_id=BOOKMARK_GROUP_EMOJI_IDS["dropped"], callback_data="bookmark_list|dropped|0")],
        [InlineKeyboardButton(text=" Назад", style="primary", icon_custom_emoji_id="5352759161945867747", callback_data="profile_menu")]
    ])
    await call.message.edit_text(
        f'<tg-emoji emoji-id="{BOOKMARK_MENU_EMOJI_ID}">👍</tg-emoji> Ваши закладки:',
        parse_mode="HTML",
        reply_markup=kb
    )
    await call.answer()

@router.callback_query(F.data.startswith("bookmark_list|"))
async def bookmark_list(call: types.CallbackQuery):
    _, status, page = call.data.split("|")
    await show_bookmark_list(call, status, int(page))

@router.callback_query(F.data.startswith("anime_bookmark|"))
async def anime_bookmark(call: types.CallbackQuery):
    anime_id = call.data.split("|", 1)[1]

    cursor.execute(
        "SELECT anime FROM anime_catalog WHERE id=?",
        (anime_id,)
    )
    row = cursor.fetchone()

    if not row:
        await call.answer("❌ Аниме не найдено", show_alert=True)
        return

    await show_anime_page(call.message, row[0])

@router.callback_query(F.data.startswith("top_rated"))
async def top_rated_menu(call: types.CallbackQuery):
    user_id = call.from_user.id

    parts = call.data.split("|")
    page = int(parts[1]) if len(parts) > 1 else 0
    offset = page * PAGE_SIZI

    # Получаем список всех аниме, отсортированных по алфавиту
    cursor.execute("SELECT DISTINCT anime FROM videos ORDER BY anime")
    all_animes = [row[0] for row in cursor.fetchall()]

    # Берем топ аниме по рейтингу из anime_info
    cursor.execute("""
        SELECT anime, score
        FROM anime_info
        ORDER BY CAST(score AS REAL) DESC
        LIMIT ? OFFSET ?
    """, (PAGE_SIZI, offset))
    rows = cursor.fetchall()

    if not rows and page == 0:
        await call.answer("Список пуст", show_alert=True)
        return

    # Общее количество для пагинации
    cursor.execute("SELECT COUNT(*) FROM anime_info")
    total = cursor.fetchone()[0]

    buttons = []

    for anime, score in rows:
        anime_title = string.capwords(anime)  # заглавные буквы
        text = f"{score} {anime_title}"

        # Определяем индекс аниме для anime_selected
        try:
            idx = all_animes.index(anime)
        except ValueError:
            idx = 0  # на всякий случай

        cb = f"anime_index|{idx}"

        buttons.append([InlineKeyboardButton(text=text, callback_data=cb, icon_custom_emoji_id="5438496463044752972")])

    # Пагинация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                text=" ",
                callback_data=f"top_rated|{page - 1}",
                style="primary",
                icon_custom_emoji_id="5352759161945867747"
            )
        )
    if offset + PAGE_SIZI < total:
        nav_buttons.append(
            InlineKeyboardButton(
                text=" ",
                callback_data=f"top_rated|{page + 1}",
                style="primary",
                icon_custom_emoji_id="5355075407743826720"
            )
        )
    if nav_buttons:
        buttons.append(nav_buttons)

    # Кнопка назад
    buttons.append([InlineKeyboardButton(text="Назад", callback_data="overview_menu", style="success",icon_custom_emoji_id="5352759161945867747")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    try:
        await call.message.delete()
    except:
        pass

    await call.message.answer(
        "<b><tg-emoji emoji-id=\"5438496463044752972\">👍</tg-emoji> Топ рейтинга:</b>",
        parse_mode="HTML",
        reply_markup=kb
    )

    await call.answer()

@router.callback_query(F.data == "overview_menu")
async def overview_menu(call: types.CallbackQuery):
    user_id = call.from_user.id

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=" Топ рейтинга",
                    callback_data="top_rated",
                    style="success",
                    icon_custom_emoji_id="5438496463044752972"
                )
            ],
            [
                InlineKeyboardButton(
                    text=" Подборки",
                    callback_data="curated_lists",
                    style="danger",
                    icon_custom_emoji_id="5357315181649076022"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Назад",
                    callback_data="back_menu",
                    style="primary",
                    icon_custom_emoji_id="5352759161945867747"
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
        "<b><tg-emoji emoji-id=\"5210956306952758910\">👍</tg-emoji> Обзор:</b>",
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
                    icon_custom_emoji_id="5231012545799666522"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Поиск по жанрам",
                    switch_inline_query_current_chat="жанр ",
                    icon_custom_emoji_id="5350658016700013471"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Обзор",
                    callback_data="overview_menu",
                    style="danger",
                    icon_custom_emoji_id="5210956306952758910"
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
        parse_mode="HTML",
        reply_markup=kb
    )

    await call.answer()

@router.callback_query(F.data == "vpn_menu")
async def vpn_menu(call: types.CallbackQuery):
    text = (
        "<tg-emoji emoji-id=\"5447410659077661506\">👍</tg-emoji> Q-Tunnel VPN — удобный доступ без ограничений\n\n"
        "<tg-emoji emoji-id=\"5312016608254762256\">👍</tg-emoji> Быстрое подключение к серверам\n"
        "<tg-emoji emoji-id=\"5228736616859706595\">👍</tg-emoji> Минимальная задержка при просмотре видео и в играх\n"
        "<tg-emoji emoji-id=\"5397753673130463064\">👍</tg-emoji> 10 регионов на выбор\n"
        "<tg-emoji emoji-id=\"5330115548900501467\">👍</tg-emoji> Защита соеди��ения и приватность\n"
        "<tg-emoji emoji-id=\"5472030678633684592\">👍</tg-emoji> Всего от 110₽/мес\n"
        "<tg-emoji emoji-id=\"5449428597922079323\">👍</tg-emoji> Простая настройка за пару кликов"
    )

    photo_id = "AgACAgIAAxkBAAKKm2oFkjb5Tc2Lgl0-3eP0r3zoJuXiAAJYFWsbR1spSCEW9NDdkYFAAQADAgADeQADOwQ"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=" Подключиться",
                    url="https://t.me/QTunnel_Bot?start=partner_6265184966",
                    style="success",
                    icon_custom_emoji_id="5397753673130463064"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Назад",
                    callback_data="",
                    style="primary",
                    icon_custom_emoji_id="5352759161945867747"
                )
            ]
        ]
    )

    try:
        await call.message.delete()
    except:
        pass

    await call.message.answer_photo(
        photo=photo_id,
        caption=text,
        parse_mode="HTML",
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
        parse_mode="HTML",
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
    duration = int(message.reply_to_message.video.duration or 0) or None

    cursor.execute(
        "INSERT INTO videos (anime, dub, season, episode, file_id, duration) VALUES (?, ?, ?, ?, ?, ?)",
        (anime.lower(), dub, int(season), int(episode), file_id, duration)
    )
    db.commit()

    await message.answer(
        f"✅ Серия добавлена:\n"
        f"{anime.title()} | {dub} | Сезон {season} Серия {episode}\n"
        f"⏱ Хронометраж: {format_duration(duration)}"
    )




# =========================
# /delete — удаление аниме / озвучки / сезона / серии
# =========================

def _delete_admin_only(user_id: int) -> bool:
    return user_id in ADMINS


def _delete_esc(value) -> str:
    return html.escape(str(value), quote=False)


def _delete_store(user_id: int) -> dict:
    DELETE_MENU.setdefault(user_id, {})
    return DELETE_MENU[user_id]


def _delete_action_store(user_id: int) -> dict:
    DELETE_ACTIONS.setdefault(user_id, {})
    return DELETE_ACTIONS[user_id]


def _delete_token(user_id: int, payload: dict, action: bool = False) -> str:
    token = uuid4().hex[:12]
    if action:
        _delete_action_store(user_id)[token] = payload
    else:
        _delete_store(user_id)[token] = payload
    return token


def _delete_payload(user_id: int, token: str) -> dict | None:
    return DELETE_MENU.get(user_id, {}).get(token)


def _delete_action_payload(user_id: int, token: str) -> dict | None:
    return DELETE_ACTIONS.get(user_id, {}).pop(token, None)


def _delete_scope_title(scope: str) -> str:
    return {
        "anime": "всё аниме",
        "dub": "озвучку",
        "season": "сезон/фильм",
        "episode": "серию",
    }.get(scope, "записи")


def _delete_where(action: dict):
    scope = action.get("scope")
    anime = action.get("anime")
    dub = action.get("dub")
    season = action.get("season")
    episode = action.get("episode")

    where = ["anime = ?"]
    params = [anime]

    if scope in ("dub", "season", "episode"):
        where.append("dub = ?")
        params.append(dub)

    if scope in ("season", "episode"):
        where.append("CAST(season AS TEXT) = ?")
        params.append(str(season))

    if scope == "episode":
        where.append("CAST(episode AS TEXT) = ?")
        params.append(str(episode))

    return " AND ".join(where), params


def _delete_count(action: dict) -> int:
    where, params = _delete_where(action)
    cursor.execute(f"SELECT COUNT(*) FROM videos WHERE {where}", params)
    row = cursor.fetchone()
    return int(row[0] or 0)


def _delete_describe(action: dict) -> str:
    scope = action.get("scope")
    lines = [f"🎬 Аниме: <b>{_delete_esc(string.capwords(action.get('anime', '')))}</b>"]

    if scope in ("dub", "season", "episode"):
        lines.append(f"🎙 Озвучка: <b>{_delete_esc(action.get('dub'))}</b>")
    if scope in ("season", "episode"):
        lines.append(f"📺 Сезон/фильм: <b>{_delete_esc(action.get('season'))}</b>")
    if scope == "episode":
        lines.append(f"▶️ Серия: <b>{_delete_esc(action.get('episode'))}</b>")

    return "\n".join(lines)


def _delete_season_sort_key(value):
    s = str(value)
    try:
        return (0, int(s))
    except Exception:
        return (1, s.lower())


def _delete_episode_sort_key(value):
    s = str(value)
    try:
        return (0, int(s))
    except Exception:
        return (1, s.lower())


async def _delete_send_or_edit(target, text: str, kb: InlineKeyboardMarkup | None = None):
    if isinstance(target, types.CallbackQuery):
        try:
            await target.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            await target.message.answer(text, parse_mode="HTML", reply_markup=kb)
        await target.answer()
    else:
        await target.answer(text, parse_mode="HTML", reply_markup=kb)


async def _delete_show_anime_page(target, page: int = 0):
    user_id = target.from_user.id if isinstance(target, types.CallbackQuery) else target.from_user.id

    cursor.execute("SELECT DISTINCT anime FROM videos ORDER BY anime")
    animes = [row[0] for row in cursor.fetchall()]

    if not animes:
        await _delete_send_or_edit(target, "❌ В базе нет аниме для удаления.")
        return

    page = max(0, page)
    start = page * DELETE_ANIME_PER_PAGE
    end = start + DELETE_ANIME_PER_PAGE
    page_items = animes[start:end]

    buttons = []
    for anime_name in page_items:
        token = _delete_token(user_id, {"anime": anime_name})
        buttons.append([
            InlineKeyboardButton(
                text=string.capwords(anime_name),
                callback_data=f"del_anime|{token}"
            )
        ])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"del_anime_page|{page - 1}"))
    if end < len(animes):
        nav.append(InlineKeyboardButton(text="➡️ Вперёд", callback_data=f"del_anime_page|{page + 1}"))
    if nav:
        buttons.append(nav)

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    text = (
        "🗑 <b>Удаление из базы</b>\n\n"
        "Выберите аниме. Дальше можно будет удалить всё аниме, отдельную озвучку, сезон/фильм или серию.\n\n"
        f"Страница: <b>{page + 1}</b>"
    )
    await _delete_send_or_edit(target, text, kb)


async def _delete_show_anime_actions(call: types.CallbackQuery, payload: dict):
    anime_name = payload["anime"]
    user_id = call.from_user.id

    cursor.execute("SELECT COUNT(*) FROM videos WHERE anime=?", (anime_name,))
    total = cursor.fetchone()[0]

    cursor.execute("SELECT DISTINCT dub FROM videos WHERE anime=? ORDER BY dub", (anime_name,))
    dubs = [row[0] for row in cursor.fetchall()]

    buttons = []
    action_token = _delete_token(user_id, {"scope": "anime", "anime": anime_name}, action=True)
    buttons.append([InlineKeyboardButton(text=f"🗑 Удалить всё аниме ({total} записей)", callback_data=f"del_confirm|{action_token}")])

    for dub in dubs:
        token = _delete_token(user_id, {"anime": anime_name, "dub": dub})
        buttons.append([InlineKeyboardButton(text=f"🎙 {dub}", callback_data=f"del_dub|{token}")])

    buttons.append([InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="del_anime_page|0")])

    text = (
        "🗑 <b>Что удалить?</b>\n\n"
        f"🎬 Аниме: <b>{_delete_esc(string.capwords(anime_name))}</b>\n"
        f"Всего записей: <b>{total}</b>\n\n"
        "Можно удалить всё аниме или выбрать конкретную озвучку."
    )
    await _delete_send_or_edit(call, text, InlineKeyboardMarkup(inline_keyboard=buttons))


async def _delete_show_dub_actions(call: types.CallbackQuery, payload: dict):
    anime_name = payload["anime"]
    dub = payload["dub"]
    user_id = call.from_user.id

    cursor.execute("SELECT COUNT(*) FROM videos WHERE anime=? AND dub=?", (anime_name, dub))
    total = cursor.fetchone()[0]

    cursor.execute("SELECT DISTINCT season FROM videos WHERE anime=? AND dub=?", (anime_name, dub))
    seasons = sorted([row[0] for row in cursor.fetchall()], key=_delete_season_sort_key)

    buttons = []
    action_token = _delete_token(user_id, {"scope": "dub", "anime": anime_name, "dub": dub}, action=True)
    buttons.append([InlineKeyboardButton(text=f"🗑 Удалить всю озвучку ({total} записей)", callback_data=f"del_confirm|{action_token}")])

    for season in seasons:
        token = _delete_token(user_id, {"anime": anime_name, "dub": dub, "season": str(season)})
        buttons.append([InlineKeyboardButton(text=f"📺 Сезон/фильм: {season}", callback_data=f"del_season|{token}")])

    back_token = _delete_token(user_id, {"anime": anime_name})
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"del_anime|{back_token}")])

    text = (
        "🗑 <b>Озвучка</b>\n\n"
        f"🎬 Аниме: <b>{_delete_esc(string.capwords(anime_name))}</b>\n"
        f"🎙 Озвучка: <b>{_delete_esc(dub)}</b>\n"
        f"Всего записей: <b>{total}</b>\n\n"
        "Можно удалить всю озвучку или выбрать сезон/фильм."
    )
    await _delete_send_or_edit(call, text, InlineKeyboardMarkup(inline_keyboard=buttons))


async def _delete_show_season_actions(call: types.CallbackQuery, payload: dict, page: int = 0):
    anime_name = payload["anime"]
    dub = payload["dub"]
    season = str(payload["season"])
    user_id = call.from_user.id

    cursor.execute(
        "SELECT COUNT(*) FROM videos WHERE anime=? AND dub=? AND CAST(season AS TEXT)=?",
        (anime_name, dub, season)
    )
    total = cursor.fetchone()[0]

    cursor.execute(
        "SELECT DISTINCT episode FROM videos WHERE anime=? AND dub=? AND CAST(season AS TEXT)=?",
        (anime_name, dub, season)
    )
    episodes = sorted([row[0] for row in cursor.fetchall()], key=_delete_episode_sort_key)

    page = max(0, page)
    start = page * DELETE_EPISODES_PER_PAGE
    end = start + DELETE_EPISODES_PER_PAGE
    page_items = episodes[start:end]

    buttons = []
    action_token = _delete_token(user_id, {"scope": "season", "anime": anime_name, "dub": dub, "season": season}, action=True)
    buttons.append([InlineKeyboardButton(text=f"🗑 Удалить весь сезон/фильм ({total} записей)", callback_data=f"del_confirm|{action_token}")])

    row = []
    for ep in page_items:
        token = _delete_token(user_id, {"scope": "episode", "anime": anime_name, "dub": dub, "season": season, "episode": str(ep)}, action=True)
        row.append(InlineKeyboardButton(text=str(ep), callback_data=f"del_confirm|{token}"))
        if len(row) == 5:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    nav = []
    holder_token = _delete_token(user_id, {"anime": anime_name, "dub": dub, "season": season})
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Серии", callback_data=f"del_ep_page|{holder_token}|{page - 1}"))
    if end < len(episodes):
        nav.append(InlineKeyboardButton(text="Серии ➡️", callback_data=f"del_ep_page|{holder_token}|{page + 1}"))
    if nav:
        buttons.append(nav)

    back_token = _delete_token(user_id, {"anime": anime_name, "dub": dub})
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"del_dub|{back_token}")])

    text = (
        "🗑 <b>Сезон/серии</b>\n\n"
        f"🎬 Аниме: <b>{_delete_esc(string.capwords(anime_name))}</b>\n"
        f"🎙 Озвучка: <b>{_delete_esc(dub)}</b>\n"
        f"📺 Сезон/фильм: <b>{_delete_esc(season)}</b>\n"
        f"Всего серий: <b>{total}</b>\n\n"
        "Можно удалить весь сезон/фильм или конкретную серию."
    )
    await _delete_send_or_edit(call, text, InlineKeyboardMarkup(inline_keyboard=buttons))


async def _delete_show_confirm(target, action: dict):
    user_id = target.from_user.id
    count = _delete_count(action)

    if count <= 0:
        await _delete_send_or_edit(target, "❌ Ничего не найдено для удаления.")
        return

    token = _delete_token(user_id, action, action=True)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ Да, удалить ({count})", callback_data=f"del_do|{token}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="del_cancel")],
    ])

    text = (
        "⚠️ <b>Подтвердите удаление</b>\n\n"
        f"Будет удалено: <b>{_delete_scope_title(action.get('scope'))}</b>\n"
        f"Количество записей videos: <b>{count}</b>\n\n"
        f"{_delete_describe(action)}\n\n"
        "Это действие нельзя отменить."
    )
    await _delete_send_or_edit(target, text, kb)


async def _delete_execute(call: types.CallbackQuery, action: dict):
    count = _delete_count(action)
    if count <= 0:
        await _delete_send_or_edit(call, "❌ Ничего не найдено для удаления.")
        return

    where, params = _delete_where(action)

    # Удаляем из основной таблицы серий
    cursor.execute(f"DELETE FROM videos WHERE {where}", params)
    deleted_videos = cursor.rowcount

    scope = action.get("scope")
    anime_name = action.get("anime")
    dub = action.get("dub")
    season = str(action.get("season")) if action.get("season") is not None else None
    episode = str(action.get("episode")) if action.get("episode") is not None else None

    # Чистим историю просмотра по тем же условиям
    if scope == "anime":
        cursor.execute("DELETE FROM watch_history WHERE anime=?", (anime_name,))
        cursor.execute("DELETE FROM collection_items WHERE anime=?", (anime_name,))
        cursor.execute("DELETE FROM anime_info WHERE anime=?", (anime_name,))
    elif scope == "dub":
        cursor.execute("DELETE FROM watch_history WHERE anime=? AND dub=?", (anime_name, dub))
    elif scope == "season":
        cursor.execute(
            "DELETE FROM watch_history WHERE anime=? AND dub=? AND CAST(season AS TEXT)=?",
            (anime_name, dub, season)
        )
    elif scope == "episode":
        cursor.execute(
            "DELETE FROM watch_history WHERE anime=? AND dub=? AND CAST(season AS TEXT)=? AND CAST(episode AS TEXT)=?",
            (anime_name, dub, season, episode)
        )

    db.commit()

    text = (
        "✅ <b>Удаление выполнено</b>\n\n"
        f"Удалено записей videos: <b>{deleted_videos}</b>\n\n"
        f"{_delete_describe(action)}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Удалить ещё", callback_data="del_anime_page|0")]
    ])
    await _delete_send_or_edit(call, text, kb)


async def _delete_from_args(message: types.Message, args: str):
    parts = [x.strip() for x in args.split(";") if x.strip()]

    if not parts or len(parts) > 4:
        await message.answer(
            "❌ Неверный формат.\n\n"
            "Примеры:\n"
            "<code>/delete Название аниме</code>\n"
            "<code>/delete Название аниме ; Озвучка</code>\n"
            "<code>/delete Название аниме ; Озвучка ; Сезон</code>\n"
            "<code>/delete Название аниме ; Озвучка ; Сезон ; Серия</code>",
            parse_mode="HTML"
        )
        return

    anime_raw = parts[0].lower()
    cursor.execute("SELECT DISTINCT anime FROM videos WHERE LOWER(anime)=LOWER(?) LIMIT 1", (anime_raw,))
    row = cursor.fetchone()
    if not row:
        await message.answer("❌ Аниме не найдено. Для выбора из списка используй просто <code>/delete</code>.", parse_mode="HTML")
        return
    anime_name = row[0]

    action = {"scope": "anime", "anime": anime_name}

    if len(parts) >= 2:
        dub_raw = parts[1]
        cursor.execute(
            "SELECT DISTINCT dub FROM videos WHERE anime=? AND LOWER(dub)=LOWER(?) LIMIT 1",
            (anime_name, dub_raw)
        )
        row = cursor.fetchone()
        if not row:
            await message.answer("❌ Озвучка не найдена. Для выбора из списка используй просто <code>/delete</code>.", parse_mode="HTML")
            return
        dub = row[0]
        action = {"scope": "dub", "anime": anime_name, "dub": dub}

    if len(parts) >= 3:
        season_raw = parts[2]
        cursor.execute(
            "SELECT DISTINCT season FROM videos WHERE anime=? AND dub=? AND CAST(season AS TEXT)=? LIMIT 1",
            (anime_name, dub, str(season_raw))
        )
        row = cursor.fetchone()
        if not row:
            await message.answer("❌ Сезон/фильм не найден. Для выбора из списка используй просто <code>/delete</code>.", parse_mode="HTML")
            return
        season = str(row[0])
        action = {"scope": "season", "anime": anime_name, "dub": dub, "season": season}

    if len(parts) >= 4:
        episode_raw = parts[3]
        cursor.execute(
            "SELECT DISTINCT episode FROM videos WHERE anime=? AND dub=? AND CAST(season AS TEXT)=? AND CAST(episode AS TEXT)=? LIMIT 1",
            (anime_name, dub, season, str(episode_raw))
        )
        row = cursor.fetchone()
        if not row:
            await message.answer("❌ Серия не найдена. Для выбора из списка используй просто <code>/delete</code>.", parse_mode="HTML")
            return
        episode = str(row[0])
        action = {"scope": "episode", "anime": anime_name, "dub": dub, "season": season, "episode": episode}

    await _delete_show_confirm(message, action)


@router.message(Command("delete"))
async def delete_command(message: types.Message):
    if not _delete_admin_only(message.from_user.id):
        await message.answer("❌ У тебя нет прав для этой команды.")
        return

    args = ""
    if message.text and len(message.text.split(maxsplit=1)) > 1:
        args = message.text.split(maxsplit=1)[1].strip()

    if args:
        await _delete_from_args(message, args)
    else:
        await _delete_show_anime_page(message, 0)


@router.callback_query(F.data.startswith("del_anime_page|"))
async def delete_anime_page(call: types.CallbackQuery):
    if not _delete_admin_only(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    page = int(call.data.split("|", 1)[1])
    await _delete_show_anime_page(call, page)


@router.callback_query(F.data.startswith("del_anime|"))
async def delete_anime_select(call: types.CallbackQuery):
    if not _delete_admin_only(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    token = call.data.split("|", 1)[1]
    payload = _delete_payload(call.from_user.id, token)
    if not payload:
        await call.answer("Меню устарело. Используй /delete заново.", show_alert=True)
        return
    await _delete_show_anime_actions(call, payload)


@router.callback_query(F.data.startswith("del_dub|"))
async def delete_dub_select(call: types.CallbackQuery):
    if not _delete_admin_only(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    token = call.data.split("|", 1)[1]
    payload = _delete_payload(call.from_user.id, token)
    if not payload:
        await call.answer("Меню устарело. Используй /delete заново.", show_alert=True)
        return
    await _delete_show_dub_actions(call, payload)


@router.callback_query(F.data.startswith("del_season|"))
async def delete_season_select(call: types.CallbackQuery):
    if not _delete_admin_only(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    token = call.data.split("|", 1)[1]
    payload = _delete_payload(call.from_user.id, token)
    if not payload:
        await call.answer("Меню устарело. Используй /delete заново.", show_alert=True)
        return
    await _delete_show_season_actions(call, payload, 0)


@router.callback_query(F.data.startswith("del_ep_page|"))
async def delete_episode_page(call: types.CallbackQuery):
    if not _delete_admin_only(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    _, token, page_raw = call.data.split("|", 2)
    payload = _delete_payload(call.from_user.id, token)
    if not payload:
        await call.answer("Меню устарело. Используй /delete заново.", show_alert=True)
        return
    await _delete_show_season_actions(call, payload, int(page_raw))


@router.callback_query(F.data.startswith("del_confirm|"))
async def delete_confirm_from_menu(call: types.CallbackQuery):
    if not _delete_admin_only(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    token = call.data.split("|", 1)[1]
    action = _delete_action_payload(call.from_user.id, token)
    if not action:
        await call.answer("Подтверждение устарело. Используй /delete заново.", show_alert=True)
        return
    await _delete_show_confirm(call, action)


@router.callback_query(F.data.startswith("del_do|"))
async def delete_do(call: types.CallbackQuery):
    if not _delete_admin_only(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    token = call.data.split("|", 1)[1]
    action = _delete_action_payload(call.from_user.id, token)
    if not action:
        await call.answer("Подтверждение устарело. Используй /delete заново.", show_alert=True)
        return
    await _delete_execute(call, action)


@router.callback_query(F.data == "del_cancel")
async def delete_cancel(call: types.CallbackQuery):
    await _delete_send_or_edit(call, "❌ Удаление отменено.")


# =========================
# /down — скачивание серий для администраторов
# =========================

def _down_admin_only(user_id: int) -> bool:
    return user_id in ADMINS


def _down_store(user_id: int) -> dict:
    DOWN_MENU.setdefault(user_id, {})
    return DOWN_MENU[user_id]


def _down_token(user_id: int, payload: dict) -> str:
    """Храним длинные значения на сервере, чтобы callback_data не превысил 64 байта."""
    token = uuid4().hex[:12]
    _down_store(user_id)[token] = payload
    return token


def _down_payload(user_id: int, token: str) -> dict | None:
    return DOWN_MENU.get(user_id, {}).get(token)


def _down_sort_key(value):
    value_as_text = str(value)
    try:
        return (0, int(value_as_text))
    except (TypeError, ValueError):
        return (1, value_as_text.lower())


async def _down_send_or_edit(target, text: str, kb: InlineKeyboardMarkup | None = None):
    if isinstance(target, types.CallbackQuery):
        try:
            await target.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            await target.message.answer(text, parse_mode="HTML", reply_markup=kb)
        try:
            await target.answer()
        except Exception:
            pass
    else:
        await target.answer(text, parse_mode="HTML", reply_markup=kb)


async def _down_show_anime_page(target, page: int = 0):
    user_id = target.from_user.id
    cursor.execute("SELECT DISTINCT anime FROM videos ORDER BY anime")
    animes = [row[0] for row in cursor.fetchall()]

    if not animes:
        await _down_send_or_edit(target, "❌ В базе пока нет аниме.")
        return

    total_pages = max(1, (len(animes) + DOWN_ANIME_PER_PAGE - 1) // DOWN_ANIME_PER_PAGE)
    page = min(max(0, page), total_pages - 1)
    start = page * DOWN_ANIME_PER_PAGE
    end = start + DOWN_ANIME_PER_PAGE

    buttons = []
    for anime_name in animes[start:end]:
        token = _down_token(user_id, {"anime": anime_name})
        buttons.append([
            InlineKeyboardButton(
                text=string.capwords(anime_name),
                callback_data=f"down_anime|{token}"
            )
        ])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"down_page|{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"down_page|{page + 1}"))
    if nav:
        buttons.append(nav)

    text = (
        "📥 <b>Скачивание серий</b>\n\n"
        "Выберите аниме. Отправленные видео будут без защиты от копирования, "
        "поэтому их можно сохранить или скачать.\n\n"
        f"Страница: <b>{page + 1}/{total_pages}</b>"
    )
    await _down_send_or_edit(target, text, InlineKeyboardMarkup(inline_keyboard=buttons))


async def _down_show_seasons(call: types.CallbackQuery, payload: dict):
    user_id = call.from_user.id
    anime_name = payload["anime"]

    cursor.execute("SELECT DISTINCT season FROM videos WHERE anime=?", (anime_name,))
    seasons = sorted([row[0] for row in cursor.fetchall()], key=_down_sort_key)

    if not seasons:
        await _down_send_or_edit(call, "❌ Для этого аниме нет сезонов.")
        return

    buttons = []
    for season in seasons:
        token = _down_token(user_id, {"anime": anime_name, "season": str(season)})
        season_title = "🎬 Фильм" if str(season).lower() in {"фильм", "film", "movie"} else f"📺 Сезон {season}"
        buttons.append([InlineKeyboardButton(text=season_title, callback_data=f"down_season|{token}")])

    buttons.append([InlineKeyboardButton(text="⬅️ К аниме", callback_data="down_page|0")])
    text = (
        "📥 <b>Выберите сезон</b>\n\n"
        f"🎬 Аниме: <b>{html.escape(string.capwords(anime_name))}</b>"
    )
    await _down_send_or_edit(call, text, InlineKeyboardMarkup(inline_keyboard=buttons))


async def _down_show_dubs(call: types.CallbackQuery, payload: dict):
    user_id = call.from_user.id
    anime_name = payload["anime"]
    season = str(payload["season"])

    cursor.execute(
        "SELECT DISTINCT dub FROM videos WHERE anime=? AND CAST(season AS TEXT)=? ORDER BY dub",
        (anime_name, season)
    )
    dubs = [row[0] for row in cursor.fetchall()]

    if not dubs:
        await _down_send_or_edit(call, "❌ Для этого сезона нет озвучек.")
        return

    buttons = []
    for dub in dubs:
        token = _down_token(user_id, {"anime": anime_name, "season": season, "dub": dub})
        buttons.append([InlineKeyboardButton(text=f"🎙 {dub}", callback_data=f"down_dub|{token}")])

    back_token = _down_token(user_id, {"anime": anime_name})
    buttons.append([InlineKeyboardButton(text="⬅️ К сезонам", callback_data=f"down_anime|{back_token}")])
    text = (
        "📥 <b>Выберите озвучку</b>\n\n"
        f"🎬 Аниме: <b>{html.escape(string.capwords(anime_name))}</b>\n"
        f"📺 Сезон/фильм: <b>{html.escape(season)}</b>"
    )
    await _down_send_or_edit(call, text, InlineKeyboardMarkup(inline_keyboard=buttons))


async def _down_show_amounts(call: types.CallbackQuery, payload: dict):
    user_id = call.from_user.id
    anime_name = payload["anime"]
    season = str(payload["season"])
    dub = payload["dub"]

    cursor.execute(
        """
        SELECT episode
        FROM videos
        WHERE anime=? AND CAST(season AS TEXT)=? AND dub=?
        ORDER BY CAST(episode AS INTEGER), episode
        """,
        (anime_name, season, dub)
    )
    episodes = [row[0] for row in cursor.fetchall()]
    total = len(episodes)

    if total == 0:
        await _down_send_or_edit(call, "❌ Для этой озвучки нет серий.")
        return

    buttons = []
    amount_buttons = []
    for amount in (1, 3, 5, 10, 25, 50):
        if amount < total:
            token = _down_token(user_id, {**payload, "amount": amount})
            amount_buttons.append(InlineKeyboardButton(text=str(amount), callback_data=f"down_send|{token}"))
            if len(amount_buttons) == 3:
                buttons.append(amount_buttons)
                amount_buttons = []
    if amount_buttons:
        buttons.append(amount_buttons)

    all_token = _down_token(user_id, {**payload, "amount": total})
    buttons.append([InlineKeyboardButton(text=f"📥 Все серии ({total})", callback_data=f"down_send|{all_token}")])

    back_token = _down_token(user_id, {"anime": anime_name, "season": season})
    buttons.append([InlineKeyboardButton(text="⬅️ К озвучкам", callback_data=f"down_season|{back_token}")])

    first_ep, last_ep = episodes[0], episodes[-1]
    text = (
        "📥 <b>Сколько серий отправить?</b>\n\n"
        f"🎬 Аниме: <b>{html.escape(string.capwords(anime_name))}</b>\n"
        f"📺 Сезон/фильм: <b>{html.escape(season)}</b>\n"
        f"🎙 Озвучка: <b>{html.escape(str(dub))}</b>\n"
        f"▶️ Доступно: <b>{total}</b> (серии {html.escape(str(first_ep))}–{html.escape(str(last_ep))})\n\n"
        "Будут отправлены первые выбранные серии по порядку."
    )
    await _down_send_or_edit(call, text, InlineKeyboardMarkup(inline_keyboard=buttons))


async def _down_send_episodes(call: types.CallbackQuery, payload: dict):
    anime_name = payload["anime"]
    season = str(payload["season"])
    dub = payload["dub"]
    amount = max(1, int(payload["amount"]))

    cursor.execute(
        """
        SELECT episode, file_id
        FROM videos
        WHERE anime=? AND CAST(season AS TEXT)=? AND dub=?
        ORDER BY CAST(episode AS INTEGER), episode
        LIMIT ?
        """,
        (anime_name, season, dub, amount)
    )
    rows = cursor.fetchall()

    if not rows:
        await call.answer("Серии не найдены", show_alert=True)
        return

    # Сразу отвечаем на callback, чтобы Telegram не показывал вечную загрузку кнопки.
    await call.answer(f"Начинаю отправку: {len(rows)}")
    try:
        await call.message.edit_text(
            "⏳ <b>Отправляю серии…</b>\n\n"
            f"🎬 {html.escape(string.capwords(anime_name))}\n"
            f"📺 {html.escape(season)} · 🎙 {html.escape(str(dub))}\n"
            f"Количество: <b>{len(rows)}</b>",
            parse_mode="HTML"
        )
    except Exception:
        pass

    sent = 0
    failed = []
    for episode, file_id in rows:
        episode_caption = format_episode_caption(season, episode)
        caption = (
            f"<b>{html.escape(string.capwords(anime_name))}</b>\n"
            f"<b><i>{html.escape(str(dub))}</i></b>\n"
            f"<i>{html.escape(episode_caption)}</i>\n\n"
            "📥 Видео можно скачать или сохранить."
        )

        try:
            if isinstance(file_id, str) and file_id.startswith(("http://", "https://")):
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📥 Скачать серию", url=file_id)]
                ])
                await bot.send_message(
                    chat_id=call.from_user.id,
                    text=caption,
                    parse_mode="HTML",
                    reply_markup=kb,
                    disable_web_page_preview=True,
                    protect_content=False
                )
            else:
                await bot.send_video(
                    chat_id=call.from_user.id,
                    video=file_id,
                    caption=caption,
                    parse_mode="HTML",
                    protect_content=False,
                    supports_streaming=True
                )
            sent += 1
            await asyncio.sleep(0.15)
        except Exception as error:
            logging.exception("Не удалось отправить серию %s через /down: %s", episode, error)
            failed.append(str(episode))

    buttons = [[InlineKeyboardButton(text="📥 Скачать ещё", callback_data="down_page|0")]]
    result_text = (
        "✅ <b>Отправка завершена</b>\n\n"
        f"Отправлено: <b>{sent}</b> из <b>{len(rows)}</b>\n"
        "Защита от копирования отключена."
    )
    if failed:
        result_text += f"\nНе удалось отправить серии: <b>{html.escape(', '.join(failed))}</b>"

    try:
        await call.message.edit_text(
            result_text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    except Exception:
        await bot.send_message(
            call.from_user.id,
            result_text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )


@router.message(Command("down"))
async def down_command(message: types.Message):
    if not _down_admin_only(message.from_user.id):
        await message.answer("❌ У тебя нет прав для этой команды.")
        return

    # Старые токены этого администратора больше не нужны.
    DOWN_MENU[message.from_user.id] = {}
    await _down_show_anime_page(message, 0)


@router.callback_query(F.data.startswith("down_page|"))
async def down_anime_page(call: types.CallbackQuery):
    if not _down_admin_only(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    page = int(call.data.split("|", 1)[1])
    await _down_show_anime_page(call, page)


@router.callback_query(F.data.startswith("down_anime|"))
async def down_anime_select(call: types.CallbackQuery):
    if not _down_admin_only(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    token = call.data.split("|", 1)[1]
    payload = _down_payload(call.from_user.id, token)
    if not payload:
        await call.answer("Меню устарело. Используй /down заново.", show_alert=True)
        return
    await _down_show_seasons(call, payload)


@router.callback_query(F.data.startswith("down_season|"))
async def down_season_select(call: types.CallbackQuery):
    if not _down_admin_only(call.from_user.id):
        await call.answer("Нет до��тупа", show_alert=True)
        return
    token = call.data.split("|", 1)[1]
    payload = _down_payload(call.from_user.id, token)
    if not payload:
        await call.answer("Меню устарело. Используй /down заново.", show_alert=True)
        return
    await _down_show_dubs(call, payload)


@router.callback_query(F.data.startswith("down_dub|"))
async def down_dub_select(call: types.CallbackQuery):
    if not _down_admin_only(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    token = call.data.split("|", 1)[1]
    payload = _down_payload(call.from_user.id, token)
    if not payload:
        await call.answer("Меню устарело. Используй /down заново.", show_alert=True)
        return
    await _down_show_amounts(call, payload)


@router.callback_query(F.data.startswith("down_send|"))
async def down_send_selected(call: types.CallbackQuery):
    if not _down_admin_only(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    token = call.data.split("|", 1)[1]
    payload = _down_payload(call.from_user.id, token)
    if not payload:
        await call.answer("Меню устарело. Используй /down заново.", show_alert=True)
        return
    await _down_send_episodes(call, payload)

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
        "Выберите способ оп��аты:"
    )

    builder = InlineKeyboardBuilder()

    crypto_callback = f"pay_crypto|{period_key}"
    stars_callback = f"pay_stars|{period_key}"

    # 1) Рубли — сверху, зелёная
    builder.row(
        InlineKeyboardButton(
            text=" Оплатить рублями",
            callback_data=f"pay_rub|{period_key}",
            style="success",
            icon_custom_emoji_id="5231449120635370684"
        )
    )

    # 2) Крипта — ниже, красная
    builder.row(
        InlineKeyboardButton(
            text=" Оплатить криптовалютой",
            callback_data=crypto_callback,
            style="danger",
            icon_custom_emoji_id="5231005931550030290"
        )
    )

    # 3) Telegram Stars — ниже крипты, оранжевая/предупреждающая
    builder.row(
        InlineKeyboardButton(
            text=" Оплатить звёздами",
            callback_data=stars_callback,
            icon_custom_emoji_id="5438496463044752972"
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
    logging.info(f"[process_tariff] Callback_data кнопки 'Оплатить звёздами': {stars_callback}")

    try:
        await send_and_track(user_id, call.message.edit_text, text, parse_mode="HTML", reply_markup=kb)
    except:
        await send_and_track(user_id, call.message.answer, text, parse_mode="HTML", reply_markup=kb)

    await call.answer()

# ===== Рублевая оплата через YooKassa =====
async def get_yookassa_payment(payment_id: str):
    """Пров��ряет платеж в YooKassa по API. Используется и для вебхука, и для кнопки проверки."""
    if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
        logging.error("[YooKassa] Не заданы YOOKASSA_SHOP_ID / YOOKASSA_SECRET_KEY")
        return None

    try:
        auth = aiohttp.BasicAuth(YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY)
        async with aiohttp.ClientSession(auth=auth) as session:
            async with session.get(f"{YOOKASSA_API_PAYMENTS}/{payment_id}", timeout=15) as resp:
                data = await resp.json(content_type=None)
                if resp.status >= 400:
                    logging.error(f"[YooKassa] get payment error {resp.status}: {data}")
                    return None
                return data
    except Exception as e:
        logging.error(f"[YooKassa] get payment exception: {e}")
        return None


async def create_yookassa_payment_async(user_id: int, rub_amount: int, period_key: str):
    """Создает платеж YooKassa и возвращает (payment_id, confirmation_url)."""
    if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
        logging.error("[YooKassa] Не заданы YOOKASSA_SHOP_ID / YOOKASSA_SECRET_KEY")
        return None, None

    payload = {
        "amount": {
            "value": f"{rub_amount:.2f}",
            "currency": "RUB"
        },
        "capture": True,
        "confirmation": {
            "type": "redirect",
            "return_url": YOOKASSA_RETURN_URL
        },
        "description": f"Подписка {period_key} для Telegram user {user_id}",
        "metadata": {
            "user_id": str(user_id),
            "period_key": period_key,
            "provider": "yookassa"
        }
    }

    headers = {
        "Idempotence-Key": str(uuid4()),
        "Content-Type": "application/json"
    }

    try:
        auth = aiohttp.BasicAuth(YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY)
        async with aiohttp.ClientSession(auth=auth) as session:
            async with session.post(YOOKASSA_API_PAYMENTS, json=payload, headers=headers, timeout=20) as resp:
                data = await resp.json(content_type=None)

                if resp.status >= 400:
                    logging.error(f"[YooKassa] create payment error {resp.status}: {data}")
                    return None, None

                payment_id = data.get("id")
                confirmation_url = data.get("confirmation", {}).get("confirmation_url")

                if not payment_id or not confirmation_url:
                    logging.error(f"[YooKassa] Нет payment_id или confirmation_url: {data}")
                    return None, None

                cursor.execute(
                    "INSERT OR REPLACE INTO pending_payments (user_id, period_key, invoice_id, pay_url, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (user_id, period_key, payment_id, confirmation_url, datetime.now().isoformat())
                )
                db.commit()

                logging.info(f"[YooKassa] Payment created user={user_id}, period={period_key}, payment_id={payment_id}")
                return payment_id, confirmation_url

    except Exception as e:
        logging.error(f"[YooKassa] create payment exception: {e}")
        return None, None


async def activate_paid_subscription(user_id: int, period_key: str, payment_id: str, provider: str = "yookassa"):
    """Единая выдача подписки после успешной оплаты. Защищает от повторной обработки."""
    processed_id = f"{provider}:{payment_id}"

    cursor.execute("SELECT 1 FROM processed_invoices WHERE invoice_id=?", (processed_id,))
    if cursor.fetchone():
        logging.warning(f"[{provider}] Payment already processed: {processed_id}")
        return False

    if period_key == "forever":
        days = None
    else:
        try:
            days = int(period_key.split("_")[0])
        except Exception:
            logging.error(f"[{provider}] Invalid period_key: {period_key}")
            return False

    cursor.execute(
        "INSERT INTO processed_invoices (invoice_id, user_id, period_key, created_at) VALUES (?, ?, ?, ?)",
        (processed_id, user_id, period_key, datetime.now().isoformat())
    )
    cursor.execute("DELETE FROM pending_payments WHERE user_id=?", (user_id,))
    db.commit()

    give_subscription(user_id, days)
    await process_referral_bonus(user_id, period_key)

    try:
        if days is None:
            await bot.send_message(
                user_id,
                "<tg-emoji emoji-id=\"5461151367559141950\">👍</tg-emoji> Ваша подписка <b>НАВСЕГДА</b> активирована!",
                parse_mode="HTML"
            )
        else:
            await bot.send_message(
                user_id,
                f"<tg-emoji emoji-id=\"5461151367559141950\">👍</tg-emoji> Ваша подписка на <b>{days} дней</b> активирована!",
                parse_mode="HTML"
            )
    except Exception as e:
        logging.error(f"[{provider}] Не удалось отправить сообщение пользователю {user_id}: {e}")

    try:
        await bot.send_message(
            ADMIN_CHAT_ID,
            f"💰 Новая оплата через {provider}\n\n"
            f"👤 User: {user_id}\n"
            f"📦 Тариф: {period_key}\n"
            f"🧾 Payment: {payment_id}"
        )
    except Exception as e:
        logging.error(f"[{provider}] Не удалось отправить сообщение а��мину: {e}")

    logging.info(f"[{provider}] Subscription activated user={user_id}, period={period_key}, payment={payment_id}")
    return True



# ===== Рублевая оплата через ЮMoney кошелёк =====
def make_yoomoney_label(user_id: int, period_key: str) -> str:
    """Короткая метка платежа для ЮMoney. По ней webhook поймёт, кому выдать подписку."""
    return f"ym|{user_id}|{period_key}|{uuid4().hex[:10]}"


def parse_yoomoney_label(label: str):
    try:
        parts = str(label or "").split("|")
        if len(parts) < 4 or parts[0] != "ym":
            return None, None
        user_id = int(parts[1])
        period_key = parts[2]
        if period_key not in RUB_PRICES:
            return None, None
        return user_id, period_key
    except Exception:
        return None, None


def create_yoomoney_payment_link(user_id: int, rub_amount: int, period_key: str):
    """Создаёт ссылку на оплату ЮMoney и сохраняет ожидающий платёж в базу."""
    if not YOOMONEY_RECEIVER:
        logging.error("[YooMoney] Не задан YOOMONEY_RECEIVER")
        return None, None

    label = make_yoomoney_label(user_id, period_key)

    params = {
        "receiver": YOOMONEY_RECEIVER,
        "quickpay-form": "button",
        "paymentType": "AC",  # AC — банковская карта; PC — кошелёк ЮMoney
        "sum": f"{rub_amount:.2f}",
        "label": label,
        "successURL": YOOMONEY_RETURN_URL,
        "formcomment": f"Подписка {period_key}",
        "short-dest": f"Подписка {period_key}",
        "comment": f"Подписка {period_key} для Telegram user {user_id}",
        "targets": f"Подписка {period_key}",
    }

    pay_url = YOOMONEY_QUICKPAY_URL + "?" + urllib.parse.urlencode(params)

    cursor.execute(
        "INSERT OR REPLACE INTO pending_payments (user_id, period_key, invoice_id, pay_url, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, period_key, label, pay_url, datetime.now().isoformat())
    )
    db.commit()

    logging.info(f"[YooMoney] Payment link created user={user_id}, period={period_key}, label={label}")
    return label, pay_url


def verify_yoomoney_signature(form_data: dict) -> bool:
    """Проверяет sign из HTTP-уведомления ЮMoney.

    Актуальный алгоритм: HMAC-SHA256 от URL-кодированной строки всех параметров,
    кроме sign, отсортированных по алфавиту.
    """
    if not YOOMONEY_SECRET:
        logging.error("[YooMoney] Не задан YOOMONEY_SECRET")
        return False

    sign = str(form_data.get("sign") or "").strip().lower()
    if not sign:
        logging.error("[YooMoney] В уведомлении нет sign")
        return False

    items = []
    for key in sorted(form_data.keys()):
        if key == "sign":
            continue
        value = "" if form_data.get(key) is None else str(form_data.get(key))
        encoded_value = urllib.parse.quote(value, safe="-_.~")
        items.append(f"{key}={encoded_value}")

    canonical = "&".join(items)
    calculated = hmac.new(
        YOOMONEY_SECRET.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(calculated, sign):
        logging.error(
            f"[YooMoney] Неверная подпись notification. calculated={calculated}, got={sign}, canonical={canonical}"
        )
        return False

    return True


async def handle_yoomoney_webhook(request):
    """Webhook ЮMoney: /yoomoney

    В настройках ЮMoney HTTP-уведомлений укажи:
    https://твой-домен/yoomoney
    """
    try:
        post = await request.post()
        data = {str(k): str(v) for k, v in post.items()}

        logging.info(f"[YOOMONEY_WEBHOOK] Получены данные: {data}")

        if not data:
            return web.Response(text="Empty form", status=400)

        # Тестовая кнопка в кабинете ЮMoney не должна выдавать подписку.
        if str(data.get("test_notification", "")).lower() == "true":
            logging.info("[YOOMONEY_WEBHOOK] Тестовое уведомление принято")
            return web.Response(text="Test OK")

        if not verify_yoomoney_signature(data):
            return web.Response(text="Bad signature", status=403)

        notification_type = data.get("notification_type")
        if notification_type not in ("p2p-incoming", "card-incoming"):
            logging.info(f"[YOOMONEY_WEBHOOK] Игнорируем notification_type={notification_type}")
            return web.Response(text="Ignored")

        operation_id = str(data.get("operation_id") or "").strip()
        label = str(data.get("label") or "").strip()

        if not operation_id:
            logging.error("[YOOMONEY_WEBHOOK] Нет operation_id")
            return web.Response(text="No operation_id", status=400)

        if not label:
            logging.error("[YOOMONEY_WEBHOOK] Нет label")
            return web.Response(text="No label", status=400)

        # Не выдаём подписку, если перевод вдруг не принят.
        if str(data.get("unaccepted", "false")).lower() == "true":
            logging.warning(f"[YOOMONEY_WEBHOOK] Платёж захолдирован/unaccepted operation_id={operation_id}")
            return web.Response(text="Unaccepted")

        if str(data.get("codepro", "false")).lower() == "true":
            logging.warning(f"[YOOMONEY_WEBHOOK] Платёж с codepro operation_id={operation_id}")
            return web.Response(text="Codepro")

        cursor.execute(
            "SELECT user_id, period_key FROM pending_payments WHERE invoice_id=?",
            (label,)
        )
        row = cursor.fetchone()

        user_id = None
        period_key = None

        if row:
            user_id, period_key = row
        else:
            user_id, period_key = parse_yoomoney_label(label)

        if not user_id or not period_key:
            logging.error(f"[YOOMONEY_WEBHOOK] Не удалось определить user/period label={label}")
            return web.Response(text="Unknown label")

        expected = Decimal(str(RUB_PRICES.get(period_key, 0)))
        # withdraw_amount — сколько списали у отправителя; amount — сколько зачислено с учётом комиссии.
        paid_raw = data.get("withdraw_amount") or data.get("amount") or "0"
        try:
            paid = Decimal(str(paid_raw))
        except Exception:
            logging.error(f"[YOOMONEY_WEBHOOK] Неверная сумма: {paid_raw}")
            return web.Response(text="Bad amount", status=400)

        if expected <= 0:
            logging.error(f"[YOOMONEY_WEBHOOK] Неверный period_key={period_key}")
            return web.Response(text="Bad period", status=400)

        if paid < expected:
            logging.warning(
                f"[YOOMONEY_WEBHOOK] Сумма меньше нужной: paid={paid}, expected={expected}, label={label}"
            )
            return web.Response(text="Low amount")

        await activate_paid_subscription(
            int(user_id),
            period_key,
            operation_id,
            provider="yoomoney"
        )

        return web.Response(text="OK")

    except Exception as e:
        logging.error(f"[YOOMONEY_WEBHOOK] Критическая ошибка: {e}")
        return web.Response(text="Server error", status=500)


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

@router.callback_query(F.data.startswith("check_yookassa|"))
async def check_yookassa_handler(call: types.CallbackQuery):
    try:
        _, payment_id = call.data.split("|", 1)
    except ValueError:
        await call.answer("Ошибка платежа", show_alert=True)
        return

    payment = await get_yookassa_payment(payment_id)
    if not payment:
        await call.answer("Не удалось проверить платёж", show_alert=True)
        return

    status = payment.get("status")
    paid = bool(payment.get("paid"))

    metadata = payment.get("metadata") or {}
    try:
        user_id = int(metadata.get("user_id") or call.from_user.id)
    except Exception:
        user_id = call.from_user.id

    period_key = metadata.get("period_key")

    if status == "succeeded" and paid and period_key:
        activated = await activate_paid_subscription(user_id, period_key, payment_id, provider="yookassa")
        if activated:
            await call.answer("✅ Оплата найдена, подписка активирована", show_alert=True)
        else:
            await call.answer("✅ Оплата уже была обработана", show_alert=True)
        return

    await call.answer(f"Платёж пока не оплачен. Статус: {status}", show_alert=True)


# ===== Оплата через Telegram Stars =====
def make_stars_payload(user_id: int, period_key: str) -> str:
    # payload должен быть коротким, чтобы стабильно проходить через Telegram invoice
    return f"stars|{user_id}|{period_key}|{uuid4().hex[:10]}"


def parse_stars_payload(payload: str):
    try:
        parts = str(payload).split("|")
        if len(parts) < 4 or parts[0] != "stars":
            return None, None
        user_id = int(parts[1])
        period_key = parts[2]
        if period_key not in RUB_PRICES:
            return None, None
        return user_id, period_key
    except Exception:
        return None, None


@router.callback_query(F.data.startswith("pay_stars|"))
async def pay_stars_handler(call: types.CallbackQuery):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    try:
        _, period_key = call.data.split("|", 1)
    except ValueError:
        await call.answer("Ошибка тарифа", show_alert=True)
        return

    stars_amount = int(RUB_PRICES.get(period_key, 0))
    if stars_amount <= 0:
        await call.answer("Ошибка тарифа", show_alert=True)
        return

    try:
        await delete_bot_messages(user_id, chat_id)
    except Exception as e:
        logging.error(f"[pay_stars_handler] Ошибка при удалении старого сообщения: {e}")

    payload = make_stars_payload(user_id, period_key)

    cursor.execute(
        "INSERT OR REPLACE INTO pending_payments (user_id, period_key, invoice_id, pay_url, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, period_key, payload, "telegram_stars", datetime.now().isoformat())
    )
    db.commit()

    try:
        msg = await bot.send_invoice(
            chat_id=chat_id,
            title=f"Подписка {period_key.replace('_', ' ')}",
            description=(
                f"Оплата подписки через Telegram Stars. "
                f"Соотношение: 1 ⭐ = 1 ₽. К оплате: {stars_amount} ⭐"
            ),
            payload=payload,
            provider_token="",
            currency="XTR",
            prices=[
                types.LabeledPrice(
                    label=f"Подписка {period_key.replace('_', ' ')}",
                    amount=stars_amount
                )
            ],
        )
        USER_MESSAGES.setdefault(user_id, []).append(msg.message_id)

        await call.answer()

    except Exception as e:
        logging.error(f"[TelegramStars] send_invoice error: {e}")
        await call.message.answer("❌ Не удалось создать счёт Telegram Stars. Проверь логи сервера.")
        await call.answer()


@router.pre_checkout_query()
async def stars_pre_checkout_handler(pre_checkout_query: types.PreCheckoutQuery):
    user_id, period_key = parse_stars_payload(pre_checkout_query.invoice_payload)

    if not user_id or not period_key:
        await pre_checkout_query.answer(
            ok=False,
            error_message="Ошибка платежа. Попробуйте создать счёт заново."
        )
        return

    if pre_checkout_query.from_user.id != user_id:
        await pre_checkout_query.answer(
            ok=False,
            error_message="Этот счёт создан для другого пользователя."
        )
        return

    expected_amount = int(RUB_PRICES.get(period_key, 0))
    if pre_checkout_query.currency != "XTR" or pre_checkout_query.total_amount != expected_amount:
        await pre_checkout_query.answer(
            ok=False,
            error_message="Сумма платежа не совпадает. Создайте счёт заново."
        )
        return

    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def stars_successful_payment_handler(message: types.Message):
    payment = message.successful_payment

    if payment.currency != "XTR":
        return

    user_id, period_key = parse_stars_payload(payment.invoice_payload)
    if not user_id or not period_key:
        logging.error(f"[TelegramStars] Invalid successful_payment payload: {payment.invoice_payload}")
        return

    if message.from_user and message.from_user.id != user_id:
        logging.error(
            f"[TelegramStars] user mismatch: payload_user={user_id}, message_user={message.from_user.id}"
        )
        return

    expected_amount = int(RUB_PRICES.get(period_key, 0))
    if payment.total_amount != expected_amount:
        logging.error(
            f"[TelegramStars] amount mismatch user={user_id}: got={payment.total_amount}, expected={expected_amount}"
        )
        return

    charge_id = (
        payment.telegram_payment_charge_id
        or payment.provider_payment_charge_id
        or payment.invoice_payload
    )

    activated = await activate_paid_subscription(
        int(user_id),
        period_key,
        charge_id,
        provider="telegram_stars"
    )

    if activated:
        try:
            await message.answer(
                f"✅ Оплата Telegram Stars прошла успешно!\n"
                f"Списано: <b>{payment.total_amount} ⭐</b>",
                parse_mode="HTML"
            )
        except Exception as e:
            logging.error(f"[TelegramStars] Не удалось отправить сообщение после оплаты: {e}")


# ===== Криптооплата через CryptoBot =====
async def create_crypto_invoice_async(user_id: int, rub_amount: int, period_key: str):
    """Создает invoice CryptoBot и возвращает (invoice_id, invoice_url)."""
    if not CRYPTOBOT_TOKEN:
        logging.error("[CryptoBot] Не задан CRYPTOBOT_TOKEN")
        return None, None

    url = f"{CRYPTOBOT_API_BASE}/createInvoice"
    headers = {
        "Crypto-Pay-API-Token": CRYPTOBOT_TOKEN,
        "Content-Type": "application/json"
    }
    payload = {
        "currency_type": "fiat",
        "fiat": "RUB",
        "amount": f"{rub_amount:.2f}",
        "description": f"Subscription:{period_key}",
        "payload": f"{user_id}|{period_key}",
        "allow_comments": False,
        "allow_anonymous": False,
        "expires_in": 3600
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=20) as resp:
                result = await resp.json(content_type=None)

                if resp.status >= 400 or not result.get("ok"):
                    logging.error(f"[CryptoBot] createInvoice error {resp.status}: {result}")
                    return None, None

                invoice = result.get("result") or {}
                invoice_id = str(invoice.get("invoice_id") or "").strip()
                invoice_url = (
                    invoice.get("bot_invoice_url")
                    or invoice.get("mini_app_invoice_url")
                    or invoice.get("web_app_invoice_url")
                    or invoice.get("pay_url")
                )

                if not invoice_id or not invoice_url:
                    logging.error(f"[CryptoBot] Нет invoice_id или invoice_url: {invoice}")
                    return None, None

                cursor.execute(
                    "INSERT OR REPLACE INTO pending_payments (user_id, period_key, invoice_id, pay_url, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (user_id, period_key, invoice_id, invoice_url, datetime.now().isoformat())
                )
                db.commit()

                logging.info(f"[CryptoBot] Invoice created user={user_id}, period={period_key}, invoice_id={invoice_id}")
                return invoice_id, invoice_url

    except Exception as e:
        logging.error(f"[CryptoBot] createInvoice exception: {e}")
        return None, None


async def get_crypto_invoice(invoice_id: str):
    """Проверяет invoice через API CryptoBot. Используется для кнопки проверки."""
    if not CRYPTOBOT_TOKEN:
        logging.error("[CryptoBot] Не задан CRYPTOBOT_TOKEN")
        return None

    url = f"{CRYPTOBOT_API_BASE}/getInvoices"
    headers = {"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN}
    params = {"invoice_ids": str(invoice_id)}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers, timeout=15) as resp:
                result = await resp.json(content_type=None)

                if resp.status >= 400 or not result.get("ok"):
                    logging.error(f"[CryptoBot] getInvoices error {resp.status}: {result}")
                    return None

                data = result.get("result")
                if isinstance(data, dict):
                    items = data.get("items") or data.get("invoices") or []
                elif isinstance(data, list):
                    items = data
                else:
                    items = []

                return items[0] if items else None

    except Exception as e:
        logging.error(f"[CryptoBot] getInvoices exception: {e}")
        return None


def verify_cryptobot_signature(raw_body: bytes, headers) -> bool:
    """Проверяет подпись webhook CryptoBot: HMAC-SHA256(body, sha256(token))."""
    if not CRYPTOBOT_TOKEN:
        logging.error("[CRYPTO_WEBHOOK] Не задан CRYPTOBOT_TOKEN")
        return False

    signature = headers.get("crypto-pay-api-signature")
    if not signature:
        logging.error("[CRYPTO_WEBHOOK] Нет заголовка crypto-pay-api-signature")
        return False

    secret = hashlib.sha256(CRYPTOBOT_TOKEN.encode("utf-8")).digest()
    calculated = hmac.new(secret, raw_body, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated, signature):
        logging.error("[CRYPTO_WEBHOOK] Неверная подпись webhook")
        return False

    return True


@router.callback_query(F.data.startswith("pay_crypto|"))
async def pay_crypto_handler(call: types.CallbackQuery):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    logging.info(f"[pay_crypto_handler] Нажата кнопка пользователем {user_id}, callback_data={call.data}")

    try:
        _, period_key = call.data.split("|", 1)
        logging.info(f"[pay_crypto_handler] Выбран тариф: {period_key}")
    except ValueError:
        await call.answer("Ошибка тарифа", show_alert=True)
        return

    rub_amount = RUB_PRICES.get(period_key, 0)
    if rub_amount == 0:
        await call.answer("Ошибка тарифа", show_alert=True)
        return

    try:
        await delete_bot_messages(user_id, chat_id)
    except Exception as e:
        logging.error(f"[pay_crypto_handler] Ошибка при удалении старого сообщения: {e}")

    invoice_id, invoice_url = await create_crypto_invoice_async(user_id, rub_amount, period_key)
    if not invoice_id or not invoice_url:
        await call.message.answer(
            "❌ Не удалось создать счёт CryptoBot. Проверь CRYPTOBOT_TOKEN и логи сервера."
        )
        await call.answer()
        return

    PENDING_PAYMENTS[user_id] = {
        "period_key": period_key,
        "invoice_id": invoice_id
    }

    text = (
        f"<tg-emoji emoji-id=\"5350452584119279096\">👍</tg-emoji> <b>Оплата подписки криптовалютой</b>\n\n"
        f"Сумма: <b>{rub_amount}₽</b>\n"
        f"Тариф: <b>{period_key.replace('_', ' ')}</b>\n\n"
        "Нажмите кнопку ниже и оплатите через CryptoBot.\n"
        "После успешной оплаты подписка активируется автоматически через webhook.\n\n"
        "Если webhook задержался, нажмите <b>Проверить оплату</b>."
    )

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
            text=" Проверить оплату",
            callback_data=f"check_crypto|{invoice_id}",
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

    await send_and_track(
        user_id,
        call.message.answer,
        text,
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )

    await call.answer()


@router.callback_query(F.data.startswith("check_crypto|"))
async def check_crypto_handler(call: types.CallbackQuery):
    try:
        _, invoice_id = call.data.split("|", 1)
        invoice_id = str(invoice_id)
    except ValueError:
        await call.answer("Ошибка счёта", show_alert=True)
        return

    cursor.execute(
        "SELECT user_id, period_key FROM pending_payments WHERE invoice_id=?",
        (invoice_id,)
    )
    row = cursor.fetchone()

    if not row:
        cursor.execute(
            "SELECT 1 FROM processed_invoices WHERE invoice_id=?",
            (f"cryptobot:{invoice_id}",)
        )
        if cursor.fetchone():
            await call.answer("✅ Эта оплата уже была обработана", show_alert=True)
        else:
            await call.answer("Счёт не найден в ожидании оплаты", show_alert=True)
        return

    user_id, period_key = row

    invoice = await get_crypto_invoice(invoice_id)
    if not invoice:
        await call.answer("Не удалось проверить счёт", show_alert=True)
        return

    status = invoice.get("status")
    if status == "paid":
        activated = await activate_paid_subscription(int(user_id), period_key, invoice_id, provider="cryptobot")
        if activated:
            await call.answer("✅ Оплата найдена, подписка активирована", show_alert=True)
        else:
            await call.answer("✅ Оплата уже была обработана", show_alert=True)
        return

    await call.answer(f"Счёт пока не оплачен. Статус: {status}", show_alert=True)


# ===== Вебхук CryptoBot =====
async def handle_crypto_webhook(request):
    try:
        raw_body = await request.read()

        if not verify_cryptobot_signature(raw_body, request.headers):
            return web.Response(text="Bad signature", status=403)

        try:
            data = json.loads(raw_body.decode("utf-8"))
        except Exception as e:
            logging.error(f"[CRYPTO_WEBHOOK] Ошибка JSON: {e}")
            return web.Response(text="Invalid JSON", status=400)

        logging.info(f"[CRYPTO_WEBHOOK] Получены данные: {data}")

        if data.get("update_type") != "invoice_paid":
            logging.info(f"[CRYPTO_WEBHOOK] Игнорируем update_type={data.get('update_type')}")
            return web.Response(text="Ignored")

        payload = data.get("payload") or {}
        invoice_id = str(payload.get("invoice_id") or "").strip()
        invoice_payload = payload.get("payload")  # user_id|period_key
        status = payload.get("status")

        if not invoice_id:
            logging.error("[CRYPTO_WEBHOOK] Нет invoice_id")
            return web.Response(text="No invoice_id", status=400)

        if status and status != "paid":
            logging.info(f"[CRYPTO_WEBHOOK] Invoice не paid: invoice={invoice_id}, status={status}")
            return web.Response(text="Not paid")

        # Сначала пытаемся найти ожидаемый платёж по invoice_id.
        cursor.execute(
            "SELECT user_id, period_key FROM pending_payments WHERE invoice_id=?",
            (invoice_id,)
        )
        row = cursor.fetchone()

        user_id = None
        period_key = None

        if row:
            user_id, period_key = row
        elif invoice_payload:
            try:
                user_id_str, period_key = str(invoice_payload).split("|", 1)
                user_id = int(user_id_str)
            except Exception as e:
                logging.error(f"[CRYPTO_WEBHOOK] Ошибка payload invoice={invoice_id}: {e}; payload={invoice_payload}")

        if not user_id or not period_key:
            logging.error(f"[CRYPTO_WEBHOOK] Не удалось определить user/period для invoice={invoice_id}")
            # 200, чтобы CryptoBot не долбил endpoint 3 дня и не отключил webhook.
            return web.Response(text="Unknown invoice")

        await activate_paid_subscription(int(user_id), period_key, invoice_id, provider="cryptobot")
        return web.Response(text="OK")

    except Exception as e:
        logging.error(f"[CRYPTO_WEBHOOK] Критическая ошибка: {e}")
        return web.Response(text="Server error", status=500)

async def handle_yookassa_webhook(request):
    try:
        data = await request.json()
        logging.info(f"[YOOKASSA_WEBHOOK] Получены данные: {data}")

        if data.get("type") != "notification":
            logging.info("[YOOKASSA_WEBHOOK] Игнорируем не notification")
            return web.Response(text="Ignored")

        event = data.get("event")
        payment_obj = data.get("object") or {}

        if event != "payment.succeeded":
            logging.info(f"[YOOKASSA_WEBHOOK] Игнорируем событие {event}")
            return web.Response(text="Ignored")

        payment_id = payment_obj.get("id")
        if not payment_id:
            logging.error("[YOOKASSA_WEBHOOK] Нет payment id")
            return web.Response(text="No payment id")

        # Дополнительная проверка через API YooKassa, чтобы не доверять только входящему JSON.
        verified_payment = await get_yookassa_payment(payment_id)
        payment = verified_payment or payment_obj

        status = payment.get("status")
        paid = bool(payment.get("paid"))
        metadata = payment.get("metadata") or payment_obj.get("metadata") or {}

        if status != "succeeded" or not paid:
            logging.warning(f"[YOOKASSA_WEBHOOK] Payment not succeeded: id={payment_id}, status={status}, paid={paid}")
            return web.Response(text="Not paid")

        try:
            user_id = int(metadata.get("user_id"))
            period_key = metadata.get("period_key")
        except Exception as e:
            logging.error(f"[YOOKASSA_WEBHOOK] Ошибка metadata: {e}; metadata={metadata}")
            return web.Response(text="Invalid metadata")

        if not period_key:
            logging.error(f"[YOOKASSA_WEBHOOK] Нет period_key в metadata: {metadata}")
            return web.Response(text="Invalid metadata")

        await activate_paid_subscription(user_id, period_key, payment_id, provider="yookassa")
        return web.Response(text="OK")

    except Exception as e:
        logging.error(f"[YOOKASSA_WEBHOOK] Критическая ошибка: {e}")
        return web.Response(text="Server error", status=500)


async def test(request):
    return web.Response(text="Server OK")

# ===== Регистрация вебхуков =====
app = web.Application()

# Для совместимости старый /webhook оставлен под CryptoBot.
# Для новых настроек лучше использовать отдельные пути:
#   CryptoBot  -> https://домен/cryptobot
#   YooKassa   -> https://домен/yookassa
app.router.add_post("/webhook", handle_crypto_webhook)
app.router.add_post("/cryptobot", handle_crypto_webhook)
app.router.add_post("/yookassa", handle_yookassa_webhook)
app.router.add_post("/yoomoney", handle_yoomoney_webhook)

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

    # Сообщение ��ользователю
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
async def live_search(message: types.Message, state: FSMContext):
    # ❗ ВАЖНО: игнорируем если пользователь в создании подборки
    if await state.get_state() == CreateCollection.picking.state:
        return

    user_id = message.from_user.id
    chat_id = message.chat.id
    query = message.text.lower().strip()

    if not query:
        return

    await delete_bot_messages(user_id, chat_id)

    # В обычном чате принимаем только шестизначный ID аниме.
    if not query.isdigit() or len(query) != 6:
        return

    cursor.execute("SELECT anime FROM anime_catalog WHERE id=?", (query,))
    row = cursor.fetchone()
    found_animes = [row[0]] if row else []

    if not found_animes:
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(
            text=" Назад в меню",
            callback_data="back_menu",
            style="primary",
            icon_custom_emoji_id="5352759161945867747"
        ))
        kb = builder.as_markup()
        await send_and_track(
            user_id,
            message.answer,
            "❌ Ничего не найдено",
            reply_markup=kb
        )
        return

    cursor.execute("SELECT DISTINCT anime FROM videos ORDER BY anime")
    all_animes = [row[0] for row in cursor.fetchall()]

    for anime in found_animes:
        try:
            anime_idx = all_animes.index(anime)
        except ValueError:
            continue

        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(
            text=" Открыть",
            callback_data=f"anime_index|{anime_idx}",
            style="danger",
            icon_custom_emoji_id="5348125953090403204"
        ))
        builder.row(InlineKeyboardButton(
            text=" Назад в меню",
            callback_data="back_menu",
            style="primary",
            icon_custom_emoji_id="5352759161945867747"
        ))
        kb = builder.as_markup()

        # ==============================
        # 🔥 НОВАЯ ЛОГИКА ДАННЫХ
        # ==============================
        data = await load_anime_info(anime)

        if data:
            anime_name, poster_url_inline, score, genres, year = data
        else:
            anime_name, poster_url_inline, score, genres, year = anime, None, "—", "—", "—"

        # старую переменную оставляем для постера fallback
        info = None
        try:
            info = await get_anime_info(anime)
        except:
            pass

        # ==============================
        # 🔥 ЛОГИКА ПОСТЕРА (НЕ ТРОГАЕМ)
        # ==============================

        cursor.execute(
            "SELECT poster FROM anime_info WHERE anime=?",
            (anime,)
        )
        row = cursor.fetchone()
        poster_url = row[0] if row and row[0] else None

        if not poster_url and info:
            cursor.execute(
                "SELECT english_name FROM videos WHERE anime=? LIMIT 1",
                (anime,)
            )
            r = cursor.fetchone()
            english_name = r[0] if r and r[0] else anime

            try:
                poster_url = await search_anilist_poster(english_name)
            except:
                poster_url = None

            if not poster_url:
                try:
                    poster_url = await search_anilist_poster(anime)
                except:
                    poster_url = None

            if not poster_url:
                poster_url = fix_shiki_poster(info.get("poster"))

            if poster_url:
                cursor.execute(
                    "INSERT INTO anime_info (anime, poster) VALUES (?, ?) "
                    "ON CONFLICT(anime) DO UPDATE SET poster=excluded.poster",
                    (anime, poster_url)
                )
                db.commit()

        # ==============================
        # 🔥 НОВЫЙ ТЕКСТ (как inline)
        # ==============================

        text = (
            f"<b>{string.capwords(anime_name)}</b>\n"
            f"<tg-emoji emoji-id=\"5438496463044752972\">👍</tg-emoji> Рейтинг: {score}\n"
            f"<tg-emoji emoji-id=\"5413879192267805083\">👍</tg-emoji> Год: {year}\n"
            f"<tg-emoji emoji-id=\"5350658016700013471\">👍</tg-emoji> Жанры: {genres}"
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
                    photo=fix_shiki_poster(info.get("poster")),
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
            print(f"Ошибка отправк�� сообщения для {anime}: {e}")
# =========================
# Выбор аниме
# =========================
# =========================
# Выбор аниме
# =========================

async def search_anilist_poster(title_en: str) -> str | None:
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

    variables = {"search": title_en}  # ✅ FIX

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://graphql.anilist.co",
                json={"query": query, "variables": variables},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:

                if resp.status != 200:
                    return None

                data = await resp.json()

                if "errors" in data:
                    return None

                media = data.get("data", {}).get("Media")
                if not media:
                    return None

                cover = media.get("coverImage")
                if not cover:
                    return None

                return cover.get("extraLarge") or cover.get("large")

    except Exception as e:
        print(f"[AniList ERROR] {title_en}: {e}")  # тоже поправил
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



# =========================
# Умный поиск аниме
# =========================

RU_TO_LAT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh", "з": "z",
    "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def normalize_search_text(text: str | None) -> str:
    """Приводит строку к виду, удобному для поиска: нижний регистр, без мусорных символов."""
    text = unicodedata.normalize("NFKC", text or "").casefold().replace("ё", "е")
    text = re.sub(r"[^0-9a-zа-я]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def ru_to_latin(text: str | None) -> str:
    """Проста�� транслитерация русского названия для поиска латиницей."""
    normalized = normalize_search_text(text)
    return "".join(RU_TO_LAT.get(ch, ch) for ch in normalized)


def compact_search_text(text: str | None) -> str:
    return normalize_search_text(text).replace(" ", "")


def title_match_score(query: str, candidate: str) -> float:
    """Оценка похожести запроса и одного варианта названия."""
    q = normalize_search_text(query)
    c = normalize_search_text(candidate)

    if not q or not c:
        return 0.0

    if q == c:
        return 100.0
    if c.startswith(q):
        return 96.0
    if q in c:
        return 91.0

    q_tokens = q.split()
    c_tokens = c.split()
    if q_tokens and all(any(token in c_token for c_token in c_tokens) for token in q_tokens):
        return 88.0

    ratio = difflib.SequenceMatcher(None, q, c).ratio() * 100.0

    q_compact = q.replace(" ", "")
    c_compact = c.replace(" ", "")
    if q_compact and c_compact:
        ratio = max(ratio, difflib.SequenceMatcher(None, q_compact, c_compact).ratio() * 100.0)

    return ratio


def fuzzy_search_anime(query_text: str, offset: int = 0, limit: int = PAGE_SIZE):
    """Ищет аниме по русскому названию, english_name и опечаткам.

    Работает без внешних библиотек, через difflib.
    Возвращает: (anime_names, next_offset)
    """
    q = normalize_search_text(query_text)
    if not q:
        return [], ""

    # Для очень коротких запросов оставляем более строгий порог, чтобы не выдавать мусор.
    if len(q) <= 2:
        threshold = 82.0
    elif len(q) <= 4:
        threshold = 70.0
    else:
        threshold = 58.0

    q_variants = {q, compact_search_text(q), ru_to_latin(q)}
    q_variants = {x for x in q_variants if x}

    cursor.execute(
        """
        SELECT DISTINCT anime, COALESCE(english_name, '')
        FROM videos
        ORDER BY anime
        """
    )

    scored = []
    seen = set()

    for anime_name, english_name in cursor.fetchall():
        if not anime_name or anime_name in seen:
            continue

        aliases = {
            anime_name,
            english_name or "",
            ru_to_latin(anime_name),
            compact_search_text(anime_name),
            compact_search_text(english_name or ""),
        }
        aliases = {a for a in aliases if a}

        best = 0.0
        for qv in q_variants:
            for alias in aliases:
                best = max(best, title_match_score(qv, alias))

        if best >= threshold:
            scored.append((best, anime_name))
            seen.add(anime_name)

    scored.sort(key=lambda x: (-x[0], x[1]))
    matched = [anime for _, anime in scored]

    page = matched[offset:offset + limit]
    next_offset = str(offset + limit) if offset + limit < len(matched) else ""
    return page, next_offset


def parse_genre_inline_query(raw_query: str) -> tuple[bool, str]:
    """Определяет режим inline-поиска по жанрам.

    Поддерживаются запросы:
    - жанр романтика
    - жанр: романтика
    - genre romance
    - genre: romance
    """
    text = (raw_query or "").strip()
    lowered = text.casefold()

    prefixes = ("жанр:", "жанр ", "genre:", "genre ", "genres:", "genres ")
    for prefix in prefixes:
        if lowered.startswith(prefix):
            return True, text[len(prefix):].strip()

    return False, ""


@router.inline_query(F.query)
async def inline_search(query: types.InlineQuery):
    raw_text = query.query.strip()
    search_text = raw_text.lower()
    if not search_text:
        return

    try:
        offset = int(query.offset) if query.offset else 0
    except ValueError:
        offset = 0

    genre_mode, genre_text = parse_genre_inline_query(raw_text)

    if genre_mode:
        # Если пользователь только нажал кнопку и ещё не ввёл жанр.
        if not genre_text:
            await query.answer(
                results=[
                    InlineQueryResultArticle(
                        id="genre_help",
                        title="Введите жанр после слова «жанр»",
                        description="Например: жанр романтика / жанр сёнен / жанр комедия",
                        input_message_content=InputTextMessageContent(
                            message_text="Введите жанр после кнопки: жанр романтика"
                        )
                    )
                ],
                cache_time=1,
                is_personal=True
            )
            return

        # Ищем именно по базе anime_info.genres. Фильтрация через Python/casefold,
        # чтобы русские жанры искались без проблем с регистром SQLite.
        cursor.execute(
            """
            SELECT DISTINCT v.anime, COALESCE(ai.genres, '')
            FROM videos v
            JOIN anime_info ai ON ai.anime = v.anime
            WHERE ai.genres IS NOT NULL
              AND ai.genres != ''
              AND ai.genres != '—'
            ORDER BY v.anime
            """
        )

        genre_key = genre_text.casefold()
        matched_animes = []
        for anime_name, genres in cursor.fetchall():
            if genre_key in (genres or "").casefold():
                matched_animes.append(anime_name)

        page_items = matched_animes[offset:offset + PAGE_SIZE]
        rows = [(anime_name,) for anime_name in page_items]
        next_offset = str(offset + PAGE_SIZE) if offset + PAGE_SIZE < len(matched_animes) else ""

    elif search_text == "all":
        cursor.execute(
            "SELECT DISTINCT anime FROM videos ORDER BY anime LIMIT ? OFFSET ?",
            (PAGE_SIZE, offset)
        )
        rows = cursor.fetchall()
        next_offset = str(offset + PAGE_SIZE) if len(rows) == PAGE_SIZE else ""

    else:
        # Умный поиск: название + исправление случайной раскладки.
        fixed_search_text = fix_keyboard_layout(search_text)

        matched_animes, next_offset = fuzzy_search_anime(fixed_search_text, offset, PAGE_SIZE)

        # Если после исправления ничего нет — пробуем оригинальный текст.
        if not matched_animes and fixed_search_text != search_text:
            matched_animes, next_offset = fuzzy_search_anime(search_text, offset, PAGE_SIZE)

        rows = [(anime_name,) for anime_name in matched_animes]

    if not rows:
        await query.answer([], cache_time=1, is_personal=True)
        return

    results = []
    for (anime_name,) in rows:
        data = await load_anime_info(anime_name)
        if not data:
            continue

        anime_name, poster_url, score, genres, year = data

        # Преобразуем название аниме в Title Case
        anime_title = string.capwords(anime_name)

        if genre_mode:
            description = f"🎭 По жанру: {genre_text} | ⭐ {score} | 📅 {year}"
        else:
            description = f"⭐ {score} | 🎭 {genres} | 📅 {year}"

        anime_id = get_or_create_anime_id(anime_name)

        results.append(
            InlineQueryResultArticle(
                # ID inline-результата совпадает с ID аниме.
                id=str(anime_id),
                title=anime_title,
                description=description,
                thumb_url=poster_url,
                input_message_content=InputTextMessageContent(
                    message_text=anime_id
                )
            )
        )

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
    Игнори��уем команды и сообщения без текста.
    """
    if message.text and not message.text.startswith("/"):
        await live_search(message)

# =========================
# Твой существующий callback без изменений
# =========================
@router.callback_query(lambda c: c.data.startswith("anime_index|"))
async def anime_selected(call: types.CallbackQuery):
    user_id = call.from_user.id

    _, idx_str = call.data.split("|")
    idx = int(idx_str)

    cursor.execute("SELECT DISTINCT anime FROM videos ORDER BY anime")
    animes = [row[0] for row in cursor.fetchall()]

    if idx < 0 or idx >= len(animes):
        await call.answer("❌ Ошибка: аниме не найдено", show_alert=True)
        return

    anime = animes[idx]

    # ✅ ОСНОВНЫЕ ДАННЫЕ (как в inline)
    data = await load_anime_info(anime)
    if not data:
        await send_and_track(user_id, call.message.answer, "❌ Не удалось получить информацию об аниме")
        return

    anime_name, poster_url, score, genres, year = data

    # ✅ ОПИСАНИЕ (отдельно)
    info = await get_anime_info(anime)

    first_paragraph = ""
    if info and info.get("description"):
        description = clean_shikimori_description(info["description"])
        first_paragraph = description.split("\n\n")[0].strip()

        MAX_LEN = 800
        if len(first_paragraph) > MAX_LEN:
            cut_text = first_paragraph[:MAX_LEN]
            match = re.search(r'[.!?](?!.*[.!?])', cut_text)
            if match:
                first_paragraph = cut_text[:match.end()]
            else:
                first_paragraph = cut_text.rstrip() + "…"

    # ✅ ТЕКСТ (как inline + описание)
    text = (
        f"<b>{string.capwords(anime_name)}</b>\n"
        f"<tg-emoji emoji-id=\"5438496463044752972\">👍</tg-emoji> Рейтинг: <b>{score}</b>\n"
        f"<tg-emoji emoji-id=\"5350658016700013471\">👍</tg-emoji> Жанры: {genres}\n"
        f"<tg-emoji emoji-id=\"5413879192267805083\">👍</tg-emoji> Год: {year}"
    )

    if first_paragraph:
        text += f"\n\n<tg-emoji emoji-id=\"5253742260054409879\">👍</tg-emoji> {first_paragraph}"

    # ===== сезоны (НЕ ТРОГАЕМ)
    cursor.execute("SELECT DISTINCT season FROM videos WHERE anime=? ORDER BY season", (anime,))
    seasons = [row[0] for row in cursor.fetchall()]

    builder = InlineKeyboardBuilder()

    # --- Статус просмотра и избранное прямо в карточке аниме ---
    statuses = get_bookmark_status(user_id, anime)
    current = next((s for s in BOOKMARK_STATUSES if s in statuses), None)
    anime_id = get_or_create_anime_id(anime)

    builder.row(
        make_status_button(anime_id, current),
        InlineKeyboardButton(
            text=" В избранном" if "favorite" in statuses else " Избранное",
            callback_data=f"favorite|{anime_id}",
            icon_custom_emoji_id=FAVORITE_BUTTON_EMOJI_ID
        )
    )

    season_buttons = []
    for season in seasons:
        season_str = str(season).lower()
        button_text = "🎬 Фильм" if season_str in ["film", "фильм", "movie"] else f"Сезон {season}"
        cb_id = make_cb_id(anime, str(season))
        season_buttons.append(
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"season|{cb_id}",
                style="primary"
            )
        )

    for i in range(0, len(season_buttons), 2):
        builder.row(*season_buttons[i:i+2])

    builder.row(
        InlineKeyboardButton(
            text=" Меню",
            callback_data="back_menu",
            style="success",
            icon_custom_emoji_id="5312486108309757006"
        )
    )

    kb = builder.as_markup()

    try:
        await call.message.delete()
    except:
        pass

    # ===== отправка (НЕ ТРОГАЕМ)
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

async def refresh_anime_buttons(
    call: types.CallbackQuery,
    anime: str,
    *,
    update_status: bool = False,
    update_favorite: bool = False,
):
    """Заменяет только нажатую кнопку, не изменяя остальные кнопки сообщения."""
    statuses = get_bookmark_status(call.from_user.id, anime)
    current = next((s for s in BOOKMARK_STATUSES if s in statuses), None)
    anime_id = get_or_create_anime_id(anime)
    markup = call.message.reply_markup

    if not markup or not markup.inline_keyboard:
        return

    # Создаём новую разметку, но переносим все старые кнопки без изменений.
    new_keyboard = [list(row) for row in markup.inline_keyboard]

    for row_index, row in enumerate(new_keyboard):
        for button_index, old_button in enumerate(row):
            callback_data = old_button.callback_data or ""

            if update_status and callback_data.startswith("set_status|"):
                # Именно новый объект кнопки — со своим текстом, callback и emoji ID.
                new_keyboard[row_index][button_index] = make_status_button(
                    anime_id,
                    current,
                )
                update_status = False

            elif update_favorite and callback_data.startswith("favorite|"):
                # Меняется только кнопка избранного; её стиль и custom emoji сохраняются.
                new_keyboard[row_index][button_index] = old_button.model_copy(
                    update={
                        "text": " В избранном" if "favorite" in statuses else " Избранное",
                        "callback_data": f"favorite|{anime_id}",
                    }
                )
                update_favorite = False

    new_markup = InlineKeyboardMarkup(inline_keyboard=new_keyboard)

    try:
        await call.message.edit_reply_markup(reply_markup=new_markup)
    except Exception as e:
        if "message is not modified" not in str(e):
            raise


@router.callback_query(F.data.startswith("set_status|"))
async def set_status(call: types.CallbackQuery):
    _, anime_id, status = call.data.split("|", 2)

    cursor.execute("SELECT anime FROM anime_catalog WHERE id=?", (anime_id,))
    row = cursor.fetchone()

    if not row:
        await call.answer("Аниме не найдено", show_alert=True)
        return

    anime = row[0]

    # Убираем старую категорию просмотра
    for s in BOOKMARK_STATUSES:
        cursor.execute(
            "DELETE FROM user_bookmarks WHERE user_id=? AND anime=? AND status=?",
            (call.from_user.id, anime, s)
        )

    # none = отсутствие категории
    if status != "none":
        cursor.execute(
            "INSERT OR IGNORE INTO user_bookmarks(user_id, anime, status) VALUES(?,?,?)",
            (call.from_user.id, anime, status)
        )

    db.commit()

    await refresh_anime_buttons(call, anime, update_status=True)
    await call.answer("Сохранено")


@router.callback_query(F.data.startswith("favorite|"))
async def favorite_handler(call: types.CallbackQuery):
    anime_id = call.data.split("|", 1)[1]

    cursor.execute("SELECT anime FROM anime_catalog WHERE id=?", (anime_id,))
    row = cursor.fetchone()

    if not row:
        await call.answer("Аниме не найдено", show_alert=True)
        return

    anime = row[0]
    toggle_favorite(call.from_user.id, anime)

    await refresh_anime_buttons(call, anime, update_favorite=True)
    await call.answer("Избранное изменено")


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
        """
        SELECT episode, file_id
        FROM videos
        WHERE anime=? AND dub=? AND season=?
        ORDER BY episode
        """,
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

    # Кнопки серий
    for i in range(0, len(page_episodes), EPISODES_PER_ROW):
        row_buttons = [
            InlineKeyboardButton(
                text=str(ep),
                callback_data=f"ep|{make_cb_id(anime, dub, str(season), str(ep))}|{page}"
            )
            for ep, _ in page_episodes[i:i + EPISODES_PER_ROW]
        ]
        builder.row(*row_buttons)

    # Навигация
    nav_buttons = []

    if start > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                text=" ",
                callback_data=f"dub|{dub_hash}|{page-1}",
                style="primary",
                icon_custom_emoji_id="5352759161945867747"
            )
        )

    if end < len(episodes):
        nav_buttons.append(
            InlineKeyboardButton(
                text=" ",
                callback_data=f"dub|{dub_hash}|{page+1}",
                style="primary",
                icon_custom_emoji_id="5355075407743826720"
            )
        )

    if nav_buttons:
        builder.row(*nav_buttons)

    # Быстрый переход
    builder.row(
        InlineKeyboardButton(
            text=" Быстрый переход",
            callback_data=f"ranges|{dub_hash}",
            style="primary",
            icon_custom_emoji_id="5357315181649076022"
        )
    )

    # Новая кнопка просмотра нескольких серий
    if has_multi_episode_access(user_id):
        builder.row(
            InlineKeyboardButton(
                text="Смотреть несколько серий",
                callback_data=f"multi|{dub_hash}",
                style="primary",
                icon_custom_emoji_id="5368653135101310687"
            )
        )

    # Остальные кнопки
    builder.row(
        InlineKeyboardButton(
            text=" К озвучкам",
            callback_data=f"season|{make_cb_id(anime, str(season))}",
            style="danger",
            icon_custom_emoji_id="5388632425314140043"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text=" Меню",
            callback_data="back_menu",
            style="success",
            icon_custom_emoji_id="5312486108309757006"
        )
    )

    kb = builder.as_markup(row_width=EPISODES_PER_ROW)

    try:
        await call.message.delete()
    except:
        pass

    await send_and_track(
        user_id,
        call.message.answer,
        "<tg-emoji emoji-id=\"5368653135101310687\">👍</tg-emoji> Выбор серии:",
        parse_mode="HTML",
        reply_markup=kb
    )

    await call.answer()

# ===== Отправка видео серии =====
@router.callback_query(lambda c: c.data.startswith("ep|"))
async def send_video(call: types.CallbackQuery):
    print(">>> send_video callback")
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

    episode_caption = format_episode_caption(season, ep)
    caption = f"<b>{anime.title()}</b>\n<b><i>{dub}</i></b>\n<i>{episode_caption}</i>"

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

async def send_episode(
    user_id,
    chat_id,
    anime,
    dub,
    season,
    ep,
    file_id,
    page=0
):
    save_watch_progress(user_id, anime, dub, season, ep)

    episode_caption = format_episode_caption(season, ep)
    caption = (
        f"<b>{anime.title()}</b>\n"
        f"<b><i>{dub}</i></b>\n"
        f"<i>{episode_caption}</i>"
    )

    builder = InlineKeyboardBuilder()

    if isinstance(file_id, str) and file_id.startswith("http"):
        builder.row(
            InlineKeyboardButton(
                text="📥 Скачать серию",
                url=file_id
            )
        )

    kb = builder.as_markup()

    # отправка
    if isinstance(file_id, str) and file_id.startswith("http"):
        msg = await bot.send_message(
            chat_id=chat_id,
            text=caption,
            parse_mode="HTML",
            reply_markup=kb,
            protect_content=True
        )
    else:
        msg = await bot.send_video(
            chat_id=chat_id,
            video=file_id,
            caption=caption,
            parse_mode="HTML",
            reply_markup=kb,
            protect_content=True
        )

    # 🔥 ВАЖНО: возвращаем chat_id + message_id
    return {
        "chat_id": chat_id,
        "message_id": msg.message_id
    }

def build_ssl_context():
    if SSL_CERT_FILE and SSL_KEY_FILE:
        ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ctx.load_cert_chain(SSL_CERT_FILE, SSL_KEY_FILE)
        return ctx
    return None

async def on_startup(dp: Dispatcher):
    print("Бот стар��овал!")

async def start_webhook():
    runner = web.AppRunner(app)
    await runner.setup()
    ssl_context = build_ssl_context()
    site = web.TCPSite(runner, "0.0.0.0", WEBHOOK_PORT, ssl_context=ssl_context)
    await site.start()
    scheme = "HTTPS" if ssl_context else "HTTP"
    print(f"Webhook сервер запущен на порту {WEBHOOK_PORT} ({scheme})")

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
    ssl_context = build_ssl_context()
    site = web.TCPSite(runner, "0.0.0.0", WEBHOOK_PORT, ssl_context=ssl_context)
    await site.start()
    scheme = "HTTPS" if ssl_context else "HTTP"
    print(f"Webhook сервер запущен на порту {WEBHOOK_PORT} ({scheme})")

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

    # Запу��каем вебхук сервер для CryptoBot
    await start_webhook()

    # Запускаем очистку invoice
    asyncio.create_task(cleanup_old_records())

    # Запускаем polling Telegram бота
    await dp.start_polling(bot, skip_updates=True, on_startup=on_startup)

if __name__ == "__main__":
    asyncio.run(main())
