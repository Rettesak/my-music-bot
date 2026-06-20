import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command

TOKEN = os.getenv("TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()
DB_FILE = "tracks.txt"

# --- ФУНКЦИИ БАЗЫ (с поддержкой прослушиваний) ---
def read_all_tracks():
    if not os.path.exists(DB_FILE): return []
    tracks = []
    with open(DB_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if "|" in line:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 5:
                    tracks.append({"num": parts[0], "title": parts[1], "tag": parts[2], "file_id": parts[3], "plays": int(parts[4])})
    return tracks

def update_plays(num):
    tracks = read_all_tracks()
    for t in tracks:
        if t["num"] == str(num):
            t["plays"] += 1
    with open(DB_FILE, "w", encoding="utf-8") as f:
        for t in tracks:
            f.write(f"{t['num']} | {t['title']} | {t['tag']} | {t['file_id']} | {t['plays']}\n")

# --- ХЭНДЛЕРЫ ---
@dp.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer("📚 **Команды бота:**\n/show_tags - список тегов\n/top - топ прослушиваний\n/delete [номер] - удалить трек", parse_mode="Markdown")

@dp.message(Command("show_tags"))
async def show_tags(message: Message):
    tags = sorted(list(set(t["tag"] for t in read_all_tracks())))
    if not tags: await message.answer("📭 База пуста.")
    else:
        kb = [[InlineKeyboardButton(text=f"🎵 {t}", callback_data=f"one_{t}")] for t in tags]
        await message.answer("Выберите тег:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("one_"))
async def send_one(callback: CallbackQuery):
    tag = callback.data.replace("one_", "")
    tracks = [t for t in read_all_tracks() if t["tag"] == tag]
    for t in tracks:
        update_plays(t["num"])
        await bot.send_audio(
            callback.message.chat.id, t["file_id"], 
            caption=f"🆔 {t['num']} | {t['title']} (Слушали: {t['plays']+1})",
            reply_to_message_id=callback.message.message_id
        )
    await callback.answer()

@dp.message(Command("delete"))
async def delete_track(message: Message):
    try:
        num = message.text.split()[1]
        tracks = [t for t in read_all_tracks() if t["num"] != num]
        with open(DB_FILE, "w", encoding="utf-8") as f:
            for t in tracks: f.write(f"{t['num']} | {t['title']} | {t['tag']} | {t['file_id']} | {t['plays']}\n")
        await message.answer(f"✅ Трек №{num} удален.")
    except: await message.answer("Ошибка. Используй: /delete [номер]")

@dp.message(Command("top"))
async def show_top(message: Message):
    tracks = sorted(read_all_tracks(), key=lambda x: x["plays"], reverse=True)[:5]
    text = "🔥 **Топ треков:**\n" + "\n".join([f"{t['title']} — {t['plays']} раз" for t in tracks])
    await message.answer(text, parse_mode="Markdown")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
