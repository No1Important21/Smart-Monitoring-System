import multiprocessing
import time
import os
import sqlite3
import cv2
from ultralytics import YOLO
from extract_cctv_video import capture_screenshots
from storage_management import manage_storage

# === Load YOLO Model for ETL ===
model = YOLO("yolov8n.pt")

# === Folder Gambar ===
folder = "images/"
folder_processed = "images_processed/"

# Pastikan folder-folder ada
if not os.path.exists(folder):
    os.makedirs(folder)
if not os.path.exists(folder_processed):
    os.makedirs(folder_processed)

# === Connect to Database ===
db_name = "suhat_monitor.db"

# === Fungsi Setup Database ===
def setup_database():
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS traffic_data (image TEXT, total_vehicle INTEGER)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS road_status (image TEXT, status TEXT, icon TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS notifications (image TEXT, message TEXT)""")
    conn.commit()
    conn.close()

# === Fungsi Menentukan Status ===
def get_status(total):
    if total <= 2: return "lancar", "🟢"
    elif total <= 4: return "ramai", "🟡"
    elif total <= 10: return "padat", "🔴"
    else: return "macet", "⚠️"

def run_storage():
    while True:
        manage_storage("images/")
        manage_storage("images_processed/")
        time.sleep(10)

def run_etl():
    setup_database()
    processed_files = set()  # Daftar file yang SUDAH diproses
    print("\n🚀 SIAP MEMANTAU FOLDER 'images/' SECARA REAL-TIME...")
    print("Tekan Ctrl+C untuk berhenti.\n")

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

                    # Tunggu sebentar memastikan file sudah tertulis sempurna
                    time.sleep(0.5)

                    # 1. Deteksi
                    results = model(image_path, verbose=False)

                    # Simpan gambar hasil deteksi
                    annotated_image = results[0].plot()
                    output_path = os.path.join(folder_processed, filename)
                    cv2.imwrite(output_path, annotated_image)

                    car_count = 0
                    for box in results[0].boxes:
                        if int(box.cls) == 2:  # Class 2 = Mobil
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
                pass

            # Istirahat 5 detik sebelum ngecek folder lagi
            time.sleep(5)

        except KeyboardInterrupt:
            print("\n🛑 ETL dihentikan.")
            break
        except Exception as e:
            print(f"Error in ETL: {e}")

if __name__ == "__main__":
    print("Starting all processes...")

    p1 = multiprocessing.Process(target=capture_screenshots)
    p2 = multiprocessing.Process(target=run_storage)
    p3 = multiprocessing.Process(target=run_etl)

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
        p1.join()
        p2.join()
        p3.join()
        print("All processes stopped.")
