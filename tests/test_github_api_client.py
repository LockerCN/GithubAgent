"""Github API 客户端测试。"""

from __future__ import annotations

import base64
import json

from src.clients.github_api_client import GithubApiClient, HttpResponse


def test_get_repository_metadata_maps_response_fields() -> None:
    client = GithubApiClient(
        api_base_url="https://api.github.com",
        token="token-value",
        request_timeout_seconds=30,
        tree_max_entries=300,
        file_max_chars=10,
        request_sender=lambda *_: HttpResponse(
            status_code=200,
            body=json.dumps(
                {
                    "full_name": "owner/repo",
                    "description": "A sample repository",
                    "default_branch": "main",
                    "stargazers_count": 123,
                    "language": "Python",
                    "html_url": "https://github.com/owner/repo",
                }
            ),
        ),
    )

    metadata = client.get_repository_metadata("owner", "repo")

    assert metadata.full_name == "owner/repo"
    assert metadata.description == "A sample repository"
    assert metadata.default_branch == "main"
    assert metadata.stars == 123
    assert metadata.language == "Python"
    assert metadata.html_url == "https://github.com/owner/repo"


def test_get_repository_tree_filters_by_path_and_non_recursive_depth() -> None:
    client = GithubApiClient(
        api_base_url="https://api.github.com",
        token="token-value",
        request_timeout_seconds=30,
        tree_max_entries=300,
        file_max_chars=10,
        request_sender=lambda *_: HttpResponse(
            status_code=200,
            body=json.dumps(
                {
                    "tree": [
                        {"path": "README.md", "type": "blob"},
                        {"path": "src", "type": "tree"},
                        {"path": "src/main.py", "type": "blob"},
                        {"path": "src/utils", "type": "tree"},
                        {"path": "src/utils/parser.py", "type": "blob"},
                    ]
                }
            ),
        ),
    )

    entries = client.get_repository_tree("owner", "repo", ref="main", path="src", recursive=False)

    assert [(entry.path, entry.type) for entry in entries] == [
        ("main.py", "file"),
        ("utils", "dir"),
    ]


def test_get_repository_file_content_truncates_long_utf8_text() -> None:
    content = "这是一段超长文本内容"
    encoded_content = base64.b64encode(content.encode("utf-8")).decode("ascii")
    client = GithubApiClient(
        api_base_url="https://api.github.com",
        token="token-value",
        request_timeout_seconds=30,
        tree_max_entries=300,
        file_max_chars=5,
        request_sender=lambda *_: HttpResponse(
            status_code=200,
            body=json.dumps(
                {
                    "type": "file",
                    "encoding": "base64",
                    "content": encoded_content,
                }
            ),
        ),
    )

    file_content = client.get_repository_file_content(
        "owner",
        "repo",
        ref="main",
        path="README.md",
    )

    assert file_content.path == "README.md"
    assert file_content.ref == "main"
    assert file_content.content == content[:5]
    assert file_content.truncated is True
