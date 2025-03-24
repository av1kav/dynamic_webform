import os 
import pandas as pd

class BaseFileSchema:
    """
    (Experimental) A base class for schema representations of tables. Meant to eventually replace direct accesses of the form 
    configuration file when generating field HTML, etc.
    """
    fields = []
    def __init__(self):
        pass
    def __repr__(self):
        pass

class ExcelFileSchema(BaseFileSchema):
    """
    (Experimental) An Excel-specific handler for form configuration files that are created as Excel sheets. Meant to eventually replace
    direct accesses of the form configuration Excel sheet when generating field HTML, collecting form responses etc.
    """
    def __init__(self, folder, filename):
        super().__init__()
        filepath = os.path.join(folder, filename)

def generate_schema_from_config_file(config_folder='formbuilder',config_filename='wny_config.xlsx'):
    """
    A utility function to parse a form_config Excel sheet into a dict of fields. This schema dict will be used as a collection
    template for collecting form responses.

    Args:
        config_folder(str): A string containing the folder under /config that contains the form_config Excel sheet.
        config_filename(str):  A string containing the actual filename of the form_config Excel sheet.
    
    Returns:
        A dictionary with keys corresponding to backend_field_names and values of None to use as a data collection template for 
        form submissions.
    """
    current_folder = os.path.dirname(os.path.abspath(__file__))    
    relative_config_file_path = os.path.join(current_folder,'..',config_folder,config_filename)
    config_workbook = pd.ExcelFile(relative_config_file_path)
    form_pages = pd.read_excel(config_workbook, 'Pages').set_index('page_number').to_dict(orient='index')
    form_fields = pd.read_excel(config_workbook, 'Fields')
    backend_field_names = form_fields['backend_field_name'].to_list()
    form_schema = {key: None for key in backend_field_names}
    return form_schema

def extract_form_response_data_using_schema(request, form_schema):
    """
    A utility function that uses a data collection template (a dict of backend_field_names) that will be populated using the form
    response data.

    Args:
        request(flask.request): The form POST request containing form response information.
        form_schema(dict): A form data collection template.
    
    Returns:
        A populated form data collection template, with keys corresponding to backend_field_names and values populated with the 
        corresponding form submission information.
    """
    return {key: request.form.get(key) for key in form_schema}
