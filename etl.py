import os
import sqlite3
import time  # <--- Butuh ini buat jeda waktu
from ultralytics import YOLO

# === Load YOLO Model ===
print("Sedang memuat model YOLO...")
model = YOLO("yolov8n.pt")

# === Folder Gambar ===
folder = "images/"

# Pastikan folder ada
if not os.path.exists(folder):
    os.makedirs(folder)

# === Connect to Database ===
db_name = "suhat_monitor.db"

# === Fungsi Setup Database ===
def setup_database():
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()
    # Hapus tabel lama biar bersih (opsional, kalau mau data numpuk hapus baris DROP ini)
    # cur.execute("DROP TABLE IF EXISTS traffic_data")
    # cur.execute("DROP TABLE IF EXISTS road_status")
    # cur.execute("DROP TABLE IF EXISTS notifications")
    
    cur.execute("""CREATE TABLE IF NOT EXISTS traffic_data (image TEXT, total_vehicle INTEGER)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS road_status (image TEXT, status TEXT, icon TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS notifications (image TEXT, message TEXT)""")
    conn.commit()
    conn.close()

# === Fungsi Menentukan Status ===
def get_status(total):
    if total <= 10: return "lancar", "🟢"
    elif total <= 30: return "ramai", "🟡"
    elif total <= 60: return "padat", "🔴"
    else: return "macet", "⚠️"

# === SETUP AWAL ===
setup_database()
processed_files = set() # <--- Daftar file yang SUDAH diproses (biar gak double)

print("\n🚀 SIAP MEMANTAU FOLDER 'images/' SECARA REAL-TIME...")
print("Tekan Ctrl+C untuk berhenti.\n")

# === LOOPING UTAMA ===
while True:
    try:
        # Cek isi folder saat ini
        current_files = os.listdir(folder)
        
        # Cari file baru (yang belum ada di processed_files)
        new_files = [f for f in current_files if f not in processed_files and f.lower().endswith(('.jpg', '.png', '.jpeg'))]

        if new_files:
            conn = sqlite3.connect(db_name)
            cur = conn.cursor()

            for filename in new_files:
                image_path = os.path.join(folder, filename)
                
                # Tunggu sebentar memastikan file sudah tertulis sempurna oleh script sebelah
                time.sleep(0.5) 

                # 1. Deteksi
                results = model(image_path, verbose=False) # verbose=False biar terminal gak penuh text YOLO
                
                car_count = 0
                for box in results[0].boxes:
                    if int(box.cls) == 2: # Class 2 = Mobil
                        car_count += 1
                
                # 2. Tentukan Status
                status, icon = get_status(car_count)
                message = f"{icon} Jalan Suhat {status} ({car_count} mobil) pada {filename}"
                
                # 3. Masukkan ke Database
                cur.execute("INSERT INTO traffic_data VALUES (?, ?)", (filename, car_count))
                cur.execute("INSERT INTO road_status VALUES (?, ?, ?)", (filename, status, icon))
                cur.execute("INSERT INTO notifications VALUES (?, ?)", (filename, message))
                
                print(f"✅ DATA BARU: {message}")
                
                # 4. Tandai file ini sudah diproses
                processed_files.add(filename)

            conn.commit()
            conn.close()
        
        else:
            # Kalau gak ada file baru, diam aja
            pass

        # Istirahat 2 detik sebelum ngecek folder lagi biar CPU gak panas
        time.sleep(2)

    except KeyboardInterrupt:
        print("\n🛑 Program dihentikan user.")
        break
    except Exception as e:
        print(f"Error: {e}")