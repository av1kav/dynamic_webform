/** Runtime Variables */

let currentStep = 1;
const totalSteps = 5;
showPage(currentStep);
var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl, { trigger: 'manual' });
});

/** Main Functions */

function showPage(step) {
    /** The main page handler for the form. Also updates the progress bar. */
    const pages = document.querySelectorAll('.form-page');
    pages.forEach((page, index) => {
        page.classList.add('d-none');
        if (index === step - 1) page.classList.remove('d-none');
    });
    document.getElementById('prevBtn').style.display = step === 1 ? 'none' : 'inline-block';
    document.getElementById('nextBtn').style.display = step === totalSteps ? 'none' : 'inline-block';
    document.getElementById('submit-button').style.display = step === totalSteps ? 'inline-block' : 'none';
    updateProgressBar(step);
}
function nextPrev(n) {
    /** Handles "pagination" while validating each page for errors. */
    if (!validateForm()) return false;
    currentStep += n;
    if (currentStep > totalSteps) {
        return false;
    }
    showPage(currentStep);
    setTimeout(() => {
        window.scrollTo({top: 0, behavior: 'smooth'})
    }, 30);
}
function updateProgressBar(step) {
    /** Update the flex progress bar based on the page/step the user is currently on. */
    const progress = (step / totalSteps) * 100;
    document.getElementById("progress-bar").style.width = progress + "%";
}
function validateForm() {
    /** Validate form fields, scrolling the first field with an error into view. */
    const currentPage = document.querySelector(`#page${currentStep}`);
    const invalidFields = currentPage.querySelectorAll(".form-control:invalid");
    if (invalidFields.length > 0) {
        invalidFields[0].classList.add("is-invalid"); 
        invalidFields[0].scrollIntoView({ behavior: "smooth", block: "center" });
        return false;
    }
    // Remove any existing invalid class if there are no issues
    invalidFields.forEach(field => field.classList.remove("is-invalid"));
    return true;
}
function prepare_form_data(){
    /** Write the session ID for the form (either generated or resumed) into a hidden form field for data entry. */
    sessionID = document.getElementById("session_id_generated").value; // If a session is resumed, this value will be overwritten with the resumed sessionID. See loadFormData()
    sessionIDFormField = document.getElementById("session_id_form_field");
    sessionIDFormField.value = sessionID
};
function copySessionID() {
    /** Utility function to copy a session ID to the clipboard. */
    // From the field that generates new IDs every time
    const sessionIDField = document.getElementById("session_id_generated"); 
    const copyButton = document.getElementById('copyButton');
    sessionIDField.select();
    sessionIDField.setSelectionRange(0, 99999); // For mobile devices
    navigator.clipboard.writeText(sessionIDField.value);
    var tooltip = bootstrap.Tooltip.getInstance(copyButton);
    if (!tooltip) {
        tooltip = new bootstrap.Tooltip(copyButton, { trigger: 'manual', title: 'Copied!' });
    }
    tooltip.show();
    setTimeout(() => {
        tooltip.hide();
    }, 2000);
}
function loadFormData() {
    /** Restore form data for a previous session ID from the datastore. */
    // Attempt to pull a SessionID from the field that holds a target session ID
    sessionID_target_field = document.getElementById("target_session_id");
    const sessionID = sessionID_target_field.value;
    // If the field is blank
    if (!sessionID) {
        tooltip = new bootstrap.Tooltip(sessionID_target_field, { trigger: 'manual', title: 'Please enter a session ID in this field.'});
        document.getElementById('session-id-container-messages').value='Please enter a session ID in this field.'
        tooltip.show();
        setTimeout(() => {
            tooltip.hide();
            document.getElementById('session-id-container-messages').value=''
        }, 2000);
        return;
    }
    // If the field has an ID
    else {
        fetch("/load_form_data", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: sessionID })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                tooltip = new bootstrap.Tooltip(sessionID_target_field, { trigger: 'manual', title: 'Invalid session ID - please try again.' });
                document.getElementById('session-id-container-messages').value='Invalid session ID - please try again.'
                tooltip.show();
                setTimeout(() => {
                    tooltip.hide();
                    document.getElementById('session-id-container-messages').value=''
                }, 2000);
            } else {
                populateFormFields(data);
                tooltip = new bootstrap.Tooltip(sessionID_target_field, { trigger: 'manual', title: 'Session restored.' });
                document.getElementById('session-id-container-messages').value='Session restored.'
                tooltip.show();
                setTimeout(() => {
                    tooltip.hide();
                    document.getElementById('session-id-container-messages').value=''
                }, 2000);
                // Update the generated sessionID field to have the entered sessionID, and clear the target field contents
                sessionID_generated_field = document.getElementById("session_id_generated"); 
                sessionID_generated_field.value = sessionID; 
                sessionID_target_field.value="";
            }
        })
        .catch(err => {
            console.error("Error loading form data:", err);
        });
    }
};
function populateFormFields(form_data) {
    /** Utility function that populates form fields using retrieved data. */
    console.log(form_data)
    for (const [key, value] of Object.entries(form_data)) {
        const field = document.querySelector(`[name="${key}"]`);
        if (field) {
            field.value = value;
        }
    }
};

function downloadFile(format) {
    fetch("{{ url_for('dashboard') }}", {
        method: "POST",
        body: JSON.stringify({ format: format }),
        headers: {
            "Content-Type": "application/json"
        }
    })
    .then(response => response.blob())  // Convert to Blob for file download
    .then(blob => {
        const link = document.createElement("a");
        link.href = window.URL.createObjectURL(blob);
        link.download = `datastore.${format === 'excel' ? 'xlsx' : format}`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    })
    .catch(error => console.error("Download error:", error));
};