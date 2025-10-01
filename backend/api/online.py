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


@router.get("/arena_top")
async def arena_top():
    """
    Retorna el top 10 de equipos 2v2, 3v3 y 5v5 por cada realm configurado.
    Estructura:
    {
      "realms": [
         {
           "realm_id": X,
           "name": "...",
           "teams": {
             "2v2": [ { team fields } ],
             "3v3": [...],
             "5v5": [...]
           }
         },
         ...
      ]
    }
    Si un realm no tiene datos de conexión a characters o falla la conexión, se marca status.
    """
    try:
        realms = await fetch_all("cms", "SELECT realm_id, name, char_db_host, char_db_port, char_db_user, char_db_password, char_db_name FROM realms")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read realms from CMS: {e}")

    if not realms:
        return {"realms": []}

    async def fetch_arena_for_realm(r):
        realm_id = r.get("realm_id")
        name = r.get("name") or f"realm-{realm_id}"
        host = r.get("char_db_host")
        port = r.get("char_db_port") or 3306
        user = r.get("char_db_user")
        password = r.get("char_db_password")
        dbname = r.get("char_db_name")
        if not host or not user or not dbname:
            return {"realm_id": realm_id, "name": name, "status": "no_connection_info", "teams": {"2v2": [], "3v3": [], "5v5": []}}
        try:
            conn = await aiomysql.connect(host=host, port=int(port), user=user, password=password or "", db=dbname)
            async with conn.cursor(aiomysql.DictCursor) as cur:
                out = {"2v2": [], "3v3": [], "5v5": []}
                for bracket, tval in [("2v2", 2), ("3v3", 3), ("5v5", 5)]:
                    q = ("SELECT arenaTeamId AS id, name, captainGuid, type, rating, seasonGames, seasonWins, weekGames, weekWins, rank "
                         "FROM arena_team WHERE type = %s ORDER BY rating DESC, rank ASC LIMIT 10")
                    await cur.execute(q, (tval,))
                    rows = await cur.fetchall()
                    serial = []
                    if rows:
                        for row in rows:
                            season_games = row.get("seasonGames") or 0
                            season_wins = row.get("seasonWins") or 0
                            week_games = row.get("weekGames") or 0
                            week_wins = row.get("weekWins") or 0
                            season_ratio = float(season_wins) / season_games if season_games > 0 else 0.0
                            week_ratio = float(week_wins) / week_games if week_games > 0 else 0.0
                            serial.append({
                                "id": row.get("id"),
                                "name": row.get("name"),
                                "captainGuid": row.get("captainGuid"),
                                "type": row.get("type"),
                                "rating": row.get("rating"),
                                "seasonGames": season_games,
                                "seasonWins": season_wins,
                                "seasonWinRatio": round(season_ratio, 4),
                                "weekGames": week_games,
                                "weekWins": week_wins,
                                "weekWinRatio": round(week_ratio, 4),
                                "rank": row.get("rank"),
                            })
                    out[bracket] = serial
            conn.close()
            await conn.wait_closed()
            return {"realm_id": realm_id, "name": name, "status": "ok", "teams": out}
        except Exception:
            return {"realm_id": realm_id, "name": name, "status": "offline", "teams": {"2v2": [], "3v3": [], "5v5": []}}

    tasks = [fetch_arena_for_realm(r) for r in realms]
    results = await asyncio.gather(*tasks)
    return {"realms": results}


@router.get("/arena_team/{team_id}")
async def arena_team_detail(team_id: int):
    """Devuelve información del equipo de arena (por id) y sus miembros en cada realm donde exista.
    Estructura:
    {
      "team_id": X,
      "realms": [
         { "realm_id": R, "name": "..", "status": "ok|offline|no_connection_info|not_found", "team": {...}, "members": [...] },
         ...
      ]
    }
    """
    try:
        realms = await fetch_all("cms", "SELECT realm_id, name, char_db_host, char_db_port, char_db_user, char_db_password, char_db_name FROM realms")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read realms from CMS: {e}")

    if not realms:
        return {"team_id": team_id, "realms": []}

    async def fetch_team(r):
        realm_id = r.get("realm_id")
        name = r.get("name") or f"realm-{realm_id}"
        host = r.get("char_db_host")
        port = r.get("char_db_port") or 3306
        user = r.get("char_db_user")
        password = r.get("char_db_password")
        dbname = r.get("char_db_name")
        if not host or not user or not dbname:
            return {"realm_id": realm_id, "name": name, "status": "no_connection_info", "team": None, "members": []}
        try:
            conn = await aiomysql.connect(host=host, port=int(port), user=user, password=password or "", db=dbname)
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("SELECT arenaTeamId AS id, name, captainGuid, type, rating, seasonGames, seasonWins, weekGames, weekWins, rank FROM arena_team WHERE arenaTeamId = %s", (team_id,))
                team_row = await cur.fetchone()
                if not team_row:
                    conn.close(); await conn.wait_closed()
                    return {"realm_id": realm_id, "name": name, "status": "not_found", "team": None, "members": []}
                # compute ratios
                sg = team_row.get("seasonGames") or 0
                sw = team_row.get("seasonWins") or 0
                wg = team_row.get("weekGames") or 0
                ww = team_row.get("weekWins") or 0
                team_row["seasonWinRatio"] = round((float(sw)/sg) if sg>0 else 0.0, 4)
                team_row["weekWinRatio"] = round((float(ww)/wg) if wg>0 else 0.0, 4)
                # members
                members = []
                try:
                    await cur.execute(
                        "SELECT m.guid, m.seasonGames, m.seasonWins, m.weekGames, m.weekWins, m.personalRating, c.name, c.race, c.class, c.level "
                        "FROM arena_team_member m LEFT JOIN characters c ON c.guid = m.guid WHERE m.arenaTeamId = %s",
                        (team_id,)
                    )
                    mrows = await cur.fetchall()
                    if mrows:
                        for mr in mrows:
                            m_sg = mr.get("seasonGames") or 0
                            m_sw = mr.get("seasonWins") or 0
                            m_wg = mr.get("weekGames") or 0
                            m_ww = mr.get("weekWins") or 0
                            members.append({
                                "guid": mr.get("guid"),
                                "name": mr.get("name"),
                                "race": mr.get("race"),
                                "class": mr.get("class"),
                                "level": mr.get("level"),
                                "seasonGames": m_sg,
                                "seasonWins": m_sw,
                                "seasonWinRatio": round((float(m_sw)/m_sg) if m_sg>0 else 0.0, 4),
                                "weekGames": m_wg,
                                "weekWins": m_ww,
                                "weekWinRatio": round((float(m_ww)/m_wg) if m_wg>0 else 0.0, 4),
                                "personalRating": mr.get("personalRating"),
                            })
                except Exception:
                    # si la tabla o columnas no existen devolvemos sin miembros detallados
                    members = []
            conn.close()
            await conn.wait_closed()
            return {"realm_id": realm_id, "name": name, "status": "ok", "team": team_row, "members": members}
        except Exception:
            return {"realm_id": realm_id, "name": name, "status": "offline", "team": None, "members": []}

    tasks = [fetch_team(r) for r in realms]
    results = await asyncio.gather(*tasks)
    return {"team_id": team_id, "realms": results}
