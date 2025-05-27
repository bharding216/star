function validatePassword(password: string) {
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

function validatePasswordMatch(password1: string, password2: string) {
    return password1 === password2;
}       

function validateEmail(email: string) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function validatePhone(phone: string) {
    const phoneRegex = /^\d{10}$/;
    return phoneRegex.test(phone);
}

function validateZipCode(zipCode: string) {
    const zipRegex = /^\d{5}$/;
    return zipRegex.test(zipCode);
}

function validateCity(city: string) {
    // Allows letters, spaces, periods, hyphens, and apostrophes
    const cityRegex = /^[A-Za-z\s.'-]+$/;
    return cityRegex.test(city);
}

function validateState(state: string) {
    // Allows letters, spaces, periods, hyphens, and apostrophes
    const stateRegex = /^[A-Za-z\s.'-]+$/;
    return stateRegex.test(state);
}

const individualRadio = document.getElementById('individual_radio') as HTMLInputElement;
const companyRadio = document.getElementById('company_radio') as HTMLInputElement;
const ssnInput = document.getElementById('ssn_div') as HTMLElement;
const einInput = document.getElementById('ein_div') as HTMLElement;
const dunsInput = document.getElementById('duns_div') as HTMLElement;

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
    if (!form) return;

    const inputs = form.querySelectorAll('input, select');
    inputs.forEach(input => {
        // Validate on input/change
        input.addEventListener('input', function(this: HTMLInputElement | HTMLSelectElement) {
            validateInput(this);
        });
        
        // Validate on blur
        input.addEventListener('blur', function(this: HTMLInputElement | HTMLSelectElement) {
            validateInput(this);
        });

        // For select elements, also validate on change
        if (input instanceof HTMLSelectElement) {
            input.addEventListener('change', function(this: HTMLSelectElement) {
                validateInput(this);
            });
        }
    });
}

// Track validation state of all fields
const fieldValidationState: { [key: string]: boolean } = {};

function validateInput(input: HTMLInputElement | HTMLSelectElement) {
    const value = input.value.trim();
    let isValid = true;
    let errorMessage = '';

    // Get the current radio selection
    const isIndividual = (document.getElementById('individual_radio') as HTMLInputElement)?.checked;

    switch(input.name) {
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
            const password1 = document.querySelector('[name="password1"]') as HTMLInputElement;
            isValid = validatePasswordMatch(password1.value, value);
            errorMessage = 'Passwords do not match';
            break;
        case 'ssn':
            isValid = isIndividual ? /^\d{9}$/.test(value) : true;
            errorMessage = 'Please enter a valid 9-digit SSN';
            break;
        case 'ein':
            isValid = !isIndividual ? /^\d{9}$/.test(value) : true;
            errorMessage = 'Please enter a valid 9-digit EIN';
            break;
        case 'duns':
            isValid = value === '' || /^\d{9}$/.test(value);
            errorMessage = 'Please enter a valid 9-digit DUNS number';
            break;
        case 'zip_code':
            isValid = validateZipCode(value);
            errorMessage = 'Please enter a valid 5-digit zip code';
            break;
        case 'address_1':
            isValid = value.length > 0;
            errorMessage = 'Street address is required';
            break;
        case 'city':
            isValid = validateCity(value);
            errorMessage = 'City can only contain letters, spaces, and common punctuation';
            break;
        case 'state':
            isValid = validateState(value);
            errorMessage = 'State can only contain letters, spaces, and common punctuation';
            break;
        case 'legal_structure':
            isValid = value !== '' && value !== 'Choose a business structure' && value !== 'Choose a business structure';
            errorMessage = 'Please select a business structure';
            break;
    }

    // Update validation classes
    if (value === '') {
        input.classList.remove('is-valid', 'is-invalid');
    } else {
        input.classList.toggle('is-valid', isValid);
        input.classList.toggle('is-invalid', !isValid);
    }

    // Update validation state
    fieldValidationState[input.name] = isValid && value !== '';

    // Update or create error message
    let errorDiv = input.parentElement?.querySelector('.invalid-feedback') as HTMLElement;
    if (!errorDiv) {
        errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback';
        input.parentElement?.appendChild(errorDiv);
    }
    errorDiv.textContent = errorMessage;

    // If the errorDiv for the password fields is not empty, add some bottom margin to the eye icon
    const eyeIcon = input.parentElement?.querySelector('.password-toggle-icon') as HTMLElement;
    if (input.type === 'password' || input.type === 'text') {
        if (!input.classList.contains('is-invalid')) {
            console.log('errorDiv is not visible');
            if (eyeIcon) {
                eyeIcon.style.paddingBottom = '0rem';
            }
        } else {
            console.log('errorDiv is visible');
            if (eyeIcon) {
                eyeIcon.style.paddingBottom = '1.5rem';
            }
        }
    }

    // Update submit button state
    updateSubmitButtonState();
}

function updateSubmitButtonState() {
    const form = document.querySelector('form');
    if (!form) return;

    const submitButton = form.querySelector('button[type="submit"]') as HTMLButtonElement;
    if (!submitButton) return;

    // Get the current radio selection
    const isIndividual = (document.getElementById('individual_radio') as HTMLInputElement)?.checked;

    // Get all required inputs on the current page
    const requiredInputs = Array.from(form.querySelectorAll('input[required], select[required]'));
    
    // Check if all required fields are valid, excluding hidden ones
    const allFieldsValid = requiredInputs.every(input => {
        const inputElement = input as HTMLInputElement;
        const shouldValidate = (inputElement.name === 'ssn' && isIndividual) || 
                             ((inputElement.name === 'ein' || inputElement.name === 'duns') && !isIndividual) ||
                             inputElement.name === 'legal_structure';
        
        if (!shouldValidate) {
            return true;
        }

        const isValid = fieldValidationState[inputElement.name] === true;
        return isValid;
    });
    
    // Update button state
    submitButton.disabled = !allFieldsValid;
    
    // Add visual feedback for disabled state
    if (allFieldsValid) {
        submitButton.classList.remove('btn-secondary');
        submitButton.classList.add('btn-primary');
    } else {
        submitButton.classList.remove('btn-primary');
        submitButton.classList.add('btn-secondary');
    }
}

// Initialize validation when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    
    // Initialize password toggles
    const password1Input = document.querySelector('[name="password1"]') as HTMLInputElement;
    const icon1Container = password1Input?.parentElement?.querySelector('.password-toggle-icon') as HTMLElement;
    const password2Input = document.querySelector('[name="password2"]') as HTMLInputElement;
    const icon2Container = password2Input?.parentElement?.querySelector('.password-toggle-icon') as HTMLElement;

    function togglePassword1() {
        if (password1Input && icon1Container) {
            if (password1Input.type === 'password') {
                password1Input.type = 'text';
                icon1Container.innerHTML = '<i class="fa-solid fa-eye-slash" id="togglePassword1"></i>';
            } else {
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
            } else {
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
            const inputElement = input as HTMLInputElement;
            if (inputElement.name) {
                // Validate each field on page load
                validateInput(inputElement);
            }
        });
        updateSubmitButtonState();
    }
});

// Form data persistence
function setupFormPersistence() {
    const form = document.querySelector('form');
    if (!form) return;

    // Load saved data
    const savedData = sessionStorage.getItem('registrationData');
    if (savedData) {
        const data = JSON.parse(savedData);
        Object.keys(data).forEach(key => {
            const input = form.querySelector(`[name="${key}"]`) as HTMLInputElement;
            if (input) {
                input.value = data[key];
                // Trigger validation after setting the value
                validateInput(input);
            }
        });
        // Update submit button state after loading all data
        updateSubmitButtonState();
    }

    // Save data on input
    form.addEventListener('input', (e) => {
        const target = e.target as HTMLInputElement;
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