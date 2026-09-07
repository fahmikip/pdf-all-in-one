# PDF Master

**PDF Master** adalah perangkat PDF all-in-one untuk Windows yang berjalan sepenuhnya **offline**, dibangun dengan Python 3.12 dan PySide6. Semua operasi dokumen dijalankan di komputer Anda sendiri — tidak ada yang diunggah, dan tidak ada pelacakan atau telemetri.

Versi saat ini: **v1.1.0**

---

## Fitur

| Kategori | Alat | Fungsi |
| --- | --- | --- |
| Alat PDF | Kompres PDF | Perkecil ukuran file dengan profil Rendah / Disarankan / Tinggi / Maksimum; mode agresif untuk file yang sudah optimal |
| Alat PDF | Gabung PDF | Gabungkan dua PDF atau lebih, atur urutan dengan drag |
| Alat PDF | Pecah PDF | Pecah per halaman, setiap N halaman, atau rentang tertentu (mis. `1-3, 5`) |
| Alat PDF | Susun PDF | Urut ulang, putar, dan hapus halaman |
| Alat PDF | Ekstrak PDF | Ekspor teks ke `.txt` atau gambar tertanam ke PNG / JPG / WEBP |
| Konversi | Konversi File | Gambar→PDF, PDF→JPG/PNG/WebP, Word/Excel/PowerPoint→PDF (LibreOffice), PDF→Word, PDF→Excel |
| Edit | Watermark & Lainnya | Watermark teks/gambar, nomor halaman, header & footer, edit metadata |
| Keamanan | Lindungi / Buka Kunci | Proteksi kata sandi PDF dan buka kunci resmi |
| OCR | OCR PDF / Gambar | Buat hasil scan dapat dicari (memerlukan Tesseract) |
| Lanjutan | Proses Batch | Jalankan operasi yang sama untuk banyak file sekaligus |
| Lainnya | Riwayat | Riwayat operasi lokal tanpa isi dokumen, lengkap dengan statistik penyimpanan |
| Lainnya | Pengaturan | Preferensi, deteksi LibreOffice / Tesseract, pemeriksaan pembaruan (hanya notifikasi, tidak pernah unduh otomatis) |
| Lainnya | Tentang Developer | Informasi developer dan versi |

Semua hasil edit ditulis ke file **baru** — file asli Anda tidak pernah diubah.

## Persyaratan Sistem

- Windows 10/11 (64-bit)
- Python 3.12 untuk menjalankan dari kode sumber
- Alat eksternal opsional (terdeteksi terpisah, tidak disertakan):
  - **LibreOffice** — konversi Office (Word/Excel/PowerPoint) → PDF
  - **Tesseract** — mesin OCR

## Menjalankan dari Kode Sumber

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app\main.py
```

Jalankan rangkaian tes dengan `python -m pytest`.

## Cara Menggunakan

1. **Kompres PDF**
   Pilih **Kompres PDF** → seret file ke area drop → pilih tingkat kompresi → **Kompres PDF** → tentukan lokasi penyimpanan. Hasilnya terbuka di Explorer.

2. **Gabung PDF**
   Pilih **Gabung PDF** → tambahkan dua file atau lebih → seret dalam daftar sesuai urutan → **Gabung PDF**.

3. **Pecah / ekstrak halaman**
   Pilih **Pecah PDF** → pilih *Setiap halaman*, *Setiap N halaman*, atau *Rentang halaman* (mis. `1-3, 5`) → jalankan dan pilih folder keluaran.

4. **Ekstrak teks atau gambar**
   Pilih **Ekstrak PDF** → pilih *Teks ke .txt* (menyimpan file teks dengan penanda halaman) atau *Gambar ke file* (PNG/JPG/WEBP, dengan filter ukuran minimum).

5. **PDF ke Excel**
   Pilih **Konversi File** → pilih *PDF to Excel* → tambahkan PDF → pilih lokasi `.xlsx`. Seluruh konten halaman (baris teks serta gambar) disusun ke dalam worksheet secara berurutan.

6. **PDF ke Word**
   Pilih **Konversi File** → *PDF to Word* → tambahkan PDF → simpan sebagai `.docx`. Konversi bersifat best-effort: teks, paragraf, dan gambar diprioritaskan; tata letak yang sangat kompleks mungkin tidak sempurna.

7. **Lindungi atau buka kunci**
   Pilih **Lindungi / Buka Kunci** → atur kata sandi untuk mengenkripsi, atau berikan kata sandi yang benar untuk menghapus proteksi.

8. **OCR hasil scan**
   Pilih **OCR PDF / Gambar** → arahkan PDF Master ke instalasi Tesseract jika diperlukan, lalu pilih scan agar dapat dicari.

## Membangun Rilis Portable

```powershell
build.bat            # menjalankan tes, menyiapkan aset, membangun dist\PDF-Master\PDFMaster.exe
installer.bat        # tambahan: membangun installer Inno Setup (memerlukan Inno Setup 6)
```

## Privasi

PDF Master memproses dokumen secara **lokal**. Tidak ada telemetri atau analitik, dan tidak mengunggah isi dokumen, nama file, maupun aktivitas. Pemeriksaan pembaruan opsional hanya menanyakan nomor versi ke GitHub; unduhan tidak pernah terjadi tanpa izin Anda.

## Developer

Dikembangkan oleh **Fahmikip** · https://github.com/fahmikip · © 2026 Fahmikip

Build portabel Windows: lihat halaman **Releases**.