# nfs-perf

**nfs-perf** is a Python tool for automated performance testing of NFS (Network File System) storage using [fio](https://github.com/axboe/fio). It runs a matrix of fio tests with various parameters and aggregates the results into a CSV file for further analysis.

## Requirements

- Python 3.8+
- [Poetry](https://python-poetry.org/) for dependency management
- `fio` installed on the system
- NFS mount point available (default: `/mnt/nfs`)

Advice - use venv in project

```bash
poetry config virtualenvs.in-project true
```

## Installation

Clone the repository and install dependencies:

```bash
git clone git@github.com:RMamonts/nfs-perf.git
cd nfs-perf
poetry install
```

## Usage

1. Make sure your NFS share is mounted (default: `/mnt/nfs`).
2. Run the benchmark:

```bash
poetry run nfs-perf
```

3.Results will be saved as a CSV file in the project directory (e.g., `fio_performance_YYYYMMDD_HHMMSS.csv`).

## Configuration

You can change test parameters in `src/nfs_perf/runner.py` by editing the `FIO_PARAMS` dictionary:

```python
FIO_PARAMS = {
    "operations": ["read", "write"],
    "numjobs": [1, 2, 4, 8, 16],
    "block_sizes": ["4k", "8k", "16k", "256k", "512k", "1M"],
    "iodepths": [1, 4, 8, 16],
    "runtime_seconds": 5,
    "direct": 0,
    "directory": "/mnt/nfs",
    "file_size": "1G",
}
```

## Development

- Lint code with [Ruff](https://github.com/astral-sh/ruff):

  ```bash
  poetry run ruff check .
  ```

- Run tests:

  ```bash
  poetry run pytest
  ```

## License

MIT License
