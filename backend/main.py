from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from db import db_pools, fetch_one
from api.auth import router as auth_router
from api.online import router as online_router
from api.toppvp import router as toppvp_router
from api.news import router as news_router
from api.forum import router as forum_router
from api.profile import router as profile_router
from api.armory import router as armory_router
from api.shop import router as shop_router

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
app.include_router(news_router)
app.include_router(forum_router)
app.include_router(profile_router)
app.include_router(armory_router)
app.include_router(shop_router)


@app.get("/", response_model=dict)
async def root():
    return {"ok": True, "service": "FastWoW CMS Backend"}
