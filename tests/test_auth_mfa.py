import hashlib
from pathlib import Path
import sys

import pyotp
from fastapi.testclient import TestClient
import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import main


def _sha512_hex(value: str) -> str:
    return hashlib.sha512(value.encode("utf-8")).hexdigest()


@pytest.fixture
def client(tmp_path, monkeypatch):
    users_file = tmp_path / "users.txt"
    mfa_file = tmp_path / "mfa_secrets.txt"

    users_file.write_text(f"admin:{_sha512_hex('admin123')}\n", encoding="utf-8")
    mfa_file.write_text("# Formato: usuario:segredo_base32\n", encoding="utf-8")

    monkeypatch.setattr(main, "USERS_FILE", str(users_file))
    monkeypatch.setattr(main, "MFA_FILE", str(mfa_file))
    monkeypatch.setattr(main, "MFA_ISSUER", "cassellas-api-test")

    return TestClient(main.app)


def test_mfa_setup_and_login_flow(client: TestClient):
    setup_resp = client.post(
        "/auth/mfa/setup",
        json={"username": "admin", "password": "admin123"},
    )
    assert setup_resp.status_code == 200

    setup_payload = setup_resp.json()
    assert setup_payload["mfa_configured"] is True
    assert "secret" in setup_payload
    assert "qr_code_png_base64" in setup_payload

    blocked_simple_login = client.post(
        "/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert blocked_simple_login.status_code == 403

    otp_code = pyotp.TOTP(setup_payload["secret"]).now()
    mfa_login_resp = client.post(
        "/auth/login/mfa",
        json={"username": "admin", "password": "admin123", "otp": otp_code},
    )

    assert mfa_login_resp.status_code == 200
    assert mfa_login_resp.json()["mfa"] is True


def test_login_mfa_with_invalid_code_returns_401(client: TestClient):
    setup_resp = client.post(
        "/auth/mfa/setup",
        json={"username": "admin", "password": "admin123"},
    )
    assert setup_resp.status_code == 200

    login_resp = client.post(
        "/auth/login/mfa",
        json={"username": "admin", "password": "admin123", "otp": "000000"},
    )

    assert login_resp.status_code == 401


def test_disable_mfa_restores_simple_login(client: TestClient):
    setup_resp = client.post(
        "/auth/mfa/setup",
        json={"username": "admin", "password": "admin123"},
    )
    assert setup_resp.status_code == 200

    secret = setup_resp.json()["secret"]
    disable_otp_code = pyotp.TOTP(secret).now()

    disable_resp = client.post(
        "/auth/mfa/disable",
        json={"username": "admin", "password": "admin123", "otp": disable_otp_code},
    )
    assert disable_resp.status_code == 200
    assert disable_resp.json()["mfa_disabled"] is True

    simple_login_resp = client.post(
        "/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert simple_login_resp.status_code == 200
