"""Download official, workspace-local validation tooling; no project secrets are used."""
import hashlib
import io
import json
import zipfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / ".tools" / "actionlint"
DEST.mkdir(parents=True, exist_ok=True)


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Moniq-local-validation"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


release = json.loads(fetch("https://api.github.com/repos/rhysd/actionlint/releases/latest"))
version = release["tag_name"].lstrip("v")
filename = f"actionlint_{version}_windows_amd64.zip"
assets = {asset["name"]: asset["browser_download_url"] for asset in release["assets"]}
archive = fetch(assets[filename])
checksums = fetch(assets[f"actionlint_{version}_checksums.txt"]).decode()
expected = next(line.split()[0] for line in checksums.splitlines() if line.split()[-1] == filename)
assert hashlib.sha256(archive).hexdigest() == expected, "actionlint checksum mismatch"
with zipfile.ZipFile(io.BytesIO(archive)) as package:
    (DEST / "actionlint.exe").write_bytes(package.read("actionlint.exe"))

refs = {}
for name in ("checkout", "setup-python", "setup-node", "upload-artifact"):
    ref = json.loads(fetch(f"https://api.github.com/repos/actions/{name}/git/ref/tags/v7"))
    obj = ref["object"]
    while obj["type"] == "tag":
        obj = json.loads(fetch(obj["url"]))["object"]
    refs[name] = obj["sha"]
(DEST / "action-refs.json").write_text(json.dumps(refs, indent=2), encoding="utf-8")
print(json.dumps({"actionlint": version, "sha256_verified": True, "action_v7_commits": refs}, indent=2))
