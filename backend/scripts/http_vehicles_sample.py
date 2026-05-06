"""通过 TestClient 调用 GET /api/v1/vehicles，检查 JSON 是否含 registered_at。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app.core import deps  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User  # noqa: E402


def main() -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "admin").first()
        if not user:
            raise SystemExit("无 admin 用户")
        app.dependency_overrides[deps.get_current_user] = lambda: user
        client = TestClient(app)
        r = client.get("/api/v1/vehicles", params={"limit": 3})
        r.raise_for_status()
        data = r.json()
        print("count", len(data))
        if data:
            keys = sorted(data[0].keys())
            print("first_keys_has_registered_at", "registered_at" in data[0])
            print("first_registered_at", data[0].get("registered_at"))
            print("all_keys", keys)
    finally:
        db.close()
        app.dependency_overrides.clear()


if __name__ == "__main__":
    main()
