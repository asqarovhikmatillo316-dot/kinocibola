import asyncio
import logging
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatJoinRequest

# ==========================================
# RENDER UCHUN SOXTA VEB-SERVER (DUMMY PORT)
# ==========================================
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler)
    server.serve_forever()

# Portni orqa fonda (background process) ochib qo'yish
threading.Thread(target=run_dummy_server, daemon=True).start()
# ==========================================


# Environment Variables orqali token olish (yoki zaxira token)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8897148620:AAHZY6uE9r0U2RuArYNEZ-3CHeC6ahL_qh4")

# Telegram privat kanallaringiz ro'yxati
CHANNELS = [
    {
        "name": "1-Kanal",
        "url": "https://t.me/+I55yoIA3bYhmZDBi",
        "id": -1003973741534  # 1-kanal ID'si
    },
    {
        "name": "2-Kanal",
        "url": "https://t.me/+8ibfJL_Q_FU5YzEy",
        "id": -1004406015595  # 2-kanal ID'si
    },
]

INSTAGRAM_URL = "https://www.instagram.com/tillobek_asqarov?utm_source=qr&stkn=d291aXk3YnVyamhn"
CONTACT_ADMIN = "https://t.me/Asqarov_Hikmatillo"
TARGET_CHANNEL = "@kinooooooolar"

# Telegram kanallarga so'rov yuborganlarni saqlash
JOIN_REQUESTS = {}

# Instagram tugmasini bosganlarni saqlash
INSTAGRAM_CLICKED = set()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# --- SO'ROVLARNI QABUL QILISH (AVTO-TASDIQLANMAYDI) ---
@dp.chat_join_request()
async def process_join_request(chat_join_request: ChatJoinRequest):
    user_id = chat_join_request.from_user.id
    chat_id = chat_join_request.chat.id
    
    if user_id not in JOIN_REQUESTS:
        JOIN_REQUESTS[user_id] = set()
    
    JOIN_REQUESTS[user_id].add(chat_id)
    print(f"📥 So'rov tushdi: {chat_join_request.from_user.first_name} ({chat_join_request.chat.title} kanaliga)")


async def check_user_subscriptions(user_id: int):
    """
    Foydalanuvchining a'zolik holatini tekshiradi.
    A'zo bo'lmagan kanallar ro'yxatini va instagram holatini qaytaradi.
    """
    unsubscribed_channels = []
    
    for channel in CHANNELS:
        ch_id = channel["id"]
        
        # 1. So'rov yuborganini tekshiramiz
        user_requests = JOIN_REQUESTS.get(user_id, set())
        if ch_id in user_requests:
            continue
            
        # 2. Telegram API orqali tekshiramiz
        try:
            member = await bot.get_chat_member(chat_id=ch_id, user_id=user_id)
            if member.status in ["left", "kicked"]:
                unsubscribed_channels.append(channel)
        except Exception as e:
            print(f"❌ XATOLIK ({channel['name']}): {e}")
            unsubscribed_channels.append(channel)
            
    is_insta_clicked = user_id in INSTAGRAM_CLICKED
    return unsubscribed_channels, is_insta_clicked


async def get_subscription_keyboard(unsubscribed_channels: list, is_insta_clicked: bool) -> InlineKeyboardMarkup:
    """Tugmalarni dinamik holatda yaratadi."""
    buttons = []
    
    # Faqat hali a'zo bo'linmagan Telegram kanallar
    for ch in unsubscribed_channels:
        buttons.append([InlineKeyboardButton(text=f"📢 {ch['name']}ga a'zo bo'lish", url=ch["url"])])
    
    # Instagram tugmasi - Bosilganda alohida havolaga olib o'tadi va bot xotiraga saqlaydi
    if not is_insta_clicked:
        buttons.append([InlineKeyboardButton(text="📸 Instagram sahifamiz", callback_data="go_to_instagram")])
    
    buttons.append([InlineKeyboardButton(text="✅ A'zolikni tekshirish", callback_data="check_sub")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """A'zolikdan o'tgandan keyingi menyu tugmalari"""
    buttons = [
        [InlineKeyboardButton(text="🎬 Kinolarni qidirish", callback_data="search_info")],
        [InlineKeyboardButton(text="ℹ️ Bot haqida", callback_data="about_bot"), InlineKeyboardButton(text="📞 Bog'lanish", url=CONTACT_ADMIN)]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@dp.message(Command("start"))
async def start_handler(message: types.Message):
    unsubbed, is_insta_clicked = await check_user_subscriptions(message.from_user.id)
    
    if not unsubbed and is_insta_clicked:
        text = (
            f"<b>Salom, {message.from_user.first_name}! 👋🍿</b>\n\n"
            f"🎬 <b>Rasmiy Kino qidiruv botiga xush kelibsiz!</b>\n\n"
            f"🍿 Bu yerda siz eng sara va premyera kinolarni HD sifatda topishingiz mumkin.\n\n"
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


# --- INSTAGRAM TUGMASI BOSILGANDA ---
@dp.callback_query(F.data == "go_to_instagram")
async def go_to_instagram_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    INSTAGRAM_CLICKED.add(user_id)  # Bosilganini xotiraga saqlaymiz
    
    # Instagram ilovasini/brauzerini alohida ochish uchun tugma chiqarib beramiz
    insta_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👉 Instagram'ga o'tish (Alohida ochish)", url=INSTAGRAM_URL)],
        [InlineKeyboardButton(text="✅ A'zo bo'ldim, tekshirish", callback_data="check_sub")]
    ])
    
    await callback.message.answer(
        "📸 <b>Quyidagi tugma orqali Instagram sahifamizga o'ting va obuna bo'ling:</b>",
        reply_markup=insta_keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


# --- TEKSHIRISH TUGMASI BOSILGANDA ---
@dp.callback_query(F.data == "check_sub")
async def check_subscription_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    unsubbed, is_insta_clicked = await check_user_subscriptions(user_id)
    
    if not is_insta_clicked:
        await callback.answer("⚠️️ Avval «📸 Instagram sahifamiz» tugmasini bosishingiz shart!", show_alert=True)
        return
        
    if unsubbed:
        await callback.answer("❌ Hali barcha Telegram kanallariga a'zo bo'lmadingiz!", show_alert=True)
        keyboard = await get_subscription_keyboard(unsubbed, is_insta_clicked)
        try:
            await callback.message.edit_reply_markup(reply_markup=keyboard)
        except Exception:
            pass
        return

    # Barcha shartlar bajarilganda:
    await callback.message.delete()
    text = (
        "<b>🎉 Rahmat! A'zolik muvaffaqiyatli tasdiqlandi.</b> ✅\n\n"
        "🍿 <b>Endi sevimli kinoingiz kodini yuborishingiz mumkin!</b>\n"
        "<i>(Masalan: <code>3</code>)</i>"
    )
    await callback.message.answer(text, reply_markup=get_main_menu_keyboard(), parse_mode="HTML")


# --- MENYU TUGMALARI ISHLOVI ---
@dp.callback_query(F.data == "about_bot")
async def about_bot_callback(callback: types.CallbackQuery):
    text = (
        "<b>🤖 Bot haqida ma'lumot:</b>\n\n"
        "🎥 <b>Kino Bot</b> — ushbu bot orqali siz kinolar, seriallar va premyeralarni kodi orqali osongina va tekinga yuklab olishingiz mumkin.\n\n"
        "⚡️ <b>Imkoniyatlar:</b>\n"
        "• Yuqori tezlik va HD sifat 💎\n"
        "• Reklamasiz va qulay qidiruv 🔍\n"
        "• Doimiy yangilanib boruvchi kino baza 📈\n\n"
        "👨‍💻 <b>Bog'lanish:</b> @Asqarov_Hikmatillo"
    )
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data == "search_info")
async def search_info_callback(callback: types.CallbackQuery):
    await callback.message.answer("🔎 Kino izlash uchun shunchaki kodni chatga yozib yuboring (Masalan: <code>3</code>).", parse_mode="HTML")
    await callback.answer()


# --- KINO QIDIRISH HANDLERI ---
@dp.message()
async def search_movie_handler(message: types.Message):
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
        await bot.copy_message(
            chat_id=message.chat.id,
            from_chat_id=TARGET_CHANNEL,
            message_id=int(code)
        )
        await msg.delete()
    except Exception:
        await msg.edit_text(
            f"❌ <b>Kino kodi «{code}» bo'yicha hech narsa topilmadi.</b> 😔\n\n"
            "Kodni to'g'ri kiritganingizni tekshirib ko'ring.",
            parse_mode="HTML"
        )


async def main():
    logging.basicConfig(level=logging.INFO)
    print("🚀 Bot muvaffaqiyatli ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())