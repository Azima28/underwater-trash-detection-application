# Sistem Analisis Tingkat Cemaran Plastik

## Overview
Sistem sekarang menghitung tingkat cemaran (pollution level) berdasarkan jumlah plastik terdeteksi dan durasi video, dengan rekomendasi solusi otomatis.

## Perhitungan Severity

### Thresholds (Batas Cemaran)
| Level | Deteksi | Deskripsi |
|-------|---------|-----------|
| 🟢 **LOW** | < 50 | Area relatif bersih |
| 🟡 **MEDIUM** | 50-100 | Perlu pembersihan berkala |
| 🟠 **HIGH** | 100-200 | Area sangat tercemar |
| 🔴 **CRITICAL** | > 300 | Darurat polusi plastik! |

### Contoh Perhitungan

**Gambar Statis (Image):**
- 10 trash objects → **LOW** ✅
- 50 trash objects → **MEDIUM** ⚠️
- 150 trash objects → **HIGH** 🔴
- 350+ trash objects → **CRITICAL** ⛔

**Video (durasi dihitung otomatis):**
- 100 trash dalam 60 detik (100/min) → **HIGH** 
- 300 trash dalam 60 detik (300/min) → **CRITICAL**
- 50 trash dalam 120 detik (25/min) → **MEDIUM**

## Rekomendasi Otomatis

### LOW (Bersih)
- ✓ Pertahankan kondisi kebersihan area
- ✓ Pemantauan rutin setiap minggu
- ✓ Edukasi publik

### MEDIUM (Sedang)
- ⚠️ Tingkatkan pembersihan 2-3x/minggu
- ⚠️ Pasang tempat sampah plastik strategis
- ⚠️ Program daur ulang
- ⚠️ Identifikasi sumber sampah

### HIGH (Tinggi)
- 🔴 Pembersihan harian
- 🔴 Kerjasama komunitas lingkungan
- 🔴 Program daur ulang intensif
- 🔴 Penyelidikan asal sampah

### CRITICAL (Darurat)
- ⛔ **OPERASI PEMBERSIHAN EMERGENSI**
- ⛔ Penutupan area sementara
- ⛔ Mobilisasi tim besar
- ⛔ Investigasi mendalam
- ⛔ Koordinasi pemerintah & NGO
- ⛔ Kampanye publik skala besar

## Implementasi Teknis

### Frontend (HTML/JavaScript)
- Fungsi `calculatePollutionLevel()` menghitung severity
- Fungsi `displayPollutionLevel()` menampilkan UI dengan warna-warna berbeda
- Ditampilkan di bagian Results setelah deteksi selesai

### Backend (Python/Flask)
- `app.py`: Menyimpan jumlah frame dalam stats JSON
- Durasi video dihitung dari: `frame_count / fps` atau dari `cap.get(cv2.CAP_PROP_FRAME_COUNT)`
- Stats file format:
```json
{
  "detections": 150,
  "class_counts": {"trash": 100, "bio": 50},
  "frames": 1800,
  "filename": "result_20250121_120000.mp4"
}
```

### Styling
- **Low**: Background hijau, border hijau
- **Medium**: Background kuning, border oranye
- **High**: Background oranye gelap, border oranye
- **Critical**: Background merah, border merah

## Testing

Sudah ditest dengan berbagai skenario:
✅ Image dengan 10-350 trash objects
✅ Video 60 detik dengan 20-600 trash objects
✅ Video 120 detik dengan durasi adjustment
✅ Kalkulasi rekomendasi per level

## Bagaimana Cara Kerjanya di Web

1. User upload video/gambar
2. Model YOLO mendeteksi trash
3. Centroid tracking menghitung unique objects
4. Backend mengirim stats dengan frame count
5. JavaScript menghitung pollution level
6. UI menampilkan level + rekomendasi berwarna
7. User mendapat insight langsung tentang tingkat cemaran & aksi yang perlu dilakukan
