from colorama import init
from colorama import Fore
from colorama import Style

from os.path import abspath
from datetime import datetime


def setup():
    init()

directory = abspath(__file__).replace('logger.py', 'logfiles/')

class CustomLogger():

    threshold: int = 1

    levels = [
        'TRACE',
        'DEBUG',
        'STATE',
        'ISSUE',
        'ERROR',
        'FATAL'
    ]

    colors = [
        Fore.CYAN,
        Fore.GREEN,
        Fore.BLUE,
        Fore.MAGENTA,
        Fore.YELLOW,
        Fore.RED
    ]

    logfiles = { 
        key: directory + key for key in ['events', 'errors']
    }

    @classmethod
    def _write(cls, message: str, *, error: bool = False) -> None:
        with open(cls.logfiles['events'], 'a+') as log:
            log.write(message +'\n')
        
        if error:
            with open(cls.logfiles['errors'], 'a+') as log:
                log.write(message + '\n')
        
        return
    
    @classmethod
    def _print(cls, message: int, *, level: str) -> None:
        if cls.levels.index(level) >= cls.threshold:
            print(message)
        
        return

    @staticmethod
    def _getTimeStamp() -> str:
        now = datetime.now()
        stamp = now.strftime('%m-%d-%y @ %H:%M:%S:%f')[:-3]

        return stamp

    @classmethod
    def _formatMessage(cls, level: int, message: str) -> tuple:
        timestamp = cls._getTimeStamp()

        file = f"[{cls.levels[level]}] {timestamp} | {message}"
        color = f"{cls.colors[level]}[{cls.levels[level]}]{Style.RESET_ALL} {timestamp} | {message}"
        
        return (file, color)
    
    @classmethod
    def trace(cls, message: str) -> None:
        file, color = cls._formatMessage(0, message)

        cls._write(file, error=False)
        cls._print(color, level='TRACE')

        return

    @classmethod
    def debug(cls, message: str) -> None:
        file, color = cls._formatMessage(1, message)

        cls._write(file, error=False)
        cls._print(color, level='DEBUG')

        return
    
    @classmethod
    def state(cls, message: str) -> None:
        file, color = cls._formatMessage(2, message)

        cls._write(file, error=False)
        cls._print(color, level='STATE')

        return
    
    @classmethod
    def issue(cls, message: str) -> None:
        file, color = cls._formatMessage(3, message)

        cls._write(file, error=True)
        cls._print(color, level='ISSUE')

        return
    
    @classmethod
    def error(cls, message: str) -> None:
        file, color = cls._formatMessage(4, message)

        cls._write(file, error=True)
        cls._print(color, level='ERROR')

        return

    @classmethod
    def fatal(cls, message: str) -> None:
        file, color = cls._formatMessage(5, message)

        cls._write(file, error=True)
        cls._print(color, level='FATAL')

        return



    