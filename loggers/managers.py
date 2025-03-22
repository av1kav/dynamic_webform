import logging.config
import os 
from abc import abstractmethod

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
        :meta private:
    """
    __logger_instance = None

    @classmethod
    @abstractmethod
    def get_logger(cls, config=None):
        """
        Return a singleton logger instance if configured, otherwise configure a new logger 
        and handlers based on the provided config and return it.

        Args:
            config(dict): (Optional, default=None) An optional kwarg which should be supplied
            the instance configuration dict only once - when first setting up the LoggerManager.

            This is a singleton classmethod - do not instantiate this class as an object.
        """
        if not cls.__logger_instance and config:
            cls.config = config
            cls.logging_dictConfig = cls.config['system']['logging']
            cls.logger_name = next(iter(cls.logging_dictConfig['loggers'].keys()))
            cls.log_dir = cls.logging_dictConfig['log_dir']
            os.makedirs(cls.log_dir, exist_ok=True)
            logging.config.dictConfig(cls.logging_dictConfig)
            cls.__logger_instance = logging.getLogger(cls.logger_name)
            cls.__logger_instance.info(f"App Logger '{cls.logger_name}' initialized with handlers: {cls.__logger_instance.handlers}")
            cls.__logger_instance.debug("Available Handlers:")
            for name, logger in logging.root.manager.loggerDict.items():
                cls.__logger_instance.debug(f"Logger: {name}, Level: {getattr(logger, 'level', 'Not Set')}")
        return cls.__logger_instance

