import json
import logging
import os
import signal
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from threading import Event

import requests
import telebot
from dotenv import load_dotenv

load_dotenv()

VK_API_URL = "https://api.vk.com/method/wall.get"
VK_API_VERSION = "5.199"

TG_TOKEN = os.getenv("TG_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
VK_TOKEN = os.getenv("VK_TOKEN")
GROUP_ID_RAW = os.getenv("GROUP_ID")

CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "3600"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
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


def send_post_to_channel(post):
    text = post.get("text", "").strip()
    attachments = post.get("attachments", [])
    photos = []

    for attachment in attachments:
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
            photos.append(best["url"])

    try:
        if len(photos) == 1:
            bot.send_photo(
                CHANNEL_ID,
                photos[0],
                caption=text[:1024] if text else None,
            )
            logger.info("Пост %s: отправлена фотография", post["id"])
        elif len(photos) > 1:
            media = [
                telebot.types.InputMediaPhoto(photo_url) for photo_url in photos[:-1]
            ]
            media.append(
                telebot.types.InputMediaPhoto(
                    photos[-1],
                    caption=text[:1024] if text else None,
                )
            )
            bot.send_media_group(CHANNEL_ID, media)
            logger.info(
                "Пост %s: отправлено фотографий: %s",
                post["id"],
                len(photos),
            )
        elif text:
            bot.send_message(CHANNEL_ID, text[:4096])
            logger.info("Пост %s: отправлен текст", post["id"])
        else:
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
