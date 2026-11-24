"""
داشبورد تعاملی گزارش روزانه کشاورزی بابامنیر
با اتصال زنده به Open-Meteo (رایگان و بدون نیاز به API Key)

اجرا محلی:
    streamlit run babamenir_dashboard.py

برای اشتراک‌گذاری در گروه واتساپ باید روی Streamlit Cloud یا Hugging Face مستقر شود.

نیازمندی‌ها (requirements.txt):
    streamlit
    pandas
    plotly
    requests
    jdatetime
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
from typing import Optional, Dict, Any, List

# تلاش برای ایمپورت jdatetime (تاریخ شمسی)
try:
    import jdatetime
    HAS_JDATETIME = True
except ImportError:
    HAS_JDATETIME = False

# -----------------------------
# تنظیمات صفحه و استایل RTL
# -----------------------------
st.set_page_config(
    page_title="گزارش روزانه کشاورزی بابامنیر",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS برای پشتیبانی کامل از راست‌چین و ظاهر حرفه‌ای
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Vazirmatn', Tahoma, sans-serif !important;
        direction: rtl;
        text-align: right;
    }
    
    .stMetric {
        direction: rtl;
        text-align: center;
    }
    
    .stMetric label {
        direction: rtl;
        text-align: center;
        display: block;
    }
    
    div[data-testid="stMetricValue"] {
        direction: ltr;
        text-align: center;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        border-radius: 12px;
        padding: 1rem;
        border: 1px solid #dee2e6;
        text-align: center;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    }
    
    .warning-box {
        background-color: #fff3cd;
        border-right: 5px solid #ffc107;
        padding: 0.8rem 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    
    .info-box {
        background-color: #e7f3ff;
        border-right: 5px solid #0d6efd;
        padding: 0.8rem 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    
    .success-box {
        background-color: #d1e7dd;
        border-right: 5px solid #198754;
        padding: 0.8rem 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    
    h1, h2, h3 {
        font-family: 'Vazirmatn', Tahoma, sans-serif !important;
    }
    
    .stDataFrame {
        direction: rtl;
    }
    
    /* بهبود ظاهر سایدبار */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a3c34 0%, #2d5a4c 100%);
    }
    
    section[data-testid="stSidebar"] * {
        color: #f8f9fa !important;
    }
    
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stRadio label {
        color: #e9ecef !important;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------
# مختصات جغرافیایی مناطق
# -----------------------------
LOCATIONS = {
    "بابامنیر": {"lat": 30.07, "lon": 51.52, "name": "بابامنیر", "elev": 950},
    "نورآباد ممسنی": {"lat": 30.11, "lon": 51.52, "name": "نورآباد ممسنی", "elev": 920},
    "ماهور میلاتی": {"lat": 29.95, "lon": 51.45, "name": "ماهور میلاتی", "elev": 1100}
}

# -----------------------------
# توابع کمکی
# -----------------------------
def weather_code_to_text(code: int) -> str:
    """تبدیل کد وضعیت هوا به متن فارسی"""
    mapping = {
        0: "صاف و آفتابی",
        1: "عمدتاً صاف",
        2: "نیمه‌ابری",
        3: "ابری",
        45: "مه",
        48: "مه یخ‌زده",
        51: "باران ریز",
        53: "باران ریز متوسط",
        55: "باران ریز شدید",
        61: "باران سبک",
        63: "باران متوسط",
        65: "باران شدید",
        71: "برف سبک",
        73: "برف متوسط",
        75: "برف شدید",
        80: "رگبار سبک",
        81: "رگبار متوسط",
        82: "رگبار شدید",
        95: "رعد و برق",
        96: "رعد و برق همراه تگرگ سبک",
        99: "رعد و برق همراه تگرگ شدید"
    }
    return mapping.get(code, "نامشخص")


def wind_direction_to_text(degrees: float) -> str:
    """تبدیل درجه باد به جهت فارسی"""
    if degrees is None:
        return "نامشخص"
    directions = [
        "شمال", "شمال‌شرقی", "شرق", "جنوب‌شرقی",
        "جنوب", "جنوب‌غربی", "غرب", "شمال‌غربی"
    ]
    idx = int((degrees + 22.5) % 360 // 45)
    return directions[idx]


def get_shamsi_date() -> str:
    """تاریخ و روز شمسی"""
    if HAS_JDATETIME:
        now = jdatetime.datetime.now()
        # jdatetime.weekday(): 0=شنبه ... 6=جمعه
        days = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه"]
        months = now.j_months_fa
        return f"{days[now.weekday()]} {now.day} {months[now.month-1]} {now.year}"
    return datetime.now().strftime("%Y-%m-%d")


def get_update_time() -> str:
    """زمان آخرین به‌روزرسانی به وقت تهران"""
    if HAS_JDATETIME:
        now = jdatetime.datetime.now()
        return now.strftime("%H:%M")
    return datetime.now().strftime("%H:%M")


@st.cache_data(ttl=1800, show_spinner="در حال دریافت داده هواشناسی...")
def get_weather(lat: float, lon: float, name: str) -> Optional[Dict[str, Any]]:
    """دریافت داده زنده هواشناسی از Open-Meteo با پارامترهای کشاورزی"""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": [
            "temperature_2m", "relative_humidity_2m", "weather_code",
            "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m",
            "surface_pressure", "apparent_temperature"
        ],
        "hourly": [
            "temperature_2m", "precipitation_probability", "precipitation",
            "weather_code", "wind_speed_10m", "soil_temperature_0cm",
            "et0_fao_evapotranspiration"
        ],
        "daily": [
            "temperature_2m_max", "temperature_2m_min",
            "precipitation_probability_max", "precipitation_sum",
            "weather_code", "wind_speed_10m_max",
            "et0_fao_evapotranspiration", "uv_index_max",
            "sunrise", "sunset"
        ],
        "timezone": "Asia/Tehran",
        "forecast_days": 7
    }
    try:
        r = requests.get(url, params=params, timeout=12)
        r.raise_for_status()
        data = r.json()
        data["_fetched_at"] = datetime.now().isoformat()
        return data
    except Exception as e:
        st.error(f"خطا در دریافت داده هواشناسی {name}: {e}")
        return None


def generate_recommendations(weather: Dict[str, Any], location: str) -> List[str]:
    """تولید توصیه‌های فنی پویا بر اساس شرایط فعلی هوا"""
    if not weather:
        return ["داده هواشناسی در دسترس نیست. لطفاً بعداً تلاش کنید."]
    
    current = weather.get("current", {})
    daily = weather.get("daily", {})
    
    temp = current.get("temperature_2m", 20)
    humidity = current.get("relative_humidity_2m", 50)
    wind = current.get("wind_speed_10m", 0)
    precip_prob = daily.get("precipitation_probability_max", [0])[0] if daily else 0
    precip_sum = daily.get("precipitation_sum", [0])[0] if daily else 0
    et0 = daily.get("et0_fao_evapotranspiration", [0])[0] if daily else 0
    code = current.get("weather_code", 0)
    
    recs = []
    
    # توصیه کشت و بذر
    if temp >= 8 and temp <= 22 and precip_prob < 60:
        recs.append(
            f"**کشت غلات:** شرایط دمایی ({temp:.0f}°C) برای ادامه کشت گندم و جو دیم مناسب است. "
            "از بذر گواهی‌شده و ضدعفونی‌شده استفاده کنید."
        )
    elif temp < 5:
        recs.append(
            "**هشدار سرما:** دمای پایین است. از کاشت جدید خودداری کنید و مزارع جوان را در برابر یخبندان احتمالی محافظت کنید."
        )
    else:
        recs.append(
            f"**کشت:** دمای فعلی {temp:.0f}°C است. زمان‌بندی کاشت را با توجه به پیش‌بینی ۷ روزه تنظیم کنید."
        )
    
    # توصیه آبیاری و تبخیر
    if et0 > 4:
        recs.append(
            f"**آبیاری:** تبخیر-تعرق مرجع (ET₀) حدود {et0:.1f} میلی‌متر است. در مزارع آبی، نیاز آبی را جدی بگیرید."
        )
    elif precip_sum > 5:
        recs.append(
            f"**بارش:** حدود {precip_sum:.1f} میلی‌متر بارش پیش‌بینی شده. از آبیاری اضافی خودداری کنید و زهکشی را بررسی کنید."
        )
    
    # توصیه سم‌پاشی
    if wind > 15:
        recs.append(
            f"**سم‌پاشی:** سرعت باد {wind:.0f} km/h است. از سم‌پاشی خودداری کنید تا از رانش سم جلوگیری شود."
        )
    elif humidity > 80 and precip_prob > 40:
        recs.append(
            "**بیماری‌های قارچی:** رطوبت بالا و احتمال بارش، خطر بیماری‌های برگی (زنگ، سپتوریوز) را افزایش می‌دهد. پایش مزارع را جدی بگیرید."
        )
    else:
        recs.append(
            "**سم‌پاشی:** شرایط باد و رطوبت نسبتاً مناسب است. قبل از سم‌پاشی سرعت باد و پیش‌بینی ۲-۳ ساعته را چک کنید."
        )
    
    # توصیه کود
    recs.append(
        "**کود:** قیمت کود اوره نوسان شدید دارد. مصرف را بر اساس آزمون خاک و نیاز واقعی گیاه تنظیم کنید و از خرید عجولانه بپرهیزید."
    )
    
    # توصیه عمومی
    if code >= 61:
        recs.append(
            "**عملیات مزرعه:** به دلیل بارش، از ورود ماشین‌آلات سنگین به مزارع خیس خودداری کنید تا از فشردگی خاک جلوگیری شود."
        )
    
    return recs


# -----------------------------
# سایدبار
# -----------------------------
with st.sidebar:
    st.markdown("### 🌾 دفتر فنی بابامنیر")
    st.markdown("---")
    
    selected_location = st.selectbox(
        "📍 انتخاب منطقه",
        list(LOCATIONS.keys()),
        index=0
    )
    
    st.markdown("---")
    page = st.radio(
        "بخش‌های داشبورد",
        [
            "🏠 خلاصه روز",
            "🌤️ هواشناسی زنده",
            "📊 مقایسه مناطق",
            "💰 قیمت نهاده‌ها",
            "🚜 توصیه‌های فنی",
            "📰 اخبار و منابع"
        ],
        index=0
    )
    
    st.markdown("---")
    st.caption("واتساپ: ۰۹۱۷۶۸۰۸۷۵۵")
    st.caption("ایتا و روبیکا: @a.d3469")
    st.caption("داده هواشناسی: Open-Meteo (زنده‌)")
    st.caption(f"آخرین به‌روزرسانی صفحه: {get_update_time()}")

# -----------------------------
# دریافت داده
# -----------------------------
loc = LOCATIONS[selected_location]
weather = get_weather(loc["lat"], loc["lon"], loc["name"])

# -----------------------------
# صفحه خلاصه روز
# -----------------------------
if page == "🏠 خلاصه روز":
    st.title("🌾 گزارش روزانه کشاورزی بابامنیر")
    st.markdown(f"**منطقه:** {selected_location} | **تاریخ:** {get_shamsi_date()}")
    st.markdown("---")
    
    if weather:
        current = weather["current"]
        daily = weather["daily"]
        
        # متریک‌های اصلی
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("دمای فعلی", f"{current['temperature_2m']:.1f}°C",
                      delta=f"احساس: {current.get('apparent_temperature', current['temperature_2m']):.1f}°C")
        with col2:
            st.metric("حداقل / حداکثر",
                      f"{daily['temperature_2m_min'][0]:.0f} / {daily['temperature_2m_max'][0]:.0f}°C")
        with col3:
            st.metric("رطوبت نسبی", f"{current['relative_humidity_2m']}%")
        with col4:
            st.metric("احتمال بارش", f"{daily['precipitation_probability_max'][0]}%")
        with col5:
            et0_today = daily.get("et0_fao_evapotranspiration", [0])[0]
            st.metric("ET₀ (تبخیر-تعرق)", f"{et0_today:.1f} mm")
        
        # وضعیت کلی
        wind_dir = wind_direction_to_text(current.get("wind_direction_10m"))
        st.info(
            f"**وضعیت فعلی:** {weather_code_to_text(current['weather_code'])} | "
            f"باد: {current['wind_speed_10m']:.0f} km/h از {wind_dir} | "
            f"تندباد: {current.get('wind_gusts_10m', 0):.0f} km/h | "
            f"فشار: {current.get('surface_pressure', 0):.0f} hPa"
        )
        
        # نمودار دما
        st.markdown("### 📈 پیش‌بینی دمای ۷ روز آینده")
        df_temp = pd.DataFrame({
            "تاریخ": daily["time"],
            "حداقل": daily["temperature_2m_min"],
            "حداکثر": daily["temperature_2m_max"]
        })
        fig_temp = go.Figure()
        fig_temp.add_trace(go.Scatter(
            x=df_temp["تاریخ"], y=df_temp["حداکثر"],
            mode="lines+markers", name="حداکثر",
            line=dict(color="#e74c3c", width=3),
            fill=None
        ))
        fig_temp.add_trace(go.Scatter(
            x=df_temp["تاریخ"], y=df_temp["حداقل"],
            mode="lines+markers", name="حداقل",
            line=dict(color="#3498db", width=3),
            fill="tonexty", fillcolor="rgba(52, 152, 219, 0.15)"
        ))
        fig_temp.update_layout(
            title=f"دمای روزانه - {selected_location}",
            height=380,
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            margin=dict(l=20, r=20, t=50, b=20)
        )
        st.plotly_chart(fig_temp, use_container_width=True)
        
        # نمودار بارش و احتمال
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("### 🌧️ احتمال و مقدار بارش")
            df_precip = pd.DataFrame({
                "تاریخ": daily["time"],
                "احتمال (%)": daily["precipitation_probability_max"],
                "بارش (mm)": daily["precipitation_sum"]
            })
            fig_precip = go.Figure()
            fig_precip.add_trace(go.Bar(
                x=df_precip["تاریخ"], y=df_precip["بارش (mm)"],
                name="بارش (mm)", marker_color="#3498db", opacity=0.8
            ))
            fig_precip.add_trace(go.Scatter(
                x=df_precip["تاریخ"], y=df_precip["احتمال (%)"],
                name="احتمال (%)", yaxis="y2",
                mode="lines+markers", line=dict(color="#e67e22", width=2)
            ))
            fig_precip.update_layout(
                height=320,
                yaxis=dict(title="بارش (mm)"),
                yaxis2=dict(title="احتمال (%)", overlaying="y", side="left", range=[0, 100]),
                legend=dict(orientation="h", y=1.12),
                margin=dict(l=20, r=20, t=30, b=20)
            )
            st.plotly_chart(fig_precip, use_container_width=True)
        
        with col_b:
            st.markdown("### 💨 حداکثر سرعت باد")
            df_wind = pd.DataFrame({
                "تاریخ": daily["time"],
                "حداکثر باد (km/h)": daily.get("wind_speed_10m_max", [0]*7)
            })
            fig_wind = px.bar(
                df_wind, x="تاریخ", y="حداکثر باد (km/h)",
                color="حداکثر باد (km/h)",
                color_continuous_scale="Blues"
            )
            fig_wind.update_layout(height=320, margin=dict(l=20, r=20, t=30, b=20), showlegend=False)
            st.plotly_chart(fig_wind, use_container_width=True)
        
        # نکات سریع
        st.markdown("### ⚡ نکات سریع امروز")
        quick_recs = generate_recommendations(weather, selected_location)[:3]
        for r in quick_recs:
            st.markdown(f"- {r}")
    else:
        st.error("دریافت داده هواشناسی با مشکل مواجه شد. لطفاً چند لحظه دیگر تلاش کنید.")

# -----------------------------
# صفحه هواشناسی زنده
# -----------------------------
elif page == "🌤️ هواشناسی زنده":
    st.title(f"🌤️ هواشناسی زنده — {selected_location}")
    
    if weather:
        current = weather["current"]
        daily = weather["daily"]
        hourly = weather.get("hourly", {})
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader("شرایط فعلی")
            st.markdown(f"""
            - **دما:** {current['temperature_2m']:.1f}°C  
            - **احساس واقعی:** {current.get('apparent_temperature', current['temperature_2m']):.1f}°C  
            - **رطوبت:** {current['relative_humidity_2m']}%  
            - **باد:** {current['wind_speed_10m']:.0f} km/h ({wind_direction_to_text(current.get('wind_direction_10m'))})  
            - **تندباد:** {current.get('wind_gusts_10m', 0):.0f} km/h  
            - **وضعیت:** {weather_code_to_text(current['weather_code'])}  
            - **فشار:** {current.get('surface_pressure', 0):.0f} hPa
            """)
        
        with col2:
            st.subheader("امروز")
            sunrise = daily.get("sunrise", ["-"])[0][-5:] if daily.get("sunrise") else "-"
            sunset = daily.get("sunset", ["-"])[0][-5:] if daily.get("sunset") else "-"
            st.markdown(f"""
            - **حداقل / حداکثر:** {daily['temperature_2m_min'][0]:.0f} / {daily['temperature_2m_max'][0]:.0f}°C  
            - **احتمال بارش:** {daily['precipitation_probability_max'][0]}%  
            - **مقدار بارش:** {daily['precipitation_sum'][0]:.1f} mm  
            - **ET₀:** {daily.get('et0_fao_evapotranspiration', [0])[0]:.1f} mm  
            - **شاخص UV حداکثر:** {daily.get('uv_index_max', [0])[0]:.1f}  
            - **طلوع / غروب:** {sunrise} / {sunset}
            """)
        
        with col3:
            st.subheader("اطلاعات منطقه")
            st.markdown(f"""
            - **عرض جغرافیایی:** {loc['lat']}  
            - **طول جغرافیایی:** {loc['lon']}  
            - **ارتفاع تقریبی:** ~{loc.get('elev', '—')} متر  
            - **منطقه زمانی:** Asia/Tehran  
            - **منبع:** Open-Meteo (مدل‌های ترکیبی)
            """)
        
        st.markdown("---")
        st.subheader("پیش‌بینی ۷ روز آینده")
        
        df7 = pd.DataFrame({
            "تاریخ": daily["time"],
            "حداقل (°C)": [round(x, 1) for x in daily["temperature_2m_min"]],
            "حداکثر (°C)": [round(x, 1) for x in daily["temperature_2m_max"]],
            "احتمال بارش (%)": daily["precipitation_probability_max"],
            "بارش (mm)": [round(x, 1) for x in daily["precipitation_sum"]],
            "باد حداکثر (km/h)": [round(x, 0) for x in daily.get("wind_speed_10m_max", [0]*7)],
            "ET₀ (mm)": [round(x, 1) for x in daily.get("et0_fao_evapotranspiration", [0]*7)],
            "UV": [round(x, 1) for x in daily.get("uv_index_max", [0]*7)],
            "وضعیت": [weather_code_to_text(c) for c in daily["weather_code"]]
        })
        st.dataframe(df7, use_container_width=True, hide_index=True)
        
        # نمودار ساعتی امروز (۱۲ ساعت آینده)
        if hourly and "time" in hourly:
            st.markdown("---")
            st.subheader("پیش‌بینی ساعتی (۲۴ ساعت آینده)")
            # فقط ۲۴ ساعت اول
            times = hourly["time"][:24]
            temps = hourly["temperature_2m"][:24]
            precip_p = hourly.get("precipitation_probability", [0]*24)[:24]
            precip = hourly.get("precipitation", [0]*24)[:24]
            
            df_h = pd.DataFrame({
                "ساعت": [t[11:16] for t in times],
                "دما": temps,
                "احتمال بارش": precip_p,
                "بارش": precip
            })
            
            fig_h = go.Figure()
            fig_h.add_trace(go.Scatter(
                x=df_h["ساعت"], y=df_h["دما"],
                mode="lines+markers", name="دما (°C)",
                line=dict(color="#e74c3c", width=2)
            ))
            fig_h.add_trace(go.Bar(
                x=df_h["ساعت"], y=df_h["بارش"],
                name="بارش (mm)", marker_color="#3498db", opacity=0.6, yaxis="y2"
            ))
            fig_h.update_layout(
                height=350,
                yaxis=dict(title="دما (°C)"),
                yaxis2=dict(title="بارش (mm)", overlaying="y", side="left", showgrid=False),
                legend=dict(orientation="h", y=1.12),
                margin=dict(l=20, r=20, t=30, b=20),
                hovermode="x unified"
            )
            st.plotly_chart(fig_h, use_container_width=True)
        
        st.caption("منبع: Open-Meteo | به‌روزرسانی خودکار هر ۳۰ دقیقه | مدل‌های ترکیبی جهانی")
    else:
        st.error("دریافت داده هواشناسی با مشکل مواجه شد.")

# -----------------------------
# صفحه مقایسه مناطق
# -----------------------------
elif page == "📊 مقایسه مناطق":
    st.title("📊 مقایسه سه منطقه تحت پوشش")
    st.markdown("مقایسه زنده شرایط هواشناسی بابامنیر، نورآباد ممسنی و ماهور میلاتی")
    st.markdown("---")
    
    comparison_data = []
    weathers = {}
    
    with st.spinner("در حال دریافت داده سه منطقه..."):
        for name, info in LOCATIONS.items():
            w = get_weather(info["lat"], info["lon"], name)
            weathers[name] = w
            if w:
                cur = w["current"]
                dai = w["daily"]
                comparison_data.append({
                    "منطقه": name,
                    "دما (°C)": round(cur["temperature_2m"], 1),
                    "رطوبت (%)": cur["relative_humidity_2m"],
                    "باد (km/h)": round(cur["wind_speed_10m"], 0),
                    "حداقل امروز": round(dai["temperature_2m_min"][0], 1),
                    "حداکثر امروز": round(dai["temperature_2m_max"][0], 1),
                    "احتمال بارش (%)": dai["precipitation_probability_max"][0],
                    "بارش (mm)": round(dai["precipitation_sum"][0], 1),
                    "ET₀ (mm)": round(dai.get("et0_fao_evapotranspiration", [0])[0], 1),
                    "وضعیت": weather_code_to_text(cur["weather_code"])
                })
    
    if comparison_data:
        df_comp = pd.DataFrame(comparison_data)
        st.dataframe(df_comp, use_container_width=True, hide_index=True)
        
        # نمودار مقایسه‌ای دما
        st.markdown("### مقایسه دمای فعلی و دامنه روزانه")
        fig_comp = go.Figure()
        for row in comparison_data:
            fig_comp.add_trace(go.Bar(
                name=row["منطقه"],
                x=["دمای فعلی", "حداقل", "حداکثر"],
                y=[row["دما (°C)"], row["حداقل امروز"], row["حداکثر امروز"]]
            ))
        fig_comp.update_layout(
            barmode="group",
            height=380,
            yaxis_title="دما (°C)",
            legend=dict(orientation="h", y=1.1),
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig_comp, use_container_width=True)
        
        st.info("💡 تفاوت ارتفاع و موقعیت محلی باعث اختلاف جزئی دما و بارش بین این سه نقطه می‌شود.")
    else:
        st.error("نتوانستیم داده مقایسه‌ای را دریافت کنیم.")

# -----------------------------
# صفحه قیمت نهاده‌ها
# -----------------------------
elif page == "💰 قیمت نهاده‌ها":
    st.title("💰 قیمت روز نهاده‌های کشاورزی")
    
    st.warning(
        "⚠️ **هشدار مهم:** قیمت کودها و نهاده‌ها به‌شدت متغیر است و به منبع، سهمیه و زمان خرید بستگی دارد. "
        "استعلام محلی از کارگزاری نورآباد ممسنی و جهاد کشاورزی ضروری است. اعداد زیر صرفاً تقریبی و جهت اطلاع هستند."
    )
    
    st.markdown("#### بذر")
    prices_seed = {
        "نهاده": [
            "بذر گندم نان گواهی‌شده",
            "بذر گندم دوروم گواهی‌شده",
            "بذر جو گواهی‌شده"
        ],
        "قیمت تقریبی (تومان)": ["۶۷٬۰۰۰ – ۷۲٬۰۰۰", "۷۵٬۰۰۰ – ۸۰٬۰۰۰", "۶۵٬۰۰۰ – ۷۲٬۰۰۰"],
        "واحد": ["کیلوگرم", "کیلوگرم", "کیلوگرم"],
        "توضیح": [
            "با احتساب یارانه دیم واجد شرایط",
            "معمولاً بدون یارانه مستقیم",
            "با یارانه برای طبقات دیم"
        ]
    }
    st.dataframe(pd.DataFrame(prices_seed), use_container_width=True, hide_index=True)
    
    st.markdown("#### کود")
    prices_fert = {
        "نهاده": [
            "کود اوره (۵۰ کیلویی)",
            "سوپرفسفات تریپل (۵۰ک)",
            "سولفات پتاسیم (۵۰ک)",
            "کود کامل NPK"
        ],
        "قیمت تقریبی (تومان)": [
            "۳٫۲ – ۳٫۸ میلیون (بازار آزاد)",
            "۶٫۵ – ۸ میلیون",
            "۶ – ۷٫۵ میلیون",
            "متغیر بر اساس آنالیز"
        ],
        "واحد": ["کیسه", "کیسه", "کیسه", "کیسه/کیلو"],
        "توضیح": [
            "نوسان بسیار شدید — حتماً استعلام محلی",
            "بازار آزاد تقریبی",
            "بازار آزاد تقریبی",
            "بسته به درصد عناصر"
        ]
    }
    st.dataframe(pd.DataFrame(prices_fert), use_container_width=True, hide_index=True)
    
    st.markdown("""
    <div class="info-box">
    <b>منابع پیشنهادی استعلام:</b><br>
    • کارگزاری‌های مجاز کود و بذر در نورآباد ممسنی<br>
    • جهاد کشاورزی شهرستان ممسنی<br>
    • شرکت خدمات حمایتی کشاورزی (سامانه)
    </div>
    """, unsafe_allow_html=True)
    
    st.caption("آخرین بازبینی دستی قیمت‌ها: آبان ۱۴۰۴ | این بخش به‌صورت دستی به‌روزرسانی می‌شود.")

# -----------------------------
# صفحه توصیه‌های فنی
# -----------------------------
elif page == "🚜 توصیه‌های فنی":
    st.title("🚜 توصیه‌های فنی امروز")
    st.markdown(f"**منطقه مبنا:** {selected_location} | **تاریخ:** {get_shamsi_date()}")
    st.markdown("---")
    
    if weather:
        recs = generate_recommendations(weather, selected_location)
        for i, rec in enumerate(recs, 1):
            st.markdown(f"**{i}.** {rec}")
            st.markdown("")
        
        st.markdown("---")
        st.subheader("نکات عمومی فصل")
        st.markdown("""
        - استفاده از بذر گواهی‌شده و ضدعفونی‌شده اولویت دارد.
        - قبل از مصرف کود، در صورت امکان آزمون خاک انجام دهید.
        - از ورود ماشین‌آلات به مزرعه در شرایط رطوبت بالای خاک خودداری کنید.
        - پایش مستمر آفات و بیماری‌ها (به‌ویژه زنگ‌ها و سپتوریوز) توصیه می‌شود.
        - در صورت بارش سنگین، زهکشی مزارع دیم را بررسی کنید.
        """)
    else:
        st.error("برای تولید توصیه‌های دقیق، به داده هواشناسی نیاز است.")

# -----------------------------
# صفحه اخبار و منابع
# -----------------------------
elif page == "📰 اخبار و منابع":
    st.title("📰 اخبار و منابع")
    
    st.markdown("### منابع هواشناسی")
    st.markdown("""
    - **Open-Meteo**: داده زنده و پیش‌بینی بدون نیاز به کلید API (منبع اصلی این داشبورد)
    - مدل‌های ترکیبی جهانی با وضوح مناسب برای منطقه فارس
    - به‌روزرسانی خودکار هر ۳۰ دقیقه در این داشبورد
    """)
    
    st.markdown("### منابع قیمت و اخبار کشاورزی")
    st.markdown("""
    - سازمان جهاد کشاورزی استان فارس
    - شرکت خدمات حمایتی کشاورزی
    - خبرگزاری‌های رسمی (ایرنا، ایسنا، مهر)
    - سامانه‌های استانی اطلاع‌رسانی کشاورزی
    """)
    
    st.markdown("### تماس با دفتر فنی بابامنیر")
    st.markdown("""
    - **واتساپ:** ۰۹۱۷۶۸۰۸۷۵۵  
    - **ایتا و روبیکا:** @a.d3469  
    - خدمات: مشاوره فنی، اطلاع‌رسانی روزانه، هماهنگی نهاده
    """)
    
    st.info("این داشبورد بخشی از سامانه اطلاع‌رسانی روزانه دفتر فنی بابامنیر است و گزارش متنی آن هر روز ساعت ۱۰ صبح به ایمیل‌های مشخص‌شده ارسال می‌شود.")

# -----------------------------
# فوتر
# -----------------------------
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #6c757d; font-size: 0.9em; padding: 1rem 0;'>
        🌱 دفتر فنی و خدمات کشاورزی بابامنیر<br>
        مشاوره | اطلاع‌رسانی | خدمات کشاورزی<br>
        واتساپ: ۰۹۱۷۶۸۰۸۷۵۵ &nbsp;|&nbsp; ایتا و روبیکا: @a.d3469<br>
        <small>داده هواشناسی از Open-Meteo • به‌روزرسانی هر ۳۰ دقیقه</small>
    </div>
    """,
    unsafe_allow_html=True
)
