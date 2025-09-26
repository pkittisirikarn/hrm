document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = '/api/v1/payroll';
    const DATA_MGMT_API_BASE_URL = '/api/v1/data-management'; // For fetching employees

    // Elements for Adding Employee Allowance
    const addEmployeeAllowanceForm = document.getElementById('addEmployeeAllowanceForm');
    const addEmployeeAllowanceMessage = document.getElementById('addEmployeeAllowanceMessage');
    const addEmployeeIdSelect = document.getElementById('addEmployeeId');
    const addAllowanceTypeIdSelect = document.getElementById('addAllowanceTypeId');
    const addAmountInput = document.getElementById('addAmount');
    const addEffectiveDateInput = document.getElementById('addEffectiveDate');

    // Elements for Listing Employee Allowances
    const employeeAllowancesTableBody = document.getElementById('employeeAllowancesTableBody');
    const employeeAllowancesMessage = document.getElementById('employeeAllowancesMessage');

    // Elements for Editing Employee Allowance Modal
    const editEmployeeAllowanceModal = document.getElementById('editEmployeeAllowanceModal');
    const closeEditModalButton = document.getElementById('closeEditModalButton');
    const editEmployeeAllowanceForm = document.getElementById('editEmployeeAllowanceForm');
    const editEmployeeAllowanceMessage = document.getElementById('editEmployeeAllowanceMessage');

    // Edit Form Fields
    const editEmployeeAllowanceIdInput = document.getElementById('editEmployeeAllowanceId');
    const editEmployeeIdSelect = document.getElementById('editEmployeeId');
    const editAllowanceTypeIdSelect = document.getElementById('editAllowanceTypeId');
    const editAmountInput = document.getElementById('editAmount');
    const editEffectiveDateInput = document.getElementById('editEffectiveDate');

    // --- Generic Message Display Function ---
    function showMessage(element, message, isError = false) {
        element.textContent = message;
        element.className = `mt-4 text-sm font-medium ${isError ? 'text-red-600' : 'text-green-600'}`;
        setTimeout(() => {
            element.textContent = '';
            element.className = 'mt-4 text-sm font-medium';
        }, 5000);
    }

    // --- Date Formatting Helper ---
    function formatDateToInput(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toISOString().split('T')[0]; // Format to YYYY-MM-DD
    }

    // --- Fetch Dropdown Data (Employees, Allowance Types) ---
    async function fetchDropdownData() {
        try {
            const [empResponse, allowanceTypeResponse] = await Promise.all([
                fetch(`${DATA_MGMT_API_BASE_URL}/employees/`),
                fetch(`${API_BASE_URL}/allowance-types/`)
            ]);

            if (!empResponse.ok) throw new Error(`HTTP error! status: ${empResponse.status} for employees`);
            if (!allowanceTypeResponse.ok) throw new Error(`HTTP error! status: ${allowanceTypeResponse.status} for allowance types`);

            const employees = await empResponse.json();
            const allowanceTypes = await allowanceTypeResponse.json();

            populateEmployeeDropdown(addEmployeeIdSelect, employees);
            populateAllowanceTypeDropdown(addAllowanceTypeIdSelect, allowanceTypes);
            populateEmployeeDropdown(editEmployeeIdSelect, employees);
            populateAllowanceTypeDropdown(editAllowanceTypeIdSelect, allowanceTypes);

        } catch (error) {
            console.error('Error fetching dropdown data:', error);
            showMessage(addEmployeeAllowanceMessage, `ไม่สามารถโหลดข้อมูลพนักงาน/ประเภทเบี้ยเลี้ยง: ${error.message}`, true);
            showMessage(employeeAllowancesMessage, `ไม่สามารถโหลดข้อมูลพนักงาน/ประเภทเบี้ยเลี้ยง: ${error.message}`, true);
        }
    }

    function populateEmployeeDropdown(selectElement, employees, selectedId = null) {
        selectElement.innerHTML = '<option value="">-- เลือกพนักงาน --</option>'; // Default option
        employees.forEach(employee => {
            const option = document.createElement('option');
            option.value = employee.id;
            option.textContent = `${employee.first_name} ${employee.last_name}`;
            if (selectedId && employee.id === selectedId) {
                option.selected = true;
            }
            selectElement.appendChild(option);
        });
    }

    function populateAllowanceTypeDropdown(selectElement, allowanceTypes, selectedId = null) {
        selectElement.innerHTML = '<option value="">-- เลือกประเภทเบี้ยเลี้ยง --</option>'; // Default option
        allowanceTypes.forEach(type => {
            const option = document.createElement('option');
            option.value = type.id;
            option.textContent = type.name;
            if (selectedId && type.id === selectedId) {
                option.selected = true;
            }
            selectElement.appendChild(option);
        });
    }

    // --- Fetch Employee Allowances from API and Render Table ---
    async function fetchEmployeeAllowances() {
        employeeAllowancesTableBody.innerHTML = `
            <tr>
                <td colspan="6" class="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500">
                    กำลังโหลดข้อมูล...
                </td>
            </tr>`;
        try {
            const response = await fetch(`${API_BASE_URL}/employee-allowances/`);
            if (!response.ok) {
                const errorData = await response.json();
                console.error('API Error (fetch employee allowances):', errorData);
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            const employeeAllowances = await response.json();
            renderEmployeeAllowancesTable(employeeAllowances);
        } catch (error) {
            console.error('Error fetching employee allowances:', error);
            employeeAllowancesTableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="px-6 py-4 whitespace-nowrap text-center text-sm text-red-600">
                        เกิดข้อผิดพลาดในการโหลดข้อมูลเบี้ยเลี้ยงพนักงาน: ${error.message}
                    </td>
                </tr>`;
            showMessage(employeeAllowancesMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
        }
    }

    // --- Render Employee Allowances Table ---
    async function renderEmployeeAllowancesTable(employeeAllowances) {
        employeeAllowancesTableBody.innerHTML = '';
        if (employeeAllowances.length === 0) {
            employeeAllowancesTableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500">
                        ยังไม่มีข้อมูลเบี้ยเลี้ยงพนักงาน
                    </td>
                </tr>`;
            return;
        }

        const employeeMap = new Map();
        const allowanceTypeMap = new Map();
        try {
            const [empResponse, allowanceTypeResponse] = await Promise.all([
                fetch(`${DATA_MGMT_API_BASE_URL}/employees/`),
                fetch(`${API_BASE_URL}/allowance-types/`)
            ]);
            const employees = await empResponse.json();
            const allowanceTypes = await allowanceTypeResponse.json();
            employees.forEach(emp => employeeMap.set(emp.id, `${emp.first_name} ${emp.last_name}`));
            allowanceTypes.forEach(type => allowanceTypeMap.set(type.id, type.name));
        } catch (error) {
            console.error('Failed to pre-fetch employee/allowance type data for table rendering:', error);
            showMessage(employeeAllowancesMessage, 'ไม่สามารถโหลดข้อมูลพนักงาน/ประเภทเบี้ยเลี้ยงได้บางส่วน', true);
        }

        employeeAllowances.forEach(ea => {
            const row = employeeAllowancesTableBody.insertRow();
            row.className = 'hover:bg-gray-50';
            
            const employeeName = employeeMap.get(ea.employee_id) || `ID: ${ea.employee_id} (ไม่พบข้อมูล)`;
            const allowanceTypeName = allowanceTypeMap.get(ea.allowance_type_id) || `ID: ${ea.allowance_type_id} (ไม่พบข้อมูล)`;
            const effectiveDateDisplay = formatDateToInput(ea.effective_date);

            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${ea.id}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${employeeName}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${allowanceTypeName}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${ea.amount.toFixed(2)}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${effectiveDateDisplay}</td>
                <td class="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                    <button data-id="${ea.id}" class="edit-btn bg-yellow-500 hover:bg-yellow-600 text-white py-1 px-3 rounded-md mr-2 transition duration-150">แก้ไข</button>
                    <button data-id="${ea.id}" class="delete-btn bg-red-600 hover:bg-red-700 text-white py-1 px-3 rounded-md transition duration-150">ลบ</button>
                </td>
            `;
        });

        // Add Event Listeners for Edit and Delete buttons
        document.querySelectorAll('.edit-btn').forEach(button => {
            button.addEventListener('click', async (event) => {
                const id = event.target.dataset.id;
                try {
                    const response = await fetch(`${API_BASE_URL}/employee-allowances/${id}`);
                    if (!response.ok) {
                        const errorData = await response.json();
                        console.error('API Error (fetch employee allowance for edit):', errorData);
                        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
                    }
                    const ea = await response.json();
                    
                    editEmployeeAllowanceIdInput.value = ea.id;
                    await fetchDropdownData(); // Re-fetch to ensure latest options for dropdowns
                    editEmployeeIdSelect.value = ea.employee_id;
                    editAllowanceTypeIdSelect.value = ea.allowance_type_id;
                    editAmountInput.value = ea.amount;
                    editEffectiveDateInput.value = formatDateToInput(ea.effective_date);

                    editEmployeeAllowanceModal.style.display = 'flex'; // Show Modal
                } catch (error) {
                    console.error('Error fetching employee allowance for edit:', error);
                    showMessage(employeeAllowancesMessage, `เกิดข้อผิดพลาดในการโหลดเบี้ยเลี้ยงพนักงานเพื่อแก้ไข: ${error.message}`, true);
                }
            });
        });

        document.querySelectorAll('.delete-btn').forEach(button => {
            button.addEventListener('click', async (event) => {
                const id = event.target.dataset.id;
                if (confirm(`คุณแน่ใจหรือไม่ที่ต้องการลบเบี้ยเลี้ยงพนักงาน ID: ${id} นี้?`)) {
                    try {
                        const response = await fetch(`${API_BASE_URL}/employee-allowances/${id}`, {
                            method: 'DELETE',
                        });
                        if (!response.ok) {
                            const errorData = await response.json();
                            console.error('API Error (delete employee allowance):', errorData);
                            throw new Error(errorData.detail || 'เกิดข้อผิดพลาดในการลบเบี้ยเลี้ยงพนักงาน');
                        }
                        showMessage(employeeAllowancesMessage, 'ลบเบี้ยเลี้ยงพนักงานเรียบร้อยแล้ว');
                        fetchEmployeeAllowances(); // Reload data
                    } catch (error) {
                        console.error('Error deleting employee allowance:', error);
                        showMessage(employeeAllowancesMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
                    }
                }
            });
        });
    }

    // --- Event Listener for Add Employee Allowance Form ---
    addEmployeeAllowanceForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        
        const employeeId = addEmployeeIdSelect.value;
        const allowanceTypeId = addAllowanceTypeIdSelect.value;
        const amount = parseFloat(addAmountInput.value);
        const effectiveDate = addEffectiveDateInput.value;

        if (!employeeId || !allowanceTypeId || !amount || !effectiveDate) {
            showMessage(addEmployeeAllowanceMessage, 'กรุณากรอกข้อมูลที่จำเป็นทั้งหมด', true);
            return;
        }

        try {
            const data = {
                employee_id: parseInt(employeeId, 10),
                allowance_type_id: parseInt(allowanceTypeId, 10),
                amount: amount,
                effective_date: effectiveDate
            };

            const response = await fetch(`${API_BASE_URL}/employee-allowances/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.error('API Error (add employee allowance):', errorData);
                if (Array.isArray(errorData.detail) && errorData.detail.length > 0) {
                    const validationErrors = errorData.detail.map(err => `${err.loc.join('.')} - ${err.msg}`).join('\n');
                    throw new Error(`ข้อมูลไม่ถูกต้อง:\n${validationErrors}`);
                }
                throw new Error(errorData.detail || 'เกิดข้อผิดพลาดในการเพิ่มเบี้ยเลี้ยงพนักงาน');
            }

            const newEa = await response.json();
            showMessage(addEmployeeAllowanceMessage, `เพิ่มเบี้ยเลี้ยงพนักงาน ID: ${newEa.id} เรียบร้อยแล้ว`);
            addEmployeeAllowanceForm.reset(); // Clear form
            addEmployeeIdSelect.value = ''; // Reset dropdowns
            addAllowanceTypeIdSelect.value = '';
            fetchEmployeeAllowances(); // Load new data
        } catch (error) {
            console.error('Final caught error adding employee allowance:', error);
            showMessage(addEmployeeAllowanceMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
        }
    });

    // --- Event Listener for Edit Employee Allowance Form ---
    editEmployeeAllowanceForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const employeeAllowanceId = editEmployeeAllowanceIdInput.value;
        
        const employeeId = editEmployeeIdSelect.value;
        const allowanceTypeId = editAllowanceTypeIdSelect.value;
        const amount = parseFloat(editAmountInput.value);
        const effectiveDate = editEffectiveDateInput.value;

        if (!employeeId || !allowanceTypeId || !amount || !effectiveDate) {
            showMessage(editEmployeeAllowanceMessage, 'กรุณากรอกข้อมูลที่จำเป็นทั้งหมด', true);
            return;
        }

        try {
            const data = {
                employee_id: parseInt(employeeId, 10),
                allowance_type_id: parseInt(allowanceTypeId, 10),
                amount: amount,
                effective_date: effectiveDate
            };
            
            // Remove null or empty string fields from data object before sending for partial update
            Object.keys(data).forEach(key => {
                if (data[key] === null || data[key] === '') {
                    delete data[key];
                }
            });

            const response = await fetch(`${API_BASE_URL}/employee-allowances/${employeeAllowanceId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.error('API Error (edit employee allowance):', errorData);
                if (Array.isArray(errorData.detail) && errorData.detail.length > 0) {
                    const validationErrors = errorData.detail.map(err => `${err.loc.join('.')} - ${err.msg}`).join('\n');
                    throw new Error(`ข้อมูลไม่ถูกต้อง:\n${validationErrors}`);
                }
                throw new Error(errorData.detail || 'เกิดข้อผิดพลาดในการอัปเดตเบี้ยเลี้ยงพนักงาน');
            }

            const updatedEa = await response.json();
            showMessage(employeeAllowancesMessage, `อัปเดตเบี้ยเลี้ยงพนักงาน ID: ${updatedEa.id} เรียบร้อยแล้ว`);
            editEmployeeAllowanceModal.style.display = 'none'; // Hide Modal
            fetchEmployeeAllowances(); // Load new data
        } catch (error) {
            console.error('Final caught error updating employee allowance:', error);
            showMessage(editEmployeeAllowanceMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
        }
    });

    // --- Event Listener for closing Edit Modal ---
    closeEditModalButton.addEventListener('click', () => {
        editEmployeeAllowanceModal.style.display = 'none';
        editEmployeeAllowanceMessage.textContent = '';
        editEffectiveDateInput.value = '';
    });

    // Initial loads
    fetchDropdownData();
    fetchEmployeeAllowances();
});
