import asyncio
from typing import Dict, Any, Optional

import aiomysql

from config import DB_CONFIG, DEFAULT_POOL_ARGS


class DatabasePools:
    """Manage aiomysql pools for multiple schemas (cms, auth, characters, world)."""

    def __init__(self):
        self._pools: Dict[str, aiomysql.Pool] = {}
        self._lock = asyncio.Lock()

    async def init_pools(self):
        async with self._lock:
            if self._pools:
                return
            for key, cfg in DB_CONFIG.items():
                pool = await aiomysql.create_pool(
                    host=cfg["host"],
                    port=cfg["port"],
                    user=cfg["user"],
                    password=cfg["password"],
                    db=cfg["db"],
                    autocommit=True,
                    **DEFAULT_POOL_ARGS,
                )
                self._pools[key] = pool

    async def close_pools(self):
        async with self._lock:
            for pool in self._pools.values():
                pool.close()
                await pool.wait_closed()
            self._pools.clear()

    def get_pool(self, key: str) -> Optional[aiomysql.Pool]:
        return self._pools.get(key)


db_pools = DatabasePools()


async def fetch_one(pool_key: str, query: str, params: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
    pool = db_pools.get_pool(pool_key)
    if pool is None:
        raise RuntimeError(f"Pool for {pool_key} is not initialized")
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(query, params or ())
            return await cur.fetchone()


async def fetch_all(pool_key: str, query: str, params: Optional[tuple] = None) -> Optional[list]:
    pool = db_pools.get_pool(pool_key)
    if pool is None:
        raise RuntimeError(f"Pool for {pool_key} is not initialized")
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(query, params or ())
            return await cur.fetchall()


async def execute(pool_key: str, query: str, params: Optional[tuple] = None) -> int:
    """Execute a statement (INSERT/UPDATE/DELETE). Returns affected rowcount."""
    pool = db_pools.get_pool(pool_key)
    if pool is None:
        raise RuntimeError(f"Pool for {pool_key} is not initialized")
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, params or ())
            # return a tuple (rowcount, lastrowid) where lastrowid may be 0 if not applicable
            return cur.rowcount, getattr(cur, "lastrowid", 0)
