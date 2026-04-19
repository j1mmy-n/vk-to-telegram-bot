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
- Python 3.7 или выше
- Доступ к VK API и Telegram Bot API
- Для запуска в РФ – сервер за пределами РФ или VPN

---

## Установка

```bash
git clone https://github.com/j1mmy-n/vk-to-telegram-bot
cd vk-to-telegram-bot
pip install -r requirements.txt
```

---

## Настройка

Создайте файл `.env` в корне проекта и добавьте туда:

```
VK_TOKEN=your_vk_token
TG_TOKEN=your_telegram_token
CHANNEL_ID=your_channel_id
```
- `CHECK_INTERVAL` – как часто проверять (в секундах). По умолчанию 3600 (1 час).

### Как получить токены

**Telegram:**
- `TG_TOKEN` – Напишите @BotFather, создайте бота, он выдаст токен вашего бота.
- `CHANNEL_ID` – Напишите @userinfobot название вашего канала в формате @primer_kanala, он выдаст айди вашего канала.

**VK:**
- `VK_TOKEN` – Перейдите на https://vkhost.github.io (выберите "Kate Mobile"), авторизуйтесь через свою страницу ВК, из появившейся сверху ссылки скопируйте все ПОСЛЕ #access_token= и до первого символа "&".
- `GROUP_ID` – Числовой ID из ссылки `vk.com/club123456789`

## Пример `.env` файла:
TG_TOKEN=ТОКЕН_ТЕЛЕГРАМ_БОТА
CHANNEL_ID=@твой_канал_или_-1001234567890
VK_TOKEN=ТОКЕН_VK_СЮДА
GROUP_ID=-123456789

❗ Не публикуйте свои реальные токены

---

## Запуск

```bash
python bot.py
```

---

## Как это работает

1. Бот получает новые посты через VK API  
2. Обрабатывает их  
3. Отправляет в Telegram через Bot API  

---

## Структура проекта

```
bot.py
.env.example
requirements.txt
```

## Примечание

Бот был сделан для личного использования, но может быть доработан под любые задачи.
