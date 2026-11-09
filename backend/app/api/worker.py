import json
import sys

from ..core.audit import append
from ..core.storage import db
from ..pipeline.run import analyze, render


def job(case_id):
    with db() as conn:
        records = conn.execute("SELECT * FROM documents WHERE case_id=? ORDER BY rowid", (case_id,)).fetchall()

    def report(step):
        with db(write=True) as conn:
            row = conn.execute("SELECT progress FROM cases WHERE id=?", (case_id,)).fetchone()
            progress = json.loads(row["progress"]) + [step]
            conn.execute("UPDATE cases SET progress=? WHERE id=?", (json.dumps(progress), case_id))
            append(conn, case_id, "pipeline", step)

    result = analyze(records, report)
    with db(write=True) as conn:
        for item in result["findings"]:
            append(conn, case_id, "finding", {key: item[key] for key in ("id", "detector", "status", "document_id", "page")})
        append(conn, case_id, "analysis_complete", {"concern": result["summary"]["concern"]})
        conn.execute("UPDATE cases SET state='ready',result=? WHERE id=?", (json.dumps(result), case_id))


if __name__ == "__main__":
    if sys.argv[1] == "render":
        with db() as conn:
            row = conn.execute("SELECT * FROM documents WHERE id=?", (sys.argv[2],)).fetchone()
        sys.stdout.buffer.write(render(row["original"], row["mime"], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]))
    else:
        job(sys.argv[1])
