import os
import webbrowser

from .packages.mapping import MappingEngine
from .packages.geocode import LocationEngine
from .packages.clustering import ClusterEngine
from .packages.dynamics import DynamicsEngine

from .logger import CustomLogger as log


static_dir = os.path.abspath(__file__).replace('__init__.py', 'static/')

class ControlFlow():

    @staticmethod
    def mapview():
        webbrowser.open(static_dir + 'map.html')

    def run(self):
        accounts = DynamicsEngine.download()
        log.debug('Saving Accounts Download...')
        accounts.to_csv(static_dir + 'accounts.csv')


        coordinates = LocationEngine.geocode(accounts)
        log.debug('Saving Geocoding Data...')
        coordinates.to_csv(static_dir + 'coordinates.csv')

        clustered = ClusterEngine.cluster(stores=coordinates)
        log.debug('Saving Cluster Algorithm Results...')
        clustered.to_csv(static_dir + 'clusters.csv')

        map = MappingEngine.map()

        map.save(static_dir + 'map.html')

        
