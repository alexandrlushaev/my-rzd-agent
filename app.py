import streamlit as st
from datetime import date, datetime, timedelta
from rzd_api import RzdClient
import pandas as pd
import statistics
from collections import defaultdict

# ---------- НАСТРОЙКА СТРАНИЦЫ ----------
st.set_page_config(
    page_title="РЖД Агент",
    page_icon="🎫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- ПОЛНОСТЬЮ НОВЫЙ CSS (СВЕТЛАЯ ТЕМА) ----------
st.markdown("""
<style>
    /* Общий фон и шрифты */
    .stApp {
        background: #f5f7fb;
        font-family: 'Segoe UI', Roboto, sans-serif;
    }
    /* Сайдбар */
    .css-1d391kg {
        background: #ffffff !important;
        border-right: 1px solid #e9ecf0 !important;
        padding-top: 2rem !important;
        box-shadow: 2px 0 12px rgba(0,0,0,0.02);
    }
    .css-1d391kg .css-1v3fvcr {
        background: transparent !important;
    }
    /* Заголовок в сайдбаре */
    .sidebar-header {
        padding: 0 1rem 1.5rem 1rem;
        border-bottom: 1px solid #eef1f5;
        margin-bottom: 1.5rem;
    }
    .sidebar-header h1 {
        font-size: 1.6rem;
        font-weight: 700;
        color: #1e293b;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .sidebar-header small {
        color: #94a3b8;
        font-size: 0.85rem;
        font-weight: 400;
        display: block;
        margin-top: 0.2rem;
    }
    /* Радио-кнопки в сайдбаре (кастом) */
    .stRadio > div {
        display: flex;
        flex-direction: column;
        gap: 0.3rem;
    }
    .stRadio label {
        background: #f8fafc;
        border-radius: 12px;
        padding: 0.7rem 1.2rem;
        border: 1px solid #e9ecf0;
        transition: all 0.2s;
        font-weight: 500;
        color: #334155;
        cursor: pointer;
    }
    .stRadio label:hover {
        background: #f1f5f9;
        border-color: #cbd5e1;
    }
    .stRadio label[data-baseweb="radio"] {
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
    }
    /* Переопределяем выбранный элемент */
    .stRadio div[role="radiogroup"] > label {
        display: flex;
        align-items: center;
        gap: 0.8rem;
        padding: 0.7rem 1.2rem;
        border-radius: 12px;
        background: #f8fafc;
        border: 1px solid #e9ecf0;
        font-weight: 500;
        color: #334155;
        transition: all 0.2s;
    }
    .stRadio div[role="radiogroup"] > label[data-checked="true"] {
        background: #e0f2fe;
        border-color: #38bdf8;
        color: #0369a1;
        box-shadow: 0 2px 8px rgba(56, 189, 248, 0.15);
    }
    /* Карточки контента */
    .content-card {
        background: #ffffff;
        border-radius: 24px;
        padding: 1.8rem 2rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.02), 0 2px 6px rgba(0,0,0,0.02);
        border: 1px solid #edf2f7;
        margin-bottom: 1.8rem;
    }
    /* Заголовки страниц */
    .page-header {
        display: flex;
        align-items: center;
        gap: 0.8rem;
        margin-bottom: 1rem;
    }
    .page-header h2 {
        font-size: 1.8rem;
        font-weight: 700;
        color: #0f172a;
        margin: 0;
        letter-spacing: -0.3px;
    }
    .page-header .icon {
        font-size: 2rem;
    }
    .page-desc {
        color: #64748b;
        font-size: 1rem;
        margin-bottom: 1.8rem;
        border-left: 3px solid #38bdf8;
        padding-left: 1rem;
    }
    /* Поля ввода */
    .stTextInput input, .stDateInput input, .stSelectbox select {
        background: #f8fafc !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 14px !important;
        padding: 0.8rem 1.2rem !important;
        font-size: 1rem !important;
        color: #0f172a !important;
        transition: all 0.2s;
    }
    .stTextInput input:focus, .stDateInput input:focus {
        border-color: #38bdf8 !important;
        box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.2) !important;
        background: #ffffff !important;
    }
    /* Кнопки */
    .stButton button {
        background: linear-gradient(135deg, #0ea5e9, #0284c7) !important;
        color: white !important;
        font-weight: 600 !important;
        border: none !important;
        border-radius: 14px !important;
        padding: 0.8rem 2.5rem !important;
        box-shadow: 0 4px 12px rgba(14, 165, 233, 0.25) !important;
        transition: all 0.3s ease;
        font-size: 1rem;
        letter-spacing: 0.3px;
    }
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(14, 165, 233, 0.35) !important;
        background: linear-gradient(135deg, #38bdf8, #0ea5e9) !important;
    }
    .stButton button:active {
        transform: scale(0.97);
    }
    /* Метрики */
    .css-1xarl3l {
        background: #f8fafc !important;
        border-radius: 18px !important;
        padding: 1.2rem 1rem !important;
        border: 1px solid #e2e8f0 !important;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    .css-1xarl3l .css-1r4brx7 {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        color: #0f172a !important;
    }
    .css-1xarl3l .css-1p1fhlq {
        color: #64748b !important;
        font-size: 0.9rem !important;
    }
    /* Таблицы */
    .dataframe {
        background: transparent !important;
        border-collapse: separate !important;
        border-spacing: 0 4px !important;
    }
    .dataframe th {
        background: #f1f5f9 !important;
        color: #334155 !important;
        font-weight: 600 !important;
        font-size: 0.8rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px;
        padding: 0.8rem 1rem !important;
        border: none !important;
        border-radius: 12px 12px 0 0 !important;
    }
    .dataframe td {
        background: #ffffff !important;
        color: #1e293b !important;
        padding: 0.8rem 1rem !important;
        border: none !important;
        border-bottom: 1px solid #f1f5f9 !important;
    }
    .dataframe tr:last-child td {
        border-bottom: none;
    }
    .dataframe tr:hover td {
        background: #f8fafc !important;
    }
    /* Прогресс */
    .stProgress > div > div {
        background: linear-gradient(90deg, #0ea5e9, #38bdf8) !important;
        border-radius: 100px !important;
    }
    /* Инфо/успех/ошибка */
    .stAlert {
        border-radius: 14px !important;
        border: none !important;
        background: #f8fafc !important;
        padding: 1rem 1.5rem !important;
        border-left: 4px solid #38bdf8 !important;
    }
    .stAlert[data-baseweb="notification"] {
        background: #f1f5f9 !important;
    }
    /* Слайдер */
    .stSlider {
        padding: 0.5rem 0;
    }
    .stSlider > div > div {
        background: #e2e8f0 !important;
        border-radius: 100px !important;
        height: 4px !important;
    }
    .stSlider > div > div > div {
        background: #0ea5e9 !important;
    }
    .stSlider > div > div > div > div {
        background: #0ea5e9 !important;
        width: 18px !important;
        height: 18px !important;
        box-shadow: 0 2px 8px rgba(14, 165, 233, 0.3) !important;
    }
    /* Скачивание */
    .stDownloadButton button {
        background: #f1f5f9 !important;
        color: #1e293b !important;
        box-shadow: none !important;
        border: 1px solid #e2e8f0 !important;
        padding: 0.6rem 1.5rem !important;
    }
    .stDownloadButton button:hover {
        background: #e2e8f0 !important;
        transform: none !important;
    }
    /* Footer (внизу) */
    .footer {
        margin-top: 3rem;
        padding-top: 1.5rem;
        border-top: 1px solid #edf2f7;
        color: #94a3b8;
        font-size: 0.85rem;
        display: flex;
        justify-content: space-between;
        flex-wrap: wrap;
    }
</style>
""", unsafe_allow_html=True)

# ---------- БОКОВАЯ ПАНЕЛЬ (НАВИГАЦИЯ) ----------
with st.sidebar:
    st.markdown("""
    <div class="sidebar-header">
        <h1>🎫 РЖД Агент</h1>
        <small>умный поиск билетов</small>
    </div>
    """, unsafe_allow_html=True)
    
    mode = st.radio(
        "Выберите режим",
        options=["🔍 Поиск билетов", "😊 Счастливый вторник", "📊 Аналитик спроса"],
        index=0,
        label_visibility="collapsed"
    )
    st.sidebar.markdown("---")
    st.sidebar.caption("Данные предоставлены ticket.rzd.ru")
    st.sidebar.caption("Версия 2.0 · интерфейс обновлён")

# ---------- ОБЩИЕ ФУНКЦИИ (без изменений) ----------
def parse_train_data(tickets):
    trains_data = []
    for train in tickets:
        min_price = None
        car_groups = train.get('CarGroups', [])
        for group in car_groups:
            group_min_price = group.get('MinPrice')
            if group_min_price is not None:
                if min_price is None or group_min_price < min_price:
                    min_price = group_min_price
        if min_price is None:
            continue
        dep_time = train.get('DepartureDateTime') or train.get('LocalDepartureDateTime')
        arr_time = train.get('ArrivalDateTime') or train.get('LocalArrivalDateTime')
        train_name = train.get('TrainName') or train.get('TrainDescription') or ''
        car_types = sorted(set(g.get('CarTypeName', '') for g in car_groups if g.get('MinPrice') is not None))
        trains_data.append({
            'Номер': train.get('TrainNumber') or train.get('DisplayTrainNumber') or '—',
            'Название': train_name,
            'Отправление': dep_time[11:16] if dep_time else 'N/A',
            'Прибытие': arr_time[11:16] if arr_time else 'N/A',
            'Цена (мин.), ₽': float(min_price),
            'Типы вагонов': ', '.join(car_types) if car_types else '—'
        })
    return trains_data

def search_trains_with_fallback(from_station, to_station, departure_date, days_range=3):
    client = RzdClient()
    for delta in range(0, days_range + 1):
        for sign in [1, -1]:
            if delta == 0 and sign == -1:
                continue
            check_date = departure_date + timedelta(days=delta * sign)
            try:
                tickets = client.search_tickets(
                    from_station=from_station,
                    to_station=to_station,
                    departure_date=check_date
                )
                if tickets:
                    return tickets, check_date, True
            except Exception:
                continue
    return [], None, False

def get_tuesdays(start_date, weeks=8):
    tuesdays = []
    current = start_date
    while current.weekday() != 1:
        current += timedelta(days=1)
    for _ in range(weeks):
        tuesdays.append(current)
        current += timedelta(weeks=1)
    return tuesdays

def find_cheapest_ticket(from_station, to_station, departure_date):
    client = RzdClient()
    try:
        tickets = client.search_tickets(
            from_station=from_station,
            to_station=to_station,
            departure_date=departure_date
        )
    except Exception as e:
        return None, str(e)
    if not tickets:
        return None, "Нет поездов"
    min_price = None
    best_train = None
    for train in tickets:
        car_groups = train.get('CarGroups', [])
        for group in car_groups:
            group_min_price = group.get('MinPrice')
            if group_min_price is not None:
                if min_price is None or group_min_price < min_price:
                    min_price = group_min_price
                    best_train = {
                        'number': train.get('TrainNumber') or train.get('DisplayTrainNumber'),
                        'name': train.get('TrainName') or train.get('TrainDescription') or '',
                        'departure': train.get('DepartureDateTime') or train.get('LocalDepartureDateTime'),
                        'arrival': train.get('ArrivalDateTime') or train.get('LocalArrivalDateTime'),
                        'price': min_price,
                        'car_types': sorted(set(g.get('CarTypeName', '') for g in car_groups if g.get('MinPrice') is not None))
                    }
    if best_train:
        return best_train, None
    else:
        return None, "Нет доступных цен"

def analyze_period(from_station, to_station, start_date, days=60, progress_callback=None):
    client = RzdClient()
    daily_stats = defaultdict(lambda: {
        'total_trains': 0,
        'fully_booked': 0,
        'min_prices': [],
        'day_name': ''
    })
    current_date = start_date
    for i in range(days):
        if progress_callback:
            progress_callback(i, days)
        try:
            tickets = client.search_tickets(
                from_station=from_station,
                to_station=to_station,
                departure_date=current_date
            )
        except Exception:
            current_date += timedelta(days=1)
            continue
        day_name = current_date.strftime('%A')
        daily_stats[current_date]['day_name'] = day_name
        for train in tickets:
            daily_stats[current_date]['total_trains'] += 1
            car_groups = train.get('CarGroups', [])
            has_places = False
            min_price = None
            for group in car_groups:
                if group.get('PlaceQuantity', 0) > 0:
                    has_places = True
                group_min = group.get('MinPrice')
                if group_min is not None:
                    if min_price is None or group_min < min_price:
                        min_price = group_min
            if not has_places or train.get('IsWaitListAvailable', False):
                daily_stats[current_date]['fully_booked'] += 1
            if min_price is not None:
                daily_stats[current_date]['min_prices'].append(min_price)
        current_date += timedelta(days=1)
    best_day = None
    max_booked = -1
    for d, stats in daily_stats.items():
        if stats['fully_booked'] > max_booked:
            max_booked = stats['fully_booked']
            best_day = d
    day_avg_prices = {}
    for d, stats in daily_stats.items():
        if stats['min_prices']:
            avg_price = statistics.mean(stats['min_prices'])
            day_avg_prices[d] = avg_price
    if day_avg_prices:
        cheapest_day = min(day_avg_prices, key=day_avg_prices.get)
        most_expensive_day = max(day_avg_prices, key=day_avg_prices.get)
    else:
        cheapest_day = most_expensive_day = None
    return {
        'popular_day': best_day,
        'popular_day_name': daily_stats[best_day]['day_name'] if best_day else None,
        'popular_day_booked': max_booked,
        'cheapest_day': cheapest_day,
        'cheapest_day_price': day_avg_prices.get(cheapest_day) if cheapest_day else None,
        'most_expensive_day': most_expensive_day,
        'most_expensive_day_price': day_avg_prices.get(most_expensive_day) if most_expensive_day else None,
        'total_days': len(daily_stats)
    }

# ---------- ОСНОВНОЙ КОНТЕНТ (в зависимости от режима) ----------
st.markdown('<div class="content-card">', unsafe_allow_html=True)

if mode == "🔍 Поиск билетов":
    st.markdown("""
    <div class="page-header">
        <span class="icon">🔍</span>
        <h2>Поиск билетов</h2>
    </div>
    <div class="page-desc">Найдите все поезда по маршруту на нужную дату. Результаты отсортированы по возрастанию цены.</div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        from_station = st.text_input("📍 Станция отправления", value="Санкт-Петербург", key="search_from")
        to_station = st.text_input("📍 Станция назначения", value="Москва", key="search_to")
    with col2:
        departure_date = st.date_input("📅 Дата отправления", value=date.today(), key="search_date")
        st.write("")  # отступ
        search_button = st.button("🔍 Найти поезда", type="primary", use_container_width=True)

    if search_button:
        if not from_station or not to_station:
            st.error("❌ Пожалуйста, заполните все поля.")
        else:
            with st.spinner(f"Ищем поезда из '{from_station}' в '{to_station}' на {departure_date.strftime('%d.%m.%Y')}..."):
                tickets, actual_date, found = search_trains_with_fallback(from_station, to_station, departure_date, days_range=3)
                if not found:
                    st.warning("😔 Поездов не найдено на ближайшие даты (в пределах ±3 дней). Попробуйте другой маршрут или дату.")
                else:
                    if actual_date != departure_date:
                        st.info(f"ℹ️ На выбранную дату билетов не найдено. Показаны билеты на ближайшую дату: {actual_date.strftime('%d.%m.%Y')}")
                    trains_data = parse_train_data(tickets)
                    if not trains_data:
                        st.warning("😔 Не удалось найти информацию о ценах.")
                    else:
                        df = pd.DataFrame(trains_data)
                        df_sorted = df.sort_values('Цена (мин.), ₽')
                        st.success(f"✅ Найдено {len(df_sorted)} поездов.")
                        st.dataframe(df_sorted, use_container_width=True, hide_index=True)

                        col1, col2, col3 = st.columns(3)
                        col1.metric("Минимальная цена", f"{df_sorted['Цена (мин.), ₽'].min():.2f} ₽")
                        col2.metric("Максимальная цена", f"{df_sorted['Цена (мин.), ₽'].max():.2f} ₽")
                        col3.metric("Количество поездов", len(df_sorted))

                        csv = df_sorted.to_csv(index=False).encode('utf-8-sig')
                        st.download_button(
                            label="📥 Скачать результаты (CSV)",
                            data=csv,
                            file_name=f"trains_{from_station}_{to_station}_{actual_date}.csv",
                            mime="text/csv",
                        )

elif mode == "😊 Счастливый вторник":
    st.markdown("""
    <div class="page-header">
        <span class="icon">😊</span>
        <h2>Счастливый вторник</h2>
    </div>
    <div class="page-desc">Проверяем наличие билетов по маршруту <strong>Москва → Санкт-Петербург</strong> на все ближайшие вторники.</div>
    """, unsafe_allow_html=True)
    
    weeks = st.slider("Количество недель для проверки", min_value=4, max_value=16, value=8, key="tuesday_weeks")
    tuesday_button = st.button("🔍 Найти билеты на вторники", type="primary", use_container_width=True)

    if tuesday_button:
        from_station = "Москва"
        to_station = "Санкт-Петербург"
        start_date = date.today()
        tuesdays = get_tuesdays(start_date, weeks)

        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        for idx, tuesday in enumerate(tuesdays):
            status_text.text(f"Обработка {tuesday.strftime('%d.%m.%Y')}...")
            result, error = find_cheapest_ticket(from_station, to_station, tuesday)
            if result:
                dep_time = result['departure'][11:16] if result['departure'] else 'N/A'
                arr_time = result['arrival'][11:16] if result['arrival'] else 'N/A'
                car_types = ', '.join(result['car_types']) if result['car_types'] else '—'
                results.append({
                    'Дата': tuesday.strftime('%d.%m.%Y'),
                    'День недели': 'Вторник',
                    'Поезд': f"{result['number']} «{result['name']}»",
                    'Отправление': dep_time,
                    'Прибытие': arr_time,
                    'Цена (мин.), ₽': result['price'],
                    'Типы вагонов': car_types
                })
            else:
                results.append({
                    'Дата': tuesday.strftime('%d.%m.%Y'),
                    'День недели': 'Вторник',
                    'Поезд': '❌ Нет данных',
                    'Отправление': '-',
                    'Прибытие': '-',
                    'Цена (мин.), ₽': None,
                    'Типы вагонов': error
                })
            progress_bar.progress((idx + 1) / len(tuesdays))

        status_text.text("Готово!")
        df = pd.DataFrame(results)
        st.dataframe(df, use_container_width=True, hide_index=True)

        available = df[df['Цена (мин.), ₽'].notna()]
        if not available.empty:
            st.success(f"✅ Найдены билеты на {len(available)} из {len(tuesdays)} вторников.")
            st.metric("Минимальная цена среди всех вторников", f"{available['Цена (мин.), ₽'].min():.2f} ₽")
        else:
            st.warning("😔 Билеты не найдены ни на один вторник.")

else:  # Аналитик спроса
    st.markdown("""
    <div class="page-header">
        <span class="icon">📊</span>
        <h2>Аналитик спроса</h2>
    </div>
    <div class="page-desc">Анализируем спрос по заданному маршруту за выбранный период. Определяем популярные, дешёвые и дорогие дни.</div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        anal_from = st.text_input("📍 Станция отправления", value="Москва", key="anal_from")
        anal_to = st.text_input("📍 Станция назначения", value="Санкт-Петербург", key="anal_to")
    with col2:
        days_analytics = st.slider("Количество дней для анализа", min_value=14, max_value=90, value=60, step=7, key="analytics_days")
        analytics_button = st.button("📊 Запустить анализ", type="primary", use_container_width=True)

    if analytics_button:
        if not anal_from or not anal_to:
            st.error("❌ Пожалуйста, укажите обе станции.")
        else:
            start_date = date.today()
            with st.spinner(f"Анализируем спрос за {days_analytics} дней... Это может занять несколько минут."):
                progress_bar = st.progress(0)
                status_text = st.empty()

                def progress_callback(i, total):
                    progress_bar.progress((i + 1) / total)
                    status_text.text(f"Обработано {i+1} из {total} дней...")

                result = analyze_period(anal_from, anal_to, start_date, days_analytics, progress_callback)
                status_text.text("Анализ завершён!")

            st.success("✅ Анализ завершён!")
            col1, col2, col3 = st.columns(3)

            if result['popular_day']:
                col1.metric(
                    "🌟 Самый популярный день",
                    f"{result['popular_day_name']} ({result['popular_day'].strftime('%d.%m.%Y')})",
                    f"{result['popular_day_booked']} поездов без мест"
                )
            else:
                col1.metric("🌟 Самый популярный день", "Нет данных")

            if result['cheapest_day']:
                col2.metric(
                    "💰 Самый дешёвый день",
                    result['cheapest_day'].strftime('%d.%m.%Y'),
                    f"Ср. мин. цена: {result['cheapest_day_price']:.2f} ₽"
                )
            else:
                col2.metric("💰 Самый дешёвый день", "Нет данных")

            if result['most_expensive_day']:
                col3.metric(
                    "💸 Самый дорогой день",
                    result['most_expensive_day'].strftime('%d.%m.%Y'),
                    f"Ср. мин. цена: {result['most_expensive_day_price']:.2f} ₽"
                )
            else:
                col3.metric("💸 Самый дорогой день", "Нет данных")

            st.info(f"📌 Всего обработано дней: {result['total_days']}")

st.markdown('</div>', unsafe_allow_html=True)

# ---------- ПОДВАЛ ----------
st.markdown("""
<div class="footer">
    <span>© 2026 РЖД Агент · данные ticket.rzd.ru</span>
    <span>⚡ версия 2.0 · дизайн обновлён</span>
</div>
""", unsafe_allow_html=True)
