import os
import sqlite3
import time
import cv2
from ultralytics import YOLO

# === Load Custom Model ===
# Kita PERCAYA pakai model.pt karena urutannya sudah benar (0,1,2,3)
try:
    print("Sedang memuat model custom (model.pt)...")
    model = YOLO("model.pt")
except:
    print("⚠️ Error: model.pt tidak ditemukan! Pastikan file ada di folder.")
    exit()

# === Folder Gambar ===
folder = "images/"
folder_processed = "images_processed/"

# Pastikan folder ada
if not os.path.exists(folder): os.makedirs(folder)
if not os.path.exists(folder_processed): os.makedirs(folder_processed)

# === Database Setup ===
db_name = "suhat_monitor.db"

def setup_database():
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()
    
    # UPDATE STRUKTUR: Ganti kolom 'bus' jadi 'bicycle' sesuai model temanmu
    cur.execute("""
    CREATE TABLE IF NOT EXISTS traffic_data (
        image TEXT,
        total_vehicle INTEGER,
        car INTEGER,
        motorcycle INTEGER,
        bicycle INTEGER, 
        truck INTEGER
    )
    """)
    cur.execute("""CREATE TABLE IF NOT EXISTS road_status (image TEXT, status TEXT, icon TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS notifications (image TEXT, message TEXT)""")
    conn.commit()
    conn.close()

# === Status Jalan ===
def get_status(total):
    # Ambang batas disesuaikan
    if total <= 15: return "lancar", "🟢"
    elif total <= 40: return "ramai", "🟡"
    elif total <= 80: return "padat", "🔴"
    else: return "macet", "⚠️"

# === MAIN PROGRAM ===
setup_database()
processed_files = set()

print("\n🚀 SIAP MEMANTAU FOLDER DENGAN MODEL CUSTOM (0=Mobil, 1=Motor)...")

while True:
    try:
        current_files = os.listdir(folder)
        new_files = [f for f in current_files if f not in processed_files and f.lower().endswith(('.jpg', '.png', '.jpeg'))]

        if new_files:
            conn = sqlite3.connect(db_name)
            cur = conn.cursor()

            for filename in new_files:
                image_path = os.path.join(folder, filename)
                time.sleep(0.5)

                # 1. Deteksi
                results = model(image_path, verbose=False)

                # Simpan gambar hasil (Fitur Rizqy)
                annotated_image = results[0].plot()
                cv2.imwrite(os.path.join(folder_processed, filename), annotated_image)

                # 2. Hitung Sesuai Urutan Baru (0, 1, 2, 3)
                counts = {'car': 0, 'motorcycle': 0, 'bicycle': 0, 'truck': 0}
                
                # MAPPING BARU (Sesuai gambar kamu)
                class_map = {
                    0: 'car', 
                    1: 'motorcycle', 
                    2: 'bicycle',  # Sepeda menggantikan Bus
                    3: 'truck'
                }

                for box in results[0].boxes:
                    cls_id = int(box.cls)
                    if cls_id in class_map:
                        counts[class_map[cls_id]] += 1
                
                total_vehicle = sum(counts.values())

                # 3. Status & Pesan
                status, icon = get_status(total_vehicle)
                detail_text = f"Mbl:{counts['car']} Mtr:{counts['motorcycle']} Spd:{counts['bicycle']} Trk:{counts['truck']}"
                message = f"{icon} Suhat {status} ({total_vehicle}). {detail_text} pada {filename}"
                
                # 4. Insert ke DB (Kolom Bicycle)
                cur.execute("INSERT INTO traffic_data VALUES (?, ?, ?, ?, ?, ?)", 
                            (filename, total_vehicle, counts['car'], counts['motorcycle'], counts['bicycle'], counts['truck']))
                cur.execute("INSERT INTO road_status VALUES (?, ?, ?)", (filename, status, icon))
                cur.execute("INSERT INTO notifications VALUES (?, ?)", (filename, message))
                
                print(f"✅ DETEKSI OK: {message}")
                processed_files.add(filename)

            conn.commit()
            conn.close()
        else:
            time.sleep(2)

    except KeyboardInterrupt:
        break
    except Exception as e:
        print(f"Error: {e}")