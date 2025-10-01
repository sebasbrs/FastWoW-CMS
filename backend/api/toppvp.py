from fastapi import APIRouter, HTTPException
from typing import Optional
from ..db import fetch_all
import aiomysql
import asyncio

router = APIRouter()


@router.get("/top_pvp")
async def top_pvp(realm_id: Optional[int] = None, limit: int = 100):
    alliance_races = {1, 3, 4, 7, 11}
    horde_races = {2, 5, 6, 8, 10}

    try:
        if realm_id:
            realms = await fetch_all("cms", "SELECT realm_id, name, char_db_host, char_db_port, char_db_user, char_db_password, char_db_name FROM realms WHERE realm_id = %s", (realm_id,))
        else:
            realms = await fetch_all("cms", "SELECT realm_id, name, char_db_host, char_db_port, char_db_user, char_db_password, char_db_name FROM realms")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read realms from CMS: {e}")

    if not realms:
        return {"realms": []}

    async def fetch_top_for_realm(r):
        realm_id = r.get("realm_id")
        name = r.get("name") or f"realm-{realm_id}"

        host = r.get("char_db_host")
        port = r.get("char_db_port") or 3306
        user = r.get("char_db_user")
        password = r.get("char_db_password")
        dbname = r.get("char_db_name")

        if not host or not user or not dbname:
            return {"realm_id": realm_id, "name": name, "status": "no_connection_info", "players": []}

        q = (
            "SELECT c.guid, c.name, c.race, c.class, c.gender, c.level, c.totalkill, g.name AS guild_name "
            "FROM characters c "
            "LEFT JOIN guild_member gm ON c.guid = gm.guid "
            "LEFT JOIN guild g ON gm.guildid = g.guildid "
            "ORDER BY c.totalkill DESC "
            f"LIMIT {int(limit)}"
        )

        try:
            conn = await aiomysql.connect(host=host, port=int(port), user=user, password=password or "", db=dbname)
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(q)
                rows = await cur.fetchall()
            conn.close()
            await conn.wait_closed()
        except Exception:
            return {"realm_id": realm_id, "name": name, "status": "offline", "players": []}

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
                "totalkill": int(row.get("totalkill") or 0),
                "faction": faction,
            })

        return {"realm_id": realm_id, "name": name, "status": "online", "players": out}

    tasks = [fetch_top_for_realm(r) for r in realms]
    results = await asyncio.gather(*tasks)

    return {"realms": results}
