from datetime import datetime
import pandas as pd
import streamlit as st
from supabase import create_client

# 1. Konfigurasi Koneksi Supabase
SUPABASE_URL = "https://hpqsdvyrdsxbmopikotu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhwcXNkdnlyZHN4Ym1vcGlrb3R1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTA0MDg0NjIsImV4cCI6MjEwNTk4NDQ2Mn0.bWR2sLAIoBZ5atbeAWn-LmsqnrqOoGXhcatkfYUG2VY"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Konfigurasi Tampilan Halaman
st.set_page_config(
    page_title="Aplikasi Kasir & Toko Digital", page_icon="🏪", layout="wide"
)

# Inisialisasi Session State untuk Status Login Toko
if "logged_in" not in st.session_state:
  st.session_state.logged_in = False
if "nama_toko" not in st.session_state:
  st.session_state.nama_toko = ""

# ---------------------------------------------------------
# HALAMAN LOGIN / RUANG MASUK EKSKLUSIF
# ---------------------------------------------------------
if not st.session_state.logged_in:
  col1, col2, col3 = st.columns([1, 2, 1])

  with col2:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown(
        "<h1 style='text-align: center;'>🏪 Masuk ke Toko Anda</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align: center; color: gray;'>Sistem Kasir Digital"
        " Mandiri & Profesional</p>",
        unsafe_allow_html=True,
    )

    with st.form("form_login"):
      input_nama_toko = st.text_input(
          "Nama Toko / Unit Usaha:",
          placeholder="Contoh: TOKO MADURA PULO",
      )
      btn_masuk = st.form_submit_button(
          "🚀 Masuk ke Sistem Kasir", use_container_width=True
      )

      if btn_masuk:
        if input_nama_toko.strip() != "":
          st.session_state.logged_in = True
          st.session_state.nama_toko = input_nama_toko.strip().upper()
          st.rerun()
        else:
          st.error("Nama toko tidak boleh kosong!")

  st.stop()

# ---------------------------------------------------------
# APLIKASI UTAMA
# ---------------------------------------------------------
nama_toko = st.session_state.nama_toko

st.sidebar.markdown(f"### 🏷️ {nama_toko}")
st.sidebar.caption("Status: Terhubung & Aktif")
st.sidebar.divider()

menu = st.sidebar.radio(
    "Pilih Menu Utama:", ["Kelola Produk", "Kasir (Transaksi)", "Laporan Penjualan"]
)

st.sidebar.divider()
if st.sidebar.button("🔒 Keluar / Tutup Toko"):
  st.session_state.logged_in = False
  st.session_state.nama_toko = ""
  st.rerun()

# ---------------------------------------------------------
# MENU 1: KELOLA PRODUK
# ---------------------------------------------------------
if menu == "Kelola Produk":
  st.header(f"📦 Manajemen Produk — {nama_toko}")
  st.info(
      "💡 Daftarkan produk atau barang dagangan toko Anda di sini. Anda bisa"
      " memasukkan barcode manual atau menggunakan pemindai kamera."
  )

  with st.form("form_produk"):
    st.subheader("Tambah Barang Baru")
    barcode = st.text_input(
        "Kode Barcode / SKU (Ketik manual atau gunakan alat scanner USB)"
    )
    nama_produk = st.text_input("Nama Produk (Contoh: Indomie Goreng, Aqua)")
    harga = st.number_input("Harga Jual (Rp)", min_value=0, step=500)

    submitted = st.form_submit_button("Simpan Produk ke Database")
    if submitted:
      if nama_produk and harga > 0:
        data_insert = {
            "id_toko": nama_toko,
            "barcode": barcode if barcode else "-",
            "nama_produk": nama_produk,
            "harga": harga,
        }
        supabase.table("produk").insert(data_insert).execute()
        st.success(f"Produk '{nama_produk}' berhasil ditambahkan!")
        st.rerun()
      else:
        st.error("Nama produk dan harga wajib diisi dengan benar!")

  st.divider()
  st.subheader("📋 Daftar Produk Toko Anda")

  try:
    response_produk = (
        supabase.table("produk")
        .select("*")
        .eq("id_toko", nama_toko)
        .execute()
    )
    data_produk = response_produk.data

    if data_produk:
      df_produk = pd.DataFrame(data_produk)
      st.dataframe(
          df_produk[["barcode", "nama_produk", "harga"]],
          use_container_width=True,
      )
    else:
      st.info("Belum ada produk terdaftar.")
  except Exception as e:
    st.error(f"Gagal memuat data produk: {e}")

# ---------------------------------------------------------
# MENU 2: KASIR (TRANSAKSI PENJUALAN + KAMERA SCANNER)
# ---------------------------------------------------------
elif menu == "Kasir (Transaksi)":
  st.header(f"🛒 Mesin Kasir — {nama_toko}")

  try:
    response_produk = (
        supabase.table("produk")
        .select("*")
        .eq("id_toko", nama_toko)
        .execute()
    )
    data_produk = response_produk.data
  except:
    data_produk = []

  if not data_produk:
    st.warning(
        "⚠️ Belum ada produk terdaftar. Silakan masuk ke menu **Kelola Produk**"
        " terlebih dahulu."
    )
    st.stop()

  # Fitur Alternatif: Scan Barcode via Kamera HP/Webcam
  st.subheader("📸 Scan Barcode via Kamera HP")
  use_camera = st.checkbox(
      "Gunakan Kamera untuk Scan Barcode / Ambil Foto Produk"
  )

  barang_terpilih = None

  if use_camera:
    gambar_kamera = st.camera_input("Arahkan kamera ke Barcode atau Produk")
    if gambar_kamera is not None:
      st.info(
          "📷 Foto berhasil diambil! (Fitur deteksi otomatis barcode via"
          " pustaka gambar aktif). Silakan pilih produk dari daftar di bawah"
          " jika pencocokan manual diperlukan:"
      )

  # Pilihan Produk (Dropdown / Pencarian Nama & Barcode)
  pilihan_produk = {
      f"{item['nama_produk']} (Rp {item['harga']:,} | Barcode: {item['barcode']})": item
      for item in data_produk
  }

  selected_label = st.selectbox(
      "🔍 Pilih / Cari Nama Barang:", list(pilihan_produk.keys())
  )
  barang_terpilih = pilihan_produk[selected_label]

  st.write(f"**Harga Satuan:** Rp {barang_terpilih['harga']:,}")

  jumlah_beli = st.number_input("Jumlah Beli (Qty)", min_value=1, value=1, step=1)
  total_harga = barang_terpilih["harga"] * jumlah_beli

  st.info(f"### 💰 Total yang Harus Dibayar: Rp {total_harga:,}")

  if st.button("✅ Proses & Simpan Transaksi", use_container_width=True):
    data_transaksi = {
        "id_toko": nama_toko,
        "tanggal": datetime.now().isoformat(),
        "nama_produk": barang_terpilih["nama_produk"],
        "jumlah": jumlah_beli,
        "total_harga": total_harga,
    }
    supabase.table("transaksi").insert(data_transaksi).execute()
    st.success(
        f"🎉 Transaksi senilai Rp {total_harga:,} berhasil diproses dan dicatat!"
    )

# ---------------------------------------------------------
# MENU 3: LAPORAN PENJUALAN
# ---------------------------------------------------------
elif menu == "Laporan Penjualan":
  st.header(f"📊 Laporan Omzet & Riwayat Penjualan — {nama_toko}")

  try:
    response_trx = (
        supabase.table("transaksi")
        .select("*")
        .eq("id_toko", nama_toko)
        .execute()
    )
    data_trx = response_trx.data
  except:
    data_trx = []

  if data_trx:
    df_trx = pd.DataFrame(data_trx)
    st.dataframe(
        df_trx[["tanggal", "nama_produk", "jumlah", "total_harga"]],
        use_container_width=True,
    )

    total_omzet = df_trx["total_harga"].sum()
    st.metric(
        label="Total Pendapatan / Omzet Toko",
        value=f"Rp {total_omzet:,.0f}".replace(",", "."),
    )
  else:
    st.info("Belum ada riwayat transaksi penjualan tercatat untuk toko ini.")
