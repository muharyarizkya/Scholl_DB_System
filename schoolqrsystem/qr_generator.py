import qrcode
import io
import base64
from datetime import datetime
import json

def generate_student_qr(student_data: dict) -> str:
    """
    Generate QR code for student containing student ID and timestamp
    """
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
    """
    Validate and parse QR code data
    """
    try:
        data = json.loads(qr_data)
        required_fields = ["student_id", "name", "timestamp"]
        
        if all(field in data for field in required_fields):
            return {"valid": True, "data": data}
        else:
            return {"valid": False, "error": "Invalid QR code format"}
    except json.JSONDecodeError:
        return {"valid": False, "error": "Invalid QR code data"}