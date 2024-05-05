import os

from .packages.mapping import MappingEngine
from .packages.geocode import LocationEngine
from .packages.clusters import ClusterEngine
from .packages.dynamics import DynamicsEngine

from .logger import CustomLogger as log


static_dir = os.path.abspath(__file__).replace('__init__.py', 'static/')

class ControlFlow():
    def run(self):
        accounts = DynamicsEngine.download()
        log.debug('Saving Accounts Download...')
        accounts.to_csv(static_dir + 'accounts.csv')


        coordinates = LocationEngine.geocode(accounts)
        log.debug('Saving Geocoding Data...')
        coordinates.to_csv(static_dir + 'coordinates.csv')

        distances = ClusterEngine.distanceMatrix(coordinates)
        log.debug('Saving Distance Matrix...')
        distances.to_csv(static_dir + 'distances.csv')

        neighborhood = ClusterEngine.neighborhood(stores=coordinates, distances=distances)
        log.debug('Saving Neighborhood Metrics...')
        neighborhood.to_csv(static_dir + 'neighborhood.csv')

        clustered = ClusterEngine.cluster(stores=neighborhood)
        log.debug('Saving Cluster Algorithm Results...')
        clustered.to_csv(static_dir + 'clusters.csv')

        map = MappingEngine.map()
        
