# -*- coding: utf-8 -*-
# 文件说明：封装 Github 仓库读取相关工具。

"""Github 仓库读取工具实现。"""

from __future__ import annotations

from dataclasses import asdict

from src.clients.github_api_client import GithubApiClient
from src.tools.base_tool import BaseTool


class GetRepositoryMetadataTool(BaseTool):
    """获取仓库基础元信息。"""

    def __init__(self, github_client: GithubApiClient) -> None:
        self._github_client = github_client

    @property
    def name(self) -> str:
        return "get_repository_metadata"

    @property
    def description(self) -> str:
        return "获取 Github 仓库的基础元信息，例如描述、默认分支、Star 数和语言。"

    @property
    def json_schema(self) -> dict:
        return _build_repo_base_schema(
            extra_properties={},
            required=["owner", "name"],
        )

    def execute(self, arguments: dict) -> dict:
        arguments = self._require_object(arguments)
        owner = self._get_str(arguments, "owner")
        name = self._get_str(arguments, "name")
        metadata = self._github_client.get_repository_metadata(owner=owner, name=name)
        return asdict(metadata)


class GetRepositoryTreeTool(BaseTool):
    """获取仓库目录树信息。"""

    def __init__(self, github_client: GithubApiClient) -> None:
        self._github_client = github_client

    @property
    def name(self) -> str:
        return "get_repository_tree"

    @property
    def description(self) -> str:
        return "获取仓库指定分支和路径下的目录树信息，支持递归读取。"

    @property
    def json_schema(self) -> dict:
        return _build_repo_base_schema(
            extra_properties={
                "ref": {
                    "type": "string",
                    "description": "目标分支或提交引用。",
                },
                "path": {
                    "type": "string",
                    "description": "可选，目录树起始路径，根目录传空字符串。",
                },
                "recursive": {
                    "type": "boolean",
                    "description": "是否递归读取整个目录树。",
                },
            },
            required=["owner", "name", "ref"],
        )

    def execute(self, arguments: dict) -> dict:
        arguments = self._require_object(arguments)
        owner = self._get_str(arguments, "owner")
        name = self._get_str(arguments, "name")
        ref = self._get_str(arguments, "ref")
        path = self._get_optional_str(arguments, "path", default="") or ""
        recursive = self._get_bool(arguments, "recursive", required=False, default=True)
        entries = self._github_client.get_repository_tree(
            owner=owner,
            name=name,
            ref=ref,
            path=path,
            recursive=recursive,
        )
        return {
            "ref": ref,
            "path": path,
            "entries": [asdict(entry) for entry in entries],
        }


class GetRepositoryFileContentTool(BaseTool):
    """获取仓库单个文件内容。"""

    def __init__(self, github_client: GithubApiClient) -> None:
        self._github_client = github_client

    @property
    def name(self) -> str:
        return "get_repository_file_content"

    @property
    def description(self) -> str:
        return "读取 Github 仓库指定分支下某个文件的文本内容。"

    @property
    def json_schema(self) -> dict:
        return _build_repo_base_schema(
            extra_properties={
                "ref": {
                    "type": "string",
                    "description": "目标分支或提交引用。",
                },
                "path": {
                    "type": "string",
                    "description": "文件路径，例如 README.md。",
                },
            },
            required=["owner", "name", "ref", "path"],
        )

    def execute(self, arguments: dict) -> dict:
        arguments = self._require_object(arguments)
        owner = self._get_str(arguments, "owner")
        name = self._get_str(arguments, "name")
        ref = self._get_str(arguments, "ref")
        path = self._get_str(arguments, "path")
        file_content = self._github_client.get_repository_file_content(
            owner=owner,
            name=name,
            ref=ref,
            path=path,
        )
        return asdict(file_content)


def _build_repo_base_schema(
    *,
    extra_properties: dict,
    required: list[str],
) -> dict:
    properties = {
        "owner": {
            "type": "string",
            "description": "Github 仓库 owner。",
        },
        "name": {
            "type": "string",
            "description": "Github 仓库名称。",
        },
    }
    properties.update(extra_properties)

    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }
