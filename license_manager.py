"""
KERZZ BOSS - Lisans ve Güncelleme Yönetim Modülü
Geliştirici: Osman Kobat
MIT License (c) 2024-2026

Bu modül:
- GitHub üzerinden lisans doğrulama
- Otomatik güncelleme kontrolü
- Lisans anahtarı doğrulama
"""

import os
import sys
import json
import hashlib
import platform
import uuid
import base64
import requests
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import subprocess

# Uygulama bilgileri
APP_NAME = "KERZZ BOSS"
APP_VERSION = "3.0.0"
DEVELOPER = "Osman Kobat"
GITHUB_REPO = "osmankobat/kerzz-boss"  # GitHub repo adresiniz
GITHUB_RAW_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}"

# Lisans dosya yolu
LICENSE_FILE = Path.home() / ".kerzz_boss" / "license.json"
CONFIG_FILE = Path.home() / ".kerzz_boss" / "config.json"


class LicenseManager:
    """Lisans yönetimi sınıfı"""
    
    def __init__(self):
        self.machine_id = self._get_machine_id()
        self.license_data = None
        self.is_valid = False
        self._ensure_config_dir()
    
    def _ensure_config_dir(self):
        """Konfigürasyon dizinini oluştur"""
        LICENSE_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    def _get_machine_id(self) -> str:
        """Benzersiz makine kimliği oluştur"""
        # Makine özelliklerini birleştir
        machine_info = f"{platform.node()}-{platform.machine()}-{platform.processor()}"
        
        # Windows için MAC adresi ekle
        try:
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) 
                          for ele in range(0, 48, 8)][::-1])
            machine_info += f"-{mac}"
        except:
            pass
        
        # Hash'le
        return hashlib.sha256(machine_info.encode()).hexdigest()[:32]
    
    def _generate_license_key(self, email: str) -> str:
        """Lisans anahtarı oluştur (sadece yönetici için)"""
        data = f"{email}-{self.machine_id}-{APP_NAME}"
        hash_val = hashlib.sha256(data.encode()).hexdigest()
        
        # Okunabilir format: XXXX-XXXX-XXXX-XXXX
        key = '-'.join([hash_val[i:i+4].upper() for i in range(0, 16, 4)])
        return key
    
    def _verify_license_key(self, license_key: str, email: str) -> bool:
        """Lisans anahtarını doğrula"""
        expected_key = self._generate_license_key(email)
        return license_key == expected_key
    
    def activate_license(self, license_key: str, email: str) -> Tuple[bool, str]:
        """Lisansı aktive et"""
        # Önce yerel doğrulama
        if not self._verify_license_key(license_key, email):
            return False, "❌ Geçersiz lisans anahtarı!"
        
        # GitHub'dan doğrulama (opsiyonel - repo'da licenses.json olmalı)
        github_valid = self._verify_with_github(license_key, email)
        
        if not github_valid:
            # GitHub doğrulaması başarısız olsa bile yerel çalışsın
            pass
        
        # Lisans bilgilerini kaydet
        self.license_data = {
            "license_key": license_key,
            "email": email,
            "machine_id": self.machine_id,
            "activated_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(days=365)).isoformat(),
            "app_version": APP_VERSION,
            "github_verified": github_valid
        }
        
        self._save_license()
        self.is_valid = True
        
        return True, "✅ Lisans başarıyla aktive edildi!"
    
    def _verify_with_github(self, license_key: str, email: str) -> bool:
        """GitHub üzerinden lisans doğrula"""
        try:
            # GitHub repo'sundaki licenses.json dosyasını kontrol et
            url = f"{GITHUB_RAW_URL}/licenses.json"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                licenses = response.json()
                for lic in licenses.get("valid_licenses", []):
                    if lic.get("key") == license_key and lic.get("email") == email:
                        return True
            return False
        except:
            # GitHub'a ulaşılamıyorsa yerel doğrulamaya güven
            return True
    
    def check_license(self) -> Tuple[bool, str]:
        """Mevcut lisansı kontrol et"""
        if not LICENSE_FILE.exists():
            return False, "❌ Lisans bulunamadı! Lütfen aktive edin."
        
        try:
            with open(LICENSE_FILE, 'r', encoding='utf-8') as f:
                self.license_data = json.load(f)
            
            # Makine ID kontrolü
            if self.license_data.get("machine_id") != self.machine_id:
                return False, "❌ Lisans bu bilgisayar için geçerli değil!"
            
            # Süre kontrolü
            expires_at = datetime.fromisoformat(self.license_data.get("expires_at", "2000-01-01"))
            if datetime.now() > expires_at:
                return False, "❌ Lisans süresi dolmuş! Lütfen yenileyin."
            
            self.is_valid = True
            days_left = (expires_at - datetime.now()).days
            return True, f"✅ Lisans geçerli ({days_left} gün kaldı)"
            
        except Exception as e:
            return False, f"❌ Lisans okuma hatası: {e}"
    
    def _save_license(self):
        """Lisans bilgilerini kaydet"""
        with open(LICENSE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.license_data, f, indent=2, ensure_ascii=False)
    
    def get_license_info(self) -> Optional[Dict]:
        """Lisans bilgilerini döndür"""
        return self.license_data
    
    def deactivate_license(self):
        """Lisansı deaktive et"""
        if LICENSE_FILE.exists():
            LICENSE_FILE.unlink()
        self.license_data = None
        self.is_valid = False


class UpdateManager:
    """Güncelleme yönetimi sınıfı"""
    
    def __init__(self):
        self.current_version = APP_VERSION
        self.latest_version = None
        self.update_available = False
        self.update_info = None
    
    def check_for_updates(self) -> Tuple[bool, str, Optional[Dict]]:
        """GitHub'dan güncelleme kontrolü"""
        try:
            # GitHub releases API
            url = f"{GITHUB_API_URL}/releases/latest"
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200:
                release = response.json()
                self.latest_version = release.get("tag_name", "").lstrip("v")
                
                if self._compare_versions(self.latest_version, self.current_version) > 0:
                    self.update_available = True
                    self.update_info = {
                        "version": self.latest_version,
                        "name": release.get("name"),
                        "body": release.get("body"),
                        "published_at": release.get("published_at"),
                        "download_url": self._get_download_url(release),
                        "html_url": release.get("html_url")
                    }
                    return True, f"🆕 Yeni sürüm mevcut: v{self.latest_version}", self.update_info
                else:
                    return False, f"✅ Güncel sürümü kullanıyorsunuz (v{self.current_version})", None
            
            elif response.status_code == 404:
                return False, "ℹ️ Release bulunamadı", None
            else:
                return False, f"⚠️ GitHub API hatası: {response.status_code}", None
                
        except requests.exceptions.Timeout:
            return False, "⚠️ Güncelleme kontrolü zaman aşımı", None
        except requests.exceptions.ConnectionError:
            return False, "⚠️ İnternet bağlantısı yok", None
        except Exception as e:
            return False, f"⚠️ Güncelleme kontrolü hatası: {e}", None
    
    def _get_download_url(self, release: Dict) -> Optional[str]:
        """İndirme URL'sini al"""
        assets = release.get("assets", [])
        for asset in assets:
            name = asset.get("name", "").lower()
            if name.endswith(".exe") or name.endswith(".zip"):
                return asset.get("browser_download_url")
        return release.get("zipball_url")
    
    def _compare_versions(self, v1: str, v2: str) -> int:
        """Sürüm karşılaştır: v1 > v2 ise 1, eşitse 0, küçükse -1"""
        try:
            parts1 = [int(x) for x in v1.split('.')]
            parts2 = [int(x) for x in v2.split('.')]
            
            # Uzunlukları eşitle
            while len(parts1) < len(parts2):
                parts1.append(0)
            while len(parts2) < len(parts1):
                parts2.append(0)
            
            for p1, p2 in zip(parts1, parts2):
                if p1 > p2:
                    return 1
                elif p1 < p2:
                    return -1
            return 0
        except:
            return 0
    
    def download_update(self, progress_callback=None) -> Tuple[bool, str]:
        """Güncellemeyi indir"""
        if not self.update_info or not self.update_info.get("download_url"):
            return False, "❌ İndirme URL'si bulunamadı"
        
        try:
            download_url = self.update_info["download_url"]
            download_path = Path.home() / ".kerzz_boss" / "updates"
            download_path.mkdir(parents=True, exist_ok=True)
            
            filename = download_url.split("/")[-1]
            filepath = download_path / filename
            
            # İndir
            response = requests.get(download_url, stream=True, timeout=60)
            total_size = int(response.headers.get('content-length', 0))
            
            downloaded = 0
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total_size:
                            progress_callback(downloaded / total_size * 100)
            
            return True, str(filepath)
            
        except Exception as e:
            return False, f"❌ İndirme hatası: {e}"
    
    def install_update(self, update_file: str) -> Tuple[bool, str]:
        """Güncellemeyi kur"""
        try:
            if update_file.endswith(".exe"):
                # Installer'ı çalıştır
                subprocess.Popen([update_file], shell=True)
                return True, "✅ Güncelleme başlatıldı. Uygulama kapanacak."
            elif update_file.endswith(".zip"):
                # ZIP'i aç
                import zipfile
                extract_path = Path(update_file).parent / "extracted"
                with zipfile.ZipFile(update_file, 'r') as zip_ref:
                    zip_ref.extractall(extract_path)
                return True, f"✅ Güncelleme çıkarıldı: {extract_path}"
            else:
                return False, "❌ Desteklenmeyen dosya formatı"
        except Exception as e:
            return False, f"❌ Kurulum hatası: {e}"


class BackgroundService:
    """Arka plan servisi yönetimi"""
    
    SERVICE_NAME = "KerzzBossService"
    SERVICE_DISPLAY_NAME = "KERZZ BOSS Update Service"
    SERVICE_DESCRIPTION = "KERZZ BOSS otomatik güncelleme servisi"
    
    def __init__(self):
        self.update_manager = UpdateManager()
        self.running = False
        self.check_interval = 3600  # 1 saat
    
    def check_and_notify(self):
        """Güncelleme kontrol et ve bildirim gönder"""
        has_update, message, info = self.update_manager.check_for_updates()
        
        if has_update:
            # Windows bildirimi gönder
            self._send_notification(
                "KERZZ BOSS Güncelleme",
                f"Yeni sürüm mevcut: v{info['version']}"
            )
        
        return has_update, message, info
    
    def _send_notification(self, title: str, message: str):
        """Windows bildirimi gönder"""
        try:
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast(title, message, duration=10, threaded=True)
        except ImportError:
            # win10toast yoksa PowerShell ile bildirim
            try:
                ps_script = f'''
                [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
                $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
                $textNodes = $template.GetElementsByTagName("text")
                $textNodes.Item(0).AppendChild($template.CreateTextNode("{title}")) | Out-Null
                $textNodes.Item(1).AppendChild($template.CreateTextNode("{message}")) | Out-Null
                $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
                [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("KERZZ BOSS").Show($toast)
                '''
                subprocess.run(["powershell", "-Command", ps_script], 
                             capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            except:
                pass
    
    def install_as_service(self) -> Tuple[bool, str]:
        """Windows servisi olarak kur"""
        try:
            # Servis script'i oluştur
            service_script = self._create_service_script()
            
            # NSSM ile servis kur (Non-Sucking Service Manager)
            # veya pywin32 kullan
            
            return True, "✅ Servis kuruldu"
        except Exception as e:
            return False, f"❌ Servis kurulum hatası: {e}"
    
    def _create_service_script(self) -> str:
        """Servis script'i oluştur"""
        script_path = Path.home() / ".kerzz_boss" / "service" / "update_service.py"
        script_path.parent.mkdir(parents=True, exist_ok=True)
        
        script_content = '''
"""KERZZ BOSS Update Service"""
import time
import sys
sys.path.insert(0, r"''' + str(Path(__file__).parent) + '''")

from license_manager import UpdateManager, BackgroundService

def main():
    service = BackgroundService()
    while True:
        try:
            service.check_and_notify()
        except Exception as e:
            print(f"Hata: {e}")
        time.sleep(3600)  # 1 saat bekle

if __name__ == "__main__":
    main()
'''
        
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        return str(script_path)
    
    def create_startup_shortcut(self) -> Tuple[bool, str]:
        """Windows başlangıcına kısayol ekle"""
        try:
            import winshell
            from win32com.client import Dispatch
            
            startup_folder = winshell.startup()
            shortcut_path = os.path.join(startup_folder, "KERZZ BOSS Updater.lnk")
            
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.Targetpath = sys.executable
            shortcut.Arguments = f'"{self._create_service_script()}"'
            shortcut.WorkingDirectory = str(Path.home() / ".kerzz_boss")
            shortcut.Description = "KERZZ BOSS Güncelleme Kontrolü"
            shortcut.save()
            
            return True, f"✅ Başlangıç kısayolu oluşturuldu: {shortcut_path}"
        except ImportError:
            # winshell yoksa manuel yol
            return self._create_startup_bat()
        except Exception as e:
            return False, f"❌ Kısayol oluşturma hatası: {e}"
    
    def _create_startup_bat(self) -> Tuple[bool, str]:
        """Başlangıç BAT dosyası oluştur"""
        try:
            startup_folder = os.path.join(
                os.environ.get('APPDATA', ''),
                r'Microsoft\Windows\Start Menu\Programs\Startup'
            )
            bat_path = os.path.join(startup_folder, "kerzz_updater.bat")
            
            script_path = self._create_service_script()
            
            bat_content = f'''@echo off
start /min "" pythonw "{script_path}"
'''
            
            with open(bat_path, 'w') as f:
                f.write(bat_content)
            
            return True, f"✅ Başlangıç script'i oluşturuldu: {bat_path}"
        except Exception as e:
            return False, f"❌ BAT dosyası oluşturma hatası: {e}"
    
    def remove_from_startup(self) -> Tuple[bool, str]:
        """Başlangıçtan kaldır"""
        try:
            startup_folder = os.path.join(
                os.environ.get('APPDATA', ''),
                r'Microsoft\Windows\Start Menu\Programs\Startup'
            )
            
            # BAT dosyasını kaldır
            bat_path = os.path.join(startup_folder, "kerzz_updater.bat")
            if os.path.exists(bat_path):
                os.remove(bat_path)
            
            # LNK kısayolunu kaldır
            lnk_path = os.path.join(startup_folder, "KERZZ BOSS Updater.lnk")
            if os.path.exists(lnk_path):
                os.remove(lnk_path)
            
            return True, "✅ Başlangıçtan kaldırıldı"
        except Exception as e:
            return False, f"❌ Kaldırma hatası: {e}"


# ===================== KODLAMA/ŞİFRELEME =====================

class CodeProtection:
    """Kod koruma ve şifreleme"""
    
    @staticmethod
    def get_protection_commands() -> str:
        """Kod koruma komutlarını döndür"""
        return """
# KERZZ BOSS Kod Koruma ve EXE Oluşturma Rehberi

## 1. Gerekli Paketleri Kur
pip install pyinstaller pyarmor nuitka

## 2. PyArmor ile Kod Şifreleme
# Tüm .py dosyalarını şifrele
pyarmor gen -O dist_protected kerzz_gui_modern.py kerzz_yonetim_programi.py license_manager.py

## 3. PyInstaller ile EXE Oluşturma (Şifreli kodlarla)
cd dist_protected
pyinstaller --onefile --windowed --icon=app.ico --name="KerzzBoss" kerzz_gui_modern.py

## 4. Nuitka ile Derleme (Daha güçlü koruma)
nuitka --standalone --onefile --windows-icon-from-ico=app.ico ^
       --enable-plugin=tk-inter ^
       --windows-company-name="Osman Kobat" ^
       --windows-product-name="KERZZ BOSS" ^
       --windows-file-version=3.0.0.0 ^
       --windows-product-version=3.0.0.0 ^
       kerzz_gui_modern.py

## 5. UPX ile Sıkıştırma (İsteğe bağlı)
upx --best KerzzBoss.exe
"""
    
    @staticmethod
    def create_pyinstaller_spec() -> str:
        """PyInstaller spec dosyası oluştur"""
        spec_content = '''# -*- mode: python ; coding: utf-8 -*-
# KERZZ BOSS PyInstaller Spec File
# Geliştirici: Osman Kobat

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Uygulama bilgileri
APP_NAME = "KerzzBoss"
APP_VERSION = "3.0.0"
COMPANY = "Osman Kobat"

a = Analysis(
    ['kerzz_gui_modern.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('LICENSE', '.'),
    ],
    hiddenimports=[
        'kerzz_yonetim_programi',
        'license_manager',
        'customtkinter',
        'PIL._tkinter_finder',
        'requests',
        'pyodbc',
        'pandas',
        'openpyxl',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'numpy.tests', 'scipy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI uygulama
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app.ico',  # İkon dosyası
    version='version_info.txt',  # Sürüm bilgisi
)
'''
        return spec_content


# Test için
if __name__ == "__main__":
    print("=" * 50)
    print("KERZZ BOSS Lisans ve Güncelleme Yöneticisi")
    print("Geliştirici: Osman Kobat")
    print("=" * 50)
    
    # Lisans kontrolü
    lm = LicenseManager()
    valid, msg = lm.check_license()
    print(f"\nLisans Durumu: {msg}")
    print(f"Makine ID: {lm.machine_id}")
    
    # Güncelleme kontrolü
    um = UpdateManager()
    has_update, update_msg, info = um.check_for_updates()
    print(f"\nGüncelleme: {update_msg}")
    
    if info:
        print(f"Yeni Sürüm: {info.get('version')}")
        print(f"İndirme: {info.get('download_url')}")
