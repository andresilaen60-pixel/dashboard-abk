import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# --- 1. CONFIG HALAMAN ---
st.set_page_config(page_title="Dashboard ABK Sumut 2026", layout="wide")

# --- 2. CSS CUSTOM (SIDEBAR PUTIH & DESIGN MODERN) ---
st.markdown("""
    <style>
    .main { background: linear-gradient(160deg, #f0f9ff 0%, #cbebff 100%); color: #01579b; }
    [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 2px solid #0288d1; }
    [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label { 
        color: #012d5e !important; font-weight: 800 !important; 
    }
    div.stButton > button {
        width: 100%; border-radius: 10px;
        background: #007bff !important; color: white !important; font-weight: bold;
    }
    div.stButton > button:hover { background: #0056b3 !important; }
    
    .custom-table { width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; color: black; margin-top: 10px; }
    .custom-table th { background: #012d5e; color: white; padding: 12px; text-align: left; }
    .custom-table td { padding: 10px; border-bottom: 1px solid #ddd; position: relative; }
    .bg-kurang { background-color: rgba(255, 0, 0, 0.1) !important; }
    .bg-lebih { background-color: rgba(0, 0, 255, 0.1) !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. LOAD DATA (VERSI LEBIH KUAT) ---
@st.cache_data
def load_and_fix_data():
    try:
        # Menambahkan engine='openpyxl' secara paksa
        xls = pd.ExcelFile("data.xlsx", engine='openpyxl')
        
        # Ambil sheet pertama secara otomatis (biar aman kalau namanya beda)
        df_u = pd.read_excel(xls, sheet_name=0)
        
        # Cari sheet DAFTAR SEKOLAH
        sheet_names = xls.sheet_names
        if "DAFTAR SEKOLAH" in sheet_names:
            df_s = pd.read_excel(xls, sheet_name="DAFTAR SEKOLAH")
        else:
            # Kalau namanya beda sedikit (misal spasi), ambil sheet ke-2
            df_s = pd.read_excel(xls, sheet_name=1)
            
        df_u.columns = df_u.columns.str.strip()
        df_s.columns = df_s.columns.str.strip()
        
        df_s_fix = df_s[['NPSN', 'Kabupaten/Kota']].drop_duplicates()
        df = pd.merge(df_u, df_s_fix, on='NPSN', how='left')
        df['Kabupaten'] = df['Kabupaten/Kota'].fillna(df['KABUPATEN BY NAMA SEKOLAH']).fillna("Lainnya")
        df.fillna(0, inplace=True)
        
        def cek_status(row):
            if row['Jml Guru'] > row['ABK']: return "Lebih Guru"
            elif row['Jml Guru'] < row['ABK']: return "Kurang Guru"
            else: return "Sesuai"
        df['Keterangan'] = df.apply(cek_status, axis=1)
        return df
    except Exception as e:
        st.error(f"Eror Memuat Data: {e}")
        return None

# --- 4. INISIALISASI SESSION STATE ---
if 'sub_view' not in st.session_state: st.session_state.sub_view = 'LIST_KAB'
if 'sel_kab' not in st.session_state: st.session_state.sel_kab = None
if 'sel_sch' not in st.session_state: st.session_state.sel_sch = None
if 'map_filter' not in st.session_state: st.session_state.map_filter = None

df = load_and_fix_data()

if df is not None:
    # --- 5. SIDEBAR MENU (MODEL TOMBOL) ---
    with st.sidebar:
        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/d/d2/Coat_of_arms_of_North_Sumatra.svg/1200px-Coat_of_arms_of_North_Sumatra.svg.png", width=80)
        st.title("E-ABK SUMUT")
        st.write("---")
        
        # Inisialisasi menu aktif jika belum ada
        if 'menu_aktif' not in st.session_state:
            st.session_state.menu_aktif = "Data Provinsi"

        # Fungsi untuk pindah menu
        def pindah_menu(nama_menu):
            st.session_state.menu_aktif = nama_menu
            st.session_state.sub_view = 'LIST_KAB' # Reset tampilan sub-menu
            st.rerun()

        # Deretan Tombol Menu
        if st.button("🏢 Data Provinsi", use_container_width=True):
            pindah_menu("Data Provinsi")
            
        if st.button("📍 Data Kabupaten Kota", use_container_width=True):
            pindah_menu("Data Kabupaten Kota")
            
        if st.button("🌐 Data Keseluruhan", use_container_width=True):
            pindah_menu("Data Keseluruhan")
            
        if st.button("🗺️ Peta Maps Sumut", use_container_width=True):
            pindah_menu("Peta Maps Sumut")

    # Ambil nilai menu dari session state untuk logika tampilan
    menu_pilihan = st.session_state.menu_aktif

    # --- 6. TAMPILAN BERDASARKAN MENU ---
    if menu_pilihan == "Data Provinsi":
        st.header("🏢 Rekapitulasi Guru Provinsi")
        c1, c2, c3 = st.columns(3)
        c1.metric("TOTAL GURU", int(df['Jml Guru'].sum()))
        c2.metric("KEPALA SEKOLAH", int(df[df['Jabatan'].str.contains('Kepala Sekolah', case=False, na=False)]['Jml Guru'].sum()))
        c3.metric("KEKURANGAN", int(df['Kurang Guru'].sum()))
        st.write("---")
        st.dataframe(df.groupby('Kabupaten').agg({'Jml Guru':'sum', 'Kurang Guru':'sum'}).reset_index(), use_container_width=True, hide_index=True)

   # B. DATA KABUPATEN KOTA
    elif menu_pilihan == "Data Kabupaten Kota":
        if st.session_state.sub_view == 'LIST_KAB':
            st.header("📍 Data Per Kabupaten / Kota")
            
            # --- 1. TOMBOL GRAFIK KABUPATEN DENGAN WARNA KHUSUS ---
            if st.button("📊 Tampilkan Grafik Analisis Kab/Kota"):
                if 'show_chart_kab' not in st.session_state: st.session_state.show_chart_kab = False
                st.session_state.show_chart_kab = not st.session_state.show_chart_kab
            
            if st.session_state.get('show_chart_kab', False):
                # Menghitung Total Guru dan Total Kurang per Kabupaten
                df_chart = df.groupby('Kabupaten').agg({
                    'Jml Guru': 'sum',
                    'Kurang Guru': 'sum'
                }).reset_index()
                
                # Menampilkan Grafik dengan kolom Jml Guru (Biru default) dan Kurang Guru (Merah)
                # Catatan: st.bar_chart secara otomatis memberi warna berbeda untuk tiap kolom
                st.bar_chart(
                    df_chart.set_index('Kabupaten')[['Jml Guru', 'Kurang Guru']],
                    color=["#0000FF", "#FF0000"] # Biru untuk Jml Guru, Merah untuk Kurang Guru
                )
            
            st.write("---")
            search_k = st.text_input("🔍 Cari Kabupaten...")
            kabs = sorted([k for k in df['Kabupaten'].unique() if k != "Lainnya"])
            if search_k: kabs = [k for k in kabs if search_k.lower() in k.lower()]
            
            h1, h2, h3 = st.columns([2, 1, 1])
            h1.write("**Kabupaten**")
            h2.write("**Guru**")
            h3.write("**Kepala Sekolah**")
            
            for k in kabs:
                df_k = df[df['Kabupaten'] == k]
                c1, c2, c3 = st.columns([2, 1, 1])
                if c1.button(k, key=f"kb_{k}"):
                    st.session_state.sel_kab = k; st.session_state.sub_view = 'LIST_SEKOLAH'; st.rerun()
                c2.write(int(df_k['Jml Guru'].sum()))
                c3.write(int(df_k[df_k['Jabatan'].str.contains('Kepala Sekolah', case=False)]['Jml Guru'].sum()))

        elif st.session_state.sub_view == 'LIST_SEKOLAH':
            st.header(f"🏫 Sekolah di {st.session_state.sel_kab}")
            
            # --- MERAPATKAN TOMBOL KEMBALI & CARI SEKOLAH ---
            c1, c2 = st.columns([1, 4]) # Kolom 1 untuk tombol, Kolom 2 untuk search
            with c1:
                # Memberikan sedikit margin atas agar sejajar dengan input box
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                if st.button("⬅ Kembali"): 
                    st.session_state.sub_view = 'LIST_KAB'
                    st.rerun()
            with c2:
                search_s = st.text_input("🔍 Cari Sekolah...", placeholder="Ketik nama sekolah di sini...")

            # Logika Hitung (Tetap Sama)
            df_kab = df[df['Kabupaten'] == st.session_state.sel_kab].copy()
            df_kab['Selisih_Real'] = df_kab['Jml Guru'] - df_kab['ABK']
            sch_summary = df_kab.groupby('Nama Sekolah').apply(
                lambda x: pd.Series({
                    'Kurang': abs(x[x['Selisih_Real'] < 0]['Selisih_Real'].sum()),
                    'Lebih': x[x['Selisih_Real'] > 0]['Selisih_Real'].sum()
                })
            ).reset_index()
            
            if search_s:
                sch_summary = sch_summary[sch_summary['Nama Sekolah'].str.contains(search_s, case=False)]

            st.write("---")

            # CSS untuk merapatkan baris tabel
            st.markdown("""<style>
                .center-text { text-align: center; font-weight: bold; margin-bottom: 0px; } 
                .stButton button { margin-bottom: -15px !important; }
                div[data-testid="stVerticalBlock"] > div { font-gap: 0rem !important; } /* Memangkas gap antar baris */
                </style>""", unsafe_allow_html=True)

            h1, h2, h3 = st.columns([2, 1, 1])
            h1.markdown("**Nama Sekolah**")
            h2.markdown("<p class='center-text'>Guru Kurang</p>", unsafe_allow_html=True)
            h3.markdown("<p class='center-text'>Guru Lebih</p>", unsafe_allow_html=True)
            st.write("---")

            for i, row in sch_summary.iterrows():
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1:
                    if st.button(row['Nama Sekolah'], key=f"sk_{row['Nama Sekolah']}"):
                        st.session_state.sel_sch = row['Nama Sekolah']
                        st.session_state.sub_view = 'DETAIL'
                        st.rerun()
                with c2:
                    st.markdown(f"<p class='center-text' style='color: red;'>🔴 {int(row['Kurang'])}</p>", unsafe_allow_html=True)
                with c3:
                    st.markdown(f"<p class='center-text' style='color: blue;'>🔵 {int(row['Lebih'])}</p>", unsafe_allow_html=True)

        elif st.session_state.sub_view == 'DETAIL':
            st.header(f"🔍 Detail: {st.session_state.sel_sch}")
            if st.button("⬅ Kembali"): st.session_state.sub_view = 'LIST_SEKOLAH'; st.rerun()
            df_res = df[df['Nama Sekolah'] == st.session_state.sel_sch].copy()
            df_res['Selisih'] = df_res['Jml Guru'] - df_res['ABK']
            html = "<table class='custom-table'><tr><th>Jabatan</th><th>Kebutuhan</th><th>Jumlah Guru</th><th>Selisih</th><th>Keterangan</th></tr>"
            for _, row in df_res.iterrows():
                s_val = f"+{int(row['Selisih'])}" if row['Selisih'] > 0 else str(int(row['Selisih']))
                cls = "bg-kurang" if row['Selisih'] < 0 else "bg-lebih" if row['Selisih'] > 0 else ""
                html += f"<tr class='{cls}'><td>{row['Jabatan']}</td><td>{int(row['ABK'])}</td><td>{int(row['Jml Guru'])}</td><td>{s_val}</td><td>{row['Keterangan']}</td></tr>"
            st.markdown(html + "</table>", unsafe_allow_html=True)
                    
    elif menu_pilihan == "Data Keseluruhan":
        st.header("🌐 Seluruh Data Pemetaan")
        search_all = st.text_input("🔍 Cari data...")
        df_all = df[['Kabupaten', 'Nama Sekolah', 'Jabatan', 'Jml Guru', 'Kurang Guru', 'Keterangan']].copy()
        if search_all:
            mask = df_all.apply(lambda x: x.astype(str).str.contains(search_all, case=False)).any(axis=1)
            df_all = df_all[mask]
        st.dataframe(df_all, use_container_width=True, hide_index=True)

    # --- MENU KE-4: PETA MAPS ---
    elif menu_pilihan == "Peta Maps Sumut":
        st.header("🗺️ Sebaran Geografis Guru")
        
        # Judul Kolom Tombol
        col1, col2, _ = st.columns([1, 1, 2])
        with col1:
            st.markdown("### **Guru Kurang**")
            if st.button("🔴 Tampilkan Merah"): st.session_state.map_filter = "Kurang"
        with col2:
            st.markdown("### **Guru Lebih**")
            if st.button("🔵 Tampilkan Biru"): st.session_state.map_filter = "Lebih"

        m = folium.Map(location=[2.1121, 99.1962], zoom_start=8, tiles="CartoDB positron")
        kab_coords = {
            "Kab. Asahan": [2.98, 99.61], "Kota Medan": [3.59, 98.67], "Kab. Dairi": [2.74, 98.31],
            "Kab. Deli Serdang": [3.42, 98.70], "Kab. Karo": [3.11, 98.26], "Kab. Simalungun": [2.90, 99.05]
        }

        for kab, loc in kab_coords.items():
            df_k = df[df['Kabupaten'] == kab]
            if st.session_state.map_filter == "Kurang":
                val = int(df_k['Kurang Guru'].sum())
                if val > 0: folium.CircleMarker(loc, radius=12, color='red', fill=True, popup=f"{kab}: {val} Kurang").addTo(m)
            elif st.session_state.map_filter == "Lebih":
                val = int(df_k.apply(lambda r: max(0, r['Jml Guru']-r['ABK']), axis=1).sum())
                if val > 0: folium.CircleMarker(loc, radius=12, color='blue', fill=True, popup=f"{kab}: {val} Lebih").addTo(m)

        st_folium(m, width=None, height=450)

        if st.session_state.map_filter:
            st.write("---")
            st.markdown("### **Sekolah**")
            list_s = sorted(df[df['Kurang Guru'] > 0]['Nama Sekolah'].unique()) if st.session_state.map_filter == "Kurang" else sorted(df[df['Jml Guru'] > df['ABK']]['Nama Sekolah'].unique())
            sel_s = st.selectbox("Pilih Sekolah:", ["-- Pilih Sekolah --"] + list(list_s))
            if sel_s != "-- Pilih Sekolah --":
                st.info(f"🏢 **Detail: {sel_s}**")
                df_s = df[df['Nama Sekolah'] == sel_s]
                target = df_s[df_s['Kurang Guru'] > 0] if st.session_state.map_filter == "Kurang" else df_s[df_s['Jml Guru'] > df_s['ABK']]
                for _, row in target.iterrows():
                    with st.expander(f"📖 {row['Jabatan']}"):
                        st.write(f"Guru: {int(row['Jml Guru'])} | ABK: {int(row['ABK'])}")

