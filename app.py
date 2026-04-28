import streamlit as st

# MUST BE THE FIRST COMMAND
st.set_page_config(page_title="Site Extents Editor", layout="wide")

import pandas as pd
import folium
from folium.plugins import Draw
from streamlit_folium import st_folium
from shapely import wkt
from shapely.geometry import shape, mapping
import io
import datetime

# Google Auth Imports
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

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
        st.text_input("Enter your Agency Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Enter your Agency Password", type="password", on_change=password_entered, key="password")
        st.error("Incorrect password")
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
st.sidebar.title(f"🌍 {agency_name} Tools")
st.sidebar.markdown("---")
st.sidebar.subheader("1. Assign Extent to Site")
st.sidebar.markdown("Select the site you are mapping. Saving a new polygon will overwrite any existing boundary.")

# Build dictionary of ALL sites: "Site Name (Site_ID)" -> "Site_ID"
site_dict = {f"{row['Site_Name']} ({row['Site_ID']})": row['Site_ID'] for idx, row in agency_df.iterrows()}

# Sort the dictionary alphabetically by Site Name for easy searching
sorted_site_dict = dict(sorted(site_dict.items()))

chosen_site_id = None
if sorted_site_dict:
    chosen_display = st.sidebar.selectbox("Select Target Site:", list(sorted_site_dict.keys()))
    chosen_site_id = sorted_site_dict[chosen_display] 

st.sidebar.markdown("---")
st.sidebar.subheader("2. Save to Drive")
st.sidebar.info("⚠️ Draw **ONE** polygon at a time, select the site above, and hit Save.")
save_btn = st.sidebar.button("💾 Update Master File", type="primary", use_container_width=True)

# ==========================================
# 5. MAIN MAP INTERFACE
# ==========================================
st.title("Humanitarian Site Extents Editor")

# Initialize Map
m = folium.Map(location=[31.4, 34.4], zoom_start=10, tiles=None)

# ADD MULTIPLE BASEMAPS
folium.TileLayer('OpenStreetMap', name='Street Map').add_to(m)
folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attr='Esri',
    name='Satellite Imagery',
    overlay=False
).add_to(m)
folium.TileLayer('cartodbpositron', name='Light Map').add_to(m)

# Add valid polygons to map (LOCKED - DEFAULT BLUE)
if features:
    fg = folium.FeatureGroup(name="Mapped Sites (Locked)")
    folium.GeoJson(
        {"type": "FeatureCollection", "features": features},
        name="Agency Sites",
        tooltip=folium.GeoJsonTooltip(fields=["Site_Name", "Site_ID"])
    ).add_to(fg)
    fg.add_to(m)

# Add Guide Pins (Blue = Valid Polygon, Red = Missing/Corrupt Polygon)
marker_fg = folium.FeatureGroup(name="📍 Site Coordinate Guides")
for idx, row in agency_df.iterrows():
    if pd.notna(row['Latitude']) and pd.notna(row['Longitude']):
        marker_color = "blue" if row['Site_ID'] in valid_site_ids else "red"
        tooltip_text = f"<b>{row.get('Site_Name', 'Unknown')}</b><br>ID: {row.get('Site_ID', 'N/A')}"
        
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            tooltip=tooltip_text,
            icon=folium.Icon(color=marker_color, icon="info-sign")
        ).add_to(marker_fg)
marker_fg.add_to(m)

# Initialize Drawing Tool (NEW SHAPES = ORANGE)
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

output = st_folium(m, use_container_width=True, height=650, returned_objects=["all_drawings"])

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
