![Python](https://img.shields.io/badge/Python-3.7%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Working-brightgreen)

# VK → Telegram Bot

Бот для автоматической пересылки постов из VK в Telegram канал.

---

## Что делает

- Получает посты из VK (группы или страницы)
- Отправляет их в Telegram канал
- Работает автоматически (без ручного вмешательства)

---

## ⚠️ Важно (для пользователей из РФ)

Telegram API может работать нестабильно или не работать без VPN.

Если вы запускаете бота:
- на сервере в РФ — возможны ошибки подключения
- на локальном компьютере — сообщения могут не отправляться

✅ Рекомендуется:
- использовать сервер за пределами РФ (например, Нидерланды)
- или запускать бота через VPN
  
## Требования

- Docker с плагином Docker Compose (рекомендуемый способ)
- либо Python 3.9 или выше для запуска без Docker
- Доступ к VK API и Telegram Bot API
- Для запуска в РФ – сервер за пределами РФ или VPN

---

## Быстрый запуск через Docker

```bash
git clone https://github.com/j1mmy-n/vk-to-telegram-bot
cd vk-to-telegram-bot
cp .env.example .env
```

Заполните `.env` своими токенами и идентификаторами, затем запустите:

```bash
docker compose up -d --build
```

Проверить состояние контейнера и посмотреть поток логов:

```bash
docker compose ps
docker compose logs -f bot
```

Обновить бота:

```bash
git pull
docker compose up -d --build
```

Остановить бота:

```bash
docker compose down
```

Данные сохраняются в именованных Docker volumes `vk-to-telegram-bot-data` и
`vk-to-telegram-bot-logs`.
Обычная команда `docker compose down` их не удаляет. Не используйте
`docker compose down -v`, если хотите сохранить ID последнего поста и логи.

### Просмотр файловых логов

Логи одновременно выводятся через `docker compose logs` и записываются в
`/app/logs/bot.log` внутри постоянного volume:

```bash
docker compose exec bot tail -f /app/logs/bot.log
docker compose cp bot:/app/logs/bot.log ./bot.log
```

По умолчанию используется ротация: основной файл до 10 МБ и пять архивных
файлов. Параметры меняются через `LOG_LEVEL`, `LOG_MAX_BYTES` и
`LOG_BACKUP_COUNT` в `.env`.

> Файловые логи помогают расследовать сбои после восстановления доступа к
> серверу. Для уведомления о полной недоступности сервера нужен отдельный
> внешний мониторинг.

### Перенос существующего состояния в Docker

Если бот уже работал без Docker и рядом с ним есть `last_post.json`, перенесите
его перед первым контейнерным запуском:

```bash
docker compose create
docker compose cp last_post.json bot:/app/data/last_post.json
docker compose up -d
```

Без переноса при первом запуске бот запомнит последний доступный пост и не
будет пересылать старые публикации.

---

## Запуск без Docker

```bash
git clone https://github.com/j1mmy-n/vk-to-telegram-bot
cd vk-to-telegram-bot
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

На Windows команда активации окружения:

```powershell
.\venv\Scripts\Activate.ps1
```

---

## Настройка

1. Скопируйте файл с примерами переменных:

```bash
cp .env.example .env
```

2. Откройте файл .env и заполните своими данными

```
VK_TOKEN=your_vk_token
TG_TOKEN=your_telegram_token 
CHANNEL_ID=your_channel_id
CHECK_INTERVAL=3600 – как часто проверять (в секундах). По умолчанию 3600 (1 час).
```

Channel ID - должен быть цифровым (например -1001234567890), формат @username может не работать.
Check Interval - как часто проверять (в секундах). По умолчанию 3600 (1 час).

---

### Как получить токены

**Telegram:**
- `TG_TOKEN` – Напишите @BotFather, создайте бота, он выдаст токен вашего бота.
- `CHANNEL_ID` – Напишите @userinfobot название вашего канала в формате @primer_kanala, он выдаст цифровой айди вашего канала.

**VK:**
- `VK_TOKEN` – Перейдите на https://vkhost.github.io (выберите "Kate Mobile"), авторизуйтесь через свою страницу ВК, из появившейся сверху ссылки скопируйте все ПОСЛЕ #access_token= и до первого символа "&".
- `GROUP_ID` – Числовой ID из ссылки `vk.com/club123456789`

---

## Пример заполненного `.env` файла:

```
TG_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
CHANNEL_ID=-1001234567890
VK_TOKEN=vk1a.ABCdef...GHIjkl
GROUP_ID=-123456789
CHECK_INTERVAL=1800
```

❗ Не публикуйте свои реальные токены!

---

## Ручной запуск

```bash
python bot.py
```

---

## Как это работает

1. Бот получает новые посты через VK API (wall.get)
2. Обрабатывает их (текст, фото)
3. Отправляет в Telegram через Bot API

---

## Структура проекта

```
vk-to-telegram-bot/
├── bot.py                     # Основной скрипт
├── Dockerfile                 # Сборка Docker-образа
├── docker-compose.yml         # Запуск и постоянные volumes
├── .dockerignore              # Исключения контекста Docker
├── .env.example               # Пример переменных окружения
├── requirements.txt           # Основные зависимости
├── requirements-dev.txt       # Зависимости для разработки
├── vk_to_tg.service           # systemd сервис (автозапуск)
├── CHANGELOG.md               # История версий
└── README.md                  # Документация
```

---

## Запуск через systemd (на сервере)

В репозитории есть файл vk_to_tg.service – готовый шаблон для автозапуска бота как службы.
**Инструкция:**

1. Отредактируйте vk_to_tg.service, заменив пути на свои
2. Скопируйте его в системную папку

```
sudo cp vk_to_tg.service /etc/systemd/system/
```

3. Перезапустите systemd и запустите бота:

```
sudo systemctl daemon-reload
sudo systemctl enable vk_to_tg
sudo systemctl start vk_to_tg
sudo systemctl status vk_to_tg
```

Подробные команды и пояснения есть внутри самого файла.

---

## Для разработчиков
Если вы хотите дорабатывать бота, установите дополнительные зависимости:

```
pip install -r requirements-dev.txt
```

Они включают:

- flake8 – проверка стиля кода
- black – автоформатирование
- isort – сортировка импортов
- pytest – тестирование

---

## TODO (планы на доработку)

1. Добавить поддержку видео
2. Добавить внешний мониторинг доступности
3. Повторные попытки при ошибках Telegram API
4. Поддержка других вложений (документы)

---

## Примечание

Бот был сделан для личного использования, но может быть доработан под любые задачи.
Pull request'ы и идеи приветствуются!

---

## Лицензия
MIT © j1mmy-n
