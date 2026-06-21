# Changelog

Все заметные изменения проекта будут документироваться в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
а версии проекта следуют [Semantic Versioning](https://semver.org/lang/ru/).

## [Unreleased]

## [1.0.0] - 2026-06-21

### Added

- Получение новых постов из группы или страницы VK через VK API.
- Пересылка текста и фотографий в Telegram-канал.
- Поддержка публикаций с несколькими фотографиями.
- Сохранение ID последнего обработанного поста в `last_post.json`.
- Настройка токенов, идентификаторов и интервала проверки через `.env`.
- Шаблон systemd-сервиса для запуска и автоматического перезапуска бота.

[Unreleased]: https://github.com/j1mmy-n/vk-to-telegram-bot/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/j1mmy-n/vk-to-telegram-bot/releases/tag/v1.0.0
