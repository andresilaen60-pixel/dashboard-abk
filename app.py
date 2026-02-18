import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import json

# --- 1. CONFIG HALAMAN ---
st.set_page_config(page_title="Dashboard ABK Sumut 2026", layout="wide")

# --- 2. CSS CUSTOM ---
st.markdown("""
    <style>
    .main { background: linear-gradient(160deg, #f0f9ff 0%, #cbebff 100%); color: #01579b; }
    [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 2px solid #0288d1; }
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
        xls = pd.ExcelFile("data.xlsx", engine='openpyxl')
        df_u = pd.read_excel(xls, sheet_name=0)
        sheet_names = xls.sheet_names
        df_s = pd.read_excel(xls, sheet_name="DAFTAR SEKOLAH" if "DAFTAR SEKOLAH" in sheet_names else 1)
        df_g = pd.read_excel(xls, sheet_name="Data Guru" if "Data Guru" in sheet_names else 2)
        
        df_u.columns = df_u.columns.str.strip()
        df_s.columns = df_s.columns.str.strip()
        df_g.columns = df_g.columns.str.strip()

        df_s_fix = df_s[['NPSN', 'Kabupaten/Kota']].drop_duplicates()
        df = pd.merge(df_u, df_s_fix, on='NPSN', how='left')
        df['Kabupaten'] = df['Kabupaten/Kota'].fillna(df['KABUPATEN BY NAMA SEKOLAH']).fillna("Lainnya")
        df.fillna(0, inplace=True)
        
        df['Keterangan'] = df.apply(lambda r: "Lebih Guru" if r['Jml Guru'] > r['ABK'] else ("Kurang Guru" if r['Jml Guru'] < r['ABK'] else "Sesuai"), axis=1)
        
        return df, df_g
    except Exception as e:
        return None, None

# --- 4. SISTEM LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/d/d2/Coat_of_arms_of_North_Sumatra.svg/1200px-Coat_of_arms_of_North_Sumatra.svg.png", width=100)
        st.header("🔑 Login E-ABK Sumut")
        u_val = st.text_input("Username").strip()
        p_val = st.text_input("Password", type="password").strip()
        if st.button("Masuk Sekarang"):
            if u_val == "admin" and p_val == "sumut2026":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Username atau Password salah!")
    st.stop()

# --- 5. SETUP DASHBOARD ---
df, df_guru = load_and_fix_data()

# Inisialisasi State
for key in ['sub_view', 'menu_aktif', 'view_personil', 'sel_kab', 'sel_sch', 'sel_jabatan']:
    if key not in st.session_state:
        if key == 'sub_view': st.session_state[key] = 'LIST_KAB'
        elif key == 'menu_aktif': st.session_state[key] = "Data Provinsi"
        else: st.session_state[key] = None

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/d/d2/Coat_of_arms_of_North_Sumatra.svg/1200px-Coat_of_arms_of_North_Sumatra.svg.png", width=80)
    st.title("E-ABK SUMUT")
    st.write("---")
    
    def nav(m):
        st.session_state.menu_aktif = m
        st.session_state.sub_view = 'LIST_KAB'
        st.session_state.view_personil = False
        st.rerun()

    if st.button("🏢 Data Provinsi"): nav("Data Provinsi")
    if st.button("📍 Data Kabupaten Kota"): nav("Data Kabupaten Kota")
    if st.button("🌐 Data Keseluruhan"): nav("Data Keseluruhan")
    if st.button("🗺️ Peta Maps Sumut"): nav("Peta Maps Sumut")
    
    st.write("---")
    if st.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.rerun()

# --- 6. LOGIKA TAMPILAN ---
menu = st.session_state.menu_aktif

if df is not None:
    if menu == "Data Provinsi":
        st.header("🏢 Rekapitulasi Guru Provinsi")
        c1, c2, c3 = st.columns(3)
        c1.metric("TOTAL GURU", int(df['Jml Guru'].sum()))
        c2.metric("KEPALA SEKOLAH", int(df[df['Jabatan'].str.contains('Kepala Sekolah', case=False, na=False)]['Jml Guru'].sum()))
        c3.metric("KEKURANGAN", int(df['Kurang Guru'].sum()))
        st.write("---")
        st.dataframe(df.groupby('Kabupaten').agg({'Jml Guru':'sum', 'Kurang Guru':'sum'}).reset_index(), use_container_width=True, hide_index=True)

    elif menu == "Data Kabupaten Kota":
        if st.session_state.sub_view == 'LIST_KAB':
            st.header("📍 Data Per Kabupaten / Kota")
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
            if st.button("⬅ Kembali"): st.session_state.sub_view = 'LIST_KAB'; st.rerun()
            search_s = st.text_input("🔍 Cari Sekolah...")
            
            df_kab = df[df['Kabupaten'] == st.session_state.sel_kab].copy()
            df_kab['S_Real'] = df_kab['Jml Guru'] - df_kab['ABK']
            sch_summary = df_kab.groupby('Nama Sekolah').apply(lambda x: pd.Series({'K': abs(x[x['S_Real'] < 0]['S_Real'].sum()), 'L': x[x['S_Real'] > 0]['S_Real'].sum()})).reset_index()
            if search_s: sch_summary = sch_summary[sch_summary['Nama Sekolah'].str.contains(search_s, case=False)]
            
            for _, row in sch_summary.iterrows():
                c1, c2, c3 = st.columns([2, 1, 1])
                if c1.button(row['Nama Sekolah'], key=f"sk_{row['Nama Sekolah']}"):
                    st.session_state.sel_sch = row['Nama Sekolah']; st.session_state.sub_view = 'DETAIL'; st.rerun()
                c2.write(f"🔴 {int(row['K'])}"); c3.write(f"🔵 {int(row['L'])}")

        elif st.session_state.sub_view == 'DETAIL':
            st.header(f"🔍 Detail: {st.session_state.sel_sch}")
            if st.button("⬅ Kembali"):
                if st.session_state.view_personil: st.session_state.view_personil = False
                else: st.session_state.sub_view = 'LIST_SEKOLAH'
                st.rerun()

            if not st.session_state.view_personil:
                df_res = df[df['Nama Sekolah'] == st.session_state.sel_sch].copy()
                for i, row in df_res.iterrows():
                    c1, c2, c3 = st.columns([2, 1, 1])
                    c1.write(row['Jabatan'])
                    c2.write(f"ABK: {int(row['ABK'])}")
                    if c3.button(f"Guru: {int(row['Jml Guru'])}", key=f"bp_{i}"):
                        st.session_state.sel_jabatan = row['Jabatan']
                        st.session_state.view_personil = True
                        st.rerun()
            else:
                st.subheader(f"👥 Personil: {st.session_state.sel_jabatan}")
                # Logika pencarian personil yang aman
                df_guru['S_UP'] = df_guru['Nama Sekolah'].str.upper().str.strip()
                df_guru['J_UP'] = df_guru['Jabatan'].str.upper().str.strip()
                match = df_guru[(df_guru['S_UP'] == st.session_state.sel_sch.upper().strip()) & (df_guru['J_UP'] == st.session_state.sel_jabatan.upper().strip())]
                if not match.empty: st.table(match[['Nama', 'NIP', 'NIK']])
                else: st.warning("Data personil tidak ditemukan di Sheet 3.")

    elif menu == "Data Keseluruhan":
        st.header("🌐 Seluruh Data Pemetaan")
        search_all = st.text_input("🔍 Cari data...")
        df_all = df[['Kabupaten', 'Nama Sekolah', 'Jabatan', 'Jml Guru', 'Kurang Guru', 'Keterangan']].copy()
        if search_all:
            mask = df_all.apply(lambda x: x.astype(str).str.contains(search_all, case=False)).any(axis=1)
            df_all = df_all[mask]
        st.dataframe(df_all, use_container_width=True, hide_index=True)

    elif menu == "Peta Maps Sumut":
        st.header("🗺️ Sebaran Geografis Guru")
        m = folium.Map(location=[2.1121, 99.1962], zoom_start=8, tiles="CartoDB positron")
        st_folium(m, width=None, height=450)
