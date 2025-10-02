from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional
from .auth import require_logged, require_admin
from ..db import fetch_one, fetch_all, execute, begin_transaction, tx_fetch_one, tx_execute, release_connection
import os, datetime, hmac, hashlib, json, time

router = APIRouter(prefix="/donations", tags=["donations"]) 

# ---------------- Config helpers ----------------
PAYPAL_CLIENT_ID = os.getenv('PAYPAL_CLIENT_ID', '')
PAYPAL_CLIENT_SECRET = os.getenv('PAYPAL_CLIENT_SECRET', '')
PAYPAL_API_BASE = os.getenv('PAYPAL_API_BASE', 'https://api-m.sandbox.paypal.com')  # sandbox por defecto
DONATION_CREDITS_RATE = int(os.getenv('DONATION_CREDITS_RATE', '100'))  # credits por 1 unidad monetaria
DONATION_ALLOWED_CURRENCIES = set((os.getenv('DONATION_ALLOWED_CURRENCIES', 'USD,EUR').split(',')))
PAYPAL_WEBHOOK_ID = os.getenv('PAYPAL_WEBHOOK_ID', '')  # para validación de firma (si se configura)

# ---- Bold Config ----
BOLD_API_KEY = os.getenv('BOLD_API_KEY','')
BOLD_SECRET_KEY = os.getenv('BOLD_SECRET_KEY','')
BOLD_ALLOWED_CURRENCIES = set((os.getenv('BOLD_ALLOWED_CURRENCIES','COP').split(',')))
BOLD_CREDITS_RATE = int(os.getenv('BOLD_CREDITS_RATE','100'))
BOLD_DEFAULT_REDIRECT_URL = os.getenv('BOLD_DEFAULT_REDIRECT_URL','')

# ---------------- Models ----------------
class CreatePaypalOrderRequest(BaseModel):
    amount: float
    currency: str = 'USD'

class CreatePaypalOrderResponse(BaseModel):
    ok: bool
    order_id: str
    approve_link: str

class DonationRecordResponse(BaseModel):
    id: int
    username: str
    gateway: str
    external_id: str
    status: str
    amount: float
    currency: str
    credits_rate: int
    credits_granted: int
    created_at: datetime.datetime

# ---- Bold Models ----
class BoldCreateRequest(BaseModel):
    amount: int  # entero sin decimales (Bold maneja unidades enteras)
    currency: str = 'COP'
    description: Optional[str] = None
    tax: Optional[str] = None  # e.g. vat-19, vat-5, etc.
    redirection_url: Optional[str] = None

class BoldCreateResponse(BaseModel):
    ok: bool
    order_id: str
    amount: int
    currency: str
    integrity_signature: str
    api_key: str
    redirection_url: str
    description: Optional[str]
    tax: Optional[str]

class BoldHashRequest(BaseModel):
    order_id: str
    amount: int
    currency: str

class BoldHashResponse(BaseModel):
    ok: bool
    integrity_signature: str

class BoldWebhook(BaseModel):
    order_id: str
    payment_status: str  # approved|rejected|pending|cancelled
    amount: Optional[int] = 0
    currency: Optional[str] = 'COP'

class BoldWebhookResponse(BaseModel):
    ok: bool
    granted: bool
    status: str

# ---------------- Utilities ----------------
import aiohttp

async def _paypal_get_access_token() -> str:
    if not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail='PayPal no configurado')
    auth = aiohttp.BasicAuth(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET)
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{PAYPAL_API_BASE}/v1/oauth2/token", data={'grant_type':'client_credentials'}, auth=auth) as resp:
            data = await resp.json()
            if resp.status >= 400:
                raise HTTPException(status_code=500, detail=f'Error token PayPal: {data}')
            return data.get('access_token')

async def _paypal_create_order(amount: float, currency: str, username: str):
    token = await _paypal_get_access_token()
    headers = { 'Authorization': f'Bearer {token}', 'Content-Type': 'application/json' }
    body = {
        'intent': 'CAPTURE',
        'purchase_units': [
            {
                'reference_id': username,
                'amount': { 'currency_code': currency, 'value': f"{amount:.2f}" }
            }
        ],
        'application_context': {
            'shipping_preference': 'NO_SHIPPING',
            'user_action': 'PAY_NOW'
        }
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{PAYPAL_API_BASE}/v2/checkout/orders", headers=headers, json=body) as resp:
            data = await resp.json()
            if resp.status >= 400:
                raise HTTPException(status_code=500, detail=f'Error creando orden PayPal: {data}')
            return data

async def _paypal_capture_order(order_id: str):
    token = await _paypal_get_access_token()
    headers = { 'Authorization': f'Bearer {token}', 'Content-Type': 'application/json' }
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{PAYPAL_API_BASE}/v2/checkout/orders/{order_id}/capture", headers=headers) as resp:
            data = await resp.json()
            if resp.status >= 400:
                raise HTTPException(status_code=500, detail=f'Error capturando orden PayPal: {data}')
            return data

# ---------------- Endpoints ----------------
@router.post('/paypal/order', response_model=CreatePaypalOrderResponse)
async def create_paypal_order(payload: CreatePaypalOrderRequest, user: dict = Depends(require_logged)):
    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail='Monto inválido')
    currency = payload.currency.upper()
    if currency not in DONATION_ALLOWED_CURRENCIES:
        raise HTTPException(status_code=400, detail='Moneda no permitida')
    order = await _paypal_create_order(payload.amount, currency, user.get('username'))
    order_id = order.get('id')
    approve_link = ''
    for link in order.get('links', []):
        if link.get('rel') == 'approve':
            approve_link = link.get('href'); break
    # registrar en DB
    credits_rate = DONATION_CREDITS_RATE
    try:
        _, did = await execute('cms', 'INSERT INTO donation_payments (username, gateway, external_id, status, amount, currency, credits_rate, raw_create_response) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)', (
            user.get('username'), 'paypal', order_id, order.get('status', 'CREATED'), payload.amount, currency, credits_rate, json.dumps(order)
        ))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error registrando orden: {e}')
    return CreatePaypalOrderResponse(ok=True, order_id=order_id, approve_link=approve_link)

class CapturePaypalOrderRequest(BaseModel):
    order_id: str

@router.post('/paypal/capture', response_model=DonationRecordResponse)
async def capture_paypal_order(payload: CapturePaypalOrderRequest, user: dict = Depends(require_logged)):
    # Verifica que la orden pertenece al usuario (defensa extra)
    record = await fetch_one('cms', 'SELECT * FROM donation_payments WHERE external_id = %s AND username = %s', (payload.order_id, user.get('username')))
    if not record:
        raise HTTPException(status_code=404, detail='Orden no encontrada')
    if record.get('status') in ('COMPLETED','APPROVED') and record.get('credits_granted')>0:
        # idempotencia
        return DonationRecordResponse(
            id=record.get('id'), username=record.get('username'), gateway=record.get('gateway'), external_id=record.get('external_id'),
            status=record.get('status'), amount=float(record.get('amount')), currency=record.get('currency'), credits_rate=record.get('credits_rate'), credits_granted=record.get('credits_granted'), created_at=record.get('created_at')
        )
    capture = await _paypal_capture_order(payload.order_id)
    # Determinar si fue completado
    new_status = capture.get('status')
    completed = new_status == 'COMPLETED'
    # Actualizar DB + otorgar créditos si procede (transacción)
    conn, tx = await begin_transaction('cms')
    try:
        # lock row
        db_row = await tx_fetch_one(conn, 'SELECT * FROM donation_payments WHERE external_id = %s FOR UPDATE', (payload.order_id,))
        if not db_row:
            raise HTTPException(status_code=404, detail='Orden no encontrada (tx)')
        if db_row.get('status') == 'COMPLETED' and db_row.get('credits_granted')>0:
            await tx.commit(); await release_connection('cms', conn)
            return DonationRecordResponse(
                id=db_row.get('id'), username=db_row.get('username'), gateway=db_row.get('gateway'), external_id=db_row.get('external_id'),
                status=db_row.get('status'), amount=float(db_row.get('amount')), currency=db_row.get('currency'), credits_rate=db_row.get('credits_rate'), credits_granted=db_row.get('credits_granted'), created_at=db_row.get('created_at')
            )
        await tx_execute(conn, 'UPDATE donation_payments SET status = %s, raw_capture_response = %s, updated_at = NOW() WHERE external_id = %s', (new_status, json.dumps(capture), payload.order_id))
        credits_granted = 0
        if completed:
            # calcular créditos
            credits_granted = int(float(db_row.get('amount')) * db_row.get('credits_rate'))
            # sumar a la cuenta
            acct = await tx_fetch_one(conn, 'SELECT credits FROM account WHERE username = %s FOR UPDATE', (db_row.get('username'),))
            if not acct:
                raise HTTPException(status_code=400, detail='Cuenta no encontrada para otorgar créditos')
            new_credits = int(acct.get('credits') or 0) + credits_granted
            await tx_execute(conn, 'UPDATE account SET credits = %s WHERE username = %s', (new_credits, db_row.get('username')))
            await tx_execute(conn, 'UPDATE donation_payments SET credits_granted = %s, granted_at = NOW() WHERE external_id = %s', (credits_granted, payload.order_id))
        await tx.commit()
    except HTTPException:
        await tx.rollback(); await release_connection('cms', conn); raise
    except Exception as e:
        await tx.rollback(); await release_connection('cms', conn); raise HTTPException(status_code=500, detail=f'Error capturando orden: {e}')
    await release_connection('cms', conn)
    rec = await fetch_one('cms', 'SELECT * FROM donation_payments WHERE external_id = %s', (payload.order_id,))
    return DonationRecordResponse(
        id=rec.get('id'), username=rec.get('username'), gateway=rec.get('gateway'), external_id=rec.get('external_id'),
        status=rec.get('status'), amount=float(rec.get('amount')), currency=rec.get('currency'), credits_rate=rec.get('credits_rate'), credits_granted=rec.get('credits_granted'), created_at=rec.get('created_at')
    )

# ---------------- Bold Helpers ----------------
def _bold_generate_order_id(username: str) -> str:
    ts = int(time.time()*1000)
    base = f"{username}-{ts}"
    return base[:60]

def _bold_hash(order_id: str, amount: int, currency: str) -> str:
    raw = f"{order_id}{amount}{currency}{BOLD_SECRET_KEY}"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()

# ---------------- Bold Endpoints ----------------
@router.post('/bold/hash', response_model=BoldHashResponse)
async def bold_hash(payload: BoldHashRequest, user: dict = Depends(require_logged)):
    if not BOLD_SECRET_KEY:
        raise HTTPException(status_code=500, detail='Bold no configurado (secret)')
    if payload.currency.upper() not in BOLD_ALLOWED_CURRENCIES:
        raise HTTPException(status_code=400, detail='Moneda no permitida')
    sig = _bold_hash(payload.order_id, payload.amount, payload.currency.upper())
    return BoldHashResponse(ok=True, integrity_signature=sig)

@router.post('/bold/create', response_model=BoldCreateResponse)
async def bold_create(payload: BoldCreateRequest, user: dict = Depends(require_logged)):
    if not BOLD_API_KEY or not BOLD_SECRET_KEY:
        raise HTTPException(status_code=500, detail='Bold no configurado')
    if payload.amount < 0:
        raise HTTPException(status_code=400, detail='Monto inválido')
    currency = payload.currency.upper()
    if currency not in BOLD_ALLOWED_CURRENCIES:
        raise HTTPException(status_code=400, detail='Moneda no permitida')
    order_id = _bold_generate_order_id(user.get('username'))
    integrity_signature = _bold_hash(order_id, payload.amount, currency)
    redirect = payload.redirection_url or BOLD_DEFAULT_REDIRECT_URL or ''
    try:
        _, _did = await execute('cms', 'INSERT INTO donation_payments (username, gateway, external_id, status, amount, currency, credits_rate, raw_create_response) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)', (
            user.get('username'), 'bold', order_id, 'CREATED', float(payload.amount), currency, BOLD_CREDITS_RATE, json.dumps({'description': payload.description, 'tax': payload.tax})
        ))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error registrando orden Bold: {e}')
    return BoldCreateResponse(ok=True, order_id=order_id, amount=payload.amount, currency=currency, integrity_signature=integrity_signature, api_key=BOLD_API_KEY, redirection_url=redirect, description=payload.description, tax=payload.tax)

ALLOWED_BOLD_FINAL = {'approved','rejected','cancelled'}

@router.post('/bold/webhook', response_model=BoldWebhookResponse)
async def bold_webhook(payload: BoldWebhook):
    order_id = payload.order_id
    row = await fetch_one('cms', 'SELECT * FROM donation_payments WHERE external_id = %s AND gateway = %s', (order_id, 'bold'))
    if not row:
        raise HTTPException(status_code=404, detail='Orden no encontrada')
    status = payload.payment_status.lower()
    if status not in ('approved','rejected','pending','cancelled'):
        raise HTTPException(status_code=400, detail='Estado inválido')
    conn, tx = await begin_transaction('cms')
    try:
        db_row = await tx_fetch_one(conn, 'SELECT * FROM donation_payments WHERE external_id = %s FOR UPDATE', (order_id,))
        if not db_row:
            await tx.rollback(); await release_connection('cms', conn)
            raise HTTPException(status_code=404, detail='Orden no encontrada tx')
        if db_row.get('status') == 'COMPLETED' and db_row.get('credits_granted')>0:
            await tx.commit(); await release_connection('cms', conn)
            return BoldWebhookResponse(ok=True, granted=True, status='COMPLETED')
        internal_status = 'COMPLETED' if status == 'approved' else ('FAILED' if status == 'rejected' else status.upper())
        await tx_execute(conn, 'UPDATE donation_payments SET status = %s, updated_at = NOW() WHERE external_id = %s', (internal_status, order_id))
        granted = False
        if internal_status == 'COMPLETED' and db_row.get('credits_granted') == 0:
            credits_granted = int(float(db_row.get('amount')) * db_row.get('credits_rate'))
            acct = await tx_fetch_one(conn, 'SELECT credits FROM account WHERE username = %s FOR UPDATE', (db_row.get('username'),))
            if acct:
                new_credits = int(acct.get('credits') or 0) + credits_granted
                await tx_execute(conn, 'UPDATE account SET credits = %s WHERE username = %s', (new_credits, db_row.get('username')))
                await tx_execute(conn, 'UPDATE donation_payments SET credits_granted = %s, granted_at = NOW() WHERE external_id = %s', (credits_granted, order_id))
                granted = True
        await tx.commit(); await release_connection('cms', conn)
    except HTTPException:
        raise
    except Exception as e:
        await tx.rollback(); await release_connection('cms', conn)
        raise HTTPException(status_code=500, detail=f'Error webhook Bold: {e}')
    return BoldWebhookResponse(ok=True, granted=granted, status=internal_status)

# -------- Webhook (PayPal) --------
class PayPalWebhookMock(BaseModel):
    id: Optional[str]
    event_type: str
    resource: dict

@router.post('/paypal/webhook')
async def paypal_webhook(payload: PayPalWebhookMock, request: Request):
    # TODO: Validar la firma del webhook (PAYPAL-AUTH-ALGO, TRANSMISSION-ID, etc). Por ahora confianza.
    event = payload.event_type
    resource = payload.resource or {}
    order_id = resource.get('id') or resource.get('resource', {}).get('id')
    if not order_id:
        raise HTTPException(status_code=400, detail='Webhook sin order id')
    # Candidatos de eventos relevantes: CHECKOUT.ORDER.APPROVED, PAYMENT.CAPTURE.COMPLETED
    try:
        if event in ('CHECKOUT.ORDER.APPROVED','PAYMENT.CAPTURE.COMPLETED'):
            # Marcar aprobado/completado y otorgar créditos si capture indica completed
            capture_status = resource.get('status')
            conn, tx = await begin_transaction('cms')
            try:
                row = await tx_fetch_one(conn, 'SELECT * FROM donation_payments WHERE external_id = %s FOR UPDATE', (order_id,))
                if not row:
                    await tx.rollback(); await release_connection('cms', conn)
                    return {'ignored': True, 'reason': 'order not found'}
                status_before = row.get('status')
                if status_before == 'COMPLETED' and row.get('credits_granted')>0:
                    await tx.commit(); await release_connection('cms', conn)
                    return {'ok': True, 'idempotent': True}
                # Update status raw_capture_response for logging
                await tx_execute(conn, 'UPDATE donation_payments SET status = %s, raw_capture_response = %s, webhook_verified = 1 WHERE external_id = %s', (capture_status or event, json.dumps(resource), order_id))
                if (capture_status == 'COMPLETED' or event == 'PAYMENT.CAPTURE.COMPLETED') and row.get('credits_granted') == 0:
                    credits = int(float(row.get('amount')) * row.get('credits_rate'))
                    acct = await tx_fetch_one(conn, 'SELECT credits FROM account WHERE username = %s FOR UPDATE', (row.get('username'),))
                    if acct:
                        new_credits = int(acct.get('credits') or 0) + credits
                        await tx_execute(conn, 'UPDATE account SET credits = %s WHERE username = %s', (new_credits, row.get('username')))
                        await tx_execute(conn, 'UPDATE donation_payments SET credits_granted = %s, granted_at = NOW() WHERE external_id = %s', (credits, order_id))
                await tx.commit()
            except Exception as e:
                await tx.rollback(); await release_connection('cms', conn)
                raise HTTPException(status_code=500, detail=f'Error webhook: {e}')
            await release_connection('cms', conn)
    except HTTPException:
        raise
    return {'ok': True}

@router.get('/mine')
async def list_my_donations(user: dict = Depends(require_logged), page: int = 1, page_size: int = 50):
    if page < 1: page = 1
    if page_size < 1: page_size = 1
    if page_size > 200: page_size = 200
    total_row = await fetch_one('cms', 'SELECT COUNT(*) AS cnt FROM donation_payments WHERE username = %s', (user.get('username'),))
    total = int(total_row.get('cnt') or 0) if total_row else 0
    offset = (page - 1) * page_size
    rows = await fetch_all('cms', 'SELECT id, gateway, external_id, status, amount, currency, credits_rate, credits_granted, created_at FROM donation_payments WHERE username = %s ORDER BY id DESC LIMIT %s OFFSET %s', (user.get('username'), page_size, offset))
    return {'items': rows or [], 'pagination': {'page': page, 'page_size': page_size, 'total': total}}

@router.get('/admin', dependencies=[Depends(require_admin)])
async def list_all_donations(page: int = 1, page_size: int = 100, status: Optional[str] = None):
    if page < 1: page = 1
    if page_size < 1: page_size = 1
    if page_size > 500: page_size = 500
    clauses = ['1=1']
    params = []
    if status:
        clauses.append('status = %s'); params.append(status)
    where = ' AND '.join(clauses)
    total_row = await fetch_one('cms', f'SELECT COUNT(*) AS cnt FROM donation_payments WHERE {where}', tuple(params))
    total = int(total_row.get('cnt') or 0) if total_row else 0
    offset = (page - 1) * page_size
    rows = await fetch_all('cms', f'SELECT id, username, gateway, external_id, status, amount, currency, credits_rate, credits_granted, created_at FROM donation_payments WHERE {where} ORDER BY id DESC LIMIT %s OFFSET %s', tuple(params + [page_size, offset]))
    return {'items': rows or [], 'pagination': {'page': page, 'page_size': page_size, 'total': total}}
