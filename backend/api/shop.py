from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from .auth import require_logged, require_admin, get_current_user
from ..db import fetch_one, fetch_all, execute, db_pools, begin_transaction, release_connection, tx_execute, tx_fetch_one
from ..config import get_soap_realm_config  # legacy env fallback (will use DB first)
import aiohttp
import asyncio
import re

router = APIRouter(prefix="/shop", tags=["shop"])

_slug_re = re.compile(r'[^a-z0-9]+')

def _slugify(text: str) -> str:
    s = text.lower().strip()
    s = _slug_re.sub('-', s)
    s = s.strip('-')
    if not s:
        s = 'cat'
    return s[:140]

async def _unique_slug(table: str, slug: str) -> str:
    base = slug
    idx = 1
    while True:
        row = await fetch_one('cms', f'SELECT id FROM {table} WHERE slug = %s', (slug,))
        if not row:
            return slug
        slug = f"{base}-{idx}"
        idx += 1

# ---------------- Models -----------------
class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    position: Optional[int] = 0

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    position: Optional[int] = None

class ItemCreate(BaseModel):
    category_id: int
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    world_item_entry: int
    realm_id: Optional[int] = None
    price_vote_points: int = 0
    price_credits: int = 0
    limit_per_account: Optional[int] = None

class ItemUpdate(BaseModel):
    category_id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    world_item_entry: Optional[int] = None
    realm_id: Optional[int] = None
    price_vote_points: Optional[int] = None
    price_credits: Optional[int] = None
    is_enabled: Optional[bool] = None
    limit_per_account: Optional[int] = None

class PurchaseRequest(BaseModel):
    # Deprecated single item legacy (mantained for compat): usar 'items'
    item_id: Optional[int] = None
    realm_id: Optional[int] = None  # override if item realm is null
    character_guid: Optional[int] = None
    character_name: Optional[str] = None
    items: Optional[list[dict]] = None  # [{"shop_item_id": int, "quantity": int}] si se omite usa item_id=1

# -------------- Categories ---------------
@router.post('/categories', dependencies=[Depends(require_admin)])
async def create_category(payload: CategoryCreate):
    if not payload.name or len(payload.name.strip()) < 2:
        raise HTTPException(status_code=400, detail='Nombre inválido')
    slug = await _unique_slug('shop_categories', _slugify(payload.name))
    try:
        _, last_id = await execute('cms', 'INSERT INTO shop_categories (name, slug, description, position) VALUES (%s,%s,%s,%s)', (payload.name.strip(), slug, payload.description, payload.position or 0))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error creando categoria: {e}')
    row = await fetch_one('cms', 'SELECT * FROM shop_categories WHERE id = %s', (last_id,))
    return row

@router.get('/categories')
async def list_categories():
    rows = await fetch_all('cms', 'SELECT * FROM shop_categories ORDER BY position ASC, id ASC')
    return rows or []

@router.patch('/categories/{category_id}', dependencies=[Depends(require_admin)])
async def update_category(category_id: int, payload: CategoryUpdate):
    row = await fetch_one('cms', 'SELECT id FROM shop_categories WHERE id = %s', (category_id,))
    if not row:
        raise HTTPException(status_code=404, detail='Categoria no encontrada')
    fields = []
    values = []
    if payload.name is not None:
        fields.append('name = %s'); values.append(payload.name)
    if payload.description is not None:
        fields.append('description = %s'); values.append(payload.description)
    if payload.position is not None:
        fields.append('position = %s'); values.append(payload.position)
    if fields:
        values.append(category_id)
        q = f"UPDATE shop_categories SET {', '.join(fields)} WHERE id = %s"
        try:
            await execute('cms', q, tuple(values))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f'Error actualizando categoria: {e}')
    row = await fetch_one('cms', 'SELECT * FROM shop_categories WHERE id = %s', (category_id,))
    return row

@router.delete('/categories/{category_id}', status_code=204, dependencies=[Depends(require_admin)])
async def delete_category(category_id: int):
    row = await fetch_one('cms', 'SELECT id FROM shop_categories WHERE id = %s', (category_id,))
    if not row:
        raise HTTPException(status_code=404, detail='Categoria no encontrada')
    try:
        await execute('cms', 'DELETE FROM shop_categories WHERE id = %s', (category_id,))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error eliminando categoria: {e}')
    return None

# ---------------- Items ------------------
@router.post('/items', dependencies=[Depends(require_admin)])
async def create_item(payload: ItemCreate):
    if not payload.name or len(payload.name.strip()) < 2:
        raise HTTPException(status_code=400, detail='Nombre inválido')
    if payload.price_vote_points < 0 or payload.price_credits < 0:
        raise HTTPException(status_code=400, detail='Precio inválido')
    # ensure category exists
    cat = await fetch_one('cms', 'SELECT id FROM shop_categories WHERE id = %s', (payload.category_id,))
    if not cat:
        raise HTTPException(status_code=400, detail='Categoria inexistente')
    try:
        _, last_id = await execute('cms', 'INSERT INTO shop_items (category_id, name, description, icon, world_item_entry, realm_id, price_vote_points, price_credits, limit_per_account) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)', (
            payload.category_id, payload.name.strip(), payload.description, payload.icon, payload.world_item_entry, payload.realm_id, payload.price_vote_points, payload.price_credits, payload.limit_per_account
        ))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error creando item: {e}')
    row = await fetch_one('cms', 'SELECT * FROM shop_items WHERE id = %s', (last_id,))
    return row

@router.get('/items')
async def list_items(category_id: Optional[int] = None, realm_id: Optional[int] = None):
    clauses = ['is_enabled = 1']
    params = []
    if category_id is not None:
        clauses.append('category_id = %s'); params.append(category_id)
    if realm_id is not None:
        clauses.append('(realm_id IS NULL OR realm_id = %s)'); params.append(realm_id)
    where = ' AND '.join(clauses)
    rows = await fetch_all('cms', f'SELECT * FROM shop_items WHERE {where} ORDER BY id DESC', tuple(params))
    return rows or []

# --------------- Realms & Characters helper endpoints ---------------
@router.get('/realms')
async def list_realms():
    rows = await fetch_all('cms', 'SELECT realm_id, name, soap_enabled FROM realms ORDER BY realm_id ASC', None)
    return rows or []


@router.get('/realms/{realm_id}/characters')
async def list_characters(realm_id: int, user: dict = Depends(require_logged)):
    auth_acct = await fetch_one('auth', 'SELECT id FROM account WHERE username = %s', (user.get('username'),))
    if not auth_acct:
        return []
    account_id = auth_acct.get('id')
    chars = await fetch_all('characters', 'SELECT guid, name, race, class, level FROM characters WHERE account = %s', (account_id,))
    return chars or []

@router.patch('/items/{item_id}', dependencies=[Depends(require_admin)])
async def update_item(item_id: int, payload: ItemUpdate):
    row = await fetch_one('cms', 'SELECT * FROM shop_items WHERE id = %s', (item_id,))
    if not row:
        raise HTTPException(status_code=404, detail='Item no encontrado')
    fields = []
    values = []
    mapping = {
        'category_id': payload.category_id,
        'name': payload.name,
        'description': payload.description,
        'icon': payload.icon,
        'world_item_entry': payload.world_item_entry,
        'realm_id': payload.realm_id,
        'price_vote_points': payload.price_vote_points,
        'price_credits': payload.price_credits,
        'is_enabled': payload.is_enabled,
        'limit_per_account': payload.limit_per_account,
    }
    for col, val in mapping.items():
        if val is not None:
            if col in ('price_vote_points', 'price_credits') and int(val) < 0:
                raise HTTPException(status_code=400, detail='Precio negativo inválido')
            fields.append(f'{col} = %s'); values.append(val)
    if fields:
        values.append(item_id)
        q = f"UPDATE shop_items SET {', '.join(fields)} WHERE id = %s"
        try:
            await execute('cms', q, tuple(values))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f'Error actualizando item: {e}')
    row = await fetch_one('cms', 'SELECT * FROM shop_items WHERE id = %s', (item_id,))
    return row

@router.delete('/items/{item_id}', status_code=204, dependencies=[Depends(require_admin)])
async def delete_item(item_id: int):
    row = await fetch_one('cms', 'SELECT id FROM shop_items WHERE id = %s', (item_id,))
    if not row:
        raise HTTPException(status_code=404, detail='Item no encontrado')
    try:
        await execute('cms', 'DELETE FROM shop_items WHERE id = %s', (item_id,))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error eliminando item: {e}')
    return None

# --------------- Purchase ----------------
async def _check_limit(username: str, item_id: int, limit: Optional[int]) -> bool:
    if not limit:
        return True
    row = await fetch_one('cms', 'SELECT COUNT(*) AS cnt FROM shop_purchases WHERE username = %s AND item_id = %s', (username, item_id))
    bought = int(row.get('cnt') or 0) if row else 0
    return bought < limit

@router.post('/purchase')
async def purchase(payload: PurchaseRequest, user: dict = Depends(require_logged)):
    username = user.get('username')
    multi_items = []
    if payload.items:
        # validar lista
        if not isinstance(payload.items, list) or len(payload.items) == 0:
            raise HTTPException(status_code=400, detail='Lista de items vacía')
        ids = [it.get('shop_item_id') for it in payload.items if it.get('shop_item_id')]
        if not ids:
            raise HTTPException(status_code=400, detail='Items inválidos')
        # cargar todos
        placeholders = ','.join(['%s'] * len(ids))
        rows = await fetch_all('cms', f'SELECT * FROM shop_items WHERE id IN ({placeholders}) AND is_enabled = 1', tuple(ids)) or []
        items_map = {r['id']: r for r in rows}
        if len(items_map) != len(ids):
            raise HTTPException(status_code=400, detail='Algún item no existe o está deshabilitado')
        for raw in payload.items:
            sid = raw.get('shop_item_id')
            qty = int(raw.get('quantity') or 1)
            if qty < 1:
                raise HTTPException(status_code=400, detail='Cantidad inválida')
            multi_items.append({
                'shop_item': items_map[sid],
                'quantity': qty
            })
        # determinar realm: si mezcla de realms incompatibles => error
        realm_ids = {it['shop_item'].get('realm_id') for it in multi_items if it['shop_item'].get('realm_id') is not None}
        item_realm = None
        if len(realm_ids) == 1:
            item_realm = list(realm_ids)[0]
        elif len(realm_ids) > 1:
            raise HTTPException(status_code=400, detail='No se pueden mezclar items de distintos realms específicos')
        # Si todos null => global
        selected_realm = payload.realm_id or item_realm
    else:
        if not payload.item_id:
            raise HTTPException(status_code=400, detail='Debe especificar item(s)')
        item = await fetch_one('cms', 'SELECT * FROM shop_items WHERE id = %s AND is_enabled = 1', (payload.item_id,))
        if not item:
            raise HTTPException(status_code=404, detail='Item no disponible')
        item_realm = item.get('realm_id')
        selected_realm = payload.realm_id or item_realm
        multi_items = [{'shop_item': item, 'quantity': 1}]
    # realm restriction
    # validar realm contra cada item
    for it in multi_items:
        ir = it['shop_item'].get('realm_id')
        if ir is not None and selected_realm and ir != selected_realm:
            raise HTTPException(status_code=400, detail='Realm inválido para un item de la lista')
    # limit per account
    for it in multi_items:
        if not await _check_limit(username, it['shop_item'].get('id'), it['shop_item'].get('limit_per_account')):
            raise HTTPException(status_code=400, detail=f'Límite alcanzado para item {it['shop_item'].get('id')}')
    # fetch user balances
    acct = await fetch_one('cms', 'SELECT credits, vote_points FROM account WHERE username = %s', (username,))
    if not acct:
        raise HTTPException(status_code=400, detail='Cuenta no encontrada')
    credits = int(acct.get('credits') or 0)
    vp = int(acct.get('vote_points') or 0)
    # sumar costos
    price_vp = 0
    price_cr = 0
    for it in multi_items:
        price_vp += int(it['shop_item'].get('price_vote_points') or 0) * it['quantity']
        price_cr += int(it['shop_item'].get('price_credits') or 0) * it['quantity']
    if (price_vp > vp) or (price_cr > credits):
        raise HTTPException(status_code=400, detail='Fondos insuficientes')
    # Validar personaje si se especifica
    char_guid = payload.character_guid
    char_name = payload.character_name
    if char_guid or char_name:
        auth_acct = await fetch_one('auth', 'SELECT id FROM account WHERE username = %s', (username,))
        if not auth_acct:
            raise HTTPException(status_code=400, detail='Cuenta auth no encontrada')
        account_id = auth_acct.get('id')
        character = await fetch_one('characters', 'SELECT guid, name FROM characters WHERE guid = %s AND account = %s', (char_guid, account_id)) if char_guid else None
        if char_guid and not character:
            raise HTTPException(status_code=400, detail='Personaje no válido')
        if not character and char_name:
            character = await fetch_one('characters', 'SELECT guid, name FROM characters WHERE name = %s AND account = %s', (char_name, account_id))
        if not character:
            raise HTTPException(status_code=400, detail='Personaje no encontrado')
        char_guid = character.get('guid')
        char_name = character.get('name')
    # Transacción real
    conn, tx = await begin_transaction('cms')
    try:
        # Refrescar saldos dentro de transacción
        acct_tx = await tx_fetch_one(conn, 'SELECT credits, vote_points FROM account WHERE username = %s FOR UPDATE', (username,))
        if not acct_tx:
            raise HTTPException(status_code=400, detail='Cuenta no encontrada (tx)')
        credits_tx = int(acct_tx.get('credits') or 0)
        vp_tx = int(acct_tx.get('vote_points') or 0)
        if price_vp > vp_tx or price_cr > credits_tx:
            raise HTTPException(status_code=400, detail='Fondos insuficientes')
        if price_vp > 0:
            upd_vp = await tx_execute(conn, 'UPDATE account SET vote_points = vote_points - %s WHERE username = %s', (price_vp, username))
        if price_cr > 0:
            upd_cr = await tx_execute(conn, 'UPDATE account SET credits = credits - %s WHERE username = %s', (price_cr, username))
        ins = await tx_execute(conn, 'INSERT INTO shop_purchases (username, item_id, realm_id, character_guid, character_name, cost_vote_points, cost_credits) VALUES (%s,NULL,%s,%s,%s,%s,%s)', (username, selected_realm, char_guid, char_name, price_vp, price_cr))
        pid = ins[1]
        # insertar items
        for it in multi_items:
            await tx_execute(conn, 'INSERT INTO shop_purchase_items (purchase_id, shop_item_id, world_item_entry, quantity) VALUES (%s,%s,%s,%s)', (pid, it['shop_item'].get('id'), it['shop_item'].get('world_item_entry'), it['quantity']))
        await tx.commit()
    except HTTPException as he:
        await tx.rollback()
        await release_connection('cms', conn)
        raise he
    except Exception as e:
        await tx.rollback()
        await release_connection('cms', conn)
        raise HTTPException(status_code=500, detail=f'Error transacción compra: {e}')
    await release_connection('cms', conn)
    # TODO: Envío via SOAP (pendiente de implementar cuando se definan credenciales)
    purchase_row = await fetch_one('cms', 'SELECT * FROM shop_purchases WHERE id = %s', (pid,))
    purchase_items = await fetch_all('cms', 'SELECT * FROM shop_purchase_items WHERE purchase_id = %s', (pid,))

    # Intento de envío SOAP en background (no bloquea la respuesta al usuario)
    asyncio.create_task(_deliver_purchase_via_soap(purchase_row, purchase_items))
    return {'ok': True, 'purchase': purchase_row, 'items': purchase_items, 'soap_dispatched': True}


# --------------- Purchases listing ---------------
@router.get('/purchases')
async def list_purchases(page: int = 1, page_size: int = 50, username: Optional[str] = None, user: dict = Depends(require_logged)):
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1
    if page_size > 200:
        page_size = 200
    is_admin = int(user.get('role', 1)) >= 2
    target_user = username if (is_admin and username) else user.get('username')
    total_row = await fetch_one('cms', 'SELECT COUNT(*) AS cnt FROM shop_purchases WHERE username = %s', (target_user,))
    total = int(total_row.get('cnt') or 0) if total_row else 0
    offset = (page - 1) * page_size
    rows = await fetch_all('cms', 'SELECT * FROM shop_purchases WHERE username = %s ORDER BY id DESC LIMIT %s OFFSET %s', (target_user, page_size, offset))
    return {
        'items': rows or [],
        'pagination': {'page': page, 'page_size': page_size, 'total': total},
        'username': target_user
    }


@router.post('/purchases/{purchase_id}/resend')
async def resend_purchase(purchase_id: int, force: bool = False, user: dict = Depends(require_logged)):
    """Reintenta el envío SOAP de una compra.

    - Si la compra ya fue enviada y `force=false`, devuelve estado sin reenviar.
    - Si `force=true`, fuerza reenvío incluso si ya estaba marcada como enviada.
    - Autorización: dueño de la compra o admin (role >=2).
    """
    purchase = await fetch_one('cms', 'SELECT * FROM shop_purchases WHERE id = %s', (purchase_id,))
    if not purchase:
        raise HTTPException(status_code=404, detail='Compra no encontrada')
    is_admin = int(user.get('role', 1)) >= 2
    if (purchase.get('username') != user.get('username')) and not is_admin:
        raise HTTPException(status_code=403, detail='No autorizado')
    if purchase.get('sent_via_soap') and not force:
        return {'ok': True, 'already_sent': True, 'forced': False}
    purchase_items = await fetch_all('cms', 'SELECT * FROM shop_purchase_items WHERE purchase_id = %s', (purchase_id,)) or []
    if not purchase_items:
        # compat: intento legacy single-item
        if purchase.get('item_id'):
            legacy_item = await fetch_one('cms', 'SELECT id AS shop_item_id, world_item_entry FROM shop_items WHERE id = %s', (purchase.get('item_id'),))
            if legacy_item:
                purchase_items = [{'world_item_entry': legacy_item.get('world_item_entry'), 'quantity': 1}]
        if not purchase_items:
            raise HTTPException(status_code=400, detail='Compra sin items asociados')
    # Disparo async
    asyncio.create_task(_deliver_purchase_via_soap(purchase, purchase_items))
    return {'ok': True, 'queued': True, 'forced': force}


# --------------- SOAP Delivery ---------------
async def _deliver_purchase_via_soap(purchase_row: dict, purchase_items: list):
    """Envía el item al personaje por SOAP.

    Estrategia mínima: usar comando 'send items' a la cuenta (requiere personaje => futuro: seleccionar personaje en payload).
    Ahora solo marca sent_via_soap=0/1 y guarda respuesta o error.
    """
    if not purchase_row:
        return
    realm_id = purchase_row.get('realm_id')
    soap_cfg = await _load_realm_soap_config(realm_id)
    if not soap_cfg:
        # fallback a variables de entorno (get_soap_realm_config) si existen
        soap_cfg = get_soap_realm_config(realm_id)
    if not soap_cfg or not soap_cfg.get('enabled'):
        await _update_purchase_soap(purchase_row['id'], False, 'SOAP deshabilitado o config ausente')
        return
    # FUTURO: obtener personaje destino. Por ahora se deja pendiente.
    # Sin personaje no podemos realmente usar 'send items <player>'.
    # Simulamos un comando placeholder que se registraría en logs del core si existiera.
    # Construcción de comando real 'send items': requiere personaje (name), asunto y cuerpo.
    character_name = purchase_row.get('character_name') or ''
    if not character_name:
        await _update_purchase_soap(purchase_row['id'], False, 'Sin personaje destino')
        return
    subject = 'Compra Tienda'
    body = f"Gracias por tu compra, {character_name}!"
    # Por ahora solo un item, stack 1
    # Construir stacks basado en world_item_entry y quantity (similar a PHP)
    # 1) Agrupar por entry
    entry_counts = {}
    for it in purchase_items:
        entry = it.get('world_item_entry')
        qty = int(it.get('quantity') or 1)
        entry_counts[entry] = entry_counts.get(entry, 0) + qty
    # 2) Obtener stack size desde world DB (si disponible) -> fallback 1
    stacks = []  # lista de (entry, stack_qty)
    for entry, total_qty in entry_counts.items():
        stack_row = await fetch_one('world', 'SELECT stackable FROM item_template WHERE entry = %s', (entry,))
        max_stack = int(stack_row.get('stackable') or 1) if stack_row else 1
        if max_stack < 1:
            max_stack = 1
        remaining = total_qty
        while remaining > 0:
            take = remaining if remaining <= max_stack else max_stack
            stacks.append((entry, take))
            remaining -= take
    # 3) Dividir en mails de máximo 12 items (AzerothCore soporta 12 attachments en send items)
    mails = []
    current = []
    for entry, count in stacks:
        if len(current) >= 12:
            mails.append(current)
            current = []
        current.append((entry, count))
    if current:
        mails.append(current)
    responses = []
    for mail_items in mails:
        parts = ' '.join([f'{e}:{c}' for e, c in mail_items])
        command = f'send items {character_name} "{subject}" "{body}" {parts}'
        try:
            resp_text = await _soap_execute(soap_cfg, command)
            responses.append(resp_text[:1000])
        except Exception as e:
            responses.append(f'Error:{e}')
    final_resp = '\n---\n'.join(responses)[:2000]
    success = all(not r.startswith('Error:') for r in responses)
    await _update_purchase_soap(purchase_row['id'], success, final_resp)
    try:
        pass
    except Exception as e:
        await _update_purchase_soap(purchase_row['id'], False, f'Error SOAP final: {e}')


async def _soap_execute(cfg: dict, command: str) -> str:
    """Ejecuta un comando SOAP simple usando HTTP POST estilo AzerothCore.
    Si el core usa SOAP clásico PHP ext/Soap, esta versión HTTP puede necesitar adaptarse.
    """
    # Placeholder genérico usando aiohttp, esperando endpoint estilo http://host:port/ con basic auth (si se configurara).
    # Muchos cores usan autenticación básica. Ajustar según entorno real.
    url = cfg.get('endpoint') or f"http://{cfg['host']}:{cfg['port']}"
    auth = aiohttp.BasicAuth(cfg['user'], cfg['password']) if cfg.get('user') else None
    envelope = f'''<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ns1="urn:AC">
  <SOAP-ENV:Body>
    <ns1:executeCommand>
      <command>{command}</command>
    </ns1:executeCommand>
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>'''
    headers = {'Content-Type': 'text/xml; charset=utf-8'}
    timeout = aiohttp.ClientTimeout(total=cfg.get('timeout', 15))
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, data=envelope.encode('utf-8'), auth=auth, headers=headers) as resp:
            text = await resp.text()
            if resp.status >= 400:
                raise RuntimeError(f'Status {resp.status}: {text[:300]}')
            return text


async def _update_purchase_soap(purchase_id: int, success: bool, response: str):
    try:
        await execute('cms', 'UPDATE shop_purchases SET sent_via_soap = %s, soap_response = %s WHERE id = %s', (1 if success else 0, response, purchase_id))
    except Exception:
        pass


async def _load_realm_soap_config(realm_id: int | None) -> dict | None:
    """Obtiene configuración SOAP desde cms.realms.

    Campos relevantes: soap_enabled, soap_endpoint, soap_user, soap_password, soap_timeout.
    Usa realm_id (columna realm_id en tabla) y no id autoincrement.
    """
    if realm_id is None:
        return None
    row = await fetch_one('cms', 'SELECT soap_enabled, soap_endpoint, soap_user, soap_password, soap_timeout FROM realms WHERE realm_id = %s', (realm_id,))
    if not row:
        return None
    return {
        'enabled': bool(row.get('soap_enabled')),
        'endpoint': row.get('soap_endpoint'),
        'user': row.get('soap_user'),
        'password': row.get('soap_password'),
        'timeout': row.get('soap_timeout') or 30,
        # compat keys para la función previa
        'host': row.get('soap_endpoint') or '',
        'port': 0,
    }
