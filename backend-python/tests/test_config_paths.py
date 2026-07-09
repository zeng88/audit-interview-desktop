import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config


def reload_config_with_env(monkeypatch, **env: str):
    """按指定环境变量重载配置，验证跨平台存储目录解析。"""
    for key in ("AUDIT_STORAGE_DIR", "APPDATA", "LOCALAPPDATA", "XDG_DATA_HOME"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return importlib.reload(config)


def test_storage_dir_can_be_overridden(monkeypatch, tmp_path: Path) -> None:
    custom_storage = tmp_path / "custom-storage"
    loaded = reload_config_with_env(monkeypatch, AUDIT_STORAGE_DIR=str(custom_storage))
    assert loaded.STORAGE_DIR == custom_storage.resolve()
    assert loaded.DB_PATH == custom_storage.resolve() / "audit.db"


def test_default_storage_dir_uses_user_data_home(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    loaded = reload_config_with_env(monkeypatch)

    if sys.platform == "darwin":
        expected = tmp_path / "Library" / "Application Support" / config.APP_NAME / "storage"
    elif sys.platform == "win32":
        expected = tmp_path / "AppData" / "Roaming" / config.APP_NAME / "storage"
    else:
        expected = tmp_path / ".local" / "share" / config.APP_NAME / "storage"

    assert loaded.STORAGE_DIR == expected


def test_windows_storage_prefers_appdata(monkeypatch, tmp_path: Path) -> None:
    if sys.platform != "win32":
        return

    appdata = tmp_path / "Roaming"
    loaded = reload_config_with_env(monkeypatch, APPDATA=str(appdata))
    assert loaded.STORAGE_DIR == appdata / config.APP_NAME / "storage"
