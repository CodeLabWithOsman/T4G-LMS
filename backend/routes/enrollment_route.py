"""Enrollment routes.

Fixes applied:
- Added GET /enrollments/. The admin dashboard called this endpoint to build
  its stats; it did not exist, so the request 404'd and the counters stayed
  empty.
- Removed the emoji from the course-completion notification.
- Replaced deprecated datetime.utcnow() with timezone-aware datetimes.
- Marking an enrollment complete is now idempotent: completing an already
  completed enrollment no longer creates a duplicate notification.
- Moved model imports to module scope.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models.enrollment_model import Enrollment
from models.notification_model import Notification
from schemas.enrollment_schema import EnrollmentCreate, EnrollmentResponse
from services.enrollment_service import (
    enroll_student,
    get_enrollments_by_course,
    get_enrollments_by_student,
    unenroll_student,
)

router = APIRouter(prefix="/enrollments", tags=["Enrollments"])


@router.get("/", response_model=list[EnrollmentResponse])
def list_enrollments(db: Session = Depends(get_db)):
    """All enrollments. Used by the admin dashboard for its summary counters."""
    return db.query(Enrollment).all()


@router.post("/", response_model=EnrollmentResponse, status_code=status.HTTP_201_CREATED)
def enroll(enrollment: EnrollmentCreate, db: Session = Depends(get_db)):
    result = enroll_student(db, enrollment)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student is already enrolled in this course",
        )
    return result


@router.get("/course/{course_id}")
def get_course_enrollments(course_id: str, db: Session = Depends(get_db)):
    enrollments = get_enrollments_by_course(db, course_id)
    return {"course_id": course_id, "enrolled_students": len(enrollments)}


@router.get("/student/{student_id}")
def get_student_enrollments(student_id: str, db: Session = Depends(get_db)):
    return get_enrollments_by_student(db, student_id)


@router.delete("/")
def unenroll(student_id: str, course_id: str, db: Session = Depends(get_db)):
    result = unenroll_student(db, student_id, course_id)
    if not result:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    return {"message": "Student unenrolled successfully"}


@router.put("/{enrollment_id}/complete")
def mark_complete(enrollment_id: str, db: Session = Depends(get_db)):
    enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    if enrollment.is_completed:
        return {"message": "Course already marked as complete"}

    enrollment.is_completed = True
    enrollment.completed_at = datetime.now(timezone.utc)

    notification = Notification(
        student_id=enrollment.student_id,
        message="Congratulations. You have completed a course.",
    )
    db.add(notification)
    db.commit()
    db.refresh(enrollment)

    return {"message": "Course marked as complete"}
