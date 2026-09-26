# (Bagian atas kode seperti konfigurasi supabase & login tetap sama)
# ...

# ---------------------------------------------------------
# MENU 2: KASIR (TRANSAKSI PENJUALAN + LIVE BARCODE SCANNER)
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

  # Memanggil Live Barcode Scanner via Kamera
  st.subheader("📷 Live Barcode Scanner")
  barcode_terdeteksi = None

  try:
    from streamlit_barcode_scanner import barcode_scanner

    scanned_code = barcode_scanner()
    if scanned_code:
      st.success(f"🎉 Barcode Terdeteksi: **{scanned_code}**")
      barcode_terdeteksi = scanned_code
  except Exception as e:
    st.info(
        "💡 (Tips: Pastikan izin kamera di browser Anda diizinkan/allowed."
        " Alternatif lain, Anda tetap bisa memilih produk dari daftar di"
        " bawah)."
    )

  # Cocokkan hasil scan dengan database produk toko ini
  barang_terpilih = None
  if barcode_terdeteksi:
    # Cari produk berdasarkan barcode yang di-scan
    match = [
        item
        for item in data_produk
        if str(item.get("barcode")) == str(barcode_terdeteksi)
    ]
    if match:
      barang_terpilih = match[0]
      st.success(f"Ditemukan Produk: **{barang_terpilih['nama_produk']}**")

  # Jika tidak dari scan atau tidak ketemu, sediakan pilihan manual / dropdown
  pilihan_produk = {
      f"{item['nama_produk']} (Rp {item['harga']:,} | Barcode: {item['barcode']})": item
      for item in data_produk
  }

  selected_label = st.selectbox(
      "🔍 Atau Pilih Manual dari Daftar:", list(pilihan_produk.keys())
  )

  # Jika ada hasil scan yang cocok, kita bisa arahkan, atau biarkan pakai dropdown
  if not barang_terpilih:
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
