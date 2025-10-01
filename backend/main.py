from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from db import db_pools, fetch_one
from api.auth import router as auth_router
from api.online import router as online_router
from api.toppvp import router as toppvp_router

app = FastAPI(title="FastWoW CMS Backend")


class HealthResponse(BaseModel):
    status: str
    details: dict


@app.on_event("startup")
async def startup_event():
    await db_pools.init_pools()


@app.on_event("shutdown")
async def shutdown_event():
    await db_pools.close_pools()


# mount modular routers
app.include_router(auth_router)
app.include_router(online_router)
app.include_router(toppvp_router)


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


@app.get("/cms/siteinfo")
async def get_site_info():
    try:
        row = await fetch_one("cms", "SELECT name, value FROM site_config LIMIT 1")
        if not row:
            raise HTTPException(status_code=404, detail="No site config found")
        return row
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

