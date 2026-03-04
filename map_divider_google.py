import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from datetime import datetime

# Кешування геокодингу з довшим TTL та спіннером
@st.cache_data(ttl="1d", show_spinner="Завантаження меж регіону...")
def get_bounds(place_name: str) -> dict | None:
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

# Кешування створення Folium-карти (основна оптимізація)
@st.cache_data(ttl="30m", hash_funcs={dict: lambda b: tuple(sorted(b.items()))}, show_spinner="Генерація карти...")
def create_cached_map(bounds_dict: dict, tile_option: str) -> folium.Map:
    bounds = bounds_dict
    center_lat = (bounds['min_lat'] + bounds['max_lat']) / 2
    center_lon = (bounds['min_lon'] + bounds['max_lon']) / 2
    m = folium.Map(location=[center_lat, center_lon], tiles=None)

    # Вибір тайлів
    if tile_option == "Google Maps (дороги)":
        tiles_url = 'https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}'
        attr = 'Google'
    elif tile_option == "Google Satellite":
        tiles_url = 'https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}'
        attr = 'Google'
    else:
        tiles_url = 'OpenStreetMap'
        attr = '© OpenStreetMap contributors'

    folium.TileLayer(tiles=tiles_url, attr=attr, name=tile_option).add_to(m)

    m.fit_bounds([[bounds['min_lat'], bounds['min_lon']], [bounds['max_lat'], bounds['max_lon']]])

    folium.Rectangle(
        bounds=[[bounds['min_lat'], bounds['min_lon']], [bounds['max_lat'], bounds['max_lon']]],
        color="black", weight=3, fill=False
    ).add_to(m)

    mid_lat = (bounds['min_lat'] + bounds['max_lat']) / 2
    mid_lon = (bounds['min_lon'] + bounds['max_lon']) / 2

    folium.PolyLine([[mid_lat, bounds['min_lon']], [mid_lat, bounds['max_lon']]], color="blue", dash_array="5").add_to(m)
    folium.PolyLine([[bounds['min_lat'], mid_lon], [bounds['max_lat'], mid_lon]], color="blue", dash_array="5").add_to(m)

    for label, pos in [
        ("1 NW", [(mid_lat + bounds['max_lat'])/2, (bounds['min_lon'] + mid_lon)/2]),
        ("2 NE", [(mid_lat + bounds['max_lat'])/2, (mid_lon + bounds['max_lon'])/2]),
        ("3 SW", [(bounds['min_lat'] + mid_lat)/2, (bounds['min_lon'] + mid_lon)/2]),
        ("4 SE", [(bounds['min_lat'] + mid_lat)/2, (mid_lon + bounds['max_lon'])/2])
    ]:
        folium.Marker(
            location=pos,
            icon=folium.DivIcon(html=f'<div style="font-size:16pt;color:red;font-weight:bold;background:white;padding:4px;border-radius:4px;">{label}</div>')
        ).add_to(m)

    folium.Marker(
        [center_lat, center_lon],
        popup=f"Центр (рівень {st.session_state.level})<br>{center_lat:.6f}° N, {center_lon:.6f}° E",
        tooltip="Центр поточного квадрата",
        icon=folium.Icon(color='red', icon='info-sign')
    ).add_to(m)

    folium.CircleMarker(
        [center_lat, center_lon],
        radius=10,
        color="red",
        fill=True,
        fill_color="red",
        fill_opacity=0.5
    ).add_to(m)

    return m

# Початкові значення
DEFAULT_BOUNDS = {'min_lat': 44.38, 'max_lat': 52.38, 'min_lon': 22.14, 'max_lon': 40.23}

if 'current_bounds' not in st.session_state:
    st.session_state.current_bounds = DEFAULT_BOUNDS.copy()
if 'level' not in st.session_state:
    st.session_state.level = 0
if 'place_name' not in st.session_state:
    st.session_state.place_name = "Україна"

st.title("Оптимізований поділ карти з Google Maps")

# Вибір типу карти
tile_option = st.selectbox(
    "Оберіть тип карти:",
    ["Google Maps (дороги)", "Google Satellite", "OpenStreetMap (класичний)"],
    key="tile_option"
)

# Введення місця
place = st.text_input("Країна, область, місто чи регіон:", value=st.session_state.place_name)

if st.button("Завантажити межі"):
    if place.strip():
        bounds = get_bounds(place)
        if bounds:
            st.session_state.current_bounds = bounds
            st.session_state.place_name = place
            st.session_state.level = 0
            st.success(f"Завантажено: **{place}**")
            st.rerun()
        else:
            st.warning("Межі не знайдено.")
    else:
        st.warning("Введіть назву місця.")

# Відображення карти (кешовано)
map_obj = create_cached_map(st.session_state.current_bounds, tile_option)
st_folium(map_obj, width="100%", height=500, returned_objects=[])

# Інформація
bounds = st.session_state.current_bounds
center_lat = (bounds['min_lat'] + bounds['max_lat']) / 2
center_lon = (bounds['min_lon'] + bounds['max_lon']) / 2

st.subheader("Поточний центр")
st.markdown(f"**{center_lat:.6f}° N   |   {center_lon:.6f}° E**")
st.caption(f"Місце: {st.session_state.place_name}   |   Рівень: {st.session_state.level}")

# Форма для вибору квадрата (оптимізація: rerun тільки після submit)
st.subheader("Оберіть квадрат")
with st.form("quadrant_form"):
    quadrant = st.radio("Квадрат:", ["1 — Північний Захід", "2 — Північний Схід", "3 — Південний Захід", "4 — Південний Схід"], horizontal=True)
    submitted = st.form_submit_button("Застосувати поділ")

if submitted:
    mid_lat = (bounds['min_lat'] + bounds['max_lat']) / 2
    mid_lon = (bounds['min_lon'] + bounds['max_lon']) / 2
    if "1" in quadrant:
        st.session_state.current_bounds = {'min_lat': mid_lat, 'max_lat': bounds['max_lat'], 'min_lon': bounds['min_lon'], 'max_lon': mid_lon}
    elif "2" in quadrant:
        st.session_state.current_bounds = {'min_lat': mid_lat, 'max_lat': bounds['max_lat'], 'min_lon': mid_lon, 'max_lon': bounds['max_lon']}
    elif "3" in quadrant:
        st.session_state.current_bounds = {'min_lat': bounds['min_lat'], 'max_lat': mid_lat, 'min_lon': bounds['min_lon'], 'max_lon': mid_lon}
    elif "4" in quadrant:
        st.session_state.current_bounds = {'min_lat': bounds['min_lat'], 'max_lat': mid_lat, 'min_lon': mid_lon, 'max_lon': bounds['max_lon']}
    st.session_state.level += 1
    st.rerun()

# Збереження у файл
if st.button("Зберегти координати у файл (center_coordinates.txt)"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = f"""Збережено: {timestamp}
Місце: {st.session_state.place_name}
Рівень поділу: {st.session_state.level}
Центр: {center_lat:.6f}° N, {center_lon:.6f}° E
Межі:
  min_lat = {bounds['min_lat']:.6f}
  max_lat = {bounds['max_lat']:.6f}
  min_lon = {bounds['min_lon']:.6f}
  max_lon = {bounds['max_lon']:.6f}

"""
    try:
        with open("center_coordinates.txt", "a", encoding="utf-8") as f:
            f.write(content + "-" * 60 + "\n\n")
        st.success("Збережено у **center_coordinates.txt**")
    except Exception as e:
        st.error(f"Помилка збереження: {e}")

# Скидання
if st.button("Скинути все"):
    st.session_state.current_bounds = DEFAULT_BOUNDS.copy()
    st.session_state.level = 0
    st.session_state.place_name = "Україна"
    st.rerun()