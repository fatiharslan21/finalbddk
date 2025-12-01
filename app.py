import streamlit as st
import pandas as pd
from selenium import webdriver
# --- GEREKLİ KÜTÜPHANELER ---
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager  # YENİ EKLENDİ
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import plotly.express as px
import time
import sys
import os

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="BDDK Analiz", layout="wide", page_icon="🏦")

# --- STİL ---
st.markdown("""
<style>
    .stApp { background-color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #FCB131; }
    [data-testid="stSidebar"] * { color: #000000 !important; font-weight: bold; }
    div.stButton > button { background-color: #FCB131; color: black; border: 2px solid black; width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- CONFIG ---
AY_LISTESI = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım",
              "Aralık"]
TARAF_SECENEKLERI = ["Sektör", "Mevduat-Kamu", "Mevduat-Yerli Özel", "Mevduat-Yabancı", "Katılım"]
VERI_KONFIGURASYONU = {
    "📌 TOPLAM AKTİFLER": {"tab": "tabloListesiItem-1", "row_text": "TOPLAM AKTİFLER", "col_id": "grdRapor_Toplam"},
    "📌 TOPLAM ÖZKAYNAKLAR": {"tab": "tabloListesiItem-1", "row_text": "TOPLAM ÖZKAYNAKLAR",
                             "col_id": "grdRapor_Toplam"},
    "⚠️ Takipteki Alacaklar": {"tab": "tabloListesiItem-1", "row_text": "Takipteki Alacaklar",
                               "col_id": "grdRapor_Toplam"},
    "💰 DÖNEM NET KARI": {"tab": "tabloListesiItem-2", "row_text": "DÖNEM NET KARI (ZARARI)",
                         "col_id": "grdRapor_Toplam"},
    "🏦 Toplam Krediler": {"tab": "tabloListesiItem-3", "row_text": "Toplam Krediler", "col_id": "grdRapor_Toplam"},
    "🏠 Tüketici Kredileri": {"tab": "tabloListesiItem-4", "row_text": "Tüketici Kredileri",
                             "col_id": "grdRapor_Toplam"},
    "💳 Bireysel Kredi Kartları": {"tab": "tabloListesiItem-4", "row_text": "Bireysel Kredi Kartları",
                                  "col_id": "grdRapor_Toplam"},
    "🏭 KOBİ Kredileri": {"tab": "tabloListesiItem-6", "row_text": "Toplam KOBİ Kredileri",
                         "col_id": "grdRapor_NakdiKrediToplam"}
}


def get_driver():
    """
    HİBRİT DRIVER:
    - Linux (Cloud): Firefox kullanır (Driver'ı Python indirir).
    - Windows (Sen): Chrome kullanır.
    """

    # DURUM 1: STREAMLIT CLOUD (LINUX) - FIREFOX
    if sys.platform == "linux":
        options = FirefoxOptions()
        options.add_argument("--headless")
        # Firefox'un sistemdeki yerini gösteriyoruz
        options.binary_location = "/usr/bin/firefox"

        # Sürücüyü (GeckoDriver) Python otomatik indirsin
        # Cache hatasını önlemek için try-except
        try:
            service = FirefoxService(GeckoDriverManager().install())
        except:
            # Yedek yöntem: Mevcutsa sistemdekini kullan (ama genelde yukarıdaki çalışır)
            service = FirefoxService("/usr/local/bin/geckodriver")

        return webdriver.Firefox(service=service, options=options)

    # DURUM 2: SENİN BİLGİSAYARIN (WINDOWS) - CHROME
    else:
        options = ChromeOptions()
        options.add_argument("--start-maximized")
        service = ChromeService(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)


def scrape_bddk(bas_yil, bas_ay, bit_yil, bit_ay, secilen_taraflar, secilen_veriler, status_container):
    driver = None
    data = []

    try:
        driver = get_driver()
        driver.get("https://www.bddk.org.tr/bultenaylik")

        WebDriverWait(driver, 25).until(EC.presence_of_element_located((By.ID, "ddlYil")))

        bas_idx = AY_LISTESI.index(bas_ay)
        bit_idx = AY_LISTESI.index(bit_ay)
        total_steps = (bit_yil - bas_yil) * 12 + (bit_idx - bas_idx) + 1
        current_step = 0
        progress_bar = st.progress(0)

        for yil in range(bas_yil, bit_yil + 1):
            start_m = bas_idx if yil == bas_yil else 0
            end_m = bit_idx if yil == bit_yil else 11

            for ay_i in range(start_m, end_m + 1):
                ay_str = AY_LISTESI[ay_i]
                donem = f"{ay_str} {yil}"

                status_container.info(f"⏳ Veri Çekiliyor: **{donem}**")

                # JS Seçimi
                driver.execute_script(f"""
                    $('#ddlYil').val('{yil}').trigger('chosen:updated').trigger('change');
                    $('#ddlAy').val('{ay_str}').trigger('chosen:updated').trigger('change');
                """)
                time.sleep(2.5)  # Bekleme süresi

                for taraf in secilen_taraflar:
                    driver.execute_script(f"""
                        var t = document.getElementById('ddlTaraf');
                        for(var i=0; i<t.options.length; i++){{
                            if(t.options[i].text.trim() == '{taraf}'){{
                                t.selectedIndex = i;
                                break;
                            }}
                        }}
                        $(t).trigger('chosen:updated').trigger('change');
                    """)
                    time.sleep(1.2)

                    for veri in secilen_veriler:
                        conf = VERI_KONFIGURASYONU[veri]
                        try:
                            driver.execute_script(f"document.getElementById('{conf['tab']}').click();")
                            time.sleep(0.5)
                            xpath = f"//tr[contains(., '{conf['row_text']}')]//td[contains(@aria-describedby, '{conf['col_id']}')]"
                            element = driver.find_element(By.XPATH, xpath)
                            val = float(element.text.replace('.', '').replace(',', '.')) if element.text else 0.0
                            data.append({"Dönem": donem, "Taraf": taraf, "Kalem": veri, "Değer": val})
                        except:
                            pass

                current_step += 1
                progress_bar.progress(current_step / max(1, total_steps))

    except Exception as e:
        st.error(f"HATA OLUŞTU: {e}")
    finally:
        if driver: driver.quit()

    return pd.DataFrame(data)


# --- ARAYÜZ ---
with st.sidebar:
    st.title("🎛️ PANEL")
    st.markdown("---")
    c1, c2 = st.columns(2)
    bas_yil = c1.number_input("Başlangıç Yılı", 2024, 2030, 2024)
    bas_ay = c2.selectbox("Başlangıç Ayı", AY_LISTESI, index=0)
    c3, c4 = st.columns(2)
    bit_yil = c3.number_input("Bitiş Yılı", 2024, 2030, 2024)
    bit_ay = c4.selectbox("Bitiş Ayı", AY_LISTESI, index=0)
    st.markdown("---")
    secilen_taraflar = st.multiselect("Taraf", TARAF_SECENEKLERI, default=["Sektör"])
    secilen_veriler = st.multiselect("Veri", list(VERI_KONFIGURASYONU.keys()), default=["📌 TOPLAM AKTİFLER"])
    st.markdown("---")
    btn = st.button("🚀 BAŞLAT")

st.title("🏦 BDDK Analiz")

if btn:
    if not secilen_taraflar or not secilen_veriler:
        st.error("Eksik seçim.")
    else:
        status = st.empty()
        df = scrape_bddk(bas_yil, bas_ay, bit_yil, bit_ay, secilen_taraflar, secilen_veriler, status)

        if not df.empty:
            status.success("İşlem Tamam!")
            tab1, tab2 = st.tabs(["📊 Grafik", "📥 İndir"])
            with tab1:
                kalem = st.selectbox("Grafik:", secilen_veriler)
                df_c = df[df["Kalem"] == kalem]
                st.plotly_chart(px.line(df_c, x="Dönem", y="Değer", color="Taraf", markers=True),
                                use_container_width=True)
            with tab2:
                excel_file = "BDDK_Final.xlsx"
                with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:
                    df.to_excel(writer, sheet_name="Data", index=False)
                with open(excel_file, "rb") as f:
                    st.download_button("Excel İndir", f, file_name="BDDK.xlsx")