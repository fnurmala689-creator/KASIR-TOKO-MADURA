import streamlit as st
import pandas as pd
import base64
import copy
import json
import requests
from datetime import datetime
import urllib.parse
import streamlit.components.v1 as components
from streamlit_qrcode_scanner import qrcode_scanner

st.set_page_config(page_title="Aplikasi Kasir Toko", page_icon="🛒", layout="wide")

# --- CSS: TAMPILAN RESPONSIF HP & PROFESIONAL ---
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 100%;
    }
    html, body, [class*="css"] {
        font-size: 15px !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    div[data-testid="column"] .menu-btn > button {
        width: 100% !important;
        border-radius: 8px !important;
        padding: 20px 12px !important;
        font-size: 16px !important;
        font-weight: 600 !important;
        border: 1px solid #dcdde1 !important;
        background-color: #f5f6fa !important;
        color: #2f3640 !important;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
    }
    @media (max-width: 768px) {
        .block-container {
            padding-left: 0.5rem;
            padding-right: 0.5rem;
        }
        h1 { font-size: 1.5rem !important; }
        h3 { font-size: 1.2rem !important; }
    }
    input { font-size: 16px !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

FALLBACK = pd.DataFrame({
    "Barcode": ["899111"],
    "Nama Barang": ["Contoh Produk (Atur Link Spreadsheet Anda)"],
    "Harga Umum": [10000],
    "Harga Reseller": [9000],
    "Harga Pengusaha": [8500],
})

# Inisialisasi Session State untuk menyimpan Link Spreadsheet milik Customer
if "custom_csv_url" not in st.session_state:
    st.session_state.custom_csv_url = ""

@st.cache_data(ttl=300)
def muat_produk(url_csv):
    if not url_csv:
        return FALLBACK.astype(str), False
    try:
        df = pd.read_csv(url_csv, dtype=str)
        ok = True
    except Exception:
        df = FALLBACK.astype(str)
        ok = False
    df.columns = df.columns.str.strip()
    for c in df.columns:
        if c.lower().startswith("harga"):
            df[c] = (
                df[c].fillna("0").astype(str)
                .str.replace(r"\.0$", "", regex=True)
                .str.replace(r"[^\d]", "", regex=True)
                .replace("", "0")
                .astype(int)
            )
        else:
            df[c] = df[c].fillna("")
    return df, ok

def norm_kode(x):
    s = str(x).strip().replace("\u00a0", "")
    if s.endswith(".0"):
        s = s[:-2]
    return s.lstrip("0")

def rp(angka):
    return f"{angka:,.0f}".replace(",", ".")

def parse_angka(val):
    s = "".join(filter(str.isdigit, str(val)))
    return int(s) if s else 0

# --- HALAMAN SETUP AWAL JIKA LINK BELUM DIISI ---
if not st.session_state.custom_csv_url:
    st.title("⚙️ Pengaturan Awal Toko")
    st.markdown("Selamat datang! Masukkan tautan CSV Google Spreadsheet toko Anda untuk mulai menggunakan aplikasi kasir ini.")
    
    with st.form("form_setup"):
        url_input = st.text_input("Tautan CSV Google Spreadsheet:", placeholder="https://docs.google.com/spreadsheets/d/e/.../pub?output=csv")
        submitted = st.form_submit_button("Simpan & Hubungkan Toko", type="primary")
        if submitted:
            if url_input.strip():
                st.session_state.custom_csv_url = url_input.strip()
                st.success("Berhasil terhubung!")
                st.rerun()
            else:
                st.warning("Tautan tidak boleh kosong.")
    
    st.info("💡 **Tips untuk Pembeli:** Buat salinan Google Spreadsheet Anda sendiri, publikasikan ke web sebagai CSV, lalu tempel tautannya di atas.")
    st.stop()

# Memuat data berdasarkan link kustom milik customer
df_produk, data_dari_sheet = muat_produk(st.session_state.custom_csv_url)
df_produk = df_produk.copy()

if not data_dari_sheet:
    st.error("⚠️ Gagal mengambil data dari tautan Spreadsheet Anda. Periksa kembali tautannya.")
    if st.button("Reset / Ubah Tautan Spreadsheet"):
        st.session_state.custom_csv_url = ""
        st.rerun()
    st.stop()

kolom_nama_opsi = ["Nama Barang", "nama barang", "Nama", "nama", "Produk", "produk"]
kolom_nama_barang = next((c for c in kolom_nama_opsi if c in df_produk.columns), df_produk.columns[0])

kolom_barcode_opsi = ["Barcode", "barcode", "SKU", "sku", "Kode", "kode"]
kolom_barcode = next((c for c in kolom_barcode_opsi if c in df_produk.columns), None)

if kolom_barcode:
    df_produk["_kode"] = df_produk[kolom_barcode].map(norm_kode)

defaults = {
    "menu_aktif": None,
    "keranjang": [],
    "lain_lain": [],
    "scan_counter_db": 0,
    "scan_counter_tambah": 0,
    "scan_counter_kasir_aktif": None,
    "tambah_barcode": "",
    "tambah_nama": "",
    "tambah_riwayat": [],
    "pesan_tambah": None,
    "editor_counter": 0,
    "riwayat": [],
    "konfirmasi_kosong": False,
    "pesan": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

def simpan_riwayat():
    st.session_state.riwayat.append(copy.deepcopy(st.session_state.keranjang))
    st.session_state.riwayat = st.session_state.riwayat[-20:]

def proses_input_barcode(idx_baris, input_val, kolom_harga_pilihan):
    val = str(input_val).strip()
    if not val:
        return

    simpan_riwayat()
    df_match = pd.DataFrame()
    if kolom_barcode:
        df_match = df_produk[df_produk["_kode"] == norm_kode(val)]
    if len(df_match) == 0:
        df_match = df_produk[
            df_produk[kolom_nama_barang].astype(str).str.contains(val, case=False, na=False, regex=False)
        ]

    if len(df_match) == 0:
        st.session_state.pesan = ("warning", f"⚠️ Barang '{val}' tidak ditemukan.")
    elif len(df_match) == 1:
        row = df_match.iloc[0]
        bcode = str(row[kolom_barcode]).strip() if kolom_barcode else "-"
        nm = str(row[kolom_nama_barang]).strip() or "(Tanpa Nama)"
        hg = int(row[kolom_harga_pilihan])
        
        st.session_state.keranjang[idx_baris] = {
            "Barcode": bcode,
            "Nama Barang": nm,
            "Qty": 1,
            "Harga Satuan": hg,
            "Subtotal": hg,
        }
        st.session_state.pesan = ("success", f"✅ Memuat: **{nm}** (Rp {rp(hg)})")
    else:
        opsi_list = []
        for _, row in df_match.iterrows():
            bcode = str(row[kolom_barcode]).strip() if kolom_barcode else "-"
            nm = str(row[kolom_nama_barang]).strip() or "(Tanpa Nama)"
            hg = int(row[kolom_harga_pilihan])
            opsi_list.append((bcode, nm, hg))
        st.session_state.keranjang[idx_baris]["_dropdown_pilihan"] = opsi_list
        st.session_state.pesan = ("info", f"Ditemukan beberapa barang untuk '{val}', silakan pilih.")
    
    st.session_state.editor_counter += 1

def barcode_diketik(idx_baris, kolom_harga_pilihan, key_widget):
    val = st.session_state.get(key_widget, "")
    proses_input_barcode(idx_baris, val, kolom_harga_pilihan)

def pilih_dari_dropdown(idx_baris, bcode, nm, hg):
    simpan_riwayat()
    st.session_state.keranjang[idx_baris] = {
        "Barcode": bcode,
        "Nama Barang": nm,
        "Qty": 1,
        "Harga Satuan": hg,
        "Subtotal": hg,
    }
    if "_dropdown_pilihan" in st.session_state.keranjang[idx_baris]:
        del st.session_state.keranjang[idx_baris]["_dropdown_pilihan"]
    st.session_state.pesan = ("success", f"✅ Dipilih: **{nm}** (Rp {rp(hg)})")
    st.session_state.editor_counter += 1

def tambah_baris_kosong():
    simpan_riwayat()
    st.session_state.keranjang.append({
        "Barcode": "",
        "Nama Barang": "Ketik barcode atau nama barang...",
        "Qty": 1,
        "Harga Satuan": 0,
        "Subtotal": 0,
    })
    st.session_state.editor_counter += 1

def tambah_baris_lain():
    st.session_state.lain_lain.append({"tipe": "Diskon", "nominal": 0})

def hapus_baris_lain(idx):
    if 0 <= idx < len(st.session_state.lain_lain):
        st.session_state.lain_lain.pop(idx)

def update_qty_ketik(index_item, key_qty_widget):
    simpan_riwayat()
    if 0 <= index_item < len(st.session_state.keranjang):
        val_baru = parse_angka(st.session_state.get(key_qty_widget, 1))
        if val_baru <= 0:
            val_baru = 1
        item = st.session_state.keranjang[index_item]
        item["Qty"] = val_baru
        item["Subtotal"] = item["Qty"] * item["Harga Satuan"]
        st.session_state.editor_counter += 1

def hapus_item_satuan(index_item):
    simpan_riwayat()
    if 0 <= index_item < len(st.session_state.keranjang):
        st.session_state.keranjang.pop(index_item)
        st.session_state.pesan = ("info", "❌ Baris dihapus.")
        st.session_state.editor_counter += 1

def batalkan_terakhir():
    if st.session_state.riwayat:
        st.session_state.keranjang = st.session_state.riwayat.pop()
        st.session_state.editor_counter += 1
        st.session_state.pesan = ("info", "↩️ Perubahan dibatalkan.")

def minta_konfirmasi_kosong():
    st.session_state.konfirmasi_kosong = True

def batal_kosongkan():
    st.session_state.konfirmasi_kosong = False

def kosongkan_keranjang():
    simpan_riwayat()
    st.session_state.keranjang = []
    st.session_state.lain_lain = []
    st.session_state.pesan = ("info", "🗑️ Keranjang dikosongkan.")
    st.session_state.konfirmasi_kosong = False
    st.session_state.editor_counter += 1

def hapus_pencarian_db():
    st.session_state.search_db = ""

# --- HEADER UTAMA ---
st.title("APLIKASI KASIR TOKO")
st.caption(f"Terhubung ke Google Sheets Mandiri")

if st.button("🔄 Ganti / Ubah Tautan Spreadsheet Toko"):
    st.session_state.custom_csv_url = ""
    st.rerun()

if st.session_state.menu_aktif is None:
    st.markdown("---")
    st.markdown("### Pilih Menu Utama:")
    c1, c2 = st.columns(2)

    with c1:
        with st.container():
            st.markdown('<div class="menu-btn">', unsafe_allow_html=True)
            if st.button("KASIR", key="menu_kasir_utama", use_container_width=True):
                st.session_state.menu_aktif = "Kasir"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        with st.container():
            st.markdown('<div class="menu-btn">', unsafe_allow_html=True)
            if st.button("CEK HARGA", key="menu_cari_harga", use_container_width=True):
                st.session_state.menu_aktif = "Database"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

else:
    st.markdown("---")
    nav1, nav2 = st.columns(2)
    with nav1:
        if st.button("🛒 Kasir", use_container_width=True, type="primary" if st.session_state.menu_aktif == "Kasir" else "secondary"):
            st.session_state.menu_aktif = "Kasir"
            st.rerun()
    with nav2:
        if st.button("🔍 Harga / Barang", use_container_width=True, type="primary" if st.session_state.menu_aktif == "Database" else "secondary"):
            st.session_state.menu_aktif = "Database"
            st.rerun()
    st.markdown("---")

    if st.session_state.menu_aktif == "Database":
        st.subheader("Daftar Barang")
        
        if st.button("🔄 Muat Ulang Data Terbaru", use_container_width=True):
            muat_produk.clear()
            st.success("Data berhasil diperbarui!")
            st.rerun()

        buka_kamera_db = st.checkbox("📷 Aktifkan Pemindai Kamera", value=False, key="toggle_kamera_db")
        if buka_kamera_db:
            hasil_scan_db = qrcode_scanner(key=f"scanner_db_{st.session_state.scan_counter_db}")
            if hasil_scan_db:
                st.session_state.search_db = str(hasil_scan_db).strip()
                st.session_state.scan_counter_db += 1
                st.rerun()

        search_database = st.text_input("Cari Nama Barang / Barcode:", placeholder="Ketik kata kunci...", key="search_db")
        df_tampil = df_produk.drop(columns="_kode", errors="ignore")
        if search_database:
            kata = search_database.strip()
            mask = df_tampil.astype(str).apply(lambda x: x.str.contains(kata, case=False, na=False, regex=False)).any(axis=1)
            if "_kode" in df_produk.columns:
                mask = mask | (df_produk["_kode"] == norm_kode(kata))
            df_tampil = df_tampil[mask]
            st.button("Reset Pencarian", on_click=hapus_pencarian_db)

        df_tampil = df_tampil.copy()
        for c in df_tampil.columns:
            if c.lower().startswith("harga"):
                df_tampil[c] = df_tampil[c].map(rp)
        
        df_tampil = df_tampil.reset_index(drop=True)
        df_tampil.index = df_tampil.index + 1

        st.dataframe(df_tampil, use_container_width=True)

    elif st.session_state.menu_aktif == "Kasir":
        st.markdown("### Kategori Harga Pelanggan")
        
        # Deteksi otomatis kolom harga yang tersedia di spreadsheet customer
        list_kolom_harga = [c.replace("Harga ", "") for c in df_produk.columns if c.lower().startswith("harga")]
        if not list_kolom_harga:
            list_kolom_harga = ["Umum"]

        jenis_pelanggan = st.selectbox(
            "Pilih kategori:",
            list_kolom_harga,
            key="pilih_level_harga",
            label_visibility="collapsed"
        )

        kolom_harga_pilihan = f"Harga {jenis_pelanggan}"
        if kolom_harga_pilihan not in df_produk.columns:
            kolom_harga_pilihan = df_produk.columns[1]

        st.markdown("---")

        if not st.session_state.keranjang:
            st.session_state.keranjang.append({
                "Barcode": "",
                "Nama Barang": "Ketik barcode atau nama barang...",
                "Qty": 1,
                "Harga Satuan": 0,
                "Subtotal": 0,
            })

        if st.session_state.pesan:
            tipe, teks = st.session_state.pesan
            getattr(st, tipe)(teks)

        st.markdown("### Daftar Transaksi")

        for idx, item in enumerate(st.session_state.keranjang):
            with st.container(border=True):
                st.markdown(f"**#{idx + 1} - {item['Nama Barang']}**")
                
                rc1, rc2 = st.columns([3, 1])
                with rc1:
                    key_bc = f"barcode_input_{idx}_{st.session_state.editor_counter}"
                    st.text_input(
                        "Barcode",
                        value=item.get("Barcode", ""),
                        key=key_bc,
                        placeholder="Scan/ketik barcode...",
                        label_visibility="collapsed",
                        on_change=barcode_diketik,
                        args=(idx, kolom_harga_pilihan, key_bc),
                    )
                with rc2:
                    if st.button("📷 Scan", key=f"btn_cam_{idx}", use_container_width=True):
                        st.session_state.scan_counter_kasir_aktif = idx
                        st.rerun()

                q_c_input, q_c_del = st.columns([2.3, 1])
                with q_c_input:
                    key_q_input = f"qty_input_{idx}_{st.session_state.editor_counter}"
                    if key_q_input not in st.session_state:
                        st.session_state[key_q_input] = str(item["Qty"])
                    st.text_input(
                        "Qty",
                        value=str(item["Qty"]),
                        key=key_q_input,
                        label_visibility="collapsed",
                        on_change=update_qty_ketik,
                        args=(idx, key_q_input)
                    )
                with q_c_del:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🗑️ Hapus", key=f"del_{idx}", use_container_width=True):
                        hapus_item_satuan(idx)
                        st.rerun()

                st.markdown(f"<div style='font-size:13px; color:gray; margin-top:4px;'>@ Rp {rp(item['Harga Satuan'])} &nbsp;|&nbsp; Subtotal: <b style='color:#2f3640;'>Rp {rp(item['Subtotal'])}</b></div>", unsafe_allow_html=True)

            if "_dropdown_pilihan" in item:
                st.markdown(f"Pilih opsi barang untuk baris {idx+1}:")
                for p_idx, (p_bcode, p_nm, p_hg) in enumerate(item["_dropdown_pilihan"]):
                    if st.button(f"[{p_bcode}] {p_nm} - Rp {rp(p_hg)}", key=f"drop_{idx}_{p_idx}", use_container_width=True):
                        pilih_dari_dropdown(idx, p_bcode, p_nm, p_hg)
                        st.rerun()

        col_tambah_baris, col_batal_aksi = st.columns(2)
        with col_tambah_baris:
            st.button("＋ Tambah Baris", on_click=tambah_baris_kosong, use_container_width=True)
        with col_batal_aksi:
            if st.session_state.riwayat:
                st.button("↩️ Batalkan", on_click=batalkan_terakhir, use_container_width=True)

        if len(st.session_state.keranjang) > 0:
            df_keranjang = pd.DataFrame(st.session_state.keranjang)
            subtotal_barang = int(df_keranjang["Subtotal"].sum()) if not df_keranjang.empty else 0

            st.markdown("### Lain-Lain (Diskon / Ongkir)")
            st.button("＋ Catatan Lain-Lain", on_click=tambah_baris_lain, use_container_width=True)

            total_diskon = 0
            total_penambah = 0
            rincian_lain = []

            for i, ll in enumerate(st.session_state.lain_lain):
                with st.container(border=True):
                    c_ll1, c_ll2, c_ll3 = st.columns([2, 2, 1])
                    with c_ll1:
                        ll["tipe"] = st.selectbox("Jenis", ["Diskon", "Ongkir"], key=f"tipe_ll_{i}", index=["Diskon", "Ongkir"].index(ll["tipe"]))
                    with c_ll2:
                        k_nominal_ll = f"Nominal_ll_str_{i}"
                        if k_nominal_ll not in st.session_state:
                            st.session_state[k_nominal_ll] = str(ll["nominal"]) if ll["nominal"] > 0 else ""
                        val_str_ll = st.text_input("Nominal (Rp)", key=k_nominal_ll, placeholder="0")
                        ll["nominal"] = parse_angka(val_str_ll)
                    with c_ll3:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("❌ Hapus", key=f"del_ll_{i}", use_container_width=True):
                            hapus_baris_lain(i)
                            st.rerun()

                if ll["tipe"] == "Diskon":
                    total_diskon += ll["nominal"]
                    rincian_lain.append(("Diskon", -ll["nominal"]))
                else:
                    total_penambah += ll["nominal"]
                    rincian_lain.append((ll["tipe"], ll["nominal"]))

            total_diskon = min(total_diskon, subtotal_barang)
            total_belanja_semua = subtotal_barang - total_diskon + total_penambah

            st.markdown("---")
            st.markdown(f"### TOTAL BAYAR: **Rp {rp(total_belanja_semua)}**")

            nama_pembeli = st.text_input("Nama Pelanggan", value="Pelanggan Umum", key="nama_pelanggan_input")
            
            k_uang_tunai = "uang_tunai_str_input"
            if k_uang_tunai not in st.session_state:
                st.session_state[k_uang_tunai] = str(total_belanja_semua) if total_belanja_semua > 0 else ""
            
            val_uang_str = st.text_input("Uang Tunai (Rp)", key=k_uang_tunai, placeholder="0")
            uang_tunai = parse_angka(val_uang_str)

            uang_kembalian = uang_tunai - total_belanja_semua
            if uang_kembalian >= 0:
                st.success(f"Kembalian: Rp {rp(uang_kembalian)}")
            else:
                st.error(f"Uang Kurang: Rp {rp(abs(uang_kembalian))}")

            st.markdown("---")
            if not st.session_state.konfirmasi_kosong:
                st.button("Kosongkan Keranjang", type="secondary", on_click=minta_konfirmasi_kosong, use_container_width=True)
            else:
                st.warning("Yakin ingin mengosongkan seluruh keranjang?")
                col_k1, col_k2 = st.columns(2)
                with col_k1:
                    st.button("Ya, Kosongkan", type="primary", on_click=kosongkan_keranjang, use_container_width=True)
                with col_k2:
                    st.button("Batal", on_click=batal_kosongkan, use_container_width=True)

            # Tombol WhatsApp Nota
            item_valid = [it for it in st.session_state.keranjang if it["Harga Satuan"] > 0]
            pesan_wa = (
                "*NOTA BELANJA*\n"
                "----------------------------------\n"
                f"Tanggal : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Kepada : {nama_pembeli}\n"
                "----------------------------------\n"
            )
            for item in item_valid:
                pesan_wa += f"• {item['Nama Barang']}\n  {rp(item['Harga Satuan'])} x {item['Qty']} = *Rp {rp(item['Subtotal'])}*\n\n"
            pesan_wa += "----------------------------------\n"
            pesan_wa += f"Total    : *Rp {rp(total_belanja_semua)}*\n"
            pesan_wa += f"Tunai    : Rp {rp(uang_tunai)}\n"
            pesan_wa += f"Kembalian: Rp {rp(uang_kembalian)}\n"
            pesan_wa += "----------------------------------\nTerima Kasih"
            whatsapp_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(pesan_wa)}"

            st.markdown(f"""
<div style="text-align: center; margin-top: 20px;">
    <a href="{whatsapp_url}" target="_blank" style="background-color: #25d366; color: white; padding: 12px 20px; text-decoration: none; font-size: 16px; border-radius: 6px; font-weight: 600; display: block;">
        💬 Kirim Nota via WhatsApp
    </a>
</div>
""", unsafe_allow_html=True)