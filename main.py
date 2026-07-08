import os
import io
import base64
import hashlib
import hmac
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
import pyotp
import qrcode


app = FastAPI(title="cassellas-api", version="0.1.0")
API_NAME = os.getenv("API_NAME", "cassellas-api")
API_PREFIX = f"/API/{API_NAME}"
USERS_FILE = os.getenv("AUTH_USERS_FILE", "users.txt")
MFA_FILE = os.getenv("AUTH_MFA_FILE", "mfa_secrets.txt")
MFA_ISSUER = os.getenv("AUTH_MFA_ISSUER", "cassellas-api")


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginMFARequest(BaseModel):
    username: str
    password: str
    otp: str


class MFASetupRequest(BaseModel):
    username: str
    password: str


class MFADisableRequest(BaseModel):
    username: str
    password: str
    otp: str


def _load_users(file_path: str) -> dict[str, str]:
    users: dict[str, str] = {}

    if not os.path.exists(file_path):
        return users

    with open(file_path, "r", encoding="utf-8") as users_file:
        for raw_line in users_file:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split(":", 1)
            if len(parts) != 2:
                continue

            username, password_hash = parts[0].strip(), parts[1].strip().lower()
            if username and password_hash:
                users[username] = password_hash

    return users


def _load_mfa_secrets(file_path: str) -> dict[str, str]:
    secrets: dict[str, str] = {}

    if not os.path.exists(file_path):
        return secrets

    with open(file_path, "r", encoding="utf-8") as secrets_file:
        for raw_line in secrets_file:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split(":", 1)
            if len(parts) != 2:
                continue

            username, secret = parts[0].strip(), parts[1].strip().replace(" ", "")
            if username and secret:
                secrets[username] = secret

    return secrets


def _save_mfa_secret(username: str, secret: str, file_path: str) -> None:
    secrets = _load_mfa_secrets(file_path)
    secrets[username] = secret

    with open(file_path, "w", encoding="utf-8") as secrets_file:
        secrets_file.write("# Formato: usuario:segredo_base32\n")
        for current_username in sorted(secrets):
            secrets_file.write(f"{current_username}:{secrets[current_username]}\n")


def _remove_mfa_secret(username: str, file_path: str) -> None:
    secrets = _load_mfa_secrets(file_path)
    secrets.pop(username, None)

    with open(file_path, "w", encoding="utf-8") as secrets_file:
        secrets_file.write("# Formato: usuario:segredo_base32\n")
        for current_username in sorted(secrets):
            secrets_file.write(f"{current_username}:{secrets[current_username]}\n")


def _is_valid_user(username: str, plain_password: str) -> bool:
    users = _load_users(USERS_FILE)
    expected_hash = users.get(username)
    if not expected_hash:
        return False

    provided_hash = hashlib.sha512(plain_password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(provided_hash, expected_hash)


def _authenticate(login: LoginRequest) -> dict[str, str | bool]:
    if not _is_valid_user(login.username, login.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    secrets = _load_mfa_secrets(MFA_FILE)
    if login.username in secrets:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="MFA required. Use /auth/login/mfa",
        )

    return {
        "authenticated": True,
        "username": login.username,
    }


def _get_or_create_mfa_secret(username: str) -> str:
    secrets = _load_mfa_secrets(MFA_FILE)
    existing_secret = secrets.get(username)
    if existing_secret:
        return existing_secret

    new_secret = pyotp.random_base32()
    _save_mfa_secret(username, new_secret, MFA_FILE)
    return new_secret


def _authenticate_mfa(login: LoginMFARequest) -> dict[str, str | bool]:
    if not _is_valid_user(login.username, login.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    secrets = _load_mfa_secrets(MFA_FILE)
    user_secret = secrets.get(login.username)
    if not user_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="MFA is not configured for this user",
        )

    totp = pyotp.TOTP(user_secret)
    if not totp.verify(login.otp.strip(), valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA code",
        )

    return {
        "authenticated": True,
        "mfa": True,
        "username": login.username,
    }


def _setup_mfa(setup: MFASetupRequest) -> dict[str, str | bool]:
    if not _is_valid_user(setup.username, setup.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    secret = _get_or_create_mfa_secret(setup.username)
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=setup.username,
        issuer_name=MFA_ISSUER,
    )

    qr_image = qrcode.make(provisioning_uri)
    buffer = io.BytesIO()
    qr_image.save(buffer, format="PNG")
    qr_code_png_base64 = base64.b64encode(buffer.getvalue()).decode("ascii")

    return {
        "mfa_configured": True,
        "username": setup.username,
        "issuer": MFA_ISSUER,
        "secret": secret,
        "otpauth_uri": provisioning_uri,
        "qr_code_png_base64": qr_code_png_base64,
    }


def _disable_mfa(disable: MFADisableRequest) -> dict[str, str | bool]:
    if not _is_valid_user(disable.username, disable.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    secrets = _load_mfa_secrets(MFA_FILE)
    user_secret = secrets.get(disable.username)
    if not user_secret:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MFA is not configured for this user",
        )

    totp = pyotp.TOTP(user_secret)
    if not totp.verify(disable.otp.strip(), valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA code",
        )

    _remove_mfa_secret(disable.username, MFA_FILE)

    return {
        "mfa_disabled": True,
        "username": disable.username,
    }


@app.get("/")
async def read_root() -> dict[str, str]:
    return {"service": "cassellas-api", "status": "ok"}


@app.get("/healthz")
async def healthcheck() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/now")
async def get_current_datetime() -> dict[str, str]:
    now = datetime.now(timezone.utc)
    return {
        "data_atual": now.isoformat(),
        "timezone": "UTC",
    }


@app.get(f"{API_PREFIX}/now")
async def get_current_datetime_with_prefix() -> dict[str, str]:
    now = datetime.now(timezone.utc)
    return {
        "api": API_NAME,
        "data_atual": now.isoformat(),
        "timezone": "UTC",
    }


@app.post("/auth/login")
async def login(login: LoginRequest) -> dict[str, str | bool]:
    return _authenticate(login)


@app.post(f"{API_PREFIX}/auth/login")
async def login_with_prefix(login: LoginRequest) -> dict[str, str | bool]:
    return _authenticate(login)


@app.post("/auth/mfa/setup")
async def mfa_setup(setup: MFASetupRequest) -> dict[str, str | bool]:
    return _setup_mfa(setup)


@app.post(f"{API_PREFIX}/auth/mfa/setup")
async def mfa_setup_with_prefix(setup: MFASetupRequest) -> dict[str, str | bool]:
    return _setup_mfa(setup)


@app.post("/auth/login/mfa")
async def login_mfa(login: LoginMFARequest) -> dict[str, str | bool]:
    return _authenticate_mfa(login)


@app.post(f"{API_PREFIX}/auth/login/mfa")
async def login_mfa_with_prefix(login: LoginMFARequest) -> dict[str, str | bool]:
    return _authenticate_mfa(login)


@app.post("/auth/mfa/disable")
async def mfa_disable(disable: MFADisableRequest) -> dict[str, str | bool]:
    return _disable_mfa(disable)


@app.post(f"{API_PREFIX}/auth/mfa/disable")
async def mfa_disable_with_prefix(disable: MFADisableRequest) -> dict[str, str | bool]:
    return _disable_mfa(disable)
