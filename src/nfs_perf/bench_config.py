class BenchConfig:
    server_type: str = "mamont"
    block_sizes: list[str] = ["4k", "16k", "32k", "128k", "1M"]
    num_jobs_list: list[int] = [1, 4, 16]
    iodepth_list: list[int] = [32]
    direct_modes: list[int] = [0, 1]
    test_types: list[str] = ["read", "write", "randread", "randwrite", "randrw"]
    size_per_job: str = "10G"
    iterations: int = 1
    ioengine: str = "libaio"
    mamont_project_dir: str = "/home/ubuntu/nfs-mamont"
    mamont_export_root: str = "/home/ubuntu"
    mamont_export_paths: str = "test"
    mamont_mount_export: str = "/test"
    mamont_mount_opts: str = "vers=3,tcp,proto=tcp,port=2049,mountport=2049,nolock"
    ganesha_binary: str = "ganesha.nfsd"
    ganesha_config_path: str = "/tmp/nfs-ganesha-bench.conf"
    ganesha_export_root: str = "/home/ubuntu"
    ganesha_export_paths: str = "test"
    ganesha_mount_export: str | None = None
    ganesha_mount_opts: str = "vers=3,tcp,proto=tcp,nolock"
    nfs_mount_point: str = "/mnt/nfs_test"
    nfs_server_ip: str | None = None
    nfs_data_ip: str = "10.0.1.2"
    server_user: str = "ubuntu"
    test_dir: str = "/mnt/nfs_test"
    output_dir: str = "bench/results"
    commit: str | None = None
    branch: str | None = None
