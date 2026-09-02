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


def make_multi_photo_post():
    post = make_photo_post()
    post["attachments"] = [
        {
            "type": "photo",
            "photo": {
                "sizes": [
                    {
                        "width": 1000,
                        "height": 1000,
                        "url": f"https://vk.example/photo_{index}.jpg",
                    }
                ]
            },
        }
        for index in range(1, 4)
    ]
    return post


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


def test_multiple_photos_are_sent_as_one_media_group(monkeypatch):
    bot_module = load_bot(monkeypatch)
    sent = {}

    def fake_get(url, **kwargs):
        sent.setdefault("download_urls", []).append(url)
        sent.setdefault("download_kwargs", []).append(kwargs)
        return FakePhotoResponse()

    def fake_send_photo(_chat_id, _photo, caption=None):
        raise AssertionError("multiple photos must not be sent one by one")

    def fake_send_media_group(chat_id, media):
        sent["chat_id"] = chat_id
        sent["media"] = media

    monkeypatch.setattr(bot_module.requests, "get", fake_get)
    monkeypatch.setattr(bot_module.bot, "send_photo", fake_send_photo)
    monkeypatch.setattr(bot_module.bot, "send_media_group", fake_send_media_group)

    assert bot_module.send_post_to_channel(make_multi_photo_post()) is True

    assert sent["download_urls"] == [
        "https://vk.example/photo_1.jpg",
        "https://vk.example/photo_2.jpg",
        "https://vk.example/photo_3.jpg",
    ]
    assert all(kwargs["stream"] is True for kwargs in sent["download_kwargs"])
    assert sent["chat_id"] == "-100123"
    assert len(sent["media"]) == 3
    assert sent["media"][0].caption == "Проверочный пост"
    assert sent["media"][1].caption is None
    assert sent["media"][2].caption is None
    assert all(not isinstance(media.media, str) for media in sent["media"])
    assert [media.media.read() for media in sent["media"]] == [
        b"fake-image",
        b"fake-image",
        b"fake-image",
    ]


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
