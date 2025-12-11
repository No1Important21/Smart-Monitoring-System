import multiprocessing
import time
import os
import sqlite3
import cv2
from ultralytics import YOLO
from extract_cctv_video import capture_screenshots
from storage_management import manage_storage

# === CONFIG ===
# Menggunakan Model Custom Rizqy
try:
    print("🤖 Memuat model custom (model.pt)...")
    model = YOLO("model.pt")
except:
    print("⚠️ model.pt tidak ditemukan! Pastikan file ada di folder.")
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
    
    # UPDATE STRUKTUR: Kolom 'bus' diganti 'bicycle' (Sesuai Dashboard Baru)
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
    if total <= 15: return "lancar", "🟢"
    elif total <= 40: return "ramai", "🟡"
    elif total <= 80: return "padat", "🔴"
    else: return "macet", "⚠️"

def run_storage():
    print("🧹 Storage Management berjalan...")
    while True:
        manage_storage("images/")
        manage_storage("images_processed/")
        time.sleep(10)

def run_etl():
    setup_database()
    processed_files = set()
    print("\n🚀 ETL SYSTEM BERJALAN (Model Custom: 0=Mobil, 1=Motor)...")
    
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

                    # Simpan gambar hasil
                    annotated_image = results[0].plot()
                    cv2.imwrite(os.path.join(folder_processed, filename), annotated_image)

                    # 2. Hitung Sesuai Urutan Model Custom
                    counts = {'car': 0, 'motorcycle': 0, 'bicycle': 0, 'truck': 0, 'bus':0 }
                    
                    # MAPPING ID (Sesuai gambar kamu: 0=Car, 1=Motor, 2=Bicycle, 3=Truck)
                    class_map = {
                        1: 'car', 
                        2: 'motorcycle', 
                        3: 'bicycle',
                        4: 'truck',
                        5: 'bus'
                    }

                    for box in results[0].boxes:
                        cls_id = int(box.cls)
                        if cls_id in class_map:
                            counts[class_map[cls_id]] += 1
                    
                    total_vehicle = sum(counts.values())

                    # 3. Status & Insert DB
                    status, icon = get_status(total_vehicle)
                    detail_text = f"Mbl:{counts['car']} Mtr:{counts['motorcycle']} Spd:{counts['bicycle']} Trk:{counts['truck']}"
                    message = f"{icon} Suhat {status} ({total_vehicle}). {detail_text}"
                    
                    # Insert Data (Kolom Bicycle)
                    cur.execute("INSERT INTO traffic_data VALUES (?, ?, ?, ?, ?, ?)", 
                                (filename, total_vehicle, counts['car'], counts['motorcycle'], counts['bicycle'], counts['truck']))
                    cur.execute("INSERT INTO road_status VALUES (?, ?, ?)", (filename, status, icon))
                    cur.execute("INSERT INTO notifications VALUES (?, ?)", (filename, message))
                    
                    print(f"✅ {message}")
                    processed_files.add(filename)

                conn.commit()
                conn.close()
            else:
                pass # Tidak ada file baru

            time.sleep(2)

        except KeyboardInterrupt:
            print("\n🛑 ETL dihentikan.")
            break
        except Exception as e:
            print(f"Error in ETL: {e}")

if __name__ == "__main__":
    print("Starting Main System...")
    
    # Menjalankan 3 Proses Sekaligus
    p1 = multiprocessing.Process(target=capture_screenshots) # Ambil CCTV
    p2 = multiprocessing.Process(target=run_storage)       # Bersih-bersih
    p3 = multiprocessing.Process(target=run_etl)           # Deteksi AI

    p1.start()
    p2.start()
    p3.start()

    try:
        p1.join()
        p2.join()
        p3.join()
    except KeyboardInterrupt:
        print("\nStopping all processes...")
        p1.terminate()
        p2.terminate()
        p3.terminate()
        print("All processes stopped.")
