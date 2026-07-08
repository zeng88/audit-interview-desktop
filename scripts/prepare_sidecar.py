#!/usr/bin/env python3
"""构建并准备 Tauri externalBin 所需的后端 sidecar。"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend-python"
BIN_DIR = ROOT_DIR / "src-tauri" / "binaries"
SIDECAR_NAME = "audit-backend"


def rust_host_triple() -> str:
    """读取 Rust host triple，用于本地打包时生成正确的 sidecar 文件名。"""
    try:
        output = subprocess.check_output(["rustc", "-vV"], text=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("无法读取 rustc host triple，请先安装 Rust 工具链。") from exc

    for line in output.splitlines():
        if line.startswith("host: "):
            return line.split("host: ", 1)[1].strip()
    raise RuntimeError("rustc -vV 输出中没有 host triple。")


def sidecar_target() -> str:
    """CI 会显式传入目标 triple；本地打包默认使用当前 Rust host triple。"""
    return os.environ.get("TAURI_SIDECAR_TARGET") or rust_host_triple()


def executable_name() -> str:
    """Windows 下 PyInstaller 会生成 .exe，其他平台保持无扩展名。"""
    return f"{SIDECAR_NAME}.exe" if platform.system() == "Windows" else SIDECAR_NAME


def run_pyinstaller() -> Path:
    """使用当前 Python 环境把 FastAPI 后端打成单文件可执行程序。"""
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        "--onefile",
        "app.py",
        "--name",
        SIDECAR_NAME,
    ]
    subprocess.check_call(command, cwd=BACKEND_DIR)

    output = BACKEND_DIR / "dist" / executable_name()
    if not output.exists():
        raise FileNotFoundError(f"PyInstaller 未生成后端 sidecar：{output}")
    return output


def copy_for_tauri(source: Path, target_triple: str) -> Path:
    """复制为 Tauri externalBin 约定的 binary-name-target-triple 文件名。"""
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    suffix = ".exe" if platform.system() == "Windows" else ""
    target = BIN_DIR / f"{SIDECAR_NAME}-{target_triple}{suffix}"
    shutil.copy2(source, target)
    target.chmod(target.stat().st_mode | 0o755)
    return target


def latest_backend_source_mtime() -> float:
    """取后端源码的最新修改时间，用于判断 sidecar 是否需要重打包。"""
    candidates = list(BACKEND_DIR.glob("*.py"))
    for folder in ("services", "parsers", "exporters", "prompts"):
        candidates.extend((BACKEND_DIR / folder).glob("*.py"))
    candidates.append(BACKEND_DIR / "requirements.txt")
    return max(path.stat().st_mtime for path in candidates if path.exists())


def prepared_sidecar_path(target_triple: str) -> Path:
    """返回 Tauri 当前平台约定的 sidecar 目标路径。"""
    suffix = ".exe" if platform.system() == "Windows" else ""
    return BIN_DIR / f"{SIDECAR_NAME}-{target_triple}{suffix}"


def main() -> None:
    target_triple = sidecar_target()
    prepared = prepared_sidecar_path(target_triple)
    if prepared.exists() and prepared.stat().st_mtime >= latest_backend_source_mtime():
        print(f"Reusing prepared Tauri sidecar: {prepared}")
        return

    source = run_pyinstaller()
    target = copy_for_tauri(source, target_triple)
    print(f"Prepared Tauri sidecar: {target}")


if __name__ == "__main__":
    main()
