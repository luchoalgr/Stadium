import pandas as pd
import requests
from math import radians
import numpy as np
import folium
import streamlit as st
from streamlit_folium import st_folium
from folium import plugins

# Streamlit Page Configuration
st.set_page_config(page_title="Stadium Finder", layout="wide", page_icon="⚽")

# =========================
# DATA LOADING
# =========================
@st.cache_data
def load_data():
    # Load local Excel file
    df = pd.read_excel("ComplexesFoot.xlsx")
    # Split coordinates into lat/lon
    df[["latitude", "longitude"]] = (
        df["equip_coordonnees"]
        .str.split(",", expand=True)
        .astype(float)
    )
    return df

stadiums = load_data()

# Reference Lists
list_trans = ['No preference', 'Autre', 'Avion', 'Bateau', 'Bus', 'Métro', 'Pas de desserte', 'Train', 'Tramway']
list_type_name = ['No preference', 'Aire de fitness/street workout', 'Arènes', 'Autres équipements divers', 
                  'But/Panier isolé de sport collectif', 'Multisports/City-stades', 'Terrain de foot 5x5', 
                  'Terrain de football', 'Terrain de futsal extérieur', 'Terrain de soccer', 'Terrain mixte']
list_nature = ['No preference', 'Découvert', 'Découvrable', 'Extérieur couvert', 'Intérieur', 'Site artificiel']
list_sol = ['No preference', 'Bitume', 'Béton', 'Gazon naturel', 'Gazon synthétique', 'Hybride', 'Sable', 'Synthétique']
list_aps_football = ['No preference', 'Football / Football en salle (Futsal)', 'Football Américain / Flag']

# =========================
# LOGIC FUNCTIONS
# =========================

def geocode_address(address: str):
    url = "https://data.geopf.fr/geocodage/search"
    params = {"q": address, "limit": 1, "returntruegeometry": "false"}
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        features = data.get("features", [])
        if not features:
            return None, None
        coordinates = features[0]["geometry"]["coordinates"]
        return coordinates[1], coordinates[0] # lat, lon
    except Exception:
        return None, None

def haversine_vectorized(lat, lon, latitudes, longitudes):
    R = 6371.0
    lat, lon = map(radians, [lat, lon])
    latitudes = np.radians(latitudes)
    longitudes = np.radians(longitudes)
    dlat = latitudes - lat
    dlon = longitudes - lon
    a = np.sin(dlat / 2) ** 2 + np.cos(lat) * np.cos(latitudes) * np.sin(dlon / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c

def apply_selection_filters(dataset_source, transport, equip_type, nature, surface, activity):
    """
    Apply filters to the dataset based on user selection.
    Handles list-like strings for transport and strict equality for others.
    """
    dataset_filtered = dataset_source.copy()
    
    # 1. Transport Filter (Handles list-like strings in Excel like ["Bus", "Train"])
    if transport != "No preference":
        # We use .str.contains to find the selected transport within the string
        # na=False ensures it doesn't crash on empty/NaN cells
        dataset_filtered = dataset_filtered[
            dataset_filtered["inst_trans_type"].astype(str).str.contains(transport, na=False)
        ]
    
    # 2. Standard Dropdown Filters (Strict equality)
    # Mapping columns to UI variables
    filters = {
        "equip_type_name": equip_type,
        "equip_nature": nature,
        "aps_name": activity
    }
    
    for column, value in filters.items():
        if value != "No preference":
            dataset_filtered = dataset_filtered[dataset_filtered[column] == value]
    
    # 3. Surface Filter (Multiselect - handles lists of values)
    if surface != "No preference" and isinstance(surface, list) and len(surface) > 0:
        # .isin() checks if the cell value matches any item in the selected list
        dataset_filtered = dataset_filtered[dataset_filtered["equip_sol"].isin(surface)]
                
    return dataset_filtered

def display_results_on_map(df_results, user_lat, user_lon):
    # Initialize Map
    m = folium.Map(location=[user_lat, user_lon], zoom_start=13, tiles='CartoDB positron')
    
    # Inject Font Awesome for icons
    header_html = '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">'
    m.get_root().header.add_child(folium.Element(header_html))

    # User Marker (Home)
    folium.Marker(
        location=[user_lat, user_lon],
        popup="<b>Your Location</b>",
        tooltip="You are here",
        icon=folium.Icon(color='red', icon='home')
    ).add_to(m)

    # Stadium Markers
    for i, (index, row) in enumerate(df_results.iterrows()):
        lat, lon = row['latitude'], row['longitude']
        ranking = i + 1
        # Google Maps Navigation URL
        nav_url = f"https://www.google.com/maps/dir/?api=1&origin={user_lat},{user_lon}&destination={lat},{lon}&travelmode=driving"

        popup_html = f"""
            <div style="font-family: Arial; width: 220px;">
                <h4 style="margin: 0 0 5px 0; color: #2c3e50;">{row['inst_nom']}</h4>
                <p style="font-size: 12px; margin: 5px 0;">
                    <b>Type:</b> {row['equip_type_name']}<br>
                    <b>Surface:</b> {row['equip_sol']}<br>
                    <b>Distance:</b> {row['distance_km']:.2f} km<br>
                </p>
                <a href="{nav_url}" target="_blank" 
                   style="background-color: #1a73e8; color: white; padding: 10px 15px; 
                          text-decoration: none; border-radius: 4px; display: block; 
                          text-align: center; font-weight: bold; font-size: 11px; margin-top: 10px;">
                   🚗 GET DIRECTIONS
                </a>
            </div>
        """
        folium.Marker(
            location=[lat, lon],
            tooltip=f"{row['inst_nom']}",
            popup=folium.Popup(popup_html, max_width=250),
            icon=plugins.BeautifyIcon(
                number=ranking,
                border_color='green' if ranking == 1 else 'blue',
                text_color='green' if ranking == 1 else 'blue',
                icon_shape='marker',
                inner_icon_style="display: flex; justify-content: center; align-items: center; margin-top: 0px; font-size: 14px; font-weight: bold;"
            )
        ).add_to(m)
    return m

# =========================
# STREAMLIT UI (SIDEBAR)
# =========================
# Custom CSS to force primary buttons to have black text
st.markdown("""
    <style>
    /* Target only primary buttons */
    .stButton > button[kind="primary"] {
        color: #000000 !important;
    }
    /* Target the hover state as well to keep it black */
    .stButton > button[kind="primary"]:hover {
        color: #000000 !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("⚽ Stadium Finder")
st.markdown("Find the nearest sports facilities based on your criteria.")

with st.sidebar:
    st.header("Search Parameters")
    
    address_input = st.text_input("Your Address:", placeholder="e.g., 10 rue de la Paix, Paris")
    
    st.subheader("Equipment Filters")
    type_choice = st.selectbox("Equipment Type:", list_type_name)
    nature_choice = st.selectbox("Environment:", list_nature)
    
    # Multiselect for Surface (replacing the complex accordion)
    surface_choice = st.multiselect("Surfaces (multiple choices possible):", 
                                    [s for s in list_sol if s != "No preference"])
    if not surface_choice:
        surface_choice = "No preference"
        
    activity_choice = st.selectbox("Activity:", list_aps_football)
    transport_choice = st.selectbox("Nearby Transport:", list_trans)
    
    st.subheader("Radius & Results")
    radius = st.slider("Search Radius (km):", 1, 50, 10)
    max_res = st.slider("Max Results:", 1, 20, 5)
    
    search_btn = st.button("🔍 Search", type="primary", use_container_width=True)

# =========================
# SESSION STATE INITIALIZATION
# =========================
# 
if 'search_performed' not in st.session_state:
    st.session_state.search_performed = False

if search_btn:
    st.session_state.search_performed = True

# =========================
# MAIN DISPLAY LOGIC
# =========================

if st.session_state.search_performed:
    if not address_input:
        st.warning("⚠️ Please enter an address to start.")
        st.session_state.search_performed = False
    else:
        with st.spinner("Finding stadiums..."):
            lat, lon = geocode_address(address_input)
            
            if lat is None:
                st.error("❌ Address not found. Please be more specific.")
            else:
                # 1. Apply Filters
                df_filtered = apply_selection_filters(stadiums, transport_choice, type_choice, 
                                                      nature_choice, surface_choice, activity_choice)
                
                if df_filtered.empty:
                    st.info("ℹ️ No stadium matches these criteria.")
                else:
                    # 2. Compute Distances
                    distances = haversine_vectorized(lat, lon, df_filtered["latitude"].values, df_filtered["longitude"].values)
                    results = (df_filtered.assign(distance_km=distances)
                               .query("distance_km <= @radius")
                               .sort_values("distance_km")
                               .head(max_res))
                    
                    if results.empty:
                        st.info(f"ℹ️ No stadium found within {radius} km.")
                    else:
                        st.success(f"✅ Found {len(results)} stadium(s)!")
                        
                        # 3. Render Map
                        map_obj = display_results_on_map(results, lat, lon)
                        st_folium(map_obj, width="100%", height=600)
                        
                        # 4. Data Details
                        with st.expander("View result details"):
                            st.dataframe(results[['inst_nom', 'equip_type_name', 'equip_sol', 'distance_km']])
else:
    st.info("👈 Set your criteria in the sidebar and click Search.")