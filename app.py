import streamlit as st
import pandas as pd

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
    
    /* GAYA TABEL HTML & TOOLTIP */
    .custom-table { width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; color: black; margin-top: 10px; }
    .custom-table th { background: #012d5e; color: white; padding: 12px; text-align: left; }
    .custom-table td { padding: 10px; border-bottom: 1px solid #ddd; position: relative; }
    .bg-kurang { background-color: rgba(255, 0, 0, 0.1) !important; }
    .bg-lebih { background-color: rgba(0, 0, 255, 0.1) !important; }
    .tooltiptext {
        visibility: hidden; width: 280px; background-color: #333; color: #fff; text-align: center;
        border-radius: 6px; padding: 10px; position: absolute; z-index: 100;
        bottom: 125%; left: 50%; margin-left: -140px; opacity: 0; transition: opacity 0.3s;
    }
    .custom-table td:hover .tooltiptext { visibility: visible; opacity: 1; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. LOAD DATA ---
@st.cache_data
def load_and_fix_data():
    try:
        xls = pd.ExcelFile("data.xlsx")
        df_u = pd.read_excel(xls, sheet_name=0)
        df_s = pd.read_excel(xls, sheet_name="DAFTAR SEKOLAH")
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

# --- 4. INISIALISASI SESSION STATE (AGAR TIDAK ERROR) ---
if 'sub_view' not in st.session_state:
    st.session_state.sub_view = 'LIST_KAB'
if 'sel_kab' not in st.session_state:
    st.session_state.sel_kab = None
if 'sel_sch' not in st.session_state:
    st.session_state.sel_sch = None

df = load_and_fix_data()

if df is not None:
    # --- 5. SIDEBAR MENU & LOGIKA RESET ---
    with st.sidebar:
        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/d/d2/Coat_of_arms_of_North_Sumatra.svg/1200px-Coat_of_arms_of_North_Sumatra.svg.png", width=80)
        st.title("E-ABK SUMUT")
        st.write("---")
        
        # Pilihan Menu
        menu_pilihan = st.radio("SISTEM NAVIGASI", ["Data Provinsi", "Data Kabupaten Kota", "Data Keseluruhan"])
        
        # Logika Reset: Jika user pindah menu utama, kembalikan tampilan sub-menu ke awal
        if 'last_menu' not in st.session_state:
            st.session_state.last_menu = menu_pilihan
        
        if menu_pilihan != st.session_state.last_menu:
            st.session_state.last_menu = menu_pilihan
            st.session_state.sub_view = 'LIST_KAB'
            st.rerun()

    # --- 6. TAMPILAN BERDASARKAN MENU ---

    # A. DATA PROVINSI
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
            search_k = st.text_input("🔍 Cari Kabupaten...")
            kabs = sorted([k for k in df['Kabupaten'].unique() if k != "Lainnya"])
            if search_k: kabs = [k for k in kabs if search_k.lower() in k.lower()]
            
            h1, h2, h3 = st.columns([2, 1, 1]); h1.write("**Kabupaten**"); h2.write("**Guru**"); h3.write("**KS**")
            for k in kabs:
                df_k = df[df['Kabupaten'] == k]
                c1, c2, c3 = st.columns([2, 1, 1])
                if c1.button(k, key=f"kb_{k}"):
                    st.session_state.sel_kab = k; st.session_state.sub_view = 'LIST_SEKOLAH'; st.rerun()
                c2.write(int(df_k['Jml Guru'].sum()))
                c3.write(int(df_k[df_k['Jabatan'].str.contains('Kepala Sekolah', case=False)]['Jml Guru'].sum()))

        elif st.session_state.sub_view == 'LIST_SEKOLAH':
            st.header(f"🏫 Sekolah di {st.session_state.sel_kab}")
            if st.button("⬅ Kembali"): st.session_state.sub_view = 'LIST_KAB'; st.rerun()
            search_s = st.text_input("🔍 Cari Sekolah...")
            df_kab = df[df['Kabupaten'] == st.session_state.sel_kab]
            sch_list = df_kab.groupby('Nama Sekolah').apply(lambda x: pd.Series({'Kurang': x['Kurang Guru'].sum(), 'Lebih': x.apply(lambda r: max(0, r['Jml Guru']-r['ABK']), axis=1).sum()})).reset_index()
            if search_s: sch_list = sch_list[sch_list['Nama Sekolah'].str.contains(search_s, case=False)]
            
            for _, row in sch_list.iterrows():
                c1, c2, c3 = st.columns([2, 1, 1])
                if c1.button(row['Nama Sekolah'], key=f"sk_{row['Nama Sekolah']}"):
                    st.session_state.sel_sch = row['Nama Sekolah']; st.session_state.sub_view = 'DETAIL'; st.rerun()
                c2.write(f"🔴 {int(row['Kurang'])}"); c3.write(f"🔵 {int(row['Lebih'])}")

        elif st.session_state.sub_view == 'DETAIL':
            st.header(f"🔍 Detail: {st.session_state.sel_sch}")
            if st.button("⬅ Kembali"): st.session_state.sub_view = 'LIST_SEKOLAH'; st.rerun()
            df_res = df[df['Nama Sekolah'] == st.session_state.sel_sch].copy()
            df_res['Selisih'] = df_res['Jml Guru'] - df_res['ABK']
            
            html = "<table class='custom-table'><tr><th>Jabatan</th><th>Kebutuhan</th><th>Jumlah Guru</th><th>Selisih</th><th>Keterangan</th></tr>"
            for _, row in df_res.iterrows():
                s_val = f"+{int(row['Selisih'])}" if row['Selisih'] > 0 else str(int(row['Selisih']))
                cls = "bg-kurang" if row['Selisih'] < 0 else "bg-lebih" if row['Selisih'] > 0 else ""
                msg = f"Posisi {row['Jabatan']} tersedia" if row['Selisih'] < 0 else f"Kuota {row['Jabatan']} penuh"
                html += f"<tr class='{cls}'><td>{row['Jabatan']}</td><td>{int(row['ABK'])}</td><td>{int(row['Jml Guru'])}</td><td>{s_val}</td><td>{row['Keterangan']}<span class='tooltiptext'>{msg}</span></td></tr>"
            st.markdown(html + "</table>", unsafe_allow_html=True)

    # C. DATA KESELURUHAN
    elif menu_pilihan == "Data Keseluruhan":
        st.header("🌐 Seluruh Data Pemetaan")
        search_all = st.text_input("🔍 Cari data...")
        df_all = df[['Kabupaten', 'Nama Sekolah', 'Jabatan', 'Jml Guru', 'Kurang Guru', 'Keterangan']].copy()
        if search_all:
            mask = df_all.apply(lambda x: x.astype(str).str.contains(search_all, case=False)).any(axis=1)
            df_all = df_all[mask]
        st.dataframe(df_all, use_container_width=True, hide_index=True)

    # D. PETA MAPS SUMUT
   elif menu_pilihan == "Peta Maps Sumut":
import folium
from streamlit_folium import st_folium
st.header("Peta Sebaran Guru Sumut")
    


