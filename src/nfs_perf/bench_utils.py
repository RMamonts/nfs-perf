from .bench_config import BenchConfig
from .fio import FioResult, parse_fio_result, run_fio
from .helpers import drop_caches, print_file_allocation
from .server_config import NFSServer

READ_PREPARED_WORKLOADS = {"read", "randread"}


def needs_read_prepare(rw: str) -> bool:
    return rw in READ_PREPARED_WORKLOADS


def prepare_read_files(
    server: NFSServer,
    test_dir: str,
    numjobs: int,
    iodepth: int,
    cfg: BenchConfig,
) -> bool:
    """Write real data before read-only tests so fio cannot read sparse holes."""
    print(" [prepare] Writing test files for read workload")
    raw = run_fio(
        test_name="testfile",
        rw="write",
        bs="1M",
        numjobs=numjobs,
        iodepth=iodepth,
        direct=1,
        directory=test_dir,
        extra_args=["--end_fsync=1"],
        cfg=cfg,
    )
    if not raw:
        print(" [prepare] FAILED to create read workload files")
        return False

    print_file_allocation(test_dir)
    drop_caches(server.executor)
    return True


def run_test_case(
    server: NFSServer,
    test_dir: str,
    test_type: str,
    rw: str,
    bs: str,
    numjobs: int,
    iodepth: int,
    direct: int,
    iteration: int,
    cfg: BenchConfig,
) -> FioResult | None:
    """Run a single fio test case."""
    srv_name = server.name
    print(f"\n{'=' * 72}")
    print(
        f" [{srv_name}] {test_type} | bs={bs} jobs={numjobs} depth={iodepth} "
        f"direct={direct} iter={iteration}"
    )
    print(f"{'=' * 72}")
    extra_args = ["--rwmixread=50"] if rw == "randrw" else None
    if needs_read_prepare(rw):
        if not prepare_read_files(server, test_dir, numjobs, iodepth, cfg):
            return None
        extra_args = (extra_args or []) + ["--allow_file_create=0"]

    raw = run_fio(
        test_name="testfile",
        rw=rw,
        bs=bs,
        numjobs=numjobs,
        iodepth=iodepth,
        direct=direct,
        directory=test_dir,
        extra_args=extra_args,
        cfg=cfg,
    )
    res = parse_fio_result(
        raw, srv_name, test_type, bs, numjobs, iteration, iodepth, direct
    )
    if res:
        print(
            f" => BW={res.bw_mib} MiB/s IOPS={res.iops} "
            f"""slat={res.slat_mean_us}us clat={res.clat_mean_us}
            us p99={res.lat_p99_us}us"""
        )
    else:
        print(" => FAILED or no data")
    return res
