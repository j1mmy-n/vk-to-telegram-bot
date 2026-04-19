# VK → Telegram Parser Bot

Автоматический парсер **новых постов** из группы ВКонтакте в Telegram-канал.

Используется для кросспостинга в Яндекс.Дзен.

### Возможности
- Отслеживает только новые посты
- Поддерживает фото и фотоальбомы
- Не дублирует посты
- Простая настройка

### Как получить токены и ID

**Telegram:**
- `TG_TOKEN` — через [@BotFather](https://t.me/BotFather)
- `CHANNEL_ID` — через [@usinfobot](https://t.me/usinfobot)

**ВКонтакте:**
- `VK_TOKEN` — через [https://vkhost.github.io/](https://vkhost.github.io/), выбери **Kate Mobile** → авторизуйся → скопируй значение после `access_token=` и до первого `&`
- `GROUP_ID` — **числовой** ID группы (из ссылки вида `vk.com/club123456789`)

### Как запустить

```bash
pip install -r requirements.txt

cp .env.example .env
# Открой файл .env и вставь свои данные
python bot.py
Настройка интервала
В bot.py измени строку time.sleep(3600):

60 — проверка каждую минуту (для теста)
3600 — раз в час (рекомендуется)
