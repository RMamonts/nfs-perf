# import re

# def _convert_to_mb(value, unit):
#     """Converts a value from a given unit to megabytes (MB)."""
#     unit = unit.lower()
#     if unit in ["mb", "mib"]:
#         return value
#     elif unit in ["kb", "kib"]:
#         return value / 1024
#     elif unit in ["gb", "gib"]:
#         return value * 1024
#     elif unit in ["b"]:
#         return value / (1024 * 1024)
#     return 0.0

import re


def _convert_to_mb(value: float, unit: str) -> float:
    """Converts a value from a given unit to megabytes (MB)."""
    # Normalize unit by removing '/s' for bandwidth units
    unit = unit.lower().replace("/s", "")
    if unit in ["mb", "mib"]:
        return value
    elif unit in ["kb", "kib"]:
        return value / 1024
    elif unit in ["gb", "gib"]:
        return value * 1024
    elif unit == "b":
        return value / (1024 * 1024)
    return 0.0


def parse_fio_line(fio_output_line: str) -> dict:
    """
    Parses a single summary line from the FIO tool output.

    This function extracts performance metrics such as bandwidth and total I/O
    from a FIO summary line. It handles various units (B, KB, MB, GB, KiB, MiB, GiB)
    and converts them to a common base unit (megabytes).

    Args:
        fio_output_line: A string containing the FIO summary line.
                         Example: "READ: bw=123MiB/s (129MB/s),
                           io=789MiB (827MB), run=10-20msec"

    Returns:
        A dictionary containing the parsed and converted metrics:
        - 'operation': The I/O operation type (e.g., 'READ', 'WRITE').
        - 'bw_mb_s': Bandwidth in megabytes per second.
        - 'io_mb': Total I/O in megabytes.
        - 'runtime_ms': Total runtime in milliseconds.

    Raises:
        ValueError: If the line cannot be parsed.
    """
    line = fio_output_line.strip()

    pattern = (
        r"^(?P<operation>[A-Z]+):"
        r".*?bw=(?P<bw_val>[\d\.]+)(?P<bw_unit>[a-zA-Z]+)/s"
        r".*?io=(?P<io_val>[\d\.]+)(?P<io_unit>[a-zA-Z]+)"
        r".*?run=(?P<run_start>\d+)-(?P<run_end>\d+)msec"
    )

    match = re.search(pattern, line)

    if not match:
        raise ValueError(f"Could not parse fio line: {line}")

    data = match.groupdict()

    return {
        "operation": data["operation"],
        "bw_mb_s": _convert_to_mb(float(data["bw_val"]), data["bw_unit"]),
        "io_mb": _convert_to_mb(float(data["io_val"]), data["io_unit"]),
        "runtime_ms": (int(data["run_end"]) + int(data["run_start"])) / 2,
    }
