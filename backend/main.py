from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel

from db import db_pools, fetch_one, execute
from db import fetch_all
import hashlib
import secrets
from typing import Optional
import time
import jwt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import aiomysql
import asyncio

from config import JWT_SECRET, JWT_ALGORITHM, JWT_EXP_SECONDS

app = FastAPI(title="FastWoW CMS Backend")

security = HTTPBearer()


class HealthResponse(BaseModel):
	status: str
	details: dict


class RegisterRequest(BaseModel):
	username: str
	password: str
	email: Optional[str] = None


class LoginRequest(BaseModel):
	username: str
	password: str


def _create_jwt(payload: dict) -> str:
	now = int(time.time())
	data = {"iat": now, "exp": now + JWT_EXP_SECONDS, **payload}
	token = jwt.encode(data, JWT_SECRET, algorithm=JWT_ALGORITHM)
	# PyJWT returns str in newer versions; ensure string
	if isinstance(token, bytes):
		token = token.decode("utf-8")
	return token


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
	token = credentials.credentials
	try:
		payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
		# validate that session in token matches cms.account.session
		username = payload.get("username")
		token_session = payload.get("session")
		if not username or not token_session:
			raise HTTPException(status_code=401, detail="Invalid token payload")

		try:
			row = await fetch_one("cms", "SELECT session FROM account WHERE username = %s", (username,))
		except Exception as e:
			raise HTTPException(status_code=500, detail=f"DB error validating session: {e}")

		if not row:
			raise HTTPException(status_code=401, detail="Invalid session")

		db_session = row.get("session")
		db_session_hex = None
		if db_session is not None:
			# db_session is binary; convert to hex for comparison
			try:
				db_session_hex = db_session.hex()
			except Exception:
				# fallback: attempt decode/str
				db_session_hex = str(db_session)

		if db_session_hex != token_session:
			raise HTTPException(status_code=401, detail="Session mismatch or expired")

		return payload
	except jwt.ExpiredSignatureError:
		raise HTTPException(status_code=401, detail="Token expired")
	except jwt.InvalidTokenError:
		raise HTTPException(status_code=401, detail="Invalid token")


def _compute_verifier(username: str, password: str):
	"""Compute AzerothCore SRP verifier and salt.

	Returns (salt_bytes, verifier_bytes).
	"""
	# constants
	g = 7
	N = int("894B645E89E1535BBDAD5B8B290650530801B18EBFBF5E8FAB3C82872A3E9BB7", 16)

	# username and password uppercase
	user_up = username.upper()
	pass_up = password.upper()

	# h1 = SHA1("USERNAME:PASSWORD") where both are uppercase, and result is binary
	h1_input = f"{user_up}:{pass_up}".encode("utf-8")
	h1 = hashlib.sha1(h1_input).digest()

	# salt is 32 random bytes
	salt = secrets.token_bytes(32)

	# h2 = SHA1(salt || h1)
	h2 = hashlib.sha1(salt + h1).digest()

	# interpret h2 as little-endian integer
	h2_int = int.from_bytes(h2, byteorder="little")

	# compute verifier = (g ^ h2) % N
	v_int = pow(g, h2_int, N)

	# convert to little-endian byte array of length 32 (schema BINARY(32))
	# N is smaller than 2^(32*8) so v_int fits into 32 bytes
	v_bytes = v_int.to_bytes(32, byteorder="little")

	return salt, v_bytes


@app.on_event("startup")
async def startup_event():
	# initialize DB pools for cms, auth, characters, world
	await db_pools.init_pools()


@app.on_event("shutdown")
async def shutdown_event():
	await db_pools.close_pools()


@app.get("/", response_model=dict)
async def root():
	return {"ok": True, "service": "FastWoW CMS Backend"}


@app.get("/db/health", response_model=HealthResponse)
async def db_health():
	details = {}
	problems = 0
	for key in ("cms", "auth", "characters", "world"):
		try:
			row = await fetch_one(key, "SELECT 1 as ok")
			healthy = bool(row and row.get("ok") == 1)
			details[key] = "ok" if healthy else "bad"
			if not healthy:
				problems += 1
		except Exception as e:
			details[key] = f"error: {e}"
			problems += 1
	status = "ok" if problems == 0 else "degraded"
	return HealthResponse(status=status, details=details)


# Example endpoint showing simple read from cms (adjust to your schema)
@app.get("/cms/siteinfo")
async def get_site_info():
	try:
		row = await fetch_one("cms", "SELECT name, value FROM site_config LIMIT 1")
		if not row:
			raise HTTPException(status_code=404, detail="No site config found")
		return row
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


@app.post("/register")
async def register(req: RegisterRequest):
	username = req.username
	password = req.password
	email = req.email or ""

	if not username or len(username) > 20:
		raise HTTPException(status_code=400, detail="Invalid username (required, max 20 chars)")
	if not password or len(password) < 4:
		raise HTTPException(status_code=400, detail="Password too short (min 4 chars)")

	# check if account exists in auth
	try:
		existing = await fetch_one("auth", "SELECT id FROM account WHERE username = %s", (username,))
		if existing:
			raise HTTPException(status_code=400, detail="Account already exists")
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"DB error checking account: {e}")

	# compute salt and verifier
	try:
		salt, verifier = _compute_verifier(username, password)
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to compute verifier: {e}")

	# insert into auth.account
	try:
		# store binary verifier and salt directly using schema fields 'verifier' and 'salt'
		auth_q = "INSERT INTO account (username, verifier, salt, email) VALUES (%s, %s, %s, %s)"
		rows_auth, _ = await execute("auth", auth_q, (username, verifier, salt, email))
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to create auth account: {e}")

	# insert into cms.account; if fails, delete auth row to rollback
	try:
		cms_q = "INSERT INTO account (username, credits, vote_points, last_login, session) VALUES (%s, %s, %s, NULL, NULL)"
		await execute("cms", cms_q, (username, 0, 0))
	except Exception as e:
		# attempt rollback on auth
		try:
			await execute("auth", "DELETE FROM account WHERE username = %s", (username,))
		except Exception:
			pass
		raise HTTPException(status_code=500, detail=f"Failed to create cms account (rolled back auth): {e}")

	return {"ok": True, "username": username}


@app.post("/login")
async def login(req: LoginRequest):
	username = req.username
	password = req.password

	if not username or not password:
		raise HTTPException(status_code=400, detail="username and password required")

	try:
		row = await fetch_one("auth", "SELECT id, username, verifier, salt FROM account WHERE username = %s", (username,))
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"DB error: {e}")

	if not row:
		raise HTTPException(status_code=401, detail="Invalid credentials")

	stored_verifier = row.get("verifier")
	stored_salt = row.get("salt")

	if stored_verifier is None or stored_salt is None:
		raise HTTPException(status_code=500, detail="Account missing verifier/salt")

	# recompute verifier from provided password and stored salt
	try:
		# h1 = SHA1(UPPER(USER):UPPER(PASS))
		h1_input = f"{username.upper()}:{password.upper()}".encode("utf-8")
		h1 = hashlib.sha1(h1_input).digest()
		h2 = hashlib.sha1(stored_salt + h1).digest()
		h2_int = int.from_bytes(h2, byteorder="little")
		g = 7
		N = int("894B645E89E1535BBDAD5B8B290650530801B18EBFBF5E8FAB3C82872A3E9BB7", 16)
		v_int = pow(g, h2_int, N)
		v_bytes = v_int.to_bytes(32, byteorder="little")
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to compute verifier: {e}")

	if v_bytes != stored_verifier:
		raise HTTPException(status_code=401, detail="Invalid credentials")

	# success: create session_key and store it in cms.account.session only
	session_key = secrets.token_bytes(40)
	try:
		await execute("cms", "UPDATE account SET session = %s, last_login = CURRENT_TIMESTAMP WHERE username = %s", (session_key, username))
	except Exception:
		pass

	# include session hex in JWT payload so we can validate against cms.account.session
	session_hex = session_key.hex()
	token = _create_jwt({"sub": row.get("id"), "username": username, "session": session_hex})
	return {"access_token": token, "token_type": "bearer"}


@app.post("/logout")
async def logout(user: dict = Depends(get_current_user)):
	"""Invalidate web session by removing cms.account.session for the logged user."""
	username = user.get("username")
	if not username:
		raise HTTPException(status_code=400, detail="Invalid token payload")

	try:
		await execute("cms", "UPDATE account SET session = NULL WHERE username = %s", (username,))
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"DB error clearing session: {e}")

	return {"ok": True}


@app.get("/realm_status")
async def realm_status():
	"""
	Public endpoint returning status for all realms.

	Assumptions:
	- There is a `cms.realms` table with columns:
		id, realm_id, name,
		char_db_host, char_db_port, char_db_user, char_db_password, char_db_name
	  (If your schema differs, adapt the column names accordingly.)
	- `auth.realmlist` contains realm information and `auth.uptime` stores uptime per realm (lookup by realm_id).
	- characters DB has table `characters` with `online` (1) and `race` integer columns.
	"""

	# race -> faction mapping from your spec (Alliance vs Horde)
	alliance_races = {1, 3, 4, 7, 11}
	horde_races = {2, 5, 6, 8, 10}

	# fetch realms from cms
	try:
		realms = await fetch_all("cms", "SELECT id, realm_id, name, char_db_host, char_db_port, char_db_user, char_db_password, char_db_name FROM realms")
	except Exception:
		# fallback: try auth.realmlist if cms.realms not available
		try:
			realms = await fetch_all("auth", "SELECT id as id, id as realm_id, name, NULL as char_db_host, NULL as char_db_port, NULL as char_db_user, NULL as char_db_password, NULL as char_db_name FROM realmlist")
		except Exception as e:
			raise HTTPException(status_code=500, detail=f"Failed to list realms: {e}")

	if not realms:
		return {"realms": []}

	async def process_realm(r):
		realm_id = r.get("realm_id")
		name = r.get("name") or f"realm-{realm_id}"

		# uptime from auth.uptime (assume column realm_id and uptime seconds)
		uptime = None
		try:
			up_row = await fetch_one("auth", "SELECT uptime FROM uptime WHERE realm_id = %s", (realm_id,))
			if up_row:
				uptime = up_row.get("uptime")
		except Exception:
			uptime = None

		# default counts
		total_online = 0
		alliance = 0
		horde = 0

		host = r.get("char_db_host")
		port = r.get("char_db_port") or 3306
		user = r.get("char_db_user")
		password = r.get("char_db_password")
		dbname = r.get("char_db_name")

		if host and user and dbname:
			# try to connect to the characters DB for this realm
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
							# unknown races count toward total but not faction
							pass

				conn.close()
				await conn.wait_closed()
			except Exception:
				# realm appears offline or unreachable
				return {"id": realm_id, "name": name, "online": 0, "alliance": 0, "horde": 0, "uptime": uptime, "status": "offline"}
		else:
			# no connection info; mark as unknown/offline
			return {"id": realm_id, "name": name, "online": 0, "alliance": 0, "horde": 0, "uptime": uptime, "status": "no_connection_info"}

		return {"id": realm_id, "name": name, "online": total_online, "alliance": alliance, "horde": horde, "uptime": uptime, "status": "online"}

	tasks = [process_realm(r) for r in realms]
	results = await asyncio.gather(*tasks)

	return {"realms": results}


@app.get("/online")
async def online_all(limit_per_realm: Optional[int] = 200, page: int = 1, page_size: int = 50):
	"""Return online characters grouped by realm (only realms that are reachable/online).

	Pagination params (applied per-realm):
	- page (1-based)
	- page_size (max 500)

	If `page`/`page_size` are provided, they take precedence over `limit_per_realm`.
	Uses connection info stored in `cms.realms` to query each realm's characters DB.
	"""
	# sanitize pagination
	if page < 1:
		page = 1
	if page_size < 1:
		page_size = 1
	MAX_PAGE_SIZE = 500
	if page_size > MAX_PAGE_SIZE:
		page_size = MAX_PAGE_SIZE
	# fetch realms that have connection info
	try:
		realms = await fetch_all("cms", "SELECT realm_id, name, char_db_host, char_db_port, char_db_user, char_db_password, char_db_name FROM realms")
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to read realms from CMS: {e}")

	if not realms:
		return {"realms": []}

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

		# compute offsets/limits
		use_pagination = True
		if not page or not page_size:
			use_pagination = False

		try:
			conn = await aiomysql.connect(host=host, port=int(port), user=user, password=password or "", db=dbname)
			async with conn.cursor(aiomysql.DictCursor) as cur:
				# total count
				await cur.execute("SELECT COUNT(*) AS cnt FROM characters WHERE online = 1")
				rcount = await cur.fetchone()
				total = int(rcount.get("cnt") or 0)

				if use_pagination:
					offset = (page - 1) * page_size
					limit = page_size
				else:
					offset = 0
					limit = int(limit_per_realm or 200)

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
			out.append({
				"guid": int(row.get("guid") or 0),
				"name": row.get("name"),
				"race": int(row.get("race") or 0),
				"class": int(row.get("class") or 0),
				"gender": int(row.get("gender") or 0),
				"level": int(row.get("level") or 0),
				"guild": row.get("guild_name"),
			})

		pagination = {"page": page, "page_size": limit, "total": total}
		return {"realm_id": realm_id, "name": name, "status": "online", "pagination": pagination, "characters": out}

	tasks = [fetch_chars_for_realm(r) for r in realms]
	results = await asyncio.gather(*tasks)

	# filter only realms that are online (status == 'online')
	online_realms = [r for r in results if r.get("status") == "online"]

	return {"realms": online_realms}

