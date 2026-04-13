"""飞书 Webhook 客户端实现。"""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from typing import Callable
from urllib import error, request

from src.common.exceptions import FeishuPublishError


LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class HttpResponse:
    """HTTP 响应摘要。"""

    status_code: int
    body: str


RequestSender = Callable[[str, str, dict[str, str], bytes | None, int], HttpResponse]


class FeishuWebhookClient:
    """负责发送飞书机器人消息。"""

    def __init__(
        self,
        webhook_url: str,
        timeout_seconds: int = 30,
        request_sender: RequestSender | None = None,
    ) -> None:
        self._webhook_url = webhook_url
        self._timeout_seconds = timeout_seconds
        self._request_sender = request_sender or self._send_request

    def send_post_message(self, payload: dict) -> None:
        """发送飞书 post 消息。"""

        body_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json; charset=utf-8"}

        try:
            response = self._request_sender(
                "POST",
                self._webhook_url,
                headers,
                body_bytes,
                self._timeout_seconds,
            )
        except FeishuPublishError:
            raise
        except Exception as error:
            raise FeishuPublishError("飞书消息发送失败。") from error

        if response.status_code < 200 or response.status_code >= 300:
            raise FeishuPublishError(f"飞书消息发送失败，HTTP 状态码: {response.status_code}")

        self._validate_response_body(response.body)
        LOGGER.info("飞书消息发送成功，HTTP 状态码: %s", response.status_code)

    def _validate_response_body(self, body: str) -> None:
        if not body.strip():
            return

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return

        if not isinstance(payload, dict):
            return

        code = payload.get("code")
        if code in (None, 0):
            return

        message = str(payload.get("msg", "未知错误"))
        raise FeishuPublishError(f"飞书消息发送失败，返回 code={code}: {message}")

    def _send_request(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | None,
        timeout_seconds: int,
    ) -> HttpResponse:
        http_request = request.Request(url=url, data=body, headers=headers, method=method)

        try:
            with request.urlopen(http_request, timeout=timeout_seconds) as response:
                return HttpResponse(
                    status_code=response.getcode(),
                    body=response.read().decode("utf-8", errors="replace"),
                )
        except error.HTTPError as http_error:
            response_body = http_error.read().decode("utf-8", errors="replace")
            return HttpResponse(status_code=http_error.code, body=response_body)
        except error.URLError as url_error:
            raise FeishuPublishError(f"飞书消息发送失败: {url_error.reason}") from url_error
