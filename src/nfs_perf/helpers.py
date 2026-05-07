import csv
import json
import os
import subprocess
import time
from collections import defaultdict
from dataclasses import asdict

from fio import FioResult
from ssh import RemoteExecutor


def cleanup_test_files(directory: str):
    """Remove fio test files."""
    print(f" [cleanup] Removing test files in {directory}")
    subprocess.run(
        f"rm -f {directory}/testfile.*",
        shell=True,
        check=False,
        timeout=60,
    )
    subprocess.run(["sync"], check=False, timeout=30)
    time.sleep(1)


def drop_caches(server_executor: RemoteExecutor | None):
    """Drop page cache on both client and server."""
    drop_cmd = "sync && sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'"

    print(" [cache] Dropping client caches")
    subprocess.run(drop_cmd, shell=True, check=False, timeout=10)

    if server_executor:
        print(" [cache] Dropping server caches")
        server_executor.run(drop_cmd, check=False)

    time.sleep(1)


def save_results(
    all_results: list[FioResult], timestamp: str, output_dir: str, git_info: str
):
    """Save results to CSV and JSON."""

    os.makedirs(output_dir, exist_ok=True)

    csv_path = os.path.join(output_dir, f"bench_{git_info}_{timestamp}.csv")
    json_path = os.path.join(output_dir, f"bench_{git_info}_{timestamp}.json")

    fields = [
        "server",
        "test_type",
        "block_size",
        "num_jobs",
        "iteration",
        "direct",
        "iodepth",
        "bw_bytes",
        "bw_mib",
        "iops",
        "slat_mean_us",
        "clat_mean_us",
        "lat_mean_us",
        "lat_p50_us",
        "lat_p95_us",
        "lat_p99_us",
        "lat_p999_us",
        "usr_cpu",
        "sys_cpu",
        "ctx",
        "runtime_ms",
        "read_bw_bytes",
        "read_iops",
        "write_bw_bytes",
        "write_iops",
    ]

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for result in all_results:
            writer.writerow(asdict(result))

    with open(json_path, "w") as f:
        json.dump([asdict(result) for result in all_results], f, indent=2)

    print("\nResults saved to:")
    print(f" CSV: {csv_path}")
    print(f" JSON: {json_path}")


def print_summary(results: list[FioResult]):
    """Print a summary table of average results
    per (server, test, bs, jobs, depth, direct)."""

    groups: dict[tuple, list[FioResult]] = defaultdict(list)
    for result in results:
        key = (
            result.server,
            result.test_type,
            result.block_size,
            result.num_jobs,
            result.iodepth,
            result.direct,
        )
        groups[key].append(result)

    print(f"\n{'=' * 128}")
    print(
        f"{'SERVER':<14} {'TEST':<10} {'BS':<8} {'JOBS':<6} {'DEPTH':<6} {'DIR':<4} "
        f"{'BW MiB/s':>10} {'IOPS':>10} {'P95 us':>10} {'P99 us':>10} {'N':>4}"
    )
    print(f"{'=' * 128}")

    for key in sorted(groups.keys()):
        items = groups[key]
        count = len(items)
        avg_bw = sum(result.bw_mib for result in items) / count
        avg_iops = sum(result.iops for result in items) / count
        avg_lat = sum(result.lat_p95_us for result in items) / count
        avg_p99 = sum(result.lat_p99_us for result in items) / count
        srv, test, bs, jobs, depth, direct = key
        print(
            f"{srv:<14} {test:<10} {bs:<8} {jobs:<6} {depth:<6} {direct:<4} "
            f"{avg_bw:>10.1f} {avg_iops:>10.1f} "
            f"{avg_lat:>10.1f} {avg_p99:>10.1f} {count:>4}"
        )

    print(f"{'=' * 128}")
