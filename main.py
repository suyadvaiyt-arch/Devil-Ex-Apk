import asyncio
import logging
import os
import re
import sqlite3
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
OWNER_IDS = {int(x.strip()) for x in os.getenv("OWNER_IDS", "").split(",") if x.strip().isdigit()}
CHANNEL_ID = os.getenv("CHANNEL_ID", "").strip()  # e.g. @yourchannel or -1001234567890
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "").strip()  # e.g. https://t.me/yourchannel
WELCOME_TEXT = os.getenv(
    "WELCOME_TEXT",
    "Welcome to Devil Ex Apk Download Bot!\n\nএখানে আপনার পছন্দের অ্যাপের APK সরাসরি পাবেন।"
)
WELCOME_BANNER_FILE_ID = os.getenv("WELCOME_BANNER_FILE_ID", "").strip()
DB_PATH = os.getenv("DB_PATH", "bot_data.sqlite3")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("devil-ex-apk-bot")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is required.")
if not OWNER_IDS:
    raise RuntimeError("OWNER_IDS environment variable is required (one or more numeric Telegram user IDs).")

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS apps (
                app_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                version TEXT NOT NULL,
                developer TEXT NOT NULL,
                apk_file_id TEXT NOT NULL,
                logo_file_id TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                downloads INTEGER DEFAULT 0
            )
        """)


def is_admin(user_id: int) -> bool:
    return user_id in OWNER_IDS


def home_keyboard(is_owner=False):
    rows = [[KeyboardButton(text="📦 Browse Apps"), KeyboardButton(text="ℹ️ Help")]]
    if is_owner:
        rows.append([KeyboardButton(text="⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add App", callback_data="admin:add")],
        [InlineKeyboardButton(text="📋 App List", callback_data="admin:list"),
         InlineKeyboardButton(text="📊 Statistics", callback_data="admin:stats")],
        [InlineKeyboardButton(text="❌ Delete App", callback_data="admin:delete_help")]
    ])


async def joined_channel(user_id: int) -> bool:
    if not CHANNEL_ID:
        return True
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception as exc:
        log.warning("Channel membership check failed: %s", exc)
        return False


async def require_join(message: Message) -> bool:
    if await joined_channel(message.from_user.id):
        return True
    kb = InlineKeyboardBuilder()
    if CHANNEL_LINK:
        kb.button(text="📢 Join Channel", url=CHANNEL_LINK)
    kb.button(text="✅ I've Joined — Check", callback_data="check_join")
    await message.answer(
        "বট ব্যবহার করতে আগে আমাদের Telegram Channel-এ Join করুন।",
        reply_markup=kb.as_markup()
    )
    return False


async def send_app(chat_id: int, app_id: str):
    with db() as con:
        app = con.execute("SELECT * FROM apps WHERE app_id = ?", (app_id,)).fetchone()
    if not app:
        await bot.send_message(chat_id, "দুঃখিত, এই অ্যাপটি পাওয়া যায়নি। সঠিক Download Link ব্যবহার করুন।")
        return
    caption = (
        f"📱 <b>{app['name']}</b>\n"
        f"🆕 Version: <code>{app['version']}</code>\n"
        f"👨‍💻 Developer: <b>{app['developer']}</b>\n"
        f"📦 File: APK\n"
        f"⬇️ Downloads: {app['downloads'] + 1}\n\n"
        "— <b>Devil Ex Apk</b>"
    )
    try:
        if app["logo_file_id"]:
            await bot.send_photo(chat_id, app["logo_file_id"], caption=caption)
        await bot.send_document(
            chat_id,
            app["apk_file_id"],
            caption=f"📥 <b>{app['name']} — APK Download</b>\nVersion: {app['version']}\nDeveloper: {app['developer']}"
        )
        with db() as con:
            con.execute("UPDATE apps SET downloads = downloads + 1 WHERE app_id = ?", (app_id,))
    except Exception:
        log.exception("Failed to send app %s", app_id)
        await bot.send_message(chat_id, "APK পাঠানো যায়নি। Admin-কে জানাও।")


class AddApp(StatesGroup):
    name = State()
    version = State()
    developer = State()
    apk = State()
    logo = State()


class DeleteApp(StatesGroup):
    app_id = State()


@dp.message(Command("start"))
async def start_cmd(message: Message, command: CommandObject):
    if not await require_join(message):
        return
    payload = (command.args or "").strip()
    if payload.startswith("app_"):
        app_id = payload[4:]
        await send_app(message.chat.id, app_id)
        return
    text = f"👋 <b>{WELCOME_TEXT}</b>\n\nনিচের Menu থেকে প্রয়োজনীয় অপশন বেছে নিন।"
    if WELCOME_BANNER_FILE_ID:
        await message.answer_photo(WELCOME_BANNER_FILE_ID, caption=text, reply_markup=home_keyboard(is_admin(message.from_user.id)))
    else:
        await message.answer(text, reply_markup=home_keyboard(is_admin(message.from_user.id)))


@dp.callback_query(F.data == "check_join")
async def check_join_cb(call: CallbackQuery):
    if await joined_channel(call.from_user.id):
        await call.message.answer("✅ Channel membership verified. এখন /start দিন।", reply_markup=home_keyboard(is_admin(call.from_user.id)))
    else:
        await call.answer("আপনাকে আগে Channel Join করতে হবে।", show_alert=True)


@dp.message(Command("getfileid"))
async def get_file_id_cmd(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ এই Command শুধু Admin-এর জন্য।")
        return
    await message.answer("Welcome Banner-এর Photo পাঠান। আমি Photo-এর file_id দেখিয়ে দেব; সেটি Railway-এর WELCOME_BANNER_FILE_ID Variable-এ বসান।")


@dp.message(F.photo)
async def show_photo_file_id(message: Message):
    if is_admin(message.from_user.id):
        await message.answer(f"Photo file_id:\n<code>{message.photo[-1].file_id}</code>")


@dp.message(Command("help"))
@dp.message(F.text == "ℹ️ Help")
async def help_cmd(message: Message):
    await message.answer(
        "📌 <b>ব্যবহারবিধি</b>\n"
        "• Channel-এর Download বাটনে চাপুন।\n"
        "• Bot নির্দিষ্ট APK পাঠিয়ে দেবে।\n"
        "• কোনো সমস্যা হলে Channel Admin-এর সাথে যোগাযোগ করুন।"
    )


@dp.message(F.text == "📦 Browse Apps")
async def browse_apps(message: Message):
    if not await require_join(message):
        return
    with db() as con:
        apps = con.execute("SELECT app_id, name, version FROM apps ORDER BY created_at DESC").fetchall()
    if not apps:
        await message.answer("এখনো কোনো অ্যাপ যোগ করা হয়নি।")
        return
    kb = InlineKeyboardBuilder()
    for app in apps:
        kb.button(text=f"{app['name']} · v{app['version']}", callback_data=f"get:{app['app_id']}")
    kb.adjust(1)
    await message.answer("📦 <b>Available Apps</b>\nযে অ্যাপটি চান সেটি নির্বাচন করুন:", reply_markup=kb.as_markup())


@dp.callback_query(F.data.startswith("get:"))
async def get_app_cb(call: CallbackQuery):
    if not await joined_channel(call.from_user.id):
        await call.answer("আগে Channel Join করুন।", show_alert=True)
        return
    await call.answer()
    await send_app(call.message.chat.id, call.data.split(":", 1)[1])


@dp.message(Command("admin"))
@dp.message(F.text == "⚙️ Admin Panel")
async def admin_cmd(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ এই Panel শুধু Admin-এর জন্য।")
        return
    await message.answer("⚙️ <b>Devil Ex Apk — Admin Panel</b>", reply_markup=admin_keyboard())


@dp.callback_query(F.data == "admin:add")
async def add_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("Not authorized", show_alert=True); return
    await state.set_state(AddApp.name)
    await call.message.answer("অ্যাপের নাম লিখুন:")
    await call.answer()


@dp.message(AddApp.name)
async def add_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip()[:100])
    await state.set_state(AddApp.version)
    await message.answer("অ্যাপের Version লিখুন (যেমন 1.2.0):")


@dp.message(AddApp.version)
async def add_version(message: Message, state: FSMContext):
    await state.update_data(version=message.text.strip()[:40])
    await state.set_state(AddApp.developer)
    await message.answer("Developer-এর নাম লিখুন:")


@dp.message(AddApp.developer)
async def add_developer(message: Message, state: FSMContext):
    await state.update_data(developer=message.text.strip()[:80])
    await state.set_state(AddApp.apk)
    await message.answer("এখন APK ফাইলটি Document হিসেবে পাঠান (APK file attach করুন):")


@dp.message(AddApp.apk)
async def add_apk(message: Message, state: FSMContext):
    if not message.document or not (message.document.file_name or "").lower().endswith(".apk"):
        await message.answer("একটি .apk ফাইল Document হিসেবে পাঠান।")
        return
    await state.update_data(apk_file_id=message.document.file_id)
    await state.set_state(AddApp.logo)
    await message.answer("অ্যাপের Logo/Image পাঠান, অথবা Logo বাদ দিতে /skip লিখুন:")


@dp.message(AddApp.logo, Command("skip"))
async def add_skip_logo(message: Message, state: FSMContext):
    await save_app(message, state, "")


@dp.message(AddApp.logo, F.photo)
async def add_logo(message: Message, state: FSMContext):
    await save_app(message, state, message.photo[-1].file_id)


async def save_app(message: Message, state: FSMContext, logo_file_id: str):
    data = await state.get_data()
    app_id = os.urandom(4).hex()
    with db() as con:
        con.execute(
            "INSERT INTO apps (app_id,name,version,developer,apk_file_id,logo_file_id) VALUES (?,?,?,?,?,?)",
            (app_id, data["name"], data["version"], data["developer"], data["apk_file_id"], logo_file_id)
        )
    await state.clear()
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start=app_{app_id}"
    await message.answer(
        f"✅ <b>অ্যাপ সফলভাবে যোগ হয়েছে!</b>\n\n"
        f"Name: {data['name']}\nVersion: {data['version']}\n"
        f"Download Link:\n<code>{link}</code>\n\n"
        "এই Link Channel-এর পোস্টে ব্যবহার করুন।",
        reply_markup=admin_keyboard()
    )


@dp.callback_query(F.data == "admin:list")
async def admin_list(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Not authorized", show_alert=True); return
    with db() as con:
        apps = con.execute("SELECT app_id,name,version,downloads FROM apps ORDER BY created_at DESC").fetchall()
    if not apps:
        await call.message.answer("কোনো অ্যাপ নেই।")
    else:
        lines = ["📋 <b>App List</b>"]
        for a in apps:
            lines.append(f"• <b>{a['name']}</b> v{a['version']} — ID: <code>{a['app_id']}</code> — {a['downloads']} downloads")
        await call.message.answer("\n".join(lines))
    await call.answer()


@dp.callback_query(F.data == "admin:stats")
async def admin_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Not authorized", show_alert=True); return
    with db() as con:
        row = con.execute("SELECT COUNT(*) AS apps, COALESCE(SUM(downloads),0) AS downloads FROM apps").fetchone()
    await call.message.answer(f"📊 <b>Statistics</b>\nApps: {row['apps']}\nDownloads: {row['downloads']}")
    await call.answer()


@dp.callback_query(F.data == "admin:delete_help")
async def delete_help(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("Not authorized", show_alert=True); return
    await state.set_state(DeleteApp.app_id)
    await call.message.answer("যে App ID মুছতে চান সেটি পাঠান। /cancel লিখলে বাতিল হবে।")
    await call.answer()


@dp.message(DeleteApp.app_id, Command("cancel"))
async def delete_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Delete বাতিল করা হয়েছে।")


@dp.message(DeleteApp.app_id)
async def delete_app(message: Message, state: FSMContext):
    app_id = message.text.strip()
    with db() as con:
        cur = con.execute("DELETE FROM apps WHERE app_id = ?", (app_id,))
    await state.clear()
    await message.answer("✅ App deleted." if cur.rowcount else "এই App ID পাওয়া যায়নি।")


async def main():
    init_db()
    log.info("Starting Devil Ex Apk bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
