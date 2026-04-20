from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.notification_model import Notification
from schemas.notification_schema import NotificationCreate, NotificationResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/student/{student_id}", response_model=list[NotificationResponse])
def get_student_notifications(student_id: str, db: Session = Depends(get_db)):
    return db.query(Notification).filter(
        Notification.student_id == student_id
    ).order_by(Notification.created_at.desc()).all()


@router.post("/", response_model=NotificationResponse)
def create_notification(data: NotificationCreate, db: Session = Depends(get_db)):
    notif = Notification(student_id=data.student_id, message=data.message)
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif


@router.put("/{notif_id}/read")
def mark_as_read(notif_id: str, db: Session = Depends(get_db)):
    notif = db.query(Notification).filter(Notification.id == notif_id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    db.commit()
    return {"message": "Marked as read"}


@router.put("/student/{student_id}/read-all")
def mark_all_read(student_id: str, db: Session = Depends(get_db)):
    db.query(Notification).filter(
        Notification.student_id == student_id,
        Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return {"message": "All marked as read"}
