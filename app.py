import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from streamlit_folium import st_folium
import zipfile
import tempfile
import os
import io  

TILE_OPTIONS = {
    "OpenStreetMap": {
        "tiles": "OpenStreetMap",
        "attr": None
    },
    "CartoDB Positron": {
        "tiles": "CartoDB Positron",
        "attr": None
    },
    "CartoDB Dark Matter": {
        "tiles": "CartoDB Dark Matter",
        "attr": None
    },
    "Stamen Terrain": {
        "tiles": "https://stamen-tiles.a.ssl.fastly.net/terrain/{z}/{x}/{y}.png",
        "attr": "Map tiles by Stamen Design, under CC BY 3.0. Data by OpenStreetMap, under ODbL."
    },
    "Stamen Toner": {
        "tiles": "https://stamen-tiles.a.ssl.fastly.net/toner/{z}/{x}/{y}.png",
        "attr": "Map tiles by Stamen Design, under CC BY 3.0. Data by OpenStreetMap, under ODbL."
    }
}

def load_shapefile(uploaded_files):
    """
    Extract the uploaded ZIP file to a temp folder and load the shapefile using GeoPandas.
    """
    for file in uploaded_files:
        if file.name.endswith('.zip'):
            # Create a temporary directory
            with tempfile.TemporaryDirectory() as tmpdir:
                # Save uploaded zip to temporary path
                zip_path = os.path.join(tmpdir, file.name)
                with open(zip_path, "wb") as f:
                    f.write(file.read())

                # Extract contents
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(tmpdir)

                # Find the .shp file and read it
                for root, _, files in os.walk(tmpdir):
                    for name in files:
                        if name.endswith(".shp"):
                            shp_path = os.path.join(root, name)
                            return gpd.read_file(shp_path)
    return None

def display_map(gdf, tile_layer="OpenStreetMap"):
    """
    Display the GeoDataFrame on a folium map embedded in Streamlit.
    """
    
    # Reproject geometries to WGS84 for folium (lat/lon)
    gdf = gdf.to_crs(epsg=4326)
    bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]


    tile_info = TILE_OPTIONS.get(tile_layer, TILE_OPTIONS["OpenStreetMap"])

    m = folium.Map(
    location=[(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2],
    zoom_start=6,
    tiles=tile_info["tiles"],
    attr=tile_info["attr"]
    )
    m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])


    def style_function(feature):
        return {
            "fillColor": "#228B22",
            "color": "green",
            "weight": 2,    
            "fillOpacity": 0.4,
        }

    for _, row in gdf.iterrows():
        geom = row.geometry
        props = row.to_dict()
        popup_content = "<b>Properties</b><br>"
        for k, v in props.items():
            if k != "geometry":
                popup_content += f"{k}: {v}<br>"

        if geom.geom_type in ["Polygon", "MultiPolygon"]:
            folium.GeoJson(
                geom,
                style_function=style_function,
                tooltip=popup_content,
                popup=folium.Popup(popup_content, max_width=300)
            ).add_to(m)
        elif geom.geom_type in ["Point", "MultiPoint"]:
            folium.Marker(
                location=[geom.y, geom.x],
                popup=folium.Popup(popup_content, max_width=300),
                tooltip=popup_content
            ).add_to(m)

    legend_html = """
    <div style="
    position: fixed; 
    bottom: 50px; left: 50px; width: 160px; height: auto; 
    border: 2px solid #ccc;
    z-index: 9999;
    font-size: 14px;
    background-color: #1e1e1e;
    color: white;
    opacity: 0.95;
    padding: 10px;
    border-radius: 10px;
    ">

    <b>Legend</b><br>
    <i style="background:green;opacity:0.5; width:18px; height:18px; float:left; margin-right:8px;"></i> Polygon<br>
    <i class="fa fa-map-marker fa-2x" style="color:red; margin-right:8px;"></i> Point
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    st_folium(m, use_container_width=True, height=500)

def main():

    st.set_page_config(page_title="GeoMap Dashboard", layout="wide", initial_sidebar_state="expanded")
    st.title("GeoMap Dashboard")

    with st.sidebar:
        st.image("logo.jpg", width=150)
        st.markdown("### GeoMap Dashboard")
        st.caption("Built during Internship @ CI-Metrics")

        st.write("""
        Upload a zipped shapefile to visualize polygons and points on an interactive map.
        """)

    
    st.header("Upload & Settings")
    uploaded_files = st.file_uploader(
        "Upload zipped Shapefile",
        type=["zip"],
        accept_multiple_files=True
    )

        # ───────────── Additional Sidebar Info ─────────────
    with st.sidebar.expander("📄 About this App", expanded=False):
        st.markdown("""
        **GeoMap Dashboard** is a geospatial visualization tool developed as part of a 21-week internship at **CI Metrics**.

        🔍 It allows users to:
        - Upload zipped Shapefiles
        - View attribute data and map geometries
        - Filter by column values
        - Export filtered data as GeoJSON
        - View summary statistics

        This tool helps in analyzing spatial datasets interactively.
                    
        Web App URL : https://geomapdashboard.streamlit.app/
        """)

    with st.sidebar.expander("📬 Contact", expanded=False):
        st.markdown("""
        **Shruti Patil**  
        - 📧shrutikpatil7111@gmail.com  
        - 🔗[GitHub Repository](https://github.com/ShrutiPatil7111/GeoMapDashboard)  
        - 🔗[LinkedIn](https://www.linkedin.com/in/shrutipatil71/)
        """)
    

    if uploaded_files:

        # Map Tile Selector
        map_tile = st.sidebar.selectbox(
            "Select Map Style",
            options=[
                "CartoDB Positron",
                "CartoDB Dark Matter",
                "OpenStreetMap",
                "Stamen Terrain",
                "Stamen Toner"
            ],
            index=2
        )


        gdf = load_shapefile(uploaded_files)
        if gdf is not None:

            # Show filter option
            with st.sidebar:
                st.subheader("Attribute Filtering")
                filter_column = st.selectbox("Select column to filter by:", options=gdf.columns.drop("geometry"))

                if pd.api.types.is_numeric_dtype(gdf[filter_column]):
                    min_val = float(gdf[filter_column].min())
                    max_val = float(gdf[filter_column].max())
                    
                    if min_val != max_val:
                        selected_range = st.slider(
                            f"Select range for {filter_column}",
                            min_value=min_val,
                            max_value=max_val,
                            value=(min_val, max_val)
                        )
                        filtered_gdf = gdf[(gdf[filter_column] >= selected_range[0]) & (gdf[filter_column] <= selected_range[1])]
                    else:
                        st.info(f"All values in '{filter_column}' are the same: {min_val}. Showing full data.")
                        filtered_gdf = gdf

                else:
                    unique_vals = gdf[filter_column].dropna().unique().tolist()
                    selected_vals = st.multiselect(f"Select {filter_column} values to display", unique_vals, default=unique_vals[:1])
                    filtered_gdf = gdf[gdf[filter_column].isin(selected_vals)]


            st.success("Shapefile loaded successfully!")

            st.subheader("Attribute Table")
            st.dataframe(gdf.drop(columns='geometry').head(5))

            #st.markdown("---")  # Optional: horizontal divider for clarity

            st.subheader("Map")
            display_map(filtered_gdf, tile_layer=map_tile)


            # GeoJSON export section
            st.subheader("Download Filtered Data")
            geojson_str = filtered_gdf.to_json()
            geojson_bytes = io.BytesIO(geojson_str.encode("utf-8"))

            st.download_button(
                label="📥 Download GeoJSON",
                data=geojson_bytes,
                file_name="filtered_data.geojson",
                mime="application/json"
            )

            st.subheader("Summary Statistics")
            col_count = filtered_gdf.shape[0]
            geom_types = filtered_gdf.geometry.geom_type.value_counts().to_dict()

            stats_text = f"- **Total Features Displayed:** {col_count}\n"
            for geom_type, count in geom_types.items():
                stats_text += f"- **{geom_type}s:** {count}\n"

            # If the GeoDataFrame has numeric columns, show basic stats
            numeric_cols = filtered_gdf.select_dtypes(include=["float", "int"]).drop(columns='geometry', errors='ignore')
            if not numeric_cols.empty:
                st.markdown(stats_text)
                st.write("📊 Attribute Summary")
                st.dataframe(numeric_cols.describe().transpose())
            else:
                st.markdown(stats_text)
                st.info("No numeric attributes to summarize.")


        else:
            st.error("Failed to load shapefile.")
    else:
        st.info("Awaiting shapefile upload...")




if __name__ == "__main__":
    main()
