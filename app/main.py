from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api import analytics_router, assistant_router, query_router, admin_router
from app.db.database import connect_db, close_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()

app = FastAPI(
    title="Acme Financial Data Warehouse",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(assistant_router)
app.include_router(query_router)
app.include_router(analytics_router)
app.include_router(admin_router)

@app.get("/health")
async def health():
    return {"status": "ok"}