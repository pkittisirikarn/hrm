document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = '/api/v1/payroll';

    // Elements for Adding Deduction Type
    const addDeductionTypeForm = document.getElementById('addDeductionTypeForm');
    const addDeductionTypeMessage = document.getElementById('addDeductionTypeMessage');
    const addNameInput = document.getElementById('addName');
    const addDescriptionInput = document.getElementById('addDescription');
    const addIsMandatoryCheckbox = document.getElementById('addIsMandatory');
    const addIsActiveCheckbox = document.getElementById('addIsActive');
    const addFormulaInput = document.getElementById('addFormula'); // New
    const addFormulaVariableNameInput = document.getElementById('addFormulaVariableName'); // New

    // Elements for Listing Deduction Types
    const deductionTypesTableBody = document.getElementById('deductionTypesTableBody');
    const deductionTypesMessage = document.getElementById('deductionTypesMessage');

    // Elements for Editing Deduction Type Modal
    const editDeductionTypeModal = document.getElementById('editDeductionTypeModal');
    const closeEditModalButton = document.getElementById('closeEditModalButton');
    const editDeductionTypeForm = document.getElementById('editDeductionTypeForm');
    const editDeductionTypeMessage = document.getElementById('editDeductionTypeMessage');

    // Edit Form Fields
    const editDeductionTypeIdInput = document.getElementById('editDeductionTypeId');
    const editNameInput = document.getElementById('editName');
    const editDescriptionInput = document.getElementById('editDescription');
    const editIsMandatoryCheckbox = document.getElementById('editIsMandatory');
    const editIsActiveCheckbox = document.getElementById('editIsActive');
    const editFormulaInput = document.getElementById('editFormula'); // New
    const editFormulaVariableNameInput = document.getElementById('editFormulaVariableName'); // New

    // --- Generic Message Display Function ---
    function showMessage(element, message, isError = false) {
        element.textContent = message;
        element.className = `mt-4 text-sm font-medium ${isError ? 'text-red-600' : 'text-green-600'}`;
        setTimeout(() => {
            element.textContent = '';
            element.className = 'mt-4 text-sm font-medium';
        }, 5000);
    }

    // --- Fetch Deduction Types from API and Render Table ---
    async function fetchDeductionTypes() {
        deductionTypesTableBody.innerHTML = `
            <tr>
                <td colspan="7" class="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500">
                    กำลังโหลดข้อมูล...
                </td>
            </tr>`;
        try {
            const response = await fetch(`${API_BASE_URL}/deduction-types/`);
            if (!response.ok) {
                const errorData = await response.json();
                console.error('API Error (fetch deduction types):', errorData);
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            const deductionTypes = await response.json();
            renderDeductionTypesTable(deductionTypes);
        } catch (error) {
            console.error('Error fetching deduction types:', error);
            deductionTypesTableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="px-6 py-4 whitespace-nowrap text-center text-sm text-red-600">
                        เกิดข้อผิดพลาดในการโหลดประเภทรายการหัก: ${error.message}
                    </td>
                </tr>`;
            showMessage(deductionTypesMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
        }
    }

    // --- Render Deduction Types Table ---
    function renderDeductionTypesTable(deductionTypes) {
        deductionTypesTableBody.innerHTML = '';
        if (deductionTypes.length === 0) {
            deductionTypesTableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500">
                        ยังไม่มีข้อมูลประเภทรายการหัก
                    </td>
                </tr>`;
            return;
        }

        deductionTypes.forEach(type => {
            const row = deductionTypesTableBody.insertRow();
            row.className = 'hover:bg-gray-50';
            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${type.id}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${type.name}</td>
                <td class="px-6 py-4 whitespace-normal text-sm text-gray-700 max-w-xs overflow-hidden text-ellipsis">${type.description || '-'}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${type.is_mandatory ? 'ใช่' : 'ไม่ใช่'}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${type.is_active ? 'ใช้งาน' : 'ไม่ใช้งาน'}</td>
                <td class="px-6 py-4 whitespace-normal text-sm text-gray-700 max-w-xs overflow-hidden text-ellipsis">${type.formula || '-'}</td>
                <td class="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                    <button data-id="${type.id}" class="edit-btn bg-yellow-500 hover:bg-yellow-600 text-white py-1 px-3 rounded-md mr-2 transition duration-150">แก้ไข</button>
                    <button data-id="${type.id}" class="delete-btn bg-red-600 hover:bg-red-700 text-white py-1 px-3 rounded-md transition duration-150">ลบ</button>
                </td>
            `;
        });

        // Add Event Listeners for Edit and Delete buttons
        document.querySelectorAll('.edit-btn').forEach(button => {
            button.addEventListener('click', async (event) => {
                const id = event.target.dataset.id;
                try {
                    const response = await fetch(`${API_BASE_URL}/deduction-types/${id}`);
                    if (!response.ok) {
                        const errorData = await response.json();
                        console.error('API Error (fetch deduction type for edit):', errorData);
                        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
                    }
                    const type = await response.json();
                    
                    editDeductionTypeIdInput.value = type.id;
                    editNameInput.value = type.name;
                    editDescriptionInput.value = type.description || '';
                    editIsMandatoryCheckbox.checked = type.is_mandatory;
                    editIsActiveCheckbox.checked = type.is_active;
                    editFormulaInput.value = type.formula || ''; // New
                    editFormulaVariableNameInput.value = type.formula_variable_name || ''; // New

                    editDeductionTypeModal.style.display = 'flex'; // Show Modal
                } catch (error) {
                    console.error('Error fetching deduction type for edit:', error);
                    showMessage(deductionTypesMessage, `เกิดข้อผิดพลาดในการโหลดประเภทรายการหักเพื่อแก้ไข: ${error.message}`, true);
                }
            });
        });

        document.querySelectorAll('.delete-btn').forEach(button => {
            button.addEventListener('click', async (event) => {
                const id = event.target.dataset.id;
                if (confirm(`คุณแน่ใจหรือไม่ที่ต้องการลบประเภทรายการหัก ID: ${id} นี้?`)) {
                    try {
                        const response = await fetch(`${API_BASE_URL}/deduction-types/${id}`, {
                            method: 'DELETE',
                        });
                        if (!response.ok) {
                            const errorData = await response.json();
                            console.error('API Error (delete deduction type):', errorData);
                            throw new Error(errorData.detail || 'เกิดข้อผิดพลาดในการลบประเภทรายการหัก');
                        }
                        showMessage(deductionTypesMessage, 'ลบประเภทรายการหักเรียบร้อยแล้ว');
                        fetchDeductionTypes(); // Reload data
                    } catch (error) {
                        console.error('Error deleting deduction type:', error);
                        showMessage(deductionTypesMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
                    }
                }
            });
        });
    }

    // --- Event Listener for Add Deduction Type Form ---
    addDeductionTypeForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        
        const name = addNameInput.value.trim();
        const description = addDescriptionInput.value.trim();
        const isMandatory = addIsMandatoryCheckbox.checked;
        const isActive = addIsActiveCheckbox.checked;
        const formula = addFormulaInput.value.trim(); // New
        const formulaVariableName = addFormulaVariableNameInput.value.trim(); // New

        if (!name) {
            showMessage(addDeductionTypeMessage, 'กรุณากรอกชื่อประเภทรายการหัก', true);
            return;
        }

        try {
            const data = {
                name: name,
                description: description || null,
                is_mandatory: isMandatory,
                is_active: isActive,
                formula: formula || null, // New
                formula_variable_name: formulaVariableName || null // New
            };

            const response = await fetch(`${API_BASE_URL}/deduction-types/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.error('API Error (add deduction type):', errorData);
                if (Array.isArray(errorData.detail) && errorData.detail.length > 0) {
                    const validationErrors = errorData.detail.map(err => `${err.loc.join('.')} - ${err.msg}`).join('\n');
                    throw new Error(`ข้อมูลไม่ถูกต้อง:\n${validationErrors}`);
                }
                throw new Error(errorData.detail || 'เกิดข้อผิดพลาดในการเพิ่มประเภทรายการหัก');
            }

            const newType = await response.json();
            showMessage(addDeductionTypeMessage, `เพิ่มประเภทรายการหัก "${newType.name}" (ID: ${newType.id}) เรียบร้อยแล้ว`);
            addDeductionTypeForm.reset(); // Clear form
            fetchDeductionTypes(); // Load new data
        } catch (error) {
            console.error('Final caught error adding deduction type:', error);
            showMessage(addDeductionTypeMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
        }
    });

    // --- Event Listener for Edit Deduction Type Form ---
    editDeductionTypeForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const deductionTypeId = editDeductionTypeIdInput.value;
        
        const name = editNameInput.value.trim();
        const description = editDescriptionInput.value.trim();
        const isMandatory = editIsMandatoryCheckbox.checked;
        const isActive = editIsActiveCheckbox.checked;
        const formula = editFormulaInput.value.trim(); // New
        const formulaVariableName = editFormulaVariableNameInput.value.trim(); // New

        if (!name) {
            showMessage(editDeductionTypeMessage, 'กรุณากรอกชื่อประเภทรายการหัก', true);
            return;
        }

        try {
            const data = {
                name: name,
                description: description || null,
                is_mandatory: isMandatory,
                is_active: isActive,
                formula: formula || null, // New
                formula_variable_name: formulaVariableName || null // New
            };
            
            // Remove null or empty string fields from data object before sending for partial update
            Object.keys(data).forEach(key => {
                if (data[key] === null || data[key] === '') {
                    delete data[key];
                }
            });

            const response = await fetch(`${API_BASE_URL}/deduction-types/${deductionTypeId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.error('API Error (edit deduction type):', errorData);
                if (Array.isArray(errorData.detail) && errorData.detail.length > 0) {
                    const validationErrors = errorData.detail.map(err => `${err.loc.join('.')} - ${err.msg}`).join('\n');
                    throw new Error(`ข้อมูลไม่ถูกต้อง:\n${validationErrors}`);
                }
                throw new Error(errorData.detail || 'เกิดข้อผิดพลาดในการอัปเดตประเภทรายการหัก');
            }

            const updatedType = await response.json();
            showMessage(deductionTypesMessage, `อัปเดตประเภทรายการหัก "${updatedType.name}" (ID: ${updatedType.id}) เรียบร้อยแล้ว`);
            editDeductionTypeModal.style.display = 'none'; // Hide Modal
            fetchDeductionTypes(); // Load new data
        } catch (error) {
            console.error('Final caught error updating deduction type:', error);
            showMessage(editDeductionTypeMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
        }
    });

    // --- Event Listener for closing Edit Modal ---
    closeEditModalButton.addEventListener('click', () => {
        editDeductionTypeModal.style.display = 'none';
        editDeductionTypeMessage.textContent = '';
    });

    // Initial load
    fetchDeductionTypes();
});
