from selenium.webdriver import Firefox, FirefoxProfile
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.firefox.options import Options
from fake_useragent import UserAgent


class Selenium:
    def __init__(self, proxy={}):
        self.proxy = proxy
        self.ua = UserAgent()

    def get_firefox_driver(self, proxy={}):
        profile = FirefoxProfile()
        if len(proxy):
            profile.set_preference("network.proxy.type", 1)
            profile.set_preference("network.proxy.http", proxy['ip'])
            profile.set_preference("network.proxy.http_port", proxy['port'])
            profile.set_preference("network.proxy.ssl", proxy['ip'])
            profile.set_preference("network.proxy.ssl_port", proxy['port'])
        profile.set_preference("general.useragent.override", self.ua.random)

        opts = Options()
        # opts.set_headless()
        driver = Firefox(options=opts, firefox_profile=profile)
        return driver

    def get_chrome_driver(self, proxy={}):
        options = ChromeOptions()
        options.add_argument(f'user-agent={self.ua.random}')
        if len(proxy):
            options.add_argument("--proxy-server=http://" + proxy['ip'] + ":" + proxy['port'])
        # options.set_headless()
        driver = Chrome(chrome_options=options)
        return driver
