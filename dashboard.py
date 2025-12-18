import streamlit as st
import sqlite3
import pandas as pd
import time
import os
import plotly.express as px

# === KONFIGURASI HALAMAN ===
st.set_page_config(
    page_title="Suhat Smart Monitor",
    page_icon="🚦",
    layout="wide"
)

# === JUDUL DASHBOARD ===
st.title("🚦 Monitoring Kepadatan Lalu Lintas - Jalan Suhat")
st.markdown("Sistem pemantauan real-time berbasis **Computer Vision** & Standar **PKJI 2023**")

# === FUNGSI AMBIL DATA ===
def get_data():
    conn = sqlite3.connect("suhat_monitor.db")
    # Ambil semua data termasuk total_vehicle (jumlah fisik) dan smp_value (beban SKR)
    query = """
    SELECT t.image, t.total_vehicle, t.car, t.motorcycle, t.bicycle, t.truck, t.smp_value, r.status, r.icon
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
                st.warning("⏳ Menunggu data masuk... Pastikan main.py sedang berjalan!")
                time.sleep(2)
                continue

            latest = df.iloc[0]

            # 2. KPI UTAMA
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            
            with kpi1:
                st.metric("Status Jalan", f"{latest['status'].upper()}", latest['icon'])
            with kpi2:
                # Beban SKR (Teoritis)
                st.metric("Beban Jalan (PKJI)", f"{latest['smp_value']:.1f} SKR", "Load")
            with kpi3:
                # Jumlah Fisik (Real)
                st.metric("Total Kendaraan", f"{latest['total_vehicle']} Unit", "Count")
            with kpi4:
                # Dominasi
                cols = ['car', 'motorcycle', 'bicycle', 'truck']
                max_type = df[cols].iloc[0].idxmax()
                translate = {'car': 'Mobil', 'motorcycle': 'Motor', 'bicycle': 'Sepeda', 'truck': 'Truk'}
                st.metric("Dominasi", translate.get(max_type, max_type))

            st.divider() 

            # 3. LAYOUT VISUALISASI
            col_kiri, col_kanan = st.columns([1.2, 1.8])

            with col_kiri:
                st.subheader("📸 CCTV Live Analysis")
                img_path = os.path.join("images_processed", latest['image'])
                
                if os.path.exists(img_path):
                    st.image(img_path, caption=f"Timestamp: {latest['image']}", use_container_width=True)
                else:
                    st.warning(f"Gambar sedang diproses... ({latest['image']})")

            with col_kanan:
                # === FITUR TABS (Dua Mode Pandang) ===
                tab_beban, tab_fisik = st.tabs(["📊 Analisis Beban (SKR)", "🔢 Data Fisik (Unit)"])
                
                # --- TAB 1: FOKUS KE BEBAN / DAMPAK MACET (SKR) ---
                with tab_beban:
                    st.caption("Grafik ini menggunakan bobot PKJI 2023 (Motor x0.4, Truk x1.3)")
                    
                    # 1. Donut Chart (SKR)
                    chart_data_skr = {
                        'Tipe': ['Mobil', 'Motor', 'Sepeda', 'Truk'],
                        'Beban (SKR)': [
                            latest['car'] * 1.0, 
                            latest['motorcycle'] * 0.40, 
                            latest['bicycle'] * 0.20, 
                            latest['truck'] * 1.30
                        ]
                    }
                    df_skr = pd.DataFrame(chart_data_skr)
                    df_skr = df_skr[df_skr['Beban (SKR)'] > 0]

                    if not df_skr.empty:
                        fig_donut = px.pie(df_skr, values='Beban (SKR)', names='Tipe', hole=0.4, 
                                     color_discrete_sequence=px.colors.sequential.RdBu)
                        fig_donut.update_traces(textinfo='percent+label')
                        fig_donut.update_layout(height=250, margin=dict(t=0, b=0, l=0, r=0))
                        st.plotly_chart(fig_donut, use_container_width=True, key=f"donut_skr_{int(time.time())}")
                    
                    # 2. Line Chart (Tren SKR)
                    st.subheader("Tren Beban Jalan")
                    st.line_chart(df[['smp_value']].iloc[::-1])

                # --- TAB 2: FOKUS KE JUMLAH ASLI / KUANTITAS (UNIT) ---
                with tab_fisik:
                    st.caption("Grafik ini menampilkan jumlah asli kendaraan yang terhitung.")
                    
                    # 1. Bar Chart (Jumlah Unit)
                    count_data = {
                        'Kendaraan': ['Mobil', 'Motor', 'Sepeda', 'Truk'],
                        'Jumlah': [latest['car'], latest['motorcycle'], latest['bicycle'], latest['truck']]
                    }
                    df_count = pd.DataFrame(count_data)
                    
                    # Pakai Bar Chart biar kelihatan beda tingginya
                    fig_bar = px.bar(df_count, x='Kendaraan', y='Jumlah', color='Kendaraan',
                                     text_auto=True, color_discrete_sequence=px.colors.qualitative.Pastel)
                    fig_bar.update_layout(height=250, margin=dict(t=0, b=0, l=0, r=0), showlegend=False)
                    
                    st.plotly_chart(fig_bar, use_container_width=True, key=f"bar_count_{int(time.time())}")

                    # 2. Line Chart (Tren Total Unit)
                    st.subheader("Tren Volume Kendaraan")
                    st.line_chart(df[['total_vehicle']].iloc[::-1])

            # 4. Download Button
            st.divider()
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Laporan Lengkap (CSV)",
                data=csv,
                file_name='laporan_suhat_final.csv',
                mime='text/csv',
                key=f"download_btn_{int(time.time())}"
            )

        except Exception as e:
            st.error(f"Sedang sinkronisasi database... ({e})")

        time.sleep(2)