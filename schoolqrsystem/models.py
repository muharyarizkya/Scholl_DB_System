from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

# SQLAlchemy Models
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

# Pydantic Models
class StudentCreate(BaseModel):
    student_id: str = Field(..., min_length=1, description="ID Siswa")
    name: str = Field(..., min_length=1, description="Nama lengkap")
    class_name: str = Field(..., description="Kelas")

class StudentOut(BaseModel):
    id: str
    student_id: str
    name: str
    class_name: str
    qr_code: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class AttendanceCreate(BaseModel):
    student_id: str
    location: Optional[str] = None

class AttendanceOut(BaseModel):
    id: int
    student_id: str
    student_name: str
    timestamp: datetime
    status: str
    location: Optional[str]
    
    class Config:
        from_attributes = True