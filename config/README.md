# Configuration

This application requires two individual configuration files within this folder - one at the same level as this md file and another under a folder called 'form_config'. Here's an example:

```
README.md
config.yaml
form_config/
    form.xlsx
```

1. **Instance Configuration:** A YAML file called config.yaml that sits within this directory, containing all required instance-level configuration such as database credentials, user login information, form and email settings etc. This does not control the fields in the actual form; for that, you'd need the form configuration sheet (see below)

2. **Form Configuration Sheet:** An Excel workbook (```.xslx```) that has a short name with no spaces, e.g. ```form.xlsx```. This file contains all the necessary information needed to automatically generate a five-page form with fields that can be regular text inputs, dropdown boxes, textareas etc. This workbook must have two sheets called "Pages" and "Fields" (case-sensitive).
    - The "Pages" sheet should have only 3 headers: 'page_number', 'page_title' and 'page_description'.
    - The "Fields" sheet should only have 7 headers: 'backend_field_name', 'field_label', 'required', 'field_type', 'data_type', 'select_options', 'page_number' and 'group_id'.
        - The 'select_options' column is only filled out when the 'field_type' is 'select', and denotes the options that would appear in a dropdown box. Add options by separating them with a comma; if a particular option contains a comma, enclose it in double-quotes to prevent it from showing up as two options (e.g "Alphabet, Inc." )

**NOTE:** The ```form_config``` folder and the form configuration sheet can both be named other values - they must also be updated appropriately under the 'form' key in the instance configuration (```config.yaml```).