from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base

# All model imports must come BEFORE create_all
from routes.students_route import router as students_router
from routes.courses_route import router as courses_router
from routes.admin_route import router as admin_router
from routes.staff_route import router as staff_router
from routes.enrollment_route import router as enrollment_router
from routes.material_route import router as material_router
from routes.notifications_route import router as notifications_router
from routes.announcement_route import router as announcement_router

# Import models explicitly so SQLAlchemy registers the new columns
import models.enrollment_model
import models.notification_model
import models.announcement_model

# NOW create tables — after all models are loaded
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Tech4Girls LMS API",
    description="A Learning Management System for Tech4Girls",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://t4g-lms.pages.dev",
        "https://admin-t4g-lms.pages.dev",
        "https://staff-t4g-lms.pages.dev"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(students_router)
app.include_router(courses_router)
app.include_router(admin_router)
app.include_router(staff_router)
app.include_router(enrollment_router)
app.include_router(material_router)
app.include_router(notifications_router)
app.include_router(announcement_router)


@app.get("/")
def root():
    return {"message": "Welcome to Tech4Girls LMS API"}
