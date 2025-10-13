import csv
import subprocess
from collections.abc import Iterable
from datetime import datetime

from .metrics import parse_fio_line

FIO_PARAMS: dict[str, Iterable] = {
    "operations": ["read", "write"],
    "numjobs": [1, 2, 4, 8, 16],
    "block_sizes": ["4k", "8k", "16k", "256k", "512k", "1M"],
    "iodepths": [1, 4, 8, 16],
    "runtime_seconds": 5,
    "direct": 0,
    "directory": "/mnt/nfs",
    "file_size": "1G",
}


def create_command(
    optype: str,
    numjobs: int,
    block_size: str,
    iodepth: int,
    runtime: int,
    direct: int,
    directory: str,
    file_size: str,
) -> str:
    """Builds a fio command string with time-based execution."""

    parts = [
        "fio",
        "--name=test",
        "--ioengine=libaio",
        f"--rw={optype}",
        f"--numjobs={numjobs}",
        f"--bs={block_size}",
        f"--iodepth={iodepth}",
        f"--direct={direct}",
        "--group_reporting=1",
        "--time_based=1",
        f"--runtime={runtime}",
        f"--size={file_size}",
        "--unlink=1",
        f"--directory={directory}",
    ]

    return " ".join(parts)


def run_fio_tests() -> None:
    """Executes a matrix of fio tests and writes aggregated metrics to CSV."""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"fio_performance_{timestamp}.csv"

    fieldnames = [
        "operation",
        "numjobs",
        "block_size",
        "iodepth",
        "runtime_seconds",
        "bw_mb_s",
        "io_mb",
        "runtime_ms",
    ]

    print("Starting FIO parameter testing...")
    print(f"Results will be saved to: {csv_filename}")
    print("=" * 80)

    with open(csv_filename, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for op in FIO_PARAMS["operations"]:
            for nj in FIO_PARAMS["numjobs"]:
                for bs in FIO_PARAMS["block_sizes"]:
                    for io_depth in FIO_PARAMS["iodepths"]:
                        command = create_command(
                            op,
                            nj,
                            bs,
                            io_depth,
                            runtime=FIO_PARAMS["runtime_seconds"],
                            direct=FIO_PARAMS["direct"],
                            directory=FIO_PARAMS["directory"],
                            file_size=FIO_PARAMS["file_size"],
                        )

                        result = subprocess.run(
                            command,
                            shell=True,
                            capture_output=True,
                            text=True,
                            check=False,
                        )

                        if result.returncode != 0:
                            print(
                                "fio command failed"
                            )
                            continue

                        try:
                            last_line = result.stdout.strip().split("\n")[-1]
                            metrics = parse_fio_line(last_line)
                        except ValueError:
                            print(
                                "Error parsing fio output"
                            )
                            continue

                        row = {
                            "operation": op,
                            "numjobs": nj,
                            "block_size": bs,
                            "iodepth": io_depth,
                            "runtime_seconds": FIO_PARAMS["runtime_seconds"],
                            "bw_mb_s": metrics["bw_mb_s"],
                            "io_mb": metrics["io_mb"],
                            "runtime_ms": metrics["runtime_ms"],
                        }

                        print(
                            f"op={op}, numjobs={nj}, bs={bs}, iodepth={io_depth} -> "
                            f"bw={row['bw_mb_s']:.2f} MB/s, io={row['io_mb']:.2f} MB"
                        )

                        writer.writerow(row)
