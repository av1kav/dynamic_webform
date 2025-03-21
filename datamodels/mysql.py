from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, select
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.dialects.mysql import insert
from utils import generate_websafe_session_id
from datetime import datetime
from sqlalchemy.orm import Session
from flask_migrate import migrate, Migrate, init, upgrade
import mysql.connector
import pandas as pd
import os

from loggers.managers import LoggerManager

SQLALCHEMY_TYPE_MAPPING = {
    "INTEGER": Integer,
    "STRING": String(255),
    "FLOAT": Float,
    "BOOLEAN": Boolean
}

db = SQLAlchemy()

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
    """
    def __init__(self, app, config):
        """
        Set up a MySQL connection, initialize the ORM engine and use Alembic to perform any necessary migrations.

        Args:
            app(Flask): The Flask app implementing this Datastore instance.
            config(dict): The full contents of the config.yaml configuration file
        Returns:
            None
        """
        self.app = app
        self.db = db
        self.config = config
        self.table_name = self.config['form']['form_config_file_name'].split('.')[0]
        self.table_model = self.generate_table_orm_from_config_file(config_folder='form_config',config_filename=self.config['form']['form_config_file_name'])  
        self.migrate = Migrate(self.app,self.db)
        self.logger = LoggerManager.get_logger()

        # Set up MYSQL connection parameters
        mysql_config_params = self.config['datastore']['datastore_params']
        self.sqlalchemy_database_uri = self.generate_database_uri_from_config(mysql_config_params=mysql_config_params)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = self.sqlalchemy_database_uri
        self.logger.info(f"Added SQLAlchemy URI to app config")
        for key, value in mysql_config_params.get('mysql_sqlalchemy_engine_options',{}).items():
            app.config[key] = value
            self.logger.info(f"Added {key}={value} to app config")
        
        # Initialize the ORM engine and track schema modifications
        self.db.init_app(self.app)
        self.migrate.init_app(self.app, self.db)
        if not os.path.exists(os.path.join('migrations','script.py.mako')):
            self.logger.info('Initial setup, no migrations found. Creating new MySQL table from form_config Excel sheet.')
            with self.app.app_context():
                self.db.create_all()
                init()
        self._refresh_table_schema() 
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
        Generates an Object-Relational Mapper (ORM) that is an object representation of the actual database table. Generated 
        dynamically using the form_config Excel sheet, and is used to control data operations on the underlying table.

        Args:
            config_folder(str): (Optional, default='formbuilder') The name of the folder, under the config/ directory, 
                                containing the form_config Excel sheet.
            config_filename(str): (Optional, default='wny_config.xlsx') The name of the actual Excel file containing form
                                  configuration information. Essentially controls the schema of the database table and ORM,
        
        Returns:
            A SQLAlchemy db.Model instance (ORM)
        """
        # Define the default table schema with ID and timestamp fields
        attributes = {
            "__tablename__": config_filename.split('.')[0],
            "__table_args__": {'extend_existing': True},
            "id": Column(Integer, primary_key=True),
        }
        attributes['id'] = Column(String(255), nullable=False, primary_key=True)
        attributes['timestamp'] = Column(DateTime, nullable=False, primary_key=False)

        # Then build the remainder of the schema dynamically from the form config file
        config_folder = os.path.join('config',config_folder)
        config_filepath = os.path.join(config_folder, config_filename) if config_folder else config_filename
        config_workbook = pd.ExcelFile(config_filepath)
        form_fields = pd.read_excel(config_workbook, 'Fields')
        for _, row in form_fields.iterrows():
            col_name = row["backend_field_name"]
            col_type = SQLALCHEMY_TYPE_MAPPING.get(row["data_type"], String(255))
            nullable = True if row["required"] == 'No' else False
            attributes[col_name] = Column(col_type, nullable=nullable, primary_key=False)
        return type(attributes['__tablename__'].capitalize(), (db.Model,), attributes)

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
    
    def _refresh_table_schema(self):
        """Helper function to track and auto-apply schema changes using flask-migrate (Alembic)."""
        with self.app.app_context():
            migrate(message="automigration")
            upgrade()
    
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
            self.logger.warrning("The 'id' field was not found in the uploaded dataset. New IDs will be generated.")
            bulk_upload_data['id'] = [generate_websafe_session_id(self.config['general']['websafe_session_id_size']) for _ in range(len(bulk_upload_data))]
        if 'timestamp' not in bulk_upload_data_columns:
            self.logger.warrning("The 'timestamp' field was not found in the uploaded dataset. New timestamps will be generated.")
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
