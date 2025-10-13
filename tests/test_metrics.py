import pytest

from nfs_perf.metrics import parse_fio_line


def test_parse_fio_line_simple_read():
    """Tests parsing a simple READ line with MiB units."""
    fio_line = "READ: bw=123MiB/s (129MB/s), io=789MiB (827MB), run=10-20msec"
    result = parse_fio_line(fio_line)
    assert result == {
        "operation": "READ",
        "bw_mb_s": 123.0,
        "io_mb": 789.0,
        "runtime_ms": 10,
    }


def test_parse_fio_line_simple_write():
    """Tests parsing a simple WRITE line with MiB units."""
    fio_line = "WRITE: bw=4545MiB/s (4766MB/s), 4545MiB/s-4545MiB/s " \
    "(4766MB/s-4766MB/s), io=100MiB (105MB), run=22-22msec"
    result = parse_fio_line(fio_line)
    assert result == {
        "operation": "WRITE",
        "bw_mb_s": 4545.0,
        "io_mb": 100.0,
        "runtime_ms": 0,
    }


def test_parse_fio_line_with_kib_units():
    """Tests parsing a line with KiB units and converting to MB."""
    fio_line = "READ: bw=2048KiB/s (2.1MB/s), io=10240KiB (10MB), run=50-60msec"
    result = parse_fio_line(fio_line)
    assert result == {
        "operation": "READ",
        "bw_mb_s": 2.0,
        "io_mb": 10.0,
        "runtime_ms": 10,
    }


def test_parse_fio_line_with_gib_units():
    """Tests parsing a line with GiB units and converting to MB."""
    fio_line = "WRITE: bw=2GiB/s (2.1GB/s), io=10GiB (11GB), run=100-150msec"
    result = parse_fio_line(fio_line)
    assert result == {
        "operation": "WRITE",
        "bw_mb_s": 2048.0,
        "io_mb": 10240.0,
        "runtime_ms": 50,
    }


def test_parse_fio_line_zeroes():
    """Tests parsing a line with all zero values."""
    fio_line = "WRITE: bw=0MiB/s (0MB/s), io=0MiB (0MB), run=0-0msec"
    result = parse_fio_line(fio_line)
    assert result == {
        "operation": "WRITE",
        "bw_mb_s": 0.0,
        "io_mb": 0.0,
        "runtime_ms": 0,
    }


def test_parse_fio_line_invalid_format():
    """Tests that an invalid line format raises a ValueError."""
    fio_line = "This is not a valid fio output line"
    with pytest.raises(ValueError, match="Could not parse fio line"):
        parse_fio_line(fio_line)


def test_parse_fio_line_no_units():
    """Tests that a line missing units raises a ValueError."""
    fio_line = "READ: bw=100, io=200, run=10-20msec"
    with pytest.raises(ValueError, match="Could not parse fio line"):
        parse_fio_line(fio_line)
