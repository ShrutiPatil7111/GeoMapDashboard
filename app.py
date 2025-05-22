import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import zipfile
import tempfile
import os

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
    centroid = gdf.geometry.centroid.to_crs(epsg=4326).unary_union.centroid

    tile_info = TILE_OPTIONS.get(tile_layer, TILE_OPTIONS["OpenStreetMap"])

    m = folium.Map(
        location=[centroid.y, centroid.x],
        zoom_start=6,
        tiles=tile_info["tiles"],
        attr=tile_info["attr"]
    )


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
        bottom: 50px; left: 50px; width: 150px; height: 90px; 
        border:2px solid grey; z-index:9999; font-size:14px;
        background-color: white;
        opacity: 0.85;
        padding: 10px;
    ">
    <b>Legend</b><br>
    <i style="background:green;opacity:0.5; width:18px; height:18px; float:left; margin-right:8px;"></i> Polygon<br>
    <i class="fa fa-map-marker fa-2x" style="color:red; margin-right:8px;"></i> Point
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    st_folium(m, width=700, height=500)

def main():

    st.set_page_config(page_title="GeoMap Dashboard", layout="wide", initial_sidebar_state="expanded")
    st.title("GeoMap Dashboard")

    with st.sidebar:
        st.image("logo.jpg", width=150)
        st.markdown("### GeoMap Dashboard")
        st.caption("Built during Internship @ CI-Metrics")

        st.write("""
        Upload a zipped shapefile to visualize polygons and points on an interactive map.
        - The map supports zooming and panning.
        - Click on features to view their attributes.
        """)

    
    st.header("Upload & Settings")
    uploaded_files = st.file_uploader(
        "Upload zipped Shapefile",
        type=["zip"],
        accept_multiple_files=True
    )
        

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
            st.success("Shapefile loaded successfully!")
            col1, col2 = st.columns([1, 2])

            with col1:
                st.subheader("Attribute Table")
                st.dataframe(gdf.drop(columns='geometry').head(10))

            with col2:
                st.subheader("Map")
                display_map(gdf, tile_layer=map_tile)

        else:
            st.error("Failed to load shapefile.")
    else:
        st.info("Awaiting shapefile upload...")



if __name__ == "__main__":
    main()
