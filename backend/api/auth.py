from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from ..db import fetch_one, execute
from ..config import JWT_SECRET, JWT_ALGORITHM, JWT_EXP_SECONDS
import hashlib
import secrets
import time
import jwt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter()
security = HTTPBearer()


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


def _create_jwt(payload: dict) -> str:
    now = int(time.time())
    data = {"iat": now, "exp": now + JWT_EXP_SECONDS, **payload}
    token = jwt.encode(data, JWT_SECRET, algorithm=JWT_ALGORITHM)
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username = payload.get("username")
        token_session = payload.get("session")
        if not username or not token_session:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        try:
            row = await fetch_one("cms", "SELECT session FROM account WHERE username = %s", (username,))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"DB error validating session: {e}")

        if not row:
            raise HTTPException(status_code=401, detail="Invalid session")

        db_session = row.get("session")
        db_session_hex = None
        if db_session is not None:
            try:
                db_session_hex = db_session.hex()
            except Exception:
                db_session_hex = str(db_session)

        if db_session_hex != token_session:
            raise HTTPException(status_code=401, detail="Session mismatch or expired")

        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def _compute_verifier(username: str, password: str):
    g = 7
    N = int("894B645E89E1535BBDAD5B8B290650530801B18EBFBF5E8FAB3C82872A3E9BB7", 16)
    h1_input = f"{username.upper()}:{password.upper()}".encode("utf-8")
    h1 = hashlib.sha1(h1_input).digest()
    salt = secrets.token_bytes(32)
    h2 = hashlib.sha1(salt + h1).digest()
    h2_int = int.from_bytes(h2, byteorder="little")
    v_int = pow(g, h2_int, N)
    v_bytes = v_int.to_bytes(32, byteorder="little")
    return salt, v_bytes


@router.post("/register")
async def register(req: RegisterRequest):
    username = req.username
    password = req.password
    email = req.email or ""

    if not username or len(username) > 20:
        raise HTTPException(status_code=400, detail="Invalid username (required, max 20 chars)")
    if not password or len(password) < 4:
        raise HTTPException(status_code=400, detail="Password too short (min 4 chars)")

    try:
        existing = await fetch_one("auth", "SELECT id FROM account WHERE username = %s", (username,))
        if existing:
            raise HTTPException(status_code=400, detail="Account already exists")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error checking account: {e}")

    try:
        salt, verifier = _compute_verifier(username, password)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute verifier: {e}")

    try:
        auth_q = "INSERT INTO account (username, verifier, salt, email) VALUES (%s, %s, %s, %s)"
        await execute("auth", auth_q, (username, verifier, salt, email))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create auth account: {e}")

    try:
        await execute("cms", "INSERT INTO account (username, credits, vote_points, last_login, session) VALUES (%s, %s, %s, NULL, NULL)", (username, 0, 0))
    except Exception as e:
        try:
            await execute("auth", "DELETE FROM account WHERE username = %s", (username,))
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Failed to create cms account (rolled back auth): {e}")

    return {"ok": True, "username": username}


@router.post("/login")
async def login(req: LoginRequest):
    username = req.username
    password = req.password

    if not username or not password:
        raise HTTPException(status_code=400, detail="username and password required")

    try:
        row = await fetch_one("auth", "SELECT id, username, verifier, salt FROM account WHERE username = %s", (username,))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")

    if not row:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    stored_verifier = row.get("verifier")
    stored_salt = row.get("salt")

    if stored_verifier is None or stored_salt is None:
        raise HTTPException(status_code=500, detail="Account missing verifier/salt")

    try:
        h1_input = f"{username.upper()}:{password.upper()}".encode("utf-8")
        h1 = hashlib.sha1(h1_input).digest()
        h2 = hashlib.sha1(stored_salt + h1).digest()
        h2_int = int.from_bytes(h2, byteorder="little")
        g = 7
        N = int("894B645E89E1535BBDAD5B8B290650530801B18EBFBF5E8FAB3C82872A3E9BB7", 16)
        v_int = pow(g, h2_int, N)
        v_bytes = v_int.to_bytes(32, byteorder="little")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute verifier: {e}")

    if v_bytes != stored_verifier:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    session_key = secrets.token_bytes(40)
    try:
        await execute("cms", "UPDATE account SET session = %s, last_login = CURRENT_TIMESTAMP WHERE username = %s", (session_key, username))
    except Exception:
        pass

    session_hex = session_key.hex()
    token = _create_jwt({"sub": row.get("id"), "username": username, "session": session_hex})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout")
async def logout(user: dict = Depends(get_current_user)):
    username = user.get("username")
    if not username:
        raise HTTPException(status_code=400, detail="Invalid token payload")

    try:
        await execute("cms", "UPDATE account SET session = NULL WHERE username = %s", (username,))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error clearing session: {e}")

    return {"ok": True}
