import os
from datamodels.local_store import ParquetLocalDataStore
from datamodels.mysql import MySQLDatastore

from loggers.managers import LoggerManager

class BaseDatastoreManager:
    """
    Abstract base class for Datastore Managers. All datastore managers must broker initial setup, connection 
    establishment, checks and teardowns as well as required data IUD operations transparently, with the same 
    high-level functions (see methods below). This is to maintain code readability and ease of use.
    """
    def __init__(self):
        """Initialize any datastore-specific connections, etc. based on config."""
        raise NotImplementedError
    def refresh(self):
        """If applicable, rebuild the state of the datastore (or any views of the state)."""
        raise NotImplementedError
    def add_data(self):
        """Data INSERT functionality; consider making this UPSERT by default."""
        raise NotImplementedError
    def add_bulk_data(self):
        """Bulk data INSERT functionality, usually from an uploaded file. Consider making this UPSERT by default."""
        raise NotImplementedError
    def delete_data(self):
        """Data DELETE functionality. Consider disabling unless required."""
        raise NotImplementedError
    def read_data(self):
        """Return data as a manipulatable object (usually a Pandas Dataframe)"""
        raise NotImplementedError
    def check_connection(self):
        """If applicable, handle any heartbeats/connection pool refreshes here."""
        raise NotImplementedError

class DatastoreManager(BaseDatastoreManager):
    """
    Main datastore-managing class that currently handles the following datastores: [mysql]
    """
    def __init__(self, app, config):
        self.datastore_type = config['datastore']['datastore_type']
        self.logger = LoggerManager.get_logger()
        self.logger.info(f"Datastore Manager configured with '{self.datastore_type}' datastore_type")
        if self.datastore_type == 'local':
            raise DeprecationWarning("The 'local' datastore_type is deprecated; consider implementing/using an ORM-based approach eg. SQLite ")
            # TODO: Ensure critical keys available in dict
            # 1. Information about whether the file exists or not at initialization
            local_store_filename = config['datastore']['datastore_file_name']
            if os.path.exists(local_store_filename):
                self.logger.info('INIT: Local store file exists; appending data.')
            else:
                self.logger.info("Local datastore does not exist.")
        elif self.datastore_type == 'mysql':
            # TODO: Ensure critical keys available in dict
            self.datastore = MySQLDatastore(app, config)
        else:
            raise ValueError(f"ERROR: '{self.datastore_type}' is not a valid datastore_type value.")
    
    def refresh(self):
        """Refresh the form table schema (migrations handled with Alembic)"""
        self.datastore._refresh_table_schema()
    
    def add_data(self, submission_data):
        """
        Data INSERT operation, implements UPSERT logic.
        
        Args:
            submission_data(dict): A dict containing JSON-equivalent form submission information.
        Returns:
            None
        """
        self.datastore.upsert_data(submission_data)

    def add_bulk_data(self, bulk_upload_data):
        """
        Bulk data INSERT operation, implements UPSERT logic.
        
        Args:
            bulk_upload_data(pd.DataFrame): A Pandas DataFrame containing multiple rows of data meant to be 
            UPSERTED into the datastore.
        Returns:
            None
        """
        self.datastore.upsert_bulk_data(bulk_upload_data)
    
    def read_data(self, id=None):
        """
        A query interface into the datastore; an optional ID controls if a specific row or all rows are returned.

        Args:
            id(str): A session_id value to look up in the datastore. If blank, all results are returned.

        """
        return self.datastore.query(id)
    