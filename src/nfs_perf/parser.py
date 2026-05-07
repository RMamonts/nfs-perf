import argparse

from bench_config import BenchConfig


def parse_args(cgf: BenchConfig):
    parser = argparse.ArgumentParser(
        description="NFS Benchmark: nfs-mamont",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--fio-type",
        "--fio-types",
        dest="fio_types",
        nargs="+",
        choices=["read", "write", "randread", "randwrite", "randrw"],
        default=cgf.test_types,
        help=f"fio workload types to test (default: {cgf.test_types})",
    )
    parser.add_argument(
        "--block-sizes",
        nargs="+",
        default=cgf.block_sizes,
        help=f"Block sizes to test (default: {cgf.block_sizes})",
    )
    parser.add_argument(
        "--num-jobs",
        nargs="+",
        type=int,
        default=cgf.num_jobs_list,
        help=f"Number of fio jobs to test (default: {cgf.num_jobs_list})",
    )
    parser.add_argument(
        "--iodepths",
        nargs="+",
        type=int,
        default=cgf.iodepth_list,
        help=f"iodepth values to test (default: {cgf.iodepth_list})",
    )
    parser.add_argument(
        "--direct-modes",
        nargs="+",
        type=int,
        choices=[0, 1],
        default=cgf.direct_modes,
        help=f"direct modes to test (default: {cgf.direct_modes})",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=cgf.iterations,
        help=f"Number of iterations per combo (default: {cgf.iterations})",
    )
    parser.add_argument(
        "--size",
        default=cgf.size_per_job,
        help=f"Size per fio job (default: {cgf.size_per_job})",
    )
    parser.add_argument(
        "--test-dir",
        default=cgf.nfs_mount_point,
        help=f"Directory for fio test files (default: {cgf.nfs_mount_point})",
    )
    parser.add_argument(
        "--output-dir",
        default=cgf.output_dir,
        help=f"Directory for result files (default: {cgf.output_dir})",
    )
    parser.add_argument(
        "--server-host",
        default=cgf.nfs_server_ip,
        help=f"NFS server host (default: {cgf.nfs_server_ip})",
    )
    parser.add_argument(
        "--server-user",
        default=cgf.server_user,
        help=f"SSH user for remote server commands (default: {cgf.server_user})",
    )
    parser.add_argument(
        "--nfs-data-ip",
        default=cgf.nfs_data_ip,
        help=f"NFS data network IP for mount (default: {cgf.nfs_data_ip})",
    )
    parser.add_argument(
        "--mount-point",
        default=cgf.nfs_mount_point,
        help=f"Local NFS mount point (default: {cgf.nfs_mount_point})",
    )
    parser.add_argument(
        "--mamont-project-dir",
        default=cgf.mamont_project_dir,
        help=f"Project dir for nfs-mamont on server (default: {cgf.mamont_project_dir})",
    )
    parser.add_argument(
        "--mamont-export-root",
        default=cgf.mamont_export_root,
        help=f"Mamont config: export root dir (default: {cgf.mamont_export_root})",
    )
    parser.add_argument(
        "--mamont-branch",
        default=cgf.branch,
        help=f"Mamont branch (default: {cgf.mamont_export_root})",
    )
    parser.add_argument(
        "--mamont-commit",
        default=cgf.commit,
        help=f"Mamont commit (default: {cgf.mamont_export_root})",
    )
    parser.add_argument(
        "--mamont-export-paths",
        default=cgf.mamont_export_paths,
        help=f"Mamont config: export paths (default: {cgf.mamont_export_paths})",
    )
    parser.add_argument(
        "--mamont-mount-export",
        default=cgf.mamont_mount_export,
        help=f"NFS export path for mamont mount (default: {cgf.mamont_mount_export})",
    )
    parser.add_argument(
        "--mamont-mount-opts",
        default=cgf.mamont_mount_opts,
        help=f"Mount options for mamont (default: {cgf.mamont_mount_opts})",
    )

    parser.add_argument(
        "--local-mode",
        action="store_true",
        help="Run fio directly on server's local filesystem (skip NFS mount)",
    )

    args = parser.parse_args()

    return args
