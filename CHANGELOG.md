# Changelog

Semua perubahan penting pada **PDF Master** akan dicatat di berkas ini.

Format mengikuti [Keep a Changelog](https://keepachangelog.com/id/1.1.0/), dan versi mengikuti [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[1.5.1]: https://github.com/fahmikip/pdf-all-in-one/releases/tag/v1.5.1
[1.5.0]: https://github.com/fahmikip/pdf-all-in-one/releases/tag/v1.5.0
[1.4.0]: https://github.com/fahmikip/pdf-all-in-one/releases/tag/v1.4.0
[1.3.0]: https://github.com/fahmikip/pdf-all-in-one/releases/tag/v1.3.0
[1.2.0]: https://github.com/fahmikip/pdf-all-in-one/releases/tag/v1.2.0
[1.1.0]: https://github.com/fahmikip/pdf-all-in-one/releases/tag/v1.1.0
[1.0.0]: https://github.com/fahmikip/pdf-all-in-one/releases/tag/v1.0.0