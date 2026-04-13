"""飞书 Webhook 客户端测试。"""

from __future__ import annotations

import json

import pytest

from src.clients.feishu_webhook_client import FeishuWebhookClient, HttpResponse
from src.common.exceptions import FeishuPublishError


def test_send_post_message_posts_json_payload() -> None:
    captured: dict[str, object] = {}

    def fake_sender(
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | None,
        timeout_seconds: int,
    ) -> HttpResponse:
        captured["method"] = method
        captured["url"] = url
        captured["headers"] = headers
        captured["body"] = body
        captured["timeout_seconds"] = timeout_seconds
        return HttpResponse(status_code=200, body='{"code":0,"msg":"ok"}')

    client = FeishuWebhookClient(
        webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/test",
        timeout_seconds=15,
        request_sender=fake_sender,
    )

    client.send_post_message({"msg_type": "post", "content": {"post": {}}})

    assert captured["method"] == "POST"
    assert captured["url"] == "https://open.feishu.cn/open-apis/bot/v2/hook/test"
    assert captured["timeout_seconds"] == 15
    assert captured["headers"] == {"Content-Type": "application/json; charset=utf-8"}
    assert json.loads((captured["body"] or b"").decode("utf-8"))["msg_type"] == "post"


def test_send_post_message_raises_when_http_status_is_not_2xx() -> None:
    client = FeishuWebhookClient(
        webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/test",
        request_sender=lambda *_: HttpResponse(status_code=500, body="server error"),
    )

    with pytest.raises(FeishuPublishError, match="HTTP 状态码: 500"):
        client.send_post_message({"msg_type": "post"})
