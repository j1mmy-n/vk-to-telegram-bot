import json
import logging
import os
import signal
import sys
from io import BytesIO
from logging.handlers import RotatingFileHandler
from pathlib import Path
from threading import Event
from urllib.parse import urlparse

import requests
import telebot
from dotenv import load_dotenv
from telebot.apihelper import ApiTelegramException

load_dotenv()

VK_API_URL = "https://api.vk.com/method/wall.get"
VK_API_VERSION = "5.199"
TELEGRAM_MEDIA_GROUP_MAX_ITEMS = 10

TG_TOKEN = os.getenv("TG_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
VK_TOKEN = os.getenv("VK_TOKEN")
GROUP_ID_RAW = os.getenv("GROUP_ID")

CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "3600"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
PHOTO_MAX_BYTES = int(os.getenv("PHOTO_MAX_BYTES", str(20 * 1024 * 1024)))
LAST_POST_FILE = Path(os.getenv("LAST_POST_FILE", "last_post.json"))
LOG_FILE = Path(os.getenv("LOG_FILE", "logs/bot.log"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", str(10 * 1024 * 1024)))
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))

stop_event = Event()


def configure_logging():
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        handlers=[console_handler, file_handler],
        force=True,
    )


configure_logging()
logger = logging.getLogger("vk-to-telegram-bot")


def validate_settings():
    missing = [
        name
        for name, value in (
            ("TG_TOKEN", TG_TOKEN),
            ("CHANNEL_ID", CHANNEL_ID),
            ("VK_TOKEN", VK_TOKEN),
            ("GROUP_ID", GROUP_ID_RAW),
        )
        if not value
    ]
    if missing:
        logger.error(
            "Не заданы обязательные переменные окружения: %s",
            ", ".join(missing),
        )
        raise SystemExit(1)

    try:
        group_id = int(GROUP_ID_RAW)
    except ValueError:
        logger.error("GROUP_ID должен быть целым числом")
        raise SystemExit(1)

    if CHECK_INTERVAL <= 0:
        logger.error("CHECK_INTERVAL должен быть больше нуля")
        raise SystemExit(1)

    if REQUEST_TIMEOUT <= 0:
        logger.error("REQUEST_TIMEOUT должен быть больше нуля")
        raise SystemExit(1)

    if PHOTO_MAX_BYTES <= 0:
        logger.error("PHOTO_MAX_BYTES должен быть больше нуля")
        raise SystemExit(1)

    return group_id


GROUP_ID = validate_settings()
bot = telebot.TeleBot(TG_TOKEN)


def load_last_post():
    try:
        with LAST_POST_FILE.open("r", encoding="utf-8") as file:
            return int(json.load(file).get("last_id", 0))
    except FileNotFoundError:
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        logger.warning("Не удалось прочитать %s: %s", LAST_POST_FILE, error)
        return 0


def save_last_post(post_id):
    LAST_POST_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = LAST_POST_FILE.with_suffix(f"{LAST_POST_FILE.suffix}.tmp")

    with temporary_file.open("w", encoding="utf-8") as file:
        json.dump({"last_id": post_id}, file)
        file.flush()
        os.fsync(file.fileno())

    temporary_file.replace(LAST_POST_FILE)


def get_new_posts():
    last_id = load_last_post()
    params = {
        "owner_id": GROUP_ID,
        "count": 30,
        "v": VK_API_VERSION,
        "access_token": VK_TOKEN,
    }

    try:
        response = requests.get(
            VK_API_URL,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as error:
        logger.exception("Ошибка запроса к VK API: %s", error)
        return []

    if "error" in payload:
        error = payload["error"]
        logger.error(
            "Ошибка VK API %s: %s",
            error.get("error_code"),
            error.get("error_msg"),
        )
        return []

    try:
        posts = payload["response"]["items"]
    except (KeyError, TypeError):
        logger.error("VK API вернул неожиданный ответ")
        return []

    logger.info("Получено постов из VK: %s", len(posts))

    if not posts:
        return []

    if last_id == 0:
        newest_id = max(post["id"] for post in posts)
        save_last_post(newest_id)
        logger.info(
            "Первый запуск: сохранён ID последнего поста %s",
            newest_id,
        )
        return []

    new_posts = [
        post
        for post in reversed(posts)
        if post["id"] > last_id and not post.get("is_pinned", False)
    ]

    if new_posts:
        logger.info("Найдено новых постов: %s", len(new_posts))

    return new_posts


def get_photo_urls(post):
    photo_urls = []

    for attachment in post.get("attachments", []):
        if attachment.get("type") != "photo":
            continue

        sizes = attachment.get("photo", {}).get("sizes", [])
        if not sizes:
            continue

        best = max(
            sizes,
            key=lambda size: size.get("width", 0) * size.get("height", 0),
        )
        if best.get("url"):
            photo_urls.append(best["url"])

    return photo_urls


def build_post_url(post):
    owner_id = post.get("owner_id", GROUP_ID)
    post_id = post.get("id")

    if not post_id:
        return None

    return f"https://vk.com/wall{owner_id}_{post_id}"


def get_photo_filename(url, post_id, photo_number):
    path = urlparse(url).path
    suffix = Path(path).suffix

    if not suffix or len(suffix) > 10:
        suffix = ".jpg"

    return f"vk_post_{post_id}_{photo_number}{suffix}"


def download_photo(url, post_id, photo_number):
    try:
        with requests.get(
            url,
            stream=True,
            timeout=REQUEST_TIMEOUT,
        ) as response:
            response.raise_for_status()

            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > PHOTO_MAX_BYTES:
                logger.warning(
                    "Пост %s: фото %s больше лимита PHOTO_MAX_BYTES (%s > %s)",
                    post_id,
                    photo_number,
                    content_length,
                    PHOTO_MAX_BYTES,
                )
                return None

            photo = BytesIO()
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue

                photo.write(chunk)
                if photo.tell() > PHOTO_MAX_BYTES:
                    logger.warning(
                        "Пост %s: фото %s превысило лимит PHOTO_MAX_BYTES (%s)",
                        post_id,
                        photo_number,
                        PHOTO_MAX_BYTES,
                    )
                    return None

    except (requests.RequestException, ValueError) as error:
        logger.warning(
            "Пост %s: не удалось скачать фото %s: %s",
            post_id,
            photo_number,
            error,
        )
        return None

    if photo.tell() == 0:
        logger.warning("Пост %s: фото %s скачалось пустым", post_id, photo_number)
        return None

    photo.seek(0)
    photo.name = get_photo_filename(url, post_id, photo_number)
    return photo


def send_text_fallback(post, text, reason):
    post_url = build_post_url(post)

    if text:
        message = text[:4096]
    elif post_url:
        message = f"Пост VK: {post_url}"
    else:
        logger.warning(
            "Пост %s не содержит поддерживаемого контента",
            post["id"],
        )
        return True

    if reason and post_url and post_url not in message:
        suffix = f"\n\nОригинал: {post_url}"
        message_limit = 4096 - len(suffix)
        message = f"{message[:message_limit]}{suffix}"

    try:
        bot.send_message(CHANNEL_ID, message)
        logger.info("Пост %s: отправлен текст%s", post["id"], reason)
        logger.info("Пост %s успешно обработан", post["id"])
        return True
    except Exception:
        logger.exception("Не удалось отправить пост %s в Telegram", post["id"])
        return False


def send_photo_file(post, photo, photo_number, caption=None):
    try:
        bot.send_photo(CHANNEL_ID, photo, caption=caption)
        return True
    except ApiTelegramException as error:
        if error.error_code == 400:
            logger.warning(
                "Пост %s: Telegram не принял фото %s: %s",
                post["id"],
                photo_number,
                error.description,
            )
            return False

        raise


def send_photo_group(post, photos, text):
    media = [
        telebot.types.InputMediaPhoto(
            photo,
            caption=text[:1024] if text and index == 0 else None,
        )
        for index, photo in enumerate(photos)
    ]

    try:
        bot.send_media_group(CHANNEL_ID, media)
        return True
    except ApiTelegramException as error:
        if error.error_code == 400:
            logger.warning(
                "Пост %s: Telegram не принял альбом из %s фото: %s",
                post["id"],
                len(photos),
                error.description,
            )
            return False

        raise


def send_post_to_channel(post):
    text = post.get("text", "").strip()
    photo_urls = get_photo_urls(post)
    downloaded_photos = []
    skipped_photos = 0

    try:
        for index, photo_url in enumerate(photo_urls, start=1):
            if len(downloaded_photos) >= TELEGRAM_MEDIA_GROUP_MAX_ITEMS:
                skipped_photos += len(photo_urls) - index + 1
                logger.warning(
                    "Пост %s: больше %s фото; оставшиеся фото пропущены",
                    post["id"],
                    TELEGRAM_MEDIA_GROUP_MAX_ITEMS,
                )
                break

            photo = download_photo(photo_url, post["id"], index)
            if not photo:
                skipped_photos += 1
                continue

            downloaded_photos.append((index, photo))

        if len(downloaded_photos) == 1:
            photo_number, photo = downloaded_photos[0]
            if send_photo_file(
                post,
                photo,
                photo_number,
                caption=text[:1024] if text else None,
            ):
                logger.info("Пост %s: отправлена фотография", post["id"])
                logger.info("Пост %s успешно обработан", post["id"])
                return True

            skipped_photos += 1
            return send_text_fallback(
                post,
                text,
                " вместо фото; Telegram не принял изображение",
            )

        if len(downloaded_photos) > 1:
            photos = [photo for _, photo in downloaded_photos]
            if send_photo_group(post, photos, text):
                logger.info(
                    "Пост %s: отправлен альбом, фотографий: %s, пропущено: %s",
                    post["id"],
                    len(downloaded_photos),
                    skipped_photos,
                )
                logger.info("Пост %s успешно обработан", post["id"])
                return True

            skipped_photos += len(downloaded_photos)
            return send_text_fallback(
                post,
                text,
                " вместо альбома; Telegram не принял изображения",
            )

        if photo_urls:
            return send_text_fallback(
                post,
                text,
                " вместо фото; все фото были пропущены",
            )

        if text:
            return send_text_fallback(post, text, "")

        logger.warning(
            "Пост %s не содержит поддерживаемого контента",
            post["id"],
        )
        logger.info("Пост %s успешно обработан", post["id"])
        return True
    except Exception:
        logger.exception("Не удалось отправить пост %s в Telegram", post["id"])
        return False


def request_shutdown(signum, _frame):
    logger.info("Получен сигнал %s, завершаю работу", signum)
    stop_event.set()


def run():
    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)

    logger.info("Бот запущен")
    logger.info("Группа VK: %s", GROUP_ID)
    logger.info("Канал Telegram: %s", CHANNEL_ID)
    logger.info("Интервал проверки: %s секунд", CHECK_INTERVAL)
    logger.info("Файл логов: %s", LOG_FILE)

    while not stop_event.is_set():
        try:
            for post in get_new_posts():
                if stop_event.is_set():
                    break

                logger.info("Обработка поста %s", post["id"])
                if not send_post_to_channel(post):
                    logger.warning(
                        "Обработка остановлена на посте %s; следующая "
                        "попытка будет через %s секунд",
                        post["id"],
                        CHECK_INTERVAL,
                    )
                    break

                save_last_post(post["id"])
                stop_event.wait(2)
        except Exception:
            logger.exception("Непредвиденная ошибка в основном цикле")

        stop_event.wait(CHECK_INTERVAL)

    logger.info("Бот остановлен")


if __name__ == "__main__":
    run()
