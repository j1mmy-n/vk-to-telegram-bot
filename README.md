![Python](https://img.shields.io/badge/Python-3.12-blue)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)
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

- Linux-сервер с Docker Engine и плагином Docker Compose
- Доступ к VK API и Telegram Bot API
- `git` для загрузки и обновления файлов проекта

Python, `pip` и библиотеки на сервер отдельно устанавливать не нужно: они уже
включены в Docker-образ.

---

## Развёртывание на чистом Ubuntu-сервере

Ниже приведён рекомендуемый вариант с
[официальным репозиторием Docker](https://docs.docker.com/engine/install/ubuntu/).

### 1. Установите Docker Engine

Удалите конфликтующие неофициальные пакеты, если они были установлены:

```bash
for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do
  sudo apt-get remove -y "$pkg"
done
```

Добавьте официальный репозиторий Docker:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

sudo apt-get update
sudo apt-get install -y \
  docker-ce \
  docker-ce-cli \
  containerd.io \
  docker-buildx-plugin \
  docker-compose-plugin
```

Проверьте установку:

```bash
sudo systemctl enable --now docker
sudo docker run --rm hello-world
sudo docker compose version
```

> Команды ниже используют `sudo`. Добавлять пользователя в группу `docker`
> необязательно: участники этой группы фактически получают root-доступ к
> серверу.

### 2. Загрузите проект

```bash
sudo git clone https://github.com/j1mmy-n/vk-to-telegram-bot \
  /opt/vk-to-telegram-bot
cd /opt/vk-to-telegram-bot
sudo cp .env.example .env
```

Откройте `.env` любым доступным редактором:

```bash
sudo nano .env
```

`nano` нужен только для редактирования конфигурации и не требуется самому боту.
Если редактор отсутствует, установите его командой `sudo apt-get install nano`
или используйте `vi`.

### 3. Запустите бота

Загрузите готовый образ из GitHub Container Registry и запустите контейнер:

```bash
sudo docker compose pull
sudo docker compose up -d
```

Проверьте состояние и логи:

```bash
sudo docker compose ps
sudo docker compose logs -f bot
```

Контейнер использует `restart: unless-stopped`, поэтому автоматически
перезапускается после сбоя приложения, перезапуска Docker и загрузки сервера.

### Обновление

```bash
cd /opt/vk-to-telegram-bot
sudo git pull --ff-only
sudo docker compose pull
sudo docker compose up -d --remove-orphans
```

Если в `.env` задано `BOT_VERSION=1.1.0`, будет использоваться именно эта
версия. Для получения последнего стабильного релиза установите
`BOT_VERSION=latest`.

### Остановка

```bash
cd /opt/vk-to-telegram-bot
sudo docker compose down
```

Обычная команда `docker compose down` не удаляет volumes. Не используйте
`docker compose down -v`, если хотите сохранить ID последнего поста и логи.

### Краткий вариант для сервера с установленным Docker

```bash
sudo git clone https://github.com/j1mmy-n/vk-to-telegram-bot \
  /opt/vk-to-telegram-bot
cd /opt/vk-to-telegram-bot
sudo cp .env.example .env
# заполните .env
sudo docker compose pull
sudo docker compose up -d
```

Данные сохраняются в именованных Docker volumes `vk-to-telegram-bot-data` и
`vk-to-telegram-bot-logs`.

### Просмотр файловых логов

Логи одновременно выводятся через `docker compose logs` и записываются в
`/app/logs/bot.log` внутри постоянного volume:

```bash
sudo docker compose exec bot tail -f /app/logs/bot.log
sudo docker compose cp bot:/app/logs/bot.log ./bot.log
```

По умолчанию используется ротация: основной файл до 10 МБ и пять архивных
файлов. Параметры меняются через `LOG_LEVEL`, `LOG_MAX_BYTES` и
`LOG_BACKUP_COUNT` в `.env`.

> Файловые логи помогают расследовать сбои после восстановления доступа к
> серверу. Для уведомления о полной недоступности сервера нужен отдельный
> внешний мониторинг.

### Выбор версии

По умолчанию Compose использует последний стабильный образ с тегом `latest`.
Чтобы закрепить конкретную версию, добавьте в `.env`:

```dotenv
BOT_VERSION=1.1.0
```

Образы публикуются для архитектур `linux/amd64` и `linux/arm64`.

Если нужно собрать образ локально из исходников:

```bash
sudo docker compose build
sudo docker compose up -d
```

### Перенос существующего состояния в Docker

Если бот уже работал без Docker и рядом с ним есть `last_post.json`, перенесите
его перед первым контейнерным запуском:

```bash
sudo docker compose create
sudo docker compose cp last_post.json bot:/app/data/last_post.json
sudo docker compose up -d
```

Без переноса при первом запуске бот запомнит последний доступный пост и не
будет пересылать старые публикации.

---

## Локальный запуск без Docker

```bash
git clone https://github.com/j1mmy-n/vk-to-telegram-bot
cd vk-to-telegram-bot
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python bot.py
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
├── .github/workflows/         # CI и публикация образов в GHCR
├── .dockerignore              # Исключения контекста Docker
├── .env.example               # Пример переменных окружения
├── requirements.txt           # Основные зависимости
├── requirements-dev.txt       # Зависимости для разработки
├── vk_to_tg.service           # Необязательное управление Compose через systemd
├── CHANGELOG.md               # История версий
└── README.md                  # Документация
```

---

## Управление через systemd (необязательно)

Docker Compose уже настроен на автоматический перезапуск контейнера, поэтому
отдельный systemd unit обычно не нужен. Файл `vk_to_tg.service` полезен, если
вы хотите управлять всем Compose-проектом командами `systemctl`.

Шаблон ожидает репозиторий в `/opt/vk-to-telegram-bot`. Если используется
другой путь, измените `WorkingDirectory` в файле.

```bash
cd /opt/vk-to-telegram-bot
sudo cp vk_to_tg.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now vk_to_tg.service
sudo systemctl status vk_to_tg.service
```

Полезные команды:

```bash
sudo systemctl reload vk_to_tg.service   # скачать и применить выбранный образ
sudo systemctl restart vk_to_tg.service  # остановить и запустить заново
sudo systemctl stop vk_to_tg.service
sudo journalctl -u vk_to_tg.service -n 50
```

Логи самого бота удобнее смотреть через:

```bash
cd /opt/vk-to-telegram-bot
sudo docker compose logs -f bot
```

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
