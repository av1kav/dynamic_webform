import pandas as pd
import os

from ..loggers.managers import LoggerManager

class ParquetLocalDataStore:
    """
    (Deprecated) Datastore class to handle data storage as a local Parquet file.
    """
    def __init__(self):
        self.logger = LoggerManager.get_logger()
        raise DeprecationWarning("This class is not meant to be used in a production environment.")
    
    def append_or_update_data_to_local_store(self, data, config, format='parquet'):
        """
        (Deprecated) Handle an UPSERT operation into local store data.

        This method defines UPSERT behavior of a new record, called 
        'data', into the local store of the specified data type. The current
        behavior is an Session ID-based UPSERT; if a row with the new record's 
        session_id value exists, it is completely overwritten with the new data;
        otherwise, the row is inserted into the datastore

        Args:
            data: A dict that stores form responses and session information
            format: (optional, default='parquet') The format of the datastore. Only
                    'parquet' is currently supported.
        Returns:
            None
        """

        local_store_filename = config['datastore']['datastore_file_name']

        if format != 'parquet':
            raise ValueError("Currently, only 'parquet' is supported as a format")
        if os.path.exists(local_store_filename):
            self.logger.info('Local store file exists; appending data.')
            existing_data = pd.read_parquet(local_store_filename)
            df = pd.DataFrame.from_dict([data])
            # If data for the same ID exists, update; otherwise insert
            matching_rows = existing_data.loc[existing_data['id'] == df['id'].values[0]]
            if matching_rows.empty:
                self.logger.info(f"No match for id '{df['id'].values[0]}' in local data store. INSERT")
                df = pd.concat([df, existing_data])
                df.to_parquet(local_store_filename, index=False)
            else:
                self.logger.info(f"Existing data found for id '{df['id'].values[0]}' in local data store. UPDATE")
                existing_data.update(df)
                existing_data.to_parquet(local_store_filename, index=False)
        else:
            self.logger.info('Creating new local store object.')
            df = pd.DataFrame.from_dict([data])
            df.to_parquet(local_store_filename, index=False)

    def read_local_store_data(self, config):
        """
        (Deprecated) Read data from the local datastore and return it as a Pandas DataFrame.

        Args:
            None
        Returns:
            A Pandas DataFrame containing all data from the local datastore.
        
        """
        local_store_filename = config['datastore']['datastore_file_name']
        
        if not os.path.exists(local_store_filename):
            self.logger.warning('No local store file created/present.')
            return pd.DataFrame.from_dict([{'id': 'Warning: There is no information in the local datastore yet.'}])
        else:
            return pd.read_parquet(local_store_filename)
