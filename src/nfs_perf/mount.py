import subprocess
import time

from bench_config import BenchConfig
from server_config import NFSServer


def ensure_mount(mount_point: str, server: NFSServer, cfg: BenchConfig):
    """Mount NFS export if not already mounted."""
    result = subprocess.run(
        ["mountpoint", "-q", mount_point],
        capture_output=True,
        check=False,
    )
    if result.returncode == 0:
        return

    subprocess.run(["sudo", "mkdir", "-p", mount_point], check=True, timeout=10)
    cmd = [
        "sudo",
        "mount",
        "-v",
        "-t",
        server.mount_type,
        "-o",
        server.mount_opts,
        f"{cfg.nfs_data_ip}:{server.mount_export}",
        mount_point,
    ]
    print(f" [mount] {' '.join(cmd)}")
    subprocess.run(cmd, check=True, timeout=30)
    time.sleep(1)


def unmount(mount_point: str):
    """Unmount NFS export."""
    result = subprocess.run(
        ["mountpoint", "-q", mount_point],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return

    print(f" [umount] {mount_point}")
    subprocess.run(["sudo", "umount", "-f", mount_point], check=False, timeout=30)
    time.sleep(1)
