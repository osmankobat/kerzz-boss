#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KERZZ BOSS - Güncelleme Kontrol Scripti
Geliştirici: Osman Kobat
MIT License (c) 2024-2026

Bu script GitHub Releases üzerinden güncelleme kontrolü yapar.
"""

import requests
import sys
import os
from pathlib import Path

# Sabitleri
APP_VERSION = "3.0.0"
GITHUB_REPO = "osmankobat/kerzz-boss"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

def parse_version(version_str: str) -> tuple:
    """Versiyon string'ini tuple'a çevir"""
    try:
        clean_version = version_str.lstrip('vV').split('-')[0]
        parts = clean_version.split('.')
        return tuple(int(p) for p in parts[:3])
    except:
        return (0, 0, 0)

def check_for_updates():
    """GitHub'dan güncelleme kontrolü yap"""
    print(f"\n{'='*50}")
    print(f"🍽️ KERZZ BOSS - Güncelleme Kontrolü")
    print(f"{'='*50}")
    print(f"\n📌 Mevcut Sürüm: v{APP_VERSION}")
    print(f"🔗 GitHub: https://github.com/{GITHUB_REPO}")
    print(f"\n⏳ Güncelleme kontrol ediliyor...")
    
    try:
        response = requests.get(
            GITHUB_API,
            headers={"Accept": "application/vnd.github.v3+json"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            latest_version = data.get('tag_name', '0.0.0')
            
            current = parse_version(APP_VERSION)
            latest = parse_version(latest_version)
            
            print(f"\n📦 En Son Sürüm: {latest_version}")
            
            if latest > current:
                print(f"\n✅ YENİ GÜNCELLEME MEVCUT!")
                print(f"\n📋 Değişiklikler:")
                print("-" * 40)
                print(data.get('body', 'Açıklama yok')[:500])
                print("-" * 40)
                
                # Download URL
                assets = data.get('assets', [])
                for asset in assets:
                    if asset['name'].endswith('.exe'):
                        print(f"\n⬇️ İndirme Linki:")
                        print(f"   {asset['browser_download_url']}")
                        print(f"   Boyut: {asset['size'] / 1024 / 1024:.1f} MB")
                
                print(f"\n🌐 Release Sayfası: {data.get('html_url')}")
                return True
            else:
                print(f"\n✅ Güncel sürümü kullanıyorsunuz!")
                return False
                
        elif response.status_code == 404:
            print(f"\n⚠️ Henüz release yayınlanmamış.")
            print(f"   Repo: https://github.com/{GITHUB_REPO}")
            return False
        else:
            print(f"\n❌ GitHub API Hatası: {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"\n⚠️ Bağlantı zaman aşımı! İnternet bağlantınızı kontrol edin.")
        return False
    except requests.exceptions.ConnectionError:
        print(f"\n⚠️ Bağlantı hatası! İnternet bağlantınızı kontrol edin.")
        return False
    except Exception as e:
        print(f"\n❌ Hata: {e}")
        return False

def create_release_info():
    """Release için bilgi dosyası oluştur"""
    info = f"""
KERZZ BOSS v{APP_VERSION}
========================

📅 Tarih: Ocak 2026
👨‍💻 Geliştirici: Osman Kobat
📜 Lisans: MIT License

✨ Bu Sürümde Yenilikler:
- Modern CustomTkinter arayüzü
- Excel benzeri filtreleme
- Lisans yönetim sistemi
- Otomatik güncelleme kontrolü
- Windows arkaplan servisi
- Korumalı EXE dağıtımı

📦 Bağımlılıklar:
- Python 3.8+
- CustomTkinter
- Pandas
- Requests
- Pillow

🔗 GitHub: https://github.com/{GITHUB_REPO}
"""
    
    output_path = Path("dist/RELEASE_NOTES.txt")
    output_path.write_text(info, encoding='utf-8')
    print(f"\n📝 Release notları oluşturuldu: {output_path}")

if __name__ == "__main__":
    has_update = check_for_updates()
    
    if "--create-notes" in sys.argv:
        create_release_info()
    
    print(f"\n{'='*50}")
    input("\nÇıkmak için Enter'a basın...")
