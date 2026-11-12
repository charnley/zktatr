"""Due dates the GNU `date -d` way: `tomorrow`, `next monday`, `next month`, `+3 days`.

Parsing is delegated to GNU date so we get its full grammar for free. macOS ships
BSD date, which cannot do this; `gdate` (brew install coreutils) is used when
present, and a plain `date` only if it is the GNU one.
"""

import re
import shutil
import subprocess
from datetime import date, datetime
from functools import cache

ISO = re.compile(r"\d{4}-\d{2}-\d{2}")


@cache
def gnu_date() -> str:
    for name in ("gdate", "date"):
        exe = shutil.which(name)
        if exe is None:
            continue
        res = subprocess.run([exe, "--version"], capture_output=True, text=True)
        if res.returncode == 0 and "GNU" in res.stdout:
            return exe
    raise RuntimeError("GNU date not found (macOS: brew install coreutils, gives `gdate`)")


def parse_due(text: str) -> date:
    """`2026-11-20` or anything GNU `date -d` understands, as a local date."""
    text = " ".join(text.split())
    if ISO.fullmatch(text):
        try:
            return datetime.strptime(text, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError(f"invalid date: {text!r}") from None
    if not text or text.startswith("-"):  # never let a value pose as a `date` option
        raise ValueError(f"invalid date: {text!r}")
    res = subprocess.run(
        [gnu_date(), "-d", text, "+%F"], capture_output=True, text=True
    )
    out = res.stdout.strip()
    if res.returncode != 0 or not ISO.fullmatch(out):
        raise ValueError(f"cannot understand date: {text!r} (try 'tomorrow', 'next monday', 'next month')")
    return datetime.strptime(out, "%Y-%m-%d").date()
