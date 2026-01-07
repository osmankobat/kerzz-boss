"""
KERZZ Boss Yönetim Programı
============================

Bu program TALAS veritabanında şu işlemleri yapar:
1. Birleştirilen adisyonları görüntüler ve geri alır
2. İptal edilen ürünleri görüntüler  
3. Adisyon/ürün silme işlemi
4. Fiyat güncelleme
5. Arşiv ve log kayıtlarını görüntüleme

NOT: Kerzz Boss programında adisyon silme işlemi yapılsa bile,
SQL sorgularında görünür çünkü kayıtlar TBL_ADISYON tablosunda
'silinme' kolonu 1 yapılarak soft delete yapılıyor.
Gerçek silme için kayıtların TBL_A_ADISYON (arşiv) tablosuna
taşınması veya fiziksel olarak DELETE işlemi gerekiyor.
"""

import pyodbc
import pandas as pd
import warnings
from datetime import datetime
from typing import List, Dict, Optional

# Pandas SQLAlchemy uyarısını bastır (pyodbc bağlantısı hala çalışıyor)
warnings.filterwarnings('ignore', message='.*pandas only supports SQLAlchemy.*')

class KerzzYonetim:
    """KERZZ BOSS veritabanı yönetim sınıfı"""
    
    def __init__(self, server: str, database: str, username: str = None, password: str = None):
        """
        Args:
            server: SQL Server adresi (örn: 'ABC01CL099' veya '172.20.16.13')
            database: Veritabanı adı (TALAS, VERI, LOG_DB)
            username: Kullanıcı adı (None ise Windows Authentication)
            password: Şifre
        """
        self.server = server
        self.database = database
        self.username = username
        self.password = password
        self.conn = None
        
    def baglan(self):
        """Veritabanına bağlan"""
        try:
            if self.username and self.password:
                # SQL Server Authentication
                conn_str = (
                    f"DRIVER={{SQL Server}};"
                    f"SERVER={self.server};"
                    f"DATABASE={self.database};"
                    f"UID={self.username};"
                    f"PWD={self.password}"
                )
            else:
                # Windows Authentication
                conn_str = (
                    f"DRIVER={{SQL Server}};"
                    f"SERVER={self.server};"
                    f"DATABASE={self.database};"
                    f"Trusted_Connection=yes;"
                )
            
            self.conn = pyodbc.connect(conn_str)
            print(f"✓ {self.database} veritabanına bağlandı")
            return True
        except Exception as e:
            print(f"✗ Bağlantı hatası: {e}")
            return False
    
    def kapat(self):
        """Bağlantıyı kapat"""
        if self.conn:
            self.conn.close()
            print("✓ Bağlantı kapatıldı")
    
    def veri_cek(self, sql: str, params: list = None) -> pd.DataFrame:
        """
        Genel SQL sorgusu çalıştır ve DataFrame döndür
        
        Args:
            sql: SQL sorgusu
            params: Parametreler
        
        Returns:
            DataFrame: Sorgu sonucu
        """
        try:
            if params:
                return pd.read_sql(sql, self.conn, params=params)
            else:
                return pd.read_sql(sql, self.conn)
        except Exception as e:
            print(f"✗ Sorgu hatası: {e}")
            raise
    
    # ==================== BİRLEŞTİRİLEN ADİSYONLAR ====================
    
    def birlestirilen_adisyonlari_listele(self, baslangic_tarih: str = None, bitis_tarih: str = None) -> pd.DataFrame:
        """
        Birleştirilmiş adisyonları listele
        
        Args:
            baslangic_tarih: Başlangıç tarihi (YYYY-MM-DD)
            bitis_tarih: Bitiş tarihi (YYYY-MM-DD)
        
        Returns:
            DataFrame: Birleştirme kayıtları
        """
        sql = """
        SELECT 
            Kimlik,
            ISLEM_ZAMANI,
            HEDEF_MASA,
            HEDEF_ADISYONNO,
            HEDEF_KIMLIK,
            IPTAL_MASA,
            IPTAL_ADISYONNO,
            IPTAL_KIMLIK,
            KULLANICI,
            HEDEF_URUN_SAYI,
            IPTAL_URUN_SAYI
        FROM TBL_MASABIRLESTIRME
        WHERE 1=1
        """
        
        params = []
        if baslangic_tarih:
            sql += " AND ISLEM_ZAMANI >= ?"
            params.append(baslangic_tarih)
        if bitis_tarih:
            sql += " AND ISLEM_ZAMANI <= ?"
            params.append(bitis_tarih + ' 23:59:59')
        
        sql += " ORDER BY ISLEM_ZAMANI DESC"
        
        return pd.read_sql(sql, self.conn, params=params)
    
    def birlestirmeyi_geri_al(self, kimlik: int) -> bool:
        """
        Masa birleştirme işlemini geri al
        
        Args:
            kimlik: TBL_MASABIRLESTIRME.Kimlik değeri
        
        Returns:
            bool: İşlem başarılı mı
        """
        try:
            cursor = self.conn.cursor()
            
            # Önce birleştirme kaydını al
            cursor.execute("""
                SELECT IPTAL_MASA, IPTAL_ADISYONNO, IPTAL_KIMLIK, 
                       HEDEF_MASA, HEDEF_ADISYONNO
                FROM TBL_MASABIRLESTIRME 
                WHERE Kimlik = ?
            """, (kimlik,))
            
            kayit = cursor.fetchone()
            if not kayit:
                print(f"✗ Kimlik {kimlik} bulunamadı")
                return False
            
            iptal_masa, iptal_adisyonno, iptal_kimlik, hedef_masa, hedef_adisyonno = kayit
            
            # İptal edilen adisyonu yeniden aktif et
            # Bu işlem birleştirme işleminden önce iptal edilen masanın
            # ürünlerini geri getirecek
            
            print(f"⚠ DİKKAT: Birleştirme geri alma işlemi manuel müdahale gerektirebilir")
            print(f"  İptal Edilen: {iptal_masa} / {iptal_adisyonno}")
            print(f"  Hedef Masa: {hedef_masa} / {hedef_adisyonno}")
            print(f"  Lütfen Kerzz Boss programından kontrol edin")
            
            # Birleştirme kaydını sil
            cursor.execute("DELETE FROM TBL_MASABIRLESTIRME WHERE Kimlik = ?", (kimlik,))
            self.conn.commit()
            
            print(f"✓ Birleştirme kaydı silindi (ID: {kimlik})")
            return True
            
        except Exception as e:
            print(f"✗ Hata: {e}")
            self.conn.rollback()
            return False
    
    # ==================== İPTAL EDİLEN ÜRÜNLER ====================
    
    def iptal_urunleri_listele(self, baslangic_tarih: str = None, bitis_tarih: str = None, 
                               adisyonno: str = None) -> pd.DataFrame:
        """
        İptal edilmiş ürünleri listele (silinme = 1)
        
        Args:
            baslangic_tarih: Başlangıç tarihi
            bitis_tarih: Bitiş tarihi
            adisyonno: Adisyon numarası filtresi
        
        Returns:
            DataFrame: İptal ürünler
        """
        sql = """
        SELECT 
            Anahtar,
            Tarih,
            adisyonno,
            masa,
            urunadi,
            miktari,
            birimfiyati,
            toplam,
            silen,
            SILINME_ZAMAN,
            sebep,
            NEDEN
        FROM TBL_ADISYON
        WHERE silinme = 1
        """
        
        params = []
        if baslangic_tarih:
            sql += " AND SILINME_ZAMAN >= ?"
            params.append(baslangic_tarih)
        if bitis_tarih:
            sql += " AND SILINME_ZAMAN <= ?"
            params.append(bitis_tarih + ' 23:59:59')
        if adisyonno:
            sql += " AND adisyonno = ?"
            params.append(adisyonno)
        
        sql += " ORDER BY SILINME_ZAMAN DESC"
        
        return pd.read_sql(sql, self.conn, params=params)
    
    def urun_iptalini_geri_al(self, anahtar: int) -> bool:
        """
        Ürün iptalini geri al (silinme = 0 yap)
        
        Args:
            anahtar: TBL_ADISYON.Anahtar (PK)
        
        Returns:
            bool: İşlem başarılı mı
        """
        try:
            cursor = self.conn.cursor()
            
            # Ürünü geri getir
            cursor.execute("""
                UPDATE TBL_ADISYON 
                SET silinme = 0, 
                    SILINME_ZAMAN = NULL,
                    silen = NULL,
                    sebep = NULL
                WHERE Anahtar = ? AND silinme = 1
            """, (anahtar,))
            
            if cursor.rowcount > 0:
                self.conn.commit()
                print(f"✓ Ürün iptali geri alındı (Anahtar: {anahtar})")
                return True
            else:
                print(f"✗ Kayıt bulunamadı veya zaten aktif (Anahtar: {anahtar})")
                return False
                
        except Exception as e:
            print(f"✗ Hata: {e}")
            self.conn.rollback()
            return False
    
    def iptal_urunu_kalici_sil(self, anahtar: int) -> bool:
        """
        İptal edilmiş ürünü veritabanından kalıcı olarak sil
        
        Args:
            anahtar: TBL_ADISYON.Anahtar (PK)
        
        Returns:
            bool: İşlem başarılı mı
        """
        try:
            cursor = self.conn.cursor()
            
            # Sadece silinme=1 olanları kalıcı sil (güvenlik için)
            cursor.execute("""
                DELETE FROM TBL_ADISYON 
                WHERE Anahtar = ? AND silinme = 1
            """, (anahtar,))
            
            if cursor.rowcount > 0:
                self.conn.commit()
                print(f"✓ İptal ürünü kalıcı silindi (Anahtar: {anahtar})")
                return True
            else:
                print(f"✗ Kayıt bulunamadı veya iptal değil (Anahtar: {anahtar})")
                return False
                
        except Exception as e:
            print(f"✗ Hata: {e}")
            self.conn.rollback()
            return False
    
    def iptal_urunleri_toplu_kalici_sil(self, anahtarlar: list) -> dict:
        """
        Birden fazla iptal ürünü kalıcı sil
        
        Args:
            anahtarlar: Silinecek anahtar listesi
        
        Returns:
            dict: {basarili: int, hatali: int}
        """
        sonuc = {'basarili': 0, 'hatali': 0}
        
        for anahtar in anahtarlar:
            if self.iptal_urunu_kalici_sil(anahtar):
                sonuc['basarili'] += 1
            else:
                sonuc['hatali'] += 1
        
        return sonuc
    
    # ==================== ADİSYON/ÜRÜN SİLME ====================
    
    def adisyon_sil(self, adisyonno: str, kullanici: str, sebep: str = None) -> bool:
        """
        Adisyondaki tüm ürünleri soft delete ile sil
        
        Args:
            adisyonno: Adisyon numarası
            kullanici: Silen kullanıcı adı
            sebep: Silme sebebi
        
        Returns:
            bool: İşlem başarılı mı
        """
        try:
            cursor = self.conn.cursor()
            
            # Adisyondaki aktif ürünleri say
            cursor.execute("""
                SELECT COUNT(*) FROM TBL_ADISYON 
                WHERE adisyonno = ? AND (silinme = 0 OR silinme IS NULL)
            """, (adisyonno,))
            
            aktif_urun_sayisi = cursor.fetchone()[0]
            
            if aktif_urun_sayisi == 0:
                print(f"✗ Adisyon {adisyonno} için aktif ürün bulunamadı")
                return False
            
            # Tüm ürünleri soft delete
            cursor.execute("""
                UPDATE TBL_ADISYON
                SET silinme = 1,
                    SILINME_ZAMAN = GETDATE(),
                    silen = ?,
                    NEDEN = ?
                WHERE adisyonno = ? AND (silinme = 0 OR silinme IS NULL)
            """, (kullanici, sebep, adisyonno))
            
            self.conn.commit()
            print(f"✓ Adisyon {adisyonno} silindi ({cursor.rowcount} ürün)")
            print(f"  ⚠ NOT: Kayıtlar hala TBL_ADISYON'da görünür (silinme=1)")
            print(f"  Kerzz Boss programında görüntülenmez ancak SQL'de görünür!")
            return True
            
        except Exception as e:
            print(f"✗ Hata: {e}")
            self.conn.rollback()
            return False
    
    def adisyonu_fiziksel_sil(self, adisyonno: str) -> bool:
        """
        Adisyonu VERİTABANINDAN TAMAMEN SİL
        ⚠️ DİKKAT: Bu işlem GERİ ALINAMAZ!
        
        Args:
            adisyonno: Adisyon numarası
        
        Returns:
            bool: İşlem başarılı mı
        """
        try:
            cursor = self.conn.cursor()
            
            # Önce yedek al (arşive taşı)
            cursor.execute("""
                INSERT INTO TBL_A_ADISYON 
                SELECT * FROM TBL_ADISYON WHERE adisyonno = ?
            """, (adisyonno,))
            
            arsiv_sayi = cursor.rowcount
            
            # Fiziksel silme
            cursor.execute("DELETE FROM TBL_ADISYON WHERE adisyonno = ?", (adisyonno,))
            
            silinen_sayi = cursor.rowcount
            
            self.conn.commit()
            print(f"✓ Adisyon {adisyonno} FİZİKSEL olarak silindi")
            print(f"  Arşive taşınan kayıt: {arsiv_sayi}")
            print(f"  Silinen kayıt: {silinen_sayi}")
            return True
            
        except Exception as e:
            print(f"✗ Hata: {e}")
            self.conn.rollback()
            return False
    
    # ==================== DERİN SİLME (DEEP DELETE) ====================
    
    def derin_sil(self, deger: str, deger_tipi: str = 'adisyonno') -> Dict:
        """
        Bir değeri TÜM veritabanlarından (TALAS, LOG_DB, VERI) tamamen sil
        Her tabloda, her kolonda arama yapar ve bulduğu her kaydı siler
        ⚠️ DİKKAT: Bu işlem GERİ ALINAMAZ ve tüm referansları siler!
        
        Args:
            deger: Silinecek değer (örn: adisyon no, kayıt no)
            deger_tipi: Değer tipi ('adisyonno', 'kayitno', 'anahtar', 'kimlik')
        
        Returns:
            dict: {
                'basarili': bool,
                'toplam_silinen': int,
                'detay': {
                    'TALAS': {'tablo1': silinen_sayi, ...},
                    'LOG_DB': {...},
                    'VERI': {...}
                },
                'hatalar': []
            }
        """
        sonuc = {
            'basarili': True,
            'toplam_silinen': 0,
            'detay': {
                'TALAS': {},
                'LOG_DB': {},
                'VERI': {}
            },
            'hatalar': []
        }
        
        # Veritabanı listesi
        veritabanlari = ['TALAS', 'LOG_DB', 'VERI']
        
        # Her veritabanında ara ve sil
        for db_adi in veritabanlari:
            try:
                # Yeni bağlantı oluştur
                db_conn = pyodbc.connect(
                    f"DRIVER={{SQL Server}};"
                    f"SERVER={self.server};"
                    f"DATABASE={db_adi};"
                    f"Trusted_Connection=yes;"
                )
                cursor = db_conn.cursor()
                
                # Veritabanındaki tüm tabloları bul
                cursor.execute("""
                    SELECT TABLE_SCHEMA, TABLE_NAME 
                    FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_TYPE = 'BASE TABLE'
                """)
                tablolar = cursor.fetchall()
                
                for schema, tablo in tablolar:
                    tam_tablo = f"{schema}.{tablo}"
                    
                    # Bu tablodaki kolonları bul
                    cursor.execute("""
                        SELECT COLUMN_NAME 
                        FROM INFORMATION_SCHEMA.COLUMNS 
                        WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
                    """, (schema, tablo))
                    kolonlar = [row[0] for row in cursor.fetchall()]
                    
                    # Değer tipine göre uygun kolonları bul
                    uygun_kolonlar = []
                    arama_kolonlar = {
                        'adisyonno': ['adisyonno', 'adisyon_no', 'ADISYONNO'],
                        'kayitno': ['kayitno', 'kayit_no', 'KAYITNO', 'recordno'],
                        'anahtar': ['Anahtar', 'anahtar', 'ANAHTAR', 'ID', 'id'],
                        'kimlik': ['Kimlik', 'kimlik', 'KIMLIK', 'ID', 'id']
                    }
                    
                    if deger_tipi in arama_kolonlar:
                        for kolon in kolonlar:
                            if any(ak.lower() == kolon.lower() for ak in arama_kolonlar[deger_tipi]):
                                uygun_kolonlar.append(kolon)
                    
                    # Eğer uygun kolon varsa sil
                    for kolon in uygun_kolonlar:
                        try:
                            # Kolonun veri tipini kontrol et
                            cursor.execute("""
                                SELECT DATA_TYPE 
                                FROM INFORMATION_SCHEMA.COLUMNS 
                                WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? AND COLUMN_NAME = ?
                            """, (schema, tablo, kolon))
                            tip_row = cursor.fetchone()
                            
                            if tip_row:
                                veri_tipi = tip_row[0].lower()
                                # Sayısal tip ve değer sayısal değilse atla
                                sayisal_tipler = ['int', 'bigint', 'smallint', 'tinyint', 'numeric', 'decimal', 'float', 'real']
                                if veri_tipi in sayisal_tipler:
                                    # Değerin sayısal olup olmadığını kontrol et
                                    try:
                                        int(deger)  # Sayıya çevrilebilir mi?
                                    except ValueError:
                                        # Sayısal değil, bu kolonu atla
                                        continue
                            
                            # Önce kaç kayıt var kontrol et
                            cursor.execute(
                                f"SELECT COUNT(*) FROM {tam_tablo} WHERE [{kolon}] = ?",
                                (deger,)
                            )
                            kayit_sayi = cursor.fetchone()[0]
                            
                            if kayit_sayi > 0:
                                # Silme işlemi
                                cursor.execute(
                                    f"DELETE FROM {tam_tablo} WHERE [{kolon}] = ?",
                                    (deger,)
                                )
                                silinen = cursor.rowcount
                                
                                if silinen > 0:
                                    sonuc['detay'][db_adi][tam_tablo] = silinen
                                    sonuc['toplam_silinen'] += silinen
                                    print(f"  ✓ {db_adi}.{tam_tablo}.{kolon}: {silinen} kayıt silindi")
                        
                        except Exception as kolon_hata:
                            # Bu kolondan silerken hata olsa bile devam et
                            sonuc['hatalar'].append(f"{db_adi}.{tam_tablo}.{kolon}: {str(kolon_hata)}")
                
                db_conn.commit()
                db_conn.close()
                
            except Exception as db_hata:
                sonuc['hatalar'].append(f"{db_adi}: {str(db_hata)}")
                sonuc['basarili'] = False
        
        print(f"\n{'='*60}")
        print(f"DERİN SİLME TAMAMLANDI")
        print(f"{'='*60}")
        print(f"Değer: {deger} ({deger_tipi})")
        print(f"Toplam Silinen Kayıt: {sonuc['toplam_silinen']}")
        print(f"Başarı Durumu: {'✓ BAŞARILI' if sonuc['basarili'] else '⚠ HATALI'}")
        
        if sonuc['hatalar']:
            print(f"\n⚠ Hatalar ({len(sonuc['hatalar'])}):")
            for hata in sonuc['hatalar'][:10]:  # İlk 10 hata
                print(f"  - {hata}")
        
        return sonuc
    
    def coklu_derin_sil(self, degerler: List[str], deger_tipi: str = 'adisyonno', 
                        progress_callback=None) -> Dict:
        """
        Birden fazla değeri derin silme ile tamamen temizle
        
        Args:
            degerler: Silinecek değerler listesi
            deger_tipi: Değer tipi
            progress_callback: İlerleme callback fonksiyonu (opsiyonel)
        
        Returns:
            dict: Toplam sonuç özeti
        """
        toplam_sonuc = {
            'basarili_sayi': 0,
            'hatali_sayi': 0,
            'toplam_silinen': 0,
            'detay_liste': []
        }
        
        toplam = len(degerler)
        
        for i, deger in enumerate(degerler, 1):
            if progress_callback:
                progress_callback(i, toplam, deger)
            
            print(f"\n[{i}/{toplam}] {deger} değeri siliniyor...")
            
            sonuc = self.derin_sil(deger, deger_tipi)
            
            if sonuc['basarili']:
                toplam_sonuc['basarili_sayi'] += 1
            else:
                toplam_sonuc['hatali_sayi'] += 1
            
            toplam_sonuc['toplam_silinen'] += sonuc['toplam_silinen']
            toplam_sonuc['detay_liste'].append({
                'deger': deger,
                'silinen': sonuc['toplam_silinen'],
                'basarili': sonuc['basarili']
            })
        
        print(f"\n{'='*60}")
        print(f"TOPLU DERİN SİLME TAMAMLANDI")
        print(f"{'='*60}")
        print(f"Toplam İşlem: {toplam}")
        print(f"Başarılı: {toplam_sonuc['basarili_sayi']}")
        print(f"Hatalı: {toplam_sonuc['hatali_sayi']}")
        print(f"Toplam Silinen Kayıt: {toplam_sonuc['toplam_silinen']}")
        
        return toplam_sonuc
    
    # ==================== FİYAT GÜNCELLEME ====================
    
    def fiyat_guncelle(self, anahtar: int, yeni_fiyat: float) -> bool:
        """
        Belirli bir ürünün fiyatını güncelle
        
        Args:
            anahtar: TBL_ADISYON.Anahtar
            yeni_fiyat: Yeni birim fiyat
        
        Returns:
            bool: İşlem başarılı mı
        """
        try:
            cursor = self.conn.cursor()
            
            # Önce mevcut kaydı al
            cursor.execute("""
                SELECT urunadi, miktari, birimfiyati, adisyonno 
                FROM TBL_ADISYON WHERE Anahtar = ?
            """, (anahtar,))
            
            kayit = cursor.fetchone()
            if not kayit:
                print(f"✗ Kayıt bulunamadı (Anahtar: {anahtar})")
                return False
            
            urun, miktar, eski_fiyat, adisyon = kayit
            yeni_toplam = miktar * yeni_fiyat
            
            # Fiyat güncelle
            cursor.execute("""
                UPDATE TBL_ADISYON
                SET birimfiyati = ?,
                    toplam = ?,
                    LastEditDate = GETDATE()
                WHERE Anahtar = ?
            """, (yeni_fiyat, yeni_toplam, anahtar))
            
            self.conn.commit()
            print(f"✓ Fiyat güncellendi:")
            print(f"  Adisyon: {adisyon}")
            print(f"  Ürün: {urun}")
            print(f"  Eski Fiyat: {eski_fiyat:.2f} TL")
            print(f"  Yeni Fiyat: {yeni_fiyat:.2f} TL")
            print(f"  Yeni Toplam: {yeni_toplam:.2f} TL")
            return True
            
        except Exception as e:
            print(f"✗ Hata: {e}")
            self.conn.rollback()
            return False
    
    def toplu_fiyat_guncelle(self, urun_adi: str, yeni_fiyat: float, 
                             baslangic_tarih: str = None) -> bool:
        """
        Belirli bir ürünün tüm aktif kayıtlarında fiyat güncelle
        
        Args:
            urun_adi: Ürün adı
            yeni_fiyat: Yeni birim fiyat
            baslangic_tarih: Bu tarihten sonraki kayıtlar (None ise tümü)
        
        Returns:
            bool: İşlem başarılı mı
        """
        try:
            cursor = self.conn.cursor()
            
            sql = """
                UPDATE TBL_ADISYON
                SET birimfiyati = ?,
                    toplam = miktari * ?,
                    LastEditDate = GETDATE()
                WHERE urunadi = ? 
                  AND (silinme = 0 OR silinme IS NULL)
            """
            
            params = [yeni_fiyat, yeni_fiyat, urun_adi]
            
            if baslangic_tarih:
                sql += " AND Tarih >= ?"
                params.append(baslangic_tarih)
            
            cursor.execute(sql, params)
            
            guncellenen_sayi = cursor.rowcount
            self.conn.commit()
            
            print(f"✓ Toplu fiyat güncellendi:")
            print(f"  Ürün: {urun_adi}")
            print(f"  Yeni Fiyat: {yeni_fiyat:.2f} TL")
            print(f"  Güncellenen Kayıt: {guncellenen_sayi}")
            return True
            
        except Exception as e:
            print(f"✗ Hata: {e}")
            self.conn.rollback()
            return False
    
    def urun_fiyat_guncelle(self, urun_adi: str, yeni_fiyat: float) -> bool:
        """
        TBL_URUN tablosunda ürün fiyatını güncelle
        
        Args:
            urun_adi: Ürün adı
            yeni_fiyat: Yeni fiyat
        
        Returns:
            bool: İşlem başarılı mı
        """
        try:
            cursor = self.conn.cursor()
            
            # Önce mevcut fiyatı al
            # Gerçek kolon isimleri: isim, fiyat1, birim1
            cursor.execute("""
                SELECT fiyat1, birim1
                FROM TBL_URUN
                WHERE isim = ?
            """, (urun_adi,))
            
            kayit = cursor.fetchone()
            if not kayit:
                print(f"✗ Ürün bulunamadı: {urun_adi}")
                return False
            
            eski_fiyat, birim = kayit
            
            # Fiyatı güncelle
            cursor.execute("""
                UPDATE TBL_URUN
                SET fiyat1 = ?
                WHERE isim = ?
            """, (yeni_fiyat, urun_adi))
            
            self.conn.commit()
            print(f"✓ TBL_URUN fiyat güncellendi:")
            print(f"  Ürün: {urun_adi}")
            print(f"  Eski Fiyat: {eski_fiyat:.2f} TL/{birim}")
            print(f"  Yeni Fiyat: {yeni_fiyat:.2f} TL/{birim}")
            return True
            
        except Exception as e:
            print(f"✗ Hata: {e}")
            self.conn.rollback()
            return False
    
    def urun_sil(self, urun_adi: str) -> bool:
        """
        TBL_URUN tablosundan ürünü sil
        
        Args:
            urun_adi: Silinecek ürünün adı
        
        Returns:
            bool: Başarılı ise True
        """
        try:
            cursor = self.conn.cursor()
            
            # Önce ürünün var olup olmadığını kontrol et
            cursor.execute("SELECT COUNT(*) FROM TBL_URUN WHERE isim = ?", (urun_adi,))
            if cursor.fetchone()[0] == 0:
                print(f"✗ Ürün bulunamadı: {urun_adi}")
                return False
            
            # Ürünü sil
            cursor.execute("DELETE FROM TBL_URUN WHERE isim = ?", (urun_adi,))
            self.conn.commit()
            
            print(f"✓ Ürün silindi: {urun_adi}")
            return True
            
        except Exception as e:
            print(f"✗ Ürün silme hatası: {e}")
            self.conn.rollback()
            return False
    
    def urun_toplu_sil(self, urun_adlari: list) -> dict:
        """
        Birden fazla ürünü toplu sil
        
        Args:
            urun_adlari: Silinecek ürün adları listesi
        
        Returns:
            dict: {'basarili': int, 'basarisiz': int, 'hatalar': list}
        """
        sonuc = {'basarili': 0, 'basarisiz': 0, 'hatalar': []}
        
        for urun_adi in urun_adlari:
            if self.urun_sil(urun_adi):
                sonuc['basarili'] += 1
            else:
                sonuc['basarisiz'] += 1
                sonuc['hatalar'].append(urun_adi)
        
        return sonuc

    def urun_listesi_getir(self) -> pd.DataFrame:
        """
        TBL_URUN tablosundan ürün listesini getir
        
        Returns:
            DataFrame: Ürün listesi (URUN_ADI, BIRIM_FIYAT, BIRIM)
        """
        sql = """
        SELECT 
            isim as URUN_ADI,
            fiyat1 as BIRIM_FIYAT,
            ISNULL(birim1, 'Adet') as BIRIM
        FROM TBL_URUN
        ORDER BY isim
        """
        return self.veri_cek(sql)
    
    # ==================== ARŞİV VE LOG ====================
    
    def adisyonlari_listele(self, baslangic_tarih: str = None, bitis_tarih: str = None, 
                           masa: str = None, adisyon_no: str = None, aktif_mi: bool = True) -> pd.DataFrame:
        """
        Adisyonları listele
        
        Args:
            baslangic_tarih: Başlangıç tarihi (YYYY-MM-DD)
            bitis_tarih: Bitiş tarihi (YYYY-MM-DD)
            masa: Masa filtresi
            adisyon_no: Adisyon no filtresi
            aktif_mi: True ise sadece aktif (silinmemiş), False ise silinmiş
        
        Returns:
            DataFrame: Adisyon listesi
        """
        sql = """
        SELECT 
            adisyonno,
            masa,
            MIN(Tarih) as Tarih,
            COUNT(*) as urun_sayisi,
            SUM(toplam) as toplam,
            MAX(ISNULL(silinme, 0)) as silinme,
            MAX(garson) as garson
        FROM TBL_ADISYON
        WHERE 1=1
        """
        
        params = []
        
        if aktif_mi:
            sql += " AND (silinme = 0 OR silinme IS NULL)"
        else:
            sql += " AND silinme = 1"
        
        if baslangic_tarih:
            sql += " AND CAST(Tarih AS DATE) >= ?"
            params.append(baslangic_tarih)
        
        if bitis_tarih:
            sql += " AND CAST(Tarih AS DATE) <= ?"
            params.append(bitis_tarih)
        
        if masa:
            sql += " AND masa = ?"
            params.append(masa)
        
        if adisyon_no:
            sql += " AND adisyonno LIKE ?"
            params.append(f"%{adisyon_no}%")
        
        sql += """
        GROUP BY adisyonno, masa
        ORDER BY MIN(Tarih) DESC
        """
        
        return pd.read_sql(sql, self.conn, params=params)
    
    def adisyon_detay_getir(self, adisyonno: str) -> pd.DataFrame:
        """
        Adisyon detaylarını getir
        
        Args:
            adisyonno: Adisyon numarası
        
        Returns:
            DataFrame: Adisyon ürünleri
        """
        sql = """
        SELECT 
            Anahtar,
            Tarih,
            adisyonno,
            masa,
            urunadi,
            miktari,
            birimfiyati,
            toplam,
            garson,
            silinme,
            silen,
            SILINME_ZAMAN
        FROM TBL_ADISYON
        WHERE adisyonno = ?
        ORDER BY Tarih
        """
        
        return pd.read_sql(sql, self.conn, params=[adisyonno])
    
    def masalari_listele(self) -> pd.DataFrame:
        """
        Aktif masaları listele
        
        Returns:
            DataFrame: Masa listesi
        """
        sql = """
        SELECT DISTINCT masa
        FROM TBL_ADISYON
        WHERE (silinme = 0 OR silinme IS NULL)
          AND CAST(Tarih AS DATE) = CAST(GETDATE() AS DATE)
        ORDER BY masa
        """
        
        return pd.read_sql(sql, self.conn)
    
    def garsonlari_listele(self) -> pd.DataFrame:
        """
        Aktif garsonları listele
        
        Returns:
            DataFrame: Garson listesi
        """
        sql = """
        SELECT DISTINCT garson
        FROM TBL_ADISYON
        WHERE garson IS NOT NULL 
          AND garson != ''
          AND (silinme = 0 OR silinme IS NULL)
        ORDER BY garson
        """
        
        return pd.read_sql(sql, self.conn)
    
    def arsiv_kayitlari_ara(self, adisyonno: str = None, baslangic_tarih: str = None) -> pd.DataFrame:
        """
        Arşiv tablosunda kayıt ara
        
        Args:
            adisyonno: Adisyon numarası
            baslangic_tarih: Başlangıç tarihi
        
        Returns:
            DataFrame: Arşiv kayıtları
        """
        sql = """
        SELECT 
            Anahtar, Tarih, adisyonno, masa, urunadi, 
            miktari, birimfiyati, toplam, garson
        FROM TBL_A_ADISYON
        WHERE 1=1
        """
        
        params = []
        if adisyonno:
            sql += " AND adisyonno = ?"
            params.append(adisyonno)
        if baslangic_tarih:
            sql += " AND Tarih >= ?"
            params.append(baslangic_tarih)
        
        sql += " ORDER BY Tarih DESC"
        
        return pd.read_sql(sql, self.conn, params=params)


# ==================== KULLANIM ÖRNEKLERİ ====================

def main():
    """Ana program"""
    
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║         KERZZ BOSS YÖNETİM PROGRAMI v1.0                     ║
    ║         Adisyon, Ürün ve Fiyat Yönetimi                      ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    
    # Veritabanı bağlantısı
    # Örnek 1: Windows Authentication
    # db = KerzzYonetim(server='ABC01CL099', database='TALAS')
    
    # Örnek 2: SQL Server Authentication
    db = KerzzYonetim(
        server='ABC01CL099', 
        database='TALAS',
        username='sa',
        password='your_password'  # Şifrenizi girin
    )
    
    if not db.baglan():
        return
    
    try:
        while True:
            print("\n" + "="*60)
            print("MENÜ:")
            print("="*60)
            print("1. Birleştirilen Adisyonları Listele")
            print("2. Birleştirmeyi Geri Al")
            print("3. İptal Edilen Ürünleri Listele")
            print("4. Ürün İptalini Geri Al")
            print("5. Adisyon Sil (Soft Delete)")
            print("6. Adisyon Fiziksel Sil (⚠️ Dikkat!)")
            print("7. Fiyat Güncelle (Tekil)")
            print("8. Toplu Fiyat Güncelle")
            print("9. Arşiv Kayıtlarını Ara")
            print("0. Çıkış")
            print("="*60)
            
            secim = input("\nSeçiminiz: ").strip()
            
            if secim == '1':
                print("\n--- Birleştirilen Adisyonlar ---")
                baslangic = input("Başlangıç tarihi (YYYY-MM-DD) [Enter=Tümü]: ").strip()
                bitis = input("Bitiş tarihi (YYYY-MM-DD) [Enter=Bugün]: ").strip()
                
                df = db.birlestirilen_adisyonlari_listele(
                    baslangic or None, 
                    bitis or None
                )
                print(f"\nToplam {len(df)} kayıt bulundu\n")
                print(df.to_string(index=False))
            
            elif secim == '2':
                kimlik = int(input("Birleştirme ID (Kimlik): "))
                db.birlestirmeyi_geri_al(kimlik)
            
            elif secim == '3':
                print("\n--- İptal Edilen Ürünler ---")
                baslangic = input("Başlangıç tarihi (YYYY-MM-DD) [Enter=Tümü]: ").strip()
                adisyonno = input("Adisyon No [Enter=Tümü]: ").strip()
                
                df = db.iptal_urunleri_listele(
                    baslangic or None,
                    None,
                    adisyonno or None
                )
                print(f"\nToplam {len(df)} iptal kayıt bulundu\n")
                print(df.to_string(index=False))
            
            elif secim == '4':
                anahtar = int(input("Ürün Anahtar ID: "))
                db.urun_iptalini_geri_al(anahtar)
            
            elif secim == '5':
                adisyonno = input("Adisyon No: ").strip()
                kullanici = input("Kullanıcı Adınız: ").strip()
                sebep = input("Silme Sebebi [Opsiyonel]: ").strip()
                db.adisyon_sil(adisyonno, kullanici, sebep or None)
            
            elif secim == '6':
                print("\n⚠️  DİKKAT: Bu işlem GERİ ALINAMAZ!")
                adisyonno = input("Adisyon No: ").strip()
                onay = input(f"'{adisyonno}' adisyonunu kalıcı silmek istiyor musunuz? (EVET/hayır): ")
                if onay.upper() == 'EVET':
                    db.adisyonu_fiziksel_sil(adisyonno)
                else:
                    print("İşlem iptal edildi")
            
            elif secim == '7':
                anahtar = int(input("Ürün Anahtar ID: "))
                yeni_fiyat = float(input("Yeni Birim Fiyat: "))
                db.fiyat_guncelle(anahtar, yeni_fiyat)
            
            elif secim == '8':
                urun_adi = input("Ürün Adı: ").strip()
                yeni_fiyat = float(input("Yeni Birim Fiyat: "))
                baslangic = input("Bu tarihten sonraki kayıtlar (YYYY-MM-DD) [Enter=Tümü]: ").strip()
                db.toplu_fiyat_guncelle(urun_adi, yeni_fiyat, baslangic or None)
            
            elif secim == '9':
                print("\n--- Arşiv Kayıtları ---")
                adisyonno = input("Adisyon No [Enter=Tümü]: ").strip()
                baslangic = input("Başlangıç tarihi (YYYY-MM-DD) [Enter=Tümü]: ").strip()
                
                df = db.arsiv_kayitlari_ara(
                    adisyonno or None,
                    baslangic or None
                )
                print(f"\nToplam {len(df)} arşiv kayıt bulundu\n")
                print(df.to_string(index=False))
            
            elif secim == '0':
                print("\nProgram sonlandırılıyor...")
                break
            
            else:
                print("✗ Geçersiz seçim!")
    
    except KeyboardInterrupt:
        print("\n\nProgram kullanıcı tarafından durduruldu")
    except Exception as e:
        print(f"\n✗ Beklenmeyen hata: {e}")
    finally:
        db.kapat()


if __name__ == "__main__":
    main()
