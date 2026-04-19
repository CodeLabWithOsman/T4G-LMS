from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from auth import verify_password, create_access_token, hash_password, get_current_user
from fastapi.security import OAuth2PasswordBearer
from database import get_db
from models.student_model import Student
from services.student_service import (
    get_all_students,
    get_student_by_id,
    create_student,
    delete_student,
    search_students
)
from schemas.student_schema import StudentCreate, StudentResponse, StudentLogin, ChangePassword, ForgotPassword, ResetPassword
from pydantic import EmailStr
from auth import verify_password, create_access_token


router = APIRouter(prefix="/students", tags=["Students"])


@router.get("/", response_model=list[StudentResponse])
def read_students(db: Session = Depends(get_db)):
    return get_all_students(db)


@router.get("/search")
def search_students_route(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db)
):
    results = search_students(db, q)
    return results


@router.post("/", response_model=StudentResponse)
def add_student(student: StudentCreate, db: Session = Depends(get_db)):
    return create_student(db, student)


@router.post("/login")
def login_student(student: StudentLogin, db: Session = Depends(get_db)):
    db_student = db.query(Student).filter(
        Student.email == student.email).first()
    if not db_student:
        raise HTTPException(status_code=404, detail="Student not found")
    if not verify_password(student.password, db_student.password):
        raise HTTPException(status_code=401, detail="Incorrect password")
    token = create_access_token(
        data={"sub": db_student.email, "role": "student"})
    return {
        "access_token": token,
        "token_type": "bearer",
        "student": {
            "id": db_student.id,
            "first_name": db_student.first_name,
            "last_name": db_student.last_name,
            "email": db_student.email,
            "student_id": db_student.student_id,
            "track": db_student.track,
            "is_default_password": db_student.is_default_password
        }
    }


@router.put("/change-password")
def change_password(
    passwords: ChangePassword,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    student = db.query(Student).filter(Student.email == current_user).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if not verify_password(passwords.current_password, student.password):
        raise HTTPException(
            status_code=401, detail="Current password is incorrect")
    student.password = hash_password(passwords.new_password)
    student.is_default_password = False
    db.commit()
    return {"message": "Password changed successfully"}


@router.post("/forgot-password")
def forgot_password(data: ForgotPassword, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.email == data.email).first()
    if not student:
        raise HTTPException(
            status_code=404, detail="No account found with this email")
    return {"message": "Email found", "email": data.email}


@router.post("/reset-password")
def reset_password(data: ResetPassword, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.email == data.email).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    student.password = hash_password(data.new_password)
    student.is_default_password = False
    db.commit()
    return {"message": "Password reset successfully"}


@router.get("/{student_id}", response_model=StudentResponse)
def read_student(student_id: str, db: Session = Depends(get_db)):
    student = get_student_by_id(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.delete("/{student_id}")
def remove_student(student_id: str, db: Session = Depends(get_db)):
    student = delete_student(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return {"message": "Student deleted successfully"}



