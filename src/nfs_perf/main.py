from nfs_perf.runner import run_fio_tests


def main():
    print("=" * 10, " STARTING NFS-PERF!", "=" * 10)
    run_fio_tests()
    print("=" * 10, " FINISHED NFS-PERF!", "=" * 10)
