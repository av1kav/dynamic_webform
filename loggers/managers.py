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
    Singleton class for Logging management; thread-safe and production-capable. Sphinx
    autodoc will set various class variables

    Attributes:
        _logger_instance: The singleton logger instance that is configured only once.
        logger_name: The name of the logger, configured in the instance config YAML.
        log_dir: (Experimental) The directory used for storing log output for any file-based handlers
    """

    _logger_instance = None

    @classmethod
    @abstractmethod
    def get_logger(cls, config=None):
        """
        Return a singleton logger instance if configured, otherwise configure a new logger 
        and handlers based on the provided config and return it. Ensure that the logger is not
        disabled when handling request-based function calls (eg. request.method)

        Args:
            config(dict): (Optional, default=None) An optional kwarg which should be supplied
            the instance configuration dict only once - when first setting up the LoggerManager.

            This is a singleton classmethod - do not instantiate this class as an object.
        
        Returns:
            A singleton logger, equivalent to (logging.getLogger(cls.logger_name))

        Usage:
            >>> app_logger = LoggerManager.get_logger(config) # Provide the config arg when setting up a singleton logger
            >>> app_logger.info("message") # An example of an INFO log
        """
        # Initial logic to set up logger
        if not cls._logger_instance and config:
            logging_dictConfig = config['system']['logging']
            cls.logger_name = next(iter(logging_dictConfig['loggers'].keys()))
            cls.log_dir = logging_dictConfig['log_dir']
            os.makedirs(cls.log_dir, exist_ok=True)
            logging.config.dictConfig(logging_dictConfig)
            cls._logger_instance = logging.getLogger(cls.logger_name)
            cls._logger_instance.info(f"App Logger '{cls.logger_name}' initialized with handlers: {cls._logger_instance.handlers}")
            cls._logger_instance.debug("Available Handlers:")
            for name, logger in logging.root.manager.loggerDict.items():
                cls._logger_instance.debug(f"Logger: {name}, Level: {getattr(logger, 'level', 'Not Set')}")
        return cls._logger_instance