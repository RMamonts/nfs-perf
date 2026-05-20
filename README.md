# nfs-perf

`nfs-perf` runs fio benchmarks against `nfs-mamont` or `nfs-ganesha`.
The tool starts the selected NFS server on a remote host, mounts the export on
the local client, runs the fio matrix, and writes CSV/JSON results.

## Requirements

- Python 3.10+
- [Poetry](https://python-poetry.org/)
- `fio` installed on the client where `nfs-perf` runs
- SSH access to the NFS server host
- `sudo` access on the client for mount/cache operations
- `sudo` access on the server for cache drops and `nfs-ganesha` management
- For mamont runs: `/home/ubuntu/nfs-mamont` exists on the server
- For ganesha runs: `ganesha.nfsd` is installed on the server

## Setup

```bash
poetry config virtualenvs.in-project true
poetry install
```

If Poetry was installed into `~/.local/bin`, make sure it is in `PATH`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## Run

The default benchmark matrix includes block sizes `4k`, `16k`, `32k`, `128k`,
and `1M`.

Run against `nfs-mamont`:

```bash
poetry run nfs-perf \
  --server mamont \
  --server-host <ssh-host-or-ip> \
  --nfs-data-ip <nfs-data-ip>
```

Run against `nfs-ganesha`:

```bash
poetry run nfs-perf \
  --server ganesha \
  --server-host <ssh-host-or-ip> \
  --nfs-data-ip <nfs-data-ip>
```

Run both servers in one benchmark for comparison:

```bash
poetry run nfs-perf \
  --server ganesha mamont \
  --server-host <ssh-host-or-ip> \
  --nfs-data-ip <nfs-data-ip>
```

Comma-separated form is also supported: `--server ganesha,mamont`.

`--server-host` is required. Use `--server-host localhost` only when the NFS
server should be started on the same machine where `nfs-perf` runs.

Useful options:

```bash
poetry run nfs-perf --help
poetry run nfs-perf --block-sizes 4k 16k 32k 128k 1M
poetry run nfs-perf --fio-types read write randread randwrite randrw
poetry run nfs-perf --num-jobs 1 4 16
poetry run nfs-perf --iodepths 1 8 32 64
poetry run nfs-perf --direct-modes 0 1
```

Results are written to `bench/results/` as `bench_<run>_<timestamp>.csv` and
`bench_<run>_<timestamp>.json`.

## Background Run

Use `PYTHONUNBUFFERED=1` and `tee` to keep the log complete and visible:

```bash
mkdir -p bench/logs
LOG="bench/logs/nfs-perf-$(date +%Y%m%d_%H%M%S).log"

nohup bash -c '
  PYTHONUNBUFFERED=1 poetry run nfs-perf \
    --server ganesha mamont \
    --server-host 10.78.119.148 \
    --nfs-data-ip 10.0.1.2 \
    --block-sizes 4k 16k 32k 128k 1M \
    2>&1 | tee -a "$1"
' _ "$LOG" >/dev/null 2>&1 &

echo "$LOG"
```

Watch the log:

```bash
tail -f "$LOG"
```

## Ganesha Config

For `--server ganesha`, the tool writes a generated config to
`/tmp/nfs-ganesha-bench.conf` on the server and starts:

```bash
sudo ganesha.nfsd -F -L /tmp/nfs-ganesha.log -f /tmp/nfs-ganesha-bench.conf
```

The generated config includes the benchmark tuning blocks and an `EXPORT` for
`/home/ubuntu/test` with pseudo path `/test`. NFSv3 mounts use the real export
path by default (`/home/ubuntu/test`); the pseudo path is for NFSv4.
These defaults can be changed:

```bash
poetry run nfs-perf \
  --server ganesha \
  --ganesha-export-root /home/ubuntu \
  --ganesha-export-paths test
```

## Development

```bash
poetry run ruff check src/nfs_perf
poetry run python -m compileall src/nfs_perf
```

## License

MIT License
