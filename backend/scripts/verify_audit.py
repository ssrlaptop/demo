"""Verify the append-only audit hash chain (NN3).

Usage:  python -m scripts.verify_audit
Exit code 0 = chain fully verified; non-zero = tampering detected.
"""

from __future__ import annotations

import sys

from app.audit.hash_chain import verify_chain
from app.audit.writer import MongoAuditWriter
from app.db.mongo import get_db


def main() -> int:
    events = MongoAuditWriter(get_db()).list_all(limit=100_000)
    ordered = list(reversed(events))  # newest-first -> ascending
    verdict = verify_chain(ordered)
    if verdict.verified:
        print(f"OK — audit chain verified ({verdict.checked} events)")
        return 0
    print(
        f"FAIL — chain broken after {verdict.checked} events "
        f"(first bad seq={verdict.first_bad_seq})",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())