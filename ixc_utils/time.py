#!/usr/bin/env python3

"""
Time related utilities.
"""

import time
from ctypes import Structure, c_long, c_longlong, cdll, pointer
from errno import EINVAL
from logging import error, warning

PTP_DEV = "/dev/ptp0"
CLOCK_ID_FD_BASE = 0xFFFFFFE0
LIBC = "libc.so.6"

_libc_dll = None  # will be the libc .so


class TimeSpecCTYPE(Structure):
    _fields_ = [
        ("tv_sec", c_longlong),
        ("tv_nsec", c_long),
    ]


def libc():
    """Return the loaded library for libc."""
    global _libc_dll
    if _libc_dll is None:
        _libc_dll = cdll.LoadLibrary(LIBC)
    return _libc_dll


def ptp_gettime() -> float:
    """Obtain the time from the PTP device."""
    tv = TimeSpecCTYPE()
    with open(PTP_DEV, "rb") as ptpf:
        ptp_fd = ptpf.fileno()
        if ptp_fd > 0x0F:
            raise ValueError(
                f"open({PTP_DEV!r}).fileno()={ptp_fd}: exceeds 0x0f, too big for the mask 0x{CLOCK_ID_FD_BASE:x}"
            )
        clock_id = CLOCK_ID_FD_BASE | ptp_fd
        if libc().clock_gettime(clock_id, pointer(tv)) != 0:
            raise OSError(EINVAL, f"libc.clock_gettime(0x{clock_id:x},buf) fails")

    return tv.tv_sec + tv.tv_nsec / 1000000000


def wait_for_time_sync(epsilon=0.1, tolerance=3.0, step=0.2) -> float:
    """
    Wait for `time.time()` to be close enough to the time from `ptp_gettime()`.
    Return the elapsed time spent waiting for synchronisation.
    Raise `RuntimeError` if the times are not in sync by then.

    A fly.io VM resumed from suspension initially has the pre-suspension
    time returned from `time.time()`. The fly.io infrastructure
    undertakes to update it to reality fairly promptly (likely <1s)
    (see https://community.fly.io/t/better-paradox-prevention-suspend-resume-clocks/25959).

    On that basis, this function checks the PTP time against `time.time()`
    and waits up to `tolerance` second for things to be in sync.
    """
    if epsilon <= 0:
        raise ValueError(f"{epsilon=} should be > 0")
    if tolerance <= 0:
        raise ValueError(f"{tolerance=} should be > 0")
    if step <= 0:
        raise ValueError(f"{step=} should be > 0")
    if step > tolerance:
        step = tolerance
    elapsed = 0.0
    while True:
        ptp_time = ptp_gettime()
        time_time = time.time()
        if abs(ptp_time - time_time) <= epsilon:
            break
        if elapsed == 0.0:
            warning(
                f"clock out of sync: time.time() {time_time:f} more than {epsilon:f}s from ptp_gettime() {ptp_time:f}"
            )
        elif elapsed >= tolerance:
            error(
                f"clock still out of sync after {elapsed:f}s: time.time() {time_time:f}, ptp_gettime() {ptp_time:f}"
            )
            raise RuntimeError(
                f"time.time() {time_time:f}, ptp_gettime() {ptp_time:f}, discrepancy > {epsilon:f}s after {elapsed:f}s"
            )
        time.sleep(step)
        elapsed += step
    if elapsed > 0.0:
        warning(
            f"clock in sync after {elapsed:f}s: time.time() {time_time:f}, ptp_gettime() {ptp_time:f}"
        )
    return elapsed


if __name__ == "__main__":
    import sys

    if sys.argv[1:] == ["poll"]:
        while True:
            print(time.time(), "PTP:", ptp_gettime(), flush=True)
            time.sleep(0.1)
    else:
        wait_for_time_sync()
