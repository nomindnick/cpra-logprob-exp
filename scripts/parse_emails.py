"""Parse downloaded productions into one JSONL row per email.

  uv run python scripts/parse_emails.py sandiego

Reads  data/manifests/sandiego/*.request.json, *.documents.jsonl
       data/raw/sandiego/{request_id}/{document_id}.{msg|eml|pdf}
Writes data/emails/sandiego.requests.jsonl   (request_id, request_text as plain text)
       data/emails/sandiego.emails.jsonl     (one row per email; full headers + body text)

The committed JSONL is the dataset of record; raw files are re-fetchable from the
manifests. Attachments are recorded by name only (SPEC §7: phase 1 excludes them).
"""
import email
import email.policy
import hashlib
import html
import json
import pathlib
import re
import sys

import extract_msg
from pypdf import PdfReader

MANIFEST_DIR = pathlib.Path("data/manifests")
RAW_DIR = pathlib.Path("data/raw")
OUT_DIR = pathlib.Path("data/emails")


def strip_html(s):
    s = re.sub(r"<(br|/p|/div)\s*/?>", "\n", s or "", flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    return html.unescape(s).replace("\xa0", " ").strip()


def norm_ws(s):
    s = (s or "").replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"[ \t]+\n", "\n", s)
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def parse_msg(path):
    m = extract_msg.openMsg(str(path))
    try:
        return {
            "subject": m.subject, "from": m.sender, "to": m.to, "cc": m.cc,
            "date": m.date.isoformat() if m.date else None,
            "message_id": m.messageId, "in_reply_to": m.inReplyTo,
            "attachments": [a.longFilename or a.shortFilename or "" for a in m.attachments],
            "body": norm_ws(m.body or (strip_html(m.htmlBody.decode("utf-8", "replace"))
                                       if m.htmlBody else "")),
        }
    finally:
        m.close()


def parse_eml(path):
    with path.open("rb") as f:
        msg = email.message_from_binary_file(f, policy=email.policy.default)
    body = ""
    part = msg.get_body(preferencelist=("plain", "html"))
    if part is not None:
        text = part.get_content()
        body = text if part.get_content_type() == "text/plain" else strip_html(text)
    d = msg.get("Date")
    try:
        d = email.utils.parsedate_to_datetime(d).isoformat() if d else None
    except Exception:
        pass
    return {
        "subject": msg.get("Subject"), "from": msg.get("From"), "to": msg.get("To"),
        "cc": msg.get("Cc"), "date": d, "message_id": msg.get("Message-ID"),
        "in_reply_to": msg.get("In-Reply-To"),
        "attachments": [p.get_filename() for p in msg.iter_attachments() if p.get_filename()],
        "body": norm_ws(body),
    }


HDR = re.compile(r"^(From|Sent|To|Cc|Subject):\s*(.*)$", re.M)


def parse_pdf(path):
    """25-5982-style productions: one printed email per native-text PDF."""
    text = "\n".join((p.extract_text() or "") for p in PdfReader(str(path)).pages)
    hdr = {}
    for k, v in HDR.findall(text[:3000]):
        hdr.setdefault(k.lower(), v.strip())
    return {
        "subject": hdr.get("subject"), "from": hdr.get("from"), "to": hdr.get("to"),
        "cc": hdr.get("cc"), "date": hdr.get("sent"), "message_id": None, "in_reply_to": None,
        "attachments": [], "body": norm_ws(text),
    }


PARSERS = {"msg": parse_msg, "eml": parse_eml, "pdf": parse_pdf}


def main(source):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    mdir = MANIFEST_DIR / source
    with (OUT_DIR / f"{source}.requests.jsonl").open("w") as f:
        for p in sorted(mdir.glob("*.request.json")):
            d = json.load(p.open())
            f.write(json.dumps({
                "request_id": d["pretty_id"], "source": source,
                "request_date": d.get("request_date"),
                "departments": d.get("department_names"),
                "request_text": norm_ws(strip_html(d["request_text"])),
                "url": f"https://pra.sandiegocounty.gov/requests/{d['pretty_id']}",
            }) + "\n")

    n = fail = 0
    stats = {}
    with (OUT_DIR / f"{source}.emails.jsonl").open("w") as f:
        for mp in sorted(mdir.glob("*.documents.jsonl")):
            for line in mp.open():
                r = json.loads(line)
                ext = r["file_extension"]
                path = RAW_DIR / source / r["request_id"] / f"{r['document_id']}.{ext}"
                if ext not in PARSERS or not path.exists():
                    continue
                try:
                    e = PARSERS[ext](path)
                except Exception as ex:
                    print(f"  FAIL {path}: {type(ex).__name__}: {ex}", file=sys.stderr)
                    fail += 1
                    continue
                row = {
                    "id": f"{source}:{r['request_id']}:{r['document_id']}",
                    "source": source, "request_id": r["request_id"],
                    "document_id": r["document_id"], "format": ext,
                    "title": r["title"], "url": r["download_url"],
                    **e,
                    "body_chars": len(e["body"]),
                    "body_sha256": hashlib.sha256(e["body"].encode()).hexdigest(),
                }
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                n += 1
                stats[r["request_id"]] = stats.get(r["request_id"], 0) + 1
    print(f"{source}: {n} emails written, {fail} failed; per request: {stats}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "sandiego")
