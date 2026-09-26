if menu == "Kelola Produk":
  st.header(f"📦 Manajemen Produk — {nama_toko}")
  st.info(
      "💡 Daftarkan produk atau barang dagangan toko Anda di sini (masukkan"
      " kode barcode dan harga)."
  )

  # Inisialisasi tempat penyimpanan hasil scan
  if "hasil_scan_produk" not in st.session_state:
    st.session_state.hasil_scan_produk = ""

  # ---------------- SCANNER KAMERA (DI LUAR FORM) ----------------
  st.subheader("📷 Scan Barcode via Kamera HP")
  try:
    from streamlit_qrcode_scanner import qrcode_scanner

    scan_result = qrcode_scanner(key="barcode_scanner_produk")
    if scan_result:
      st.session_state.hasil_scan_produk = str(scan_result)
      st.success(f"🎉 Barcode Terdeteksi: **{scan_result}**")
  except Exception as e:
    st.info(
        "💡 (Jika kamera belum aktif, pastikan Anda memberikan izin akses kamera"
        " pada browser HP/laptop Anda)."
    )

  st.divider()

  # ---------------- FORM TAMBAH PRODUK ----------------
  with st.form("form_produk"):
    st.subheader("Tambah Barang Baru")
    barcode = st.text_input(
        "Kode Barcode / SKU (Ketik manual atau scan dengan alat)",
        value=st.session_state.hasil_scan_produk,
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
        st.session_state.hasil_scan_produk = ""  # reset setelah simpan
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
