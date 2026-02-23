#!/usr/bin/env python3

"""
Time related utilities.
"""

"""Code to probe the real system clock time versus `time.time()` an if they're out of sync, wait."""

from ctypes import cdll, c_longlong, c_long, pointer, sizeof, Structure
from errno import EINVAL
from functools import cached_property
from logging import error, warning
import time


class PTP:
    """Interface to access The Precision Time Protocol (Linux only)."""

    PTP_DEV = "/dev/ptp0"
    CLOCK_ID_FD_BASE = 0xFFFFFFE0
    LIBC = "libc.so.6"

    class TimeSpecCTYPE(Structure):
        _fields_ = [
            ("tv_sec", c_longlong),
            ("tv_nsec", c_long),
        ]

    @cached_property
    def libc(self):
        return cdll.LoadLibrary(self.LIBC)

    def gettime(self) -> float:
        tv = self.TimeSpecCTYPE()
        libc = self.libc
        with open(self.PTP_DEV, "rb") as ptpf:
            ptp_fd = ptpf.fileno()
            if ptp_fd > 0x0F:
                raise ValueError(
                    f"open({self.PTP_DEV!r}).fileno()={ptp_fd}: exceeds 0x0f, too big for the mask 0x{self.CLOCK_ID_FD_BASE:x}"
                )
            clock_id = self.CLOCK_ID_FD_BASE | ptp_fd
            if libc.clock_gettime(clock_id, pointer(tv)) != 0:
                raise OSError(EINVAL, f"libc.clock_gettime(0x{clock_id:x},buf) fails")

        return tv.tv_sec + tv.tv_nsec / 1000000000


# make an instance of the class to use for access
ptp = PTP()


def ptp_gettime() -> float:
    """Return the PTP time."""
    return ptp.gettime()


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
    wait_for_time_sync()
