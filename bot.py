import time
import json
import requests
import telebot
from dotenv import load_dotenv
import os

# Загружаем переменные из .env файла
load_dotenv()

# ==================== НАСТРОЙКИ ====================
TG_TOKEN = os.getenv("TG_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
VK_TOKEN = os.getenv("VK_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))

if not all([TG_TOKEN, CHANNEL_ID, VK_TOKEN, GROUP_ID]):
	print("❌ Ошибка: Не все переменные найдены в .env файле!")
	exit(1)
print (f"✅ Токены успешно загружены (Группа: {GROUP_ID})")
# ===================================================

bot = telebot.TeleBot(TG_TOKEN)
LAST_POST_FILE = "last_post.json"

def load_last_post():
    try:
        with open(LAST_POST_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("last_id", 0)
    except:
        return 0

def save_last_post(post_id):
    with open(LAST_POST_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_id": post_id}, f)

def get_new_posts():
    last_id = load_last_post()
    
    url = "https://api.vk.com/method/wall.get"
    params = {
        'owner_id': GROUP_ID,
        'count': 30,
        'v': '5.131',
        'access_token': VK_TOKEN
    }
    
    try:
        response = requests.get(url, params=params).json()
        
        if 'error' in response:
            print(f"❌ Ошибка VK API: {response['error']['error_msg']}")
            print(f"Код ошибки: {response['error'].get('error_code')}")
            return []
        
        posts = response['response']['items']
        print(f"📥 Получено постов из ВК: {len(posts)}")
        
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
        return []
    
    if not posts:
        return []
    
    # Первый запуск - запоминаем последний пост и не отправляем
    if last_id == 0:
        max_id = max(p["id"] for p in posts)
        save_last_post(max_id)
        print(f"🎯 Первый запуск. Запомнили последний ID: {max_id}")
        print(f"Новые посты будут отправляться при следующей проверке")
        return []
    
    # Ищем новые посты
    new_posts = []
    for p in reversed(posts):  # от старых к новым
        if p["id"] > last_id and not p.get("is_pinned", False):
            new_posts.append(p)
    
    if new_posts:
        # Сохраняем ID самого нового поста
        save_last_post(new_posts[-1]["id"])
        print(f"✨ Найдено {len(new_posts)} новых постов")
        for p in new_posts:
            print(f"  - Пост ID {p['id']} от {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(p['date']))}")
    
    return new_posts

def send_post_to_channel(post):
    text = post.get("text", "").strip()
    
    # Получаем фото из вложений
    attachments = post.get("attachments", [])
    photos = []
    
    for att in attachments:
        if att["type"] == "photo":
            sizes = att["photo"]["sizes"]
            # Ищем самое большое фото
            best = max(sizes, key=lambda s: s.get("width", 0) * s.get("height", 0))
            photos.append(best["url"])
    
    try:
        if photos:
            if len(photos) == 1:
                # Отправляем одно фото с подписью (только текст поста)
                bot.send_photo(CHANNEL_ID, photos[0], caption=text[:1024] if text else "")
                print(f"  📸 Отправлено с 1 фото")
            else:
                # Отправляем несколько фото, первое с подписью
                media = [telebot.types.InputMediaPhoto(photos[0])]
                for photo_url in photos[1:]:
                    media.append(telebot.types.InputMediaPhoto(photo_url))
                if text:
                    media[0].caption = text[:1024]
                bot.send_media_group(CHANNEL_ID, media)
                print(f"  📸📸 Отправлено с {len(photos)} фото")
        else:
            # Без фото - просто текст
            if text:
                bot.send_message(CHANNEL_ID, text[:4096])
                print(f"  📝 Отправлен текстовый пост")
            else:
                print(f"  ⚠️ Пост без текста и фото — пропущен")
        
        print(f"✅ Пост {post['id']} успешно отправлен в Telegram")
    except Exception as e:
        print(f"❌ Ошибка отправки в TG: {e}")

# ==================== ЗАПУСК ====================
print("🤖 Бот запущен")
print(f"📡 Отслеживается группа ВК: {GROUP_ID}")
print(f"📨 Канал Telegram: {CHANNEL_ID}")
print("⏱️  Проверка каждый час")
print("─" * 50)

while True:
    try:
        new_posts = get_new_posts()
        
        for post in new_posts:
            print(f"\n📬 Обработка поста {post['id']}...")
            send_post_to_channel(post)
        
        if not new_posts:
            print(".", end="", flush=True)  # Точка вместо пустой строки
        
    except Exception as e:
        print(f"\n❌ Общая ошибка: {e}")
    
    time.sleep(3600)  # Проверка каждую минуту (для продакшена поставь 300-600)
