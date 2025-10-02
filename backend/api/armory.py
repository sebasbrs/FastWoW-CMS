from fastapi import APIRouter, HTTPException
from db import fetch_one
import aiomysql

router = APIRouter(prefix="/armory", tags=["armory"])

SLOT_NAMES = {
    0: "head",
    1: "neck",
    2: "shoulder",
    3: "shirt",
    4: "chest",
    5: "waist",
    6: "legs",
    7: "feet",
    8: "wrist",
    9: "hands",
    10: "finger1",
    11: "finger2",
    12: "trinket1",
    13: "trinket2",
    14: "back",
    15: "mainhand",
    16: "offhand",
    17: "relic",
    18: "tabard",
}

POWER_KEYS = [
    ("power1", "mana"),
    ("power2", "rage"),
    ("power3", "focus"),
    ("power4", "energy"),
    ("power5", "happiness"),
    ("power6", "runes"),
    ("power7", "runic_power"),
]

@router.get('/{realm_id}/{guid}')
async def character_armory(realm_id: int, guid: int):
    # Obtener datos de conexión del realm
    realm = await fetch_one('cms', 'SELECT realm_id, name, char_db_host, char_db_port, char_db_user, char_db_password, char_db_name FROM realms WHERE realm_id = %s', (realm_id,))
    if not realm:
        raise HTTPException(status_code=404, detail='Realm no encontrado')
    host = realm.get('char_db_host')
    port = realm.get('char_db_port') or 3306
    user = realm.get('char_db_user')
    password = realm.get('char_db_password') or ''
    dbname = realm.get('char_db_name')
    if not host or not user or not dbname:
        raise HTTPException(status_code=503, detail='Realm sin datos de conexión')

    try:
        conn = await aiomysql.connect(host=host, port=int(port), user=user, password=password, db=dbname)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f'No se pudo conectar al realm: {e}')

    character = None
    equipment_sets = []
    arena_teams = []
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # Datos básicos del personaje (column names may vary slightly per core; adjust if needed)
            try:
                await cur.execute('SELECT guid, name, level, race, class, gender, health, power1, power2, power3, power4, power5, power6, power7, totalKills, todayKills, yesterdayKills FROM characters WHERE guid = %s', (guid,))
            except Exception:
                # fallback sin algunas columnas de poder si difiere
                await cur.execute('SELECT guid, name, level, race, class, gender, health, totalKills, todayKills, yesterdayKills FROM characters WHERE guid = %s', (guid,))
            row = await cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail='Personaje no encontrado')
            powers = {}
            for col, label in POWER_KEYS:
                if col in row:
                    powers[label] = row.get(col)
            character = {
                'guid': row.get('guid'),
                'name': row.get('name'),
                'level': row.get('level'),
                'race': row.get('race'),
                'class': row.get('class'),
                'gender': row.get('gender'),
                'health': row.get('health'),
                'powers': powers,
                'totalKills': row.get('totalKills'),
                'todayKills': row.get('todayKills'),
                'yesterdayKills': row.get('yesterdayKills'),
            }
            # Equipment sets
            try:
                await cur.execute('SELECT * FROM character_equipmentsets WHERE guid = %s ORDER BY setindex ASC', (guid,))
                eq_rows = await cur.fetchall()
                if eq_rows:
                    for eq in eq_rows:
                        # typical structure has item0..item18
                        slots = []
                        for slot_id in range(0, 19):
                            col = f'item{slot_id}'
                            if col in eq:
                                item_guid = eq.get(col)
                                if item_guid and int(item_guid) != 0:
                                    slots.append({'slot_id': slot_id, 'slot_name': SLOT_NAMES.get(slot_id, f'slot_{slot_id}'), 'item_guid': item_guid})
                        equipment_sets.append({
                            'setguid': eq.get('setguid'),
                            'index': eq.get('setindex'),
                            'name': eq.get('name'),
                            'icon': eq.get('iconname'),
                            'ignore_mask': eq.get('ignore_mask'),
                            'slots': slots
                        })
            except Exception:
                equipment_sets = []
            # Arena teams del personaje
            try:
                await cur.execute('SELECT atm.arenaTeamId, at.name, at.type, atm.personalRating, atm.seasonGames, atm.seasonWins, atm.weekGames, atm.weekWins FROM arena_team_member atm JOIN arena_team at ON at.arenaTeamId = atm.arenaTeamId WHERE atm.guid = %s', (guid,))
                team_rows = await cur.fetchall()
                if team_rows:
                    for t in team_rows:
                        sg = t.get('seasonGames') or 0
                        sw = t.get('seasonWins') or 0
                        wg = t.get('weekGames') or 0
                        ww = t.get('weekWins') or 0
                        arena_teams.append({
                            'id': t.get('arenaTeamId'),
                            'name': t.get('name'),
                            'type': t.get('type'),
                            'personalRating': t.get('personalRating'),
                            'seasonGames': sg,
                            'seasonWins': sw,
                            'seasonWinRatio': round((float(sw)/sg) if sg>0 else 0.0, 4),
                            'weekGames': wg,
                            'weekWins': ww,
                            'weekWinRatio': round((float(ww)/wg) if wg>0 else 0.0, 4),
                        })
            except Exception:
                arena_teams = []
    finally:
        conn.close()
        try:
            await conn.wait_closed()
        except Exception:
            pass

    return {
        'realm_id': realm_id,
        'realm_name': realm.get('name'),
        'character': character,
        'equipment_sets': equipment_sets,
        'arena_teams': arena_teams
    }
