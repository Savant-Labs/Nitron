import os
import folium
import random
import webbrowser

import pandas as pd
import geopandas as gpd

from ..logger import CustomLogger as log


class MappingEngine():

    map_center = [45, -100]

    mapfile = os.path.abspath(__file__).replace('packages\\mapping.py', 'static\\map.html')
    clusterfile = os.path.abspath(__file__).replace('packages\\mapping.py', 'static\\clusters.csv')

    @staticmethod
    def convert(df: pd.DataFrame):
        log.debug('Converting Coordinate DataFrame into Geometric Dataframe')

        geo = gpd.GeoDataFrame(
            df,
            geometry = gpd.points_from_xy(df.Longitude, df.Latitude),
            crs = 'EPSG:4326'
        )

        return geo
    
    @classmethod
    def map(cls, df: pd.DataFrame = None):
        log.state('Creating Cluster Map...')
        if df is None:
            df = pd.read_csv(cls.clusterfile)
        
        geo = cls.convert(df)

        def colormap(df: pd.DataFrame):
            clusters = df["Cluster Center"].unique()
            colors = {cluster: '#' + ''.join([random.choice("ABCDEF0123456789") for _ in range(6)]) for cluster in clusters}

            return colors

        map = folium.Map(location=cls.map_center, zoom_start=4)

        colors = colormap(geo)
        
        for idx, row in geo.iterrows():
            log.trace(f'Adding Marker for Row {idx} - {row["Account_Number"]} | {row["Account_Name"]}')
            
            tooltip = f'''
                Store: {row["Account_Number"]} | {row["Account_Name"]}
                Stores Within Range: {row["Neighbors"]}
                Avg Travel Distance: {row["Total Density"]}
                Territory: {row["Cluster Center"]}
                Territory Size: {len(df[df["Cluster Center"] == row["Cluster Center"]])}
            '''

            if (row["Latitude"], row["Longitude"]) == row["Cluster Center"]:
                background = "red"
            else:
                background = "gray"

            folium.Marker(
                location = [row['Latitude'], row['Longitude']],
                tooltip = tooltip,
                icon = folium.Icon(icon='circle', prefix='fa', icon_color=colors[row['Cluster Center']], color=background)
            ).add_to(map)
        
        centroids = geo["Cluster Center"].unique()
        for centroid in centroids:
            folium.Marker(
                location = centroid,
                popup=None,
                icon = folium.Icon(color="red", icon_color=colors[centroid], icon="circle", prefix="fa")
            ).add_to(map)

        
        log.state('Saving Cluster Map to HTML File...')
        map.save(cls.mapfile)

        log.state('Opening MapView...')
        webbrowser.open(cls.mapfile)

        
