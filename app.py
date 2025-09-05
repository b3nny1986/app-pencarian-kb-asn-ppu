import streamlit as st
import pandas as pd
import os

# ===============================
# KONFIGURASI FILE CSV
# ===============================
DATA_DIR = "data"
DATA_MASTER = os.path.join(DATA_DIR, "data_master.csv")
DATA_INSTANSI = os.path.join(DATA_DIR, "data_instansi.csv")
HASIL_PENCARIAN = os.path.join(DATA_DIR, "hasil_pencarian.csv")

HEADER = [
    "NAMA_INSTANSI", "NOPOL", "NAMA", "ALAMAT",
    "TANGGAL_PKB", "TANGGAL_STNK", "STATUS_KB", "STATUS_BAYAR"
]

# ===============================
# UTILITAS
# ===============================
def ensure_dirs_and_files():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(HASIL_PENCARIAN):
        pd.DataFrame(columns=HEADER).to_csv(HASIL_PENCARIAN, index=False)

def load_csv(path, columns=None):
    if not os.path.exists(path):
        return pd.DataFrame(columns=columns or [])
    try:
        df = pd.read_csv(path)
        if columns:
            for c in columns:
                if c not in df.columns:
                    df[c] = ""
            df = df[columns]
        return df
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=columns or [])
    except Exception as e:
        st.error(f"Gagal membaca {path}: {e}")
        return pd.DataFrame(columns=columns or [])

def safe_to_csv(df, path):
    try:
        df.to_csv(path, index=False)
        return True, f"💾 DEBUG: simpan {path}, total baris = {len(df)}"
    except Exception as e:
        return False, f"❌ Gagal menyimpan {path}: {e}"

def append_rows_dedup(rows_df):
    existing = load_csv(HASIL_PENCARIAN, columns=HEADER)
    before = len(existing)
    rows_df = rows_df.copy()[HEADER]
    combined = pd.concat([existing, rows_df], ignore_index=True)
    combined.drop_duplicates(
        subset=["NAMA_INSTANSI", "NOPOL", "NAMA", "ALAMAT"],
        keep="first", inplace=True
    )
    after = len(combined)
    ok, msg = safe_to_csv(combined, HASIL_PENCARIAN)
    return ok, msg, before, after

def reset_csv():
    df = pd.DataFrame(columns=HEADER)
    ok, msg = safe_to_csv(df, HASIL_PENCARIAN)
    if ok:
        st.success("✅ hasil_pencarian.csv di-reset (header saja)")
    st.write(msg)

# ===============================
# INISIALISASI
# ===============================
st.set_page_config(page_title="Pusat Informasi Pajak Kendaraan", layout="wide")
ensure_dirs_and_files()

if "hasil" not in st.session_state:
    st.session_state["hasil"] = pd.DataFrame()
if "instansi_selected" not in st.session_state:
    st.session_state["instansi_selected"] = None
if "last_search" not in st.session_state:
    st.session_state["last_search"] = {"nama": "", "alamat": "", "jumlah": 0}

df_master = load_csv(DATA_MASTER, columns=[
    "NOPOL","NAMA","ALAMAT","TANGGAL_PKB","TANGGAL_STNK","STATUS_KB","STATUS_BAYAR"
])
df_instansi = load_csv(DATA_INSTANSI, columns=["NAMA_INSTANSI"])
df_hasil_now = load_csv(HASIL_PENCARIAN, columns=HEADER)

# ===============================
# SIDEBAR & MENU NAVIGASI
# ===============================
st.sidebar.header("🔎 Pencarian Data")
menu = st.sidebar.radio("📁 Navigasi Halaman", ["🔍 Pencarian", "📂 Laporan Tersimpan"])

instansi = st.sidebar.selectbox(
    "Pilih Instansi",
    df_instansi["NAMA_INSTANSI"].tolist() if not df_instansi.empty else [],
    index=0 if not df_instansi.empty else None,
)

nama = st.sidebar.text_input("Masukkan Nama")
alamat = st.sidebar.text_input("Masukkan Alamat")

if st.sidebar.button("Cari"):
    if df_master.empty:
        st.error(f"File master kosong/tdk ditemukan: {DATA_MASTER}")
    else:
        kondisi = pd.Series(True, index=df_master.index)
        if nama.strip():
            kondisi &= df_master["NAMA"].str.contains(nama, case=False, na=False)
        if alamat.strip():
            kondisi &= df_master["ALAMAT"].str.contains(alamat, case=False, na=False)

        hasil = df_master[kondisi].copy()
        st.session_state["hasil"] = hasil
        st.session_state["instansi_selected"] = instansi
        st.session_state["last_search"] = {
            "nama": nama.strip(),
            "alamat": alamat.strip(),
            "jumlah": len(hasil),
        }

# ===============================
# HALAMAN: PENCARIAN
# ===============================
if menu == "🔍 Pencarian":
    st.title("🚗 Pusat Informasi Pajak Kendaraan (ASN PPU)")
    colA, colB = st.columns(2)
    with colA:
        if st.button("🔄 Reset CSV (hasil_pencarian.csv)"):
            reset_csv()
            df_hasil_now = load_csv(HASIL_PENCARIAN, columns=HEADER)
    with colB:
        st.info(f"📦 File hasil saat ini: **{len(df_hasil_now)} baris**")

    st.subheader("📌 Hasil Pencarian (tidak otomatis tersimpan)")
    ls = st.session_state["last_search"]
    st.caption(f"Debug: last search → nama='{ls['nama']}', alamat='{ls['alamat']}', jumlah={ls['jumlah']}'")

    hasil = st.session_state["hasil"]
    instansi_selected = st.session_state["instansi_selected"]

    if hasil is not None and not hasil.empty:
        st.write(f"Menampilkan **{len(hasil)}** baris. Instansi terpilih: **{instansi_selected}**")
        st.dataframe(hasil)

        if st.button("💾 Simpan SEMUA hasil pencarian ke CSV (tanpa duplikat)"):
            if not instansi_selected:
                st.warning("Pilih instansi terlebih dahulu.")
            else:
                to_save = hasil.copy()
                to_save.insert(0, "NAMA_INSTANSI", instansi_selected)
                ok, msg, before, after = append_rows_dedup(to_save)
                st.write(msg)
                st.info(f"🐞 DEBUG: sebelum={before}, sesudah={after}, bertambah={after-before}")
                if ok:
                    st.success("✅ Penyimpanan selesai.")

        st.markdown("---")
        st.markdown("### ➕ Tambah Per Baris (klik tombol per baris)")

        for i, row in hasil.iterrows():
            with st.container():
                st.write(
                    f"**{row['NOPOL']}** | {row['NAMA']} | {row['ALAMAT']} | "
                    f"PKB: {row['TANGGAL_PKB']} | STNK: {row['TANGGAL_STNK']} | "
                    f"KB: {row['STATUS_KB']} | Bayar: {row['STATUS_BAYAR']}"
                )
                btn_key = f"add_{i}_{row['NOPOL']}"
                if st.button("➕ Tambah baris ini ke CSV", key=btn_key):
                    if not instansi_selected:
                        st.warning("Pilih instansi terlebih dahulu.")
                    else:
                        new_row = pd.DataFrame([{
                            "NAMA_INSTANSI": instansi_selected,
                            "NOPOL": row["NOPOL"],
                            "NAMA": row["NAMA"],
                            "ALAMAT": row["ALAMAT"],
                            "TANGGAL_PKB": row["TANGGAL_PKB"],
                            "TANGGAL_STNK": row["TANGGAL_STNK"],
                            "STATUS_KB": row["STATUS_KB"],
                            "STATUS_BAYAR": row["STATUS_BAYAR"],
                        }])
                        ok, msg, before, after = append_rows_dedup(new_row)
                        st.write(msg)
                        st.info(f"🐞 DEBUG: sebelum={before}, sesudah={after}, bertambah={after-before}")
                        if ok:
                            st.success(f"✅ Baris {row['NOPOL']} disimpan (tanpa duplikat).")
    else:
        st.info("Belum ada hasil pencarian. Silakan gunakan form di sidebar.")

# ===============================
# HALAMAN: LAPORAN TERSIMPAN
# ===============================
elif menu == "📂 Laporan Tersimpan":
    st.title("📂 Laporan hasil_pencarian.csv")
    df_hasil_now = load_csv(HASIL_PENCARIAN, columns=HEADER)
    if not df_hasil_now.empty:
        st.dataframe(df_hasil_now)
        st.download_button(
    label="⬇️ Download CSV",
    data=df_hasil_now.to_csv(index=False).encode("utf-8"),
    file_name="hasil_pencarian.csv",
    mime="text/csv"
)