js
function applyToAll(button) {
    const mappings = [
        { master: 'apply_lunch_break', rowSuffix: 'has_lunch_break' },
        { master: 'apply_break1', rowSuffix: 'has_break1' },
        { master: 'apply_break2', rowSuffix: 'has_break2' },
        { master: 'apply_break3', rowSuffix: 'has_break3' },
        { master: 'apply_break4', rowSuffix: 'has_break4' },
        { master: 'apply_break5', rowSuffix: 'has_break5' }
    ];

    // Define the list of "working" statuses: 0 (出勤), 2 (午前休), 3 (午後休)
    const validStatuses = ["0", "2", "3"];

    mappings.forEach(mapping => {
        const masterCheckbox = document.querySelector(`input[name="${mapping.master}"]`);
        if (!masterCheckbox) return;

        const isChecked = masterCheckbox.checked;
        const rowCheckboxes = document.querySelectorAll(`input[type="checkbox"][name$="-${mapping.rowSuffix}"]`);

        rowCheckboxes.forEach(checkbox => {
            const nameParts = checkbox.name.split('-');
            const index = nameParts[1]; 
            const prefix = nameParts[0];

            const statusSelect = document.querySelector(`select[name="${prefix}-${index}-date_status"]`);

            // Check if statusSelect exists and its value is in our allowed list
            if (statusSelect && validStatuses.includes(statusSelect.value)) {
                checkbox.checked = isChecked;
                checkbox.dispatchEvent(new Event('change', { bubbles: true }));
            }
        });
    });
}