import os

import pandas as pd
import tqdm as tqdm

from geopy import Bing

from ..secrets import SecretManager
from ..logger import CustomLogger as log


class LocationEngine():

    geocoder = Bing(api_key=SecretManager.BingMapsAPI)

    savefile = os.path.abspath(__file__).replace('geocode.py', 'static/coordinates.csv')
    
    @staticmethod
    def format_table(data: pd.DataFrame):
        def create_address(x):
            
            columns = ['Street_Address', 'City', 'State', 'Country']

            composite = ', '.join(str(x[column]) for column in columns if x[column] is not None)
            
            return f'{composite} {x["Postal_Code"]}'
        
        data['Address'] = data.apply(lambda x: create_address(x), axis=1)

        return data

    @classmethod
    def geocode(cls, data: pd.DataFrame) -> pd.DataFrame:
        log.state('Creating Composite Index for Address Search...')
        table = cls.format_table(data)

        log.state('Applying Geocoding Software...')
        print()

        tqdm.tqdm.pandas(desc='Fetching Coordinates...', colour='GREEN')
        table['Coordinates'] = table['Address'].progress_apply(cls.geocoder.geocode).apply(lambda x: (x.latitude, x.longitude))
        table[['Latitude', 'Longitude']] = table['Coordinates'].apply(lambda x: pd.Series(x))
        print()

        columns = ['Account_Number', 'Account_Name', 'Store_Status', 'Coordinates', 'Latitude', 'Longitude']
        geocoded = table.reindex(columns, axis=1)

        geocoded.to_csv(cls.savefile)

        return geocoded