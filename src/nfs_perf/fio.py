import json
import subprocess
from dataclasses import dataclass

from bench_config import BenchConfig


@dataclass
class FioResult:
    server: str
    test_type: str
    block_size: str
    num_jobs: int
    iteration: int
    direct: int
    iodepth: int
    bw_bytes: int = 0  # bandwidth in bytes/sec
    bw_mib: float = 0.0  # bandwidth in MiB/s
    iops: float = 0.0
    slat_mean_us: float = 0.0
    clat_mean_us: float = 0.0
    lat_mean_us: float = 0.0
    lat_p50_us: float = 0.0
    lat_p95_us: float = 0.0
    lat_p99_us: float = 0.0
    lat_p999_us: float = 0.0
    usr_cpu: float = 0.0
    sys_cpu: float = 0.0
    ctx: int = 0
    runtime_ms: int = 0
    read_bw_bytes: int = 0
    read_iops: float = 0.0
    write_bw_bytes: int = 0
    write_iops: float = 0.0


def run_fio(
    test_name: str,
    rw: str,
    bs: str,
    numjobs: int,
    iodepth: int,
    direct: int,
    directory: str,
    cfg: BenchConfig,
    extra_args: list[str] | None,
) -> dict:
    """Run a single fio test and return parsed JSON output."""
    cmd = [
        "fio",
        f"--name={test_name}",
        f"--rw={rw}",
        f"--bs={bs}",
        f"--numjobs={numjobs}",
        f"--iodepth={iodepth}",
        f"--size={cfg.size_per_job}",
        f"--direct={direct}",
        f"--ioengine={cfg.ioengine}",
        f"--directory={directory}",
        "--filename_format=$jobname.$jobnum",
        "--group_reporting",
        "--output-format=json",
        "--fallocate=none",
        "--randrepeat=0",
    ]

    if extra_args:
        cmd.extend(extra_args)

    print(f" [fio] {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)

    if result.returncode != 0:
        print(f" [fio] FAILED (rc={result.returncode})")
        print(f" stderr: {result.stderr[:500]}")
        return {}

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print(" [fio] Failed to parse JSON output")
        print(f" stdout (first 500 chars): {result.stdout[:500]}")
        return {}


def parse_fio_result(
    raw: dict,
    server: str,
    test_type: str,
    bs: str,
    numjobs: int,
    iteration: int,
    iodepth: int,
    direct: int,
) -> FioResult | None:
    """Extract key metrics from fio JSON output."""
    if not raw or "jobs" not in raw:
        return None

    jobs = raw["jobs"]
    if not jobs:
        return None

    job = jobs[0]
    read_data = job.get("read", {})
    write_data = job.get("write", {})

    total_bw = read_data.get("bw_bytes", 0) + write_data.get("bw_bytes", 0)
    total_iops = read_data.get("iops", 0.0) + write_data.get("iops", 0.0)

    if read_data.get("bw_bytes", 0) > write_data.get("bw_bytes", 0):
        primary = read_data
    else:
        primary = write_data

    clat_ns = primary.get("clat_ns", {})
    slat_ns = primary.get("slat_ns", {})
    lat_ns = primary.get("lat_ns", {})
    lat_info = lat_ns if lat_ns.get("mean", 0) > 0 else clat_ns
    percentiles = lat_info.get("percentile", {})

    return FioResult(
        server=server,
        test_type=test_type,
        block_size=bs,
        num_jobs=numjobs,
        iteration=iteration,
        direct=direct,
        iodepth=iodepth,
        bw_bytes=total_bw,
        bw_mib=round(total_bw / (1024 * 1024), 2),
        iops=round(total_iops, 2),
        slat_mean_us=round(slat_ns.get("mean", 0) / 1000, 2),
        clat_mean_us=round(clat_ns.get("mean", 0) / 1000, 2),
        lat_mean_us=round(lat_info.get("mean", 0) / 1000, 2),
        lat_p50_us=round(percentiles.get("50.000000", 0) / 1000, 2),
        lat_p95_us=round(percentiles.get("95.000000", 0) / 1000, 2),
        lat_p99_us=round(
            percentiles.get("99.000000", 0) / 1000,
            2,
        ),
        lat_p999_us=round(percentiles.get("99.900000", 0) / 1000, 2),
        usr_cpu=round(job.get("usr_cpu", 0.0), 2),
        sys_cpu=round(job.get("sys_cpu", 0.0), 2),
        ctx=int(job.get("ctx", 0)),
        runtime_ms=primary.get("runtime", 0),
        read_bw_bytes=read_data.get("bw_bytes", 0),
        read_iops=round(read_data.get("iops", 0.0), 2),
        write_bw_bytes=write_data.get("bw_bytes", 0),
        write_iops=round(write_data.get("iops", 0.0), 2),
    )
