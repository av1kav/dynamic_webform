import logging.config

class BaseLoggerManager:
    def __init__(self):
        raise NotImplementedError
    def debug(self):
        raise NotImplementedError
    def info(self):
        raise NotImplementedError
    def warning(self):
        raise NotImplementedError
    def error(self):
        raise NotImplementedError
    def critical(self):
        raise NotImplementedError
    
class LoggerManager(BaseLoggerManager):
    def __init__(self, config):
        self.config = config
        self.logging_dictConfig = self.config['system']['logging']
        logging.config.dictConfig(self.logging_dictConfig)