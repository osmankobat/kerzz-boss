# -*- mode: python ; coding: utf-8 -*-
# ============================================================
# KERZZ BOSS PyInstaller Spec File
# Geliştirici: Osman Kobat
# MIT License (c) 2024-2026
# ============================================================
#
# KULLANIM:
# pyinstaller KerzzBoss_Protected.spec
#
# ÖNCESİNDE PyArmor ile şifrele:
# pyarmor gen -O dist_protected kerzz_gui_modern.py kerzz_yonetim_programi.py license_manager.py
# ============================================================

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Şifreleme anahtarı (32 byte)
block_cipher = None  # PyArmor kullanılıyorsa None bırak

# Uygulama bilgileri
APP_NAME = "KerzzBoss"
APP_VERSION = "3.0.0"
COMPANY = "Osman Kobat"

# Ana dizin
BASEDIR = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    ['kerzz_gui_modern.py'],
    pathex=[BASEDIR],
    binaries=[],
    datas=[
        ('LICENSE', '.'),
        ('assets/icon.ico', 'assets'),
        ('assets/icon.png', 'assets'),
    ],
    hiddenimports=[
        # Ana modüller
        'kerzz_yonetim_programi',
        'license_manager',
        
        # CustomTkinter
        'customtkinter',
        'customtkinter.windows',
        'customtkinter.windows.widgets',
        
        # Tkinter
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.filedialog',
        
        # PIL/Pillow
        'PIL',
        'PIL._tkinter_finder',
        'PIL.Image',
        'PIL.ImageTk',
        
        # Veritabanı
        'pyodbc',
        
        # Veri işleme
        'pandas',
        'pandas.core',
        'openpyxl',
        
        # Ağ
        'requests',
        'urllib3',
        
        # Diğer
        'json',
        'hashlib',
        'uuid',
        'threading',
        'datetime',
        'pathlib',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Gereksiz büyük paketler
        'matplotlib',
        'numpy.tests',
        'scipy',
        'IPython',
        'notebook',
        'pytest',
        'sphinx',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Gereksiz dosyaları kaldır (boyut küçültme)
def remove_unwanted(analysis):
    unwanted = ['tcl/tzdata', 'tcl/encoding', 'tcl/msgs']
    for item in unwanted:
        analysis.datas = [x for x in analysis.datas if item not in x[0]]
    return analysis

a = remove_unwanted(a)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

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
    upx_exclude=[
        'vcruntime140.dll',
        'python*.dll',
    ],
    runtime_tmpdir=None,
    console=False,  # GUI uygulama - konsol yok
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',
    version='version_info.txt' if os.path.exists('version_info.txt') else None,
    manifest=None,
    uac_admin=False,  # Admin yetkisi gerektirmez
)

# ============================================================
# EXE OLUŞTURMA KOMUTLARI
# ============================================================
#
# 1. Normal EXE:
#    pyinstaller KerzzBoss_Protected.spec
#
# 2. PyArmor ile şifreli EXE:
#    pyarmor gen -O protected kerzz_gui_modern.py kerzz_yonetim_programi.py license_manager.py
#    cd protected
#    pyinstaller ../KerzzBoss_Protected.spec
#
# 3. Nuitka ile derleme (en güçlü koruma):
#    nuitka --standalone --onefile --windows-disable-console ^
#           --windows-icon-from-ico=app.ico ^
#           --enable-plugin=tk-inter ^
#           --company-name="Osman Kobat" ^
#           --product-name="KERZZ BOSS" ^
#           --file-version=3.0.0.0 ^
#           kerzz_gui_modern.py
#
# ============================================================
