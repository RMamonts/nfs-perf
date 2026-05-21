import os
import subprocess
import sys
from datetime import datetime

from . import parser
from .bench_config import BenchConfig
from .bench_utils import needs_read_prepare, run_test_case
from .fio import FioResult
from .helpers import cleanup_test_files, drop_caches, save_results
from .mount import ensure_mount, unmount
from .server_config import build_server


def configure_output():
    """Keep logs visible when stdout/stderr are piped through tee/nohup."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(line_buffering=True)


def apply_args_to_config(cfg: BenchConfig, args):
    cfg.size_per_job = args.size
    cfg.test_dir = args.test_dir
    cfg.output_dir = args.output_dir
    cfg.nfs_server_ip = args.server_host
    cfg.server_user = args.server_user
    cfg.nfs_data_ip = args.nfs_data_ip
    cfg.nfs_mount_point = args.mount_point
    cfg.mamont_project_dir = args.mamont_project_dir
    cfg.mamont_export_root = args.mamont_export_root
    cfg.mamont_export_paths = args.mamont_export_paths
    cfg.mamont_mount_export = args.mamont_mount_export
    cfg.mamont_mount_opts = args.mamont_mount_opts
    cfg.branch = args.mamont_branch
    cfg.commit = args.mamont_commit
    cfg.ganesha_binary = args.ganesha_binary
    cfg.ganesha_config_path = args.ganesha_config_path
    cfg.ganesha_export_root = args.ganesha_export_root
    cfg.ganesha_export_paths = args.ganesha_export_paths
    cfg.ganesha_mount_export = args.ganesha_mount_export
    cfg.ganesha_mount_opts = args.ganesha_mount_opts


def prepare_mamont(server, cfg: BenchConfig) -> str:
    git_pull = "git -C /home/ubuntu/nfs-mamont pull"
    subprocess.run(git_pull, shell=True, check=False, timeout=10)
    server.executor.run(git_pull, check=False)

    git_checkout = "git -C /home/ubuntu/nfs-mamont checkout main"

    ssh_cmd = [
        "ssh",
        "-A",  # forward agent (optional)
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",  # avoid permission problems
        "-t",  # force a pseudo-tty (if needed)
        f"ubuntu@{cfg.nfs_server_ip}",
        "git -C /home/ubuntu/nfs-mamont rev-parse HEAD",
    ]

    if cfg.branch is not None and cfg.commit is not None:
        git_checkout = f"git -C /home/ubuntu/nfs-mamont checkout {cfg.commit}"
        git_info = f"{cfg.branch}_{cfg.commit}"
    elif cfg.branch is not None:
        commit = subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            env=os.environ.copy(),  # inherit current env (incl. SSH_AUTH_SOCK)
            check=False,  # we want to inspect the return code ourselves
        )

        print("COMMIT: \n", commit.stdout[:7])

        git_info = f"{cfg.branch}_{commit.stdout[:7]}"
        git_checkout = f"git -C /home/ubuntu/nfs-mamont checkout {cfg.branch}"
    else:
        commit = subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            env=os.environ.copy(),  # inherit current env (incl. SSH_AUTH_SOCK)
            check=False,  # we want to inspect the return code ourselves
        )

        print("COMMIT:\n", commit.stdout[:7])

        git_info = f"main_{commit.stdout[:7]}"

    server.executor.run(git_checkout, check=False)
    return git_info


def main():
    configure_output()
    cfg = BenchConfig()
    args = parser.parse_args(cgf=cfg)

    print("Start")
    print("config is ready")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    apply_args_to_config(cfg, args)
    print("args are ready")

    total_combos = (
        len(args.fio_types)
        * len(args.block_sizes)
        * len(args.num_jobs)
        * len(args.iodepths)
        * len(args.direct_modes)
        * args.iterations
        * len(args.server)
    )

    print(f"\n{'#' * 60}")
    print("# NFS Benchmark")
    print(
        f"# Server host: {cfg.nfs_server_ip} "
        f"(SSH: {cfg.server_user}@{cfg.nfs_server_ip})"
    )
    print(f"# Server types: {args.server}")
    print("# Client: local (fio + mount)")
    print(f"# fio types: {args.fio_types}")
    print(f"# Block sizes: {args.block_sizes}")
    print(f"# Num jobs: {args.num_jobs}")
    print(f"# Iterations: {args.iterations}")
    print(f"# Size/job: {cfg.size_per_job}")
    print(f"# iodepths: {args.iodepths}")
    print(f"# direct modes: {args.direct_modes}")
    print(f"# Mount point: {cfg.nfs_mount_point} (via {cfg.nfs_data_ip})")
    print(f"# Total combos: {total_combos}")
    print(f"# Test dir: {cfg.test_dir}")
    print(f"{'#' * 60}\n")

    all_results: list[FioResult] = []
    combo_idx = 0
    run_info = "_".join(args.server)

    for server_type in args.server:
        cfg.server_type = server_type
        server = build_server(cfg)

        if args.iterations > 0 and server.name == "nfs-mamont":
            mamont_git_info = prepare_mamont(server, cfg)
            if len(args.server) == 1:
                run_info = mamont_git_info

        for test_type in args.fio_types:
            for bs in args.block_sizes:
                for num_jobs in args.num_jobs:
                    for iodepth in args.iodepths:
                        for direct in args.direct_modes:
                            for iteration in range(1, args.iterations + 1):
                                combo_idx += 1
                                print(f"\n{'#' * 60}")
                                print(
                                    f"# Combo {combo_idx}/{total_combos} "
                                    f"{server.name} {test_type} bs={bs} "
                                    f"jobs={num_jobs} depth={iodepth} "
                                    f"direct={direct} iter={iteration}"
                                )
                                print(f"{'#' * 60}")
                                test_dir = cfg.test_dir
                                if args.local_mode:
                                    test_dir = server.export_path

                                print(f"\n>>> Starting iteration {iteration}")
                                server.restart()
                                if not args.local_mode:
                                    ensure_mount(cfg.nfs_mount_point, server, cfg)
                                subprocess.run(
                                    ["sudo", "mkdir", "-p", test_dir],
                                    check=False,
                                    timeout=10,
                                )
                                cleanup_test_files(test_dir)
                                if not needs_read_prepare(test_type):
                                    drop_caches(server.executor)

                                result = run_test_case(
                                    server,
                                    test_dir,
                                    test_type,
                                    test_type,
                                    bs,
                                    num_jobs,
                                    iodepth,
                                    direct,
                                    iteration,
                                    cfg,
                                )
                                if result:
                                    all_results.append(result)

                                cleanup_test_files(test_dir)

                                save_results(
                                    all_results,
                                    timestamp,
                                    cfg.output_dir,
                                    run_info,
                                )

                                if not args.local_mode:
                                    unmount(cfg.nfs_mount_point)
                                server.stop()


if __name__ == "__main__":
    main()
