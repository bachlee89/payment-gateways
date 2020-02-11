import requests
from fake_useragent import UserAgent


class Session:
    def __init__(self, proxy={}):
        self.session = None
        self.user_agent = None
        self.tree = None
        self.driver = None
        self.last_driver = None
        self.token = None
        self.proxy = proxy
        self.need_to_change_proxy = 0

    def init_session(self, proxy={}):
        self.session = requests.session()
        self.user_agent = UserAgent().random
        self.proxy = proxy

    def get_proxy(self):
        return self.proxy

    def set_changing_proxy(self, value):
        self.need_to_change_proxy = value

    def is_changing_proxy(self):
        return self.need_to_change_proxy

    def set_tree(self, tree):
        self.tree = tree

    def get_tree(self):
        return self.tree

    def set_driver(self, driver):
        self.driver = driver

    def get_driver(self):
        return self.driver

    def set_last_driver(self, last_driver):
        self.last_driver = last_driver

    def get_last_driver(self):
        return self.last_driver

    def get(self, url, headers={}):
        if len(self.proxy) > 1:
            proxies = {
                "http": 'http://' + self.proxy['ip'] + ':' + self.proxy['port'],
                "https": 'http://' + self.proxy['ip'] + ':' + self.proxy['port']
            }
        else:
            proxies = {}
        default_headers = {'User-Agent': self.user_agent}
        headers = dict(headers, **default_headers)
        return self.session.get(url, headers=headers, proxies=proxies, timeout=(5, 30))

    def post(self, url, payload, headers={}):
        if len(self.proxy) > 1:
            proxies = {
                "http": 'http://' + self.proxy['ip'] + ':' + self.proxy['port'],
                "https": 'http://' + self.proxy['ip'] + ':' + self.proxy['port']
            }
        else:
            proxies = {}
        default_headers = {'User-Agent': self.user_agent}
        headers = dict(headers, **default_headers)
        return self.session.post(url, data=payload, headers=headers, proxies=proxies)

    def get_user_agent(self):
        return self.user_agent

    def set_token(self, token):
        self.token = token

    def get_token(self):
        return self.token
