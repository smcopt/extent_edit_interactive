import streamlit as st

# MUST BE THE FIRST COMMAND
st.set_page_config(
    page_title="CCCM Site Extents Editor (Interactive)",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

import pandas as pd
import folium
from folium.plugins import Draw
from streamlit_folium import st_folium
from shapely import wkt
from shapely.geometry import shape, mapping
import io
import datetime
import re

# Google Auth Imports
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# ==========================================
# BRANDING: CCCM Cluster Design System
# ==========================================
LOGO_URL = "https://raw.githubusercontent.com/smcopt/extent_edit/refs/heads/main/CountryLogo_Palestine_V01.png"

# CCCM Primary Colors
BLUE_SAPPHIRE = "#1B657C"
BALTIC_SEA = "#2C2C2C"
BURNT_SIENNA = "#EC6B4D"

# CCCM Secondary Colors
ECRU_WHITE = "#F5F3E8"
MOSS_GREEN = "#BBDFBB"
MOONSTONE_BLUE = "#6FC5BC"
STEEL_BLUE = "#4595AD"

# ==========================================
# INTERACTIVE: Click-to-Select Session State
# ==========================================
if "clicked_site_id" not in st.session_state:
    st.session_state["clicked_site_id"] = None
if "map_center" not in st.session_state:
    st.session_state["map_center"] = [31.4, 34.4]
if "map_zoom" not in st.session_state:
    st.session_state["map_zoom"] = 10

# ==========================================
# CUSTOM CSS — CCCM CLUSTER BRANDING
# ==========================================
st.markdown(f"""
<style>
    /* ── Import Inter (body) + Montserrat (headings) ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@200;400;600;700&family=Montserrat:wght@400;600;700;800&display=swap');

    /* ── Global resets ── */
    html, body, [class*="css"] {{
        font-family: 'Inter', sans-serif;
        color: {BALTIC_SEA};
    }}

    /* ── Montserrat for all headings ── */
    h1, h2, h3, h4, h5, h6 {{
        font-family: 'Montserrat', sans-serif !important;
    }}

    /* ── Hide default Streamlit chrome for cleaner look ── */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}

    /* ── Reduce default padding to maximize map space ── */
    .block-container {{
        padding-top: 3.5rem;
        padding-bottom: 0rem;
        padding-left: 1.5rem;
        padding-right: 1.5rem;
    }}

    /* ── Sidebar branding ── */
    section[data-testid="stSidebar"] {{
        background-color: {BLUE_SAPPHIRE};
        border-right: 3px solid {BURNT_SIENNA};
    }}

    section[data-testid="stSidebar"] > div:first-child {{
        padding-top: 0.5rem;
    }}

    section[data-testid="stSidebar"] * {{
        color: {ECRU_WHITE} !important;
    }}

    section[data-testid="stSidebar"] .stMarkdown p {{
        color: {ECRU_WHITE} !important;
        font-size: 0.9rem;
    }}

    /* Sidebar title */
    section[data-testid="stSidebar"] h1 {{
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        color: white !important;
        font-size: 1.3rem;
        letter-spacing: 0.02em;
    }}

    /* Sidebar subheaders */
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {{
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        color: {MOONSTONE_BLUE} !important;
        font-size: 1rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.3rem;
    }}

    /* Sidebar dividers */
    section[data-testid="stSidebar"] hr {{
        border-color: rgba(111, 197, 188, 0.3);
        margin: 0.8rem 0;
    }}

    /* Sidebar selectbox */
    section[data-testid="stSidebar"] .stSelectbox label {{
        color: {ECRU_WHITE} !important;
        font-weight: 600;
        font-size: 0.85rem;
    }}

    section[data-testid="stSidebar"] .stSelectbox > div > div {{
        background-color: rgba(255,255,255,0.1);
        border: 1px solid rgba(111, 197, 188, 0.4);
        border-radius: 6px;
        color: {ECRU_WHITE} !important;
    }}

    /* Sidebar search input */
    section[data-testid="stSidebar"] .stTextInput label {{
        color: {ECRU_WHITE} !important;
        font-weight: 600;
        font-size: 0.85rem;
    }}

    section[data-testid="stSidebar"] .stTextInput > div > div > input {{
        background-color: rgba(255,255,255,0.1);
        border: 1px solid rgba(111, 197, 188, 0.4);
        border-radius: 6px;
        color: {ECRU_WHITE} !important;
        font-family: 'Inter', sans-serif;
    }}

    section[data-testid="stSidebar"] .stTextInput > div > div > input::placeholder {{
        color: rgba(245, 243, 232, 0.5) !important;
    }}

    section[data-testid="stSidebar"] .stTextInput > div > div > input:focus {{
        border-color: {MOONSTONE_BLUE};
        box-shadow: 0 0 0 2px rgba(111, 197, 188, 0.25);
    }}

    /* Primary button (Save) */
    section[data-testid="stSidebar"] .stButton > button[kind="primary"] {{
        background-color: {BURNT_SIENNA} !important;
        color: white !important;
        border: none;
        border-radius: 6px;
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 0.95rem;
        letter-spacing: 0.03em;
        padding: 0.6rem 1.2rem;
        transition: all 0.2s ease;
        box-shadow: 0 2px 8px rgba(236, 107, 77, 0.3);
    }}

    section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {{
        background-color: #d4583b !important;
        box-shadow: 0 4px 14px rgba(236, 107, 77, 0.45);
        transform: translateY(-1px);
    }}

    /* Secondary button (Remove) */
    section[data-testid="stSidebar"] .stButton > button[kind="secondary"] {{
        background-color: transparent !important;
        color: {BURNT_SIENNA} !important;
        border: 1.5px solid {BURNT_SIENNA} !important;
        border-radius: 6px;
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 0.85rem;
        padding: 0.45rem 1rem;
        transition: all 0.2s ease;
    }}

    section[data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover {{
        background-color: rgba(236, 107, 77, 0.15) !important;
    }}

    section[data-testid="stSidebar"] .stButton > button[kind="secondary"]:disabled {{
        opacity: 0.35;
        border-color: rgba(236, 107, 77, 0.3) !important;
        color: rgba(236, 107, 77, 0.4) !important;
    }}

    /* Sidebar checkbox */
    section[data-testid="stSidebar"] .stCheckbox label span {{
        color: {ECRU_WHITE} !important;
        font-size: 0.8rem;
    }}

    /* Sidebar info/alert boxes */
    section[data-testid="stSidebar"] .stAlert {{
        background-color: rgba(69, 149, 173, 0.2);
        border: 1px solid rgba(111, 197, 188, 0.3);
        border-radius: 6px;
        color: {ECRU_WHITE} !important;
    }}

    /* ── Main area heading ── */
    .main h1 {{
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        color: {BLUE_SAPPHIRE};
        font-size: 1.5rem;
        letter-spacing: 0.01em;
        margin-bottom: 0.2rem;
    }}

    /* ── Password input styling ── */
    .stTextInput > div > div > input {{
        border: 2px solid {STEEL_BLUE};
        border-radius: 6px;
        font-family: 'Inter', sans-serif;
        padding: 0.6rem 0.8rem;
    }}

    .stTextInput > div > div > input:focus {{
        border-color: {BLUE_SAPPHIRE};
        box-shadow: 0 0 0 2px rgba(27, 101, 124, 0.2);
    }}

    /* ── Map iframe — maximize height ── */
    iframe {{
        border-radius: 8px;
        border: 2px solid {STEEL_BLUE};
        box-shadow: 0 2px 12px rgba(27, 101, 124, 0.12);
    }}

    /* ── Success/Error/Warning messages ── */
    .stSuccess {{
        background-color: rgba(187, 223, 187, 0.2);
        border-left: 4px solid {MOSS_GREEN};
    }}

    .stError {{
        border-left: 4px solid {BURNT_SIENNA};
    }}

    /* ── Scrollbar styling ── */
    ::-webkit-scrollbar {{
        width: 6px;
    }}
    ::-webkit-scrollbar-track {{
        background: {ECRU_WHITE};
    }}
    ::-webkit-scrollbar-thumb {{
        background: {STEEL_BLUE};
        border-radius: 3px;
    }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. AUTHENTICATION
# ==========================================
def check_password():
    def password_entered():
        for agency, pwd in st.secrets["passwords"].items():
            if st.session_state["password"] == pwd:
                st.session_state["password_correct"] = True
                st.session_state["agency"] = agency
                del st.session_state["password"]
                return
        st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Branded login screen
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown(f"""
            <div style="text-align:center; padding: 2rem 0 1rem 0;">
                <img src="{LOGO_URL}" style="height:90px; margin-bottom:1rem;" alt="CCCM Cluster Logo"/>
                <h2 style="font-family:'Inter',sans-serif; font-weight:700; color:{BLUE_SAPPHIRE}; margin:0;">
                    Site Extents Editor
                </h2>
                <p style="font-family:'Inter',sans-serif; color:{STEEL_BLUE}; font-size:0.95rem; margin-top:0.3rem;">
                    Enter your agency password to continue
                </p>
            </div>
            """, unsafe_allow_html=True)
            st.text_input("Agency Password", type="password", on_change=password_entered, key="password", label_visibility="collapsed")
        return False
    elif not st.session_state["password_correct"]:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown(f"""
            <div style="text-align:center; padding: 2rem 0 1rem 0;">
                <img src="{LOGO_URL}" style="height:90px; margin-bottom:1rem;" alt="CCCM Cluster Logo"/>
                <h2 style="font-family:'Inter',sans-serif; font-weight:700; color:{BLUE_SAPPHIRE}; margin:0;">
                    Site Extents Editor
                </h2>
                <p style="font-family:'Inter',sans-serif; color:{STEEL_BLUE}; font-size:0.95rem; margin-top:0.3rem;">
                    Enter your agency password to continue
                </p>
            </div>
            """, unsafe_allow_html=True)
            st.text_input("Agency Password", type="password", on_change=password_entered, key="password", label_visibility="collapsed")
            st.error("Incorrect password. Please try again.")
        return False
    return True

if not check_password():
    st.stop()

# Replaces underscores with spaces in case secrets use "HEKS_EPER" format
agency_name = st.session_state["agency"].replace("_", " ")

# ==========================================
# 2. GOOGLE DRIVE SETUP
# ==========================================
@st.cache_resource
def get_gdrive_service():
    creds = Credentials(
        token=None,
        refresh_token=st.secrets["drive_oauth"]["refresh_token"],
        client_id=st.secrets["drive_oauth"]["client_id"],
        client_secret=st.secrets["drive_oauth"]["client_secret"],
        token_uri="https://oauth2.googleapis.com/token"
    )
    return build('drive', 'v3', credentials=creds)

drive_service = get_gdrive_service()

# ==========================================
# 3. DATA LOADING & WKT VALIDATION
# ==========================================
@st.cache_data
def load_data(file_id):
    request = drive_service.files().get_media(fileId=file_id)
    file_content = request.execute()
    return pd.read_csv(io.BytesIO(file_content))

try:
    master_df = load_data(st.secrets["drive"]["master_file_id"])
except Exception as e:
    st.error(f"Could not load Master File. Error: {e}")
    st.stop()

agency_df = master_df[master_df['Final_Agency'] == agency_name].copy()

# Test all WKTs. Separate valid ones from corrupt/missing ones.
valid_site_ids = []
features = []

for idx, row in agency_df.iterrows():
    if pd.notna(row['WKT']):
        try:
            geom = wkt.loads(str(row['WKT']))
            feature = {
                "type": "Feature",
                "properties": {"Site_Name": row.get("Site_Name", ""), "Site_ID": row.get("Site_ID", "")},
                "geometry": mapping(geom)
            }
            features.append(feature)
            valid_site_ids.append(row['Site_ID'])
        except Exception:
            pass

# ==========================================
# 4. SIDEBAR UI (ATTRIBUTES & SAVING)
# ==========================================

# Sidebar logo and agency header
st.sidebar.markdown(f"""
<div style="
    text-align:center;
    padding: 0.8rem 1rem;
    margin: -1rem -1rem 0.6rem -1rem;
    background: white;
    border-bottom: 3px solid {BURNT_SIENNA};
">
    <img src="{LOGO_URL}" style="height:70px;" alt="CCCM Cluster Logo"/>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown(f"""
<div style="text-align:center; margin-bottom:0.3rem;">
    <h2 style="font-family:'Inter',sans-serif; font-weight:700; color:white !important; font-size:1.4rem; margin:0; letter-spacing:0.02em;">
        {agency_name}
    </h2>
</div>
""", unsafe_allow_html=True)

# Stats bar
total_sites = len(agency_df)
mapped_sites = len(valid_site_ids)
unmapped_sites = total_sites - mapped_sites

st.sidebar.markdown(f"""
<div style="
    display: flex;
    justify-content: space-around;
    background: rgba(255,255,255,0.08);
    border-radius: 8px;
    padding: 0.6rem 0.4rem;
    margin: 0.4rem 0 0.6rem 0;
    border: 1px solid rgba(111, 197, 188, 0.2);
">
    <div style="text-align:center;">
        <div style="font-size:1.3rem; font-weight:700; color:white;">{total_sites}</div>
        <div style="font-size:0.65rem; text-transform:uppercase; letter-spacing:0.05em; color:{MOONSTONE_BLUE};">Total</div>
    </div>
    <div style="text-align:center;">
        <div style="font-size:1.3rem; font-weight:700; color:{MOSS_GREEN};">{mapped_sites}</div>
        <div style="font-size:0.65rem; text-transform:uppercase; letter-spacing:0.05em; color:{MOONSTONE_BLUE};">Mapped</div>
    </div>
    <div style="text-align:center;">
        <div style="font-size:1.3rem; font-weight:700; color:{BURNT_SIENNA};">{unmapped_sites}</div>
        <div style="font-size:0.65rem; text-transform:uppercase; letter-spacing:0.05em; color:{MOONSTONE_BLUE};">Pending</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.subheader("1. Assign Extent")
st.sidebar.markdown("Select the site you are mapping. Drawing a new polygon will overwrite any existing boundary.")

# Build dictionary of ALL sites: "Site Name (Site_ID)" -> "Site_ID"
site_dict = {f"{row['Site_Name']} ({row['Site_ID']})": row['Site_ID'] for idx, row in agency_df.iterrows()}

# Build mapped/unmapped lookup
site_status_map = {}
for idx, row in agency_df.iterrows():
    display_key = f"{row['Site_Name']} ({row['Site_ID']})"
    site_status_map[display_key] = row['Site_ID'] in valid_site_ids

# Sort the dictionary alphabetically
sorted_site_dict = dict(sorted(site_dict.items()))

chosen_site_id = None
if sorted_site_dict:
    # Compact filter dropdown
    filter_mode = st.sidebar.selectbox(
        "Show:",
        ["All Sites", "Unmapped Only", "Mapped Only"],
        key="filter_mode"
    )

    # Apply filter mode
    if filter_mode == "Unmapped Only":
        mode_filtered = {k: v for k, v in sorted_site_dict.items() if not site_status_map.get(k, False)}
    elif filter_mode == "Mapped Only":
        mode_filtered = {k: v for k, v in sorted_site_dict.items() if site_status_map.get(k, False)}
    else:
        mode_filtered = sorted_site_dict

    # Search filter
    search_query = st.sidebar.text_input("🔍 Search Sites:", placeholder="Type site name or ID...", key="site_search")

    if search_query:
        filtered_sites = {k: v for k, v in mode_filtered.items() if search_query.lower() in k.lower()}
    else:
        filtered_sites = mode_filtered

    if filtered_sites:
        # Determine default index from map click
        site_keys = list(filtered_sites.keys())
        default_idx = 0
        clicked_sid = st.session_state.get("clicked_site_id")
        map_selected = False
        if clicked_sid:
            # Find the display key that matches the clicked Site_ID
            for i, (display_key, sid) in enumerate(filtered_sites.items()):
                if sid == clicked_sid:
                    default_idx = i
                    map_selected = True
                    break

        chosen_display = st.sidebar.selectbox(
            f"Select Target Site ({len(filtered_sites)} shown):",
            site_keys,
            index=default_idx
        )
        chosen_site_id = filtered_sites[chosen_display]

        # Update clicked_site_id to match dropdown (in case user changes manually)
        st.session_state["clicked_site_id"] = chosen_site_id

        # Show "selected from map" indicator
        if map_selected and chosen_site_id == clicked_sid:
            st.sidebar.markdown(f"""
            <div style="
                background: rgba(111, 197, 188, 0.15);
                border: 1px solid rgba(111, 197, 188, 0.3);
                border-radius: 4px;
                padding: 0.3rem 0.5rem;
                margin: 0.2rem 0 0.4rem 0;
                font-size: 0.73rem;
                color: {MOONSTONE_BLUE};
                text-align: center;
            ">
                📍 Selected from map click
            </div>
            """, unsafe_allow_html=True)

        # ── Status indicator for selected site ──
        is_mapped = site_status_map.get(chosen_display, False)
        if is_mapped:
            st.sidebar.markdown(f"""
            <div style="
                background: rgba(187, 223, 187, 0.15);
                border: 1px solid rgba(187, 223, 187, 0.4);
                border-left: 3px solid {MOSS_GREEN};
                border-radius: 6px;
                padding: 0.5rem 0.7rem;
                margin: 0.4rem 0 0.2rem 0;
                font-size: 0.8rem;
            ">
                <span style="color:{MOSS_GREEN};">●</span>
                <b style="color:white;">Already mapped</b>
                <span style="color:rgba(245,243,232,0.7); display:block; font-size:0.73rem; margin-top:0.15rem;">
                    Drawing a new polygon will <b style="color:{BURNT_SIENNA};">replace</b> the existing boundary.
                    The old extent is backed up automatically before overwriting.
                </span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.sidebar.markdown(f"""
            <div style="
                background: rgba(236, 107, 77, 0.12);
                border: 1px solid rgba(236, 107, 77, 0.3);
                border-left: 3px solid {BURNT_SIENNA};
                border-radius: 6px;
                padding: 0.5rem 0.7rem;
                margin: 0.4rem 0 0.2rem 0;
                font-size: 0.8rem;
            ">
                <span style="color:{BURNT_SIENNA};">●</span>
                <b style="color:white;">No extent yet</b>
                <span style="color:rgba(245,243,232,0.7); display:block; font-size:0.73rem; margin-top:0.15rem;">
                    Use the red pin on the map as a guide to draw this site's boundary.
                </span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.sidebar.warning(f"No sites matching \"{search_query}\"" if search_query else f"No {filter_mode.lower()} sites.")
        chosen_site_id = None

st.sidebar.markdown("---")
st.sidebar.subheader("2. Save to Drive")
st.sidebar.info("Draw **one** polygon at a time, select the site above, and hit Save.")
save_btn = st.sidebar.button("💾 Update Master File", type="primary", use_container_width=True)

# ── 3. Remove Extent ──
st.sidebar.markdown("---")
st.sidebar.subheader("3. Remove Extent")

# Initialize remove session state
if "remove_confirmed" not in st.session_state:
    st.session_state["remove_confirmed"] = False
if "remove_triggered" not in st.session_state:
    st.session_state["remove_triggered"] = False

# Only show remove option if a mapped site is selected
if chosen_site_id and chosen_site_id in valid_site_ids:
    st.sidebar.markdown(f"""
    <div style="
        font-size:0.8rem;
        color: rgba(245,243,232,0.7);
        margin-bottom: 0.4rem;
    ">
        Clear the boundary for the selected site. This removes its WKT from the master file.
    </div>
    """, unsafe_allow_html=True)

    def on_confirm_change():
        st.session_state["remove_confirmed"] = st.session_state["confirm_remove_cb"]

    st.sidebar.checkbox(
        "I confirm I want to remove this extent",
        key="confirm_remove_cb",
        value=st.session_state["remove_confirmed"],
        on_change=on_confirm_change
    )

    def on_remove_click():
        st.session_state["remove_triggered"] = True

    st.sidebar.button(
        "🗑️ Remove Site Extent",
        type="secondary",
        use_container_width=True,
        disabled=not st.session_state["remove_confirmed"],
        on_click=on_remove_click
    )
else:
    # Reset states if site changes to unmapped
    st.session_state["remove_confirmed"] = False
    st.session_state["remove_triggered"] = False
    st.sidebar.markdown(f"""
    <div style="
        font-size:0.8rem;
        color: rgba(245,243,232,0.4);
        font-style: italic;
    ">
        Select a mapped site above to enable removal.
    </div>
    """, unsafe_allow_html=True)

# Sidebar footer
st.sidebar.markdown("---")
st.sidebar.markdown(f"""
<div style="text-align:center; padding: 0.5rem 0; opacity:0.6;">
    <p style="font-size:0.7rem; margin:0;">CCCM Cluster — Site Management</p>
    <p style="font-size:0.65rem; margin:0.1rem 0 0 0;">Supporting displaced communities</p>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 5. MAIN MAP INTERFACE
# ==========================================

# Compact branded header above the map
st.markdown(f"""
<div style="
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.3rem 0 0.5rem 0;
">
    <div style="display:flex; align-items:center; gap:0.6rem;">
        <h1 style="margin:0; padding:0;">Site Extents Editor <span style="font-size:0.6rem; color:{BURNT_SIENNA}; vertical-align:super;">INTERACTIVE</span></h1>
    </div>
    <div style="display:flex; align-items:center; gap:1rem;">
        <span style="
            display:inline-flex; align-items:center; gap:0.3rem;
            font-size:0.75rem; color:{BALTIC_SEA};
        ">
            <span style="width:10px;height:10px;border-radius:50%;background:blue;display:inline-block;"></span>
            Mapped
        </span>
        <span style="
            display:inline-flex; align-items:center; gap:0.3rem;
            font-size:0.75rem; color:{BALTIC_SEA};
        ">
            <span style="width:10px;height:10px;border-radius:50%;background:red;display:inline-block;"></span>
            Unmapped
        </span>
        <span style="
            display:inline-flex; align-items:center; gap:0.3rem;
            font-size:0.75rem; color:{BALTIC_SEA};
        ">
            <span style="width:10px;height:10px;border-radius:50%;background:orange;display:inline-block;"></span>
            New Drawing
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

# Initialize Map (persisted center & zoom)
m = folium.Map(
    location=st.session_state["map_center"],
    zoom_start=st.session_state["map_zoom"],
    tiles=None
)

# ADD MULTIPLE BASEMAPS
folium.TileLayer('OpenStreetMap', name='Street Map').add_to(m)
folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attr='Esri',
    name='Satellite Imagery',
    overlay=False
).add_to(m)
folium.TileLayer('cartodbpositron', name='Light Map').add_to(m)

# Determine which site IDs to show on the map based on filter
filter_mode = st.session_state.get("filter_mode", "All Sites")

if filter_mode == "Unmapped Only":
    visible_site_ids = set(agency_df['Site_ID']) - set(valid_site_ids)
elif filter_mode == "Mapped Only":
    visible_site_ids = set(valid_site_ids)
else:
    visible_site_ids = set(agency_df['Site_ID'])

# Add valid polygons to map (LOCKED - DEFAULT BLUE — colors NOT changed per requirement)
# Only show polygons for sites in the visible set
filtered_features = [f for f in features if f["properties"].get("Site_ID") in visible_site_ids]
if filtered_features:
    fg = folium.FeatureGroup(name="Mapped Sites (Locked)")

    def style_function(feature):
        """Style polygons — highlight the clicked one."""
        site_id = feature["properties"].get("Site_ID", "")
        if site_id == st.session_state.get("clicked_site_id"):
            return {
                "color": "#EC6B4D",
                "weight": 3,
                "fillColor": "#EC6B4D",
                "fillOpacity": 0.25,
            }
        return {
            "color": "#3388ff",
            "weight": 2,
            "fillColor": "#3388ff",
            "fillOpacity": 0.2,
        }

    folium.GeoJson(
        {"type": "FeatureCollection", "features": filtered_features},
        name="Agency Sites",
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(fields=["Site_Name", "Site_ID"]),
        popup=folium.GeoJsonPopup(fields=["Site_Name", "Site_ID"], labels=True)
    ).add_to(fg)
    fg.add_to(m)

# Add Guide Pins (Blue = Valid Polygon, Red = Missing/Corrupt Polygon — colors NOT changed)
# Only show pins for sites in the visible set
marker_fg = folium.FeatureGroup(name="📍 Site Coordinate Guides")
for idx, row in agency_df.iterrows():
    if row['Site_ID'] not in visible_site_ids:
        continue
    if pd.notna(row['Latitude']) and pd.notna(row['Longitude']):
        marker_color = "blue" if row['Site_ID'] in valid_site_ids else "red"
        tooltip_text = f"<b>{row.get('Site_Name', 'Unknown')}</b><br>ID: {row.get('Site_ID', 'N/A')}"
        popup_text = f"<b>{row.get('Site_Name', 'Unknown')}</b><br>Site_ID: {row.get('Site_ID', 'N/A')}"

        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            tooltip=tooltip_text,
            popup=folium.Popup(popup_text, max_width=250),
            icon=folium.Icon(color=marker_color, icon="info-sign")
        ).add_to(marker_fg)
marker_fg.add_to(m)

# Initialize Drawing Tool (NEW SHAPES = ORANGE — colors NOT changed per requirement)
draw = Draw(
    export=False,
    position='topleft',
    draw_options={
        'polygon': {
            'shapeOptions': {
                'color': 'orange',
                'fillColor': 'orange',
                'fillOpacity': 0.5
            }
        },
        'rectangle': {
            'shapeOptions': {
                'color': 'orange',
                'fillColor': 'orange',
                'fillOpacity': 0.5
            }
        },
        'polyline': False,
        'circle': False,
        'circlemarker': False,
        'marker': False
    },
    edit_options={'edit': True, 'remove': True}
)
draw.add_to(m)

folium.LayerControl().add_to(m)

# Render map with maximum height
# NOTE: Only return click data and drawings — NOT zoom/center
# Returning zoom/center causes reruns on every pan/zoom (the pulsing issue)
output = st_folium(
    m,
    use_container_width=True,
    height=720,
    returned_objects=["all_drawings", "last_object_clicked_tooltip", "last_object_clicked_popup", "last_clicked"],
    key="main_map"
)

# ==========================================
# INTERACTIVE: Parse click to auto-select site
# ==========================================
def parse_site_id_from_click(output):
    """Extract Site_ID from tooltip or popup returned by st_folium."""
    # Try tooltip first (from GeoJsonTooltip: "Site_Name: xxx\nSite_ID: yyy")
    tooltip = output.get("last_object_clicked_tooltip")
    if tooltip and isinstance(tooltip, str):
        match = re.search(r'Site_ID[:\s]+([A-Za-z0-9_-]+)', tooltip)
        if match:
            return match.group(1)
        match = re.search(r'ID:\s*([A-Za-z0-9_-]+)', tooltip)
        if match:
            return match.group(1)

    # Try popup (from GeoJsonPopup: similar format)
    popup = output.get("last_object_clicked_popup")
    if popup and isinstance(popup, str):
        match = re.search(r'Site_ID[:\s]+([A-Za-z0-9_-]+)', popup)
        if match:
            return match.group(1)
        match = re.search(r'ID:\s*([A-Za-z0-9_-]+)', popup)
        if match:
            return match.group(1)

    return None

clicked_id = parse_site_id_from_click(output)
if clicked_id and clicked_id != st.session_state.get("clicked_site_id"):
    if clicked_id in set(agency_df['Site_ID']):
        st.session_state["clicked_site_id"] = clicked_id
        # Capture the clicked location as the new map center to preserve view
        last_clicked = output.get("last_clicked")
        if last_clicked:
            if isinstance(last_clicked, dict):
                st.session_state["map_center"] = [last_clicked.get("lat", 31.4), last_clicked.get("lng", 34.4)]
            elif isinstance(last_clicked, (list, tuple)) and len(last_clicked) >= 2:
                st.session_state["map_center"] = list(last_clicked)
            # Preserve a close zoom level when clicking a site
            st.session_state["map_zoom"] = max(st.session_state.get("map_zoom", 10), 13)
        st.rerun()

# ==========================================
# 6. SAVE LOGIC & AUTOMATED BACKUP
# ==========================================
if save_btn:
    drawings = output.get("all_drawings")
    if drawings and len(drawings) > 0:

        if not chosen_site_id:
            st.sidebar.error("Please select a valid site from the dropdown first.")
            st.stop()

        geom = shape(drawings[-1]["geometry"])
        wkt_string = geom.wkt

        updated_df = master_df.copy()
        folder_id = st.secrets["drive"]["folder_id"]

        with st.spinner("Creating backup and updating Drive..."):
            try:
                # --- 1. AUTOMATED ROLLING BACKUP ---
                backup_buffer = io.BytesIO()
                master_df.to_csv(backup_buffer, index=False)
                backup_buffer.seek(0)
                backup_media = MediaIoBaseUpload(backup_buffer, mimetype='text/csv', resumable=True)

                query = f"name='Site_Extents_BACKUP.csv' and '{folder_id}' in parents and trashed=false"
                results = drive_service.files().list(q=query, spaces='drive', fields='files(id)').execute()
                files = results.get('files', [])

                if files:
                    drive_service.files().update(fileId=files[0]['id'], media_body=backup_media).execute()
                else:
                    file_metadata = {'name': 'Site_Extents_BACKUP.csv', 'parents': [folder_id]}
                    drive_service.files().create(body=file_metadata, media_body=backup_media, fields='id').execute()

                # --- 2. INJECT/OVERWRITE WKT INTO THE EXACT ROW ---
                row_idx = updated_df.index[updated_df['Site_ID'] == chosen_site_id].tolist()

                if row_idx:
                    updated_df.at[row_idx[0], 'WKT'] = wkt_string
                else:
                    st.sidebar.error("Error: Could not locate the Site ID in the master database.")
                    st.stop()

                # --- 3. UPLOAD NEW MASTER FILE ---
                csv_buffer = io.BytesIO()
                updated_df.to_csv(csv_buffer, index=False)
                csv_buffer.seek(0)

                media = MediaIoBaseUpload(csv_buffer, mimetype='text/csv', resumable=True)
                drive_service.files().update(
                    fileId=st.secrets["drive"]["master_file_id"],
                    media_body=media
                ).execute()

                st.cache_data.clear()
                st.sidebar.success("✅ Backup created & Site Extent Updated!")
                st.rerun()

            except Exception as e:
                st.sidebar.error(f"Error saving: {e}")
    else:
        st.sidebar.warning("You must draw a polygon on the map before saving.")

# ==========================================
# 7. REMOVE EXTENT LOGIC
# ==========================================
if st.session_state.get("remove_triggered") and st.session_state.get("remove_confirmed") and chosen_site_id:
    # Reset trigger immediately
    st.session_state["remove_triggered"] = False
    st.session_state["remove_confirmed"] = False

    updated_df = master_df.copy()
    folder_id = st.secrets["drive"]["folder_id"]

    with st.spinner("Creating backup and removing extent..."):
        try:
            # --- 1. AUTOMATED ROLLING BACKUP ---
            backup_buffer = io.BytesIO()
            master_df.to_csv(backup_buffer, index=False)
            backup_buffer.seek(0)
            backup_media = MediaIoBaseUpload(backup_buffer, mimetype='text/csv', resumable=True)

            query = f"name='Site_Extents_BACKUP.csv' and '{folder_id}' in parents and trashed=false"
            results = drive_service.files().list(q=query, spaces='drive', fields='files(id)').execute()
            files = results.get('files', [])

            if files:
                drive_service.files().update(fileId=files[0]['id'], media_body=backup_media).execute()
            else:
                file_metadata = {'name': 'Site_Extents_BACKUP.csv', 'parents': [folder_id]}
                drive_service.files().create(body=file_metadata, media_body=backup_media, fields='id').execute()

            # --- 2. CLEAR WKT FOR THE SELECTED SITE ---
            row_idx = updated_df.index[updated_df['Site_ID'] == chosen_site_id].tolist()

            if row_idx:
                updated_df.at[row_idx[0], 'WKT'] = ""
            else:
                st.sidebar.error("Error: Could not locate the Site ID in the master database.")
                st.stop()

            # --- 3. UPLOAD UPDATED MASTER FILE ---
            csv_buffer = io.BytesIO()
            updated_df.to_csv(csv_buffer, index=False)
            csv_buffer.seek(0)

            media = MediaIoBaseUpload(csv_buffer, mimetype='text/csv', resumable=True)
            drive_service.files().update(
                fileId=st.secrets["drive"]["master_file_id"],
                media_body=media
            ).execute()

            st.cache_data.clear()
            st.sidebar.success("✅ Backup created & Site Extent Removed!")
            st.rerun()

        except Exception as e:
            st.sidebar.error(f"Error removing extent: {e}")
