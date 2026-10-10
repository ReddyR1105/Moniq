"""Package Git-visible source and media; verify paths, CRCs and file hashes."""
import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT.parent / "Moniq-submission.zip"
FORBIDDEN_PARTS = {".git", ".venv", ".tools", ".runtime", "node_modules", "dist", "__pycache__", ".pytest_cache", ".ruff_cache", "test-results", "playwright-report"}
FORBIDDEN_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".joblib", ".pyc", ".pyo", ".log", ".pem", ".key", ".enc", ".tsbuildinfo"}
SECRET = re.compile(rb"(?:-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\bAKIA[A-Z0-9]{16}\b|\bgh[pousr]_[A-Za-z0-9]{30,}|\bsk-(?:proj-)?[A-Za-z0-9_-]{30,}|\bGOCSPX-[A-Za-z0-9_-]{20,})")


def source_files():
    result = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT, capture_output=True, check=True)
    names = sorted({name.decode("utf-8") for name in result.stdout.split(b"\0") if name})
    files = []
    for name in names:
        relative = Path(name)
        file = ROOT / relative
        if relative.is_absolute() or ".." in relative.parts or set(relative.parts) & FORBIDDEN_PARTS:
            raise ValueError(f"Unsafe package path: {name}")
        if file.is_symlink() or file.suffix.lower() in FORBIDDEN_SUFFIXES or (file.name.startswith(".env") and file.name != ".env.example") or any(word in file.name.lower() for word in ("client_secret", "credentials.enc")):
            raise ValueError(f"Sensitive/generated file in source set: {name}")
        if not file.is_file():
            continue
        content = file.read_bytes()
        if file.suffix.lower() not in {".png", ".webm"} and SECRET.search(content):
            raise ValueError(f"Possible credential in {name}; contents withheld")
        files.append((relative.as_posix(), content))
    required = {"README.md", ".env.example", ".github/workflows/ci.yml", "backend/requirements-lock.txt", "frontend/package-lock.json", "docs/QA_REPORT.md", "docs/DEMO_WALKTHROUGH.md", "docs/demo/moniq-demo.webm", "docs/demo/Moniq_Hacklanta_Final.mp4", "docs/demo/Moniq_All_Features.mp4", "docs/DEVPOST_SUBMISSION.md", "docs/JUDGES_PITCH.md", "docs/DEMO_SCRIPT.md", "docs/SUBMISSION_CHECKLIST.md", "tests/test_gmail.py", "tests/test_goals.py", "frontend/e2e/final.spec.ts"}
    assert required <= {name for name, _ in files}, "Required submission files missing"
    return files


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DESTINATION)
    args = parser.parse_args()
    DESTINATION = args.output.resolve()
    files = source_files()
    manifest = {name: hashlib.sha256(content).hexdigest() for name, content in files}
    with zipfile.ZipFile(DESTINATION, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files:
            archive.writestr(f"Moniq/{name}", content)
    with zipfile.ZipFile(DESTINATION) as archive:
        assert archive.testzip() is None, "ZIP CRC failure"
        assert len(archive.namelist()) == len(files)
        for name, digest in manifest.items():
            assert hashlib.sha256(archive.read(f"Moniq/{name}")).hexdigest() == digest
    summary = {"zip": str(DESTINATION), "source_files": len(files), "bytes": DESTINATION.stat().st_size,
               "sha256": hashlib.sha256(DESTINATION.read_bytes()).hexdigest(),
               "all_file_hashes_and_crc_verified": True, "source_secret_pattern_scan": "passed",
               "manifest": manifest}
    (ROOT / ".runtime/package-verification.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "manifest"}, indent=2))
