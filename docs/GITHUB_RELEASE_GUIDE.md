# GitHub Release Hazırlık Rehberi

## 📦 GitHub'a Yüklenecek Dosyalar

### Ana Dosyalar (Zorunlu)
- ✅ `kerzz_gui_modern.py` - Ana uygulama
- ✅ `kerzz_yonetim_programi.py` - Yönetim fonksiyonları
- ✅ `license_manager.py` - Lisans sistemi
- ✅ `requirements.txt` - Bağımlılıklar
- ✅ `LICENSE` - MIT Lisansı
- ✅ `README.md` - Proje açıklaması

### GitHub Özel Dosyalar
- ✅ `.gitignore` - Git ignore listesi
- ✅ `CONTRIBUTING.md` - Katkı rehberi
- ✅ `CHANGELOG.md` - Değişiklik günlüğü
- ✅ `SECURITY.md` - Güvenlik politikası

### EXE Oluşturma
- ✅ `KerzzBoss_Protected.spec` - PyInstaller config
- ✅ `version_info.txt` - Windows versiyon bilgisi
- ✅ `assets/icon.ico` - Uygulama ikonu
- ✅ `assets/icon.png` - PNG ikon

### Release Assets
- ✅ `dist/KerzzBoss.exe` (96 MB) - Windows EXE
- ✅ `dist/RELEASE_NOTES.txt` - Sürüm notları

---

## 🚀 GitHub'a Yükleme Adımları

### 1. Repository Oluştur
```bash
# GitHub'da yeni repo oluştur: osmankobat/kerzz-boss
```

### 2. Yerel Git Başlat
```bash
cd "c:\Users\Osman KOBAT\Desktop\Python\Karışık\abc-akilliposta-web"
git init
git add .
git commit -m "Initial commit: KERZZ BOSS v3.0.0"
git branch -M main
git remote add origin https://github.com/osmankobat/kerzz-boss.git
git push -u origin main
```

### 3. Release Oluştur
```bash
# GitHub web arayüzünden:
# 1. Releases > Create new release
# 2. Tag: v3.0.0
# 3. Title: KERZZ BOSS v3.0.0
# 4. Description: CHANGELOG.md içeriği
# 5. Assets: KerzzBoss.exe dosyasını yükle
# 6. Publish release
```

---

## 📋 Kontrol Listesi

### Yükleme Öncesi
- [x] Tüm dosyalar oluşturuldu
- [x] EXE test edildi
- [x] Icon eklendi
- [x] Requirements güncel
- [x] License eklendi

### GitHub Ayarları
- [ ] Repository oluştur (Public/Private)
- [ ] Description ekle
- [ ] Topics ekle: python, customtkinter, restaurant-management
- [ ] About bölümünü doldur

### Release
- [ ] Tag oluştur (v3.0.0)
- [ ] Release notes yaz
- [ ] EXE'yi asset olarak ekle
- [ ] Publish et

---

## 🔗 Yararlı Linkler

- GitHub: https://github.com/osmankobat/kerzz-boss
- PyInstaller: https://pyinstaller.org/
- CustomTkinter: https://github.com/TomSchimansky/CustomTkinter
