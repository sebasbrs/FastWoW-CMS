from fastapi import APIRouter, HTTPException
from ..db import fetch_one, fetch_all
import aiomysql
import asyncio

router = APIRouter()


@router.get("/realm_status")
async def realm_status():
    alliance_races = {1, 3, 4, 7, 11}
    horde_races = {2, 5, 6, 8, 10}

    try:
        realms = await fetch_all("cms", "SELECT id, realm_id, name, char_db_host, char_db_port, char_db_user, char_db_password, char_db_name FROM realms")
    except Exception:
        try:
            realms = await fetch_all("auth", "SELECT id as id, id as realm_id, name, NULL as char_db_host, NULL as char_db_port, NULL as char_db_user, NULL as char_db_password, NULL as char_db_name FROM realmlist")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to list realms: {e}")

    if not realms:
        return {"realms": []}

    async def process_realm(r):
        realm_id = r.get("realm_id")
        name = r.get("name") or f"realm-{realm_id}"

        uptime = None
        try:
            up_row = await fetch_one("auth", "SELECT uptime FROM uptime WHERE realm_id = %s", (realm_id,))
            if up_row:
                uptime = up_row.get("uptime")
        except Exception:
            uptime = None

        total_online = 0
        alliance = 0
        horde = 0

        host = r.get("char_db_host")
        port = r.get("char_db_port") or 3306
        user = r.get("char_db_user")
        password = r.get("char_db_password")
        dbname = r.get("char_db_name")

        if host and user and dbname:
            try:
                conn = await aiomysql.connect(host=host, port=int(port), user=user, password=password or "", db=dbname)
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute("SELECT COUNT(*) AS cnt FROM characters WHERE online = 1")
                    r1 = await cur.fetchone()
                    total_online = int(r1.get("cnt") or 0)

                    await cur.execute("SELECT race, COUNT(*) AS cnt FROM characters WHERE online = 1 GROUP BY race")
                    rows = await cur.fetchall()
                    for row in rows:
                        race = int(row.get("race") or 0)
                        cnt = int(row.get("cnt") or 0)
                        if race in alliance_races:
                            alliance += cnt
                        elif race in horde_races:
                            horde += cnt
                        else:
                            pass

                conn.close()
                await conn.wait_closed()
            except Exception:
                return {"id": realm_id, "name": name, "online": 0, "alliance": 0, "horde": 0, "uptime": uptime, "status": "offline"}
        else:
            return {"id": realm_id, "name": name, "online": 0, "alliance": 0, "horde": 0, "uptime": uptime, "status": "no_connection_info"}

        return {"id": realm_id, "name": name, "online": total_online, "alliance": alliance, "horde": horde, "uptime": uptime, "status": "online"}

    tasks = [process_realm(r) for r in realms]
    results = await asyncio.gather(*tasks)

    return {"realms": results}


@router.get("/online")
async def online_all(limit_per_realm: int = 200, page: int = 1, page_size: int = 50):
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1
    MAX_PAGE_SIZE = 500
    if page_size > MAX_PAGE_SIZE:
        page_size = MAX_PAGE_SIZE

    try:
        realms = await fetch_all("cms", "SELECT realm_id, name, char_db_host, char_db_port, char_db_user, char_db_password, char_db_name FROM realms")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read realms from CMS: {e}")

    if not realms:
        return {"realms": []}

    alliance_races = {1, 3, 4, 7, 11}
    horde_races = {2, 5, 6, 8, 10}

    async def fetch_chars_for_realm(r):
        realm_id = r.get("realm_id")
        name = r.get("name") or f"realm-{realm_id}"

        host = r.get("char_db_host")
        port = r.get("char_db_port") or 3306
        user = r.get("char_db_user")
        password = r.get("char_db_password")
        dbname = r.get("char_db_name")

        if not host or not user or not dbname:
            return {"realm_id": realm_id, "name": name, "status": "no_connection_info", "characters": []}

        try:
            conn = await aiomysql.connect(host=host, port=int(port), user=user, password=password or "", db=dbname)
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("SELECT COUNT(*) AS cnt FROM characters WHERE online = 1")
                rcount = await cur.fetchone()
                total = int(rcount.get("cnt") or 0)

                offset = (page - 1) * page_size
                limit = page_size

                q = (
                    "SELECT c.guid, c.name, c.race, c.class, c.gender, c.level, g.name AS guild_name "
                    "FROM characters c "
                    "LEFT JOIN guild_member gm ON c.guid = gm.guid "
                    "LEFT JOIN guild g ON gm.guildid = g.guildid "
                    "WHERE c.online = 1 "
                    "ORDER BY c.level DESC, c.name ASC "
                    f"LIMIT {offset}, {limit}"
                )
                await cur.execute(q)
                rows = await cur.fetchall()
            conn.close()
            await conn.wait_closed()
        except Exception:
            return {"realm_id": realm_id, "name": name, "status": "offline", "characters": []}

        out = []
        for row in rows:
            race_val = int(row.get("race") or 0)
            if race_val in horde_races:
                faction = 1
            elif race_val in alliance_races:
                faction = 2
            else:
                faction = 0

            out.append({
                "guid": int(row.get("guid") or 0),
                "name": row.get("name"),
                "race": race_val,
                "class": int(row.get("class") or 0),
                "gender": int(row.get("gender") or 0),
                "level": int(row.get("level") or 0),
                "guild": row.get("guild_name"),
                "faction": faction,
            })

        pagination = {"page": page, "page_size": limit, "total": total}
        return {"realm_id": realm_id, "name": name, "status": "online", "pagination": pagination, "characters": out}

    tasks = [fetch_chars_for_realm(r) for r in realms]
    results = await asyncio.gather(*tasks)

    online_realms = [r for r in results if r.get("status") == "online"]

    return {"realms": online_realms}


