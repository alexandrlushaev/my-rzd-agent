import streamlit as st
from datetime import date, datetime, timedelta
from rzd_api import RzdClient
import pandas as pd
import statistics
from collections import defaultdict

# ---------- ОБЩИЕ ФУНКЦИИ (ЛОГИКА ОСТАЕТСЯ РАБОЧЕЙ) ----------
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

# ---------- КОЛОССАЛЬНЫЙ РЕБРЕНДИНГ И ИНЪЕКЦИЯ СТИЛЕЙ ----------
st.set_page_config(page_title="АвиаЖД Экстра | Поиск билетов", page_icon="🎫", layout="wide")

# Полный сброс стилей Streamlit под премиальный светлый интерфейс
st.markdown("""
    <style>
    /* Перекрашиваем абсолютно всё приложение в чистый светлый стиль */
    .stApp {
        background-color: #F8FAFC !important;
        color: #1E293B !important;
        font-family: '-apple-system', BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    
    /* Прячем дефолтные элементы шапки и подвала */
    #MainMenu, footer, header {visibility: hidden;}
    .block-container {padding-top: 2rem !important; padding-bottom: 2rem !important;}

    /* Блок заголовка в минималистичном стиле */
    .brand-container {
        background: #ffffff;
        padding: 30px;
        border-radius: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05), 0 1px 2px rgba(0,0,0,0.1);
        margin-bottom: 30px;
        border: 1px solid #E2E8F0;
    }
    .brand-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #0F172A;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .brand-subtitle {
        color: #64748B;
        font-size: 1rem;
        margin-top: 5px;
        margin-bottom: 0;
    }

    /* Мощная переделка вкладок (Tabs) под вид кнопок-переключателей */
    div[data-testid="stTabs"] {
        background: #E2E8F0;
        padding: 6px;
        border-radius: 14px;
        margin-bottom: 25px;
    }
    div[data-testid="stTabs"] button {
        background: transparent !important;
        color: #475569 !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 10px 20px !important;
        margin: 0 2px !important;
        transition: all 0.2s ease;
    }
    div[data-testid="stTabs"] button[aria-selected="true"] {
        background: #FFFFFF !important;
        color: #1A56DB !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08) !important;
    }
    /* Скрываем уродливую дефолтную красную линию под вкладками */
    div[data-testid="stTabs"] div[data-baseweb="tab-highlight-bar"] {
        display: none !important;
    }

    /* Новые премиум-карточки для метрик */
    div[data-testid="metric-container"] {
        background: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 16px !important;
        padding: 20px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05) !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 800 !important;
        color: #1E293B !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #64748B !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        text-transform: uppercase;
    }

    /* Полный редизайн кнопок действий */
    div.stButton > button:first-child {
        background: #1A56DB !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 14px 28px !important;
        box-shadow: 0 4px 12px rgba(26, 86, 219, 0.2) !important;
        transition: all 0.2s ease;
        width: 100%;
    }
    div.stButton > button:first-child:hover {
        background: #1E429F !important;
        box-shadow: 0 6px 16px rgba(26, 86, 219, 0.3) !important;
    }

    /* Переделка полей ввода */
    .stTextInput input, .stDateInput input {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 10px !important;
        color: #1E293B !important;
        padding: 12px !important;
    }
    .stTextInput input:focus, .stDateInput input:focus {
        border-color: #1A56DB !important;
        box-shadow: 0 0 0 3px rgba(26, 86, 219, 0.1) !important;
    }
    
    /* Стилизация контейнеров и разделителей */
    hr { border-top: 1px solid #E2E8F0 !important; }
    label { color: #475569 !important; font-weight: 600 !important; margin-bottom: 6px !important; }
    </style>
""", unsafe_allow_html=True)

# Отрисовка уникального верхнего блока
st.markdown("""
    <div class="brand-container">
        <h1 class="brand-title">🌐 Панель Навигации Билетов</h1>
        <p class="brand-subtitle">Система мониторинга тарифов и автоматического поиска свободных мест</p>
    </div>
""", unsafe_allow_html=True)

# Инициализация переработанных вкладок
tab1, tab2, tab3 = st.tabs(["🗺️ Поиск и фильтры", "📅 Календарь вторников", "📊 Аналитический модуль"])

with tab1:
    st.markdown("🔍 **Параметры нового поиска**")
    
    # Сетка ввода данных
    col1, col2, col3 = st.columns([2, 2, 1.3])
    with col1:
        from_station = st.text_input("Откуда", value="Санкт-Петербург", key="search_from")
    with col2:
        to_station = st.text_input("Куда", value="Москва", key="search_to")
    with col3:
        departure_date = st.date_input("Дата выезда", value=date.today(), key="search_date")

    st.write("")
    search_button = st.button("Сформировать таблицу рейсов", type="primary")

    if search_button:
        if not from_station or not to_station:
            st.error("Ошибка: укажите станции отправления и прибытия.")
        else:
            with st.spinner("Получение актуальных матриц мест..."):
                tickets, actual_date, found = search_trains_with_fallback(from_station, to_station, departure_date, days_range=3)
                
                if not found:
                    st.warning("По указанному направлению мест не найдено.")
                else:
                    if actual_date != departure_date:
                        st.info(f"На выбранную дату мест нет. Найдена ближайшая альтернатива: {actual_date.strftime('%d.%m.%Y')}")
                    
                    trains_data = parse_train_data(tickets)
                    if not trains_data:
                        st.warning("Не удалось прочесть тарифные планы.")
                    else:
                        df = pd.DataFrame(trains_data)
                        df_sorted = df.sort_values('Цена (мин.), ₽')
                        
                        st.write("")
                        # Вывод обновленных карточек-метрик
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Минимальный тариф", f"{df_sorted['Цена (мин.), ₽'].min():.0f} ₽")
                        m2.metric("Максимальный тариф", f"{df_sorted['Цена (мин.), ₽'].max():.0f} ₽")
                        m3.metric("Всего найдено поездов", len(df_sorted))

                        st.write("")
                        st.markdown("### 📋 Результаты мониторинга")
                        st.dataframe(df_sorted, use_container_width=True, hide_index=True)

                        csv = df_sorted.to_csv(index=False).encode('utf-8-sig')
                        st.download_button(
                            label="📥 Скачать отчет результатов (.CSV)",
                            data=csv,
                            file_name=f"report_{from_station}_{to_station}_{actual_date}.csv",
                            mime="text/csv",
                        )

with tab2:
    st.markdown("### 📅 Автоматический трекер «Вторники»")
    st.markdown("Система сканирует фиксированный маршрут **Москва → Санкт-Петербург**.")
    
    weeks = st.slider("Глубина анализа сетки (недель)", min_value=4, max_value=16, value=8, key="tuesday_weeks")
    tuesday_button = st.button("Запустить парсинг календаря", type="primary")

    if tuesday_button:
        from_station, to_station = "Москва", "Санкт-Петербург"
        start_date = date.today()
        tuesdays = get_tuesdays(start_date, weeks)

        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        for idx, tuesday in enumerate(tuesdays):
            status_text.markdown(f"🔍 *Анализ среза:* `{tuesday.strftime('%d.%m.%Y')}`")
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
                    'Типы мест': car_types
                })
            else:
                results.append({
                    'Дата': tuesday.strftime('%d.%m.%Y'),
                    'День недели': 'Вторник',
                    'Поезд': '❌ Свободных мест нет',
                    'Отправление': '-',
                    'Прибытие': '-',
                    'Цена (мин.), ₽': None,
                    'Типы мест': error
                })
            progress_bar.progress((idx + 1) / len(tuesdays))

        status_text.empty()
        st.success("Календарный анализ успешно завершен!")
        
        df = pd.DataFrame(results)
        st.dataframe(df, use_container_width=True, hide_index=True)

        available = df[df['Цена (мин.), ₽'].notna()]
        if not available.empty:
            st.write("")
            st.metric("🎯 Лучший тариф в серии", f"{available['Цена (мин.), ₽'].min():.0f} ₽")

with tab3:
    st.markdown("### 📊 Аналитический модуль")
    st.markdown("Сбор статистики емкости и загруженности вагонов.")
    
    col1, col2, col3 = st.columns([2, 2, 1.5])
    with col1:
        anal_from = st.text_input("Станция А", value="Москва", key="anal_from")
    with col2:
        anal_to = st.text_input("Станция Б", value="Санкт-Петербург", key="anal_to")
    with col3:
        days_analytics = st.slider("Глубина анализа (дней)", min_value=14, max_value=90, value=14, step=7, key="analytics_days")
    
    st.write("")
    analytics_button = st.button("Рассчитать коэффициенты спроса", type="primary")

    if analytics_button:
        if not anal_from or not anal_to:
            st.error("Заполните оба направления.")
        else:
            start_date = date.today()
            with st.spinner("Агрегация исторических срезов цен..."):
                progress_bar = st.progress(0)
                status_text = st.empty()

                def progress_callback(i, total):
                    progress_bar.progress((i + 1) / total)
                    status_text.markdown(f"🔄 *Чтение логов тарифов:* день `{i+1}` из `{total}`...")

                result = analyze_period(anal_from, anal_to, start_date, days_analytics, progress_callback)
                status_text.empty()

            st.success("Матрица спроса сформирована.")
            
            col1, col2, col3 = st.columns(3)
            if result['popular_day']:
                col1.metric("День максимального спроса", f"{result['popular_day_name']} ({result['popular_day'].strftime('%d.%m')})")
            else:
                col1.metric("День максимального спроса", "Нет данных")

            if result['cheapest_day']:
                col2.metric("Самый выгодный день", result['cheapest_day'].strftime('%d.%m.%Y'), f"Ср: {result['cheapest_day_price']:.0f} ₽")
            else:
                col2.metric("Самый выгодный день", "Нет данных")

            if result['most_expensive_day']:
                col3.metric("Самый дорогой период", result['most_expensive_day'].strftime('%d.%m.%Y'), f"Ср: {result['most_expensive_day_price']:.0f} ₽")
            else:
                col3.metric("Самый дорогой период", "Нет данных")
