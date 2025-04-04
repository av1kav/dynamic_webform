.. dynamic_webform documentation master file, created by
   sphinx-quickstart on Sat Mar 22 13:05:36 2025.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

dynamic_webform documentation
=============================

Beta Test
---------
1. What are dynamic webforms? No-code solution to form data management. You define and manage a configuration, and the form fields, database and API management are handled by the system. Users can freely submit and update their data using a session-ID token, and can be configured to receive email reminders. Members of the SOM Research team can then perform actions based on their role permissions.
2. All websites need to run on some sort of hosting platform. We are using PythonAnywhere because it is free and gives us database access. Only admins will have credentials to log into the web server and manage the site (change the form fields, upload data into the database)
3. The data platform has two configuration files that users will need to edit. 
    1. The instance configuration YAML: A YAML file with credentials needed to initialize the web server application, database keys, form validation/analytics features etc. 
    2. The form config Excel: An Excel sheet that contains all the fields that should be contained in the dynamic webform. The database will automatically be brought in sync with the columns in this file to ensure automated form data management.
4. Admins have privileges to bulk-insert data as well, formats of which are also controlled by the config. This can be both for new data as well as updating existing data
    1. When bulk-inserting new data, do not include the 'id' and 'timestamp' fields
    2. When bulk-updating existing data, include the 'id' and 'timestamp' fields, ensuring they are filled out for all rows
5. User story walkthrough:
    1. Viewing summary analytics (summary graphs and charts)
        1. Configuring the dynamic donut breakdown chart
    2. Viewing form submission history
        1. Exporting data from the database
    3. Uploading new data into the database
        1. Type restrictions in the config
        2. Dataset size limitations
    4. Viewing documentation pages
    5. Uploading the form configuration excel (i.e. changing what the form looks like)
        1. Min-5 page requirement
        2. Reminder to reload
    6. Configuring the instance configuration file
        1. Managing server-side config variables
        2. Reminder to reload
    7. Generating documentation
        1. Generating rst sources
        2. Generating HTML
        3. VCS sync and Reminder to reload
    8. Syncing code changes from VCS
        1. Git and current hosting target
        2. Eventual plan: host UB VCS system

API Reference
-------------

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   dynamic_webform

Indices and Search
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`