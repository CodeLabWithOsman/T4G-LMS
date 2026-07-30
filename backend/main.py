"""Tech4Girls LMS API entrypoint.

Fixes applied:
- CORS previously allowed only the three production pages.dev origins, so the
  frontend could not be run locally at all. Local dev origins are now allowed,
  and extra origins can be supplied via the CORS_ORIGINS env var.
- Added a global exception handler so an unexpected error returns clean JSON
  with a `detail` field (the shape the frontend parses) instead of an HTML 500
  page that broke error handling in the browser.
- Added explicit 401/422 handlers that also return `detail`.
- Added a /health endpoint.
"""

import logging
import os

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from database import Base, engine

# All model imports must come BEFORE create_all
from routes.admin_route import router as admin_router
from routes.announcement_route import router as announcement_router
from routes.courses_route import router as courses_router
from routes.enrollment_route import router as enrollment_router
from routes.material_route import router as material_router
from routes.notifications_route import router as notifications_router
from routes.staff_route import router as staff_router
from routes.students_route import router as students_router

# Import models explicitly so SQLAlchemy registers every table/column
import models.admin_model  # noqa: F401
import models.announcement_model  # noqa: F401
import models.course_model  # noqa: F401
import models.enrollment_model  # noqa: F401
import models.material_model  # noqa: F401
import models.notification_model  # noqa: F401
import models.staff_model  # noqa: F401
import models.student_model  # noqa: F401

logger = logging.getLogger("t4g")
logging.basicConfig(level=logging.INFO)

# NOW create tables - after all models are loaded
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Tech4Girls LMS API",
    description="A Learning Management System for Tech4Girls",
    version="1.1.0",
)


def _allowed_origins() -> list[str]:
    origins = [
        "https://t4g-lms.pages.dev",
        "https://admin-t4g-lms.pages.dev",
        "https://staff-t4g-lms.pages.dev",
        # Local development
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5500",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5500",
        "http://127.0.0.1:8000",
    ]
    extra = os.getenv("CORS_ORIGINS", "")
    for origin in extra.split(","):
        origin = origin.strip()
        if origin and origin not in origins:
            origins.append(origin)
    return origins


app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    # Allows Cloudflare Pages preview deployments (*.pages.dev) without having
    # to redeploy the API for every new preview URL.
    allow_origin_regex=r"https://.*\.pages\.dev",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

app.include_router(students_router)
app.include_router(courses_router)
app.include_router(admin_router)
app.include_router(staff_router)
app.include_router(enrollment_router)
app.include_router(material_router)
app.include_router(notifications_router)
app.include_router(announcement_router)


# --------------------------------------------------------------- error shape


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return a single readable message the frontend can display directly."""
    messages = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error.get("loc", []) if part != "body")
        message = error.get("msg", "Invalid value")
        messages.append(f"{location}: {message}" if location else message)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "; ".join(messages) or "Invalid request"},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Something went wrong on our end. Please try again."},
    )


# -------------------------------------------------------------------- health


@app.get("/")
def root():
    return {"message": "Welcome to Tech4Girls LMS API", "status": "ok"}


@app.get("/health")
def health():
    return {"status": "ok"}
