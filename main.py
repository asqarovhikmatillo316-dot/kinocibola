import os
import logging
from aiohttp import web

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatJoinRequest
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# =========================
# LOGGING
# =========================
logging.basicConfig(level=logging.INFO)

# =========================
# ENV SOZLAMALARI
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")
WEBHOOK_PATH = "/telegram-webhook"
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "kino-bot-secret-2026")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi!")

if not RENDER_EXTERNAL_URL:
    raise RuntimeError("RENDER_EXTERNAL_URL topilmadi!")

WEBHOOK_URL = f"{RENDER_EXTERNAL_URL}{WEBHOOK_PATH}"

# =========================
# BOT VA KANAL SOZLAMALARI
# =========================
CHANNELS = [
    {
        "name": "1-Kanal",
        "url": "https://t.me/+I55yoIA3bYhmZDBi",
        "id": -1003973741534
    },
    {
        "name": "2-Kanal",
        "url": "https://t.me/+8ibfJL_Q_FU5YzEy",
        "id": -1004406015595
    },
]

INSTAGRAM_URL = "https://www.instagram.com/tillobek_asqarov?utm_source=qr&stkn=d291aXk3YnVyamhn"
CONTACT_ADMIN = "https://t.me/Asqarov_Hikmatillo"
TARGET_CHANNEL = "@kinooooooolar"

JOIN_REQUESTS = {}
INSTAGRAM_CLICKED = set()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# =========================
# HANDLERS & LOGIC
# =========================
@dp.chat_join_request()
async def process_join_request(chat_join_request: ChatJoinRequest):
    user_id = chat_join_request.from_user.id
    chat_id = chat_join_request.chat.id

    if user_id not in JOIN_REQUESTS:
        JOIN_REQUESTS[user_id] = set()

    JOIN_REQUESTS[user_id].add(chat_id)


async def check_user_subscriptions(user_id: int):
    unsubscribed_channels = []

    for channel in CHANNELS:
        ch_id = channel["id"]
        user_requests = JOIN_REQUESTS.get(user_id, set())

        if ch_id in user_requests:
            continue

        try:
            member = await bot.get_chat_member(chat_id=ch_id, user_id=user_id)
            if member.status in ["left", "kicked"]:
                unsubscribed_channels.append(channel)
        except Exception as e:
            logging.error(f"Xatolik ({channel['name']}): {e}")
            unsubscribed_channels.append(channel)

    is_insta_clicked = user_id in INSTAGRAM_CLICKED
    return unsubscribed_channels, is_insta_clicked


async def get_subscription_keyboard(unsubscribed_channels: list, is_insta_clicked: bool):
    buttons = []
    for ch in unsubscribed_channels:
        buttons.append([InlineKeyboardButton(text=f"📢 {ch['name']}ga a'zo bo'lish", url=ch["url"])])

    if not is_insta_clicked:
        buttons.append([InlineKeyboardButton(text="📸 Instagram sahifamiz", callback_data="go_to_instagram")])

    buttons.append([InlineKeyboardButton(text="✅ A'zolikni tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_main_menu_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🎬 Kinolarni qidirish", callback_data="search_info")],
        [InlineKeyboardButton(text="ℹ️ Bot haqida", callback_data="about_bot")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@dp.message(Command("start"))
async def start_handler(message: types.Message):
    unsubbed, is_insta_clicked = await check_user_subscriptions(message.from_user.id)

    if not unsubbed and is_insta_clicked:
        text = (
            f"<b>Salom, {message.from_user.first_name}! 👋🍿</b>\n\n"
            f"🎬 <b>Rasmiy Kino qidiruv botiga xush kelibsiz!</b>\n\n"
            f"👉 Kino ko'rish uchun kino kodini yuboring (Masalan: <code>3</code>)."
        )
        await message.answer(text, reply_markup=get_main_menu_keyboard(), parse_mode="HTML")
    else:
        text = (
            f"<b>Salom, {message.from_user.first_name}! 👋✨</b>\n\n"
            f"🤖 <b>Botimiz xizmatlaridan to'liq va bepul foydalanish uchun</b> quyidagi rasmiy kanallarga hamda Instagram sahifamizga a'zo bo'ling:\n\n"
            f"📌 <i>A'zo bo'lib bo'lgach, «✅ A'zolikni tekshirish» tugmasini bosing!</i>"
        )
        keyboard = await get_subscription_keyboard(unsubbed, is_insta_clicked)
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@dp.callback_query(F.data == "go_to_instagram")
async def go_to_instagram_callback(callback: types.CallbackQuery):
    insta_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👉 Instagram'ga o'tish", url=INSTAGRAM_URL, callback_data="track_insta")],
            [InlineKeyboardButton(text="✅ A'zo bo'ldim, tekshirish", callback_data="check_sub")]
        ]
    )
    await callback.message.answer(
        "📸 <b>Quyidagi tugma orqali Instagram sahifamizga o'ting va obuna bo'ling:</b>",
        reply_markup=insta_keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data == "track_insta")
async def track_insta_callback(callback: types.CallbackQuery):
    INSTAGRAM_CLICKED.add(callback.from_user.id)
    await callback.answer()


@dp.callback_query(F.data == "check_sub")
async def check_subscription_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    # URL tugmalari callback bermasligi sababli "Instagram sahifamiz" oynasiga kirganligini belgilaymiz
    INSTAGRAM_CLICKED.add(user_id)
    
    unsubbed, is_insta_clicked = await check_user_subscriptions(user_id)

    if unsubbed:
        await callback.answer("❌ Hali barcha Telegram kanallariga a'zo bo'lmadingiz!", show_alert=True)
        keyboard = await get_subscription_keyboard(unsubbed, is_insta_clicked)
        try:
            await callback.message.edit_reply_markup(reply_markup=keyboard)
        except Exception:
            pass
        return

    await callback.message.delete()
    text = (
        "<b>🎉 Rahmat! A'zolik muvaffaqiyatli tasdiqlandi.</b> ✅\n\n"
        "🍿 <b>Endi sevimli kinoingiz kodini yuborishingiz mumkin!</b>\n"
        "<i>(Masalan: <code>3</code>)</i>"
    )
    await callback.message.answer(text, reply_markup=get_main_menu_keyboard(), parse_mode="HTML")


@dp.callback_query(F.data == "about_bot")
async def about_bot_callback(callback: types.CallbackQuery):
    about_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📞 Bog'lanish", url=CONTACT_ADMIN)]
        ]
    )
    text = (
        "<b>🤖 Bot haqida ma'lumot:</b>\n\n"
        "🎥 <b>Kino Bot</b> — ushbu bot orqali siz kinolar va seriallarni kodi orqali osongina yuklab olishingiz mumkin.\n\n"
        "⚡️ <b>Imkoniyatlar:</b>\n"
        "• Yuqori tezlik va HD sifat 💎\n"
        "• Reklamasiz va qulay qidiruv 🔍\n"
        "• Doimiy yangilanib boruvchi kino baza 📈"
    )
    await callback.message.answer(text, reply_markup=about_keyboard, parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data == "search_info")
async def search_info_callback(callback: types.CallbackQuery):
    await callback.message.answer("🔎 Kino izlash uchun shunchaki kodni chatga yozib yuboring (Masalan: <code>3</code>).", parse_mode="HTML")
    await callback.answer()


@dp.message()
async def search_movie_handler(message: types.Message):
    if not message.text:
        return

    unsubbed, is_insta_clicked = await check_user_subscriptions(message.from_user.id)
    if unsubbed or not is_insta_clicked:
        text = "<b>⚠️ Botdan foydalanish uchun avval barcha kanallarga va Instagram sahifamizga o'tishingiz shart:</b> 🛑"
        keyboard = await get_subscription_keyboard(unsubbed, is_insta_clicked)
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        return

    code = message.text.strip()
    if not code.isdigit():
        await message.answer("⚠️ Iltimos, faqat raqamlardan iborat kino kodini yuboring (Masalan: <code>3</code>). 🔢", parse_mode="HTML")
        return

    msg = await message.answer("🔎 <i>Kino qidirilmoqda, biroz kuting...</i> 🍿", parse_mode="HTML")

    try:
        await bot.copy_message(chat_id=message.chat.id, from_chat_id=TARGET_CHANNEL, message_id=int(code))
        await msg.delete()
    except Exception:
        await msg.edit_text(f"❌ <b>Kino kodi «{code}» bo'yicha hech narsa topilmadi.</b> 😔", parse_mode="HTML")


# =========================
# WEBHOOK EVENTS
# =========================
async def on_startup(bot: Bot):
    await bot.set_webhook(
        url=WEBHOOK_URL,
        secret_token=WEBHOOK_SECRET,
        drop_pending_updates=True
    )
    logging.info(f"Webhook muvaffaqiyatli o'rnatildi: {WEBHOOK_URL}")


async def on_shutdown(bot: Bot):
    await bot.delete_webhook()
    await bot.session.close()


dp.startup.register(on_startup)
dp.shutdown.register(on_shutdown)

# =========================
# MAIN APP
# =========================
app = web.Application()

SimpleRequestHandler(
    dispatcher=dp,
    bot=bot,
    secret_token=WEBHOOK_SECRET
).register(app, path=WEBHOOK_PATH)

setup_application(app, dp, bot=bot)

if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    web.run_app(app, host="0.0.0.0", port=port)
