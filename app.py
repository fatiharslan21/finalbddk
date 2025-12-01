import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import plotly.express as px
import time
import sys

# --- SAYFA VE RENK AYARLARI ---
st.set_page_config(page_title="Finansal Analiz", layout="wide", page_icon="🏦")

st.markdown("""
<style>
    .stApp { background-color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #FCB131; }
    [data-testid="stSidebar"] * { color: #000000 !important; font-weight: bold; }
    h1, h2, h3 { color: #d99000 !important; }
    div.stButton > button { background-color: #FCB131; color: black; border: 2px solid black; width: 100%; }
    div.stButton > button:hover { background-color: #e5a02d; color: white; border-color: black; }
</style>
""", unsafe_allow_html=True)

# --- SABİTLER ---
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
    "📊 Sermaye Yeterliliği Rasyosu": {"tab": "#tabloListesiItem-7", "row_text": "Sermaye Yeterliliği Standart Rasyosu",
                                      "col_attr": "grdRapor_Toplam"},
    "🏦 Toplam Krediler": {"tab": "tabloListesiItem-3", "row_text": "Toplam Krediler", "col_id": "grdRapor_Toplam"},
    "🏠 Tüketici Kredileri": {"tab": "tabloListesiItem-4", "row_text": "Tüketici Kredileri",
                             "col_id": "grdRapor_Toplam"},
    "💳 Bireysel Kredi Kartları": {"tab": "tabloListesiItem-4", "row_text": "Bireysel Kredi Kartları",
                                  "col_id": "grdRapor_Toplam"},
    "🏭 KOBİ Kredileri": {"tab": "tabloListesiItem-6", "row_text": "Toplam KOBİ Kredileri",
                         "col_id": "grdRapor_NakdiKrediToplam"}
}


# --- DRIVER AYARLARI ---
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    if sys.platform == "linux":
        # Streamlit Cloud Yolları
        chrome_options.binary_location = "/usr/bin/chromium"
        service = Service("/usr/bin/chromedriver")
    else:
        # Local Windows Yolu (Otomatik)
        service = Service()

    return webdriver.Chrome(service=service, options=chrome_options)


# --- SCRAPING FONKSİYONU ---
def scrape_bddk(bas_yil, bas_ay, bit_yil, bit_ay, secilen_taraflar, secilen_veriler, status_container):
    driver = None
    data = []

    try:
        driver = get_driver()
        driver.get("https://www.bddk.org.tr/bultenaylik")

        # Sayfanın yüklenmesini bekle
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "ddlYil")))

        bas_idx = AY_LISTESI.index(bas_ay)
        bit_idx = AY_LISTESI.index(bit_ay)

        # İlerleme Çubuğu İçin Toplam Adım
        total_steps = (bit_yil - bas_yil) * 12 + (bit_idx - bas_idx) + 1
        current_step = 0
        progress_bar = st.progress(0)

        # YIL DÖNGÜSÜ
        for yil in range(bas_yil, bit_yil + 1):
            start_m = bas_idx if yil == bas_yil else 0
            end_m = bit_idx if yil == bit_yil else 11

            # AY DÖNGÜSÜ
            for ay_i in range(start_m, end_m + 1):
                ay_str = AY_LISTESI[ay_i]
                donem = f"{ay_str} {yil}"

                status_container.info(f"⏳ Veri Çekiliyor: **{donem}**")

                # JavaScript ile Hızlı Tarih Değişimi
                driver.execute_script(f"""
                    $('#ddlYil').val('{yil}').trigger('chosen:updated').trigger('change');
                    $('#ddlAy').val('{ay_str}').trigger('chosen:updated').trigger('change');
                """)
                time.sleep(1.5)  # Tablonun güncellenmesi için bekle

                # TARAF DÖNGÜSÜ
                for taraf in secilen_taraflar:
                    # JavaScript ile Taraf Seçimi
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
                    time.sleep(1.0)  # Taraf değişimini bekle

                    # VERİ KALEMİ DÖNGÜSÜ
                    for veri in secilen_veriler:
                        conf = VERI_KONFIGURASYONU[veri]
                        try:
                            # Sekmeye Tıkla
                            driver.execute_script(f"document.getElementById('{conf['tab']}').click();")
                            time.sleep(0.3)

                            # XPath ile satır ve sütun bul
                            xpath = f"//tr[contains(., '{conf['row_text']}')]//td[contains(@aria-describedby, '{conf['col_id']}')]"
                            element = driver.find_element(By.XPATH, xpath)
                            val_text = element.text

                            # Sayıyı temizle (1.250,00 -> 1250.0)
                            val_float = float(val_text.replace('.', '').replace(',', '.')) if val_text else 0.0

                            data.append({
                                "Dönem": donem,
                                "Taraf": taraf,
                                "Kalem": veri,
                                "Değer": val_float
                            })
                        except:
                            pass  # Veri yoksa veya hata varsa atla

                current_step += 1
                progress_bar.progress(current_step / max(1, total_steps))

    except Exception as e:
        st.error(f"HATA: {e}")
    finally:
        if driver: driver.quit()

    return pd.DataFrame(data)


# --- YAN MENÜ ---
with st.sidebar:
    st.title("🎛️ KONTROL PANELİ")
    st.markdown("---")

    # 1. BAŞLANGIÇ
    st.subheader("🗓️ Başlangıç Tarihi")
    c1, c2 = st.columns(2)
    bas_yil = c1.number_input("Yıl (Baş)", 2020, 2030, 2024)
    bas_ay = c2.selectbox("Ay (Baş)", AY_LISTESI, index=0)

    # 2. BİTİŞ (BURASI EKLENDİ)
    st.subheader("🏁 Bitiş Tarihi")
    c3, c4 = st.columns(2)
    bit_yil = c3.number_input("Yıl (Bit)", 2020, 2030, 2024)
    bit_ay = c4.selectbox("Ay (Bit)", AY_LISTESI, index=0)

    st.markdown("---")

    # SEÇİMLER
    secilen_taraflar = st.multiselect("Karşılaştır:", TARAF_SECENEKLERI, default=["Sektör", "Mevduat-Kamu"])
    secilen_veriler = st.multiselect("Veri Kalemleri:", list(VERI_KONFIGURASYONU.keys()), default=["📌 TOPLAM AKTİFLER"])

    st.markdown("---")
    btn_baslat = st.button("🚀 ANALİZİ BAŞLAT")

# --- ANA EKRAN ---
st.title("🏦 BDDK Gelişmiş Analiz Paneli")

if btn_baslat:
    if not secilen_taraflar or not secilen_veriler:
        st.error("Lütfen Taraf ve Veri seçimi yapınız!")
    else:
        durum_kutusu = st.empty()
        df_sonuc = scrape_bddk(bas_yil, bas_ay, bit_yil, bit_ay, secilen_taraflar, secilen_veriler, durum_kutusu)

        if not df_sonuc.empty:
            durum_kutusu.success("✅ Veriler Başarıyla Çekildi!")

            # TABS
            tab1, tab2, tab3 = st.tabs(["📊 GRAFİK ANALİZ", "📋 TABLO", "📥 İNDİR"])

            with tab1:
                # Dinamik Grafik
                kalem_sec = st.selectbox("Grafikte Göster:", secilen_veriler)
                df_chart = df_sonuc[df_sonuc["Kalem"] == kalem_sec]

                fig = px.line(df_chart, x="Dönem", y="Değer", color="Taraf", markers=True,
                              title=f"{kalem_sec} Trend Analizi",
                              color_discrete_sequence=["#FCB131", "#000000", "#FF5733"])
                st.plotly_chart(fig, use_container_width=True)

            with tab2:
                # Pivot Tablo
                pivot = df_sonuc.pivot_table(index="Dönem", columns=["Kalem", "Taraf"], values="Değer", aggfunc="sum")
                st.dataframe(pivot, use_container_width=True)

            with tab3:
                # Excel İndir
                excel_file = "BDDK_Analiz_Rapor.xlsx"
                with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:
                    df_sonuc.to_excel(writer, sheet_name="Ham Veri", index=False)
                    for k in secilen_veriler:
                        sheet_ismi = k.replace("📌", "").replace("⚠️", "")[:30].strip()
                        df_sonuc[df_sonuc["Kalem"] == k].pivot(index="Dönem", columns="Taraf", values="Değer").to_excel(
                            writer, sheet_name=sheet_ismi)

                with open(excel_file, "rb") as f:
                    st.download_button("📥 Excel Olarak İndir", f, file_name="BDDK_Analiz.xlsx")
        else:
            durum_kutusu.warning("Veri çekilemedi. Bağlantıyı kontrol edip tekrar deneyin.")