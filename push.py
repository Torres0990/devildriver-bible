#!/usr/bin/env python3
"""Push the devildriver-bible site source to GitHub (Torres0990/devildriver-bible).

Uses the Contents API via the github skill's gh_api.py shim (surrogate auth).
Works on empty repos (first PUT creates the initial commit). One commit per file.
"""
import base64
import json
import subprocess
import sys
from pathlib import Path

SITE = Path.home() / "workspace/games/devildriver/site"
SHIM = Path.home() / "workspace/skills/github/bin/gh_api.py"
REPO = "Torres0990/devildriver-bible"

FILES = [
    "devildriver.json", "build.py", "deploy.py", "push.py", "README.md",
    "assets/samurai-base.webp", "assets/katana.webp",
]


def gh(method, path, body=None):
    spec = {"method": method, "path": path}
    if body is not None:
        spec["body"] = body
    p = subprocess.run([sys.executable, str(SHIM)], input=json.dumps(spec),
                       capture_output=True, text=True, timeout=120)
    r = json.loads(p.stdout)
    b = r["body"]
    if isinstance(b, str):
        try:
            b = json.loads(b)
        except Exception:
            pass
    return r["status"], b


def main():
    for rel in FILES:
        data = (SITE / rel).read_bytes()
        # get current sha if the file exists (for updates)
        s, b = gh("GET", f"/repos/{REPO}/contents/{rel}")
        sha = b.get("sha") if s == 200 and isinstance(b, dict) else None
        body = {"message": f"devildriver bible: {rel}",
                "content": base64.b64encode(data).decode()}
        if sha:
            body["sha"] = sha
        s, b = gh("PUT", f"/repos/{REPO}/contents/{rel}", body)
        if s not in (200, 201):
            print(f"FAILED {rel}: {s} {str(b)[:300]}")
            sys.exit(1)
        print("pushed", rel, (b["commit"]["sha"][:8] if isinstance(b, dict) else ""))
    print("done -> https://github.com/" + REPO)


if __name__ == "__main__":
    main()
