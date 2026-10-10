"""Restrict locally stored secrets to the owner and Windows SYSTEM."""
import csv
import io
import os
import subprocess
from functools import cache
from pathlib import Path


@cache
def windows_owner_sid():
    command = Path(os.environ["SystemRoot"]) / "System32" / "whoami.exe"
    result = subprocess.run([str(command), "/user", "/fo", "csv", "/nh"], check=True, capture_output=True,
                            text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    return next(csv.reader(io.StringIO(result.stdout)))[1]


def protect_local_path(path, directory=False):
    path = Path(path)
    if os.name == "nt":
        command = Path(os.environ["SystemRoot"]) / "System32" / "icacls.exe"
        access = "(OI)(CI)F" if directory else "F"
        subprocess.run([str(command), str(path), "/inheritance:r", "/grant:r",
                        f"*{windows_owner_sid()}:{access}", f"*S-1-5-18:{access}"],
                       check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        path.chmod(0o700 if directory else 0o600)
