"""Verify the vendored upstream workflows without network access."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
source = json.loads((ROOT / ".agents/agent-skills-source.json").read_text())
for item in source["files"]:
    path = ROOT / item["path"]
    if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
        raise SystemExit(f"Upstream workflow differs: {item['path']}")
print(f"Verified {len(source['files'])} upstream files at {source['commit']}")
