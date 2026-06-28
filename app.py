import streamlit as st
from datetime import date, datetime, timedelta
from rzd_api import RzdClient
import pandas as pd
import statistics
from collections import defaultdict

# ---------- ОБЩИЕ ФУНКЦИИ (ЛОГИКА АГЕНТА) ----------
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

# ---------- НАСТРОЙКА СТРАНИЦЫ И ГЛУБОКИЙ РЕБРЕНДИНГ ДИЗАЙНА ----------
st.set_page_config(page_title="SmartTicket Pro | Продвинутая аналитика", page_icon="⚡", layout="wide")

# Инъекция кастомных стилей CSS для полной переработки интерфейса
st.markdown("""
    <style>
    /* 1. Глобальный футуристичный фон приложения */
    .stApp {
        background: linear-gradient(135deg, #0d0e15 0%, #16192b 50%, #0d0e15 100%) !important;
        font-family: 'Inter', -apple-system, sans-serif;
    }
    
    /* Скрываем стандартный копирайт и элементы Streamlit, чтобы сайт выглядел авторским */
    #MainMenu, footer, header {visibility: hidden;}
    
    /* 2. Стилизация главного кастомного заголовка */
    .header-box {
        text-align: center;
        padding: 40px 10px 20px 10px;
    }
    .main-title {
        font-size: 3.5rem;
        font-weight: 800;
        background: linear-gradient(45deg, #00f2fe, #4facfe);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -1px;
        margin-bottom: 5px;
    }
    .sub-title {
        color: #7e84a3;
        font-size: 1.2rem;
        font-weight: 400;
    }

    /* 3. Переработка карточек статистики (Метрик) */
    div[data-testid="metric-container"] {
        background: rgba(30, 34, 58, 0.6) !important;
        border: 1px solid rgba(79, 172, 254, 0.3) !important;
        border-radius: 16px !important;
        padding: 22px 20px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37) !important;
        backdrop-filter: blur(8px) !important;
        -webkit-backdrop-filter: blur(8px) !important;
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 40px 0 rgba(0, 242, 254, 0.2) !important;
        border: 1px solid rgba(0, 242, 254, 0.6) !important;
    }
    
    /* Настройка шрифтов внутри карточек */
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        color: #ffffff !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #a0aec0 !important;
        font-size: 0.95rem !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* 4. Полная переделка кнопок под неоновый стиль */
    div.stButton > button:first-child {
        background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%) !important;
        color: #0d0e15 !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 12px 24px !important;
        box-shadow: 0 4px 15px rgba(0, 242, 254, 0.3) !important;
        transition: all 0.25s ease;
    }
    div.stButton > button:first-child:hover {
        transform: scale(1.01);
        box-shadow: 0 6px 20px rgba(0, 242, 254, 0.5) !important;
    }
    div.stButton > button:first-child:active {
        transform: scale(0.99);
    }

    /* 5. Настройка контейнеров для полей ввода (Blur эффект) */
    div[data-testid="stForm"], .stTextInput, .stDateInput, .stSlider {
        background: rgba(22, 25, 43, 0.7);
        padding: 10px;
        border-radius: 12px;
    }
    label {
        color: #cbd5e1 !important;
        font-weight: 500 !important;
    }
    
    /* Изменение вида вкладок (Tabs) */
    button[data-baseweb="tab"] {
        color: #7e84a3 !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        transition: color 0.3s ease;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #00f2fe !important;
        border-bottom-color: #00f2fe !important;
    }
    </style>
""", unsafe_allow_html=True)

# Рендеринг нового фирменного блока заголовка
st.markdown("""
    <div class="header-box">
        <h1 class="main-title">⚡ SmartTicket Pro</h1>
        <p class="sub-title">Аналитическая AI-панель мониторинга и оптимизации пассажирских маршрутов</p>
    </div>
""", unsafe_allow_html=True)

st.write("") 

# Инициализация стильных вкладок
tab1, tab2, tab3 = st.tabs(["🔍 Интеллектуальный поиск", "📆 Мониторинг «Вторники»", "📊 Аналитика спроса"])

with tab1:
    st.markdown("### 🔎 Поиск рейсов по заданному направлению")
    
    # Компактный блок параметров ввода
    col1, col2, col3 = st.columns([2, 2, 1.2])
    with col1:
        from_station = st.text_input("📍 Станция отправления", value="Санкт-Петербург", key="search_from")
    with col2:
        to_station = st.text_input("🏁 Станция назначения", value="Москва", key="search_to")
    with col3:
        departure_date = st.date_input("📅 Дата поездки", value=date.today(), key="search_date")

    st.write("")
    search_button = st.button("🚀 Найти оптимальные билеты", type="primary", use_container_width=True)

    if search_button:
        if not from_station or not to_station:
            st.error("❌ Пожалуйста, заполните пункты отправления и назначения.")
        else:
            with st.spinner("⏳ Подключение к шлюзу данных, агрегация рейсов..."):
                tickets, actual_date, found = search_trains_with_fallback(from_station, to_station, departure_date, days_range=3)
                
                if not found:
                    st.warning("😔 Поездов на выбранные и ближайшие даты не обнаружено.")
                else:
                    if actual_date != departure_date:
                        st.info(f"ℹ️ Прямых рейсов на указанную дату нет. Выведены ближайшие доступные варианты на: **{actual_date.strftime('%d.%m.%Y')}**")
                    
                    trains_data = parse_train_data(tickets)
                    if not trains_data:
                        st.warning("😔 Информация о тарифной сетке пуста.")
                    else:
                        df = pd.DataFrame(trains_data)
                        df_sorted = df.sort_values('Цена (мин.), ₽')
                        
                        st.success(f"📊 Анализ завершен. Найдено актуальных рейсов: {len(df_sorted)}")
                        
                        # Метрики в кастомных неоновых карточках
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Лучшая цена", f"{df_sorted['Цена (мин.), ₽'].min():.0f} ₽", "Самый выгодный")
                        m2.metric("Максимальный тариф", f"{df_sorted['Цена (мин.), ₽'].max():.0f} ₽")
                        m3.metric("Доступно поездов", len(df_sorted))

                        st.write("")
                        st.markdown("#### 📋 Сводная таблица рейсов")
                        st.dataframe(df_sorted, use_container_width=True, hide_index=True)

                        # Стильная кнопка скачивания
                        csv = df_sorted.to_csv(index=False).encode('utf-8-sig')
                        st.download_button(
                            label="📥 Экспортировать выгрузку в CSV",
                            data=csv,
                            file_name=f"smartticket_{from_station}_{to_station}_{actual_date}.csv",
                            mime="text/csv",
                        )

with tab2:
    st.markdown("### 📆 Автоматический трекер «Счастливый вторник»")
    st.markdown("Поиск и детекция минимальных цен по стратегическому направлению **Москва ➔ Санкт-Петербург**.")
    
    weeks = st.slider("Глубина сканирования (недель)", min_value=4, max_value=16, value=8, key="tuesday_weeks")
    tuesday_button = st.button("⚡ Запустить циклическое сканирование вторников", type="primary")

    if tuesday_button:
        from_station, to_station = "Москва", "Санкт-Петербург"
        start_date = date.today()
        tuesdays = get_tuesdays(start_date, weeks)

        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        for idx, tuesday in enumerate(tuesdays):
            status_text.markdown(f"📡 *Сканирование квантовых данных на дату:* `{tuesday.strftime('%d.%m.%Y')}`...")
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
                    'Класс мест': car_types
                })
            else:
                results.append({
                    'Дата': tuesday.strftime('%d.%m.%Y'),
                    'День недели': 'Вторник',
                    'Поезд': '❌ Места распроданы / Ошибка',
                    'Отправление': '-',
                    'Прибытие': '-',
                    'Цена (мин.), ₽': None,
                    'Класс мест': error
                })
            progress_bar.progress((idx + 1) / len(tuesdays))

        status_text.empty()
        st.success("✅ Все периоды успешно просканированы!")
        
        df = pd.DataFrame(results)
        st.dataframe(df, use_container_width=True, hide_index=True)

        available = df[df['Цена (мин.), ₽'].notna()]
        if not available.empty:
            st.write("")
            st.metric("🎯 Минимальная зафиксированная стоимость", f"{available['Цена (мин.), ₽'].min():.0f} ₽", "Рекомендуется к покупке")
        else:
            st.warning("😔 На выбранные вторники свободных мест в системе продаж не найдено.")

with tab3:
    st.markdown("### 📊 Агент-аналитик спроса и рыночных трендов")
    st.markdown("Многопоточный сбор статистики загруженности мест для вычисления аномалий спроса.")
    
    col1, col2, col3 = st.columns([2, 2, 1.5])
    with col1:
        anal_from = st.text_input("📍 Пункт А", value="Москва", key="anal_from")
    with col2:
        anal_to = st.text_input("🏁 Пункт Б", value="Санкт-Петербург", key="anal_to")
    with col3:
        days_analytics = st.slider("Временной диапазон (дней)", min_value=14, max_value=90, value=14, step=7, key="analytics_days")
    
    st.write("")
    analytics_button = st.button("🧠 Запустить предиктивный анализ спроса", type="primary", use_container_width=True)

    if analytics_button:
        if not anal_from or not anal_to:
            st.error("❌ Укажите обе контрольные станции.")
        else:
            start_date = date.today()
            with st.spinner("⏳ Парсинг исторических срезов мест и вычисление дельт цен..."):
                progress_bar = st.progress(0)
                status_text = st.empty()

                def progress_callback(i, total):
                    progress_bar.progress((i + 1) / total)
                    status_text.markdown(f"🔄 *Анализируется матрица тарифов:* день `{i+1}` из `{total}`...")

                result = analyze_period(anal_from, anal_to, start_date, days_analytics, progress_callback)
                status_text.empty()

            st.success("✅ Сводный аналитический отчет сформирован!")
            
            st.markdown("#### 💡 Результаты макроанализа")
            col1, col2, col3 = st.columns(3)

            if result['popular_day']:
                col1.metric(
                    "🔥 Пиковая нагрузка (Sold Out)",
                    f"{result['popular_day_name']} ({result['popular_day'].strftime('%d.%m')})",
                    f"{result['popular_day_booked']} поездов без мест",
                    delta_color="inverse"
                )
            else:
                col1.metric("🔥 Пиковая нагрузка", "Недостаточно данных")

            if result['cheapest_day']:
                col2.metric(
                    "💰 Оптимальное окно покупки",
                    result['cheapest_day'].strftime('%d.%m.%Y'),
                    f"Ср. тариф: {result['cheapest_day_price']:.0f} ₽"
                )
            else:
                col2.metric("💰 Оптимальное окно покупки", "Нет данных")

            if result['most_expensive_day']:
                col3.metric(
                    "💸 Максимальное удорожание",
                    result['most_expensive_day'].strftime('%d.%m.%Y'),
                    f"Ср. тариф: {result['most_expensive_day_price']:.0f} ₽",
                    delta_color="inverse"
                )
            else:
                col3.metric("💸 Максимальное удорожание", "Нет данных")

            st.write("")
            st.info(f"📋 Суммарно обработано посуточных срезов: {result['total_days']}. Данные актуальны на текущую минуту.")
