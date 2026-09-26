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
    page_title="Aplikasi Kasir Toko Madura", page_icon="🏪", layout="wide"
)

st.title("🏪 Aplikasi Kasir & Manajemen Toko Madura")

# 2. Sistem Login / Identifikasi Toko Sederhana
st.sidebar.header("🔐 Masuk Toko")
nama_toko = st.sidebar.text_input(
    "Masukkan Nama Toko Anda:", placeholder="Contoh: TOKO MADURA PULO"
)

if not nama_toko:
  st.warning("⚠️ Silakan masukkan Nama Toko di sidebar kiri untuk mulai.")
  st.stop()

st.sidebar.success(f"Terhubung sebagai: **{nama_toko}**")

# Navigasi Menu (Disarankan mulai dari Kelola Produk untuk toko baru)
menu = st.sidebar.radio(
    "Pilih Menu:", ["Kelola Produk", "Kasir (Transaksi)", "Laporan Penjualan"]
)

# ---------------------------------------------------------
# MENU 1: KELOLA PRODUK (Pendaftaran Barang Awal)
# ---------------------------------------------------------
if menu == "Kelola Produk":
  st.header("📦 Kelola Daftar Barang Dagangan")
  st.info(
      "💡 **Langkah Pertama:** Silakan daftarkan terlebih dahulu barang-barang"
      " yang dijual di toko Anda pada form di bawah ini."
  )

  with st.form("form_produk"):
    st.subheader("Tambah Barang Baru")
    barcode = st.text_input("Kode Barcode / SKU (Boleh dikosongkan jika manual)")
    nama_produk = st.text_input("Nama Produk (Contoh: Aqua 600ml, Rokok X)")
    harga = st.number_input("Harga Jual (Rp)", min_value=0, step=500)

    submitted = st.form_submit_button("Simpan Produk")
    if submitted:
      if nama_produk and harga > 0:
        data_insert = {
            "id_toko": nama_toko,
            "barcode": barcode,
            "nama_produk": nama_produk,
            "harga": harga,
        }
        supabase.table("produk").insert(data_insert).execute()
        st.success(f"Produk '{nama_produk}' berhasil disimpan!")
        st.rerun()
      else:
        st.error("Nama produk dan harga wajib diisi dengan benar!")

  st.divider()
  st.subheader("📋 Daftar Barang Toko Anda")

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
      st.info(
          "Belum ada produk. Yuk, daftarkan produk pertama Anda menggunakan form"
          " di atas!"
      )
  except Exception as e:
    st.error(f"Gagal memuat produk: {e}")

# ---------------------------------------------------------
# MENU 2: KASIR (TRANSAKSI PENJUALAN)
# ---------------------------------------------------------
elif menu == "Kasir (Transaksi)":
  st.header("🛒 Kasir Penjualan")

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
        "⚠️ Belum ada produk terdaftar untuk toko ini. Silakan pindah ke menu"
        " **Kelola Produk** terlebih dahulu untuk mendaftarkan barang."
    )
    st.stop()

  pilihan_produk = {item["nama_produk"]: item for item in data_produk}

  selected_nama = st.selectbox(
      "Pilih / Cari Barang:", list(pilihan_produk.keys())
  )
  barang_terpilih = pilihan_produk[selected_nama]

  st.write(f"**Harga Satuan:** Rp {barang_terpilih['harga']:,}")

  jumlah_beli = st.number_input("Jumlah Beli", min_value=1, value=1, step=1)
  total_harga = barang_terpilih["harga"] * jumlah_beli

  st.info(f"### Total Bayar: Rp {total_harga:,}")

  if st.button("Proses Transaksi"):
    data_transaksi = {
        "id_toko": nama_toko,
        "tanggal": datetime.now().isoformat(),
        "nama_produk": selected_nama,
        "jumlah": jumlah_beli,
        "total_harga": total_harga,
    }
    supabase.table("transaksi").insert(data_transaksi).execute()
    st.success(
        f"✅ Transaksi berhasil! Total: Rp {total_harga:,} tercatat di sistem."
    )

# ---------------------------------------------------------
# MENU 3: LAPORAN PENJUALAN
# ---------------------------------------------------------
elif menu == "Laporan Penjualan":
  st.header("📊 Riwayat & Laporan Penjualan")

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
        label="Total Omzet Toko Anda",
        value=f"Rp {total_omzet:,.0f}".replace(",", "."),
    )
  else:
    st.info("Belum ada transaksi tercatat untuk toko ini.")
