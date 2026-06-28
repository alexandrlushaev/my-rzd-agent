import streamlit as st
from datetime import date, datetime, timedelta
from rzd_api import RzdClient
import pandas as pd
import statistics
from collections import defaultdict

# ---------- НАСТРОЙКА СТРАНИЦЫ ----------
st.set_page_config(
    page_title="РЖД Агент 2.0",
    page_icon="🚄",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------- КАСТОМНЫЙ CSS (ТЁМНАЯ ТЕМА) ----------
st.markdown("""
<style>
    /* Общий фон */
    .stApp {
        background: radial-gradient(ellipse at 20% 30%, #13203a, #09101e);
    }
    /* Карточки */
    .css-1r6slb0, .css-1v3fvcr, .css-1y4p8pa {
        background: rgba(255,255,255,0.03) !important;
        border: 1px solid rgba(255,255,255,0.05) !important;
        border-radius: 20px !important;
        padding: 20px !important;
        backdrop-filter: blur(4px);
        box-shadow: 0 8px 32px rgba(0,0,0,0.2);
    }
    /* Заголовки */
    h1, h2, h3, .stMarkdown {
        color: #f0f2f8 !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(255,255,255,0.04);
        border-radius: 16px;
        padding: 4px;
        border: 1px solid rgba(255,255,255,0.04);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 12px !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
        color: rgba(255,255,255,0.5) !important;
        transition: all 0.25s ease;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #1e3050, #0f1a30) !important;
        color: white !important;
        border: 1px solid rgba(212,175,55,0.15) !important;
        box-shadow: 0 8px 24px rgba(0,0,0,0.4) !important;
    }
    /* Кнопки */
    .stButton button {
        background: linear-gradient(135deg, #d4af37, #b8922e) !important;
        color: #0b1424 !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 14px !important;
        padding: 12px 32px !important;
        box-shadow: 0 8px 24px rgba(212,175,55,0.20);
        transition: all 0.25s ease;
    }
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 32px rgba(212,175,55,0.30);
        background: linear-gradient(135deg, #e2c14a, #c49f33) !important;
    }
    /* Метрики */
    .css-1xarl3l {
        background: rgba(255,255,255,0.03) !important;
        border-radius: 16px !important;
        padding: 16px !important;
        border: 1px solid rgba(255,255,255,0.04) !important;
        text-align: center;
    }
    .css-1xarl3l .css-1r4brx7 {
        font-size: 28px !important;
        font-weight: 700 !important;
        background: linear-gradient(135deg, #f6e6b0, #d4af37);
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
    }
    /* Таблицы */
    .dataframe {
        background: transparent !important;
        border-collapse: collapse !important;
    }
    .dataframe th {
        background: rgba(255,255,255,0.03) !important;
        color: rgba(255,255,255,0.5) !important;
        font-weight: 600 !important;
        font-size: 12px !important;
        text-transform: uppercase !important;
        border-bottom: 1px solid rgba(255,255,255,0.05) !important;
        padding: 12px 16px !important;
    }
    .dataframe td {
        color: rgba(255,255,255,0.85) !important;
        border-bottom: 1px solid rgba(255,255,255,0.03) !important;
        padding: 10px 16px !important;
    }
    .dataframe tr:hover td {
        background: rgba(255,255,255,0.02) !important;
    }
    /* Поля ввода */
    .stTextInput input, .stDateInput input, .stSelectbox select {
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        border-radius: 12px !important;
        color: #f0f2f8 !important;
        padding: 14px 18px !important;
    }
    .stTextInput input:focus, .stDateInput input:focus {
        border-color: rgba(212,175,55,0.4) !important;
        box-shadow: 0 0 0 3px rgba(212,175,55,0.08) !important;
    }
    /* Прогресс-бар */
    .stProgress > div > div {
        background: linear-gradient(90deg, #d4af37, #f6e6b0) !important;
    }
    /* Логотип и заголовок */
    .custom-header {
        display: flex;
        align-items: center;
        gap: 14px;
        margin-bottom: 20px;
    }
    .custom-header h1 {
        font-size: 26px;
        font-weight: 700;
        background: linear-gradient(135deg, #f6e6b0, #d4af37);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .custom-header small {
        color: rgba(255,255,255,0.3);
        font-size: 14px;
        font-weight: 400;
        -webkit-text-fill-color: rgba(255,255,255,0.3);
    }
</style>
""", unsafe_allow_html=True)

# ---------- КАСТОМНЫЙ ЗАГОЛОВОК (меняем «ссылку» / брендинг) ----------
st.markdown("""
<div class="custom-header">
    <span style="font-size:36px;">🚄</span>
    <h1>РЖД Агент <small>· умный поиск</small></h1>
</div>
""", unsafe_allow_html=True)

# ---------- ОБЩИЕ ФУНКЦИИ (ваши, без изменений) ----------
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

# ---------- ИНТЕРФЕЙС (3 ВКЛАДКИ) ----------
tab1, tab2, tab3 = st.tabs(["🔍 Поиск билетов", "😊 Счастливый вторник", "📊 Аналитик спроса"])

# --- Вкладка 1: Поиск ---
with tab1:
    st.header("🔍 Поиск билетов по маршруту")
    col1, col2 = st.columns(2)
    with col1:
        from_station = st.text_input("📍 Станция отправления", value="Санкт-Петербург", key="search_from")
        to_station = st.text_input("📍 Станция назначения", value="Москва", key="search_to")
    with col2:
        departure_date = st.date_input("📅 Дата отправления", value=date.today(), key="search_date")
        search_button = st.button("🔍 Найти поезда", type="primary", use_container_width=True)

    if search_button:
        if not from_station or not to_station:
            st.error("❌ Пожалуйста, заполните все поля.")
        else:
            with st.spinner(f"⏳ Ищем поезда из '{from_station}' в '{to_station}' на {departure_date.strftime('%d.%m.%Y')}..."):
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

# --- Вкладка 2: Счастливый вторник ---
with tab2:
    st.header("😊 Счастливый вторник")
    st.markdown("Проверяем наличие билетов по маршруту **Москва → Санкт-Петербург** на все ближайшие вторники.")
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

# --- Вкладка 3: Аналитик ---
with tab3:
    st.header("📊 Аналитик спроса")
    st.markdown("Анализируем спрос по заданному маршруту за выбранный период.")
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
            with st.spinner(f"⏳ Анализируем спрос за {days_analytics} дней... Это может занять несколько минут."):
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
