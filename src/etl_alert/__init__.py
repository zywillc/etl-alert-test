import os
import yaml
ETL_METADATA_URL_KEY = 'ETL_METADATA_URL'

class ConfigSet(object):
    def __init__(self, filename):
        self._read_cfg(filename)
    
    @staticmethod
    def get_abs_file_path(filename):
        abs_file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            filename
        )
        return abs_file_path

    def _read_cfg(self, filename):
        abs_filename = self.get_abs_file_path(filename)
        stream = open(abs_filename, 'r')
        cfg = yaml.load(stream) 
        self.cfg = cfg

    @property
    def driver(self):
        return self.cfg['driver']

    def url(self):
        if not self.driver['url']:
            self.driver['url'] = os.environ[ETL_METADATA_URL_KEY]
        return self.driver['url']

    def db(self):
        return self.driver['db']
    
    def coll(self):
        return self.driver['coll']

def log_config():
    import logging
    import logging.config 
    logging.config.dictConfig(yaml.load(open(ConfigSet.get_abs_file_path('logging.yaml'), 'r')))
