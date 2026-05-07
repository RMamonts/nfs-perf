from bench_config import BenchConfig
from fio import FioResult, parse_fio_result, run_fio
from server_config import NFSServer


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
