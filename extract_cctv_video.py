import cv2
import os
import time
from storage_management import manage_storage

# === PENGATURAN ===
stream_url = "http://stream.cctv.malangkota.go.id/WebRTCApp/streams/673512185163543498056968.m3u8?token=null"
output_folder = "images/"
interval_seconds = 5  # Ambil screenshot tiap 5 detik

# Buat folder images kalau belum ada
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

def capture_screenshots():
    cap = cv2.VideoCapture(stream_url)

    if not cap.isOpened():
        print("Error: Tidak bisa membuka stream. Cek URL atau koneksi internet!")
        return

    print(f"Mulai menangkap screenshot dari stream: {stream_url}")
    print("Tekan Ctrl+C untuk berhenti.\n")

    screenshot_count = 0
    last_capture_time = time.time()

    try:
        while True:
            success, frame = cap.read()

            if not success:
                print("Warning: Gagal membaca frame. Mencoba reconnect...")
                cap.release()
                time.sleep(5)  # Tunggu 5 detik sebelum reconnect
                cap = cv2.VideoCapture(stream_url)
                if not cap.isOpened():
                    print("Error: Tidak bisa reconnect ke stream.")
                    break
                continue

            current_time = time.time()
            if current_time - last_capture_time >= interval_seconds:
                # Nama file dengan timestamp
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.jpg"
                filepath = os.path.join(output_folder, filename)

                cv2.imwrite(filepath, frame)
                print(f"📸 Screenshot tersimpan: {filename}")
                screenshot_count += 1
                last_capture_time = current_time

                # Manage storage after saving the image
                manage_storage("images/")
                manage_storage("images_processed/")

            # Sedikit delay untuk mengurangi beban CPU
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n🛑 Program dihentikan oleh user.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cap.release()
        print(f"\nSelesai! {screenshot_count} screenshot tersimpan di folder '{output_folder}'.")

if __name__ == "__main__":
    capture_screenshots()
