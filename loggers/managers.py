import logging.config
import os 

class BaseLoggerManager:
    """
    Abstract singleton base class for Loggers.
    """
    @classmethod
    def get_logger(cls):
        """Return a singleton logger instance."""
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
    """
    Singleton class for Logging management. Thread-safe and production-capable.

    Attributes:
        _logger_instance: The singleton logger instance that is configured only once.
    """
    _logger_instance = None
    @classmethod
    def get_logger(cls, config=None):
        """
        Return a singleton logger instance if configured, otherwise configure a new logger 
        using the config, save it and return it.
        """
        if not cls._logger_instance:
            cls.config = config
            cls.logging_dictConfig = cls.config['system']['logging']
            cls.logger_name = cls.logging_dictConfig['loggers'].items()[0]
            cls.log_dir = cls.logging_dictConfig['log_dir']
            os.makedirs(cls.log_dir, exist_ok=True)
            logging.config.dictConfig(cls.logging_dictConfig)
            cls._logger_instance = logging.getLogger(cls.logger_name)
        return cls._logger_instance
            
