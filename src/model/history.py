from datetime import datetime
from pytz import timezone
import time
from .config import Config


class History:
    def __init__(self):
        self.config = Config()

    def get_update_file(self, name):
        update_file = self.config.get_base_dir('tmp') + name + '_update.txt'
        return update_file

    def get_current_update(self, name):
        path = self.get_update_file(name)
        with open(path, 'r') as content_file:
            current_update = content_file.read()
        return current_update

    def set_current_update(self, name, format="%d/%m/%Y"):
        path = self.get_update_file(name)
        current_date = time.strftime(format)
        file = open(path, 'w')
        file.write(current_date)
        file.close()
