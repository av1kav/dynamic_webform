"""
utils.py
=========

This module provides utility functions, primarily for web-related operations.

Example:
    >>> from utils import is_valid_filename
    >>> is_valid_filename('abcnotafilename')
    False

When contributing to this module, ensure to write proper Google-style docstrings.

"""

from flask import request, redirect, url_for, send_file, flash
from bs4 import BeautifulSoup
import os
import hashlib
import secrets
import requests
import ipinfo
import pandas as pd
import yaml
import io

from .loggers.managers import LoggerManager

def download_datastore_in_specific_format(datastore, target_format):
    """
    Utility function to download the contents of the specified datastore 

    Args:
        datastore(datamodels.DatastoreManager): A DatastoreManager object configured with a backend Datastore.
        target_format(str): One of 'excel', 'parquet', 'json'. Specifies the format in which the datastore's contents should be downloaded. Ensure page JS specifies one of the keys above in any AJAX calls.
    
    Returns:
        A Flask URL redirect to the dashboard page.
    """
    df = datastore.read_data()
    buffer = io.BytesIO()
    if target_format == 'excel':
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name="data.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    elif target_format == 'parquet':
        df.to_parquet(buffer, index=False)
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name="data.parquet", mimetype="application/octet-stream")
    elif target_format == 'json':
        return df.to_json(orient='records',indent=4), 200, {'Content-Type': 'application/json'}
    else:
        flash('Unsupported format requested.', 'danger')
        return redirect(url_for('dashboard'))

def read_instance_config(config_folder='config', config_file_name='config.yaml'):
    """
    Utility function to read main configuration YAML from the config folder and return a verified configuration dict.
    By default, the function expects a file called config/config.yaml, and it is recommended to keep it that way.
    
    Args:
        config_folder(str): (Optional, default='config') The name of the folder containing the config YAML.
        config_file_name(str): (Optional, default='config.yaml') The name of the folder containing the config YAML.
    
    Returns:
        A dictionary containing all configuration information in the YAML file.
    """
    
    # Sphinx gods, look at the trouble you've caused
    current_folder = os.path.dirname(os.path.abspath(__file__))
    relative_config_file_path = os.path.join(current_folder,config_folder,config_file_name)
    with open(relative_config_file_path) as handle:
        config = yaml.safe_load(handle)
    ## TODO: Ensure critical keys available in dict
    return config

def read_uploaded_dataset(file_path, config):
    """
    Utility function to read an uploaded file, usually for bulk data uploads, as a Pandas DataFrame.

    Args:
        file_path(str): The path of the file to be read.
        config(dict): The main instance configuration (from YAML)
    
    Returns:
        A Pandas DataFrame containing the contents of the uploaded file.
    """
    if file_path.endswith('csv'):
        df = pd.read_csv(file_path)
    elif file_path.endswith('xlsx'):
        df = pd.read_excel(file_path)
    return df
    
def is_valid_filename(filename, config):
    """
    Utility function to check whether a filename is compliant with the formats specified in the instance configuration.

    Args:
        filename(str): The name of the file.
        config(dict): The main instance configuration (from YAML)

    Returns:
        True if the filename is compliant, and False otherwise.
    """
    allowed_formats = config['datastore'].get('data_upload').get('allowed_formats', [])
    if '.' in filename and filename.split('.')[-1] in allowed_formats:
        return True
    else:
        return False

def generate_websafe_session_id(size=8):
    """
    Utility function to generate and return a web-safe hexadecimal number of a specific size.
    
    Args:
        size(uint): (Optional, default=8) A positive integer value that specifies the length of the string to be generated. Should be
        at least 8 digits long, and will be force-set to 8 if the configured value is less than 8 for safety and stability.
    
    Returns:
        A generated hexadecimal string of the specified size. 
    """

    logger = LoggerManager.get_logger()
    if size < 8:
        logger.warning(f"The 'size' parameter provided to the generate_websafe_session_id method is less than {size}. For safety and stability, this value will be ignored and the default value of {size} will be used.")
    return secrets.token_hex(size)

def scrape_form_content(config_dict):
    """
    (Deprecated) Utility function to scrape the specified (static) form for field labels, input types and names return them as a dict. This method,
    while perfectly valid, is not currently in use since forms are now dynamic and cannot be parsed directly from source files. 
    
    Args:
        config_dict(dict): A helper configuration dict containing the following keys:
            1. form_id: The value of the HTML 'id' element in the <form> definition of the webform
            2. form_html_file: The name of the source file containing the (static) form HTML
    
    Returns:
        Form content parsed into a JSON document in the following format:
        [ 
                {
                    'field_label': '',
                    'field_name': '',
                    'field_type': '',
                    'input_type': '',
                    'is_required': '',
                    'select-options': [
                        {'backend_value': '', 'display_text': ''},
                    ]
                },    
            ]
    """

    if 'form_html_file' not in config_dict or 'form_id' not in config_dict:
        raise RuntimeError("Please ensure that both the 'form_id' and 'form_html_file' keys are specified in the provided config_dict.")

    form_html_file = config_dict['form_html_file']
    form_id = config_dict['form_id']

    with open(os.path.join('templates',form_html_file),'r') as handle:
        html_doc = handle.read()

    soup = BeautifulSoup(html_doc, 'html.parser')
    form = soup.find('form', id=form_id)
    if not form:
        raise ValueError(f"Form with ID '{form_id}' not found!")

    form_content = []
    for label in form.find_all('label'):
        field_id = label.get('for')
        input_field = form.find(id=field_id)
        if input_field:
            field_info = {
                'field_label': label.text.strip(),
                'field_name': input_field.get('name'),
                'field_type': input_field.name,
                'input_type': input_field.get('type'),
                'is_required': True if 'required' in input_field.attrs else False 
            }
            if input_field.name == 'select':
                field_info['select_options'] = [{'display_text': option.text.strip(), 'backend_value': option.get('value')} for option in input_field.find_all('option')]
            form_content.append(field_info)
    return form_content

def generate_html_table_using_form_content_html(form_content):
    """
    (Deprecated) Utility function to generate and return an HTML table string to neatly display form_content generated by the 
    scrape_form_content function.

    Args:
        json_data: A JSON document in the form:
            [ 
                {
                    'field_label': '',
                    'field_name': '',
                    'field_type': '',
                    'input_type': '',
                    'is_required': '',
                    'select-options': [
                        {'backend_value': '', 'display_text': ''},
                    ]
                },  
            ]
            that is generated using the scrape_form_content function.
    Returns:
        An HTML string containing a <table> that contains form information and can be rendered as HTML.
    """

    html_start="""
    <!-- Unique MD5 for versioning -->
    <p class="text-center text-muted">Version: {md5_string}</p>
    <!-- Form submission table --> 
    <table class="docs table table-responsive table-hover table-striped table-bordered">
        <thead>
            <tr>
                <th>#</th>
                <th>Backend Field Name</th>
                <th>Field Label</th>
                <th>Required?</th>
                <th>Field Type</th>
                <th>Select Options (if applicable)</th>
            </tr>
        </thead>
        <tbody>
    """
    html_end="""
        </tbody>
    </table>
    """

    rows = ""
    for i, field in enumerate(form_content):
        select_options = []
        if field.get('select_options'):
            select_options = [opt['display_text'] for opt in field['select_options']]
        rows += f"""
        <tr>
            <td>{i+1}</td>
            <td>{field['field_name']}</td>
            <td>{field['field_label']}</td>
            <td>{field['is_required']}</td>
            <td>{field['field_type']}</td>
            <td>{', '.join(select_options)}</td>
        </tr>
        """
    # Unique string for each version generated, for file versioning
    md5_string = hashlib.md5(rows.encode()).hexdigest()
    html_content = html_start.format(md5_string=md5_string) + rows + html_end
    return html_content

def ip_info_check(ip_address, form_validation_options):
    """
    Utility function to return a set of information fields for the specified IP address.

    This method retrieves metadata for the originating IP address of the connecting client (i.e. user IP)
    in order to be used for submission validation. Currently, all details returned by the IPInfo service
    are returned, but future revisions will require a list of keys that should be retrieved.

    Args:
        ip_address(str): A string containing the target IP address
        form_validation_options(dict): A subset of the instance configuration dict specifically for 
            advanced analytics options. Must contain a valid token against the key 'ipinfo_token'
            under the 'sessiondata' key in the instance configuration. For example:
            
            advanced_analytics:
                form_validations:
                    sessiondata:
                        ipinfo_token: abc6c819b58d
    Returns:
        A dict containing all metadata fron the IPInfo service for the specified IP
    """

    logger = LoggerManager.get_logger()
    access_token = form_validation_options['sessiondata'].get('ipinfo_token')
    if access_token:
        handler = ipinfo.getHandler(access_token)
        details = handler.getDetails(ip_address).all
        return details
    else:
        logger.warning("An ipinfo access token was not specified under the 'sessiondata' key. Specify a valid token value for the  ipinfo_token key under the sessiondata config, or see docs for ip_info_check().")
        
def get_ip_address():
    """
    Utility function to extract and return client session IP address from request headers.
    
    Args:
        None
    Returns:
        IP address of the user/client that initiated the request. 
    """
    if request.headers.get('X-Forwarded-For'):
        ip = request.headers.get('X-Forwarded-For').split(',')[0]
    else:
        ip = request.remote_addr
    return ip

def l1_validations(session_info):
    """
    (Experimental) Level-1 validations on session data.
    
    This method performs a set of validations on the provided session metadata 
    and returns a dictionary with results. The list of validations is arbitrary
    and can be found in project documentation.
    
    Args:
        session_info: A dict containing session metadata
    Returns:
        A dict containing validations and their results. 

    This method is currently a stub and returns an empty dictionary.
    """
    return {}

def l2_validations(session_info):
    """
    (Experimental) Level-2 validations on session data.

    This method performs a set of validations on the provided session metadata 
    and returns a dictionary with results. The list of validations is arbitrary
    and can be found in project documentation.

    Args:
        session_info: A dict containing session metadata
    Returns:
        A dict containing validations and their results.  
    """
    results = {}
    # Honeypot field modification check
    results['honeypot_validation_pass'] = True if session_info['hpfm'] == 'n' else False
    return results

def l3_validations(session_info):
    """
    (Experimental) Level-3 validations on session data.

    This method performs a set of validations on the provided session metadata 
    and returns a dictionary with results. The list of validations is arbitrary
    and can be found in project documentation.

    Args:
        session_info: A dict containing session metadata
    Returns:
        A dict containing validations and their results.  
    
    This method is currently a stub and returns an empty dictionary.
    """
    results = {}

    # Elapsed Time validation
    elapsed_time = session_info['elapsed_time']
    results['elapsed_time_validation_pass'] = False if elapsed_time < 15.0 else True 
    # Final model output
    if not results['elapsed_time_validation_pass']: # TODO: Actually implement a model here instead of hardcoding
        results['elapsed_time_validation_pass'] = False
    return results

def send_session_id_reminder_email(destination_address, session_id, config):
    """
    Utility function to send a reminder email to users who submit the web form, even partially, to the specified destination
    email address. The specific form field that contains this address is not fixed and so is up to the programmer to pass into
    this utility function.

    Args:
        destination_address(str): The destination email address to which the reminder will be sent
        session_id(str): The session_id of the session in which the form submission was made.
    
    Returns:
        None
    """

    logger = LoggerManager.get_logger()
    email_config = config.get('email')
    if email_config and 'sender_address' in email_config and 'provider' in email_config:
        provider_name = email_config['provider']['provider_name']
        logger.info("Configured email provider: {provider_name}")
        API_URL = email_config['provider']['http_service_api_url']
        FROM_EMAIL_ADDRESS = email_config['sender_address']
        api_key = email_config['provider']['api_key']
        to_address = destination_address
        
        subject = 'Submission Reminder'
        message = f"Thank you for your form submission!\n\n Your session id was {session_id}. If you would like to pick up where you left off, please use it to restore your session.\n\nUB SOM Research"

        resp = requests.post(
            API_URL,
            auth=("api", api_key),
            data={
                "from": FROM_EMAIL_ADDRESS,
                "to": to_address,
                "subject": subject,
                "text": message
            }
        )
        if resp.status_code == 200:
            logger.info(f"Successfully sent an email to '{to_address}' via {provider_name} API.")
        else:
            logger.warning(f"Email provider API response failed: {resp.text}")
    else:
        logger.warning("The 'sender_address' and 'provider' keys were not configured correctly for email functionality. Aborting email attempt.")