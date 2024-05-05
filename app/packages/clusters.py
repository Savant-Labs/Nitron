import math
import warnings

import numpy as np
import pandas as pd

from tqdm import tqdm

from ..logger import CustomLogger as log


warnings.filterwarnings("ignore", category=FutureWarning)


class Cluster():

    ''' 
        Insert DocString Here
    
    '''

    def __init__(self, id: int = 0, *, centre: tuple):
        self.id = id
        self.points = []
        self.centre = centre

        log.trace(f'Initializing New Cluster {id} with Centre: {centre}')
        self.assign(centre)     

    def assign(self, point: tuple):
        self.points.append(point)

        log.trace(f'Assigning Point {point} to Cluster {self.id}')

    def unassign(self, point: tuple):
        try:
            index = self.points.index(point)
            self.points.pop(index)

        except ValueError:
            log.issue(f'Unable to Remove Point {point} from Cluster {self.id} - Point Not In Cluster')
        except IndexError:
            log.issue(f'Unable to Remove Point {point} from Cluster {self.id} - Invalid Cluster Index')
        
        else:
            log.trace(f'Unassigned Point {point} from Cluster {self.id}')
        
        return


class ClusterEngine():

    _radius = 200
    radius = _radius * 1.6

    min_size = 80
    max_size = 150
       

    @staticmethod
    def haversine(a: list, b: list):
        r = 6371.0

        ay = math.radians(a[0])
        ax = math.radians(a[1])

        by = math.radians(b[0])
        bx = math.radians(b[1])

        xdelta = bx - ax
        ydelta = by - ay

        z = (math.sin(ydelta / 2) ** 2) + math.cos(ay) * math.cos(by) * (math.sin(xdelta / 2) ** 2)
        d = 2 * math.atan2(math.sqrt(z), math.sqrt(1 - z))

        distance = r * d

        return distance

    @staticmethod
    def distanceToCenter(point: tuple, center: tuple, distances: pd.DataFrame):
        row = distances.loc[
            ((distances["From"] == point) & (distances["To"] == center)),
            "Distance"
        ]

        try:
            return row.values[0]
        except IndexError:
            pass

    
    @classmethod
    def distanceMatrix(cls, df: pd.DataFrame):
        dmatrix = []

        log.state('Initializing Distance Matrix...')
        total = (len(df) ** 2) - len(df)
        print()

        with tqdm(total=total, desc="Calculating Distance Matrix", colour="green", leave=True) as pbar:
            for start, startrow in df.iterrows():
                a = (startrow["Latitude"], startrow["Longitude"])

                log.trace(f'Building Distance Matrix for Point {a}')
                for end, endrow in df.iterrows():
                    if start == end:
                        continue
                    
                    else:
                        b = (endrow["Latitude"], endrow["Longitude"])

                        dmatrix.append([
                            a,
                            b,
                            cls.haversine(a, b)
                        ])
                    
                    pbar.update(1)
                
                continue
        print()        
        log.debug('Converting Matrix to DataFrame...')
        
        return pd.DataFrame(dmatrix, columns=["From", "To", "Distance"])
    
    @classmethod
    def neighborhood(cls, *, stores: pd.DataFrame, distances: pd.DataFrame):
        total = len(stores)

        stores["Neighbors"] = np.nan
        stores["Total Density"] = np.nan

        log.state('Creating Neighborhood Mappings...')
        print()

        with tqdm(total=total, desc="Calculating Neighborhood Metrics", colour="green", leave=True) as pbar:
            for index, store in stores.iterrows():
                log.trace(f'Calculating Neighborhood Metrics for {store["Account_Number"]}')
                coords = (store["Latitude"], store["Longitude"])

                neighbors = distances.loc[
                    ((distances["From"] == coords) & (distances["Distance"] < cls.radius))
                ]

                population = len(neighbors)
                density = neighbors["Distance"].mean()

                stores.at[index, "Neighbors"] = population
                stores.at[index, "Total Density"] = density

                pbar.update(1)
        
        print()
        
        return stores

    @classmethod
    def getClusterCentres(cls, *, neighborhood: pd.DataFrame):
        log.state('Identifying Cluster Centers...')

        sorted = neighborhood.sort_values(by=["Total Density"], ascending=False).reset_index(drop=True)

        i = 0
        clusters = []

        print()

        with tqdm(total=len(neighborhood), desc="Analyzing Neighborhood Density", colour="green", leave=True) as pbar:
            for index, row in sorted.iterrows():
                if row["Neighbors"] < cls.min_size:
                    pbar.update(1)

                    continue
                    
                coords = (row["Latitude"], row["Longitude"])
                centrepoints = [cluster.centre for cluster in clusters]

                if coords in centrepoints:
                    continue

                proximity = [cls.haversine(coords, centrepoint) for centrepoint in centrepoints]

                if len(clusters) == 0 or all([distance > (2 * cls.radius) for distance in proximity]):
                    cluster = Cluster(i, centre=coords)
                    clusters.append(cluster)

                    i += 1
                
                pbar.update(1)
            
        print()
        log.debug(f'Identified {len(clusters)} high-density points')
        
        return clusters


    @classmethod
    def getClosestCluster(cls, *, stores: pd.DataFrame, clusters: list):
        log.state('Setting Point Clusters...')

        stores["Cluster Center"] = [() for _ in range(len(stores))]
        centrepoints = [cluster.centre for cluster in clusters]

        print()

        with tqdm(total=len(stores), desc="Finding Closest Cluster Centre", colour="green", leave=True) as pbar:

            for index, row in stores.iterrows():
                coords = (row["Latitude"], row["Longitude"])

                if coords in centrepoints:
                    stores.at[index, "Cluster Center"] = coords
                
                else:
                    proximity = [cls.haversine(coords, centrepoint,) for centrepoint in centrepoints]
                    closest = centrepoints[proximity.index(min(proximity))]

                    stores.at[index, "Cluster Center"] = closest
                
                pbar.update(1)

                continue
        
        print()
        log.debug('Cluster Assignment Completed')

        return stores

    @classmethod
    def alignCentroid(cls, df: pd.DataFrame):
        focalpoints= df["Cluster Center"].unique()

        clusters = {
            focalpoint: df[df["Cluster Center"] == focalpoint]
            for focalpoint in focalpoints
        }

        centroids = []

        for cluster, points in clusters.items():
            centroid = (points["Latitude"].mean(), points["Longitude"].mean())
            centroids.append(Cluster(0, centre=centroid))
        
        stores = cls.getClosestCluster(stores=df, clusters=centroids)

        return stores
        
    
    @classmethod
    def split(cls, *, stores: pd.DataFrame, max_size: int = 250):
        centrepoints = stores["Cluster Center"].unique()
        log.state('Optimizing Cluster Size...')

        clusters = {
            centrepoint: stores[stores["Cluster Center"] == centrepoint]
            for centrepoint in centrepoints
        }

        x = 1
        centrepoints = []

        for cluster, points in clusters.items():
            if len(points) > max_size:
                max_distance = -float("inf")

                point1, point2 = None, None

                print()
                with tqdm(total=len(points), desc=f"Optimizing Cluster: {x}/{len(clusters)}", leave=True, colour="green") as pbar:

                    for index, row in points.iterrows():
                        coord1 = (row["Latitude"], row["Longitude"])

                        for _index, _row in points.iterrows():
                            coord2 = (_row["Latitude"], _row["Longitude"])

                            if index == _index:
                                continue

                            distance = sum((
                                cls.haversine(coord1, cluster),
                                cls.haversine(coord2, cluster),
                                cls.haversine(coord1, coord2)
                            ))

                            if distance > max_distance:
                                max_distance = distance
                                point1 = coord1
                                point2 = coord2

                            continue
                        
                        pbar.update(1)

                        continue
                    
                    x += 1

                    centrepoints.append(point1)
                    centrepoints.append(point2)

            else:
                centrepoints.append(cluster)
        
        clusters = [Cluster(i, centre=centrepoints[i]) for i in range(len(centrepoints))]

        print()
        log.debug(f'Identified {len(clusters)} Optimized Clusters')
        
        return cls.getClosestCluster(stores=stores, clusters=clusters)

    @classmethod
    def cluster(cls, *, stores: pd.DataFrame):
        log.state('Running Clustering Alogrithm (Iteration 1 of 1) ...')
        centrepoints = cls.getClusterCentres(neighborhood=stores)
        first_pass = cls.getClosestCluster(stores=stores, clusters=centrepoints)
        first_alignment = cls.alignCentroid(first_pass)
        
        log.state('Running Cluster Optimization Algorithm (Iteration 1 of 3) ...')
        second_pass = cls.split(stores=first_alignment)
        second_alignment = cls.alignCentroid(second_pass)

        log.state('Running Cluster Optimization Algorithm (Iteration 2 of 3) ...')
        third_pass = cls.split(stores=second_alignment, max_size=160)
        third_alignment = cls.alignCentroid(third_pass)

        log.state('Running Final Cluster Optimization Algorithm (Iteration 3 of 3) ...')
        final_pass = cls.split(stores=third_alignment, max_size=120)
        final_alignment = cls.alignCentroid(final_pass)

        return final_alignment


                        


        

            
                    
                





                    
           

    
            


        


                




