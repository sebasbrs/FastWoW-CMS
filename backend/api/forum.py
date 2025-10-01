from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from .auth import require_logged, require_admin, get_current_user
from ..db import fetch_one, fetch_all, execute
import re

router = APIRouter(prefix="/forum", tags=["forum"])

# ----------------- Models -----------------
class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    position: Optional[int] = 0

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    position: Optional[int] = None

class TopicCreate(BaseModel):
    title: str
    content: str

class TopicUpdate(BaseModel):
    title: Optional[str] = None

class TopicModerate(BaseModel):
    is_locked: Optional[bool] = None
    is_pinned: Optional[bool] = None
    category_id: Optional[int] = None

class PostCreate(BaseModel):
    content: str

# ----------------- Helpers -----------------
_slug_re = re.compile(r'[^a-z0-9]+')

def _slugify(text: str) -> str:
    s = text.lower().strip()
    s = _slug_re.sub('-', s)
    s = s.strip('-')
    if not s:
        s = 'cat'
    return s[:140]

async def _unique_category_slug(base: str) -> str:
    slug = base
    idx = 1
    while True:
        row = await fetch_one('cms', 'SELECT id FROM forum_categories WHERE slug = %s', (slug,))
        if not row:
            return slug
        slug = f"{base}-{idx}"
        idx += 1

# ----------------- Category Endpoints -----------------
@router.post('/categories', dependencies=[Depends(require_admin)])
async def create_category(payload: CategoryCreate):
    if not payload.name or len(payload.name.strip()) < 2:
        raise HTTPException(status_code=400, detail='Nombre demasiado corto')
    base = _slugify(payload.name)
    slug = await _unique_category_slug(base)
    try:
        _, last_id = await execute('cms', 'INSERT INTO forum_categories (name, slug, description, position) VALUES (%s,%s,%s,%s)', (payload.name.strip(), slug, payload.description, payload.position or 0))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error creando categoria: {e}')
    row = await fetch_one('cms', 'SELECT * FROM forum_categories WHERE id = %s', (last_id,))
    return row

@router.get('/categories')
async def list_categories():
    rows = await fetch_all('cms', 'SELECT * FROM forum_categories ORDER BY position ASC, id ASC')
    return rows or []

@router.patch('/categories/{category_id}', dependencies=[Depends(require_admin)])
async def update_category(category_id: int, payload: CategoryUpdate):
    row = await fetch_one('cms', 'SELECT * FROM forum_categories WHERE id = %s', (category_id,))
    if not row:
        raise HTTPException(status_code=404, detail='Categoria no encontrada')
    fields = []
    values = []
    if payload.name is not None:
        fields.append('name = %s')
        values.append(payload.name)
    if payload.description is not None:
        fields.append('description = %s')
        values.append(payload.description)
    if payload.position is not None:
        fields.append('position = %s')
        values.append(payload.position)
    if fields:
        values.append(category_id)
        q = f"UPDATE forum_categories SET {', '.join(fields)} WHERE id = %s"
        try:
            await execute('cms', q, tuple(values))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f'Error actualizando categoria: {e}')
    row = await fetch_one('cms', 'SELECT * FROM forum_categories WHERE id = %s', (category_id,))
    return row

@router.delete('/categories/{category_id}', status_code=204, dependencies=[Depends(require_admin)])
async def delete_category(category_id: int):
    row = await fetch_one('cms', 'SELECT id FROM forum_categories WHERE id = %s', (category_id,))
    if not row:
        raise HTTPException(status_code=404, detail='Categoria no encontrada')
    try:
        await execute('cms', 'DELETE FROM forum_categories WHERE id = %s', (category_id,))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error eliminando categoria: {e}')
    return None

# ----------------- Topic & Post Endpoints -----------------
@router.post('/categories/{category_id}/topics')
async def create_topic(category_id: int, payload: TopicCreate, user: dict = Depends(require_logged)):
    cat = await fetch_one('cms', 'SELECT id FROM forum_categories WHERE id = %s', (category_id,))
    if not cat:
        raise HTTPException(status_code=404, detail='Categoria no encontrada')
    if not payload.title or len(payload.title.strip()) < 3:
        raise HTTPException(status_code=400, detail='Titulo demasiado corto')
    if not payload.content or len(payload.content.strip()) < 3:
        raise HTTPException(status_code=400, detail='Contenido demasiado corto')
    try:
        _, topic_id = await execute('cms', 'INSERT INTO forum_topics (category_id, title, author_username, last_post_at, posts_count) VALUES (%s,%s,%s,CURRENT_TIMESTAMP,1)', (category_id, payload.title.strip(), user.get('username')))
        await execute('cms', 'INSERT INTO forum_posts (topic_id, author_username, content) VALUES (%s,%s,%s)', (topic_id, user.get('username'), payload.content.strip()))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error creando topic: {e}')
    topic = await fetch_one('cms', 'SELECT * FROM forum_topics WHERE id = %s', (topic_id,))
    return topic

@router.get('/categories/{category_id}/topics')
async def list_topics(category_id: int, page: int = 1, page_size: int = 20):
    if page < 1: page = 1
    if page_size < 1: page_size = 1
    if page_size > 100: page_size = 100
    cat = await fetch_one('cms', 'SELECT id FROM forum_categories WHERE id = %s', (category_id,))
    if not cat:
        raise HTTPException(status_code=404, detail='Categoria no encontrada')
    total_row = await fetch_one('cms', 'SELECT COUNT(*) AS cnt FROM forum_topics WHERE category_id = %s', (category_id,))
    total = int(total_row.get('cnt')) if total_row else 0
    offset = (page - 1) * page_size
    rows = await fetch_all('cms', 'SELECT id, title, author_username, created_at, updated_at, last_post_at, posts_count, is_locked, is_pinned FROM forum_topics WHERE category_id = %s ORDER BY is_pinned DESC, last_post_at DESC, id DESC LIMIT %s OFFSET %s', (category_id, page_size, offset))
    return { 'items': rows or [], 'pagination': { 'page': page, 'page_size': page_size, 'total': total } }

@router.get('/topics/{topic_id}')
async def get_topic(topic_id: int):
    topic = await fetch_one('cms', 'SELECT * FROM forum_topics WHERE id = %s', (topic_id,))
    if not topic:
        raise HTTPException(status_code=404, detail='Topic no encontrado')
    posts = await fetch_all('cms', 'SELECT * FROM forum_posts WHERE topic_id = %s ORDER BY id ASC', (topic_id,))
    topic['posts'] = posts or []
    return topic


@router.patch('/topics/{topic_id}')
async def edit_topic(topic_id: int, payload: TopicUpdate, user: dict = Depends(require_logged)):
    topic = await fetch_one('cms', 'SELECT id, author_username FROM forum_topics WHERE id = %s', (topic_id,))
    if not topic:
        raise HTTPException(status_code=404, detail='Topic no encontrado')
    is_admin = int(user.get('role', 1)) >= 2
    if topic.get('author_username') != user.get('username') and not is_admin:
        raise HTTPException(status_code=403, detail='No autorizado')
    if payload.title is not None:
        if len(payload.title.strip()) < 3:
            raise HTTPException(status_code=400, detail='Titulo demasiado corto')
        try:
            await execute('cms', 'UPDATE forum_topics SET title = %s WHERE id = %s', (payload.title.strip(), topic_id))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f'Error editando topic: {e}')
    row = await fetch_one('cms', 'SELECT * FROM forum_topics WHERE id = %s', (topic_id,))
    return row


@router.delete('/topics/{topic_id}', status_code=204, dependencies=[Depends(require_admin)])
async def delete_topic(topic_id: int):
    topic = await fetch_one('cms', 'SELECT id FROM forum_topics WHERE id = %s', (topic_id,))
    if not topic:
        raise HTTPException(status_code=404, detail='Topic no encontrado')
    try:
        await execute('cms', 'DELETE FROM forum_topics WHERE id = %s', (topic_id,))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error eliminando topic: {e}')
    return None

@router.post('/topics/{topic_id}/posts')
async def add_post(topic_id: int, payload: PostCreate, user: dict = Depends(require_logged)):
    topic = await fetch_one('cms', 'SELECT * FROM forum_topics WHERE id = %s', (topic_id,))
    if not topic:
        raise HTTPException(status_code=404, detail='Topic no encontrado')
    if topic.get('is_locked'):
        raise HTTPException(status_code=403, detail='Topic bloqueado')
    if not payload.content or len(payload.content.strip()) < 2:
        raise HTTPException(status_code=400, detail='Contenido demasiado corto')
    try:
        _, post_id = await execute('cms', 'INSERT INTO forum_posts (topic_id, author_username, content) VALUES (%s,%s,%s)', (topic_id, user.get('username'), payload.content.strip()))
        await execute('cms', 'UPDATE forum_topics SET posts_count = posts_count + 1, last_post_at = CURRENT_TIMESTAMP WHERE id = %s', (topic_id,))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error agregando post: {e}')
    post = await fetch_one('cms', 'SELECT * FROM forum_posts WHERE id = %s', (post_id,))
    return post

@router.delete('/posts/{post_id}', status_code=204)
async def delete_post(post_id: int, user: dict = Depends(require_logged)):
    post = await fetch_one('cms', 'SELECT topic_id, author_username FROM forum_posts WHERE id = %s', (post_id,))
    if not post:
        raise HTTPException(status_code=404, detail='Post no encontrado')
    is_admin = int(user.get('role', 1)) >= 2
    if post.get('author_username') != user.get('username') and not is_admin:
        raise HTTPException(status_code=403, detail='No autorizado')
    try:
        await execute('cms', 'DELETE FROM forum_posts WHERE id = %s', (post_id,))
        # decrement posts_count (safe guard: not below zero)
        await execute('cms', 'UPDATE forum_topics SET posts_count = GREATEST(posts_count - 1,0) WHERE id = %s', (post.get('topic_id'),))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error eliminando post: {e}')
    return None

@router.post('/topics/{topic_id}/lock', dependencies=[Depends(require_admin)])
async def lock_topic(topic_id: int):
    topic = await fetch_one('cms', 'SELECT id FROM forum_topics WHERE id = %s', (topic_id,))
    if not topic:
        raise HTTPException(status_code=404, detail='Topic no encontrado')
    try:
        await execute('cms', 'UPDATE forum_topics SET is_locked = 1 WHERE id = %s', (topic_id,))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error bloqueando topic: {e}')
    return { 'ok': True }

@router.post('/topics/{topic_id}/unlock', dependencies=[Depends(require_admin)])
async def unlock_topic(topic_id: int):
    topic = await fetch_one('cms', 'SELECT id FROM forum_topics WHERE id = %s', (topic_id,))
    if not topic:
        raise HTTPException(status_code=404, detail='Topic no encontrado')
    try:
        await execute('cms', 'UPDATE forum_topics SET is_locked = 0 WHERE id = %s', (topic_id,))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error desbloqueando topic: {e}')
    return { 'ok': True }


@router.post('/topics/{topic_id}/pin', dependencies=[Depends(require_admin)])
async def pin_topic(topic_id: int):
    topic = await fetch_one('cms', 'SELECT id FROM forum_topics WHERE id = %s', (topic_id,))
    if not topic:
        raise HTTPException(status_code=404, detail='Topic no encontrado')
    try:
        await execute('cms', 'UPDATE forum_topics SET is_pinned = 1 WHERE id = %s', (topic_id,))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error fijando topic: {e}')
    return { 'ok': True }


@router.post('/topics/{topic_id}/unpin', dependencies=[Depends(require_admin)])
async def unpin_topic(topic_id: int):
    topic = await fetch_one('cms', 'SELECT id FROM forum_topics WHERE id = %s', (topic_id,))
    if not topic:
        raise HTTPException(status_code=404, detail='Topic no encontrado')
    try:
        await execute('cms', 'UPDATE forum_topics SET is_pinned = 0 WHERE id = %s', (topic_id,))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error desfijando topic: {e}')
    return { 'ok': True }


@router.post('/topics/{topic_id}/move/{new_category_id}', dependencies=[Depends(require_admin)])
async def move_topic(topic_id: int, new_category_id: int):
    topic = await fetch_one('cms', 'SELECT id FROM forum_topics WHERE id = %s', (topic_id,))
    if not topic:
        raise HTTPException(status_code=404, detail='Topic no encontrado')
    cat = await fetch_one('cms', 'SELECT id FROM forum_categories WHERE id = %s', (new_category_id,))
    if not cat:
        raise HTTPException(status_code=404, detail='Categoria destino no existe')
    try:
        await execute('cms', 'UPDATE forum_topics SET category_id = %s WHERE id = %s', (new_category_id, topic_id))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error moviendo topic: {e}')
    return { 'ok': True }
