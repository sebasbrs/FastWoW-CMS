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


@router.get("/arena_top")
async def arena_top():
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
                sg = team_row.get("seasonGames") or 0
                sw = team_row.get("seasonWins") or 0
                wg = team_row.get("weekGames") or 0
                ww = team_row.get("weekWins") or 0
                team_row["seasonWinRatio"] = round((float(sw)/sg) if sg>0 else 0.0, 4)
                team_row["weekWinRatio"] = round((float(ww)/wg) if wg>0 else 0.0, 4)
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
                    members = []
            conn.close()
            await conn.wait_closed()
            return {"realm_id": realm_id, "name": name, "status": "ok", "team": team_row, "members": members}
        except Exception:
            return {"realm_id": realm_id, "name": name, "status": "offline", "team": None, "members": []}

    tasks = [fetch_team(r) for r in realms]
    results = await asyncio.gather(*tasks)
    return {"team_id": team_id, "realms": results}
