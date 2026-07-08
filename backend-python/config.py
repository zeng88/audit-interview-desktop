from pathlib import Path


# 所有运行时文件都放在后端目录内，避免污染用户其他目录。
BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "storage"
FILES_DIR = STORAGE_DIR / "files"
EXPORTS_DIR = STORAGE_DIR / "exports"
LOGS_DIR = STORAGE_DIR / "logs"
DB_PATH = STORAGE_DIR / "audit.db"

APP_VERSION = "0.1.0"


def ensure_storage_dirs() -> None:
    """创建本地运行目录，保证中文路径在 UTF-8 环境下可用。"""
    for path in (STORAGE_DIR, FILES_DIR, EXPORTS_DIR, LOGS_DIR):
        path.mkdir(parents=True, exist_ok=True)

