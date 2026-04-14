"""配置加载器测试。"""

from __future__ import annotations

from pathlib import Path
import textwrap

import pytest

from src.common.exceptions import ConfigurationError
from src.config.config_loader import ConfigLoader


def test_load_valid_config_returns_app_config(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)

    app_config = ConfigLoader().load(config_path)

    assert app_config.scheduler.timezone == "Asia/Shanghai"
    assert app_config.trendshift.top_n == 10
    assert app_config.github.file_max_chars == 20000
    assert app_config.llm.request_timeout_seconds == 180
    assert app_config.llm.max_rounds == 12
    assert app_config.feishu.webhook_url.startswith("https://open.feishu.cn/")
    assert app_config.runtime.archive_dir == "runtime/archive"


@pytest.mark.parametrize(
    ("mutations", "expected_message"),
    [
        ({"top_n": "top_n = 11"}, "trendshift.top_n"),
        ({"file_max_chars": "file_max_chars = 1000"}, "github.file_max_chars"),
        ({"max_rounds": "max_rounds = 0"}, "llm.max_rounds"),
        (
            {"llm_request_timeout_seconds": "request_timeout_seconds = 0"},
            "llm.request_timeout_seconds",
        ),
        (
            {"webhook_url": 'webhook_url = ""'},
            "feishu.webhook_url",
        ),
        (
            {"archive_dir": 'archive_dir = "../outside/archive"'},
            "runtime.archive_dir",
        ),
        (
            {"state_file": 'state_file = "../outside/delivery_state.json"'},
            "runtime.state_file",
        ),
    ],
)
def test_load_invalid_config_raises_configuration_error(
    tmp_path: Path,
    mutations: dict[str, str],
    expected_message: str,
) -> None:
    config_path = _write_config(tmp_path, **mutations)

    with pytest.raises(ConfigurationError, match=expected_message):
        ConfigLoader().load(config_path)


def _write_config(tmp_path: Path, **replacements: str) -> Path:
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

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
        request_timeout_seconds = 180
        enable_web_search = true
        max_rounds = 12

        [feishu]
        webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/placeholder"

        [runtime]
        archive_dir = "runtime/archive"
        state_file = "runtime/state/delivery_state.json"
        """
    ).strip()

    for original, replacement in {
        'top_n = 10': replacements.get("top_n", 'top_n = 10'),
        'file_max_chars = 20000': replacements.get("file_max_chars", 'file_max_chars = 20000'),
        'max_rounds = 12': replacements.get("max_rounds", 'max_rounds = 12'),
        'request_timeout_seconds = 180': replacements.get(
            "llm_request_timeout_seconds",
            'request_timeout_seconds = 180',
        ),
        'webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/placeholder"': replacements.get(
            "webhook_url",
            'webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/placeholder"',
        ),
        'archive_dir = "runtime/archive"': replacements.get(
            "archive_dir",
            'archive_dir = "runtime/archive"',
        ),
        'state_file = "runtime/state/delivery_state.json"': replacements.get(
            "state_file",
            'state_file = "runtime/state/delivery_state.json"',
        ),
    }.items():
        content = content.replace(original, replacement)

    config_path = config_dir / "app.toml"
    config_path.write_text(content + "\n", encoding="utf-8")
    return config_path
