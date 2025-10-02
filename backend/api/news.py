from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Any
import re
import datetime

from db import fetch_one, fetch_all, execute
from api.auth import get_current_user, require_logged, require_admin  # reuse session + role validation

router = APIRouter()


class NewsCreate(BaseModel):
    title: str
    content: str
    summary: Optional[str] = None
    realm_id: Optional[int] = None
    publish: bool = False
    priority: int = 0


class NewsUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    realm_id: Optional[int] = None
    publish: Optional[bool] = None
    priority: Optional[int] = None


class CommentCreate(BaseModel):
    content: str


def _serialize_comment(row: dict) -> dict:
    return {
        'id': row.get('id'),
        'author': row.get('author_username'),
        'content': row.get('content'),
        'created_at': row.get('created_at').isoformat() if row.get('created_at') else None
    }


SLUG_SAFE_RE = re.compile(r'[^a-z0-9\-]+')


async def _generate_unique_slug(title: str) -> str:
    base = title.strip().lower()
    # replace spaces with dashes
    base = re.sub(r'\s+', '-', base)
    # remove unsafe chars
    base = SLUG_SAFE_RE.sub('', base)
    # collapse multiple dashes
    base = re.sub(r'-{2,}', '-', base).strip('-')
    if not base:
        base = 'noticia'

    slug = base
    idx = 1
    # ensure uniqueness
    while True:
        row = await fetch_one('cms', 'SELECT id FROM news WHERE slug = %s', (slug,))
        if not row:
            return slug
        idx += 1
        slug = f"{base}-{idx}"


def _serialize_news(row: dict) -> dict:
    if not row:
        return {}
    return {
        'id': row.get('id'),
        'title': row.get('title'),
        'slug': row.get('slug'),
        'summary': row.get('summary'),
        'content': row.get('content'),
        'realm_id': row.get('realm_id'),
        'author': row.get('author_username'),
        'is_published': bool(row.get('is_published')),
        'published_at': row.get('published_at').isoformat() if row.get('published_at') else None,
        'created_at': row.get('created_at').isoformat() if row.get('created_at') else None,
        'updated_at': row.get('updated_at').isoformat() if row.get('updated_at') else None,
        'priority': row.get('priority')
    }


@router.get('/news')
async def list_news(page: int = 1, page_size: int = 10, realm_id: Optional[int] = None):
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1
    MAX_PAGE = 100
    if page_size > MAX_PAGE:
        page_size = MAX_PAGE

    params: list[Any] = []
    where = 'WHERE is_published = 1'
    if realm_id is not None:
        where += ' AND (realm_id = %s OR realm_id IS NULL)'
        params.append(realm_id)

    # total
    row = await fetch_one('cms', f'SELECT COUNT(*) AS cnt FROM news {where}', tuple(params))
    total = int(row.get('cnt') if row else 0)
    offset = (page - 1) * page_size

    rows = await fetch_all('cms', f'SELECT * FROM news {where} ORDER BY priority DESC, published_at DESC, id DESC LIMIT %s OFFSET %s', (*params, page_size, offset))
    items = [_serialize_news(r) for r in (rows or [])]
    return {'items': items, 'pagination': {'page': page, 'page_size': page_size, 'total': total}}

@router.get('/news/admin', dependencies=[Depends(require_admin)])
async def admin_list_news(page: int = 1, page_size: int = 20, realm_id: Optional[int] = None, include_unpublished: bool = True):
    """Lista todas las noticias sin filtrar por publicación para el panel admin."""
    if page < 1: page = 1
    if page_size < 1: page_size = 1
    if page_size > 200: page_size = 200
    clauses = []
    params: list[Any] = []
    if realm_id is not None:
        clauses.append('(realm_id = %s OR realm_id IS NULL)'); params.append(realm_id)
    where = ' WHERE ' + ' AND '.join(clauses) if clauses else ''
    total_row = await fetch_one('cms', f'SELECT COUNT(*) AS cnt FROM news{where}', tuple(params))
    total = int(total_row.get('cnt') if total_row else 0)
    offset = (page - 1) * page_size
    rows = await fetch_all('cms', f'SELECT * FROM news{where} ORDER BY priority DESC, created_at DESC, id DESC LIMIT %s OFFSET %s', (*params, page_size, offset))
    items = [_serialize_news(r) for r in (rows or [])]
    return { 'items': items, 'pagination': { 'page': page, 'page_size': page_size, 'total': total } }


@router.get('/news/{id_or_slug}')
async def get_news(id_or_slug: str):
    row = None
    if id_or_slug.isdigit():
        row = await fetch_one('cms', 'SELECT * FROM news WHERE id = %s', (int(id_or_slug),))
    if not row:
        row = await fetch_one('cms', 'SELECT * FROM news WHERE slug = %s', (id_or_slug,))
    if not row:
        raise HTTPException(status_code=404, detail='Noticia no encontrada')
    # hide unpublished
    if not row.get('is_published'):
        raise HTTPException(status_code=404, detail='Noticia no encontrada')
    comments = await fetch_all('cms', 'SELECT * FROM news_comments WHERE news_id = %s ORDER BY id DESC', (row.get('id'),))
    serialized_comments = [_serialize_comment(c) for c in (comments or [])]
    data = _serialize_news(row)
    data['comments'] = serialized_comments
    data['comments_count'] = len(serialized_comments)
    return data


@router.post('/news', status_code=201)
async def create_news(payload: NewsCreate, user: dict = Depends(require_logged)):
    # Any authenticated user can create for now
    if len(payload.title.strip()) < 3:
        raise HTTPException(status_code=400, detail='Título demasiado corto')
    if len(payload.content.strip()) < 5:
        raise HTTPException(status_code=400, detail='Contenido demasiado corto')

    slug = await _generate_unique_slug(payload.title)
    is_pub = 1 if payload.publish else 0
    published_at = datetime.datetime.utcnow() if is_pub else None

    q = ('INSERT INTO news (title, slug, summary, content, realm_id, author_username, is_published, published_at, priority) '
         'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)')
    params = (payload.title, slug, payload.summary, payload.content, payload.realm_id, user.get('username'), is_pub, published_at, payload.priority)
    try:
        _, last_id = await execute('cms', q, params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error creando noticia: {e}')

    row = await fetch_one('cms', 'SELECT * FROM news WHERE id = %s', (last_id,))
    return _serialize_news(row)


@router.patch('/news/{news_id}')
async def update_news(news_id: int, payload: NewsUpdate, user: dict = Depends(require_logged)):
    row = await fetch_one('cms', 'SELECT * FROM news WHERE id = %s', (news_id,))
    if not row:
        raise HTTPException(status_code=404, detail='Noticia no encontrada')

    fields = []
    params: list[Any] = []

    # Title => maybe slug change
    if payload.title is not None:
        if len(payload.title.strip()) < 3:
            raise HTTPException(status_code=400, detail='Título demasiado corto')
        new_slug = await _generate_unique_slug(payload.title) if payload.title != row.get('title') else row.get('slug')
        fields.extend(['title = %s', 'slug = %s'])
        params.extend([payload.title, new_slug])

    if payload.content is not None:
        if len(payload.content.strip()) < 5:
            raise HTTPException(status_code=400, detail='Contenido demasiado corto')
        fields.append('content = %s')
        params.append(payload.content)

    if payload.summary is not None:
        fields.append('summary = %s')
        params.append(payload.summary)

    if payload.realm_id is not None:  # allow setting to explicit value or keep existing
        fields.append('realm_id = %s')
        params.append(payload.realm_id)

    if payload.priority is not None:
        fields.append('priority = %s')
        params.append(payload.priority)

    if payload.publish is not None:
        if payload.publish and not row.get('is_published'):
            fields.append('is_published = 1')
            fields.append('published_at = UTC_TIMESTAMP()')
        elif (not payload.publish) and row.get('is_published'):
            fields.append('is_published = 0')
            fields.append('published_at = NULL')

    if not fields:
        return _serialize_news(row)  # nothing changed

    fields.append('updated_at = UTC_TIMESTAMP()')
    set_clause = ', '.join(fields)
    params.append(news_id)
    q = f'UPDATE news SET {set_clause} WHERE id = %s'
    try:
        await execute('cms', q, tuple(params))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error actualizando noticia: {e}')

    row2 = await fetch_one('cms', 'SELECT * FROM news WHERE id = %s', (news_id,))
    return _serialize_news(row2)


@router.delete('/news/{news_id}', status_code=204)
async def delete_news(news_id: int, user: dict = Depends(require_admin)):
    row = await fetch_one('cms', 'SELECT id FROM news WHERE id = %s', (news_id,))
    if not row:
        raise HTTPException(status_code=404, detail='Noticia no encontrada')
    try:
        await execute('cms', 'DELETE FROM news WHERE id = %s', (news_id,))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error eliminando noticia: {e}')
    return None


# -------- Comments --------

@router.post('/news/{news_id}/comments', status_code=201)
async def add_comment(news_id: int, payload: CommentCreate, user: dict = Depends(require_logged)):
    if len(payload.content.strip()) < 2:
        raise HTTPException(status_code=400, detail='Comentario demasiado corto')
    # ensure news exists and is published
    news_row = await fetch_one('cms', 'SELECT id, is_published FROM news WHERE id = %s', (news_id,))
    if not news_row or not news_row.get('is_published'):
        raise HTTPException(status_code=404, detail='Noticia no encontrada')
    try:
        _, last_id = await execute('cms', 'INSERT INTO news_comments (news_id, author_username, content) VALUES (%s,%s,%s)', (news_id, user.get('username'), payload.content))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error creando comentario: {e}')
    row = await fetch_one('cms', 'SELECT * FROM news_comments WHERE id = %s', (last_id,))
    return _serialize_comment(row)


@router.get('/news/{news_id}/comments')
async def list_comments(news_id: int, page: int = 1, page_size: int = 30):
    if page < 1: page = 1
    if page_size < 1: page_size = 1
    if page_size > 100: page_size = 100
    # ensure news exists & is published
    news_row = await fetch_one('cms', 'SELECT id, is_published FROM news WHERE id = %s', (news_id,))
    if not news_row or not news_row.get('is_published'):
        raise HTTPException(status_code=404, detail='Noticia no encontrada')
    total_row = await fetch_one('cms', 'SELECT COUNT(*) AS cnt FROM news_comments WHERE news_id = %s', (news_id,))
    total = int(total_row.get('cnt') if total_row else 0)
    offset = (page - 1) * page_size
    rows = await fetch_all('cms', 'SELECT * FROM news_comments WHERE news_id = %s ORDER BY id DESC LIMIT %s OFFSET %s', (news_id, page_size, offset))
    return {
        'items': [_serialize_comment(r) for r in (rows or [])],
        'pagination': {'page': page, 'page_size': page_size, 'total': total}
    }


@router.delete('/news/{news_id}/comments/{comment_id}', status_code=204)
async def delete_comment(news_id: int, comment_id: int, user: dict = Depends(require_logged)):
    row = await fetch_one('cms', 'SELECT author_username FROM news_comments WHERE id = %s AND news_id = %s', (comment_id, news_id))
    if not row:
        raise HTTPException(status_code=404, detail='Comentario no encontrado')
    # allow delete if admin or author
    is_admin = int(user.get('role', 1)) >= 2
    if (row.get('author_username') != user.get('username')) and not is_admin:
        raise HTTPException(status_code=403, detail='No autorizado')
    try:
        await execute('cms', 'DELETE FROM news_comments WHERE id = %s', (comment_id,))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error eliminando comentario: {e}')
    return None
