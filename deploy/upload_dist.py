"""上传前端 dist/ 到服务器"""

from pathlib import Path

import paramiko
from paramiko import RSAKey

HOST = "93901.pro"
PORT = 22
USER = "root"
PEM = Path.home() / ".ssh" / "InsightTrader.pem"
LOCAL_DIST = Path(__file__).resolve().parent.parent / "mobile_h5" / "dist"
REMOTE_DIST = "/opt/insighttrader/mobile_h5/dist"


def mkdir_p(sftp, remote_dir):
    dirs = []
    d = remote_dir
    while d and d != "/":
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


def upload():
    files = [p for p in LOCAL_DIST.rglob("*") if p.is_file()]
    total = len(files)
    print(f"共 {total} 个文件待上传\n")

    pkey = RSAKey.from_private_key_file(PEM)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USER, pkey=pkey)
    sftp = client.open_sftp()

    mkdir_p(sftp, REMOTE_DIST)

    for i, path in enumerate(files, 1):
        rel = path.relative_to(LOCAL_DIST)
        remote_path = REMOTE_DIST + "/" + rel.as_posix()
        mkdir_p(sftp, remote_path.rsplit("/", 1)[0])
        sftp.put(str(path), remote_path)
        print(f"[{i:>3}/{total}] {rel}")

    sftp.close()
    client.close()
    print(f"\n完成：共上传 {total} 个文件")


if __name__ == "__main__":
    upload()
