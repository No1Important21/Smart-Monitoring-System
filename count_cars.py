import os
import csv
from ultralytics import YOLO

# Load model YOLO
model = YOLO("yolov8n.pt")

# Folder gambar
folder = "images/"

# Simpan hasil hitungan
hasil = []

for filename in os.listdir(folder):
    if filename.lower().endswith((".jpg", ".jpeg", ".png")):
        path = os.path.join(folder, filename)

        # Run detection
        results = model(path)

        # Hitung mobil (class 2 = car)
        car_count = 0
        for box in results[0].boxes:
            cls = int(box.cls)
            if cls == 2:   # class mobil
                car_count += 1

        print(f"{filename} → Jumlah mobil: {car_count}")

        # simpan data ke list
        hasil.append([filename, car_count])

# Buat CSV output
with open("traffic_from_images.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["image", "total_vehicle"])
    writer.writerows(hasil)

print("\nCSV selesai dibuat: traffic_from_images.csv")
