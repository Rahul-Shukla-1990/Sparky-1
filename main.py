from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.config import settings
from app.db import Base, engine
from app.api.auth import router as auth_router
from app.api.incidents import router as incidents_router
from app.api.sources import router as sources_router
from app.api.stats import router as stats_router
from app.api.social import router as social_router
from app.api.audit import router as audit_router
from app.api.clusters import router as clusters_router
from app.api.attachments import router as attachments_router
from app.api.api_catalogue import router as api_catalogue_router
from app.services.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title=settings.app_name, version="0.7.0", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(incidents_router)
app.include_router(sources_router)
app.include_router(stats_router)
app.include_router(social_router)
app.include_router(audit_router)
app.include_router(clusters_router)
app.include_router(attachments_router)
app.include_router(api_catalogue_router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/uploads", StaticFiles(directory="data/uploads"), name="uploads")

@app.get("/")
def dashboard():
    return FileResponse("app/static/index.html")

@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env, "version": "0.7.0"}
