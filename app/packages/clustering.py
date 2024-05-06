import math
import warnings

import numpy as np
import pandas as pd

from tqdm import tqdm
from dataclasses import dataclass

from ..logger import CustomLogger as log


# Remove Unnecessary Logging Outputs
warnings.filterwarnings("ignore", category=FutureWarning)


@dataclass
class Cluster:
    centre: tuple
    points: list


class EngineSetup():
    radius_mi: int = 200
    radius_km: float = radius_mi * 1.6

    min_cluster_size = 80
    max_cluster_size = 150
    
    @staticmethod
    def geodesic_distance(start: tuple, end: tuple) -> float:
        """
            Calculates the distance between two points on a 3D sphere

            Args:
                start:  Latitude/Longitude tuple for First Point (Lat, Long)
                end:    Latitude/Longitude tuple for Second Point (Lat, Long)
            
            Returns:
                Float value representing the distance between the two points in kilometers
        """

        # Earth's Radius in Kilometers (approximate)
        r = 6371.0

        lat1 = math.radians(start[0])
        lon1 = math.radians(start[1])

        lat2 = math.radians(end[0])
        lon2 = math.radians(end[1])

        xdelta = lon2 - lon1
        ydelta = lat2 - lat1

        # Haversine Formulae
        a = (math.sin(ydelta / 2) ** 2) + math.cos(lat1) * math.cos(lat2) * (math.sin(xdelta / 2) **2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

        distance = r * c

        return distance
    
    @classmethod
    def calculate_pair_wise(cls, stores: pd.DataFrame, *, start: tuple) -> list:
        """
            Builds a Distance Matrix for a single starting point

            Args:
                stores: A dataframe containing Latitude/Longitude Columns
                start:  A Latitude/Longitude tuple for the Starting Point
            
            Returns:
                2-D Array containing [start, point, distance] lists
        """

        array = []

        log.trace(f'Calculating Distance Matrix for Point: {start}')

        for _, row in stores.iterrows():
            point = (row["Latitude"], row["Longitude"])

            if point == start:
                continue

            distance = cls.geodesic_distance(start, point)
            entry = [start, point, distance]

            array.append(entry)
        
        return array
    

class ClusterEngine(EngineSetup):

    @classmethod
    def build_distance_matrix(cls, *, stores: pd.DataFrame) -> pd.DataFrame:
        """
            Calculates pair-wise distances for each point combination

            Args:
                stores: A Pandas DataFrame containing Latitude and Longitude Columns
            
            Returns:
                A dataframe containing the distance between each combination of points
        """

        log.state('Calculating Distance Matrix...')

        distances = []
        for _, row in stores.iterrows():
            distances.extend(
                cls.calculate_pair_wise(stores, start=(row["Latitude"], row["Longitude"]))
            )

        matrix = pd.DataFrame(distances, columns=["From", "To", "Distance"])

        return matrix

    @classmethod
    def relative_density(cls, *, stores: pd.DataFrame) -> pd.DataFrame:
        """
            Analyzes Distance Matrix to determine relative density per store

            Args:
                stores: A Pandas DataFrame containing Store Information
            
            Returns:
                `stores` dataframe with additional columns
        """ 

        distances = cls.build_distance_matrix(stores=stores)

        stores["Neighbors"] = np.nan
        stores["Relative Density"] = np.nan

        log.state('Analyzing Distance Matrix...')

        # Create Progress Bar
        print()
        with tqdm(total=len(stores), desc="Calculating Relative Density", colour="green", leave=True) as pbar:
            for i, row in stores.iterrows():
                point = (row["Latitude"], row["Longitude"])

                # Find Stores within Range
                neighbors = distances.loc[
                    ((distances["From"] == point) & distances["Distance"] < cls.radius_km)
                ]

                population = len(neighbors)
                avg_distance = neighbors["Distance"].mean()

                density = population / avg_distance

                stores.at[i, "Neighbors"] = population
                stores.at[i, "Relative Density"] = density

                pbar.update(1)

            pbar.close()
        
        print()

        return stores

    @classmethod
    def identify_centrepoints(cls, *, stores: pd.DataFrame) -> list:
        """
            Identifies likely candidates for cluster centrepoints by analyzing relative densities

            Args:
                stores: A dataframe containing store information and density metrics
            
            Returns:
                A list of possible centrepoints
        """

        log.state('Identifying Potential Cluster Centrepoints...')

        sorted = stores.sort_values(by=["Relative Density"], ascending=False).reset_index(drop=True)

        centrepoints = []

        # Create Progress Bar
        print()
        with tqdm(total=len(stores), desc="Analyzing Relative Density", colour="green", leave=True) as pbar:
            for i, row in sorted.iterrows():
                if row["Neighbors"] < cls.min_cluster_size:
                    pbar.update(1)

                    continue
                
                point = (row["Latitude"], row["Longitude"])

                # Calculate Distance Relative to Known Centrepoints
                proximity = [cls.geodesic_distance(point, centrepoint) for centrepoint in centrepoints]

                if row["Neighbors"] > cls.max_cluster_size:
                    existing = [distance > cls.radius_km for distance in proximity]
                else:
                    existing = [distance > (cls.radius_km * 2) for distance in proximity]
                
                if len(centrepoints) == 0 or all(existing):
                    centrepoints.append(point)
                
                pbar.update(1)
            
            pbar.close()
        
        print()
        log.debug(f'Identified {len(centrepoints)} potential clusters')

        return centrepoints

    @classmethod
    def assign_closest_cluster(cls, *, stores: pd.DataFrame, centrepoints: list) -> pd.DataFrame:
        """"
            Assigns a Centrepoint to Each Store

            Args:
                stores: A Pandas Dataframe containing store information
                centrepoints: A List of cluster centrepoints
            
            Returns:
                An updated dataframe with additional columns
        """

        log.state('Locating Closest Cluster Centrepoint...')

        stores["Cluster Centre"] = [() for _ in range(len(stores))]

        # Create a Progress Bar
        print()
        with tqdm(total=len(stores), desc="Assigning Centrepoints", colour="green", leave=True) as pbar:
            for i, row in stores.iterrows():
                point = (row["Latitude"], row["Longitude"])

                if point in centrepoints:
                    stores.at[i, "Cluster Centre"] = point
                
                else:
                    proximity = [
                        cls.geodesic_distance(point, centrepoint)
                        for centrepoint in centrepoints
                    ]

                    closest = centrepoints[proximity.index(min(proximity))]

                    stores.at[i, "Cluster Centre"] = closest
                
                pbar.update()

            pbar.close()
        
        print()
        log.debug('Cluster Assignment Completed')

        return stores
    
    @classmethod
    def align_to_center(cls, *, stores: pd.DataFrame) -> pd.DataFrame:
        """
            Re-aligns the Cluster to a Central Point

            Args:
                stores: A dataframe containing store information
            
            Returns:
                A dataframe containing store information with updated Cluster Centres
        """

        log.state('Aligning Clusters...')

        centrepoints = stores["Cluster Centre"].unique()

        clusters = {
            centrepoint: stores[stores["Cluster Centre"] == centrepoint]
            for centrepoint in centrepoints
        }

        centroids = []

        for cluster, points in clusters.items():
            centroid = (points["Latitude"].mean(), points["Longitude"].mean())
            centroids.append(centroid)
        
        stores = cls.assign_closest_cluster(stores=stores, centrepoints=centroids)

        return stores
    
    @classmethod
    def cluster(cls, *, stores: pd.DataFrame) -> pd.DataFrame:
        """
            Orchestrates the Functioning of the Cluster Engine

            Args:
                stores: A dataframe containing store information
            
            Returns:
                A dataframe containing store information and cluster assignments
        """

        densities = cls.relative_density(stores=stores)
        centrepoints = cls.identify_centrepoints(stores=densities)

        unaligned_clusters = cls.assign_closest_cluster(stores=densities, centrepoints=centrepoints)
        aligned_clusters = cls.align_to_center(stores=unaligned_clusters)

        return aligned_clusters










    

        
        


