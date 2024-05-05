import os
import sys
from dotenv import load_dotenv

from . import logger
from .logger import CustomLogger as log


logger.setup()

envPath = os.path.abspath(__file__).replace('app/secrets.py', '.env')


class SecretMeta(type):
    def __getattribute__(self, name: str) -> str:
        try:
            value = os.environ.get(name)

        except KeyError:
            log.error(f'Credential Not Found: {name}')
            log.debug(f'Verify the presence of this key within the .env config file: {envPath}')

            value = None

        finally:
            return value


class SecretManager(metaclass=SecretMeta):
    print()
    load_dotenv()

    if os.path.exists(envPath):
        log.debug(f'Located .env config file: {envPath}')
    else:
        log.fatal(f'Unable to locate .env config file at {envPath} - Terminating...')
        sys.exit()


        



