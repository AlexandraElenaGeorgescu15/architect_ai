"""
Smoke E2E test for Architect.AI
Runs without AI keys; validates DB, auth, metrics, jobs, publish, and filesystem outputs.
"""

import os
import sys
import time
from pathlib import Path

PASS = "OK"
FAIL = "FAIL"


def main():
    base = Path(__file__).resolve().parent.parent
    if str(base) not in sys.path:
        sys.path.insert(0, str(base))
    outputs = base / "outputs"
    inputs = base / "inputs"
    (outputs / "visualizations").mkdir(parents=True, exist_ok=True)
    (outputs / "documentation").mkdir(parents=True, exist_ok=True)
    (outputs / "prototypes").mkdir(parents=True, exist_ok=True)
    (outputs / "workflows").mkdir(parents=True, exist_ok=True)
    inputs.mkdir(parents=True, exist_ok=True)

    results = []

    # 1) DB init and auth flows
    try:
        from db.database import init_db, get_session
        from db.models import User
        from components import auth_db as adb
        init_db()
        # create admin (first user)
        adb.create_user("admin", "admin123", "Admin")
        assert adb.authenticate("admin", "admin123")
        # change password
        assert adb.change_password("admin", "admin123", "newpass") is None
        assert adb.authenticate("admin", "newpass")
        # reset
        token = adb.create_reset_token("admin")
        assert token is not None
        assert adb.reset_password(token, "resetpass") is None
        assert adb.authenticate("admin", "resetpass")
        results.append(("DB/Auth", True))
    except Exception as e:
        results.append((f"DB/Auth {e}", False))

    # 2) Inputs & sample artifacts
    try:
        (inputs / "meeting_notes.md").write_text("""
# Feature: Inventory ERD

We need tables: Users, Products, Orders

""".strip(), encoding="utf-8")
        (outputs / "visualizations" / "sample_diagram.mmd").write_text("""
graph TD
    A[App] --> B[API]
    B --> C[DB]
""".strip(), encoding="utf-8")
        (outputs / "documentation" / "design.md").write_text("# Design Doc\n\nSample.", encoding="utf-8")
        (outputs / "prototypes" / "visual_prototype.html").write_text("<html><body>Prototype</body></html>", encoding="utf-8")
        (outputs / "workflows" / "workflows.md").write_text("# Workflows\n\nSample.", encoding="utf-8")
        results.append(("Files", True))
    except Exception as e:
        results.append((f"Files {e}", False))

    # 3) Metrics
    try:
        from components.metrics_dashboard import MetricsTracker
        mt = MetricsTracker()
        mt.record_generation("erd", cost=0.01, time_saved=0.1)
        mt.record_cache_hit()
        assert (outputs / "metrics.json").exists()
        results.append(("Metrics", True))
    except Exception as e:
        results.append((f"Metrics {e}", False))

    # 4) Publish token store
    try:
        from db.database import get_session
        from db.models import SecretToken
        with get_session() as s:
            s.add(SecretToken(service="confluence", username="u", token="t"))
        results.append(("Publish tokens", True))
    except Exception as e:
        results.append((f"Publish {e}", False))

    # 5) Jobs queue
    try:
        from components.jobs import enqueue_job

        def write_file_job(path: str, content: str, job_id: int = 0):  # job_id injected
            p = Path(path)
            p.write_text(content, encoding="utf-8")
            return str(p)

        target = outputs / "job_output.txt"
        jid = enqueue_job("write_file", write_file_job, path=str(target), content="hello")
        # wait briefly
        time.sleep(1.0)
        assert target.exists()
        results.append(("Jobs", True))
    except Exception as e:
        results.append((f"Jobs {e}", False))

    # Summary
    ok = all(s for _, s in results)
    for name, s in results:
        print(f"{PASS if s else FAIL} {name}")
    print("\nOverall:", PASS if ok else FAIL)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())


