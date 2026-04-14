"""
推送后端代码到生产服务器（白名单模式，只传必要文件）
用法：python deploy/upload.py
"""
import os
import stat
from pathlib import Path
import paramiko
from paramiko import RSAKey

# ── 配置 ──────────────────────────────────────────────────────────────────────
HOST        = "93901.pro"
PORT        = 22
USER        = "root"
PEM         = Path.home() / ".ssh" / "InsightTrader.pem"
LOCAL_ROOT  = Path(__file__).resolve().parent.parent  # deploy/ 的上级即项目根
REMOTE_ROOT = "/opt/insighttrader"

# 只上传这些顶层目录和文件（白名单）
INCLUDE_DIRS = {
    "ta_service",
    "tradingagents",
    "tests",
    "deploy",
}
INCLUDE_FILES = {
    "Dockerfile.ta_service",
    "docker-compose.prod.yml",
    "pyproject.toml",
    ".env.production.example",
}

# 目录内部的排除规则
EXCLUDE_SUFFIXES = {".pyc", ".pyo"}
EXCLUDE_NAMES    = {"__pycache__", ".pytest_cache"}

# ── 收集需要上传的文件 ─────────────────────────────────────────────────────────
def collect_files():
    files = []

    # 顶层文件
    for fname in INCLUDE_FILES:
        p = LOCAL_ROOT / fname
        if p.is_file():
            files.append((p, Path(fname)))

    # 白名单目录
    for d in INCLUDE_DIRS:
        base = LOCAL_ROOT / d
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(LOCAL_ROOT)
            # 排除 __pycache__ 等
            if any(part in EXCLUDE_NAMES for part in rel.parts):
                continue
            if path.suffix in EXCLUDE_SUFFIXES:
                continue
            files.append((path, rel))

    return files

# ── 远端创建目录（递归）────────────────────────────────────────────────────────
def mkdir_p(sftp, remote_dir):
    dirs = []
    d = remote_dir
    while d and d != REMOTE_ROOT and d != "/":
        dirs.append(d)
        d = d.rsplit("/", 1)[0]
    for d in reversed(dirs):
        try:
            sftp.stat(d)
        except FileNotFoundError:
            try:
                sftp.mkdir(d)
            except Exception:
                pass

# ── 上传 ──────────────────────────────────────────────────────────────────────
def upload():
    files = collect_files()
    total = len(files)
    print(f"共 {total} 个文件待上传\n")

    pkey = RSAKey.from_private_key_file(PEM)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USER, pkey=pkey)
    sftp = client.open_sftp()

    # 确保远端根目录存在
    try:
        sftp.stat(REMOTE_ROOT)
    except FileNotFoundError:
        sftp.mkdir(REMOTE_ROOT)

    for i, (local_path, rel) in enumerate(files, 1):
        remote_path = REMOTE_ROOT + "/" + rel.as_posix()
        remote_dir  = remote_path.rsplit("/", 1)[0]
        mkdir_p(sftp, remote_dir)
        sftp.put(str(local_path), remote_path)
        print(f"[{i:>4}/{total}] {rel}")

    sftp.close()
    client.close()
    print(f"\n完成：共上传 {total} 个文件到 {REMOTE_ROOT}")

if __name__ == "__main__":
    upload()
