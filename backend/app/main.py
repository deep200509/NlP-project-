from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.agent.repair_routes import router as repair_router
from app.agent.routes import router as agent_router
from app.auth.routes import router as auth_router
from app.auth.security import get_current_user
from app.code_generator.routes import router as codegen_router
from app.config import APP_NAME, APP_VERSION
from app.database import models  # noqa: F401  (importing registers the tables)
from app.database.database import Base, engine
from app.nlp.routes import router as nlp_router
from app.projects.dashboard import router as dashboard_router
from app.projects.extras import router as project_extras_router
from app.projects.routes import router as projects_router
from app.specification.routes import router as spec_router
from app.testing.routes import router as testing_router

# creates users, conversations, messages, projects and test_results if they do not exist
Base.metadata.create_all(bind=engine)

app = FastAPI(title=APP_NAME, version=APP_VERSION)

# lets the React frontend (port 5173) call this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

login_required = [Depends(get_current_user)]

app.include_router(auth_router)                                  # Phase 7: register / login
app.include_router(projects_router)                              # Phase 7: saved projects (login inside)
app.include_router(agent_router)                                 # Phase 8: chat agent (login inside)
app.include_router(repair_router)                                # Phase 9: self-repair loop (login inside)
app.include_router(dashboard_router)                             # Phase 10: dashboard numbers (login inside)
app.include_router(project_extras_router)                        # Phase 10: file viewer, regenerate (login inside)
app.include_router(nlp_router)                                   # Phase 2-3: analysis only, stays open for demos
app.include_router(spec_router)                                  # Phase 4: analysis only, stays open for demos
app.include_router(codegen_router, dependencies=login_required)  # Phase 5: writes files -> login required
app.include_router(testing_router, dependencies=login_required)  # Phase 6: runs code   -> login required


@app.get("/")
def root():
    return {"message": f"{APP_NAME} is running", "docs": "/docs"}


@app.get("/health")
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))  # proves the DB is reachable
    return {"status": "ok", "database": "connected", "version": APP_VERSION}