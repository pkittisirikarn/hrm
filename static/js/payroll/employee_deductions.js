document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = '/api/v1/payroll';
    const DATA_MGMT_API_BASE_URL = '/api/v1/data-management'; // For fetching employees

    // Elements for Adding Employee Deduction
    const addEmployeeDeductionForm = document.getElementById('addEmployeeDeductionForm');
    const addEmployeeDeductionMessage = document.getElementById('addEmployeeDeductionMessage');
    const addEmployeeIdSelect = document.getElementById('addEmployeeId');
    const addDeductionTypeIdSelect = document.getElementById('addDeductionTypeId');
    const addAmountInput = document.getElementById('addAmount');
    const addEffectiveDateInput = document.getElementById('addEffectiveDate');

    // Elements for Listing Employee Deductions
    const employeeDeductionsTableBody = document.getElementById('employeeDeductionsTableBody');
    const employeeDeductionsMessage = document.getElementById('employeeDeductionsMessage');

    // Elements for Editing Employee Deduction Modal
    const editEmployeeDeductionModal = document.getElementById('editEmployeeDeductionModal');
    const closeEditModalButton = document.getElementById('closeEditModalButton');
    const editEmployeeDeductionForm = document.getElementById('editEmployeeDeductionForm');
    const editEmployeeDeductionMessage = document.getElementById('editEmployeeDeductionMessage');

    // Edit Form Fields
    const editEmployeeDeductionIdInput = document.getElementById('editEmployeeDeductionId');
    const editEmployeeIdSelect = document.getElementById('editEmployeeId');
    const editDeductionTypeIdSelect = document.getElementById('editDeductionTypeId');
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

    // --- Fetch Dropdown Data (Employees, Deduction Types) ---
    async function fetchDropdownData() {
        try {
            const [empResponse, deductionTypeResponse] = await Promise.all([
                fetch(`${DATA_MGMT_API_BASE_URL}/employees/`),
                fetch(`${API_BASE_URL}/deduction-types/`)
            ]);

            if (!empResponse.ok) throw new Error(`HTTP error! status: ${empResponse.status} for employees`);
            if (!deductionTypeResponse.ok) throw new Error(`HTTP error! status: ${deductionTypeResponse.status} for deduction types`);

            const employees = await empResponse.json();
            const deductionTypes = await deductionTypeResponse.json();

            populateEmployeeDropdown(addEmployeeIdSelect, employees);
            populateDeductionTypeDropdown(addDeductionTypeIdSelect, deductionTypes);
            populateEmployeeDropdown(editEmployeeIdSelect, employees);
            populateDeductionTypeDropdown(editDeductionTypeIdSelect, deductionTypes);

        } catch (error) {
            console.error('Error fetching dropdown data:', error);
            showMessage(addEmployeeDeductionMessage, `ไม่สามารถโหลดข้อมูลพนักงาน/ประเภทรายการหัก: ${error.message}`, true);
            showMessage(employeeDeductionsMessage, `ไม่สามารถโหลดข้อมูลพนักงาน/ประเภทรายการหัก: ${error.message}`, true);
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

    function populateDeductionTypeDropdown(selectElement, deductionTypes, selectedId = null) {
        selectElement.innerHTML = '<option value="">-- เลือกประเภทรายการหัก --</option>'; // Default option
        deductionTypes.forEach(type => {
            const option = document.createElement('option');
            option.value = type.id;
            option.textContent = type.name;
            if (selectedId && type.id === selectedId) {
                option.selected = true;
            }
            selectElement.appendChild(option);
        });
    }

    // --- Fetch Employee Deductions from API and Render Table ---
    async function fetchEmployeeDeductions() {
        employeeDeductionsTableBody.innerHTML = `
            <tr>
                <td colspan="6" class="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500">
                    กำลังโหลดข้อมูล...
                </td>
            </tr>`;
        try {
            const response = await fetch(`${API_BASE_URL}/employee-deductions/`);
            if (!response.ok) {
                const errorData = await response.json();
                console.error('API Error (fetch employee deductions):', errorData);
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            const employeeDeductions = await response.json();
            renderEmployeeDeductionsTable(employeeDeductions);
        } catch (error) {
            console.error('Error fetching employee deductions:', error);
            employeeDeductionsTableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="px-6 py-4 whitespace-nowrap text-center text-sm text-red-600">
                        เกิดข้อผิดพลาดในการโหลดข้อมูลรายการหักพนักงาน: ${error.message}
                    </td>
                </tr>`;
            showMessage(employeeDeductionsMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
        }
    }

    // --- Render Employee Deductions Table ---
    async function renderEmployeeDeductionsTable(employeeDeductions) {
        employeeDeductionsTableBody.innerHTML = '';
        if (employeeDeductions.length === 0) {
            employeeDeductionsTableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500">
                        ยังไม่มีข้อมูลรายการหักพนักงาน
                    </td>
                </tr>`;
            return;
        }

        const employeeMap = new Map();
        const deductionTypeMap = new Map();
        try {
            const [empResponse, deductionTypeResponse] = await Promise.all([
                fetch(`${DATA_MGMT_API_BASE_URL}/employees/`),
                fetch(`${API_BASE_URL}/deduction-types/`)
            ]);
            const employees = await empResponse.json();
            const deductionTypes = await deductionTypeResponse.json();
            employees.forEach(emp => employeeMap.set(emp.id, `${emp.first_name} ${emp.last_name}`));
            deductionTypes.forEach(type => deductionTypeMap.set(type.id, type.name));
        } catch (error) {
            console.error('Failed to pre-fetch employee/deduction type data for table rendering:', error);
            showMessage(employeeDeductionsMessage, 'ไม่สามารถโหลดข้อมูลพนักงาน/ประเภทรายการหักได้บางส่วน', true);
        }

        employeeDeductions.forEach(ed => {
            const row = employeeDeductionsTableBody.insertRow();
            row.className = 'hover:bg-gray-50';
            
            const employeeName = employeeMap.get(ed.employee_id) || `ID: ${ed.employee_id} (ไม่พบข้อมูล)`;
            const deductionTypeName = deductionTypeMap.get(ed.deduction_type_id) || `ID: ${ed.deduction_type_id} (ไม่พบข้อมูล)`;
            const effectiveDateDisplay = formatDateToInput(ed.effective_date);

            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${ed.id}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${employeeName}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${deductionTypeName}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${ed.amount.toFixed(2)}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${effectiveDateDisplay}</td>
                <td class="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                    <button data-id="${ed.id}" class="edit-btn bg-yellow-500 hover:bg-yellow-600 text-white py-1 px-3 rounded-md mr-2 transition duration-150">แก้ไข</button>
                    <button data-id="${ed.id}" class="delete-btn bg-red-600 hover:bg-red-700 text-white py-1 px-3 rounded-md transition duration-150">ลบ</button>
                </td>
            `;
        });

        // Add Event Listeners for Edit and Delete buttons
        document.querySelectorAll('.edit-btn').forEach(button => {
            button.addEventListener('click', async (event) => {
                const id = event.target.dataset.id;
                try {
                    const response = await fetch(`${API_BASE_URL}/employee-deductions/${id}`);
                    if (!response.ok) {
                        const errorData = await response.json();
                        console.error('API Error (fetch employee deduction for edit):', errorData);
                        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
                    }
                    const ed = await response.json();
                    
                    editEmployeeDeductionIdInput.value = ed.id;
                    await fetchDropdownData(); // Re-fetch to ensure latest options for dropdowns
                    editEmployeeIdSelect.value = ed.employee_id;
                    editDeductionTypeIdSelect.value = ed.deduction_type_id;
                    editAmountInput.value = ed.amount;
                    editEffectiveDateInput.value = formatDateToInput(ed.effective_date);

                    editEmployeeDeductionModal.style.display = 'flex'; // Show Modal
                } catch (error) {
                    console.error('Error fetching employee deduction for edit:', error);
                    showMessage(employeeDeductionsMessage, `เกิดข้อผิดพลาดในการโหลดรายการหักพนักงานเพื่อแก้ไข: ${error.message}`, true);
                }
            });
        });

        document.querySelectorAll('.delete-btn').forEach(button => {
            button.addEventListener('click', async (event) => {
                const id = event.target.dataset.id;
                if (confirm(`คุณแน่ใจหรือไม่ที่ต้องการลบรายการหักพนักงาน ID: ${id} นี้?`)) {
                    try {
                        const response = await fetch(`${API_BASE_URL}/employee-deductions/${id}`, {
                            method: 'DELETE',
                        });
                        if (!response.ok) {
                            const errorData = await response.json();
                            console.error('API Error (delete employee deduction):', errorData);
                            throw new Error(errorData.detail || 'เกิดข้อผิดพลาดในการลบรายการหักพนักงาน');
                        }
                        showMessage(employeeDeductionsMessage, 'ลบรายการหักพนักงานเรียบร้อยแล้ว');
                        fetchEmployeeDeductions(); // Reload data
                    } catch (error) {
                        console.error('Error deleting employee deduction:', error);
                        showMessage(employeeDeductionsMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
                    }
                }
            });
        });
    }

    // --- Event Listener for Add Employee Deduction Form ---
    addEmployeeDeductionForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        
        const employeeId = addEmployeeIdSelect.value;
        const deductionTypeId = addDeductionTypeIdSelect.value;
        const amount = parseFloat(addAmountInput.value);
        const effectiveDate = addEffectiveDateInput.value;

        if (!employeeId || !deductionTypeId || !amount || !effectiveDate) {
            showMessage(addEmployeeDeductionMessage, 'กรุณากรอกข้อมูลที่จำเป็นทั้งหมด', true);
            return;
        }

        try {
            const data = {
                employee_id: parseInt(employeeId, 10),
                deduction_type_id: parseInt(deductionTypeId, 10),
                amount: amount,
                effective_date: effectiveDate
            };

            const response = await fetch(`${API_BASE_URL}/employee-deductions/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.error('API Error (add employee deduction):', errorData);
                if (Array.isArray(errorData.detail) && errorData.detail.length > 0) {
                    const validationErrors = errorData.detail.map(err => `${err.loc.join('.')} - ${err.msg}`).join('\n');
                    throw new Error(`ข้อมูลไม่ถูกต้อง:\n${validationErrors}`);
                }
                throw new Error(errorData.detail || 'เกิดข้อผิดพลาดในการเพิ่มรายการหักพนักงาน');
            }

            const newEd = await response.json();
            showMessage(addEmployeeDeductionMessage, `เพิ่มรายการหักพนักงาน ID: ${newEd.id} เรียบร้อยแล้ว`);
            addEmployeeDeductionForm.reset(); // Clear form
            addEmployeeIdSelect.value = ''; // Reset dropdowns
            addDeductionTypeIdSelect.value = '';
            fetchEmployeeDeductions(); // Load new data
        } catch (error) {
            console.error('Final caught error adding employee deduction:', error);
            showMessage(addEmployeeDeductionMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
        }
    });

    // --- Event Listener for Edit Employee Deduction Form ---
    editEmployeeDeductionForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const employeeDeductionId = editEmployeeDeductionIdInput.value;
        
        const employeeId = editEmployeeIdSelect.value;
        const deductionTypeId = editDeductionTypeIdSelect.value;
        const amount = parseFloat(editAmountInput.value);
        const effectiveDate = editEffectiveDateInput.value;

        if (!employeeId || !deductionTypeId || !amount || !effectiveDate) {
            showMessage(editEmployeeDeductionMessage, 'กรุณากรอกข้อมูลที่จำเป็นทั้งหมด', true);
            return;
        }

        try {
            const data = {
                employee_id: parseInt(employeeId, 10),
                deduction_type_id: parseInt(deductionTypeId, 10),
                amount: amount,
                effective_date: effectiveDate
            };
            
            // Remove null or empty string fields from data object before sending for partial update
            Object.keys(data).forEach(key => {
                if (data[key] === null || data[key] === '') {
                    delete data[key];
                }
            });

            const response = await fetch(`${API_BASE_URL}/employee-deductions/${employeeDeductionId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.error('API Error (edit employee deduction):', errorData);
                if (Array.isArray(errorData.detail) && errorData.detail.length > 0) {
                    const validationErrors = errorData.detail.map(err => `${err.loc.join('.')} - ${err.msg}`).join('\n');
                    throw new Error(`ข้อมูลไม่ถูกต้อง:\n${validationErrors}`);
                }
                throw new Error(errorData.detail || 'เกิดข้อผิดพลาดในการอัปเดตรายการหักพนักงาน');
            }

            const updatedEd = await response.json();
            showMessage(employeeDeductionsMessage, `อัปเดตรายการหักพนักงาน ID: ${updatedEd.id} เรียบร้อยแล้ว`);
            editEmployeeDeductionModal.style.display = 'none'; // Hide Modal
            fetchEmployeeDeductions(); // Load new data
        } catch (error) {
            console.error('Final caught error updating employee deduction:', error);
            showMessage(editEmployeeDeductionMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
        }
    });

    // --- Event Listener for closing Edit Modal ---
    closeEditModalButton.addEventListener('click', () => {
        editEmployeeDeductionModal.style.display = 'none';
        editEmployeeDeductionMessage.textContent = '';
        editEffectiveDateInput.value = '';
    });

    // Initial loads
    fetchDropdownData();
    fetchEmployeeDeductions();
});
