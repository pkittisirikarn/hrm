document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = '/api/v1/payroll';

    // Elements for Adding Allowance Type
    const addAllowanceTypeForm = document.getElementById('addAllowanceTypeForm');
    const addAllowanceTypeMessage = document.getElementById('addAllowanceTypeMessage');
    const addNameInput = document.getElementById('addName');
    const addDescriptionInput = document.getElementById('addDescription');
    const addIsTaxableCheckbox = document.getElementById('addIsTaxable');
    const addIsActiveCheckbox = document.getElementById('addIsActive');
    const addFormulaInput = document.getElementById('addFormula'); // New
    const addFormulaVariableNameInput = document.getElementById('addFormulaVariableName'); // New

    // Elements for Listing Allowance Types
    const allowanceTypesTableBody = document.getElementById('allowanceTypesTableBody');
    const allowanceTypesMessage = document.getElementById('allowanceTypesMessage');

    // Elements for Editing Allowance Type Modal
    const editAllowanceTypeModal = document.getElementById('editAllowanceTypeModal');
    const closeEditModalButton = document.getElementById('closeEditModalButton');
    const editAllowanceTypeForm = document.getElementById('editAllowanceTypeForm');
    const editAllowanceTypeMessage = document.getElementById('editAllowanceTypeMessage');

    // Edit Form Fields
    const editAllowanceTypeIdInput = document.getElementById('editAllowanceTypeId');
    const editNameInput = document.getElementById('editName');
    const editDescriptionInput = document.getElementById('editDescription');
    const editIsTaxableCheckbox = document.getElementById('editIsTaxable');
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

    // --- Fetch Allowance Types from API and Render Table ---
    async function fetchAllowanceTypes() {
        allowanceTypesTableBody.innerHTML = `
            <tr>
                <td colspan="7" class="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500">
                    กำลังโหลดข้อมูล...
                </td>
            </tr>`;
        try {
            const response = await fetch(`${API_BASE_URL}/allowance-types/`);
            if (!response.ok) {
                const errorData = await response.json();
                console.error('API Error (fetch allowance types):', errorData);
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            const allowanceTypes = await response.json();
            renderAllowanceTypesTable(allowanceTypes);
        } catch (error) {
            console.error('Error fetching allowance types:', error);
            allowanceTypesTableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="px-6 py-4 whitespace-nowrap text-center text-sm text-red-600">
                        เกิดข้อผิดพลาดในการโหลดประเภทเบี้ยเลี้ยง: ${error.message}
                    </td>
                </tr>`;
            showMessage(allowanceTypesMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
        }
    }

    // --- Render Allowance Types Table ---
    function renderAllowanceTypesTable(allowanceTypes) {
        allowanceTypesTableBody.innerHTML = '';
        if (allowanceTypes.length === 0) {
            allowanceTypesTableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500">
                        ยังไม่มีข้อมูลประเภทเบี้ยเลี้ยง
                    </td>
                </tr>`;
            return;
        }

        allowanceTypes.forEach(type => {
            const row = allowanceTypesTableBody.insertRow();
            row.className = 'hover:bg-gray-50';
            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${type.id}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${type.name}</td>
                <td class="px-6 py-4 whitespace-normal text-sm text-gray-700 max-w-xs overflow-hidden text-ellipsis">${type.description || '-'}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${type.is_taxable ? 'ใช่' : 'ไม่ใช่'}</td>
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
                    const response = await fetch(`${API_BASE_URL}/allowance-types/${id}`);
                    if (!response.ok) {
                        const errorData = await response.json();
                        console.error('API Error (fetch allowance type for edit):', errorData);
                        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
                    }
                    const type = await response.json();
                    
                    editAllowanceTypeIdInput.value = type.id;
                    editNameInput.value = type.name;
                    editDescriptionInput.value = type.description || '';
                    editIsTaxableCheckbox.checked = type.is_taxable;
                    editIsActiveCheckbox.checked = type.is_active;
                    editFormulaInput.value = type.formula || ''; // New
                    editFormulaVariableNameInput.value = type.formula_variable_name || ''; // New

                    editAllowanceTypeModal.style.display = 'flex'; // Show Modal
                } catch (error) {
                    console.error('Error fetching allowance type for edit:', error);
                    showMessage(allowanceTypesMessage, `เกิดข้อผิดพลาดในการโหลดประเภทเบี้ยเลี้ยงเพื่อแก้ไข: ${error.message}`, true);
                }
            });
        });

        document.querySelectorAll('.delete-btn').forEach(button => {
            button.addEventListener('click', async (event) => {
                const id = event.target.dataset.id;
                if (confirm(`คุณแน่ใจหรือไม่ที่ต้องการลบประเภทเบี้ยเลี้ยง ID: ${id} นี้?`)) {
                    try {
                        const response = await fetch(`${API_BASE_URL}/allowance-types/${id}`, {
                            method: 'DELETE',
                        });
                        if (!response.ok) {
                            const errorData = await response.json();
                            console.error('API Error (delete allowance type):', errorData);
                            throw new Error(errorData.detail || 'เกิดข้อผิดพลาดในการลบประเภทเบี้ยเลี้ยง');
                        }
                        showMessage(allowanceTypesMessage, 'ลบประเภทเบี้ยเลี้ยงเรียบร้อยแล้ว');
                        fetchAllowanceTypes(); // Reload data
                    } catch (error) {
                        console.error('Error deleting allowance type:', error);
                        showMessage(allowanceTypesMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
                    }
                }
            });
        });
    }

    // --- Event Listener for Add Allowance Type Form ---
    addAllowanceTypeForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        
        const name = addNameInput.value.trim();
        const description = addDescriptionInput.value.trim();
        const isTaxable = addIsTaxableCheckbox.checked;
        const isActive = addIsActiveCheckbox.checked;
        const formula = addFormulaInput.value.trim(); // New
        const formulaVariableName = addFormulaVariableNameInput.value.trim(); // New

        if (!name) {
            showMessage(addAllowanceTypeMessage, 'กรุณากรอกชื่อประเภทเบี้ยเลี้ยง', true);
            return;
        }

        try {
            const data = {
                name: name,
                description: description || null,
                is_taxable: isTaxable,
                is_active: isActive,
                formula: formula || null, // New
                formula_variable_name: formulaVariableName || null // New
            };

            const response = await fetch(`${API_BASE_URL}/allowance-types/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.error('API Error (add allowance type):', errorData);
                if (Array.isArray(errorData.detail) && errorData.detail.length > 0) {
                    const validationErrors = errorData.detail.map(err => `${err.loc.join('.')} - ${err.msg}`).join('\n');
                    throw new Error(`ข้อมูลไม่ถูกต้อง:\n${validationErrors}`);
                }
                throw new Error(errorData.detail || 'เกิดข้อผิดพลาดในการเพิ่มประเภทเบี้ยเลี้ยง');
            }

            const newType = await response.json();
            showMessage(addAllowanceTypeMessage, `เพิ่มประเภทเบี้ยเลี้ยง "${newType.name}" (ID: ${newType.id}) เรียบร้อยแล้ว`);
            addAllowanceTypeForm.reset(); // Clear form
            fetchAllowanceTypes(); // Load new data
        } catch (error) {
            console.error('Final caught error adding allowance type:', error);
            showMessage(addAllowanceTypeMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
        }
    });

    // --- Event Listener for Edit Allowance Type Form ---
    editAllowanceTypeForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const allowanceTypeId = editAllowanceTypeIdInput.value;
        
        const name = editNameInput.value.trim();
        const description = editDescriptionInput.value.trim();
        const isTaxable = editIsTaxableCheckbox.checked;
        const isActive = editIsActiveCheckbox.checked;
        const formula = editFormulaInput.value.trim(); // New
        const formulaVariableName = editFormulaVariableNameInput.value.trim(); // New

        if (!name) {
            showMessage(editAllowanceTypeMessage, 'กรุณากรอกชื่อประเภทเบี้ยเลี้ยง', true);
            return;
        }

        try {
            const data = {
                name: name,
                description: description || null,
                is_taxable: isTaxable,
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

            const response = await fetch(`${API_BASE_URL}/allowance-types/${allowanceTypeId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.error('API Error (edit allowance type):', errorData);
                if (Array.isArray(errorData.detail) && errorData.detail.length > 0) {
                    const validationErrors = errorData.detail.map(err => `${err.loc.join('.')} - ${err.msg}`).join('\n');
                    throw new Error(`ข้อมูลไม่ถูกต้อง:\n${validationErrors}`);
                }
                throw new Error(errorData.detail || 'เกิดข้อผิดพลาดในการอัปเดตประเภทเบี้ยเลี้ยง');
            }

            const updatedType = await response.json();
            showMessage(allowanceTypesMessage, `อัปเดตประเภทเบี้ยเลี้ยง "${updatedType.name}" (ID: ${updatedType.id}) เรียบร้อยแล้ว`);
            editAllowanceTypeModal.style.display = 'none'; // Hide Modal
            fetchAllowanceTypes(); // Load new data
        } catch (error) {
            console.error('Final caught error updating allowance type:', error);
            showMessage(editAllowanceTypeMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
        }
    });

    // --- Event Listener for closing Edit Modal ---
    closeEditModalButton.addEventListener('click', () => {
        editAllowanceTypeModal.style.display = 'none';
        editAllowanceTypeMessage.textContent = '';
    });

    // Initial load
    fetchAllowanceTypes();
});
