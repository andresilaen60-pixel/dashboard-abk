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
    .custom-table { width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; color: black; margin-top: 10px; }
    .custom-table th { background: #012d5e; color: white; padding: 12px; text-align: left; }
    .custom-table td { padding: 10px; border-bottom: 1px solid #ddd; }
    .bg-kurang { background-color: rgba(255, 0, 0, 0.1) !important; }
    .bg-lebih { background-color: rgba(0, 0, 255, 0.1) !important; }
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

# --- 4. INISIALISASI SESSION STATE ---
if 'sub_view' not in st.session_state: st.session_state.sub_view = 'LIST_KAB'
if 'sel_kab' not in st.session_state: st.session_state.sel_kab = None
if 'sel_sch' not in st.session_state: st.session_state.sel_sch = None
if 'map_filter' not in st.session_state: st.session_state.map_filter = None

df = load_and_fix_data()

if df is not None:
    # --- 5. SIDEBAR MENU & LOGIKA RESET ---
    with st.sidebar:
        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/d/d2/Coat_of_arms_of_North_Sumatra.svg/1200px-Coat_of_arms_of_North_Sumatra.svg.png", width=80)
        st.title("E-ABK SUMUT")
        st.write("---")
        menu_pilihan = st.radio("SISTEM NAVIGASI", ["Data Provinsi", "Data Kabupaten Kota", "Data Keseluruhan", "Peta Maps Sumut"])
        
        if 'last_menu' not in st.session_state: st.session_state.last_menu = menu_pilihan
        if menu_pilihan != st.session_state.last_menu:
            st.session_state.last_menu = menu_pilihan
            st.session_state.sub_view = 'LIST_KAB'
            st.session_state.map_filter = None
            st.rerun()

    # --- 6. TAMPILAN BERDASARKAN MENU ---

    # A. DATA PROVINSI
    if menu_pilihan == "Data Provinsi":
        st.header("🏢 Rekapitulasi Guru Provinsi")
        c1, c2, c3 = st.columns(3)
        c1.metric("TOTAL GURU", int(df['Jml Guru'].sum()))
        c2.metric("KEPALA SEKOLAH", int(df[df['Jabatan'].str.contains('Kepala Sekolah',
