import streamlit as st
import sqlite3
import pandas as pd
import time
import os

# === KONFIGURASI HALAMAN ===
st.set_page_config(
    page_title="Suhat Smart Monitor",
    page_icon="🚦",
    layout="wide"
)

# === JUDUL DASHBOARD ===
st.title("🚦 Monitoring Kepadatan Lalu Lintas - Jalan Suhat")
st.markdown("Sistem pemantauan real-time berbasis Computer Vision & IoT")

# === FUNGSI AMBIL DATA ===
def get_data():
    conn = sqlite3.connect("suhat_monitor.db")
    # Query disesuaikan dengan kolom 'bicycle'
    query = """
    SELECT t.image, t.total_vehicle, t.car, t.motorcycle, t.bicycle, t.truck, r.status, r.icon
    FROM traffic_data t
    JOIN road_status r ON t.image = r.image
    ORDER BY t.image DESC
    LIMIT 100
    """
    try:
        df = pd.read_sql(query, conn)
    except Exception as e:
        df = pd.DataFrame()
    finally:
        conn.close()
    return df

# === TEMPAT TAMPILAN (CONTAINER) ===
placeholder = st.empty()

# === LOOPING REAL-TIME ===
while True:
    with placeholder.container():
        try:
            # 1. Ambil Data
            df = get_data()
            
            if df.empty:
                st.warning("⏳ Menunggu data masuk... Pastikan etl.py sedang berjalan!")
                time.sleep(2)
                continue

            latest = df.iloc[0]

            # 2. Tampilkan KPI
            kpi1, kpi2, kpi3 = st.columns(3)
            with kpi1:
                st.metric("Status Jalan", f"{latest['status'].upper()}", latest['icon'])
            with kpi2:
                st.metric("Total Kendaraan", f"{latest['total_vehicle']} Unit", "Real-time")
            with kpi3:
                cols = ['car', 'motorcycle', 'bicycle', 'truck']
                max_type = df[cols].iloc[0].idxmax()
                translate = {'car': 'Mobil', 'motorcycle': 'Motor', 'bicycle': 'Sepeda', 'truck': 'Truk'}
                st.metric("Dominasi Kendaraan", translate.get(max_type, max_type))

            st.divider() 

            # 3. Tampilkan Visualisasi
            col_kiri, col_kanan = st.columns([1, 2])

            with col_kiri:
                st.subheader("📸 CCTV Live Analysis")
                img_path = os.path.join("images_processed", latest['image'])
                if os.path.exists(img_path):
                    st.image(img_path, caption=f"Timestamp: {latest['image']}", use_container_width=True)
                else:
                    st.warning(f"Gambar sedang diproses... ({latest['image']})")

            with col_kanan:
                st.subheader("📊 Tren Kepadatan")
                st.line_chart(df[['total_vehicle']].iloc[::-1])

                st.subheader("🚗 Komposisi Kendaraan")
                chart_data = pd.DataFrame({
                    'Tipe': ['Mobil', 'Motor', 'Sepeda', 'Truk'],
                    'Jumlah': [latest['car'], latest['motorcycle'], latest['bicycle'], latest['truck']]
                })
                st.bar_chart(chart_data.set_index('Tipe'))

            # 4. Download Button (FIXED)
            st.divider()
            csv = df.to_csv(index=False).encode('utf-8')
            
            # Tambahkan Key Unik biar tidak error duplikat ID
            unique_key = f"download_btn_{int(time.time())}"
            
            st.download_button(
                label="📥 Download Laporan Data (CSV)",
                data=csv,
                file_name='laporan_suhat_monitor.csv',
                mime='text/csv',
                key=unique_key
            )

        except Exception as e:
            st.error(f"Sedang sinkronisasi database... ({e})")

        time.sleep(2)