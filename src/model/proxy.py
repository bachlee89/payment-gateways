from urllib.request import Request, urlopen
from bs4 import BeautifulSoup
import random
from fake_useragent import UserAgent


class Proxy:
    def __init__(self):
        self.proxies = []
        self.use_proxy = 1

    def get_proxies(self, country=None):
        if len(self.proxies) == 0:
            # Retrieve latest proxies
            proxies = []
            while 1:
                ua = UserAgent()
                proxies_req = Request('https://www.sslproxies.org/')
                proxies_req.add_header('User-Agent', ua.random)
                proxies_doc = urlopen(proxies_req).read().decode('utf8')

                soup = BeautifulSoup(proxies_doc, 'html.parser')
                proxies_table = soup.find(id='proxylisttable')

                # Save proxies in the array
                for row in proxies_table.tbody.find_all('tr'):
                    # if row.find_all('td')[1].string in ['80', '8080', '8888']:
                    proxy = None
                    if country is not None:
                        if row.find_all('td')[2].string in country.split(','):
                            proxy = {
                                'ip': row.find_all('td')[0].string,
                                'port': row.find_all('td')[1].string
                            }

                    else:
                        proxy = {
                            'ip': row.find_all('td')[0].string,
                            'port': row.find_all('td')[1].string
                        }
                    if proxy is not None:
                        proxies.append(proxy)
                if len(proxies) > 1:
                    break
            self.proxies = proxies
        return self.proxies

    def random_proxy(self, country=None):
        proxies = self.get_proxies(country)
        if self.use_proxy == 1 and len(proxies) > 1:
            index = random.randint(0, len(proxies) - 1)
            proxy = self.proxies[index]
            del self.proxies[index]
        else:
            proxy = {}
        return proxy
