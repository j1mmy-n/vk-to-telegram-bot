import importlib
import sys

import requests


def load_bot(monkeypatch):
    monkeypatch.setenv("TG_TOKEN", "123456:test")
    monkeypatch.setenv("CHANNEL_ID", "-100123")
    monkeypatch.setenv("VK_TOKEN", "test")
    monkeypatch.setenv("GROUP_ID", "-1")

    sys.modules.pop("bot", None)
    return importlib.import_module("bot")


class FakePhotoResponse:
    headers = {"Content-Length": "10"}

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _traceback):
        return False

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size):
        yield b"fake-image"


def make_photo_post():
    return {
        "id": 6655,
        "owner_id": -8763403,
        "text": "Проверочный пост",
        "attachments": [
            {
                "type": "photo",
                "photo": {
                    "sizes": [
                        {
                            "width": 100,
                            "height": 100,
                            "url": "https://vk.example/small.jpg",
                        },
                        {
                            "width": 1000,
                            "height": 1000,
                            "url": "https://vk.example/big.jpg",
                        },
                    ]
                },
            }
        ],
    }


def test_photo_is_downloaded_before_sending(monkeypatch):
    bot_module = load_bot(monkeypatch)
    sent = {}

    def fake_get(url, **kwargs):
        sent["download_url"] = url
        sent["download_kwargs"] = kwargs
        return FakePhotoResponse()

    def fake_send_photo(chat_id, photo, caption=None):
        sent["chat_id"] = chat_id
        sent["photo"] = photo
        sent["caption"] = caption

    monkeypatch.setattr(bot_module.requests, "get", fake_get)
    monkeypatch.setattr(bot_module.bot, "send_photo", fake_send_photo)

    assert bot_module.send_post_to_channel(make_photo_post()) is True

    assert sent["download_url"] == "https://vk.example/big.jpg"
    assert sent["download_kwargs"]["stream"] is True
    assert sent["chat_id"] == "-100123"
    assert not isinstance(sent["photo"], str)
    assert sent["photo"].read() == b"fake-image"
    assert sent["photo"].name == "vk_post_6655_1.jpg"
    assert sent["caption"] == "Проверочный пост"


def test_failed_photo_download_sends_fallback_text(monkeypatch):
    bot_module = load_bot(monkeypatch)
    sent = {}

    def fake_get(_url, **_kwargs):
        raise requests.Timeout("download timed out")

    def fake_send_message(chat_id, message):
        sent["chat_id"] = chat_id
        sent["message"] = message

    monkeypatch.setattr(bot_module.requests, "get", fake_get)
    monkeypatch.setattr(bot_module.bot, "send_message", fake_send_message)

    assert bot_module.send_post_to_channel(make_photo_post()) is True

    assert sent["chat_id"] == "-100123"
    assert "Проверочный пост" in sent["message"]
    assert "https://vk.com/wall-8763403_6655" in sent["message"]


def test_failed_photo_only_post_sends_original_link(monkeypatch):
    bot_module = load_bot(monkeypatch)
    post = make_photo_post()
    post["text"] = ""
    sent = {}

    def fake_get(_url, **_kwargs):
        raise requests.Timeout("download timed out")

    def fake_send_message(_chat_id, message):
        sent["message"] = message

    monkeypatch.setattr(bot_module.requests, "get", fake_get)
    monkeypatch.setattr(bot_module.bot, "send_message", fake_send_message)

    assert bot_module.send_post_to_channel(post) is True

    assert sent["message"] == "Пост VK: https://vk.com/wall-8763403_6655"
