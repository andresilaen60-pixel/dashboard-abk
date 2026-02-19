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
    [data-testid="stSidebar"] .stMarkdown p { color: #012d5e !important; font-weight: 800 !important; }
    
    div.stButton > button {
        width: 100%; border-radius: 10px;
        background: #007bff !important; color: white !important; font-weight: bold;
    }
    div.stButton > button:hover { background: #0056b3 !important; }
    
    /* Tabel Header Styling */
    .table-header {
        background-color: #012d5e;
        color: white;
        padding: 10px;
        border-radius: 5px;
        font-weight: bold;
        text-align: center;
    }
    .center-text { text-align: center; font-weight: bold; }
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

# --- 4. SISTEM LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/d/d2/Coat_of_arms_of_North_Sumatra.svg/1200px-Coat_of_arms_of_North_Sumatra.svg.png", width=100)
        st.header("🔑 Login E-ABK Sumut")
        u = st.text_input("Username").strip()
        p = st.text_input("Password", type="password").strip()
        if st.button("Masuk Sekarang"):
            if u == "admin" and p == "sumut2026":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Username atau Password salah!")
    st.stop()

# --- 5. SETUP DASHBOARD ---
df = load_and_fix_data()
if 'sub_view' not in st.session_state: st.session_state.sub_view = 'LIST_KAB'
if 'menu_aktif' not in st.session_state: st.session_state.menu_aktif = "Data Provinsi"
if 'sel_kab' not in st.session_state: st.session_state.sel_kab = None
if 'sel_sch' not in st.session_state: st.session_state.sel_sch = None
if 'map_filter' not in st.session_state: st.session_state.map_filter = None

if df is not None:
    with st.sidebar:
        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/d/d2/Coat_of_arms_of_North_Sumatra.svg/1200px-Coat_of_arms_of_North_Sumatra.svg.png", width=80)
        st.title("E-ABK SUMUT")
        st.write("---")
        
        def pindah_menu(nama_menu):
            st.session_state.menu_aktif = nama_menu
            st.session_state.sub_view = 'LIST_KAB'
            st.rerun()

        if st.button("🏢 Data Provinsi", use_container_width=True): pindah_menu("Data Provinsi")
        if st.button("📍 Data Kabupaten Kota", use_container_width=True): pindah_menu("Data Kabupaten Kota")
        if st.button("🌐 Data Keseluruhan", use_container_width=True): pindah_menu("Data Keseluruhan")
        if st.button("🗺️ Peta Maps Sumut", use_container_width=True): pindah_menu("Peta Maps Sumut")
        st.write("---")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

    menu_pilihan = st.session_state.menu_aktif

    # --- 6. LOGIKA TAMPILAN ---
    if menu_pilihan == "Data Provinsi":
        st.header("🏢 Rekapitulasi Guru Provinsi")
        c1, c2, c3 = st.columns(3)
        c1.metric("TOTAL GURU", int(df['Jml Guru'].sum()))
        c2.metric("KEPALA SEKOLAH", int(df[df['Jabatan'].str.contains('Kepala Sekolah', case=False, na=False)]['Jml Guru'].sum()))
        c3.metric("KEKURANGAN", int(df['Kurang Guru'].sum()))
        st.write("---")
        st.dataframe(df.groupby('Kabupaten').agg({'Jml Guru':'sum', 'Kurang Guru':'sum'}).reset_index(), use_container_width=True, hide_index=True)

    elif menu_pilihan == "Data Kabupaten Kota":
        if st.session_state.sub_view == 'LIST_KAB':
            st.header("📍 Data Per Kabupaten / Kota")
            
            # --- BAGIAN TOMBOL GRAFIK YANG DIKEMBALIKAN ---
            if st.button("📊 Tampilkan Grafik Analisis Kab/Kota"):
                if 'show_chart_kab' not in st.session_state: st.session_state.show_chart_kab = False
                st.session_state.show_chart_kab = not st.session_state.show_chart_kab
            
            if st.session_state.get('show_chart_kab', False):
                # Menghitung data untuk grafik
                df_chart = df.groupby('Kabupaten').agg({
                    'Jml Guru': 'sum',
                    'Kurang Guru': 'sum'
                }).reset_index()
                
                # Menampilkan Grafik
                st.bar_chart(
                    df_chart.set_index('Kabupaten')[['Jml Guru', 'Kurang Guru']],
                    color=["#0000FF", "#FF0000"] # Biru untuk Guru, Merah untuk Kurang
                )
            # ----------------------------------------------
            
            st.write("---")
            search_k = st.text_input("🔍 Cari Kabupaten...")
            kabs = sorted([k for k in df['Kabupaten'].unique() if k != "Lainnya"])
            if search_k: kabs = [k for k in kabs if search_k.lower() in k.lower()]
            
            for k in kabs:
                df_k = df[df['Kabupaten'] == k]
                c1, c2, c3 = st.columns([2, 1, 1])
                if c1.button(k, key=f"kb_{k}"):
                    st.session_state.sel_kab = k; st.session_state.sub_view = 'LIST_SEKOLAH'; st.rerun()
                c2.write(int(df_k['Jml Guru'].sum()))
                c3.write(int(df_k[df_k['Jabatan'].str.contains('Kepala Sekolah', case=False)]['Jml Guru'].sum()))

        elif st.session_state.sub_view == 'LIST_SEKOLAH':
            st.header(f"🏫 Sekolah di {st.session_state.sel_kab}")
            c1, c2 = st.columns([1, 4])
            with c1:
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                if st.button("⬅ Kembali"): st.session_state.sub_view = 'LIST_KAB'; st.rerun()
            with c2: search_s = st.text_input("🔍 Cari Sekolah...")

            df_kab = df[df['Kabupaten'] == st.session_state.sel_kab].copy()
            df_kab['S_Real'] = df_kab['Jml Guru'] - df_kab['ABK']
            sch_summary = df_kab.groupby('Nama Sekolah').apply(lambda x: pd.Series({'K': abs(x[x['S_Real'] < 0]['S_Real'].sum()), 'L': x[x['S_Real'] > 0]['S_Real'].sum()})).reset_index()
            if search_s: sch_summary = sch_summary[sch_summary['Nama Sekolah'].str.contains(search_s, case=False)]
            
            st.write("---")
            h1, h2, h3 = st.columns([2, 1, 1])
            h1.markdown("**Nama Sekolah**")
            h2.markdown("<p class='center-text'>Kurang</p>", unsafe_allow_html=True)
            h3.markdown("<p class='center-text'>Lebih</p>", unsafe_allow_html=True)
            for i, row in sch_summary.iterrows():
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1:
                    if st.button(row['Nama Sekolah'], key=f"sk_{row['Nama Sekolah']}"):
                        st.session_state.sel_sch = row['Nama Sekolah']; st.session_state.sub_view = 'DETAIL'; st.rerun()
                c2.markdown(f"<p class='center-text' style='color: red;'>🔴 {int(row['K'])}</p>", unsafe_allow_html=True)
                c3.markdown(f"<p class='center-text' style='color: blue;'>🔵 {int(row['L'])}</p>", unsafe_allow_html=True)

        elif st.session_state.sub_view == 'DETAIL':
            st.header(f"🔍 Detail: {st.session_state.sel_sch}")
            if st.button("⬅ Kembali"): st.session_state.sub_view = 'LIST_SEKOLAH'; st.rerun()
            
            st.write("---")
            # Header kolom yang lurus
            h1, h2, h3, h4, = st.columns([2.5, 1, 1, 1])
            h1.markdown("**Jabatan**")
            h2.markdown("**Kebutuhan Guru**")
            h3.markdown("**Jumlah Guru**")
            h4.markdown("**Selisih**")
            st.markdown("<hr style='margin: 10px 0px; border-top: 2px solid #012d5e;'>", unsafe_allow_html=True)

            df_res = df[df['Nama Sekolah'] == st.session_state.sel_sch].copy()
            df_res['Selisih'] = df_res['Jml Guru'] - df_res['ABK']
            
            for _, row in df_res.iterrows():
                c1, c2, c3, c4, = st.columns([2.5, 1, 1, 1])
                c1.write(row['Jabatan'])
                c2.write(str(int(row['ABK'])))
                c3.write(str(int(row['Jml Guru'])))
                
                selisih = int(row['Selisih'])
                s_txt = f"+{selisih}" if selisih > 0 else str(selisih)
                color = "red" if selisih < 0 else "blue" if selisih > 0 else "green"
                c4.markdown(f"<span style='color:{color}; font-weight:bold;'>{s_txt}</span>", unsafe_allow_html=True)
                st.markdown("<hr style='margin: 5px 0px; opacity: 0.2;'>", unsafe_allow_html=True)
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
        m = folium.Map(location=[2.1121, 99.1962], zoom_start=8, tiles="CartoDB positron")
        st_folium(m, width=None, height=450)







