from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, abort, send_from_directory, send_file
from flask_login import LoginManager, login_user, logout_user, login_required
from datetime import datetime
import platform
from formbuilder.form_utils import generate_form_html_from_config_file
from formbuilder.schema_utils import generate_schema_from_config_file, extract_form_response_data_using_schema
from utils import User, role_required
from utils import read_instance_config, parse_user_auth_info_from_config, generate_websafe_session_id, l2_validations, l3_validations, get_ip_address, ip_info_check, send_session_id_reminder_email, is_valid_filename, read_uploaded_dataset, download_datastore_in_specific_format, generate_excel_template_from_schema
from datamodels.managers import  DatastoreManager
from loggers.managers import LoggerManager
from werkzeug.utils import secure_filename
import os
import glob

## Initialization ##
# Read instance config YAML and form schema
config = read_instance_config(config_folder='config', config_file_name='config.yaml')
form_schema = generate_schema_from_config_file(config_folder=os.path.join('config',config['form']['form_config_folder']),config_filename=config['form']['form_config_file_name'])

# Initialize logging
app_logger = LoggerManager.get_logger(config)

# Define Flask app and set app-level configs
app = Flask(__name__) 
app.secret_key = config['general']['flask_app_secret_key']

# Initialize datastore manager
datastore = DatastoreManager(app, config)

# Initialize login manager and authentication functions
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message_category = "warning"
user_auth_info = parse_user_auth_info_from_config(config)

@login_manager.user_loader
def load_user(user_id):
    """
    This function is here because it needs an instantiated LoginManager.
    """
    if user_id in user_auth_info:
        return User(**user_auth_info[user_id])
    
## App Routes ##
@app.route('/')
def form():
    """
    Main form-serving page that dynamically generates and renders a form.

    The page_load_time variable is used to calculate elapsed time, while session_id is
    displayed in an interactable element.

    Args:
        None

    Returns:
        None    
    """
    # Pass the current timestamp to the form as page load time
    page_load_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    session_id = generate_websafe_session_id(config['general']['websafe_session_id_size'])
    config_folder = os.path.join('config', config['form']['form_config_folder'])
    config_filename = config['form']['form_config_file_name']
    form_content_html = generate_form_html_from_config_file(config_folder=config_folder, config_filename=config_filename)
    return render_template('dynamic_form.html', page_load_time=page_load_time, session_id=session_id,form_content_html=form_content_html)

@app.route('/submit', methods=['POST'])
def submit():
    """
    Form submission route that accepts data into the datastore (UPSERT by default).

    Once form data is extrected from the POST request, additional metadata and validation 
    fields are added and the user is redirected to the 'Thank You' page.

    Args:
        None
    
    Returns:
        None
    """
    if request.method == 'POST':
        # Extract data from the form submission using the defined form schema
        form_data = extract_form_response_data_using_schema(request,form_schema)
        
        # Raise an error if the Session ID is not in the response for some reason
        if not request.form.get('session_id_form_field'):
            raise RuntimeError('No session_id populated.')        

        # Add form data to baseline data row containing ID and timestamp
        submission_data = {
            "id": request.form.get('session_id_form_field'),
            "timestamp": datetime.now(),
        }
        submission_data.update(form_data)

        # Optionally add advanced analytics form validation features based on config
        advanced_analytics_form_validation_options = config['advanced_analytics']
        if advanced_analytics_form_validation_options:
            if 'sessiondata' in advanced_analytics_form_validation_options.keys():
                app_logger.info("Found 'sessiondata' key in config; enabling session metadata recording.")
                # Session data 
                _name = request.form.get('_name','Not Enabled') # Honeypot field
                user_agent = request.headers.get('User-Agent')
                os_system = platform.system() + " " + platform.release()  # Operating system
                ip_address = get_ip_address()
                # Calculate time taken to fill the form
                form_load_time = request.form.get('form_load_time')
                form_load_dt = datetime.strptime(form_load_time, '%Y-%m-%d %H:%M:%S')
                form_submission_time = datetime.now()
                time_taken = (form_submission_time - form_load_dt).total_seconds()
                submission_data.update({
                    "user_agent": user_agent,
                    "operating_system": os_system,
                    "ip_address": ip_address,
                    "hpfm": _name, # Honeypot Field Modified?
                    "elapsed_time": time_taken
                })
                submission_data.update(ip_info_check(ip_address, form_validation_options=advanced_analytics_form_validation_options))
            if 'L2' in advanced_analytics_form_validation_options.keys():
                app_logger.info("Found 'L2' key in config; enabling L2 form validation metadata recording.")
                submission_data.update(l2_validations(submission_data))
            if 'L3' in advanced_analytics_form_validation_options.keys():
                app_logger.info("Found 'L3' key in config; enabling L3 form validation metadata recording.")
                submission_data.update(l3_validations(submission_data))
        
        # Save data to datastore
        datastore.add_data(submission_data)
        # Save fields in session dict to re-display once on the thank you message
        session['session_id_for_reminder_email'] = submission_data.get('id')
        session['applicant_email_for_reminder_email'] = submission_data.get('email')
        return redirect(url_for('thank_you'))

@app.route('/thank-you')
def thank_you():
    """
    Mainly static page that renders after a form is submitted; also sends a reminder email to the applicant's
    email address if configured to do so. Reminds the user of the session ID that was just used for submission
    of the form either way, in case the user did not fill out an email address in submission.

    Args:
        None
    
    Returns:
        None
    """        
    # By default, assume the page is directly being accessed i.e. not from a redirect after a form submission and define the appropriate message
    session_id = ''
    message = 'This page should only be directly viewed after submitting a form, and it appears that this has not occurred. Reach out to the team for support if you believe this happened in error.'
    # If the page is being displayed after a successful submission, the session will have a session_id_for_reminder_email key
    if session.get('session_id_for_reminder_email'):
        # If the email field was filled out, the session will have a applicant_email_for_reminder_email key
        if session.get('applicant_email_for_reminder_email'):
            session_id = session.pop('session_id_for_reminder_email')
            destination_address = session.pop('applicant_email_for_reminder_email')
            send_session_id_reminder_email(destination_address=destination_address, session_id=session_id, config=config)
            message = f"Thank you for your response. We have sent the session ID of this submission to '{destination_address}'. Please use it to restore the session if needed, and contact support if you did not receive the email. For reference, the session ID is also displayed below."
            session.pop('applicant_email_for_reminder_email')
        # If the email field was not filled out, remind the user of the session ID but don't send an email.
        else:
            session_id = session.pop('session_id_for_reminder_email')
            message = 'Since the applicant_email field was not filled out, we are unable to email you the session ID for your submission. Please copy the session ID below, as it will not be shown again.'
    
    return render_template('thank_you.html', session_id=session_id, message=message)

@app.route('/load_form_data', methods=['POST'])
def load_form():
    """
    App route to populate the fields a rendered form from a record in the database using the session_id as a key. This
    route is not meant to be accessed directly by the user and is a potential security vulnerability.

    Args:
        None
    
    Returns:
        None
    """
    # Pull session ID from request
    session_id = request.json.get("session_id")
    if not session_id:
        return jsonify({"error": "No session code provided."}), 400
    # Retrieve data for the specified session_id, or return 404
    df = datastore.read_data(id=session_id)
    if df.empty:
        return jsonify({"error": "Session code not found."}), 404
    return df.to_dict(orient="records")[0]

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    User authentication app route. Uses flask-login management to authenticate users
    based on the credential values configured in the instance configuration YAML.

    Args:
        None
    
    Returns:
        None
    """
    if request.method == 'POST':
        username = str(request.form.get('username'))
        password = str(request.form.get('password'))
        app_logger.info('Attempting to authenticate:', username, password)
        if username in user_auth_info and user_auth_info[username]['password'] == password:
            current_user = load_user(username)
            login_user(current_user)
            return redirect(url_for('dashboard'))            
        else:
            flash('Incorrect password. Please try again.','danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    """
    Logout app route to remove session authentication variables.

    Args:
        None
    
    Returns:
        None
    """
    logout_user()
    flash("You have been logged out.",'info')
    return redirect(url_for('login'))

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    """
    Login-protected dashboard page for viewing submissions, uploading/downloading data and general 
    management. Some features/functions will be enabled only if roles permit.
    
    Args: 
        None
    
    Returns:
        None
    """
    df = datastore.read_data()
    formatting_options = {
        'classes': ['table','table-striped', 'table-bordered'],
        'index': False
    }
    if request.method == 'POST':       
        data = request.get_json()
        target_format = data.get('format') 
        if target_format:
            # Key "format" exists, download datastore as file
            return download_datastore_in_specific_format(datastore=datastore, target_format=target_format)
    elif request.method == 'GET':
        # Query aggregated data for submission time trend
        submissionTimeTrend_result = datastore.read_aggregated_data(
            group_by_field='timestamp',
            aggregation_function='count',
            aggregation_field='id',
            field_options={
                'CAST': {
                    'target_field': 'timestamp',
                    'target_type': 'date'
                }
            }
        )
        submissionTimeTrend_labels = [x.strftime("%m-%d-%y") for x in submissionTimeTrend_result['group'].to_list()]
        submissionTimeTrend_data = submissionTimeTrend_result['aggregation'].to_list()

        # Query aggregated data for submission time trend
        breakdown_field = 'import_export'
        categoryDonut_1_result = datastore.read_aggregated_data(
            group_by_field=breakdown_field,
            aggregation_function='count',
            aggregation_field='id'
        )
        categoryDonut_1_labels = categoryDonut_1_result['group'].to_list()
        categoryDonut_1_data = categoryDonut_1_result['aggregation'].to_list()
        categoryDonut_1_title = f"Breakdown by {breakdown_field}"

    return render_template(
        'dashboard.html',
        form_submissions=df.to_html(**formatting_options),
        submissionTimeTrend_labels=submissionTimeTrend_labels,
        submissionTimeTrend_data=submissionTimeTrend_data,
        categoryDonut_1_labels=categoryDonut_1_labels,
        categoryDonut_1_data=categoryDonut_1_data,
        categoryDonut_1_title=categoryDonut_1_title
    )

@app.route("/upload", methods=["GET", "POST"])
@login_required
@role_required(authorized_roles=["admin"])
def upload_file():
    """
    App route to handle data uploads into the database. Take caution to ensure the provided file has the correct headers;
    only valid field names will be ingested while invalid ones will simply be ignored.

    Args:
        None
    
    Returns:
        None
    """
    if request.method == "POST":
        if "file" not in request.files:
            return jsonify({"error": "No file part"}), 400
        
        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No selected file"}), 400
        
        if file and is_valid_filename(file.filename, config=config):
            filename = secure_filename(file.filename)
            file_path = os.path.join(config['datastore']['data_upload']['data_upload_folder'], filename)
            file.save(file_path)
            bulk_upload_data = read_uploaded_dataset(file_path, config=config)
            datastore.add_bulk_data(bulk_upload_data=bulk_upload_data)
            return jsonify({"message": "Ingestion complete."}), 200
        else:
            app_logger.warning(f"Invalid file type when attempting upload for ingestion: {file.filename}")
            return jsonify({"error": "Invalid file type."}), 400

    return render_template("upload.html")  # Render the HTML upload form

@app.route('/generate_data_upload_template')
def generate_data_upload_template():
    """
    Separate app route that simply returns an Excel-format template that contains all fields in the current
    form schema. Useful when uploading data into the datastore.

    NOTE: This app route needs to be separate since it is serving binary data.
    """    
    return send_file(
        generate_excel_template_from_schema(form_schema=form_schema),
        download_name="data_upload_template.xlsx", 
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@login_required
@role_required(authorized_roles=["viewer","admin"])
@app.route('/docs/<path:filename>')
def serve_sphinx_docs(filename="index.html"):
    parent_dir = config['general']['sphinx_docs']['parent_dir']
    sub_path = config['general']['sphinx_docs']['sub_path']
    suffix = "*.*"
    safe_file_path = os.path.join(parent_dir, sub_path)
    static_resources_path = os.path.join(safe_file_path,'_static')
    # glob files to build an allow-list for the actual HTML files as well as the associated static content
    # in order to prevent path traversal attacks. See CVE-2021-43494.
    ALLOW_LIST = [x.split('/')[-1] for x in glob.glob(os.path.join(safe_file_path,suffix))] +\
                 ['_static/' + x.split('/')[-1] for x in glob.glob(os.path.join(static_resources_path,suffix))]
    if filename not in ALLOW_LIST:
        abort(403)    
    return send_from_directory(safe_file_path, filename)

if __name__ == '__main__':
    app.run(debug=True)