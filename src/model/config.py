import configparser
import sys


class Config:
    def __init__(self):
        self.config = configparser.ConfigParser()
        project = self.get_project()
        if project is not None:
            self.config.read(self.get_base_dir('etc') + project + '/' + 'config.ini')
        else:
            self.config.read(self.get_base_dir('etc') + 'config.ini')

    def get_project(self):
        project = None
        args = sys.argv
        if len(args) > 1:
            project = args[1]
        return project

    def get_section_config(self, section):
        config = {}
        options = self.config.options(section)
        for option in options:
            config[option] = self.config.get(section, option)
        return config

    def get_sections(self):
        return self.config.sections()

    def get_base_dir(self, type=None):
        base_dir = sys.path[0]
        if not type:
            return base_dir
        if type == 'etc':
            return base_dir + '/etc/'
        if type == 'var':
            return base_dir + '/var/'
        if type == 'tmp':
            return base_dir + '/tmp/'
        return base_dir
