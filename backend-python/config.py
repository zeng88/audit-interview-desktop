import os
import sys
from pathlib import Path


APP_NAME = "审计访谈清单生成工具"
BASE_DIR = Path(__file__).resolve().parent
LEGACY_STORAGE_DIR = BASE_DIR / "storage"


def resolve_storage_dir() -> Path:
    """返回跨平台用户数据目录，避免把业务数据写入安装包内部。"""
    override = os.environ.get("AUDIT_STORAGE_DIR")
    if override:
        return Path(override).expanduser().resolve()

    home = Path.home()
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / APP_NAME / "storage"
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
        base_dir = Path(appdata) if appdata else home / "AppData" / "Roaming"
        return base_dir / APP_NAME / "storage"

    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    base_dir = Path(xdg_data_home) if xdg_data_home else home / ".local" / "share"
    return base_dir / APP_NAME / "storage"


STORAGE_DIR = resolve_storage_dir()
FILES_DIR = STORAGE_DIR / "files"
EXPORTS_DIR = STORAGE_DIR / "exports"
LOGS_DIR = STORAGE_DIR / "logs"
DB_PATH = STORAGE_DIR / "audit.db"

APP_VERSION = "0.1.1"


def ensure_storage_dirs() -> None:
    """创建本地运行目录，保证中文路径在 UTF-8 环境下可用。"""
    for path in (STORAGE_DIR, FILES_DIR, EXPORTS_DIR, LOGS_DIR):
        path.mkdir(parents=True, exist_ok=True)
