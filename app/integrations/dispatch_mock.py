"""Mock dispatch — writes the CSV to disk and returns a fake submission ref.

Stands in for the real email-to-Evri path (no SMTP, no live mailboxes).
"""

from __future__ import annotations

import hashlib
import os

DISPATCH_DIR = os.getenv("BATCH_DIR", "data/batches")


def dispatch(csv_bytes: bytes, channel_name: str) -> dict:
    os.makedirs(DISPATCH_DIR, exist_ok=True)
    sha = hashlib.sha256(csv_bytes).hexdigest()
    path = os.path.join(DISPATCH_DIR, f"{sha[:16]}.csv")
    with open(path, "wb") as f:
        f.write(csv_bytes)
    # Deterministic fake reference in Evri's NNNNNN-NNNNNN shape.
    ref = f"{int(sha[:6], 16) % 1000000:06d}-{int(sha[6:12], 16) % 1000000:06d}"
    return {"submission_ref": ref, "file_path": path, "file_sha256": sha}
