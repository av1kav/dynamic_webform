from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine,  cast, Date, Integer
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.dialects.mysql import insert
from utils import generate_websafe_session_id
from datetime import datetime
from sqlalchemy.orm import Session
from flask_migrate import Migrate, init, revision, migrate, upgrade
import mysql.connector
import pandas as pd
import os
from sqlalchemy.sql import func

from loggers.managers import LoggerManager

SQLALCHEMY_TYPE_MAPPING = {
    "INTEGER": Integer,
    "STRING": String(255),
    "FLOAT": Float,
    "BOOLEAN": Boolean
}

class MySQLDatastore:
    """
    SQLAlchemy-interfaced, ORM-bound MySQL Datastore class. Implements low-level data operations on a configured MySQL instance.

    Attributes:
        app(Flask): The Flask app implementing this Datastore instance.
        db(SQLAlchemy): The Flask-SQLAlchemy instance used to perform ORM-bound operations
        config(dict): The full contents of the config.yaml configuration file
        table_name(str): The name of the table that will contain form submission data (from config)
        table_model(db.Model): A SQLAlchemy model of the table, generated at runtime using the form_config Excel sheet
        migrate(Migrate): An Alembic Migrate object used to initialize and govern migrations (changes in schema)
        logger(LoggerManager): A singleton logger instance for logging.
        sqlalchemy_database_uri: A SQLAlchemy URI generated using the config and added to the app dictionary
        engine: A SQLAlchemy ORM Engine to handle specific low-level data operations

    Usage:
        >>> datastore = MySQLDatastore(app, config) # Should be done within a DatastoreManager instance
    """
    def __init__(self, app, config):
        """
        Set up a MySQL connection, initialize the ORM engine and use Flask-Migrate (Alembic) to perform any necessary migrations
        to bring the database in sync with the fields in the form configuration sheet.

        Args:
            app(Flask): The Flask app implementing this Datastore instance.
            config(dict): The full contents of the config.yaml configuration file
        Returns:
            None
        """
        self.app = app
        self.db = SQLAlchemy()
        self.config = config
        self.table_name = self.config['form']['form_config_file_name'].split('.')[0]
        self.table_schema = self.config['datastore']['datastore_params']['mysql_database'] # Not a typo - MySQL does not have "schemas"
        self.logger = LoggerManager.get_logger()

        # Set up MYSQL and initialize the SQLAlchemy ORM engine
        mysql_config_params = self.config['datastore']['datastore_params']
        self.sqlalchemy_database_uri = self.generate_database_uri_from_config(mysql_config_params=mysql_config_params)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = self.sqlalchemy_database_uri
        self.logger.info(f"Added SQLAlchemy URI to app config")
        for key, value in mysql_config_params.get('mysql_sqlalchemy_engine_options',{}).items():
            app.config[key] = value
            self.logger.info(f"Added {key}={value} to app config")
        self.db.init_app(self.app)

        # Initialize flask-migrate (Alembic), load the table model and run a single migration if required
        self.migrate = Migrate(self.app, self.db)
        self.table_model = self.generate_table_orm_from_config_file(config_folder='form_config',config_filename=self.config['form']['form_config_file_name'])  
        with self.app.app_context():
            if not os.path.exists('migrations'):
                self.logger.warning("Initial setup, no migrations folder found. Initializing new migrations folder and running first auto-migration.")
                init()
            migrate(message="auto-migration")
            upgrade() 
        self.create_engine()

    def create_engine(self):
        """Create a SQLAlchemy engine to handle low-level data operations (IUD)"""
        self.engine = create_engine(self.sqlalchemy_database_uri, echo=True)
    
    def generate_database_uri_from_config(self, mysql_config_params):
        """
        Helper function to cleanly generate a MySQL-specific SQLAlchemy Database URI for the app dictionary.
        
        Args:
            mysql_config_params(dict): A subset of MySQL-specific configuration parameters from the config.yaml file
        
        Returns:
            SQLALCHEMY_DATABASE_URI(str): A formatted SQLAlchemy database URI.
        """
        SQLALCHEMY_DATABASE_URI = "mysql+mysqlconnector://{username}:{password}@{hostname}/{databasename}".format(
            username=mysql_config_params['mysql_username'],
            password=mysql_config_params['mysql_password'],
            hostname=mysql_config_params['mysql_hostname'],
            databasename=mysql_config_params['mysql_database']
        )
        return SQLALCHEMY_DATABASE_URI
    
    def generate_table_orm_from_config_file(self, config_folder='formbuilder',config_filename='wny_config.xlsx'):
        """
        Generates an ORM (object representation of the actual database table) and creates it under the configured engine.
        The model is generated dynamically using the form_config Excel sheet, and will be used as a reference by Alembic
        to build migration scripts. The first "migration" will be blank, since this method also creates the 

        Args:
            config_folder(str): (Optional, default='formbuilder') The name of the folder, under the config/ directory, 
                                containing the form_config Excel sheet.
            config_filename(str): (Optional, default='wny_config.xlsx') The name of the actual Excel file containing form
                                  configuration information. Essentially controls the schema of the database table and ORM,
        
        Returns:
            A SQLAlchemy db.Model class object
        """
        # Define the default table schema with ID and timestamp fields
        attributes = {
            "__tablename__": config_filename.split('.')[0].lower(),
            "__table_args__": {'extend_existing': True},
            "id": Column(Integer, primary_key=True), 
        }
        attributes['id'] = Column(String(255), nullable=False, primary_key=True)
        attributes['timestamp'] = Column(DateTime, nullable=False, primary_key=False)

        # Then build the remainder of the schema dynamically from the form config file
        config_folder = os.path.join('config',config_folder)
        config_filepath = os.path.join(config_folder, config_filename)
        current_folder = os.path.dirname(os.path.abspath(__file__))
        relative_config_file_path = os.path.join(current_folder,'..',config_filepath)
        config_workbook = pd.ExcelFile(relative_config_file_path)

        form_fields = pd.read_excel(config_workbook, 'Fields')
        for _, row in form_fields.iterrows():
            col_name = row["backend_field_name"]
            col_type = SQLALCHEMY_TYPE_MAPPING.get(row["data_type"], String(255))
            nullable = True if row["required"].lower() == 'no' else False
            attributes[col_name] = Column(col_type, nullable=nullable, primary_key=False)
        model = type(attributes['__tablename__'], (self.db.Model,), attributes)
        return model

    def check_connection(self):
        """'Check' the existing connection associated with this Datastore instance by opening and closing the configured connection."""
        mysql_config_params = self.config['datastore']['datastore_params']
        self.con = mysql.connector.connect(
                user=mysql_config_params['mysql_username'],
                password=mysql_config_params['mysql_password'],
                host=mysql_config_params['mysql_hostname'],
                database=mysql_config_params['mysql_database']
        )
        self.con.close()
        self.logger.info('Datastore connection check OK.')
    
    def upsert_data(self, submission_data):
        """
        Perform an UPSERT (UPDATE row with the same session_id as the submission data, INSERT if such a row does not exist)
        against the data in the database using the provided submission data.

        Args:
            submission_data(dict): A JSON-equivalent dict containing form submission information.

        Returns:
            None
        """
        # Create a session
        with Session(self.engine) as session:
            # Create an instance of the dynamic model
            stmt = insert(self.table_model).values(**submission_data)
            upsert_stmt = stmt.on_duplicate_key_update(**submission_data)
            session.execute(upsert_stmt)
            session.commit()
            self.logger.info(f"Upserted row into {self.table_name}: {submission_data}")
    
    def upsert_bulk_data(self, bulk_upload_data):
        """
        Perform a bulk UPSERT (UPDATE rows with the same session_ids as the submission data, INSERT if such rows do not exist). Also
        ensure that the 'id' and 'timestamp' fields are added to the data if they do not already exist. The 'id' and 'timestamp' fields
        are not case-sensitive but must be included if updating existing data. 

        Args:
            bulk_upload_data(pd.DataFrame): A Pandas DataFrame that contains several instances (rows) of form submission data.

        Returns:
            None
        """
        # Ensure the default id and timestamp fields are present in the dataframe 
        num_rows = len(bulk_upload_data)
        bulk_upload_data_columns = [x.lower() for x in bulk_upload_data.columns]
        if 'id' not in bulk_upload_data_columns:
            self.logger.warning("The 'id' field was not found in the uploaded dataset. New IDs will be generated.")
            bulk_upload_data['id'] = [generate_websafe_session_id(self.config['general']['websafe_session_id_size']) for _ in range(len(bulk_upload_data))]
        if 'timestamp' not in bulk_upload_data_columns:
            self.logger.warning("The 'timestamp' field was not found in the uploaded dataset. New timestamps will be generated.")
            bulk_upload_data['timestamp'] = datetime.now()
        # Prepare the data for bulk upsertion by converting it to a dict
        bulk_upload_data = bulk_upload_data.where((pd.notnull(bulk_upload_data)), None)
        bulk_upload_data = bulk_upload_data.to_dict(orient="records")
        # Create a session
        with Session(self.engine) as session:
            # Create an instance of the dynamic model
            stmt = insert(self.table_model).values(bulk_upload_data)
            update_dict = {col.name: getattr(stmt.inserted, col.name) for col in self.table_model.__table__.columns}
            upsert_stmt = stmt.on_duplicate_key_update(update_dict)
            session.execute(upsert_stmt)
            session.commit()
            self.logger.info(f"Bulk-upserted {num_rows} row(s) into {self.table_name}")

    def query(self, id=None):
        """
        Query the MySQL database associated with this Datastore instance; return all rows or a specific one using an ID if provided.

        Args:
            id(str): (Optional) An optional session_id value to look up in the underlying MySQL database.

        Returns:
            A Pandas DataFrame object containing query results.  
        """
        with Session(self.engine) as session:
            query = session.query(self.table_model)
            if id:
                query = query.filter_by(id=id)
            df = pd.read_sql(query.statement, con=self.engine)
            # Drop SQLAlchemy-specific metadata
            if '_sa_instance_state' in df.columns:
                df = df.drop(columns=["_sa_instance_state"])
            return df
    
    def query_aggregated_data(self, group_by_field='timestamp', aggregation_function='count', aggregation_field='id', field_options=None):
        """
        Helper function to perform aggregation queries against the MySQL database associated with this Datastore instance. Used primarily for
        reporting and visualization purposes.

        Args:
            group_by_field(str): Defaults to 'timestamp'. This denotes the field that would be used in an equivalent SQL GROUP BY clause.
            aggregation_function(str): Defaults to 'count'. This is the aggregation function applied on the data. Must be one of ['count','avg','sum','min','max']
            aggregation_field(str): Defaults to 'id'. Specifies the column that would have been specified in the aggregation function in SQL
            field_options(dict): (Optional) An optional dictionary specifying field operation options; currently only the CAST operation is supported.
                For example:
                ```
                    {
                        CAST: {
                            target_field: 'timestamp'
                            target_type: 'date'
                        }
                    }
                ```
                target_type must be one of ['date','']
        Returns:
            A Pandas DataFrame object containing aggregated query results.
        """
        aggregation_function_map = {
            "count": func.count,
            "sum": func.sum,
            #"avg": func.avg,
            "min": func.min,
            "max": func.max
        }

        # Validate parameters against data model
        try:
            getattr(self.table_model, group_by_field)
        except AttributeError:
            self.logger.warning(f"An invalid group_by_field, '{group_by_field}', was specified; an empty dataframe will be returned.")
            return pd.DataFrame()
        if aggregation_function not in aggregation_function_map:
            self.logger.warning(f"An invalid aggregation_function value, '{aggregation_function}', was specified; an empty dataframe will be returned.")
            return pd.DataFrame()
        try:
            getattr(self.table_model, aggregation_field)
        except AttributeError:
            self.logger.warning(f"An invalid aggregation_field, '{aggregation_field}', was specified; an empty dataframe will be returned.")
            return pd.DataFrame()
       
        # Perform the aggregation query against the table
        with Session(self.engine) as session:
            
            if field_options:
                # Handle any field options eg. CASTs
                if 'CAST' in field_options:
                    target_field = field_options['CAST'].get('target_field')
                    target_type = field_options['CAST'].get('target_type')
                    if not target_field or not target_type or target_field not in [group_by_field, aggregation_field]:
                        self.logger.warning("Invalid CAST options were specified for an aggregation query; they will be ignored.")
                        return pd.DataFrame()
                    else:
                        if target_type == 'date':
                            group_by_field = cast(getattr(self.table_model, group_by_field), Date) if target_field == group_by_field else getattr(self.table_model, group_by_field)
                            aggregation_field = cast(getattr(self.table_model, aggregation_field), Date) if target_field == aggregation_field else getattr(self.table_model, aggregation_field)
                        elif target_type == 'int':
                            group_by_field = cast(getattr(self.table_model, group_by_field), Integer) if target_field == group_by_field else getattr(self.table_model, group_by_field)
                            aggregation_field = cast(getattr(self.table_model, aggregation_field), Integer) if target_field == aggregation_field else getattr(self.table_model, aggregation_field)
            else:
                group_by_field = getattr(self.table_model, group_by_field)
                aggregation_field = getattr(self.table_model, aggregation_field)
            # Define and execute the query
            aggregation_function = aggregation_function_map[aggregation_function]
            aggregation_query = session.query(
                group_by_field.label("group"), 
                aggregation_function(aggregation_field).label("aggregation")
            ).group_by(group_by_field)                            
            df = pd.read_sql(aggregation_query.statement, con=self.engine)
            # Drop SQLAlchemy-specific metadata
            if '_sa_instance_state' in df.columns:
                df = df.drop(columns=["_sa_instance_state"])
            return df