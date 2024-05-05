import sys
import urllib.parse
import requests
import urllib

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC

from ..secrets import SecretManager
from ..logger import CustomLogger as log


class OAuth2():
    redirect = 'http://localhost:8000'

    @staticmethod
    def getBrowserEngine() -> webdriver.Chrome:
        options = webdriver.ChromeOptions()
        service = Service(ChromeDriverManager().install())

        options.headless = True
        options.add_argument("--disable-logging")
        options.add_experimental_option("excludeSwitches", ['enable-logging'])

        driver = webdriver.Chrome(
            service = service,
            options = options
        )

        return driver
    
    @classmethod
    def getSignInURL(cls) -> str:
        params = {
            'client_id': SecretManager.DynamicsID,
            'response_type': 'code',
            'redirect_uri': cls.redirect,
            'response_mode': 'query',
            'scope': SecretManager.DynamicsEndpoint + '.default',
            'state': '12345'
        }

        if any([value is None for value in params.values()]):
            log.fatal('Unable to Build OAuth 2.0 Authorization URL - Exiting...')
            
            return sys.exit()

        args = urllib.parse.urlencode(params)
        url = '?'.join([SecretManager.DynamicsOAuthURL, args])

        return url

    @classmethod
    def spoofAuthorization(cls) -> str:
        log.state('Simulating OAuth Web Flow...')
        engine = cls.getBrowserEngine()

        log.debug('Accessing Web Endpoint...')
        url = cls.getSignInURL()
        engine.get(url)

        log.trace('Entering Username...')
        usernameField = EC.element_to_be_clickable((By.NAME, 'loginfmt'))
        usernameBox = WebDriverWait(engine, 10).until(usernameField)

        username = SecretManager.DynamicsUser
        if not username:
            log.fatal('Unable to Login to Dynamics 365 - Missing Username')
            
            return sys.exit()

        usernameBox.send_keys(username)
        nextButton = engine.find_element(By.ID, 'idSIButton9')
        nextButton.click()

        log.trace('Entering Password...')
        passwordField = EC.element_to_be_clickable((By.NAME, 'passwd'))
        passwordBox = WebDriverWait(engine, 10).until(passwordField)

        password = SecretManager.DynamicsPass
        if not password:
            log.fatal('Unable to Login to Dynamics 365 - Missing Password')

            sys.exit()
        
        passwordBox.send_keys(password)
        submitButton = engine.find_element(By.ID, 'idSIButton9')
        submitButton.click()

        log.debug('Bypassing Security Prompt...')
        prompt = EC.element_to_be_clickable((By.ID, 'idBtn_Back'))
        promptButton = WebDriverWait(engine, 10).until(prompt)
        promptButton.click()

        log.debug('Retrieving Authentication Code...')
        WebDriverWait(engine, 10).until(EC.url_contains(cls.redirect))
        
        redirect_url = urllib.parse.urlparse(engine.current_url).query
        query = urllib.parse.parse_qs(redirect_url)
        authcode = query['code'][0]

        log.state('Exiting Simulated Web Flow...')
        engine.quit()

        return authcode
    
    @classmethod
    def refreshToken(cls, *, authorization: str) -> str:
        log.state('Converting Authorization Code...')

        data = {
            'client_id': SecretManager.DynamicsID,
            'client_secret': SecretManager.DynamicsKey,
            'scope': SecretManager.DynamicsEndpoint + '.default',
            'grant_type': 'authorization_code',
            'redirect_uri': cls.redirect,
            'code': authorization
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        url = SecretManager.DynamicsTokenURL

        if any([value is None for value in data.values()]) or url is None:
            log.fatal('Unable to Build Token Request Data - Exiting...')
            
            return sys.exit()
    
        response = requests.post(url, headers=headers, data=data)

        try:
            token = response.json()['access_token']
            log.debug('Retrieved Access Token...')

        except KeyError:
            log.fatal('Invalid Access Code Recieved - Terminating...')
            
            return sys.exit(0)

        return token
    
    @classmethod
    def authorize(cls):
        code = cls.spoofAuthorization()
        token = cls.refreshToken(authorization=code)

        return token


        




