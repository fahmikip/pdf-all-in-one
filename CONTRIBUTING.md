# Kontribusi

Terima kasih sudah tertarik berkontribusi ke **PDF Master**! Proyek ini bebas digunakan dan dimodifikasi di bawah lisensi MIT.

## Menyiapkan Lingkungan Pengembangan

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app\main.py
```

## Menjalankan Tes

```powershell
python -m pytest
```

Semua tes harus lolos sebelum mengirim perubahan. Jika mengubah perilaku inti, tambahkan tes yang sesuai di `tests/`.

## Panduan Kode

- Dukungannya **Python 3.12+** dan **PySide6 6.x** (tidak perlu versi lama).
- UI berada di `ui/`, logika dokumen di `core/`, dan pertukaran data lewat `app/config.py`.
- Jangan menambahkan dependensi baru tanpa mendiskusikannya dulu.
- Jangan mengunggah dokumen pengguna, dan jangan menambahkan telemetri — proyek ini **offline-first**.
- Kode baru harus bebas komentar berlebihan dan mengikuti gaya file di sekitarnya.

## Proses Pull Request

1. Cabang dari `main`.
2. Buat perubahan dengan pesan commit yang jelas (lihat `git log` untuk gaya yang dipakai).
3. Tambahkan/ubah tes bila perlu dan pastikan `python -m pytest` lolos.
4. Satu PR untuk satu perubahan logis.
5. Sebutkan label yang sesuai (bug, enhancement, dll.) bila ada.

## Rilis

Rilis mengikuti [Semantic Versioning](https://semver.org/). `version.txt`, `installer/version_info.txt`, dan `CHANGELOG.md` diperbarui bersama saat menambah versi. Saat tag `vX.Y.Z` di-push, [workflow rilis](.github/workflows/release.yml) akan membangun zip portable dan installer secara otomatis.