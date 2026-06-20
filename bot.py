import asyncio
import os
import re
import random
from aiogram import Bot, Dispatcher, F
from aiogram.types import (Message, InlineKeyboardMarkup, InlineKeyboardButton, 
                           CallbackQuery, InlineQueryResultCachedAudio)
from aiogram.filters import Command
from aiogram.utils.media_group import MediaGroupBuilder

# --- НАСТРОЙКИ ---
# Теперь токен берется из настроек облака Railway (вкладка Variables)
TOKEN = os.getenv("TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

DB_FILE = "tracks.txt"

# --- ФУНКЦИИ БАЗЫ ДАННЫХ ---
def get_next_number():
    if not os.path.exists(DB_FILE) or os.stat(DB_FILE).st_size == 0:
        return 1
    with open(DB_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
        if not lines: return 1
        last_line = lines[-1].strip()
        if last_line and "|" in last_line:
            try: return int(last_line.split("|")[0].strip()) + 1
            except: return len(lines) + 1
    return 1

def save_track_to_db(title, hashtag, file_id, msg_id):
    num = get_next_number()
    clean_tag = hashtag.lower().strip()
    with open(DB_FILE, "a", encoding="utf-8") as f:
        f.write(f"{num} | {title} | {clean_tag} | {file_id} | {msg_id}\n")
    return num

def read_all_tracks():
    if not os.path.exists(DB_FILE): return []
    tracks = []
    with open(DB_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if "|" in line:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) == 5:
                    tracks.append({"num": parts[0], "title": parts[1], "tag": parts[2], "file_id": parts[3], "msg_id": parts[4]})
    return tracks

def get_all_hashtags():
    return sorted(list(set(t["tag"] for t in read_all_tracks())))

# --- ХЭНДЛЕРЫ ---
@dp.message(F.audio, F.caption)
async def auto_catch_audio(message: Message):
    hashtags = re.findall(r"#\w+", message.caption)
    if not hashtags: return
    for tag in hashtags:
        num = save_track_to_db(message.audio.title or "Без названия", tag, message.audio.file_id, message.message_id)
        await message.answer(f"✅ Добавлено: {tag} (№{num})")

@dp.message(Command("show_tags"))
async def show_tags_buttons(message: Message):
    tags = get_all_hashtags()
    if not tags:
        await message.answer("📭 База пуста.")
        return
    keyboard = [[InlineKeyboardButton(text=f"🎵 {t}", callback_data=f"one_{t}"),
                 InlineKeyboardButton(text=f"📦 Плейлист", callback_data=f"pack_{t}")] for t in tags]
    keyboard.append([InlineKeyboardButton(text="🎲 Случайный", callback_data="random_track")])
    await message.answer("Выберите режим:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@dp.callback_query(F.data.startswith("one_"))
async def send_one(callback: CallbackQuery):
    tag = callback.data.replace("one_", "")
    tracks = [t for t in read_all_tracks() if t["tag"] == tag]
    for t in tracks:
        try:
            await bot.send_audio(callback.message.chat.id, t["file_id"], caption=f"🆔 {t['num']} | {t['title']}")
            await asyncio.sleep(0.3)
        except: continue
    await callback.answer()

@dp.callback_query(F.data.startswith("pack_"))
async def send_pack(callback: CallbackQuery):
    tag = callback.data.replace("pack_", "")
    tracks = [t for t in read_all_tracks() if t["tag"] == tag]
    for i in range(0, len(tracks), 10):
        group = MediaGroupBuilder()
        for t in tracks[i:i+10]: group.add_audio(media=t["file_id"], caption=t["title"])
        await bot.send_media_group(callback.message.chat.id, media=group.build())
        await asyncio.sleep(0.5)
    await callback.answer()

@dp.callback_query(F.data == "random_track")
async def send_random(callback: CallbackQuery):
    tracks = read_all_tracks()
    if tracks:
        t = random.choice(tracks)
        await bot.send_audio(callback.message.chat.id, t["file_id"], caption=f"🎲 {t['title']}")
    await callback.answer()

@dp.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer("📚 Бот работает! Команды: /show_tags")

# --- ЗАПУСК ---
async def main():
    # Очистка старых хуков для чистого запуска
    await bot.delete_webhook(drop_pending_updates=True)
    print("Бот успешно запущен напрямую!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
