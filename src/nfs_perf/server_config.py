import time

from bench_config import BenchConfig
from ssh import RemoteExecutor


class NFSServer:
    """Base class for NFS server management."""

    def __init__(
        self,
        name: str,
        executor: RemoteExecutor,
        mount_export: str,
        mount_opts: str,
        mount_type: str = "nfs",
    ):
        self.name = name
        self.executor = executor
        self.mount_export = mount_export
        self.mount_opts = mount_opts
        self.mount_type = mount_type

    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def restart(self):
        self.stop()
        time.sleep(2)
        self.start()

    def is_running(self) -> bool:
        raise NotImplementedError

    def wait_ready(self, timeout: int = 30):
        """Wait until the NFS server is accepting connections."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.is_running():
                time.sleep(1)
                return
            time.sleep(0.5)

        raise TimeoutError(f"{self.name} did not become ready in {timeout}s")


class MamontServer(NFSServer):
    BENCH_CONFIG_PATH = "/tmp/nfs-mamont-bench.toml"

    def __init__(
        self,
        executor: RemoteExecutor,
        project_dir: str,
        export_root: str,
        export_paths: str,
        mount_export: str,
        mount_opts: str,
    ):
        super().__init__(
            "nfs-mamont",
            executor,
            mount_export=mount_export,
            mount_opts=mount_opts,
            mount_type="nfs",
        )
        self.project_dir = project_dir
        self.export_root = export_root
        self.export_paths = export_paths
        self._built = False

    def _source_env(self, cmd: str) -> str:
        return f"source $HOME/.cargo/env 2>/dev/null; {cmd}"

    def _write_config(self):
        """Generate mamont config on the remote server."""
        lines = [
            "[allocator]",
            "read_buffer_size = 1048576",
            "read_buffer_count = 2048",
            "write_buffer_size = 1048576",
            "write_buffer_count = 2048",
            "[exports]",
            f'root = "{self.export_root}"',
            f'paths = ["{self.export_paths}"]',
        ]
        content = "\\n".join(lines)
        self.executor.run(
            f"printf '{content}\\n' > {self.BENCH_CONFIG_PATH}",
            check=True,
        )
        print(f" Config written to remote: {self.BENCH_CONFIG_PATH}")

    def _ensure_built(self):
        if self._built:
            return

        print(f" Building {self.name} (cargo build --release)...")
        self.executor.run(
            self._source_env(f"cd {self.project_dir} && cargo build --release"),
            timeout=600,
            check=True,
        )
        self._built = True
        print(" Build complete")

    def start(self):
        print(f" Starting {self.name} on remote server...")
        self.stop()
        time.sleep(1)

        self._ensure_built()
        self._write_config()

        binary = f"{self.project_dir}/target/release/mirrorfs"
        cmd = (
            f"nohup {binary} -c {self.BENCH_CONFIG_PATH} "
            f"> /tmp/nfs-mamont.log 2>&1 & echo $!"
        )
        result = self.executor.run(cmd, check=True)
        remote_pid = result.stdout.strip().split("\n")[-1]
        print(f" {self.name} launched on remote (pid={remote_pid})")
        self.wait_ready(timeout=60)
        print(f" {self.name} is ready")

    def stop(self):
        print(f" Stopping {self.name} on remote server...")
        self.executor.run("pkill -f 'mirrorfs' || true", check=False)
        time.sleep(2)
        self.executor.run("pkill -9 -f 'mirrorfs' || true", check=False)
        time.sleep(1)

    def is_running(self) -> bool:
        result = self.executor.run(
            "ss -tln | grep -q ':2049'",
            check=False,
        )
        return result.returncode == 0


def build_server(cfg: BenchConfig) -> NFSServer:
    executor = RemoteExecutor(
        host=cfg.nfs_server_ip,
        user=cfg.server_user,
    )
    return MamontServer(
        executor=executor,
        project_dir=cfg.mamont_project_dir,
        export_root=cfg.mamont_export_root,
        export_paths=cfg.mamont_export_paths,
        mount_export=cfg.mamont_mount_export,
        mount_opts=cfg.mamont_mount_opts,
    )
