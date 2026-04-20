from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from services.enrollment_service import (
    get_enrollments_by_course,
    get_enrollments_by_student,
    enroll_student,
    unenroll_student
)
from schemas.enrollment_schema import EnrollmentCreate, EnrollmentResponse

router = APIRouter(prefix="/enrollments", tags=["Enrollments"])


@router.post("/", response_model=EnrollmentResponse)
def enroll(enrollment: EnrollmentCreate, db: Session = Depends(get_db)):
    result = enroll_student(db, enrollment)
    if not result:
        raise HTTPException(
            status_code=400, detail="Student already enrolled in this course")
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
    from models.enrollment_model import Enrollment
    from models.notification_model import Notification

    enrollment = db.query(Enrollment).filter(
        Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    enrollment.is_completed = True
    enrollment.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(enrollment)

    # Notify the student
    notif = Notification(
        student_id=enrollment.student_id,
        message="🎉 Congratulations! You have completed a course."
    )
    db.add(notif)
    db.commit()

    return {"message": "Course marked as complete"}
