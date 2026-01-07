# 🍽️ KERZZ BOSS - Restoran Yönetim Sistemi PRO

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![CustomTkinter](https://img.shields.io/badge/CustomTkinter-5.0+-green.svg)](https://github.com/TomSchimansky/CustomTkinter)

**KERZZ BOSS**, restoranlar için geliştirilmiş kapsamlı bir yönetim sistemidir. Müşteri yönetimi, şube takibi, e-posta pazarlama, yapay zeka destekli analizler ve daha fazlasını tek bir arayüzde sunar.

![KERZZ BOSS Screenshot](docs/screenshot.png)

## ✨ Özellikler

### 📊 Dashboard
- Gerçek zamanlı istatistikler
- Grafik görselleştirmeler
- Hızlı özet kartları

### 👥 Müşteri Yönetimi
- Detaylı müşteri veritabanı
- Excel benzeri filtreleme
- Toplu silme ve güncelleme
- CSV/Excel export

### 🏢 Şube Yönetimi
- Çoklu şube desteği
- Şube bazlı raporlama
- Mesafe hesaplama

### 📧 E-posta Pazarlama
- Otomatik e-posta gönderimi
- Şablon yönetimi
- Zamanlı gönderim

### 🤖 Yapay Zeka Modülü
- Müşteri davranış analizi
- Tahminleme
- Akıllı öneriler

### 📱 Bildirim Sistemi
- Anlık bildirimler
- SMS entegrasyonu
- Push notification

### 🔐 Lisans Sistemi
- Makine bazlı lisanslama
- Online doğrulama
- Otomatik güncelleme

## 🚀 Kurulum

### Gereksinimler
- Python 3.8 veya üzeri
- pip paket yöneticisi

### Adımlar

1. **Depoyu klonlayın:**
```bash
git clone https://github.com/osmankobat/kerzz-boss.git
cd kerzz-boss
```

2. **Sanal ortam oluşturun:**
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
```

3. **Bağımlılıkları yükleyin:**
```bash
pip install -r requirements.txt
```

4. **Uygulamayı başlatın:**
```bash
python kerzz_gui_modern.py
```

## 📦 EXE Oluşturma

### Basit Yöntem (PyInstaller)
```bash
pyinstaller KerzzBoss_Protected.spec
```

### Korumalı EXE (PyArmor + PyInstaller)
```bash
pip install pyarmor
pyarmor gen -O dist_protected kerzz_gui_modern.py license_manager.py
pyinstaller KerzzBoss_Protected.spec
```

### En Güçlü Koruma (Nuitka)
```bash
pip install nuitka
nuitka --standalone --onefile --windows-disable-console --enable-plugin=tk-inter kerzz_gui_modern.py
```

## 📋 Bağımlılıklar

```
customtkinter>=5.0.0
pillow>=9.0.0
requests>=2.28.0
matplotlib>=3.5.0
pandas>=1.4.0
openpyxl>=3.0.0
python-dateutil>=2.8.0
win10toast>=0.9 (Windows)
pywin32>=300 (Windows)
```

## 🎨 Klavye Kısayolları

| Kısayol | İşlev |
|---------|-------|
| `Ctrl+R` | Verileri yenile |
| `Ctrl+E` | Excel'e aktar |
| `Ctrl+D` | Seçili sil |
| `Ctrl+A` | Tümünü seç |
| `Ctrl+F` | Filtreleme |
| `Escape` | Seçimi temizle |
| `F5` | Sayfayı yenile |
| `Delete` | Seçili kayıtları sil |

## 📁 Proje Yapısı

```
kerzz-boss/
├── kerzz_gui_modern.py      # Ana GUI uygulaması
├── kerzz_yonetim_programi.py # Yönetim fonksiyonları
├── license_manager.py        # Lisans ve güncelleme sistemi
├── KerzzBoss_Protected.spec  # PyInstaller yapılandırması
├── requirements.txt          # Python bağımlılıkları
├── LICENSE                   # MIT Lisansı
├── README.md                 # Bu dosya
├── assets/
│   └── icon.ico             # Uygulama ikonu
├── backend/
│   ├── app.py               # Flask API
│   ├── scheduler.py         # Zamanlanmış görevler
│   └── models/              # Veritabanı modelleri
└── frontend/
    └── src/                 # Next.js web arayüzü
```

## 🔄 Güncelleme

Uygulama GitHub Releases üzerinden otomatik güncelleme desteği sunar:

1. "Hakkında" sekmesine gidin
2. "Güncelleme Kontrol" butonuna tıklayın
3. Yeni sürüm varsa "Güncelle" ile indirin

## 🤝 Katkıda Bulunma

1. Bu depoyu fork edin
2. Feature branch oluşturun (`git checkout -b feature/AmazingFeature`)
3. Değişikliklerinizi commit edin (`git commit -m 'Add some AmazingFeature'`)
4. Branch'i push edin (`git push origin feature/AmazingFeature`)
5. Pull Request açın

## 📝 Lisans

Bu proje MIT Lisansı altında lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakın.

## 👨‍💻 Geliştirici

**Osman Kobat**

- GitHub: [@osmankobat](https://github.com/osmankobat)
- E-posta: osmankbt038@gmail.com

## 🙏 Teşekkürler

- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) - Modern GUI framework
- [Pillow](https://pillow.readthedocs.io/) - Görüntü işleme
- [Matplotlib](https://matplotlib.org/) - Grafik oluşturma

---

⭐ Bu proje işinize yaradıysa yıldız vermeyi unutmayın!
