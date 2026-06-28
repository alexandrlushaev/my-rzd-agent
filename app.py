import streamlit as st
from datetime import date, datetime, timedelta
from rzd_api import RzdClient
import pandas as pd
import statistics
from collections import defaultdict

# ---------- ОБЩИЕ ФУНКЦИИ (ЛОГИКА КЛИЕНТА) ----------
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

# ---------- ТОТАЛЬНЫЙ РЕДИЗАЙН: СУПЕРКОНТРАСТНЫЙ ТЕМНЫЙ СТИЛЬ ----------
st.set_page_config(page_title="RZD Analytics Terminal", page_icon="🎛️", layout="wide")

st.markdown("""
    <style>
    /* 1. Глубокий темный фон для всего приложения */
    .stApp {
        background-color: #121318 !important;
        color: #E2E8F0 !important;
        font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Скрытие стандартных контролов Streamlit */
    #MainMenu, footer, header {visibility: hidden;}
    .block-container {padding-top: 2.5rem !important; padding-bottom: 2rem !important;}

    /* 2. Контрастный премиум-блок заголовка */
    .brand-container {
        background: #1A1C23;
        padding: 35px;
        border-radius: 16px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
        margin-bottom: 30px;
        border: 1px solid #2D313F;
        text-align: left;
    }
    .brand-title {
        font-size: 2.4rem;
        font-weight: 800;
        color: #FFFFFF !important;
        margin: 0;
        letter-spacing: -0.5px;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .brand-subtitle {
        color: #94A3B8 !important;
        font-size: 1.05rem;
        margin-top: 8px;
        margin-bottom: 0;
    }

    /* 3. Кнопки-вкладки (Tabs) в стиле темного терминала */
    div[data-testid="stTabs"] {
        background: #1A1C23 !important;
        padding: 6px;
        border-radius: 12px;
        margin-bottom: 30px;
        border: 1px solid #2D313F;
    }
    div[data-testid="stTabs"] button {
        background: transparent !important;
        color: #94A3B8 !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 12px 24px !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
    div[data-testid="stTabs"] button[aria-selected="true"] {
        background: #2D313F !important;
        color: #00E676 !important; /* Контрастный неоновый зеленый */
    }
    div[data-testid="stTabs"] div[data-baseweb="tab-highlight-bar"] {
        display: none !important;
    }

    /* 4. Неоновые высококонтрастные карточки-метрики */
    div[data-testid="metric-container"] {
        background: #1A1C23 !important;
        border: 1px solid #2D313F !important;
        border-radius: 16px !important;
        padding: 24px !important;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3) !important;
    }
    div[data-testid="metric-container"]:hover {
        border-color: #00E676 !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 2.1rem !important;
        font-weight: 800 !important;
        color: #FFFFFF !important; /* Ярко-белые цифры */
    }
    div[data-testid="stMetricLabel"] {
        color: #94A3B8 !important; /* Четкий серый текст */
        font-weight: 700 !important;
        font-size: 0.85rem !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* 5. Экстремально заметная кнопка действия */
    div.stButton > button:first-child {
        background: #00E676 !important; /* Неоновый зеленый — промахнуться невозможно */
        color: #0F1115 !important; /* Глубокий черный текст для максимального контраста */
        font-weight: 700 !important;
        font-size: 1.05rem !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 16px 32px !important;
        box-shadow: 0 4px 20px rgba(0, 230, 118, 0.25) !important;
        transition: all 0.2s ease;
        width: 100%;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    div.stButton > button:first-child:hover {
        background: #00B359 !important;
        transform: translateY(-1px);
        box-shadow: 0 6px 24px rgba(0, 230, 118, 0.4) !important;
    }

    /* 6. Кастомизация полей ввода (Темный контраст) */
    .stTextInput input, .stDateInput input {
        background-color: #1A1C23 !important;
        border: 2px solid #2D313F !important;
        border-radius: 10px !important;
        color: #FFFFFF !important; /* Белый текст при вводе */
        padding: 14px !important;
        font-size: 1rem !important;
    }
    .stTextInput input:focus, .stDateInput input:focus {
        border-color: #00E676 !important;
    }
    
    /* Текст лейблов над полями ввода */
    label {
        color: #CBD5E1 !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        margin-bottom: 8px !important;
    }

    /* Настройка разделителей и системных сообщений */
    hr { border-top: 1px solid #2D313F !important; }
    .stAlert {
        background-color: #1A1C23 !important;
        color: #E2E8F0 !important;
        border: 1px solid #2D313F !important;
        border-radius: 12px !important;
    }
    </style>
""", unsafe_allow_html=True)

# Отображение кастомного баннера шапки
st.markdown("""
    <div class="brand-container">
        <h1 class="brand-title">🎛️ RZD Terminal v2.0</h1>
        <p class="brand-subtitle">Профессиональный инструмент мониторинга цен, парсинга емкости вагонов и трекинга свободных мест</p>
    </div>
""", unsafe_allow_html=True)

# Инициализация темных табов
tab1, tab2, tab3 = st.tabs(["⚡ Поиск билетов", "📅 Календарь (Вторники)", "📊 Глубокий анализ спроса"])

with tab1:
    st.markdown("### 🔍 Спецификация параметров поиска")
    
    col1, col2, col3 = st.columns([2, 2, 1.3])
    with col1:
        from_station = st.text_input("Станция отправления", value="Санкт-Петербург", key="search_from")
    with col2:
        to_station = st.text_input("Станция назначения", value="Москва", key="search_to")
    with col3:
        departure_date = st.date_input("Дата поездки", value=date.today(), key="search_date")

    st.write("")
    search_button = st.button("Выполнить сканирование рейсов", type="primary")

    if search_button:
        if not from_station or not to_station:
            st.error("Ошибка: Поля станций обязательны к заполнению.")
        else:
            with st.spinner("Синхронизация со шлюзом данных РЖД..."):
                tickets, actual_date, found = search_trains_with_fallback(from_station, to_station, departure_date, days_range=3)
                
                if not found:
                    st.warning("В системе бронирования нет доступных поездов на выбранные даты.")
                else:
                    if actual_date != departure_date:
                        st.info(f"На выбранное число мест нет. Ближайшие рейсы найдены на: {actual_date.strftime('%d.%m.%Y')}")
                    
                    trains_data = parse_train_data(tickets)
                    if not trains_data:
                        st.warning("Доступные рейсы обнаружены, но тарифная сетка скрыта системой.")
                    else:
                        df = pd.DataFrame(trains_data)
                        df_sorted = df.sort_values('Цена (мин.), ₽')
                        
                        st.write("")
                        # Высококонтрастные карточки
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Минимальный тариф", f"{df_sorted['Цена (мин.), ₽'].min():.0f} ₽")
                        m2.metric("Максимальный тариф", f"{df_sorted['Цена (мин.), ₽'].max():.0f} ₽")
                        m3.metric("Рейсов в выдаче", len(df_sorted))

                        st.write("")
                        st.markdown("#### Актуальное расписание и цены")
                        st.dataframe(df_sorted, use_container_width=True, hide_index=True)

                        csv = df_sorted.to_csv(index=False).encode('utf-8-sig')
                        st.write("")
                        st.download_button(
                            label="📥 Экспорт выгрузки в файл CSV",
                            data=csv,
                            file_name=f"terminal_export_{from_station}_{to_station}_{actual_date}.csv",
                            mime="text/csv",
                        )

with tab2:
    st.markdown("### 📅 Трекер серии «Вторники»")
    st.markdown("Поиск минимальных цен по направлению **Москва → Санкт-Петербург**.")
    
    weeks = st.slider("Глубина анализа (недель)", min_value=4, max_value=16, value=8, key="tuesday_weeks")
    tuesday_button = st.button("Запустить пакетный парсинг", type="primary")

    if tuesday_button:
        from_station, to_station = "Москва", "Санкт-Петербург"
        start_date = date.today()
        tuesdays = get_tuesdays(start_date, weeks)

        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        for idx, tuesday in enumerate(tuesdays):
            status_text.markdown(f"📡 *Парсинг логов на дату:* `{tuesday.strftime('%d.%m.%Y')}`")
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
                    'Классы мест': car_types
                })
            else:
                results.append({
                    'Дата': tuesday.strftime('%d.%m.%Y'),
                    'День недели': 'Вторник',
                    'Поезд': '❌ Мест нет / Закрыто',
                    'Отправление': '-',
                    'Прибытие': '-',
                    'Цена (мин.), ₽': None,
                    'Классы мест': error
                })
            progress_bar.progress((idx + 1) / len(tuesdays))

        status_text.empty()
        st.success("Пакетный анализ завершен успешно.")
        
        df = pd.DataFrame(results)
        st.dataframe(df, use_container_width=True, hide_index=True)

        available = df[df['Цена (мин.), ₽'].notna()]
        if not available.empty:
            st.write("")
            st.metric("🎯 Самый дешевый рейс в серии вторников", f"{available['Цена (мин.), ₽'].min():.0f} ₽")

with tab3:
    st.markdown("### 📊 Предиктивный модуль спроса")
    st.markdown("Расчет загрузки мест на линии для вычисления лучшего окна покупки билетов.")
    
    col1, col2, col3 = st.columns([2, 2, 1.5])
    with col1:
        anal_from = st.text_input("Станция А (Откуда)", value="Москва", key="anal_from")
    with col2:
        anal_to = st.text_input("Станция Б (Куда)", value="Санкт-Петербург", key="anal_to")
    with col3:
        days_analytics = st.slider("Глубина анализа сетки (дней)", min_value=14, max_value=90, value=14, step=7, key="analytics_days")
    
    st.write("")
    analytics_button = st.button("Рассчитать аналитическую матрицу", type="primary")

    if analytics_button:
        if not anal_from or not anal_to:
            st.error("Укажите обе контрольные точки маршрута.")
        else:
            start_date = date.today()
            with st.spinner("Сбор массивов исторических тарифов..."):
                progress_bar = st.progress(0)
                status_text = st.empty()

                def progress_callback(i, total):
                    progress_bar.progress((i + 1) / total)
                    status_text.markdown(f"🔄 *Анализ посуточных тренд-карт:* день `{i+1}` из `{total}`...")

                result = analyze_period(anal_from, anal_to, start_date, days_analytics, progress_callback)
                status_text.empty()

            st.success("Аналитический срез построен успешно!")
            
            col1, col2, col3 = st.columns(3)
            if result['popular_day']:
                col1.metric("Пиковый спрос (Sold Out)", f"{result['popular_day_name']} ({result['popular_day'].strftime('%d.%m')})")
            else:
                col1.metric("Пиковый спрос", "Нет данных")

            if result['cheapest_day']:
                col2.metric("Лучшее окно покупки", result['cheapest_day'].strftime('%d.%m.%Y'), f"Ср. цена: {result['cheapest_day_price']:.0f} ₽")
            else:
                col2.metric("Лучшее окно покупки", "Нет данных")

            if result['most_expensive_day']:
                col3.metric("Максимальное удорожание", result['most_expensive_day'].strftime('%d.%m.%Y'), f"Ср. цена: {result['most_expensive_day_price']:.0f} ₽")
            else:
                col3.metric("Максимальное удорожание", "Нет данных")
