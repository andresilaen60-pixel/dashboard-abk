import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# --- 1. CONFIG HALAMAN ---
st.set_page_config(page_title="Dashboard ABK Sumut 2026", layout="wide")

# --- 2. CSS CUSTOM ---
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
    .custom-table td { padding: 10px; border-bottom: 1px solid #ddd; }
    .bg-kurang { background-color: rgba(255, 0, 0, 0.1) !important; }
    .bg-lebih { background-color: rgba(0, 0, 255, 0.1) !important; }
    .center-text { text-align: center; font-weight: bold; margin-bottom: 0px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. LOAD DATA ---
@st.cache_data
def load_and_fix_data():
    try:
        xls = pd.ExcelFile("data.xlsx", engine='openpyxl')
        df_u = pd.read_excel(xls, sheet_name=0)
        sheet_names = xls.sheet_names
        df_s = pd.read_excel(xls, sheet_name="DAFTAR SEKOLAH" if "DAFTAR SEKOLAH" in sheet_names else 1)
        
        # MEMBACA SHEET 3 (DATA GURU)
        df_g = pd.read_excel(xls, sheet_name="Data Guru" if "Data Guru" in sheet_names else 2)
        
        df_u.columns = df_u.columns.str.strip()
        df_s.columns = df_s.columns.str.strip()
        df_g.columns = df_g.columns.str.strip() # Bersihkan spasi di judul kolom

        df_s_fix = df_s[['NPSN', 'Kabupaten/Kota']].drop_duplicates()
        df = pd.merge(df_u, df_s_fix, on='NPSN', how='left')
        df['Kabupaten'] = df['Kabupaten/Kota'].fillna(df['KABUPATEN BY NAMA SEKOLAH']).fillna("Lainnya")
        df.fillna(0, inplace=True)
        
        def cek_status(row):
            if row['Jml Guru'] > row['ABK']: return "Lebih Guru"
            elif row['Jml Guru'] < row['ABK']: return "Kurang Guru"
            else: return "Sesuai"
        df['Keterangan'] = df.apply(cek_status, axis=1)
        
        # Kembalikan dua dataframe: data utama dan data guru
        return df, df_g
    except Exception as e:
        st.error(f"Eror Memuat Data: {e}")
        return None, None
        
# --- 4. SISTEM LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/d/d2/Coat_of_arms_of_North_Sumatra.svg/1200px-Coat_of_arms_of_North_Sumatra.svg.png", width=100)
        st.header("🔑 Login E-ABK Sumut")
        u_input = st.text_input("Username").strip()
        p_input = st.text_input("Password", type="password").strip()
        
        if st.button("Masuk Sekarang", use_container_width=True):
            # Cek login dengan sangat simpel
            if u_input == "admin" and p_input == "sumut2026":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Username atau Password salah!")
    st.stop() # Paksa berhenti di sini jika belum login

# --- 5. SETUP DASHBOARD ---
df, df_guru = load_and_fix_data()
if 'sub_view' not in st.session_state: st.session_state.sub_view = 'LIST_KAB'
if 'menu_aktif' not in st.session_state: st.session_state.menu_aktif = "Data Provinsi"
if 'view_personil' not in st.session_state: st.session_state.view_personil = False
if 'sel_npsn' not in st.session_state: st.session_state.sel_npsn = None
# --- 6. LOGIKA MENU ---
if df is not None:
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
            if st.button("📊 Tampilkan Grafik Analisis Kab/Kota"):
                if 'show_chart_kab' not in st.session_state: st.session_state.show_chart_kab = False
                st.session_state.show_chart_kab = not st.session_state.show_chart_kab
            
            if st.session_state.get('show_chart_kab', False):
                df_c = df.groupby('Kabupaten').agg({'Jml Guru':'sum', 'Kurang Guru':'sum'}).reset_index()
                st.bar_chart(df_c.set_index('Kabupaten')[['Jml Guru', 'Kurang Guru']], color=["#0000FF", "#FF0000"])
            
            st.write("---")
            search_k = st.text_input("🔍 Cari Kabupaten...")
            kabs = sorted([k for k in df['Kabupaten'].unique() if k != "Lainnya"])
            if search_k: kabs = [k for k in kabs if search_k.lower() in k.lower()]
            for k in kabs:
                df_k = df[df['Kabupaten'] == k]
                c1, c2, c3 = st.columns([2, 1, 1])
                if c1.button(k, key=f"kb_{k}"):
                    st.session_state.sel_kab = k; st.session_state.sub_view = 'LIST_SEKOLAH'; st.rerun()
                c2.write(int(df_k['Jml Guru'].sum())); c3.write(int(df_k[df_k['Jabatan'].str.contains('Kepala Sekolah', case=False)]['Jml Guru'].sum()))

        elif st.session_state.sub_view == 'LIST_SEKOLAH':
            st.header(f"🏫 Sekolah di {st.session_state.sel_kab}")
            c1, c2 = st.columns([1, 4])
            with c1:
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                if st.button("⬅ Kembali"): st.session_state.sub_view = 'LIST_KAB'; st.rerun()
            with c2: search_s = st.text_input("🔍 Cari Sekolah...")

            df_kab = df[df['Kabupaten'] == st.session_state.sel_kab].copy()
            df_kab['Selisih_Real'] = df_kab['Jml Guru'] - df_kab['ABK']
            sch_summary = df_kab.groupby('Nama Sekolah').apply(lambda x: pd.Series({'Kurang': abs(x[x['Selisih_Real'] < 0]['Selisih_Real'].sum()), 'Lebih': x[x['Selisih_Real'] > 0]['Selisih_Real'].sum()})).reset_index()
            if search_s: sch_summary = sch_summary[sch_summary['Nama Sekolah'].str.contains(search_s, case=False)]
            
            st.write("---")
            h1, h2, h3 = st.columns([2, 1, 1])
            h1.markdown("**Nama Sekolah**")
            h2.markdown("<p class='center-text'>Guru Kurang</p>", unsafe_allow_html=True)
            h3.markdown("<p class='center-text'>Guru Lebih</p>", unsafe_allow_html=True)
            for i, row in sch_summary.iterrows():
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1:
                    if st.button(row['Nama Sekolah'], key=f"sk_{row['Nama Sekolah']}"):
                        st.session_state.sel_sch = row['Nama Sekolah']; st.session_state.sub_view = 'DETAIL'; st.session_state.view_personil = False; st.rerun()
                with c2: st.markdown(f"<p class='center-text' style='color: red;'>🔴 {int(row['Kurang'])}</p>", unsafe_allow_html=True)
                with c3: st.markdown(f"<p class='center-text' style='color: blue;'>🔵 {int(row['Lebih'])}</p>", unsafe_allow_html=True)

        elif st.session_state.sub_view == 'DETAIL':
            st.header(f"🔍 Detail: {st.session_state.sel_sch}")
            
            # 1. Tombol Kembali
            if st.button("⬅ Kembali"):
                if st.session_state.get('view_personil', False):
                    st.session_state.view_personil = False
                else:
                    st.session_state.sub_view = 'LIST_SEKOLAH'
                st.rerun()

            st.write("---")

            if not st.session_state.get('view_personil', False):
                # CSS khusus untuk membuat tombol angka terlihat seperti link
                st.markdown("""
                    <style>
                    div.stButton > button[key^="btn_p_"] {
                        background-color: transparent !important;
                        color: #007bff !important;
                        border: none !important;
                        text-decoration: underline !important;
                        padding: 0 !important;
                        font-size: 16px !important;
                        height: auto !important;
                        width: auto !important;
                        display: inline-block !important;
                    }
                    div.stButton > button[key^="btn_p_"]:hover {
                        color: #0056b3 !important;
                        background-color: transparent !important;
                    }
                    </style>
                """, unsafe_allow_html=True)

                df_res = df[df['Nama Sekolah'] == st.session_state.sel_sch].copy()
                df_res['Selisih'] = df_res['Jml Guru'] - df_res['ABK']
                
                # Header Tabel Manual agar rapi
                h1, h2, h3, h4 = st.columns([2, 1, 1, 1])
                h1.markdown("**Jabatan**")
                h2.markdown("**Kebutuhan**")
                h3.markdown("**Jml Guru**")
                h4.markdown("**Selisih**")
                st.write("---")

                for i, row in df_res.iterrows():
                    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                    c1.write(row['Jabatan'])
                    c2.write(f"{int(row['ABK'])}")
                    
                    with c3:
                        if row['Jml Guru'] > 0:
                            # Tombol dengan Key unik agar bisa dimanipulasi CSS
                            if st.button(f"{int(row['Jml Guru'])}", key=f"btn_p_{i}_{row['Jabatan']}"):
                                st.session_state.sel_jabatan = row['Jabatan']
                                st.session_state.view_personil = True
                                st.rerun()
                        else:
                            st.write("0")
                    
                    # Selisih dengan warna
                    s_val = f"+{int(row['Selisih'])}" if row['Selisih'] > 0 else str(int(row['Selisih']))
                    color = "#d32f2f" if row['Selisih'] < 0 else "#1976d2" if row['Selisih'] > 0 else "#000"
                    c4.markdown(f"<p style='color:{color}; font-weight:bold; margin:0;'>{s_val}</p>", unsafe_allow_html=True)
                    st.write("<div style='margin-top: -10px;'></div>", unsafe_allow_html=True) # Merapatkan baris

            else:
                # --- TAMPILAN DATA PERSONIL (SHEET 3) ---
                st.subheader(f"👥 Daftar Guru: {st.session_state.sel_jabatan}")
                
                # Kita buat perbandingan yang tidak sensitif huruf besar/kecil (Case Insensitive)
                # Dan kita buang spasi di awal/akhir (Strip)
                df_guru['Nama Sekolah_Clean'] = df_guru['Nama Sekolah'].str.strip().str.upper()
                df_guru['Jabatan_Clean'] = df_guru['Jabatan'].str.strip().str.upper()
                
                target_sekolah = st.session_state.sel_sch.strip().upper()
                target_jabatan = st.session_state.sel_jabatan.strip().upper()

                detail_p = df_guru[
                    (df_guru['Nama Sekolah_Clean'] == target_sekolah) & 
                    (df_guru['Jabatan_Clean'] == target_jabatan)
                ]
                
                if not detail_p.empty:
                    # Menampilkan Nama, NIP, NIK
                    # Kita pakai kolom asli untuk ditampilkan
                    cols = [c for c in ['Nama', 'NIP', 'NIK'] if c in df_guru.columns]
                    st.table(detail_p[cols].reset_index(drop=True))
                else:
                    st.warning(f"Data tidak ditemukan untuk Jabatan: {st.session_state.sel_jabatan}")
                    # FITUR DEBUG (Hanya untuk Andre cek)
                    with st.expander("Klik untuk cek masalah data (Debug)"):
                        st.write(f"Mencari Sekolah: '{target_sekolah}'")
                        st.write(f"Mencari Jabatan: '{target_jabatan}'")
                        st.write("Data yang tersedia di Sheet 3 (5 baris pertama):")
                        st.write(df_guru[['Nama Sekolah', 'Jabatan']].head())

    elif menu_pilihan == "Data Keseluruhan":
        st.header("🌐 Seluruh Data Pemetaan")
        search_all = st.text_input("🔍 Cari data...")
        df_all = df[['Kabupaten', 'Nama Sekolah', 'Jabatan', 'Jml Guru', 'Kurang Guru', 'Keterangan']].copy()
        if search_all:
            mask = df_all.apply(lambda x: x.astype(str).str.contains(search_all, case=False)).any(axis=1)
            df_all = df_all[mask]
        st.dataframe(df_all, use_container_width=True, hide_index=True)

    elif menu_pilihan == "Peta Maps Sumut":
        st.header("🗺️ Sebaran Geografis Guru")
        c1, c2, _ = st.columns([1, 1, 2])
        with c1:
            if st.button("🔴 Tampilkan Merah"): st.session_state.map_filter = "Kurang"
        with c2:
            if st.button("🔵 Tampilkan Biru"): st.session_state.map_filter = "Lebih"
        m = folium.Map(location=[2.1121, 99.1962], zoom_start=8, tiles="CartoDB positron")
        kab_coords = {"Kab. Asahan": [2.98, 99.61], "Kota Medan": [3.59, 98.67], "Kab. Dairi": [2.74, 98.31], "Kab. Deli Serdang": [3.42, 98.70], "Kab. Karo": [3.11, 98.26], "Kab. Simalungun": [2.90, 99.05]}
        for kab, loc in kab_coords.items():
            df_k = df[df['Kabupaten'] == kab]
            if st.session_state.get('map_filter') == "Kurang":
                v = int(df_k['Kurang Guru'].sum())
                if v > 0: folium.CircleMarker(loc, radius=12, color='red', fill=True, popup=f"{kab}: {v} Kurang").addTo(m)
            elif st.session_state.get('map_filter') == "Lebih":
                v = int(df_k.apply(lambda r: max(0, r['Jml Guru']-r['ABK']), axis=1).sum())
                if v > 0: folium.CircleMarker(loc, radius=12, color='blue', fill=True, popup=f"{kab}: {v} Lebih").addTo(m)
        st_folium(m, width=None, height=450)








