"""Maintainer: run after committing source, then commit just the manifest.
The updater always reads immutable files from the recorded source commit.
"""

from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.cap_nhat_du_an import PREFIXES, ROOT_FILES, validate_manifest

ref = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
paths = subprocess.check_output(
    ["git", "ls-tree", "-r", "--name-only", ref], cwd=ROOT, text=True
).splitlines()
files = []
for name in paths:
    if name == "scripts/update_manifest.json":
        continue
    if name in ROOT_FILES or name.startswith(PREFIXES):
        data = subprocess.check_output(["git", "show", ref + ":" + name], cwd=ROOT)
        files.append({"path": name, "sha256": hashlib.sha256(data).hexdigest()})
manifest = {"ref": ref, "files": files}
validate_manifest(manifest)
(ROOT / "scripts/update_manifest.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print("Manifest:", ref, len(files), "files")
