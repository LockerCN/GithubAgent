# -*- coding: utf-8 -*-
# 文件说明：验证程序入口装配、运行目录初始化与配置路径切换。

"""程序入口测试。"""

from __future__ import annotations

import os
from pathlib import Path
import textwrap

from src.main import CONFIG_PATH_ENV_NAME, main


def test_main_returns_zero_with_valid_config(tmp_path: Path, monkeypatch) -> None:
    _write_app_config(tmp_path)
    _patch_workflow(monkeypatch)
    monkeypatch.chdir(tmp_path)

    result = main()

    assert result == 0


def test_main_initializes_stage_two_runtime_layout(tmp_path: Path, monkeypatch) -> None:
    _write_app_config(tmp_path)
    _patch_workflow(monkeypatch)
    monkeypatch.chdir(tmp_path)

    result = main()

    assert result == 0
    assert (tmp_path / "runtime" / "state" / "delivery_state.json").exists()
    assert (tmp_path / "runtime" / "archive").is_dir()


def test_main_supports_custom_config_path_from_environment(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_path = _write_custom_app_config(tmp_path, relative_path="config/app.ci.toml")
    _patch_workflow(monkeypatch)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(CONFIG_PATH_ENV_NAME, os.fspath(config_path.relative_to(tmp_path)))

    result = main()

    assert result == 0


def _patch_workflow(monkeypatch) -> None:
    class _FakeWorkflow:
        def __init__(self, **_: object) -> None:
            self.run_called = False

        def run(self) -> None:
            self.run_called = True

    monkeypatch.setattr("src.main.DailyHotRepoWorkflow", _FakeWorkflow)


def _write_app_config(tmp_path: Path) -> None:
    _write_custom_app_config(tmp_path, relative_path="config/app.toml")


def _write_custom_app_config(tmp_path: Path, relative_path: str) -> Path:
    config_path = tmp_path / relative_path
    config_path.parent.mkdir(parents=True, exist_ok=True)

    content = textwrap.dedent(
        """
        [scheduler]
        timezone = "Asia/Shanghai"

        [trendshift]
        daily_explore_url = "https://trendshift.io/"
        top_n = 10
        browser_timeout_ms = 30000

        [github]
        api_base_url = "https://api.github.com"
        token = "github-token-placeholder"
        request_timeout_seconds = 30
        tree_max_entries = 300
        file_max_chars = 20000

        [llm]
        base_url = "https://api.example.com/v1"
        api_key = "llm-api-key-placeholder"
        model = "model-placeholder"
        enable_web_search = true
        max_rounds = 12

        [feishu]
        webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/placeholder"

        [runtime]
        archive_dir = "runtime/archive"
        state_file = "runtime/state/delivery_state.json"
        """
    ).strip()

    config_path.write_text(content + "\n", encoding="utf-8")
    return config_path
