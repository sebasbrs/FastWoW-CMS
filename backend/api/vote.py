from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional
from api.auth import require_admin, require_logged
from db import fetch_one, fetch_all, execute, begin_transaction, release_connection, tx_execute, tx_fetch_one
import datetime

router = APIRouter(prefix="/vote", tags=["vote"]) 

# ----------------- Models -----------------
class VoteSiteCreate(BaseModel):
    name: str
    url: str
    image_url: Optional[str] = None
    cooldown_minutes: int = 720
    points_reward: int = 1
    position: int = 0

class VoteSiteUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    cooldown_minutes: Optional[int] = None
    points_reward: Optional[int] = None
    position: Optional[int] = None
    is_enabled: Optional[bool] = None

class VoteClaimResponse(BaseModel):
    ok: bool
    site_id: int
    reward: int
    next_available_at: datetime.datetime
    total_vote_points: int
    site_url: Optional[str] = None

# ----------------- Admin Sites CRUD -----------------
@router.post('/sites', dependencies=[Depends(require_admin)])
async def create_site(payload: VoteSiteCreate):
    if payload.cooldown_minutes < 1 or payload.points_reward < 1:
        raise HTTPException(status_code=400, detail='Valores inválidos')
    try:
        _, sid = await execute('cms', 'INSERT INTO vote_sites (name, url, image_url, cooldown_minutes, points_reward, position) VALUES (%s,%s,%s,%s,%s,%s)', (
            payload.name.strip(), payload.url.strip(), (payload.image_url or '').strip() or None, payload.cooldown_minutes, payload.points_reward, payload.position
        ))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error creando sitio: {e}')
    site = await fetch_one('cms', 'SELECT * FROM vote_sites WHERE id = %s', (sid,))
    return site

@router.get('/sites')
async def list_sites(include_disabled: bool = False):
    where = '1=1' if include_disabled else 'is_enabled = 1'
    rows = await fetch_all('cms', f'SELECT * FROM vote_sites WHERE {where} ORDER BY position ASC, id ASC')
    return rows or []

@router.patch('/sites/{site_id}', dependencies=[Depends(require_admin)])
async def update_site(site_id: int, payload: VoteSiteUpdate):
    row = await fetch_one('cms', 'SELECT * FROM vote_sites WHERE id = %s', (site_id,))
    if not row:
        raise HTTPException(status_code=404, detail='Sitio no encontrado')
    fields = []
    values = []
    mapping = {
        'name': payload.name,
        'url': payload.url,
        'image_url': payload.image_url,
        'cooldown_minutes': payload.cooldown_minutes,
        'points_reward': payload.points_reward,
        'position': payload.position,
        'is_enabled': payload.is_enabled,
    }
    for col, val in mapping.items():
        if val is not None:
            fields.append(f'{col} = %s'); values.append(val)
    if fields:
        values.append(site_id)
        try:
            await execute('cms', f"UPDATE vote_sites SET {', '.join(fields)} WHERE id = %s", tuple(values))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f'Error actualizando sitio: {e}')
    site = await fetch_one('cms', 'SELECT * FROM vote_sites WHERE id = %s', (site_id,))
    return site

@router.delete('/sites/{site_id}', status_code=204, dependencies=[Depends(require_admin)])
async def delete_site(site_id: int):
    row = await fetch_one('cms', 'SELECT id FROM vote_sites WHERE id = %s', (site_id,))
    if not row:
        raise HTTPException(status_code=404, detail='Sitio no encontrado')
    try:
        await execute('cms', 'DELETE FROM vote_sites WHERE id = %s', (site_id,))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error eliminando sitio: {e}')
    return None

# ----------------- Voting / Claim -----------------
async def _perform_claim(username: str, site_id: int):
    site = await fetch_one('cms', 'SELECT * FROM vote_sites WHERE id = %s AND is_enabled = 1', (site_id,))
    if not site:
        raise HTTPException(status_code=404, detail='Sitio no disponible')
    cooldown = int(site.get('cooldown_minutes') or 0)
    reward = int(site.get('points_reward') or 0)
    if cooldown < 1 or reward < 1:
        raise HTTPException(status_code=400, detail='Configuración inválida')
    now = datetime.datetime.utcnow()
    last_log = await fetch_one('cms', 'SELECT next_available_at FROM vote_logs WHERE username = %s AND site_id = %s ORDER BY id DESC LIMIT 1', (username, site_id))
    if last_log:
        nla = last_log.get('next_available_at')
        if nla and nla > now:
            # Cooldown activo
            raise HTTPException(status_code=429, detail='Cooldown activo')
    next_available_at = now + datetime.timedelta(minutes=cooldown)
    conn, tx = await begin_transaction('cms')
    try:
        acct_tx = await tx_fetch_one(conn, 'SELECT vote_points FROM account WHERE username = %s FOR UPDATE', (username,))
        if not acct_tx:
            raise HTTPException(status_code=400, detail='Cuenta no encontrada')
        new_points = int(acct_tx.get('vote_points') or 0) + reward
        await tx_execute(conn, 'UPDATE account SET vote_points = %s WHERE username = %s', (new_points, username))
        await tx_execute(conn, 'INSERT INTO vote_logs (username, site_id, claimed_points, next_available_at) VALUES (%s,%s,%s,%s)', (username, site_id, reward, next_available_at))
        await tx.commit()
    except HTTPException:
        await tx.rollback(); await release_connection('cms', conn); raise
    except Exception as e:
        await tx.rollback(); await release_connection('cms', conn)
        raise HTTPException(status_code=500, detail=f'Error reclamando voto: {e}')
    await release_connection('cms', conn)
    return {
        'site': site,
        'reward': reward,
        'next_available_at': next_available_at,
        'total_vote_points': new_points
    }

@router.post('/sites/{site_id}/claim', response_model=VoteClaimResponse)
async def claim_vote(site_id: int, user: dict = Depends(require_logged)):
    username = user.get('username')
    data = await _perform_claim(username, site_id)
    site = data['site']
    return VoteClaimResponse(
        ok=True,
        site_id=site_id,
        reward=data['reward'],
        next_available_at=data['next_available_at'],
        total_vote_points=data['total_vote_points'],
        site_url=site.get('url')
    )

@router.post('/sites/{site_id}/click', response_model=VoteClaimResponse)
async def click_vote(site_id: int, user: dict = Depends(require_logged)):
    """Endpoint para usar en el click del frontend.
    Otorga el punto inmediatamente (si no hay cooldown) y devuelve la URL para abrir en nueva pestaña.
    """
    username = user.get('username')
    data = await _perform_claim(username, site_id)
    site = data['site']
    return VoteClaimResponse(
        ok=True,
        site_id=site_id,
        reward=data['reward'],
        next_available_at=data['next_available_at'],
        total_vote_points=data['total_vote_points'],
        site_url=site.get('url')
    )

@router.get('/sites/{site_id}/redirect')
async def redirect_vote(site_id: int, user: dict = Depends(require_logged)):
    """Versión GET para abrir directamente en nueva pestaña usando window.open.
    Intenta reclamar y luego redirige. Si hay cooldown, igual redirige (sin otorgar puntos)."""
    username = user.get('username')
    try:
        data = await _perform_claim(username, site_id)
        site_url = data['site'].get('url')
    except HTTPException as he:
        # Si sitio no disponible => error; si cooldown activo => redirigir igual sin puntos
        if he.status_code == 429:
            site = await fetch_one('cms', 'SELECT url FROM vote_sites WHERE id = %s', (site_id,))
            if site:
                return RedirectResponse(url=site.get('url'))
        raise
    return RedirectResponse(url=site_url)

@router.get('/logs')
async def list_logs(page: int = 1, page_size: int = 50, site_id: Optional[int] = None, user: dict = Depends(require_logged)):
    if page < 1: page = 1
    if page_size < 1: page_size = 1
    if page_size > 200: page_size = 200
    params = [user.get('username')]
    where = 'username = %s'
    if site_id is not None:
        where += ' AND site_id = %s'
        params.append(site_id)
    total_row = await fetch_one('cms', f'SELECT COUNT(*) AS cnt FROM vote_logs WHERE {where}', tuple(params))
    total = int(total_row.get('cnt') or 0) if total_row else 0
    offset = (page - 1) * page_size
    rows = await fetch_all('cms', f'SELECT * FROM vote_logs WHERE {where} ORDER BY id DESC LIMIT %s OFFSET %s', tuple(params + [page_size, offset]))
    return {'items': rows or [], 'pagination': {'page': page, 'page_size': page_size, 'total': total}}
