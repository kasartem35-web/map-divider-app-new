import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from datetime import datetime

# Функція отримання bounding box
@st.cache_data(ttl=3600)
def get_bounds(place_name):
    geolocator = Nominatim(user_agent="map_divider_app")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1.1)
    try:
        location = geocode(place_name)
        if location and location.raw.get('boundingbox'):
            bb = location.raw['boundingbox']
            min_lat, max_lat, min_lon, max_lon = map(float, bb)
            if min_lat > max_lat: min_lat, max_lat = max_lat, min_lat
            if min_lon > max_lon: min_lon, max_lon = max_lon, min_lon
            return {'min_lat': min_lat, 'max_lat': max_lat, 'min_lon': min_lon, 'max_lon': max_lon}
        return None
    except Exception as e:
        st.error(f"Помилка геокодингу: {e}")
        return None

# Початкові значення
DEFAULT_BOUNDS = {'min_lat': 44.38, 'max_lat': 52.38, 'min_lon': 22.14, 'max_lon': 40.23}

if 'current_bounds' not in st.session_state:
    st.session_state.current_bounds = DEFAULT_BOUNDS.copy()
if 'initial_bounds' not in st.session_state:
    st.session_state.initial_bounds = DEFAULT_BOUNDS.copy()  # для кнопки "До початку"
if 'level' not in st.session_state:
    st.session_state.level = 0
if 'place_name' not in st.session_state:
    st.session_state.place_name = "Україна"
if 'history' not in st.session_state:
    st.session_state.history = []

st.title("Поділ карти з Google Maps інтеграцією")

# Вибір типу базової карти
tile_option = st.selectbox(
    "Оберіть тип карти:",
    ["Google Maps (дороги)", "Google Satellite", "OpenStreetMap (класичний)"]
)

if tile_option == "Google Maps (дороги)":
    tiles_url = 'https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}'
    attr = 'Google'
elif tile_option == "Google Satellite":
    tiles_url = 'https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}'
    attr = 'Google'
else:
    tiles_url = 'OpenStreetMap'
    attr = '© OpenStreetMap contributors'

# Введення місця
place = st.text_input("Країна, область, місто чи регіон:", value=st.session_state.place_name)

if st.button("Завантажити межі") or (place != st.session_state.place_name and place.strip()):
    if place.strip():
        bounds = get_bounds(place)
        if bounds:
            st.session_state.current_bounds = bounds.copy()
            st.session_state.initial_bounds = bounds.copy()  # запам'ятовуємо як "початок"
            st.session_state.place_name = place
            st.session_state.level = 0
            st.session_state.history = []
            st.success(f"Завантажено: **{place}**")
            st.rerun()
        else:
            st.warning("Межі не знайдено. Спробуйте: 'Київська область', 'New South Wales' тощо.")
    else:
        st.warning("Введіть назву місця.")

# Функція створення карти
# Функція створення карти (оновлена)
def create_map(bounds):
    center_lat = (bounds['min_lat'] + bounds['max_lat']) / 2
    center_lon = (bounds['min_lon'] + bounds['max_lon']) / 2
    
    m = folium.Map(location=[center_lat, center_lon], tiles=None)

    folium.TileLayer(
        tiles=tiles_url,
        attr=attr,
        name=tile_option,
        overlay=False,
        control=True
    ).add_to(m)

    # Додаємо прямокутник і елементи (як було)
    folium.Rectangle(
        bounds=[[bounds['min_lat'], bounds['min_lon']], [bounds['max_lat'], bounds['max_lon']]],
        color="black", weight=3, fill=False
    ).add_to(m)

    mid_lat = (bounds['min_lat'] + bounds['max_lat']) / 2
    mid_lon = (bounds['min_lon'] + bounds['max_lon']) / 2

    folium.PolyLine([[mid_lat, bounds['min_lon']], [mid_lat, bounds['max_lon']]], color="blue", dash_array="5").add_to(m)
    folium.PolyLine([[bounds['min_lat'], mid_lon], [bounds['max_lat'], mid_lon]], color="blue", dash_array="5").add_to(m)

    # Маркери 1-4, центр тощо (залишаємо як є)
    # ... ваш код маркерів ...

    # Важливо: явно встановлюємо bounds після всіх елементів
    m.fit_bounds(
        [[bounds['min_lat'], bounds['min_lon']], [bounds['max_lat'], bounds['max_lon']]],
        padding_top_left=[30, 30],
        padding_bottom_right=[30, 100],   # більше місця знизу для кнопок
        max_zoom=12                        # обмежуємо максимальний зум, щоб не було надто близько
    )

    return m

# Виклик карти — з ключем для примусового оновлення
key = f"map_{st.session_state.level}_{tile_option}"  # ключ змінюється при зміні рівня або типу карти

map_obj = create_map(st.session_state.current_bounds)
st_folium(
    map_obj,
    width="100%",
    height=550,
    key=key,                       # критичний рядок — змушує Streamlit перестворювати віджет
    returned_objects=[]            # якщо не потрібні кліки по карті
)


# Виклик карти — з ключем для примусового оновлення
key = f"map_{st.session_state.level}_{tile_option}"  # ключ змінюється при зміні рівня або типу карти

map_obj = create_map(st.session_state.current_bounds)
st_folium(
    map_obj,
    width="100%",
    height=550,
    key=key,                       # критичний рядок — змушує Streamlit перестворювати віджет
    returned_objects=[]            # якщо не потрібні кліки по карті
)

map_obj = create_map(st.session_state.current_bounds)
st_folium(map_obj, width=900, height=600)

# Інформація
bounds = st.session_state.current_bounds
center_lat = (bounds['min_lat'] + bounds['max_lat']) / 2
center_lon = (bounds['min_lon'] + bounds['max_lon']) / 2

st.subheader("Поточний центр")
st.markdown(f"**{center_lat:.6f}° N   |   {center_lon:.6f}° E**")
st.caption(f"Місце: {st.session_state.place_name}   |   Рівень: {st.session_state.level}")

# Панель керування
st.subheader("Керування поділом")

col_back, col_reset, _ = st.columns([2, 2, 4])

with col_back:
    if st.button("← Повернутися на крок назад", disabled=len(st.session_state.history) == 0):
        if st.session_state.history:
            st.session_state.current_bounds = st.session_state.history.pop()
            st.session_state.level = max(0, st.session_state.level - 1)
            st.rerun()

with col_reset:
    if st.button("Повернутися до початку"):
        st.session_state.current_bounds = st.session_state.initial_bounds.copy()
        st.session_state.level = 0
        st.session_state.history = []  # очищаємо історію, бо повернулися до старту
        st.rerun()

# Кнопки поділу
st.subheader("Оберіть квадрат")
col1, col2, col3, col4 = st.columns(4)
with col1:
    if st.button("1 — Північний Захід"):
        mid_lat = (bounds['min_lat'] + bounds['max_lat']) / 2
        mid_lon = (bounds['min_lon'] + bounds['max_lon']) / 2
        st.session_state.history.append(st.session_state.current_bounds.copy())
        st.session_state.current_bounds = {'min_lat': mid_lat, 'max_lat': bounds['max_lat'], 'min_lon': bounds['min_lon'], 'max_lon': mid_lon}
        st.session_state.level += 1
        st.rerun()
with col2:
    if st.button("2 — Північний Схід"):
        mid_lat = (bounds['min_lat'] + bounds['max_lat']) / 2
        mid_lon = (bounds['min_lon'] + bounds['max_lon']) / 2
        st.session_state.history.append(st.session_state.current_bounds.copy())
        st.session_state.current_bounds = {'min_lat': mid_lat, 'max_lat': bounds['max_lat'], 'min_lon': mid_lon, 'max_lon': bounds['max_lon']}
        st.session_state.level += 1
        st.rerun()
with col3:
    if st.button("3 — Південний Захід"):
        mid_lat = (bounds['min_lat'] + bounds['max_lat']) / 2
        mid_lon = (bounds['min_lon'] + bounds['max_lon']) / 2
        st.session_state.history.append(st.session_state.current_bounds.copy())
        st.session_state.current_bounds = {'min_lat': bounds['min_lat'], 'max_lat': mid_lat, 'min_lon': bounds['min_lon'], 'max_lon': mid_lon}
        st.session_state.level += 1
        st.rerun()
with col4:
    if st.button("4 — Південний Схід"):
        mid_lat = (bounds['min_lat'] + bounds['max_lat']) / 2
        mid_lon = (bounds['min_lon'] + bounds['max_lon']) / 2
        st.session_state.history.append(st.session_state.current_bounds.copy())
        st.session_state.current_bounds = {'min_lat': bounds['min_lat'], 'max_lat': mid_lat, 'min_lon': mid_lon, 'max_lon': bounds['max_lon']}
        st.session_state.level += 1
        st.rerun()

# Збереження у файл
if st.button("Зберегти координати у файл"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = f"""Збережено: {timestamp}
Місце: {st.session_state.place_name}
Рівень: {st.session_state.level}
Центр: {center_lat:.6f} N, {center_lon:.6f} E
Межі:
  min_lat = {bounds['min_lat']:.6f}
  max_lat = {bounds['max_lat']:.6f}
  min_lon = {bounds['min_lon']:.6f}
  max_lon = {bounds['max_lon']:.6f}

"""
    try:
        with open("center_coordinates.txt", "a", encoding="utf-8") as f:
            f.write(content + "-" * 60 + "\n\n")
        st.success("Збережено у center_coordinates.txt")
    except Exception as e:
        st.error(f"Помилка збереження: {e}")

# Скидання всього
if st.button("Скинути все до дефолтної України"):
    st.session_state.current_bounds = DEFAULT_BOUNDS.copy()
    st.session_state.initial_bounds = DEFAULT_BOUNDS.copy()
    st.session_state.level = 0
    st.session_state.place_name = "Україна"
    st.session_state.history = []
    st.rerun()

