# Changelog

Semua perubahan penting pada **PDF Master** akan dicatat di berkas ini.

Format mengikuti [Keep a Changelog](https://keepachangelog.com/id/1.1.0/), dan versi mengikuti [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.6.2] - 2026-09-17

### Ditambahkan
- Screenshot README untuk halaman **Print Layout**, **Page Tools**, dan **Repair & Optimize** (digenerate headless).

### Diperbaiki
- Screenshot README kini merender font sistem dengan benar: platform offscreen sebelumnya punya basis data font kosong sehingga teks khusus (`→`, `↶`, `↷`, `—`, `…`) tampil sebagai kotak-kotak. Script screenshot kini mendaftarkan font sistem (338 berkas) dan memakai `Segoe UI`.

### Diubah
- Kualitas kode: ambang **coverage dinaikkan ke 90%** (sebelumnya 85%) dan kini dijamin CI melalui `fail_under = 90`; ~40 baris baru diuji (validasi input, progress callback, jalur error).

## [1.6.1] - 2026-09-17

### Diperbaiki
- *False positive* antivirus saat instalasi/memperbarui: matikan **kompresi UPX** pada build PyInstaller yang sering memicu heuristik tanda-tangan palsu.

## [1.6.0] - 2026-09-17

### Ditambahkan
- **Print Layout**: susun 2–16 halaman per lembar (N-up) dan cetakan **booklet lipat-tengah** yang siap dicetak bolak-balik.
- **Page Tools**: hapus halaman kosong otomatis, ubah ukuran halaman ke standar (A4/A3/A5/Letter/Legal) dengan mode Fit/Fill/Stretch dan margin, serta membuat **PDF kosong baru** dari template.
- **Repair & Optimize**: perbaiki PDF rusak (qpdf/pikepdf/PyMuPDF) dan buat salinan **Fast Web View (linearize)** untuk pemuatan cepat daring.
- **Tanda tangan tulisan tangan** di PDF Forms & Signature: gambar tanda tangan dengan mouse/touchscreen lalu sisipkan ke PDF.
- Verifikasi **SHA-256** untuk installer hasil unduhan; rilis kini menyertakan aset `SHA256SUMS.txt` dan pengunduh menolak file yang tidak cocok.
- Mesin kompresi baru: **Lossless (qpdf/pikepdf)** dan **Ghostscript**, dapat dipilih di halaman Kompres PDF.
- Langkah **code signing** opsional (Azure Trusted Signing) pada workflow rilis.
- Badge coverage kini diperbarui otomatis oleh CI.

### Diubah
- Versi kini bersumber tunggal dari `version.txt` (dipakai `pyproject.toml`, `version_info.txt`, dan installer Inno Setup).
- `requirements.txt` hanya berisi dependensi runtime; dependensi pengembangan dipindah ke ekstra `[dev]`.
- Matriks CI diperluas ke Python **3.13**.
- Menghapus pengaturan bahasa yang tidak dipakai dari `Settings`.

## [1.5.1] - 2026-09-16

### Diubah
- Lisensi diganti dari hak cipta tertutup menjadi **MIT License**.
- Ditambahkan `CHANGELOG.md`, `CONTRIBUTING.md`, dan `SECURITY.md`.
- Kualitas kode: linter & formatter **Ruff**, pola pre-commit, dan langkah CI untuk lint + format + coverage.
- Screenshot aplikasi dan badge coverage ditambahkan ke README.

## [1.5.0] - 2026-09-15

### Diubah
- Revamp total UI: tombol semantik warna-warni dan pengalaman pengguna yang lebih jelas.

## [1.4.0] - 2026-09-10

### Ditambahkan
- Editor interaktif **Insert & Edit**: letakkan foto, geser objek, ubah ukuran lewat titik sudut, dan tambah teks dengan pilihan font, ukuran, serta warna.
- Mesin inti `insert_objects` dan resolver font untuk teks bergaya di halaman PDF.

## [1.3.0] - 2026-09-09

### Ditambahkan
- Alat **Place Photo** untuk menyisipkan gambar JPEG/PNG ke halaman PDF.

### Diperbaiki
- Pembuatan aset melewati file identik dan menyinkronkan byte logo untuk branding installer.

## [1.2.0] - 2026-09-09

### Ditambahkan
- **PDF Forms & Signature**: isi formulir PDF interaktif dan tambah tanda tangan visual (gambar + nama).
- Unduh **installer otomatis** pada pemeriksaan pembaruan (selalu dengan izin pengguna).

### Diperbaiki
- Fidelitas konversi **PDF ke Word** dan **PDF ke Excel** ditingkatkan.

## [1.1.0] - 2026-09-07

### Ditambahkan
- Alat **Ekstrak PDF**: ekspor teks ke `.txt` dengan penanda halaman, atau gambar tertanam ke PNG/JPG/WebP.
- Konversi **PDF ke Excel** dengan deteksi tabel otomatis dan cadangan kolom kata.
- README diterjemahkan ke Bahasa Indonesia.

## [1.0.0] - 2026-08-02

### Ditambahkan
- Rilis awal **PDF Master** — perangkat PDF all-in-one offline untuk Windows.
- Alat PDF: Kompres, Gabung, Pecah, Susun.
- Konversi Office (Word/Excel/PowerPoint) → PDF via LibreOffice, dan PDF → Word.
- Keamanan: Lindungi / Buka Kunci PDF.
- OCR (memerlukan Tesseract) dengan pengaturan di aplikasi.
- Pemrosesan batch dan **Riwayat** lokal tanpa isi dokumen.
- Kompresi PDF adaptif dengan profil Rendah / Disarankan / Tinggi / Maksimum.

[1.6.2]: https://github.com/fahmikip/pdf-all-in-one/releases/tag/v1.6.2
[1.6.1]: https://github.com/fahmikip/pdf-all-in-one/releases/tag/v1.6.1
[1.6.0]: https://github.com/fahmikip/pdf-all-in-one/releases/tag/v1.6.0
[1.5.1]: https://github.com/fahmikip/pdf-all-in-one/releases/tag/v1.5.1
[1.5.0]: https://github.com/fahmikip/pdf-all-in-one/releases/tag/v1.5.0
[1.4.0]: https://github.com/fahmikip/pdf-all-in-one/releases/tag/v1.4.0
[1.3.0]: https://github.com/fahmikip/pdf-all-in-one/releases/tag/v1.3.0
[1.2.0]: https://github.com/fahmikip/pdf-all-in-one/releases/tag/v1.2.0
[1.1.0]: https://github.com/fahmikip/pdf-all-in-one/releases/tag/v1.1.0
[1.0.0]: https://github.com/fahmikip/pdf-all-in-one/releases/tag/v1.0.0