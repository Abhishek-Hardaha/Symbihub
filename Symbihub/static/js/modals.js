/* Add to existing app.js content */
document.addEventListener('DOMContentLoaded', function() {
    // Success modals for event creation and registration
    const eventCreatedData = document.getElementById('eventCreatedData');
    const registrationData = document.getElementById('registrationData');
    
    if (eventCreatedData) {
        const data = JSON.parse(eventCreatedData.textContent);
        showModal('eventCreatedModal');
        // Clear the session data by calling the clear endpoint
        fetch('/clear_modal_data');
    }
    
    if (registrationData) {
        const data = JSON.parse(registrationData.textContent);
        showModal('registrationSuccessModal');
        // Clear the session data
        fetch('/clear_modal_data');
    }

    // Modal controls
    document.querySelectorAll('[data-modal-close]').forEach(button => {
        button.addEventListener('click', () => {
            const modalId = button.closest('.modal').id;
            hideModal(modalId);
        });
    });
});

function showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('hidden');
        document.body.classList.add('overflow-hidden');
    }
}

function hideModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('hidden');
        document.body.classList.remove('overflow-hidden');
    }
}