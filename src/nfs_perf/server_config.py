import shlex
import time

from .bench_config import BenchConfig
from .ssh import RemoteExecutor


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

    @property
    def export_path(self) -> str:
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

    @property
    def export_path(self) -> str:
        return f"{self.export_root.rstrip('/')}/{self.export_paths.lstrip('/')}"

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


class GaneshaServer(NFSServer):
    LOG_PATH = "/tmp/nfs-ganesha.log"
    STDOUT_PATH = "/tmp/nfs-ganesha.stdout"

    def __init__(
        self,
        executor: RemoteExecutor,
        binary: str,
        config_path: str,
        export_root: str,
        export_paths: str,
        mount_export: str | None,
        mount_opts: str,
    ):
        self.binary = binary
        self.config_path = config_path
        self.export_root = export_root
        self.export_paths = export_paths
        super().__init__(
            "nfs-ganesha",
            executor,
            mount_export=mount_export or self.export_path,
            mount_opts=mount_opts,
            mount_type="nfs",
        )

    @property
    def export_path(self) -> str:
        return f"{self.export_root.rstrip('/')}/{self.export_paths.lstrip('/')}"

    def _ensure_binary_exists(self):
        cmd = f"command -v {shlex.quote(self.binary)}"
        result = self.executor.run(
            f"sudo sh -lc {shlex.quote(cmd)}",
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"{self.name} binary was not found: {self.binary}. "
                "Install nfs-ganesha on the server or pass --ganesha-binary."
            )

    def _is_process_running(self) -> bool:
        result = self.executor.run(
            "pgrep -f 'ganesha.nfsd' >/dev/null",
            check=False,
        )
        return result.returncode == 0

    def _print_logs(self):
        for path in (self.STDOUT_PATH, self.LOG_PATH):
            result = self.executor.run(
                f"sudo test -f {shlex.quote(path)} "
                f"&& sudo tail -n 80 {shlex.quote(path)} || true",
                check=False,
            )
            if result.stdout.strip():
                print(f" [{path}]\n{result.stdout[-4000:]}")

    def _write_config(self):
        config = f"""NFS_CORE_PARAM {{
    DRC_Disabled = true;
}}

NFSv4 {{
    Delegations = false;
}}

MDCACHE {{
    Dir_Chunk = 0;

    Cache_FDs = false;

    Close_Fast = true;

    Entries_HWMark = 1;
    Entries_Release_Size = 1;
    Chunks_HWMark = 1;
    Chunks_LWMark = 1;
}}

EXPORT_DEFAULTS {{
    Attr_Expiration_Time = 0;

    Delegations = None;
    PrivilegedPort = false;
}}

EXPORT {{
    Export_Id = 1;
    Path = "{self.export_path}";
    Pseudo = "{self.mount_export}";
    Access_Type = RW;
    Squash = No_Root_Squash;
    SecType = sys;
    Protocols = 3, 4;
    Transports = TCP;

    FSAL {{
        Name = VFS;
    }}

    CLIENT {{
        Clients = *;
        Access_Type = RW;
        Squash = No_Root_Squash;
        SecType = sys;
    }}
}}
"""
        quoted_config_path = shlex.quote(self.config_path)
        self.executor.run(f"sudo mkdir -p {shlex.quote(self.export_path)}", check=True)
        self.executor.run(
            f"sudo chown $(id -u):$(id -g) {shlex.quote(self.export_path)}",
            check=True,
        )
        self.executor.run(
            f"sudo tee {quoted_config_path} > /dev/null <<'EOF'\n{config}EOF",
            check=True,
        )
        print(f" Config written to remote: {self.config_path}")

    def start(self):
        print(f" Starting {self.name} on remote server...")
        self.stop()
        time.sleep(1)

        self._ensure_binary_exists()
        self._write_config()

        cmd = (
            f"sudo nohup {shlex.quote(self.binary)} -F "
            f"-L {self.LOG_PATH} -f {shlex.quote(self.config_path)} "
            f"> {self.STDOUT_PATH} 2>&1 & echo $!"
        )
        result = self.executor.run(cmd, check=True)
        remote_pid = result.stdout.strip().split("\n")[-1]
        print(f" {self.name} launched on remote (pid={remote_pid})")
        time.sleep(1)
        if not self._is_process_running():
            self._print_logs()
            raise RuntimeError(f"{self.name} exited immediately after start")

        try:
            self.wait_ready(timeout=60)
        except TimeoutError:
            self._print_logs()
            raise
        print(f" {self.name} is ready")

    def stop(self):
        print(f" Stopping {self.name} on remote server...")
        self.executor.run("sudo systemctl stop nfs-ganesha || true", check=False)
        self.executor.run("sudo pkill -f 'ganesha.nfsd' || true", check=False)
        time.sleep(2)
        self.executor.run("sudo pkill -9 -f 'ganesha.nfsd' || true", check=False)
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
    if cfg.server_type == "ganesha":
        return GaneshaServer(
            executor=executor,
            binary=cfg.ganesha_binary,
            config_path=cfg.ganesha_config_path,
            export_root=cfg.ganesha_export_root,
            export_paths=cfg.ganesha_export_paths,
            mount_export=cfg.ganesha_mount_export,
            mount_opts=cfg.ganesha_mount_opts,
        )

    return MamontServer(
        executor=executor,
        project_dir=cfg.mamont_project_dir,
        export_root=cfg.mamont_export_root,
        export_paths=cfg.mamont_export_paths,
        mount_export=cfg.mamont_mount_export,
        mount_opts=cfg.mamont_mount_opts,
    )
