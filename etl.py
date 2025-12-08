import os
import sqlite3
from ultralytics import YOLO

# === Load YOLO Model ===
model = YOLO("yolov8n.pt")

# === Folder Gambar ===
folder = "images/"

# === Connect to Database ===
conn = sqlite3.connect("suhat_monitor.db")
cur = conn.cursor()

# === Create Tables (if not exist) ===
cur.execute("""
CREATE TABLE IF NOT EXISTS traffic_data (
    image TEXT,
    total_vehicle INTEGER
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS road_status (
    image TEXT,
    status TEXT,
    icon TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS notifications (
    image TEXT,
    message TEXT
)
""")

conn.commit()

# === Fungsi menentukan status jalan ===
def get_status(total):
    if total <= 10:
        return "lancar", "🟢"
    elif total <= 30:
        return "ramai", "🟡"
    elif total <= 60:
        return "padat", "🔴"
    else:
        return "macet", "⚠️"

# === PROSES UTAMA (YOLO + ETL) ===
for filename in os.listdir(folder):
    if filename.lower().endswith((".jpg", ".jpeg", ".png")):
        image_path = os.path.join(folder, filename)

        # YOLO Detection
        results = model(image_path)

        # Hitung mobil saja (class 2 = car)
        car_count = 0
        for box in results[0].boxes:
            cls = int(box.cls)
            if cls == 2:
                car_count += 1

        print(f"{filename} → Jumlah mobil: {car_count}")

        # ETL Insert → traffic_data
        cur.execute("INSERT INTO traffic_data VALUES (?, ?)",
                    (filename, car_count))

        # Tentukan status jalan
        status, icon = get_status(car_count)

        # ETL Insert → road_status
        cur.execute("INSERT INTO road_status VALUES (?, ?, ?)",
                    (filename, status, icon))

        # Buat notifikasi
        message = f"{icon} Jalan Suhat {status} pada gambar {filename}"

        # ETL Insert → notifications
        cur.execute("INSERT INTO notifications VALUES (?, ?)",
                    (filename, message))

        print(message)

conn.commit()
conn.close()

print("\nData masuk ke suhat_monitor.db")
