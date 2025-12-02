from fastapi import FastAPI, Form, Depends, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship, Session, DeclarativeBase
from datetime import datetime, timedelta
import json
import base64
import io
import warnings

# Ignore deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Cek dan import qrcode
try:
    import qrcode
    QR_AVAILABLE = True
    print("✅ QRCode module successfully imported!")
except ImportError:
    QR_AVAILABLE = False
    print("⚠ QRCode module not available, using fallback")

# Database setup
DATABASE_URL = "sqlite:///./school.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Models Base
class Base(DeclarativeBase):
    pass

# Models
class Student(Base):
    __tablename__ = "students"
    
    id = Column(String, primary_key=True, index=True)
    student_id = Column(String, unique=True, index=True)
    name = Column(String)
    class_name = Column(String)
    qr_data = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Attendance(Base):
    __tablename__ = "attendance"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, ForeignKey("students.student_id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="present")
    location = Column(String)

# Create tables
Base.metadata.create_all(bind=engine)

# FastAPI app
app = FastAPI(title="School QR System")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# QR Code functions
def generate_qr_code(student_info: dict) -> str:
    """Generate QR code as base64 string"""
    try:
        if QR_AVAILABLE:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            
            qr_data = json.dumps(student_info)
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{img_str}"
        else:
            json_str = json.dumps(student_info)
            encoded = base64.b64encode(json_str.encode()).decode()
            return f"data:application/json;base64,{encoded}"
            
    except Exception as e:
        print(f"QR generation error: {e}")
        return f"text:{student_info['student_id']}:{student_info['name']}"

def parse_qr_data(qr_data: str) -> dict:
    """Parse QR code data"""
    try:
        if qr_data.startswith("data:image/png;base64,"):
            return {"valid": False, "error": "Cannot decode PNG QR images"}
        elif qr_data.startswith("data:application/json;base64,"):
            base64_str = qr_data.replace("data:application/json;base64,", "")
            json_str = base64.b64decode(base64_str).decode()
            data = json.loads(json_str)
            return {"valid": True, "data": data}
        elif qr_data.startswith("text:"):
            parts = qr_data.split(":")
            if len(parts) >= 3:
                return {
                    "valid": True, 
                    "data": {
                        "student_id": parts[1],
                        "name": parts[2],
                        "class_name": parts[3] if len(parts) > 3 else "Unknown"
                    }
                }
        data = json.loads(qr_data)
        return {"valid": True, "data": data}
    except Exception as e:
        return {"valid": False, "error": str(e)}

# API Routes
@app.get("/")
def root():
    return {
        "message": "School Management System", 
        "qr_available": QR_AVAILABLE,
        "status": "running"
    }

@app.post("/register")
def register_student(
    student_id: str = Form(...),
    name: str = Form(...),
    class_name: str = Form(...),
    db: Session = Depends(get_db)
):
    # Check if student exists
    existing = db.query(Student).filter(Student.student_id == student_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Student ID already exists")
    
    # Create student data
    student_info = {
        "student_id": student_id,
        "name": name,
        "class_name": class_name,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Generate QR code
    qr_code = generate_qr_code(student_info)
    
    # Save to database
    student = Student(
        id=student_id,
        student_id=student_id,
        name=name,
        class_name=class_name,
        qr_data=qr_code
    )
    
    db.add(student)
    db.commit()
    db.refresh(student)
    
    return {
        "success": True,
        "message": "Student registered successfully",
        "student": {
            "id": student.id,
            "name": student.name,
            "class_name": student.class_name,
            "qr_code": student.qr_data
        }
    }

# PRESENSI SEDERHANA - HANYA DENGAN ID SISWA
@app.post("/attendance-simple")
def record_attendance_simple(
    student_id: str = Form(...),
    location: str = Form("School"),
    db: Session = Depends(get_db)
):
    """Rekam presensi sederhana hanya dengan ID Siswa"""
    
    # Cari siswa berdasarkan ID
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        return {
            "success": False,
            "message": "❌ Siswa tidak ditemukan"
        }
    
    if not student.is_active:
        return {
            "success": False, 
            "message": "❌ Siswa tidak aktif"
        }
    
    # Cek apakah sudah presensi hari ini
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    existing_attendance = db.query(Attendance).filter(
        Attendance.student_id == student_id,
        Attendance.timestamp >= today_start,
        Attendance.timestamp < today_end
    ).first()
    
    if existing_attendance:
        return {
            "success": False,
            "message": "❌ Sudah presensi hari ini"
        }
    
    # Tentukan status (telat atau tepat waktu)
    current_time = datetime.now()
    late_threshold = current_time.replace(hour=8, minute=0, second=0)
    status = "late" if current_time > late_threshold else "present"
    
    # Rekam presensi
    attendance = Attendance(
        student_id=student_id,
        status=status,
        location=location
    )
    
    db.add(attendance)
    db.commit()
    
    return {
        "success": True,
        "message": "✅ Presensi berhasil dicatat",
        "student_name": student.name,
        "student_id": student.student_id,
        "class_name": student.class_name,
        "status": status,
        "time": current_time.strftime("%H:%M:%S"),
        "date": current_time.strftime("%Y-%m-%d"),
        "location": location
    }

# Endpoint QR lama (tetap ada untuk kompatibilitas)
@app.post("/attendance")
def record_attendance(
    qr_data: str = Form(...),
    location: str = Form("School"),
    db: Session = Depends(get_db)
):
    result = parse_qr_data(qr_data)
    if not result["valid"]:
        return {"success": False, "message": result["error"]}
    
    student_info = result["data"]
    student_id = student_info["student_id"]
    
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        return {"success": False, "message": "Student not found"}
    
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    existing = db.query(Attendance).filter(
        Attendance.student_id == student_id,
        Attendance.timestamp >= today_start,
        Attendance.timestamp < today_end
    ).first()
    
    if existing:
        return {"success": False, "message": "Already attended today"}
    
    current_time = datetime.now()
    late_time = current_time.replace(hour=8, minute=0, second=0)
    status = "late" if current_time > late_time else "present"
    
    attendance = Attendance(
        student_id=student_id,
        status=status,
        location=location
    )
    
    db.add(attendance)
    db.commit()
    
    return {
        "success": True,
        "message": "Attendance recorded",
        "student_name": student.name,
        "status": status,
        "time": current_time.strftime("%H:%M:%S"),
        "location": location
    }

@app.get("/students")
def get_students(db: Session = Depends(get_db)):
    students = db.query(Student).all()
    return {
        "success": True,
        "students": [
            {
                "id": s.id,
                "student_id": s.student_id,
                "name": s.name,
                "class_name": s.class_name,
                "is_active": s.is_active
            } for s in students
        ]
    }

@app.get("/attendance-records")
def get_attendance(db: Session = Depends(get_db)):
    records = db.query(Attendance).order_by(Attendance.timestamp.desc()).limit(20).all()
    
    result = []
    for record in records:
        student = db.query(Student).filter(Student.student_id == record.student_id).first()
        result.append({
            "id": record.id,
            "student_id": record.student_id,
            "student_name": student.name if student else "Unknown",
            "timestamp": record.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "status": record.status,
            "location": record.location
        })
    
    return {"success": True, "attendance": result}

@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    total_students = db.query(Student).count()
    active_students = db.query(Student).filter(Student.is_active == True).count()
    
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_attendance = db.query(Attendance).filter(Attendance.timestamp >= today_start).count()
    
    return {
        "success": True,
        "stats": {
            "total_students": total_students,
            "active_students": active_students,
            "today_attendance": today_attendance
        }
    }

# ==================== ENDPOINT QR CODE GAMBAR ====================
@app.get("/qrcode/{student_id}")
def get_qr_code(student_id: str, db: Session = Depends(get_db)):
    """Download QR Code dalam bentuk gambar PNG"""
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Generate QR code sebagai file PNG
    try:
        import qrcode
        from io import BytesIO
        
        # Data untuk QR code
        qr_data = {
            "student_id": student.student_id,
            "name": student.name,
            "class_name": student.class_name,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        
        qr.add_data(json.dumps(qr_data))
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Simpan ke buffer
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        
        # Return sebagai file download
        return Response(
            content=buffer.getvalue(),
            media_type="image/png",
            headers={
                "Content-Disposition": f"attachment; filename=qr_{student_id}.png"
            }
        )
        
    except ImportError:
        raise HTTPException(status_code=500, detail="QR code generation not available")

@app.get("/qrcode-view/{student_id}")
def view_qr_code(student_id: str, db: Session = Depends(get_db)):
    """Lihat QR Code langsung di browser"""
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    try:
        import qrcode
        from io import BytesIO
        
        qr_data = {
            "student_id": student.student_id,
            "name": student.name,
            "class_name": student.class_name,
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
        
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        
        return Response(content=buffer.getvalue(), media_type="image/png")
        
    except ImportError:
        raise HTTPException(status_code=500, detail="QR code generation not available")

@app.get("/student/{student_id}")
def get_student_detail(student_id: str, db: Session = Depends(get_db)):
    """Get detailed student information"""
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Get attendance history for this student
    attendance_records = db.query(Attendance).filter(
        Attendance.student_id == student_id
    ).order_by(Attendance.timestamp.desc()).limit(10).all()
    
    attendance_list = []
    for record in attendance_records:
        attendance_list.append({
            "timestamp": record.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "status": record.status,
            "location": record.location
        })
    
    return {
        "success": True,
        "student": {
            "id": student.id,
            "student_id": student.student_id,
            "name": student.name,
            "class_name": student.class_name,
            "is_active": student.is_active,
            "created_at": student.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "attendance_history": attendance_list,
            "total_attendance": len(attendance_list)
        }
    }

# Endpoint untuk update status siswa
@app.post("/student/{student_id}/toggle")
def toggle_student_status(student_id: str, db: Session = Depends(get_db)):
    """Toggle active/inactive status of student"""
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    student.is_active = not student.is_active
    db.commit()
    
    return {
        "success": True,
        "message": f"Student status updated to {'active' if student.is_active else 'inactive'}",
        "is_active": student.is_active
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)