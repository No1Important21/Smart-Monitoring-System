import multiprocessing
import time
import os
import sqlite3
import cv2
from ultralytics import YOLO
from extract_cctv_video import capture_screenshots
from storage_management import manage_storage

# === KONFIGURASI ===
try:
    print("🤖 Memuat model custom (model.pt)...")
    model = YOLO("model.pt")
except:
    print("⚠️ model.pt tidak ditemukan! Program berhenti.")
    exit()

folder = "images/"
folder_processed = "images_processed/"
# Buat folder jika belum ada
if not os.path.exists(folder): os.makedirs(folder)
if not os.path.exists(folder_processed): os.makedirs(folder_processed)

db_name = "suhat_monitor.db"

def setup_database():
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()
    # Kita tetap pakai nama kolom 'smp_value' di database agar kompatibel,
    # tapi isinya nanti adalah nilai SKR (PKJI 2023).
    cur.execute("""
    CREATE TABLE IF NOT EXISTS traffic_data (
        image TEXT,
        total_vehicle INTEGER,
        car INTEGER,
        motorcycle INTEGER,
        bicycle INTEGER,
        truck INTEGER,
        smp_value REAL
    )
    """)
    cur.execute("""CREATE TABLE IF NOT EXISTS road_status (image TEXT, status TEXT, icon TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS notifications (image TEXT, message TEXT)""")
    conn.commit()
    conn.close()

# === LOGIKA PKJI 2023 (Pedoman Kapasitas Jalan Indonesia) ===
def get_status_pkji(counts):
    # Bobot Ekivalensi Kendaraan Ringan (ekr) untuk Jalan Perkotaan (Tipe 4/2 T):
    # Sumber: PKJI 2023
    
    # KR (Kendaraan Ringan/Mobil) = 1.0
    # SM (Sepeda Motor)           = 0.40 (Naik dibanding MKJI 97 yg 0.33)
    # KB (Kendaraan Berat/Truk)   = 1.30
    # UM (Unmotorized/Sepeda)     = 0.20 (Faktor hambatan samping)
    
    skr = (counts['car'] * 1.0) + \
          (counts['motorcycle'] * 0.40) + \
          (counts['truck'] * 1.30) + \
          (counts['bicycle'] * 0.20)
    
    # Threshold (Batas) Macet berdasarkan Kapasitas Visual Frame CCTV
    # (Disesuaikan dari kapasitas jalan ~3300 SKR/jam dibagi ke skala frame detik)
    if skr <= 10: return "lancar", "🟢", skr
    elif skr <= 30: return "ramai", "🟡", skr
    elif skr <= 55: return "padat", "🔴", skr
    else: return "macet", "⚠️", skr

def run_storage():
    print("🧹 Storage Management berjalan...")
    while True:
        manage_storage("images/")
        manage_storage("images_processed/")
        time.sleep(30)

def run_etl():
    setup_database()
    processed_files = set()
    print("\n🚀 ETL SYSTEM BERJALAN (Standar: PKJI 2023)...")
    print(f"🧐 Kamus Internal Model: {model.names}")
    
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

                    # Deteksi (Confidence 0.45: Seimbang antara sensitif & akurat)
                    results = model(image_path, verbose=False, conf=0.45, iou=0.45)
                    
                    annotated_image = results[0].plot()
                    cv2.imwrite(os.path.join(folder_processed, filename), annotated_image)

                    # Reset Hitungan
                    counts = {'car': 0, 'motorcycle': 0, 'bicycle': 0, 'truck': 0}

                    # === LOGIKA BACA LABEL (Bukan ID Angka) ===
                    # Mencegah error salah ID (Mobil masuk Sepeda)
                    for box in results[0].boxes:
                        cls_id = int(box.cls)
                        cls_name = model.names[cls_id].lower() # Ambil nama, kecilkan huruf
                        
                        # Pencocokan Kata Kunci (Support Indo/Inggris)
                        if 'mobil' in cls_name or 'car' in cls_name:
                            counts['car'] += 1
                        elif 'motor' in cls_name or 'cycle' in cls_name:
                            counts['motorcycle'] += 1
                        elif 'sepeda' in cls_name or 'bicycle' in cls_name or 'bike' in cls_name:
                            counts['bicycle'] += 1
                        elif 'truk' in cls_name or 'truck' in cls_name or 'bus' in cls_name:
                            counts['truck'] += 1
                    
                    total_vehicle = sum(counts.values())
                    
                    # HITUNG STATUS MENGGUNAKAN RUMUS PKJI 2023
                    status, icon, skr_val = get_status_pkji(counts)
                    
                    detail_text = f"Mbl:{counts['car']} Mtr:{counts['motorcycle']} Spd:{counts['bicycle']} Trk:{counts['truck']}"
                    message = f"{icon} Suhat {status} (Beban: {skr_val:.1f} SKR). {detail_text}"
                    
                    # Simpan ke Database
                    cur.execute("INSERT INTO traffic_data VALUES (?, ?, ?, ?, ?, ?, ?)", 
                                (filename, total_vehicle, counts['car'], counts['motorcycle'], counts['bicycle'], counts['truck'], skr_val))
                    cur.execute("INSERT INTO road_status VALUES (?, ?, ?)", (filename, status, icon))
                    cur.execute("INSERT INTO notifications VALUES (?, ?)", (filename, message))
                    
                    print(f"✅ {message}")
                    processed_files.add(filename)

                conn.commit()
                conn.close()
            else:
                pass

            time.sleep(2)

        except KeyboardInterrupt:
            print("\n🛑 ETL dihentikan.")
            break
        except Exception as e:
            print(f"Error in ETL: {e}")

if __name__ == "__main__":
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
        p1.terminate()
        p2.terminate()
        p3.terminate()