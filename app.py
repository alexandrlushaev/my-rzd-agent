import streamlit as st
from datetime import date, datetime, timedelta
from rzd_api import RzdClient
import pandas as pd
import statistics
from collections import defaultdict

# ---------- ОБЩИЕ ФУНКЦИИ (Оставлены без изменений логики) ----------
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

# ---------- НАСТРОЙКА СТРАНИЦЫ И ДИЗАЙН ----------
st.set_page_config(page_title="SmartTicket | Ассистент путешественника", page_icon="🎫", layout="wide")

# Кастомный CSS для улучшения визуала
st.markdown("""
    <style>
    /* Улучшение карточек с метриками */
    div[data-testid="metric-container"] {
        background-color: #1E1E2E; /* Темно-синий фон карточек для темной темы */
        border: 1px solid #33334d;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s ease-in-out;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        border: 1px solid #FF4B4B;
    }
    /* Если включена светлая тема */
    @media (prefers-color-scheme: light) {
        div[data-testid="metric-container"] {
            background-color: #ffffff;
            border: 1px solid #f0f2f6;
            box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        }
    }
    /* Кастомный заголовок сайта */
    .main-title {
        text-align: center;
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 700;
        font-size: 3rem;
        background: -webkit-linear-gradient(45deg, #FF4B4B, #FF8F8F);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
        padding-bottom: 0px;
    }
    .sub-title {
        text-align: center;
        color: #888888;
        font-size: 1.1rem;
        margin-top: -10px;
        margin-bottom: 30px;
    }
    </style>
""", unsafe_allow_html=True)

# Отрисовка нового заголовка
st.markdown("<h1 class='main-title'>🎫 SmartTicket</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>Ваш продвинутый ассистент по поиску и аналитике железнодорожных билетов</p>", unsafe_allow_html=True)

st.divider()

# Вкладки с новыми названиями
tab1, tab2, tab3 = st.tabs(["🔍 Умный поиск", "🍀 Счастливый вторник", "📈 Аналитика рынка"])

with tab1:
    st.markdown("### 🔎 Поиск билетов по маршруту")
    
    # Сгруппированные элементы ввода
    with st.container():
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            from_station = st.text_input("📍 Откуда", value="Санкт-Петербург", key="search_from")
        with col2:
            to_station = st.text_input("📍 Куда", value="Москва", key="search_to")
        with col3:
            departure_date = st.date_input("📅 Дата", value=date.today(), key="search_date")

    st.write("") # Небольшой отступ
    search_button = st.button("🚀 Найти рейсы", type="primary", use_container_width=True)

    if search_button:
        if not from_station or not to_station:
            st.error("❌ Пожалуйста, заполните пункты отправления и назначения.")
        else:
            with st.spinner(f"⏳ Собираем данные по маршруту '{from_station}' ➔ '{to_station}'..."):
                tickets, actual_date, found = search_trains_with_fallback(from_station, to_station, departure_date, days_range=3)
                
                if not found:
                    st.warning("😔 Поездов не найдено на ближайшие даты (в пределах ±3 дней).")
                else:
                    if actual_date != departure_date:
                        st.info(f"ℹ️ На {departure_date.strftime('%d.%m')} билетов нет. Показаны результаты на **{actual_date.strftime('%d.%m.%Y')}**")
                    
                    trains_data = parse_train_data(tickets)
                    if not trains_data:
                        st.warning("😔 Не удалось получить информацию о ценах.")
                    else:
                        df = pd.DataFrame(trains_data)
                        df_sorted = df.sort_values('Цена (мин.), ₽')
                        
                        st.success(f"✅ Успешно! Доступно поездов: {len(df_sorted)}")
                        
                        # Блок с красивой статистикой
                        st.markdown("#### 📊 Сводка по билетам")
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Минимальная цена", f"{df_sorted['Цена (мин.), ₽'].min():.0f} ₽", "Самый выгодный", delta_color="normal")
                        m2.metric("Максимальная цена", f"{df_sorted['Цена (мин.), ₽'].max():.0f} ₽")
                        m3.metric("Всего рейсов", len(df_sorted))

                        st.markdown("#### 📋 Расписание и цены")
                        st.dataframe(df_sorted, use_container_width=True, hide_index=True)

                        csv = df_sorted.to_csv(index=False).encode('utf-8-sig')
                        st.download_button(
                            label="📥 Сохранить отчет (CSV)",
                            data=csv,
                            file_name=f"smartticket_{from_station}_{to_station}_{actual_date}.csv",
                            mime="text/csv",
                        )

with tab2:
    st.markdown("### 🍀 Счастливый вторник")
    st.markdown("Поиск выгодных билетов на маршруте **Москва ➔ Санкт-Петербург** на ближайшие вторники.")
    
    with st.container():
        weeks = st.slider("Глубина поиска (в неделях)", min_value=4, max_value=16, value=8, key="tuesday_weeks")
        tuesday_button = st.button("🔍 Запустить проверку вторников", type="primary")

    if tuesday_button:
        from_station, to_station = "Москва", "Санкт-Петербург"
        start_date = date.today()
        tuesdays = get_tuesdays(start_date, weeks)

        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        for idx, tuesday in enumerate(tuesdays):
            status_text.text(f"Проверка: {tuesday.strftime('%d.%m.%Y')}...")
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
                    'Вагоны': car_types
                })
            else:
                results.append({
                    'Дата': tuesday.strftime('%d.%m.%Y'),
                    'День недели': 'Вторник',
                    'Поезд': '❌ Нет рейсов',
                    'Отправление': '-',
                    'Прибытие': '-',
                    'Цена (мин.), ₽': None,
                    'Вагоны': error
                })
            progress_bar.progress((idx + 1) / len(tuesdays))

        status_text.empty()
        st.success("✅ Проверка завершена!")
        
        df = pd.DataFrame(results)
        st.dataframe(df, use_container_width=True, hide_index=True)

        available = df[df['Цена (мин.), ₽'].notna()]
        if not available.empty:
            st.metric("🔥 Абсолютный минимум за период", f"{available['Цена (мин.), ₽'].min():.0f} ₽")
        else:
            st.warning("😔 Билеты не найдены ни на один из запрошенных вторников.")

with tab3:
    st.markdown("### 📈 Аналитика спроса")
    st.markdown("Глубокий анализ загруженности и динамики цен на заданном маршруте.")
    
    with st.container():
        col1, col2, col3 = st.columns([2, 2, 1.5])
        with col1:
            anal_from = st.text_input("📍 Откуда", value="Курск", key="anal_from")
        with col2:
            anal_to = st.text_input("📍 Куда", value="Москва", key="anal_to")
        with col3:
            days_analytics = st.slider("Период (дней)", min_value=14, max_value=90, value=14, step=7, key="analytics_days")
    
    st.write("")
    analytics_button = st.button("🧠 Сгенерировать инсайты", type="primary", use_container_width=True)

    if analytics_button:
        if not anal_from or not anal_to:
            st.error("❌ Укажите станции отправления и назначения.")
        else:
            start_date = date.today()
            with st.spinner("⏳ ИИ анализирует массивы данных... Это может занять время."):
                progress_bar = st.progress(0)
                status_text = st.empty()

                def progress_callback(i, total):
                    progress_bar.progress((i + 1) / total)
                    status_text.markdown(f"**Парсинг данных:** день {i+1} из {total}...")

                result = analyze_period(anal_from, anal_to, start_date, days_analytics, progress_callback)
                status_text.empty()

            st.success("✅ Анализ успешно завершен!")
            
            st.markdown("#### 💡 Ключевые выводы")
            col1, col2, col3 = st.columns(3)

            if result['popular_day']:
                col1.metric(
                    "🔥 Пиковый день загрузки",
                    f"{result['popular_day_name']} ({result['popular_day'].strftime('%d.%m')})",
                    f"Без мест: {result['popular_day_booked']}",
                    delta_color="inverse"
                )
            else:
                col1.metric("🔥 Пиковый день загрузки", "Нет данных")

            if result['cheapest_day']:
                col2.metric(
                    "💰 Самый бюджетный день",
                    result['cheapest_day'].strftime('%d.%m.%Y'),
                    f"Средняя цена: {result['cheapest_day_price']:.0f} ₽",
                    delta_color="normal"
                )
            else:
                col2.metric("💰 Самый бюджетный день", "Нет данных")

            if result['most_expensive_day']:
                col3.metric(
                    "💸 Самый дорогой день",
                    result['most_expensive_day'].strftime('%d.%m.%Y'),
                    f"Средняя цена: {result['most_expensive_day_price']:.0f} ₽",
                    delta_color="inverse"
                )
            else:
                col3.metric("💸 Самый дорогой день", "Нет данных")

            st.caption(f"ℹ️ Собрана аналитика за {result['total_days']} дней на основе текущего состояния продаж билетов.")