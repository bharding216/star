"use strict";
console.log('Registration script loaded');
function validatePassword(password) {
    if (password.length < 8) {
        return false;
    }
    if (!/[A-Z]/.test(password)) {
        return false;
    }
    if (!/[0-9]/.test(password)) {
        return false;
    }
    return true;
}
function validatePasswordMatch(password1, password2) {
    return password1 === password2;
}
function validateEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}
function validatePhone(phone) {
    const phoneRegex = /^\d{10}$/;
    return phoneRegex.test(phone);
}
const individualRadio = document.getElementById('individual_radio');
const companyRadio = document.getElementById('company_radio');
const ssnInput = document.getElementById('ssn_div');
const einInput = document.getElementById('ein_div');
const dunsInput = document.getElementById('duns_div');
if (individualRadio && companyRadio && ssnInput && einInput && dunsInput) {
    individualRadio.addEventListener('change', () => {
        if (individualRadio.checked) {
            ssnInput.style.display = 'block';
            einInput.style.display = 'none';
            dunsInput.style.display = 'none';
        }
    });
    companyRadio.addEventListener('change', () => {
        if (companyRadio.checked) {
            ssnInput.style.display = 'none';
            einInput.style.display = 'block';
            dunsInput.style.display = 'block';
        }
    });
}
// Add real-time validation for all form fields
function setupRealTimeValidation() {
    const form = document.querySelector('form');
    if (!form)
        return;
    const inputs = form.querySelectorAll('input');
    inputs.forEach(input => {
        input.addEventListener('input', function () {
            validateInput(this);
        });
    });
}
// Track validation state of all fields
const fieldValidationState = {};
function validateInput(input) {
    var _a, _b;
    const value = input.value.trim();
    let isValid = true;
    let errorMessage = '';
    switch (input.name) {
        case 'email':
            isValid = validateEmail(value);
            errorMessage = 'Please enter a valid email address';
            break;
        case 'phone':
            isValid = validatePhone(value);
            errorMessage = 'Please enter a valid 10-digit phone number';
            break;
        case 'password1':
            isValid = validatePassword(value);
            errorMessage = 'Password must be at least 8 characters with 1 uppercase letter and 1 number';
            break;
        case 'password2':
            const password1 = document.querySelector('[name="password1"]');
            isValid = validatePasswordMatch(password1.value, value);
            errorMessage = 'Passwords do not match';
            break;
        case 'ssn':
            isValid = /^\d{9}$/.test(value);
            errorMessage = 'Please enter a valid 9-digit SSN';
            break;
        case 'ein':
            isValid = /^\d{9}$/.test(value);
            errorMessage = 'Please enter a valid 9-digit EIN';
            break;
        case 'duns':
            isValid = value === '' || /^\d{9}$/.test(value);
            errorMessage = 'Please enter a valid 9-digit DUNS number';
            break;
    }
    input.classList.toggle('is-valid', isValid && value !== '');
    // Update validation state
    fieldValidationState[input.name] = isValid && value !== '';
    // Update or create error message
    let errorDiv = (_a = input.parentElement) === null || _a === void 0 ? void 0 : _a.querySelector('.invalid-feedback');
    if (!errorDiv) {
        errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback';
        (_b = input.parentElement) === null || _b === void 0 ? void 0 : _b.appendChild(errorDiv);
    }
    errorDiv.textContent = errorMessage;
    // Update submit button state
    updateSubmitButtonState();
}
function updateSubmitButtonState() {
    const form = document.querySelector('form');
    if (!form)
        return;
    const submitButton = form.querySelector('button[type="submit"]');
    if (!submitButton)
        return;
    // Get all required inputs on the current page
    const requiredInputs = Array.from(form.querySelectorAll('input[required], select[required]'));
    // Check if all required fields are valid
    const allFieldsValid = requiredInputs.every(input => {
        const inputElement = input;
        return fieldValidationState[inputElement.name] === true;
    });
    // Update button state
    submitButton.disabled = !allFieldsValid;
    // Add visual feedback for disabled state
    if (allFieldsValid) {
        submitButton.classList.remove('btn-secondary');
        submitButton.classList.add('btn-primary');
    }
    else {
        submitButton.classList.remove('btn-primary');
        submitButton.classList.add('btn-secondary');
    }
}
// Initialize validation when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    var _a, _b;
    console.log('DOM Content Loaded');
    // Initialize password toggles
    const password1Input = document.querySelector('[name="password1"]');
    const icon1Container = (_a = password1Input === null || password1Input === void 0 ? void 0 : password1Input.parentElement) === null || _a === void 0 ? void 0 : _a.querySelector('.password-toggle-icon');
    const password2Input = document.querySelector('[name="password2"]');
    const icon2Container = (_b = password2Input === null || password2Input === void 0 ? void 0 : password2Input.parentElement) === null || _b === void 0 ? void 0 : _b.querySelector('.password-toggle-icon');
    function togglePassword1() {
        if (password1Input && icon1Container) {
            if (password1Input.type === 'password') {
                password1Input.type = 'text';
                icon1Container.innerHTML = '<i class="fa-solid fa-eye-slash" id="togglePassword1"></i>';
            }
            else {
                password1Input.type = 'password';
                icon1Container.innerHTML = '<i class="fa-solid fa-eye" id="togglePassword1"></i>';
            }
        }
    }
    function togglePassword2() {
        if (password2Input && icon2Container) {
            if (password2Input.type === 'password') {
                password2Input.type = 'text';
                icon2Container.innerHTML = '<i class="fa-solid fa-eye-slash" id="togglePassword2"></i>';
            }
            else {
                password2Input.type = 'password';
                icon2Container.innerHTML = '<i class="fa-solid fa-eye" id="togglePassword2"></i>';
            }
        }
    }
    if (icon1Container) {
        icon1Container.addEventListener('click', togglePassword1);
    }
    if (icon2Container) {
        icon2Container.addEventListener('click', togglePassword2);
    }
    setupRealTimeValidation();
    setupFormPersistence();
    // Set initial button state
    const form = document.querySelector('form');
    if (form) {
        const inputs = form.querySelectorAll('input, select');
        inputs.forEach(input => {
            const inputElement = input;
            if (inputElement.name) {
                fieldValidationState[inputElement.name] = false;
            }
        });
        updateSubmitButtonState();
    }
});
// Form data persistence
function setupFormPersistence() {
    const form = document.querySelector('form');
    if (!form)
        return;
    // Load saved data
    const savedData = sessionStorage.getItem('registrationData');
    if (savedData) {
        const data = JSON.parse(savedData);
        Object.keys(data).forEach(key => {
            const input = form.querySelector(`[name="${key}"]`);
            if (input) {
                input.value = data[key];
                validateInput(input);
            }
        });
    }
    // Save data on input
    form.addEventListener('input', (e) => {
        const target = e.target;
        if (target.name) {
            const currentData = JSON.parse(sessionStorage.getItem('registrationData') || '{}');
            currentData[target.name] = target.value;
            sessionStorage.setItem('registrationData', JSON.stringify(currentData));
        }
    });
    // Clear data on successful submission
    form.addEventListener('submit', () => {
        sessionStorage.removeItem('registrationData');
    });
}
//# sourceMappingURL=registration.js.map