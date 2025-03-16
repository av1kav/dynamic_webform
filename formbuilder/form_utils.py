import yaml
import pandas as pd
import numpy as np
import os
from bs4 import BeautifulSoup as soup

from loggers.managers import LoggerManager

def prettify_raw_html(html_string, engine='bs4'):
    """
    Helper function to properly format generated raw HTML. Currently, only BeautifulSoup4's html.parser is supported.
    
    Args:
        html_string(str): A string of raw, unformatted HTML
        engine(str): (Default='bs4') The parsing engine to use. Currently, only BeautifulSoup4's html.parser is supported.

    Returns:
        A well-formatted HTML string.
    """
    if engine == 'bs4':
        return soup(html_string, features='html.parser').prettify()

def generate_html_for_field(field):
    """
    Utility function to generate a specific type of HTML for a specified field according to formatting information.

    Args:
        field(dict): A dict containing HTML formatting information about a form field. This information is sourced from the 
                     form_config Excel sheet and contains the following keys:

                     1. 'backend_field_name': The key against which the form submission data for this field is stored. Different
                        from the display name. This string must not contain any spaces.
                     2. 'field_label': The display name for the field; may contain spaces, web-safe characters etc.
                     3. 'required': A Yes/No field that controls whether a field is required to be populated in the form before submission.
                     4. 'field_type': One of 'input', 'select' or 'text'. Determines the corresponding HTML input element to be used.
                     5. 'data_type': An unused field that is primarily used for SQLAlchemy ORM purposes.
                     6. 'select_options': A list of choices to be rendered in HTML dropdown boxes when the field_type is 'select'.
    Returns:
        A HTML representation of the specified field, built according to the formatting information provided (see above)
    """
    logger = LoggerManager.get_logger()

    field_type = field.pop('field_type')
    modifier_keys = {
        'field_required': 'required' if field['required'].lower() == 'yes' else '',
        'field_required_style': 'required-field' if field['required'].lower() == 'yes' else '',
        'col_size_modifier': 'col-md-6' if field.get('group_id') else ''
    }   
    if field_type == 'input':    
        input_field_template = \
        """<div class="{col_size_modifier} mb-3">
            <label for="{backend_field_name}" class="form-label {field_required_style}">{field_label}</label>
            <input type="text" class="form-control" id="{backend_field_name}" name="{backend_field_name}" {field_required}>
        </div>"""
        return input_field_template.format(**{**modifier_keys, **field})
    elif field_type == 'select':
        option_list = '\n'.join([f"<option value=\"{option.strip()}\">{option.strip()}</option>" for option in field['select_options'].split(',')])
        select_field_template = \
        """<div class="{col_size_modifier} mb-3">
            <label for="{backend_field_name}" class="form-label {field_required_style}">{field_label}</label>
            <select class="form-select" id="{backend_field_name}" name="{backend_field_name}" {field_required}>
                {option_list}
            </select>
        </div>"""
        return select_field_template.format(**{'option_list': option_list, **modifier_keys, **field})
    elif field_type == 'text':
        text_field_template = \
        """<div class="{col_size_modifier} mb-3">
            <label for="{backend_field_name}" class="form-label {field_required_style}">{field_label}</label>
            <input type="text" class="form-control" id="{backend_field_name}" name="{backend_field_name}" {field_required}>
        </div>"""
        return text_field_template.format(**{**modifier_keys, **field})
    else:
        logger.error(f"Unknown field type '{field_type}' for field '{field['backend_field_name']}'")
        return ''

def generate_html_for_page(page_number, page_config, field_html):
    page_template = \
    """<div class="form-page" id="page{page_number}">
            <h4 class="mt-4" aria-level="2">{page_title}</h4>
            <p class="text-muted">{page_description}</p>
            {field_html}
       </div>"""
    return page_template.format(**{
        'page_number': page_number,
        'field_html': field_html,
        **page_config
        }
    )

def generate_html_for_input_group_start():
    return "<div class=\"row\">"

def generate_html_for_input_group_end():
    return "</div>"

def generate_form_html_from_config_file(config_folder='formbuilder',config_filename='wny_config.xlsx'):
    logger = LoggerManager.get_logger()
    logger.info("Attempting to generate form HTML using config file configured at {config_folder}/{config_filename}")
    config_filepath = os.path.join(config_folder, config_filename) if config_folder else config_filename
    config_workbook = pd.ExcelFile(config_filepath)
    form_pages = pd.read_excel(config_workbook, 'Pages').set_index('page_number').to_dict(orient='index')
    form_fields = pd.read_excel(config_workbook, 'Fields')
    generated_form_html = """"""
    for page_number, page_config in form_pages.items():
        # Step 1: Generate HTML for fields inside the page
        generated_field_html = """"""
        # Select subset of data that is associated with the current page, clean up missing group_id values and build a dictionary
        page_fields = form_fields.loc[form_fields['page_number'] == page_number].replace({np.nan:None}).to_dict(orient='records')
        current_group_id = None
        for i, field in enumerate(page_fields):
            if not field['group_id']:
                generated_field_html += generate_html_for_field(field)
            else:
                if current_group_id is None:
                    # First group on the page, so don't end any previous group
                    generated_field_html += generate_html_for_input_group_start()
                elif field['group_id'] != current_group_id:
                    # Non-first group on the page, so end the previous group and start a new one
                    generated_field_html += generate_html_for_input_group_end()
                    generated_field_html += generate_html_for_input_group_start()
                generated_field_html += generate_html_for_field(field)
                current_group_id = field['group_id']
        if current_group_id:
            # If at least 1 group has been created, the last group will need to be closed.
            generated_field_html += generate_html_for_input_group_end()
        # Step 2: Generate HTML for the page using the generated field HTML and page_config information
        generated_page_html = generate_html_for_page(page_number, page_config, generated_field_html)
        # Step 3: Append the generated page HTML to the final form HTML
        generated_form_html += generated_page_html
    # Step 4: Prettify and return the final form content HTML (pages and fields only)
    return prettify_raw_html(generated_form_html)