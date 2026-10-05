#!/usr/bin/env python3
"""Deploy ~/workspace/games/devildriver/site to Cloudflare Pages (direct upload).

Protocol (reverse-engineered from wrangler, verified against multiple sources):
1. POST /accounts/{id}/pages/projects/{name}/upload-token (account token) -> JWT
2. POST /pages/assets/upload (Bearer JWT): [{key, value:b64, metadata:{contentType}, base64:true}]
3. POST /pages/assets/upsert-hashes (Bearer JWT): {hashes:[...]}
4. POST /accounts/{id}/pages/projects/{name}/deployments (account token, multipart manifest)
Hash: blake3(base64(file_bytes) + ext_without_dot).hexdigest()[:32]

Account-token calls go through the cloudflare skill shim (surrogate auth).
JWT calls use plain urllib — the JWT is short-lived and project-scoped, never
the raw account credential.
"""
import base64
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import blake3

SITE = Path.home() / "workspace/games/devildriver/site"
SHIM = Path.home() / "workspace/skills/cloudflare/bin/cf_fetch.py"
ACCOUNT = "57456d82b9eef741f83c2af00a861986"
PROJECT = "devildriver-bible"
V4 = "https://api.cloudflare.com/client/v4"

PUBLISH = [
    "index.html", "demons.html", "arena.html", "mechanics.html",
    "styles.html", "pipeline.html", "prompts.html", "economy.html",
    "devildriver.json", "llms.txt",
    "assets/samurai-base.webp", "assets/katana.webp",
]
CTYPES = {".html": "text/html", ".json": "application/json",
          ".txt": "text/plain", ".webp": "image/webp"}


def cf(spec):
    p = subprocess.run([sys.executable, str(SHIM)], input=json.dumps(spec),
                       capture_output=True, text=True, timeout=120)
    try:
        return json.loads(p.stdout)
    except Exception:
        return {"status": 0, "body": "shim stdout unparseable: " + p.stdout[:300]}


def jwt_post(path, payload, jwt):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(V4 + path, data=data, method="POST",
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {jwt}",
                                          "User-Agent": "muse-deploy/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return {"status": resp.status, "body": json.loads(resp.read().decode())}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "body": e.read().decode()[:600]}
    except Exception as e:
        return {"status": 0, "body": str(e)[:300]}


def file_hash(data: bytes, name: str) -> str:
    ext = Path(name).suffix  # '.webp' -> 'webp'; '' for no extension
    ext_nodot = ext[1:] if ext.startswith(".") else ext
    return blake3.blake3(base64.b64encode(data) + ext_nodot.encode()).hexdigest()[:32]


def main():
    # 1. upload token (JWT)
    r = cf({"url": f"{V4}/accounts/{ACCOUNT}/pages/projects/{PROJECT}/upload-token",
            "method": "GET"})
    body = r["body"] if isinstance(r["body"], dict) else {}
    jwt = (body.get("result") or {}).get("jwt")
    if not jwt:
        print("upload-token failed:", r["status"], str(r["body"])[:400])
        sys.exit(1)
    print("got upload JWT")

    # 2. hash + upload assets
    assets, manifest = [], {}
    for rel in PUBLISH:
        data = (SITE / rel).read_bytes()
        h = file_hash(data, rel)
        manifest["/" + rel] = h
        ctype = CTYPES.get(Path(rel).suffix, "application/octet-stream")
        assets.append({"key": h, "value": base64.b64encode(data).decode(),
                       "metadata": {"contentType": ctype}, "base64": True})
    print(f"uploading {len(assets)} assets...")
    r = jwt_post("/pages/assets/upload", assets, jwt)
    print("upload:", r["status"], str(r["body"])[:300])
    if r["status"] != 200:
        sys.exit(1)

    # 3. upsert hashes
    r = jwt_post("/pages/assets/upsert-hashes",
                 {"hashes": [a["key"] for a in assets]}, jwt)
    print("upsert-hashes:", r["status"], str(r["body"])[:300])
    if r["status"] != 200:
        sys.exit(1)

    # 4. create deployment
    r = cf({"url": f"{V4}/accounts/{ACCOUNT}/pages/projects/{PROJECT}/deployments",
            "method": "POST",
            "multipart": {"fields": {"manifest": manifest, "branch": "main"},
                          "files": {}}})
    rbody = r["body"] if isinstance(r["body"], dict) else {}
    if not (r["status"] == 200 and rbody.get("success")):
        print("deployment failed:", r["status"], str(r["body"])[:600])
        sys.exit(1)
    dep = rbody["result"]
    dep_id, url = dep["id"], dep.get("url")
    print("deployment:", dep_id, url)

    # 5. poll
    for _ in range(30):
        r = cf({"url": f"{V4}/accounts/{ACCOUNT}/pages/projects/{PROJECT}/deployments/{dep_id}",
                "method": "GET"})
        rb = r["body"] if isinstance(r["body"], dict) else {}
        if r["status"] == 200 and rb.get("success"):
            stage = (rb["result"].get("latest_stage") or {})
            if stage.get("status") in ("success", "failure", "failed"):
                print("FINAL:", stage.get("status"), rb["result"].get("url"))
                # sanity: fetch the live page
                try:
                    with urllib.request.urlopen(url, timeout=30) as resp:
                        html = resp.read().decode()
                    print("live check:", resp.status,
                          "DEVILDRIVER" in html.upper() and "title ok" or "content?")
                except Exception as e:
                    print("live check failed:", str(e)[:200])
                sys.exit(0 if stage.get("status") == "success" else 1)
        time.sleep(6)
    print("timed out waiting for deployment")
    sys.exit(1)


if __name__ == "__main__":
    main()
