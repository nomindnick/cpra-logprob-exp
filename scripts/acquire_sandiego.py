"""Acquire CPRA request text and produced documents from the County of San Diego
NextRequest portal (https://pra.sandiegocounty.gov).

Two steps, both idempotent:

  python scripts/acquire_sandiego.py manifest 25-3152 24-409 ...
      -> data/manifests/sandiego/{id}.request.json   (request metadata + text)
      -> data/manifests/sandiego/{id}.documents.jsonl (one row per published document)

  python scripts/acquire_sandiego.py download 25-3152 24-409 ... [--ext msg,eml]
      -> data/raw/sandiego/{id}/{document_id}.{ext}

Manifests are committed (they are the reproducibility index); raw files are not.

Etiquette: bounded to the request IDs given, one HTTP call per --delay seconds,
browser User-Agent (the portal's CDN returns 403 to non-browser UAs on downloads).
Stdlib only.
"""
import argparse
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

BASE = "https://pra.sandiegocounty.gov"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/128.0 Safari/537.36")
MANIFEST_DIR = pathlib.Path("data/manifests/sandiego")
RAW_DIR = pathlib.Path("data/raw/sandiego")


class Client:
    def __init__(self, delay):
        self.delay = delay
        self._last = 0.0

    def _throttle(self):
        wait = self._last + self.delay - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self._last = time.monotonic()

    def get(self, url, referer=None, retries=3):
        headers = {"User-Agent": UA, "Accept": "application/json, */*"}
        if referer:
            headers["Referer"] = referer
        for attempt in range(retries):
            self._throttle()
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=120) as r:
                    return r.read(), r.headers
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503) and attempt < retries - 1:
                    time.sleep(10 * (attempt + 1))
                    continue
                raise
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                # transient network trouble (read timeout, reset); back off and retry
                if attempt < retries - 1:
                    time.sleep(10 * (attempt + 1))
                    continue
                raise

    def json(self, url):
        body, _ = self.get(url)
        return json.loads(body)


def manifest(client, req_id):
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    meta = client.json(f"{BASE}/client/requests/{req_id}")
    (MANIFEST_DIR / f"{req_id}.request.json").write_text(json.dumps(meta, indent=1))

    out = MANIFEST_DIR / f"{req_id}.documents.jsonl"
    rows, page, total = [], 1, None
    while True:
        d = client.json(f"{BASE}/client/request_documents?request_id={req_id}&page_number={page}")
        total = d["total_documents_count"]
        docs = d["documents"]
        if not docs:
            break
        for x in docs:
            rows.append({
                "request_id": req_id, "document_id": x["id"], "title": x["title"],
                "file_extension": x["file_extension"], "visibility": x["visibility"],
                "file_size_mb": (x.get("document_scan") or {}).get("file_size"),
                "upload_date": (x.get("document_scan") or {}).get("upload_date"),
                "folder_name": x.get("folder_name"), "subfolder_name": x.get("subfolder_name"),
                "expiration_date": x.get("expiration_date"),
                "download_url": f"{BASE}/documents/{x['id']}/download",
            })
        print(f"  {req_id} page {page}: {len(rows)}/{total}", file=sys.stderr)
        if len(rows) >= total:
            break
        page += 1
    with out.open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"{req_id}: {len(rows)} documents (portal says {total}) -> {out}", file=sys.stderr)


def download(client, req_id, exts):
    rows = [json.loads(l) for l in (MANIFEST_DIR / f"{req_id}.documents.jsonl").open()]
    rows = [r for r in rows if r["file_extension"] in exts and r["visibility"] == "Public"]
    dest = RAW_DIR / req_id
    dest.mkdir(parents=True, exist_ok=True)
    done = skipped = failed = 0
    for r in rows:
        path = dest / f"{r['document_id']}.{r['file_extension']}"
        if path.exists() and path.stat().st_size > 0:
            skipped += 1
            continue
        try:
            body, headers = client.get(r["download_url"], referer=f"{BASE}/documents/{r['document_id']}")
        except urllib.error.HTTPError as e:
            print(f"  FAIL {r['document_id']} HTTP {e.code}", file=sys.stderr)
            failed += 1
            continue
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            print(f"  FAIL {r['document_id']} {type(e).__name__}: {e}", file=sys.stderr)
            failed += 1
            continue
        if not body or body[:15].lower().startswith(b"<!doctype html") or body[:5] == b"<html":
            print(f"  FAIL {r['document_id']} got HTML instead of file", file=sys.stderr)
            failed += 1
            continue
        path.write_bytes(body)
        done += 1
        if done % 50 == 0:
            print(f"  {req_id}: {done} downloaded, {skipped} skipped, {failed} failed", file=sys.stderr)
    print(f"{req_id}: {done} downloaded, {skipped} already present, {failed} failed "
          f"of {len(rows)} {'/'.join(sorted(exts))} documents", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["manifest", "download"])
    ap.add_argument("request_ids", nargs="+")
    ap.add_argument("--ext", default="msg,eml", help="comma-separated extensions to download")
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between HTTP calls")
    a = ap.parse_args()
    client = Client(a.delay)
    for rid in a.request_ids:
        if a.step == "manifest":
            manifest(client, rid)
        else:
            download(client, rid, set(a.ext.split(",")))


if __name__ == "__main__":
    main()
