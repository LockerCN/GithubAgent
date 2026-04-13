"""Github API 客户端实现。"""

from __future__ import annotations

import base64
from dataclasses import dataclass
import json
from typing import Any, Callable
from urllib import error, parse, request

from src.common.exceptions import GithubApiError
from src.models.repository_models import FileContent, RepositoryMetadata, RepositoryTreeEntry


@dataclass(slots=True)
class HttpResponse:
    """HTTP 响应摘要。"""

    status_code: int
    body: str


RequestSender = Callable[[str, str, dict[str, str], bytes | None, int], HttpResponse]


class GithubApiClient:
    """负责访问 Github REST API。"""

    def __init__(
        self,
        api_base_url: str,
        token: str,
        request_timeout_seconds: int,
        tree_max_entries: int,
        file_max_chars: int,
        request_sender: RequestSender | None = None,
    ) -> None:
        self._api_base_url = api_base_url.rstrip("/")
        self._token = token
        self._request_timeout_seconds = request_timeout_seconds
        self._tree_max_entries = tree_max_entries
        self._file_max_chars = file_max_chars
        self._request_sender = request_sender or self._send_request

    def get_repository_metadata(self, owner: str, name: str) -> RepositoryMetadata:
        """读取仓库基础元信息。"""

        payload = self._get_json(f"/repos/{owner}/{name}")
        return RepositoryMetadata(
            full_name=str(payload.get("full_name", f"{owner}/{name}")),
            description=str(payload.get("description") or ""),
            default_branch=str(payload.get("default_branch") or "main"),
            stars=self._to_int(payload.get("stargazers_count"), "stargazers_count"),
            language=self._to_optional_str(payload.get("language")),
            html_url=str(payload.get("html_url") or f"https://github.com/{owner}/{name}"),
        )

    def get_repository_tree(
        self,
        owner: str,
        name: str,
        ref: str,
        path: str,
        recursive: bool,
    ) -> list[RepositoryTreeEntry]:
        """读取仓库目录树。"""

        query = {"recursive": "1"} if recursive else {}
        payload = self._get_json(
            f"/repos/{owner}/{name}/git/trees/{parse.quote(ref, safe='')}",
            query=query,
        )
        tree_items = payload.get("tree")
        if not isinstance(tree_items, list):
            raise GithubApiError("Github API 返回的目录树格式非法。")

        normalized_path = path.strip("/")
        prefix = f"{normalized_path}/" if normalized_path else ""
        entries: list[RepositoryTreeEntry] = []

        for item in tree_items:
            if not isinstance(item, dict):
                continue

            entry_path = str(item.get("path") or "").strip("/")
            if not entry_path:
                continue

            if prefix and not entry_path.startswith(prefix):
                continue

            relative_path = entry_path[len(prefix) :] if prefix else entry_path
            if not relative_path:
                continue

            if not recursive and "/" in relative_path:
                continue

            entry_type = self._map_tree_entry_type(str(item.get("type") or ""))
            entries.append(RepositoryTreeEntry(path=relative_path, type=entry_type))

            if len(entries) >= self._tree_max_entries:
                break

        return entries

    def get_repository_file_content(
        self,
        owner: str,
        name: str,
        ref: str,
        path: str,
    ) -> FileContent:
        """读取单个仓库文件内容。"""

        encoded_path = parse.quote(path.strip("/"), safe="/")
        payload = self._get_json(f"/repos/{owner}/{name}/contents/{encoded_path}", query={"ref": ref})

        file_type = str(payload.get("type") or "")
        if file_type != "file":
            raise GithubApiError(f"目标路径不是文件: {path}")

        encoding_name = str(payload.get("encoding") or "")
        encoded_content = payload.get("content")
        if encoding_name != "base64" or not isinstance(encoded_content, str):
            raise GithubApiError(f"Github API 返回的文件内容格式不受支持: {path}")

        try:
            content_text = base64.b64decode(encoded_content, validate=False).decode(
                "utf-8",
                errors="replace",
            )
        except Exception as error:
            raise GithubApiError(f"文件内容解码失败: {path}") from error

        truncated = len(content_text) > self._file_max_chars
        final_content = content_text[: self._file_max_chars] if truncated else content_text
        return FileContent(path=path, ref=ref, content=final_content, truncated=truncated)

    def _get_json(self, path: str, query: dict[str, str] | None = None) -> dict[str, Any]:
        url = f"{self._api_base_url}{path}"
        if query:
            url = f"{url}?{parse.urlencode(query)}"

        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "github-hot-repo-agent",
        }
        if self._token.strip():
            headers["Authorization"] = f"Bearer {self._token}"

        try:
            response = self._request_sender(
                "GET",
                url,
                headers,
                None,
                self._request_timeout_seconds,
            )
        except GithubApiError:
            raise
        except Exception as error:
            raise GithubApiError(f"Github API 请求失败: {url}") from error

        if response.status_code < 200 or response.status_code >= 300:
            raise GithubApiError(f"Github API 请求失败，HTTP 状态码: {response.status_code}")

        try:
            payload = json.loads(response.body)
        except json.JSONDecodeError as error:
            raise GithubApiError(f"Github API 返回非 JSON 响应: {url}") from error

        if not isinstance(payload, dict):
            raise GithubApiError(f"Github API 返回的 JSON 根节点非法: {url}")

        return payload

    def _map_tree_entry_type(self, raw_type: str) -> str:
        if raw_type == "blob":
            return "file"
        if raw_type == "tree":
            return "dir"
        return raw_type or "unknown"

    def _to_int(self, value: Any, field_name: str) -> int:
        if isinstance(value, bool):
            raise GithubApiError(f"Github API 字段 {field_name} 非法。")
        try:
            return int(value)
        except (TypeError, ValueError) as error:
            raise GithubApiError(f"Github API 字段 {field_name} 非法。") from error

    def _to_optional_str(self, value: Any) -> str | None:
        if value is None:
            return None
        return str(value)

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
            raise GithubApiError(f"Github API 请求失败: {url_error.reason}") from url_error
