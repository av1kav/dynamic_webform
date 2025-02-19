import os 
import pandas as pd
from pprint import pprint

class BaseFileSchema:
    fields = []
    def __init__(self):
        pass
    def __repr__(self):
        pass

class ExcelFileSchema(BaseFileSchema):
    def __init__(self, folder, filename):
        super().__init__()
        filepath = os.path.join(folder, filename)

def generate_schema_from_config_file(config_folder='formbuilder',config_filename='wny_config.xlsx'):
    config_filepath = os.path.join(config_folder, config_filename)
    config_workbook = pd.ExcelFile(config_filepath)
    form_pages = pd.read_excel(config_workbook, 'Pages').set_index('page_number').to_dict(orient='index')
    form_fields = pd.read_excel(config_workbook, 'Fields')
    backend_field_names = form_fields['backend_field_name'].to_list()
    form_schema = {key: None for key in backend_field_names}
    return form_schema

def extract_form_response_data_using_schema(request, form_schema):
    return {key: request.form.get(key) for key in form_schema}
