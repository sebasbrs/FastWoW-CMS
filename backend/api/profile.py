from fastapi import APIRouter, HTTPException
from db import fetch_one, fetch_all
import aiomysql
import hashlib
import asyncio

router = APIRouter(prefix="/profile", tags=["profile"])

# Ruta (lógica) para un avatar local por defecto. El frontend puede mapear este path a /assets/...
AVATAR_FALLBACK_PATH = "/assets/avatars/default.png"


def gravatar_url(email: str, size: int = 128, default: str = "identicon") -> str:
    if not email:
        email = ""
    h = hashlib.md5(email.strip().lower().encode('utf-8')).hexdigest()
    return f"https://www.gravatar.com/avatar/{h}?d={default}&s={size}"


@router.get('/{username}')
async def get_profile(username: str):
    # fetch auth account id + email
    try:
        acct = await fetch_one('auth', 'SELECT id, email FROM account WHERE username = %s', (username,))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error consultando cuenta: {e}')
    if not acct:
        raise HTTPException(status_code=404, detail='Usuario no encontrado')

    account_id = acct.get('id')
    email = acct.get('email') or ''
    avatar = gravatar_url(email)

    # realms
    try:
        realms = await fetch_all('cms', 'SELECT realm_id, name, char_db_host, char_db_port, char_db_user, char_db_password, char_db_name FROM realms')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error obteniendo realms: {e}')

    characters_accum = []

    async def fetch_chars(realm):
        host = realm.get('char_db_host')
        user = realm.get('char_db_user')
        dbname = realm.get('char_db_name')
        port = realm.get('char_db_port') or 3306
        password = realm.get('char_db_password') or ''
        realm_id = realm.get('realm_id')
        realm_name = realm.get('name') or f'Realm {realm_id}'
        if not host or not user or not dbname:
            return []
        try:
            conn = await aiomysql.connect(host=host, port=int(port), user=user, password=password, db=dbname)
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute('SELECT name, level, race, class, gender FROM characters WHERE account = %s', (account_id,))
                rows = await cur.fetchall()
            conn.close()
            await conn.wait_closed()
        except Exception:
            return []
        out = []
        if rows:
            for r in rows:
                out.append({
                    'realm_id': realm_id,
                    'realm_name': realm_name,
                    'name': r.get('name'),
                    'level': int(r.get('level') or 0),
                    'race': int(r.get('race') or 0),
                    'class': int(r.get('class') or 0),
                    'gender': int(r.get('gender') or 0)
                })
        return out

    if realms:
        tasks = [fetch_chars(r) for r in realms]
        results = await asyncio.gather(*tasks)
        for chunk in results:
            if chunk:
                characters_accum.extend(chunk)

    return {
        'username': username,
        'gravatar': avatar,
        'avatar_fallback': AVATAR_FALLBACK_PATH,
        'has_email': bool(email),
        'characters': characters_accum
    }
