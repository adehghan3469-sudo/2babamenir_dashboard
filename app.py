import streamlit as st
import plotly.graph_objects as go
import requests
from datetime import datetime

# -------------------------------------------------
# تنظیمات صفحه
# -------------------------------------------------
st.set_page_config(
    page_title="دفتر فنی بابامنیر | گزارش کشاورزی و خدمات فنی",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------
# استایل سفارشی
# -------------------------------------------------
st.markdown("""
<style>
    [data-testid="stSidebar"] {
        background-color: #1a3c34;
    }
    [data-testid="stSidebar"] * {
        color: #ffffff !important;
    }
    .main-title {
        font-size: 1.7rem;
        font-weight: 700;
        color: #1a3c34;
        margin-bottom: 0.3rem;
    }
    .banner-box {
        background: linear-gradient(135deg, #1a3c34, #2e5c4e);
        color: white;
        padding: 14px 18px;
        border-radius: 12px;
        margin-bottom: 12px;
        text-align: center;
        font-size: 1.05rem;
        font-weight: 500;
        min-height: 70px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .service-card {
        background: #f8f9fa;
        border-right: 4px solid #1a3c34;
        padding: 12px 16px;
        border-radius: 10px;
        margin-bottom: 10px;
    }
    .mobile-card {
        border-right: 4px solid #2980b9;
        background: #f0f7ff;
    }
    .home-card {
        border-right: 4px solid #e67e22;
        background: #fff8f0;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# داده هواشناسی
# -------------------------------------------------
LOCATIONS = {
    "بابامنیر": {"lat": 30.07, "lon": 51.21, "name": "بابامنیر"},
}

@st.cache_data(ttl=1800)
def get_weather_data(lat, lon):
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,wind_direction_10m,surface_pressure"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,et0_fao_evapotranspiration"
            f"&timezone=Asia%2FTehran&forecast_days=7"
        )
        r = requests.get(url, timeout=10)
        return r.json()
    except:
        return None

def weather_code_to_text(code):
    codes = {
        0: "صاف و آفتابی", 1: "عمدتاً صاف", 2: "نیمه ابری", 3: "ابری",
        45: "مه‌آلود", 51: "باران ریز", 61: "بارانی", 80: "رگبار", 95: "رعد و برق"
    }
    return codes.get(code, "نامشخص")

def wind_dir_to_text(degree):
    dirs = ["شمال", "شمال‌شرقی", "شرق", "جنوب‌شرقی", "جنوب", "جنوب‌غربی", "غرب", "شمال‌غربی"]
    return dirs[round(degree / 45) % 8]

# -------------------------------------------------
# بنر چرخشی خدمات (شبیه ترب)
# -------------------------------------------------
BANNERS = [
    "📱 تعمیر تخصصی گوشی‌های چینی، سامسونگ و موتورولا — تعویض ال‌سی‌دی و باتری",
    "🔧 تعمیرات لوازم خانگی در محل: تلویزیون، آبگرمکن، یخچال، کابینت و جوشکاری",
    "🌾 مشاوره کشاورزی و توصیه‌های فنی روز — دفتر فنی بابامنیر",
    "🛠️ خدمات پیک‌نیک پر کنی و تعمیرات سیار در محل شما",
    "📞 ثبت سوال و درخواست آنلاین — پاسخ از طریق ایمیل و تماس",
]

def show_rotating_banner():
    if "banner_idx" not in st.session_state:
        st.session_state.banner_idx = 0

    # نمایش بنر فعلی
    current = BANNERS[st.session_state.banner_idx % len(BANNERS)]
    st.markdown(f'<div class="banner-box">{current}</div>', unsafe_allow_html=True)

    # دکمه‌های کنترل
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("◀ قبلی"):
            st.session_state.banner_idx = (st.session_state.banner_idx - 1) % len(BANNERS)
            st.rerun()
    with col3:
        if st.button("بعدی ▶"):
            st.session_state.banner_idx = (st.session_state.banner_idx + 1) % len(BANNERS)
            st.rerun()

# -------------------------------------------------
# صفحات
# -------------------------------------------------
def page_summary(data, location_name):
    st.markdown(f'<div class="main-title">گزارش روزانه کشاورزی {location_name}</div>', unsafe_allow_html=True)

    # بنر چرخشی
    show_rotating_banner()

    if not data:
        st.warning("داده هواشناسی در دسترس نیست.")
        return

    current = data.get("current", {})
    daily = data.get("daily", {})

    temp = current.get("temperature_2m", "–")
    humidity = current.get("relative_humidity_2m", "–")
    wind_speed = current.get("wind_speed_10m", "–")
    wind_dir = wind_dir_to_text(current.get("wind_direction_10m", 0))
    pressure = current.get("surface_pressure", "–")
    condition = weather_code_to_text(current.get("weather_code", 0))
    et0 = daily.get("et0_fao_evapotranspiration", [None])[0]
    rain_prob = daily.get("precipitation_probability_max", [0])[0]
    max_temps = daily.get("temperature_2m_max", [])
    min_temps = daily.get("temperature_2m_min", [])

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("ET₀", f"{et0:.1f} mm" if et0 else "–")
    c2.metric("احتمال بارش", f"{rain_prob}%")
    c3.metric("رطوبت", f"{humidity}%")
    c4.metric("حداقل / حداکثر", f"{min_temps[0]:.0f} / {max_temps[0]:.0f}°C" if max_temps else "–")
    c5.metric("دمای فعلی", f"{temp}°C")

    st.info(f"وضعیت فعلی: {condition} | باد: {wind_speed} km/h از {wind_dir} | فشار: {pressure} hPa")

    st.subheader("📈 پیش‌بینی دمای ۷ روز آینده")
    days = [f"روز {i+1}" for i in range(len(max_temps))]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=days, y=max_temps, mode="lines+markers", name="حداکثر", line=dict(color="red")))
    fig.add_trace(go.Scatter(x=days, y=min_temps, mode="lines+markers", name="حداقل", line=dict(color="blue")))
    fig.update_layout(height=340, margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(fig, use_container_width=True)


def page_mobile():
    st.header("📱 خدمات موبایل")
    st.caption("کلیه کارهای فنی و تعمیراتی توسط تعمیرکار مجرب انجام می‌شود.")

    show_rotating_banner()

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🔧 تعمیرات تخصصی")
        st.markdown("""
        <div class="service-card mobile-card">
        <b>انواع گوشی‌های تحت پوشش:</b><br>
        • گوشی‌های چینی (شیائومی، ریلمی، آنر، هواوی، پوکو و ...)<br>
        • سامسونگ (تمام سری‌ها)<br>
        • موتورولا<br><br>
        <b>خدمات قابل ارائه:</b><br>
        • تعویض ال‌سی‌دی و تاچ<br>
        • تعویض باتری اصل و فیک<br>
        • تعمیرات برد و ریزکاری<br>
        • حل مشکلات نرم‌افزاری و آنلاک<br>
        • تعویض درب پشت، قاب و قطعات جانبی<br>
        • گارانتی خدمات انجام‌شده
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("### 💰 خرید و فروش")
        st.markdown("""
        <div class="service-card mobile-card">
        • خرید گوشی کارکرده با قیمت منصفانه<br>
        • فروش گوشی‌های سالم و تست‌شده<br>
        • معاوضه گوشی<br>
        • مشاوره قبل از خرید<br>
        • کارشناسی گوشی در محل
        </div>
        """, unsafe_allow_html=True)

    st.success("برای ثبت درخواست تعمیر یا خرید و فروش با شماره ۰۹۱۷۴۸۰۸۷۵۵ تماس بگیرید یا در ایتا پیام دهید.")


def page_home_appliances():
    st.header("🛠️ تعمیرات لوازم خانگی و خدمات در محل")
    st.caption("خدمات فنی در محل شما انجام می‌شود.")

    show_rotating_banner()

    st.markdown("---")

    st.markdown("""
    <div class="service-card home-card">
    <b>خدمات قابل ارائه:</b><br>
    • تنظیمات و تعمیر تلویزیون<br>
    • تعمیر و سرویس آبگرمکن<br>
    • تعمیر یخچال و فریزر<br>
    • نصب و تعمیر کابینت<br>
    • جوشکاری سیار<br>
    • پیک‌نیک پر کنی در محل<br>
    • سایر خدمات فنی ساختمانی و خانگی
    </div>
    """, unsafe_allow_html=True)

    st.info("برای هماهنگی و اعزام تعمیرکار با شماره ۰۹۱۷۴۸۰۸۷۵۵ تماس بگیرید.")


def page_questions():
    st.header("📝 ثبت سوال و درخواست")
    st.write("سوالات خود را در زمینه کشاورزی، خدمات آنلاین، نرم‌افزار گوشی یا سایر موضوعات بنویسید. پاسخ از طریق ایمیل یا تماس به شما اعلام می‌شود.")

    with st.form("question_form"):
        name = st.text_input("نام و نام خانوادگی")
        contact = st.text_input("شماره تماس یا ایمیل")
        category = st.selectbox("موضوع سوال", [
            "مشکلات کشاورزی و باغداری",
            "خدمات آنلاین و اداری",
            "مشکلات نرم‌افزاری گوشی",
            "درخواست تعمیر موبایل",
            "درخواست تعمیر لوازم خانگی",
            "سایر موضوعات"
        ])
        question = st.text_area("متن سوال یا درخواست", height=150)
        submitted = st.form_submit_button("ارسال سوال")

        if submitted:
            if name and contact and question:
                st.success("سوال شما با موفقیت ثبت شد. در اسرع وقت پاسخ داده خواهد شد.")
                st.info("پاسخ از طریق ایمیل یا شماره تماسی که وارد کرده‌اید ارسال می‌شود.")
            else:
                st.warning("لطفاً تمام فیلدهای ضروری را پر کنید.")


def page_placeholder(title):
    st.header(title)
    st.info("این بخش به زودی تکمیل می‌شود.")
    show_rotating_banner()


# -------------------------------------------------
# سایدبار
# -------------------------------------------------
with st.sidebar:
    st.markdown("## 🌾 دفتر فنی بابامنیر")
    st.caption("زیر نظر مهندس افشین دهقان")
    st.markdown("---")

    location = st.selectbox("انتخاب منطقه", list(LOCATIONS.keys()))

    st.markdown("---")
    menu = st.radio(
        "بخش‌های داشبورد",
        [
            "خلاصه روز",
            "خدمات موبایل",
            "تعمیرات لوازم خانگی",
            "ثبت سوال و درخواست",
            "هواشناسی زنده",
            "قیمت نهاده‌ها",
            "توصیه‌های فنی",
            "اخبار و منابع"
        ]
    )

    st.markdown("---")
    st.caption("تماس: ۰۹۱۷۴۸۰۸۷۵۵")
    st.caption("ایتا و روبیکا: a.d3469@")

# -------------------------------------------------
# اجرای صفحات
# -------------------------------------------------
loc = LOCATIONS[location]
data = get_weather_data(loc["lat"], loc["lon"])

if menu == "خلاصه روز":
    page_summary(data, loc["name"])
elif menu == "خدمات موبایل":
    page_mobile()
elif menu == "تعمیرات لوازم خانگی":
    page_home_appliances()
elif menu == "ثبت سوال و درخواست":
    page_questions()
elif menu == "هواشناسی زنده":
    page_placeholder("🌤️ هواشناسی زنده")
elif menu == "قیمت نهاده‌ها":
    page_placeholder("💰 قیمت نهاده‌ها")
elif menu == "توصیه‌های فنی":
    page_placeholder("🛠️ توصیه‌های فنی")
elif menu == "اخبار و منابع":
    page_placeholder("📰 اخبار و منابع")
