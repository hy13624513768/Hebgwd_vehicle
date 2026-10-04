"""在临时 SQLite 中验证完整启动和登录，不访问项目 .env 中的数据库。"""
import os
from pathlib import Path
from tempfile import TemporaryDirectory


def main() -> None:
    with TemporaryDirectory(prefix="vehicle-smoke-") as test_dir:
        os.environ.update(
            DATABASE_URL=f"sqlite:///{(Path(test_dir) / 'smoke.db').as_posix()}",
            ENVIRONMENT="test",
            DEMO_SEEDING_ENABLED="false",
            BOOTSTRAP_ADMIN_USERNAME="smoke_admin",
            BOOTSTRAP_ADMIN_PASSWORD="SmokeOnly123!",
            JWT_SECRET="isolated-smoke-test-secret-not-for-deployment",
            UPLOAD_DIR=str(Path(test_dir) / "uploads"),
        )
        run_checks()
    print("smoke_ok (isolated temporary database)")


def run_checks() -> None:
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 200

        start = client.post("/api/v1/auth/slider/start")
        assert start.status_code == 200
        session_id = start.json()["session_id"]

        done = client.post("/api/v1/auth/slider/complete", json={"session_id": session_id})
        assert done.status_code == 204

        login = client.post(
            "/api/v1/auth/login",
            json={"username": "smoke_admin", "password": "SmokeOnly123!", "slider_session_id": session_id},
        )
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]

        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200, me.text

if __name__ == "__main__":
    main()
