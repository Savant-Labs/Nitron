import os
import sys
import requests

import pandas as pd

from .oauth2 import OAuth2
from ..types import class_property
from ..secrets import SecretManager
from ..logger import CustomLogger as log


class DynamicsConnector():
    token: str = None
    version: str = 'api/data/v9.2/'

    @class_property
    def header(cls):
        try:
            token = os.environ.get('DynamicsToken')
            if token is None:
                raise KeyError
            
        except KeyError:
            token = cls.authenticate()

        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json; charset=utf-8',
            'OData-MaxVersion': '4.0',
            'OData-Version': '4.0'
        }

        return headers


    @staticmethod
    def authenticate():
        log.state('Connecting to Dynamics 365 API...')
        token = OAuth2.authorize()

        os.environ['DynamicsToken'] = token

        return token

    @staticmethod
    def condense(table: pd.DataFrame) -> pd.DataFrame:
        columns = {
            'accountnumber' : 'Account_Number',
            'name': 'Account_Name',
            'address1_line1': 'Street_Address',
            'address1_city': 'City',
            'new_stateorprovincename': 'State',
            'new_countryname': 'Country',
            'address1_postalcode': 'Postal_Code',
            'new_storestatusname': 'Store_Status'
        }

        condensed = table.reindex(columns.keys(), axis=1)
        table = condensed.rename(columns=columns)

        accountfilter = table[~table["Account_Number"].str.contains("LI0")]

        return accountfilter

    @classmethod
    def getRequestEndpoint(cls, entity: str) -> str:
        base = SecretManager.DynamicsEndpoint

        if not base:
            log.fatal('Unable to Access Dynamics 365 Database - Invalid URL')
            
            return sys.exit()

        _filter = ' and new_storestatus ne '
        excluded = ['100000009', '100000006', '100000002', '100000001', '100000005', '100000008', 'null']
        filter = '?$filter=accountnumber ne null' + _filter + _filter.join(excluded)
           
        return base + cls.version + entity + filter
    
    
    @classmethod
    def _download(cls):
        header = cls.header

        log.state('Requesting [dbo.Accounts] Table...')
        url = cls.getRequestEndpoint('accounts')
        response = requests.get(url, headers=header)

        log.state('Loading Response into Data Frame...')
        data = response.json()
        
        try:
            _table = pd.json_normalize(data, 'value')

        except KeyError:
            log.fatal('Malformed Response - Terminating...')
            
            return sys.exit()


        log.debug('Condensing Table...')
        table = cls.condense(_table)
        
        return table


class DynamicsEngine(DynamicsConnector):

    @classmethod
    def download(cls):
        data = super()._download()

        return data