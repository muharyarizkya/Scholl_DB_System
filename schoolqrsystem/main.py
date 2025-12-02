from fastapi import FastAPI, Depends, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Optional
import json
from datetime import datetime, timedelta
import io
import base64
import qrcode

# Database setup
from sqlalchemy import create_engine, Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

DATABASE_URL = "sqlite:///./school_management.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class StudentDB(Base):
    __tablename__ = "students"
    
    id = Column(String, primary_key=True, index=True)
    student_id = Column(String, unique=True, index=True)
    name = Column(String, index=True)
    class_name = Column(String)
    qr_code = Column(String, unique=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class AttendanceDB(Base):
    __tablename__ = "attendance"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, ForeignKey("students.student_id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="present")
    location = Column(String, nullable=True)
    
    student = relationship("StudentDB")

# Create tables
Base.metadata.create_all(bind=engine)

# FastAPI App
app = FastAPI(title="School Management System", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# QR Code Functions
def generate_student_qr(student_data: dict) -> str:
    """Generate QR code for student"""
    qr_data = {
        "student_id": student_data["student_id"],
        "name": student_data["name"],
        "timestamp": datetime.utcnow().isoformat()
    }
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    
    qr.add_data(json.dumps(qr_data))
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64 for web display
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return f"data:image/png;base64,{img_str}"

def validate_qr_code(qr_data: str) -> dict:
    """Validate and parse QR code data"""
    try:
        data = json.loads(qr_data)
        required_fields = ["student_id", "name", "timestamp"]
        
        if all(field in data for field in required_fields):
            return {"valid": True, "data": data}
        else:
            return {"valid": False, "error": "Invalid QR code format"}
    except json.JSONDecodeError:
        return {"valid": False, "error": "Invalid QR code data"}

# API Routes
@app.get("/")
def root():
    return {"message": "School Management System API is running"}

@app.post("/students/")
def create_student(student_id: str = Form(...), name: str = Form(...), class_name: str = Form(...), db: Session = Depends(get_db)):
    # Check if student ID already exists
    existing_student = db.query(StudentDB).filter(StudentDB.student_id == student_id).first()
    if existing_student:
        raise HTTPException(status_code=400, detail="Student ID already exists")
    
    # Generate QR code
    student_data = {
        "student_id": student_id,
        "name": name,
        "class_name": class_name
    }
    qr_code = generate_student_qr(student_data)
    
    # Create student record
    db_student = StudentDB(
        id=student_id,
        student_id=student_id,
        name=name,
        class_name=class_name,
        qr_code=qr_code
    )
    
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    
    return {
        "id": db_student.id,
        "student_id": db_student.student_id,
        "name": db_student.name,
        "class_name": db_student.class_name,
        "qr_code": db_student.qr_code,
        "is_active": db_student.is_active,
        "created_at": db_student.created_at
    }

@app.get("/students/")
def get_students(db: Session = Depends(get_db)):
    students = db.query(StudentDB).all()
    return students

@app.post("/qr/scan")
def scan_qr_code(qr_data: str = Form(...), location: str = Form("School"), db: Session = Depends(get_db)):
    # Validate QR code
    validation_result = validate_qr_code(qr_data)
    
    if not validation_result["valid"]:
        raise HTTPException(status_code=400, detail=validation_result["error"])
    
    qr_info = validation_result["data"]
    student_id = qr_info["student_id"]
    
    # Check if student exists
    student = db.query(StudentDB).filter(StudentDB.student_id == student_id).first()
    if not student:
        return {"success": False, "message": "Student not found"}
    
    if not student.is_active:
        return {"success": False, "message": "Student is not active"}
    
    # Check if attendance already recorded today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    existing_attendance = db.query(AttendanceDB).filter(
        AttendanceDB.student_id == student_id,
        AttendanceDB.timestamp >= today_start,
        AttendanceDB.timestamp < today_end
    ).first()
    
    if existing_attendance:
        return {"success": False, "message": "Attendance already recorded for today"}
    
    # Determine status based on time
    current_time = datetime.utcnow()
    late_threshold = current_time.replace(hour=8, minute=0, second=0, microsecond=0)
    
    status = "late" if current_time > late_threshold else "present"
    
    # Create attendance record
    db_attendance = AttendanceDB(
        student_id=student_id,
        status=status,
        location=location
    )
    
    db.add(db_attendance)
    db.commit()
    db.refresh(db_attendance)
    
    return {
        "success": True,
        "message": "Attendance recorded successfully",
        "student_name": student.name,
        "status": status,
        "timestamp": db_attendance.timestamp
    }

@app.get("/attendance/")
def get_attendance_records(db: Session = Depends(get_db)):
    attendance_records = db.query(AttendanceDB).order_by(AttendanceDB.timestamp.desc()).limit(50).all()
    
    result = []
    for record in attendance_records:
        student = db.query(StudentDB).filter(StudentDB.student_id == record.student_id).first()
        result.append({
            "id": record.id,
            "student_id": record.student_id,
            "student_name": student.name if student else "Unknown",
            "timestamp": record.timestamp,
            "status": record.status,
            "location": record.location
        })
    
    return result

@app.get("/dashboard")
def get_dashboard_stats(db: Session = Depends(get_db)):
    # Total students
    total_students = db.query(StudentDB).count()
    
    # Active students
    active_students = db.query(StudentDB).filter(StudentDB.is_active == True).count()
    
    # Today's attendance
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    today_attendance = db.query(AttendanceDB).filter(
        AttendanceDB.timestamp >= today_start,
        AttendanceDB.timestamp < today_end
    ).count()
    
    return {
        "total_students": total_students,
        "active_students": active_students,
        "today_attendance": today_attendance
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)