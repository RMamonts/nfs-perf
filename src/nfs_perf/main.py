import os
import subprocess
from datetime import datetime

import parser
from bench_config import BenchConfig
from bench_utils import needs_read_prepare, run_test_case
from fio import FioResult
from helpers import cleanup_test_files, drop_caches, save_results
from mount import ensure_mount, unmount
from server_config import build_server


def main():
    print("Start")
    cfg = BenchConfig()
    print("config is ready")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    args = parser.parse_args(cgf=cfg)
    print("args are ready")

    total_combos = (
        len(args.fio_types)
        * len(args.block_sizes)
        * len(args.num_jobs)
        * len(args.iodepths)
        * len(args.direct_modes)
        * args.iterations
    )

    print(f"\n{'#' * 60}")
    print("# NFS Benchmark")
    print(
        f"# Server host: {cfg.nfs_server_ip} "
        f"(SSH: {cfg.server_user}@{cfg.nfs_server_ip})"
    )
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

    server = build_server(cfg)

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
        "-t",  # force a pseudo‑tty (if needed)
        f"ubuntu@{cfg.nfs_server_ip}",
        "git -C /home/ubuntu/nfs-mamont rev-parse HEAD",
    ]

    git_info = ""

    if cfg.branch is not None and cfg.commit is not None:
        git_checkout = f"git -C /home/ubuntu/nfs-mamont checkout {cfg.commit}"
        git_info = f"{cfg.branch}_{cfg.commit}"
    elif cfg.branch is not None:
        commit = subprocess.run(
            ssh_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=os.environ.copy(),  # inherit current env (incl. SSH_AUTH_SOCK)
            check=False,  # we want to inspect the return code ourselves
        )

        print(f"COMMIT: \n", commit.stdout[:7])

        git_info = f"{cfg.branch}_{commit.stdout[:7]}"
        git_checkout = f"git -C /home/ubuntu/nfs-mamont checkout {cfg.branch}"
    else:
        commit = subprocess.run(
            ssh_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=os.environ.copy(),  # inherit current env (incl. SSH_AUTH_SOCK)
            check=False,  # we want to inspect the return code ourselves
        )

        print("COMMIT:\n", commit.stdout[:7])

        git_info = f"main_{commit.stdout[:7]}"

    server.executor.run(git_checkout, check=False)

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
                                f"{test_type} bs={bs} jobs={num_jobs} depth={iodepth} "
                                f"direct={direct} iter={iteration}"
                            )
                            print(f"{'#' * 60}")
                            test_dir = cfg.test_dir
                            if args.local_mode:
                                test_dir = f"{cfg.mamont_export_root}/{cfg.mamont_export_paths}"

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

                            if combo_idx % 5 == 0:
                                save_results(
                                    all_results,
                                    timestamp,
                                    cfg.output_dir,
                                    git_info,
                                )

                            if not args.local_mode:
                                unmount(cfg.nfs_mount_point)
                            server.stop()


main()
