from fastapi.testclient import TestClient

from app.main import app


def main() -> None:
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200

        start = client.post("/api/v1/auth/slider/start")
        assert start.status_code == 200
        session_id = start.json()["session_id"]

        done = client.post("/api/v1/auth/slider/complete", json={"session_id": session_id})
        assert done.status_code == 204

        login = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "Admin123!@#", "slider_session_id": session_id},
        )
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]

        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200, me.text

    print("smoke_ok")


if __name__ == "__main__":
    main()
