import os
from datamodels.local_store import ParquetLocalDataStore
from datamodels.mysql import MySQLDatastore

class BaseDatastoreManager:
    def __init__(self):
        raise NotImplementedError
    def refresh(self):
        raise NotImplementedError
    def add_data(self):
        raise NotImplementedError
    def add_bulk_data(self):
        raise NotImplementedError
    def delete_data(self):
        raise NotImplementedError
    def read_data(self):
        raise NotImplementedError
    def check_connection(self):
        raise NotImplementedError

class DatastoreManager(BaseDatastoreManager):
    def __init__(self, app, config):
        self.datastore_type = config['datastore']['datastore_type']
        if self.datastore_type == 'local':
            # TODO: Ensure critical keys available in dict
            # 1. Information about whether the file exists or not at initialization
            local_store_filename = config['datastore']['datastore_file_name']
            if os.path.exists(local_store_filename):
                print('INIT: Local store file exists; appending data.')
            else:
                print("Local datastore does not exist.")
        elif self.datastore_type == 'mysql':
            # TODO: Ensure critical keys available in dict
            self.datastore = MySQLDatastore(app, config)
        else:
            raise ValueError(f"ERROR: '{self.datastore_type}' is not a valid datastore_type value.")
    
    def refresh(self):
        self.datastore._refresh_table_schema()
    
    def add_data(self, submission_data):
        self.datastore.upsert_data(submission_data)

    def add_bulk_data(self, bulk_upload_data):
        self.datastore.upsert_bulk_data(bulk_upload_data)
    
    def read_data(self, id=None):
        return self.datastore.query(id)
    