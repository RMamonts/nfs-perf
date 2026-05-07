import subprocess


class RemoteExecutor:
    """Execute commands on the NFS server (local or remote via SSH)."""

    def __init__(
        self,
        host: str,
        user: str = "ubuntu",
    ):
        self.host = host
        self.user = user

    def run(
        self,
        cmd: str,
        timeout: int = 120,
        check: bool = True,
    ) -> subprocess.CompletedProcess:
        if self.host and self.host not in ("127.0.0.1", "localhost"):
            ssh_cmd = ["ssh", "-o", "StrictHostKeyChecking=no"]
            ssh_cmd += [f"{self.user}@{self.host}", cmd]
            full_cmd = ssh_cmd
        else:
            full_cmd = ["bash", "-c", cmd]

        print(f" [exec] {cmd}")
        result = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if result.returncode != 0 and check:
            print(f" [exec] FAILED (rc={result.returncode})")
            if result.stdout.strip():
                print(f" [stdout] {result.stdout[-2000:]}")
            if result.stderr.strip():
                print(f" [stderr] {result.stderr[-2000:]}")
            raise subprocess.CalledProcessError(
                result.returncode,
                full_cmd,
                result.stdout,
                result.stderr,
            )

        return result
