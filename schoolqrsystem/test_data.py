import json
from datetime import datetime
import urllib.request
import urllib.parse

BASE_URL = "http://127.0.0.1:8000"

# Data siswa untuk testing
students = [
    {"student_id": "IF001", "name": "Elsa Khairunisa", "class_name": "XII IPA 1"},
    {"student_id": "IF002", "name": "Ahmad Fauzi", "class_name": "XII IPA 2"},
    {"student_id": "IF003", "name": "Siti Rahma", "class_name": "XII IPS 1"},
    {"student_id": "IF004", "name": "Budi Santoso", "class_name": "XII IPA 1"},
    {"student_id": "IF005", "name": "Maya Sari", "class_name": "XII IPS 2"}
]

def register_students():
    """Daftarkan siswa ke sistem"""
    print("Mendaftarkan siswa...")
    for student in students:
        try:
            # Prepare form data
            data = urllib.parse.urlencode(student).encode()
            
            # Create request
            req = urllib.request.Request(
                f"{BASE_URL}/register",
                data=data,
                method='POST'
            )
            
            # Send request
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode())
                
            if result["success"]:
                print(f"✅ {student['name']} berhasil didaftarkan")
            else:
                print(f"❌ {student['name']} gagal: {result['message']}")
                
        except Exception as e:
            print(f"❌ Error mendaftarkan {student['name']}: {e}")

def generate_qr_data():
    """Generate data QR code untuk testing"""
    print("\n📱 Data QR Code untuk testing:")
    print("=" * 60)
    
    for student in students:
        qr_data = {
            "student_id": student["student_id"],
            "name": student["name"],
            "class_name": student["class_name"],
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"\n👤 {student['name']} ({student['student_id']}):")
        print(json.dumps(qr_data))
        print("-" * 40)

def record_attendance():
    """Rekam presensi secara otomatis"""
    print("\n📝 Merekam presensi...")
    
    attendance_data = [
        {"student_id": "IF001", "time": "07:55:00", "status": "present"},
        {"student_id": "IF002", "time": "08:05:00", "status": "present"},
        {"student_id": "IF003", "time": "08:15:00", "status": "late"},
        {"student_id": "IF004", "time": "08:25:00", "status": "late"},
        {"student_id": "IF005", "time": "08:35:00", "status": "late"}
    ]
    
    for attn in attendance_data:
        # Find student data
        student = next((s for s in students if s["student_id"] == attn["student_id"]), None)
        if not student:
            print(f"❌ Student {attn['student_id']} tidak ditemukan")
            continue
            
        qr_data = {
            "student_id": attn["student_id"],
            "name": student["name"],
            "class_name": student["class_name"],
            "timestamp": f"2024-01-15T{attn['time']}.000Z"
        }
        
        try:
            # Prepare form data
            form_data = urllib.parse.urlencode({
                "qr_data": json.dumps(qr_data),
                "location": "Gerbang Sekolah"
            }).encode()
            
            # Create request
            req = urllib.request.Request(
                f"{BASE_URL}/attendance",
                data=form_data,
                method='POST'
            )
            
            # Send request
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode())
                
            if result["success"]:
                print(f"✅ Presensi {student['name']}: {result['status']}")
            else:
                print(f"⚠️  {student['name']}: {result['message']}")
                
        except Exception as e:
            print(f"❌ Error presensi {student['name']}: {e}")

def check_system_status():
    """Cek status sistem"""
    print("🔍 Mengecek status sistem...")
    try:
        with urllib.request.urlopen(f"{BASE_URL}/") as response:
            result = json.loads(response.read().decode())
            print(f"✅ Sistem berjalan: {result['message']}")
            print(f"📊 QR Available: {result.get('qr_available', 'Unknown')}")
    except Exception as e:
        print(f"❌ Tidak dapat terhubung ke server: {e}")

if __name__ == "__main__":
    print("🚀 School QR System - Data Generator")
    print("=" * 40)
    
    check_system_status()
    
    print("\nPilih opsi:")
    print("1. Daftarkan semua siswa")
    print("2. Generate data QR code untuk testing")
    print("3. Rekam presensi otomatis")
    print("4. Semua di atas")
    
    try:
        choice = input("\nPilih opsi (1/2/3/4): ").strip()
        
        if choice == "1":
            register_students()
        elif choice == "2":
            generate_qr_data()
        elif choice == "3":
            record_attendance()
        elif choice == "4":
            register_students()
            generate_qr_data()
            record_attendance()
        else:
            print("❌ Pilihan tidak valid")
            
    except KeyboardInterrupt:
        print("\n👋 Program dihentikan")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n✨ Selesai!")