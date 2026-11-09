from datetime import datetime, timezone
from .hashing import canonical, sha256

GENESIS = "0" * 64


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def append(conn, case_id, action, payload):
    row = conn.execute("SELECT hash FROM audit WHERE case_id=? ORDER BY seq DESC LIMIT 1", (case_id,)).fetchone()
    previous = row["hash"] if row else GENESIS
    envelope = canonical({"case": case_id, "action": action, "timestamp": now(), "details": payload})
    digest = sha256((previous + envelope).encode())
    conn.execute("INSERT INTO audit(case_id,previous,payload,hash) VALUES(?,?,?,?)", (case_id, previous, envelope, digest))
    return digest


def verify(rows):
    previous = GENESIS
    for row in rows:
        actual = sha256((previous + row["payload"]).encode())
        if previous != row["previous"] or actual != row["hash"]:
            return {"valid": False, "failed_at": row["seq"], "head": previous}
        previous = actual
    return {"valid": True, "count": len(rows), "head": previous}
