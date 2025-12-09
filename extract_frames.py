import cv2
import os

# === PENGATURAN ===
video_path = "video_rakha.mp4"  # Ganti nama file videonya sesuai yg dikasih Rakha
output_folder = "images/"       # Folder tujuan (biar langsung dibaca etl.py)
interval_detik = 60             # Ambil gambar tiap 60 detik (1 menit)

# Buat folder images kalau belum ada
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# Buka video
cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print("Error: Video tidak bisa dibuka. Cek nama filenya ya!")
    exit()

fps = cap.get(cv2.CAP_PROP_FPS) # Frame per second (biasanya 30 atau 60)
frame_interval = int(fps * interval_detik) # Hitung loncat berapa frame

frame_count = 0
saved_count = 0

print(f"Mulai memproses video: {video_path}...")

while True:
    success, frame = cap.read()
    
    if not success:
        break # Video habis

    # Cek apakah saatnya ambil gambar (sesuai interval)
    if frame_count % frame_interval == 0:
        # Nama file output: menit_ke_0.jpg, menit_ke_1.jpg, dst
        menit = frame_count // int(fps * 60)
        nama_file = f"suhat_menit_{saved_count}.jpg"
        path_simpan = os.path.join(output_folder, nama_file)
        
        cv2.imwrite(path_simpan, frame)
        print(f"📸 Tersimpan: {nama_file}")
        saved_count += 1

    frame_count += 1

cap.release()
print(f"\nSelesai! {saved_count} gambar tersimpan di folder '{output_folder}'.")
print("Sekarang jalankan etl.py untuk memproses data.")