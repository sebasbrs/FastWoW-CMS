from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from ..db import fetch_one, execute
from ..config import (
    JWT_SECRET, JWT_ALGORITHM, JWT_EXP_SECONDS,
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_STARTTLS, EMAIL_FROM,
    PASSWORD_RESET_TOKEN_EXP_MIN, EMAIL_VERIFICATION_TOKEN_EXP_MIN
)
import hashlib
import secrets
import time
import jwt
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta
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


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ChangeEmailRequest(BaseModel):
    new_email: str


class PasswordRecoveryRequest(BaseModel):
    username: str


class PasswordResetConfirmRequest(BaseModel):
    username: str
    token: str
    new_password: str


class EmailVerificationRequest(BaseModel):
    username: str


class EmailVerificationConfirmRequest(BaseModel):
    username: str
    token: str


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

        # enrich with role from cms.account
        try:
            role_row = await fetch_one("cms", "SELECT role FROM account WHERE username = %s", (username,))
            if role_row and role_row.get("role") is not None:
                payload["role"] = int(role_row.get("role"))
            else:
                payload["role"] = 1
        except Exception:
            payload["role"] = 1
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.get('/me')
async def me(user: dict = Depends(get_current_user)):
    """Devuelve datos básicos del usuario autenticado para el frontend.
    Incluye username, credits, vote_points y gravatar.
    """
    username = user.get('username')
    if not username:
        raise HTTPException(status_code=400, detail='Invalid token payload')
    try:
        acct = await fetch_one('cms', 'SELECT credits, vote_points FROM account WHERE username = %s', (username,))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error leyendo cuenta cms: {e}')
    try:
        auth_acct = await fetch_one('auth', 'SELECT email FROM account WHERE username = %s', (username,))
    except Exception:
        auth_acct = None
    email = (auth_acct.get('email') if auth_acct else '') or ''
    grav_hash = hashlib.md5(email.strip().lower().encode('utf-8')).hexdigest()
    gravatar_url = f"https://www.gravatar.com/avatar/{grav_hash}?d=identicon&s=96"
    return {
        'username': username,
        'credits': int((acct or {}).get('credits') or 0),
        'vote_points': int((acct or {}).get('vote_points') or 0),
        'gravatar': gravatar_url
    }


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
        # role default 1 (logged)
        await execute("cms", "INSERT INTO account (username, credits, vote_points, last_login, session, role, email_verified) VALUES (%s, %s, %s, NULL, NULL, %s, 0)", (username, 0, 0, 1))
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
    # include role in JWT for faster checks (still validated against DB each request via get_current_user)
    try:
        role_row = await fetch_one("cms", "SELECT role FROM account WHERE username = %s", (username,))
        user_role = int(role_row.get("role")) if role_row and role_row.get("role") is not None else 1
    except Exception:
        user_role = 1
    token = _create_jwt({"sub": row.get("id"), "username": username, "session": session_hex, "role": user_role})
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


def require_role(min_role: int):
    async def _dep(user: dict = Depends(get_current_user)):
        role = int(user.get("role", 1))
        if role < min_role:
            raise HTTPException(status_code=403, detail="Permisos insuficientes")
        return user
    return _dep


require_logged = require_role(1)
require_admin = require_role(2)


def _send_email(subject: str, to_email: str, body: str):
    if not to_email:
        raise HTTPException(status_code=400, detail="Cuenta sin email registrado")
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = to_email
    msg.set_content(body)
    try:
        with smtplib.SMTP(host=SMTP_HOST, port=SMTP_PORT, timeout=10) as smtp:
            if SMTP_STARTTLS:
                try:
                    smtp.starttls()
                except Exception:
                    pass
            if SMTP_USER:
                smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.send_message(msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error enviando email: {e}")


@router.post('/change_password')
async def change_password(req: ChangePasswordRequest, user: dict = Depends(get_current_user)):
    username = user.get('username')
    # validar current password usando misma lógica SRP (recalcular verificador y comparar)
    if len(req.new_password) < 4:
        raise HTTPException(status_code=400, detail='Nueva contraseña demasiado corta')
    try:
        row = await fetch_one('auth', 'SELECT verifier, salt FROM account WHERE username = %s', (username,))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error leyendo cuenta: {e}')
    if not row:
        raise HTTPException(status_code=400, detail='Cuenta inexistente')
    stored_verifier = row.get('verifier')
    stored_salt = row.get('salt')
    # verificar password actual
    try:
        h1_input = f"{username.upper()}:{req.current_password.upper()}".encode('utf-8')
        h1 = hashlib.sha1(h1_input).digest()
        h2 = hashlib.sha1(stored_salt + h1).digest()
        h2_int = int.from_bytes(h2, byteorder='little')
        g = 7
        N = int("894B645E89E1535BBDAD5B8B290650530801B18EBFBF5E8FAB3C82872A3E9BB7", 16)
        v_int = pow(g, h2_int, N)
        v_bytes = v_int.to_bytes(32, byteorder='little')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error validando contraseña: {e}')
    if v_bytes != stored_verifier:
        raise HTTPException(status_code=403, detail='Contraseña actual incorrecta')
    # generar nuevo salt/verifier
    try:
        new_salt, new_verifier = _compute_verifier(username, req.new_password)
        await execute('auth', 'UPDATE account SET verifier = %s, salt = %s WHERE username = %s', (new_verifier, new_salt, username))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error actualizando contraseña: {e}')
    return {'ok': True}


@router.post('/change_email')
async def change_email(req: ChangeEmailRequest, user: dict = Depends(get_current_user)):
    username = user.get('username')
    if not req.new_email or '@' not in req.new_email:
        raise HTTPException(status_code=400, detail='Email inválido')
    try:
        await execute('auth', 'UPDATE account SET email = %s WHERE username = %s', (req.new_email.strip(), username))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error actualizando email: {e}')
    return {'ok': True}


@router.post('/password_recovery/request')
async def password_recovery_request(req: PasswordRecoveryRequest):
    username = req.username
    try:
        row = await fetch_one('auth', 'SELECT email FROM account WHERE username = %s', (username,))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error buscando cuenta: {e}')
    # No revelar si existe o no: comportamiento silencioso
    if not row or not row.get('email'):
        return {'ok': True}
    # verificar si email está verificado en cms.account (nuevo campo requerido)
    try:
        ver_row = await fetch_one('cms', 'SELECT email_verified FROM account WHERE username = %s', (username,))
    except Exception:
        ver_row = None
    if not ver_row or int(ver_row.get('email_verified') or 0) != 1:
        # si no verificado, enviamos token de verificación en lugar de recovery
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(minutes=EMAIL_VERIFICATION_TOKEN_EXP_MIN)
        try:
            await execute('cms', 'INSERT INTO email_verification_tokens (username, token, expires_at) VALUES (%s,%s,%s)', (username, token, expires_at.strftime('%Y-%m-%d %H:%M:%S')))
        except Exception:
            return {'ok': True}
        body = (
            f"Hola {username},\n\nNecesitas verificar tu email antes de recuperar la contraseña.\n"
            f"Token de verificación: {token}\nVálido por {EMAIL_VERIFICATION_TOKEN_EXP_MIN} minutos.\n\n"
            "Si no solicitaste esto, ignora este mensaje."
        )
        _send_email('Verificación de email', row.get('email'), body)
        return {'ok': True}
    email = row.get('email')
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(minutes=PASSWORD_RESET_TOKEN_EXP_MIN)
    try:
        await execute('cms', 'INSERT INTO password_reset_tokens (username, token, expires_at) VALUES (%s,%s,%s)', (username, token, expires_at.strftime('%Y-%m-%d %H:%M:%S')))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error generando token: {e}')
    body = f"Hola {username},\n\nHemos recibido una solicitud para restablecer tu contraseña.\n\nToken (OTP): {token}\nVálido por {PASSWORD_RESET_TOKEN_EXP_MIN} minutos.\n\nSi no solicitaste esto, ignora este mensaje."
    _send_email('Recuperación de contraseña', email, body)
    return {'ok': True}


@router.post('/email_verification/request')
async def email_verification_request(req: EmailVerificationRequest):
    username = req.username
    try:
        row = await fetch_one('auth', 'SELECT email FROM account WHERE username = %s', (username,))
    except Exception:
        return {'ok': True}
    if not row or not row.get('email'):
        return {'ok': True}
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(minutes=EMAIL_VERIFICATION_TOKEN_EXP_MIN)
    try:
        await execute('cms', 'INSERT INTO email_verification_tokens (username, token, expires_at) VALUES (%s,%s,%s)', (username, token, expires_at.strftime('%Y-%m-%d %H:%M:%S')))
    except Exception:
        return {'ok': True}
    body = (
        f"Hola {username},\n\nUsa este token para verificar tu email: {token}\n"
        f"Válido por {EMAIL_VERIFICATION_TOKEN_EXP_MIN} minutos.\n"
        "Si no solicitaste esto, ignora este mensaje."
    )
    _send_email('Verificación de email', row.get('email'), body)
    return {'ok': True}


@router.post('/email_verification/confirm')
async def email_verification_confirm(req: EmailVerificationConfirmRequest):
    try:
        token_row = await fetch_one('cms', 'SELECT id, username, token, expires_at, consumed FROM email_verification_tokens WHERE token = %s AND username = %s', (req.token, req.username))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error validando token: {e}')
    if not token_row:
        raise HTTPException(status_code=400, detail='Token inválido')
    if int(token_row.get('consumed') or 0) == 1:
        raise HTTPException(status_code=400, detail='Token ya usado')
    expires_at = token_row.get('expires_at')
    try:
        if isinstance(expires_at, str):
            expires_dt = datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S')
        else:
            expires_dt = expires_at
    except Exception:
        raise HTTPException(status_code=500, detail='Formato de expiración inválido en token')
    if datetime.utcnow() > expires_dt:
        raise HTTPException(status_code=400, detail='Token expirado')
    # Marcar verificado
    try:
        await execute('cms', 'UPDATE account SET email_verified = 1 WHERE username = %s', (req.username,))
        await execute('cms', 'UPDATE email_verification_tokens SET consumed = 1 WHERE id = %s', (token_row.get('id'),))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error aplicando verificación: {e}')
    return {'ok': True}


@router.post('/password_recovery/confirm')
async def password_recovery_confirm(req: PasswordResetConfirmRequest):
    if len(req.new_password) < 4:
        raise HTTPException(status_code=400, detail='Contraseña demasiado corta')
    try:
        token_row = await fetch_one('cms', 'SELECT id, username, token, expires_at, consumed FROM password_reset_tokens WHERE token = %s AND username = %s', (req.token, req.username))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error validando token: {e}')
    if not token_row:
        raise HTTPException(status_code=400, detail='Token inválido')
    if int(token_row.get('consumed') or 0) == 1:
        raise HTTPException(status_code=400, detail='Token ya usado')
    # verificar expiración
    expires_at = token_row.get('expires_at')
    try:
        if isinstance(expires_at, str):
            # intentar parse rápido
            expires_dt = datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S')
        else:
            expires_dt = expires_at
    except Exception:
        raise HTTPException(status_code=500, detail='Formato de expiración inválido en token')
    if datetime.utcnow() > expires_dt:
        raise HTTPException(status_code=400, detail='Token expirado')
    # actualizar password
    try:
        new_salt, new_verifier = _compute_verifier(req.username, req.new_password)
        await execute('auth', 'UPDATE account SET verifier = %s, salt = %s WHERE username = %s', (new_verifier, new_salt, req.username))
        await execute('cms', 'UPDATE password_reset_tokens SET consumed = 1 WHERE id = %s', (token_row.get('id'),))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error aplicando nueva contraseña: {e}')
    return {'ok': True}
