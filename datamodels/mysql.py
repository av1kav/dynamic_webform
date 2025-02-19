from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, select
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.dialects.mysql import insert
from utils import generate_websafe_session_id
from datetime import datetime
from sqlalchemy.orm import Session
from flask_migrate import Migrate
import mysql.connector
import pandas as pd
import os

SQLALCHEMY_TYPE_MAPPING = {
    "INTEGER": Integer,
    "STRING": String(255),
    "FLOAT": Float,
    "BOOLEAN": Boolean
}

db = SQLAlchemy()

class MySQLDatastore:
    def __init__(self, app, config):
        self.app = app
        self.db = db
        self.config = config
        mysql_config_params = self.config['datastore']['datastore_params']
        self.sqlalchemy_database_uri = self.generate_database_uri_from_config(mysql_config_params=mysql_config_params)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = self.sqlalchemy_database_uri
        for key, value in mysql_config_params.get('mysql_sqlalchemy_engine_options',{}).items():
            app.config[key] = value
        self.table_name = self.config['form']['form_config_file_name'].split('.')[0]
        self.table_model = self.generate_table_orm_from_config_file(config_folder='form_config',config_filename=self.config['form']['form_config_file_name'])  
        
        # Initialize the ORM engine and track schema modifications
        self.db.init_app(self.app)
        if not os.path.exists('migrations'):
            print('INFO: Initial setup, no migrations folder found. Creating new MySQL table.')
            self.db.create_all()
            from flask_migrate import init
            init()
        self._refresh_table_schema()
        self.create_engine()
    
    def create_engine(self):
        self.engine = create_engine(self.sqlalchemy_database_uri, echo=True)

    def check_connection(self):
        pass
    
    def generate_database_uri_from_config(self, mysql_config_params):
        SQLALCHEMY_DATABASE_URI = "mysql+mysqlconnector://{username}:{password}@{hostname}/{databasename}".format(
            username=mysql_config_params['mysql_username'],
            password=mysql_config_params['mysql_password'],
            hostname=mysql_config_params['mysql_hostname'],
            databasename=mysql_config_params['mysql_database']
        )
        return SQLALCHEMY_DATABASE_URI
    
    def generate_table_orm_from_config_file(self, config_folder='formbuilder',config_filename='wny_config.xlsx'):
        
        # Define the default table schema with ID and timestamp fields
        attributes = {
            "__tablename__": config_filename.split('.')[0],
            "__table_args__": {'extend_existing': True},
            "id": Column(Integer, primary_key=True),
        }
        attributes['id'] = Column(String(255), nullable=False, primary_key=True)
        attributes['timestamp'] = Column(DateTime, nullable=False, primary_key=True)

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
        mysql_config_params = self.config['datastore']['datastore_params']
        self.con = mysql.connector.connect(
                user=mysql_config_params['mysql_username'],
                password=mysql_config_params['mysql_password'],
                host=mysql_config_params['mysql_hostname'],
                database=mysql_config_params['mysql_database']
        )
        self.con.close()
    
    def _refresh_table_schema(self):
        # Track and auto-apply schema changes using flask-migrate (Alembic)
        migrate = Migrate(self.app,self.db)   
        with self.app.app_context():
            from flask_migrate import migrate, upgrade
            migrate(message="automigration")
            upgrade()
    
    def upsert_data(self, submission_data):
        # Create a session
        with Session(self.engine) as session:
            # Create an instance of the dynamic model
            stmt = insert(self.table_model).values(**submission_data)
            upsert_stmt = stmt.on_duplicate_key_update(**submission_data)
            session.execute(upsert_stmt)
            session.commit()
            print(f"Upserted row into {self.table_name}: {submission_data}")
    
    def upsert_bulk_data(self, bulk_upload_data):
        # Ensure the default id and timestamp fields are present in the dataframe 
        num_rows = len(bulk_upload_data)
        if 'id' not in bulk_upload_data.columns:
            bulk_upload_data['id'] = [generate_websafe_session_id(self.config['general']['websafe_session_id_size']) for _ in range(len(bulk_upload_data))]
        if 'timestamp' not in bulk_upload_data.columns:
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
            print(f"Bulk-upserted {num_rows} row(s) into {self.table_name}")

    def query(self, id=None):
        with Session(self.engine) as session:
            query = session.query(self.table_model)
            if id:
                query = query.filter_by(id=id)
            df = pd.read_sql(query.statement, con=self.engine)
            if '_sa_instance_state' in df.columns:
                df = df.drop(columns=["_sa_instance_state"])
            return df
