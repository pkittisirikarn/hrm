document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = '/api/v1/payroll';
    const DATA_MGMT_API_BASE_URL = '/api/v1/data-management'; // For fetching employees

    // Elements for Adding Salary Structure
    const addSalaryStructureForm = document.getElementById('addSalaryStructureForm');
    const addSalaryStructureMessage = document.getElementById('addSalaryStructureMessage');
    const addEmployeeIdSelect = document.getElementById('addEmployeeId');
    const addBaseSalaryInput = document.getElementById('addBaseSalary');
    const addEffectiveDateInput = document.getElementById('addEffectiveDate');

    // Elements for Listing Salary Structures
    const salaryStructuresTableBody = document.getElementById('salaryStructuresTableBody');
    const salaryStructuresMessage = document.getElementById('salaryStructuresMessage');

    // Elements for Editing Salary Structure Modal
    const editSalaryStructureModal = document.getElementById('editSalaryStructureModal');
    const closeEditModalButton = document.getElementById('closeEditModalButton');
    const editSalaryStructureForm = document.getElementById('editSalaryStructureForm');
    const editSalaryStructureMessage = document.getElementById('editSalaryStructureMessage');

    // Edit Form Fields
    const editSalaryStructureIdInput = document.getElementById('editSalaryStructureId');
    const editEmployeeNameInput = document.getElementById('editEmployeeName'); // Display employee name, not editable
    const editBaseSalaryInput = document.getElementById('editBaseSalary');
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

    // --- Fetch Employees for Dropdowns ---
    async function fetchEmployeesForDropdowns() {
        try {
            const response = await fetch(`${DATA_MGMT_API_BASE_URL}/employees/`);
            if (!response.ok) {
                const errorData = await response.json();
                console.error('API Error (fetch employees):', errorData);
                throw new Error(errorData.detail || `HTTP error! status: ${response.status} for employees`);
            }
            const employees = await response.json();
            populateEmployeeDropdown(addEmployeeIdSelect, employees);
        } catch (error) {
            console.error('Error fetching employees for dropdowns:', error);
            showMessage(addSalaryStructureMessage, `ไม่สามารถโหลดข้อมูลพนักงาน: ${error.message}`, true);
            showMessage(salaryStructuresMessage, `ไม่สามารถโหลดข้อมูลพนักงาน: ${error.message}`, true);
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

    // --- Fetch Salary Structures from API and Render Table ---
    async function fetchSalaryStructures() {
        salaryStructuresTableBody.innerHTML = `
            <tr>
                <td colspan="5" class="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500">
                    กำลังโหลดข้อมูล...
                </td>
            </tr>`;
        try {
            const response = await fetch(`${API_BASE_URL}/salary-structures/`);
            if (!response.ok) {
                const errorData = await response.json();
                console.error('API Error (fetch salary structures):', errorData);
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            const salaryStructures = await response.json();
            renderSalaryStructuresTable(salaryStructures);
        } catch (error) {
            console.error('Error fetching salary structures:', error);
            salaryStructuresTableBody.innerHTML = `
                <tr>
                    <td colspan="5" class="px-6 py-4 whitespace-nowrap text-center text-sm text-red-600">
                        เกิดข้อผิดพลาดในการโหลดโครงสร้างเงินเดือน: ${error.message}
                    </td>
                </tr>`;
            showMessage(salaryStructuresMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
        }
    }

    // --- Render Salary Structures Table ---
    async function renderSalaryStructuresTable(salaryStructures) {
        salaryStructuresTableBody.innerHTML = '';
        if (salaryStructures.length === 0) {
            salaryStructuresTableBody.innerHTML = `
                <tr>
                    <td colspan="5" class="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500">
                        ยังไม่มีข้อมูลเงินเดือนพื้นฐาน
                    </td>
                </tr>`;
            return;
        }

        const employeeMap = new Map();
        try {
            const empResponse = await fetch(`${DATA_MGMT_API_BASE_URL}/employees/`);
            const employees = await empResponse.json();
            employees.forEach(emp => employeeMap.set(emp.id, `${emp.first_name} ${emp.last_name}`));
        } catch (error) {
            console.error('Failed to pre-fetch employees for table rendering:', error);
            showMessage(salaryStructuresMessage, 'ไม่สามารถโหลดชื่อพนักงานได้บางส่วน', true);
        }

        salaryStructures.forEach(ss => {
            const row = salaryStructuresTableBody.insertRow();
            row.className = 'hover:bg-gray-50';
            
            const employeeName = employeeMap.get(ss.employee_id) || `ID: ${ss.employee_id} (ไม่พบข้อมูล)`;

            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${ss.id}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${employeeName}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${ss.base_salary.toFixed(2)}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${formatDateToInput(ss.effective_date)}</td>
                <td class="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                    <button data-id="${ss.id}" class="edit-btn bg-yellow-500 hover:bg-yellow-600 text-white py-1 px-3 rounded-md mr-2 transition duration-150">แก้ไข</button>
                    <button data-id="${ss.id}" class="delete-btn bg-red-600 hover:bg-red-700 text-white py-1 px-3 rounded-md transition duration-150">ลบ</button>
                </td>
            `;
        });

        // Add Event Listeners for Edit and Delete buttons
        document.querySelectorAll('.edit-btn').forEach(button => {
            button.addEventListener('click', async (event) => {
                const id = event.target.dataset.id;
                try {
                    const response = await fetch(`${API_BASE_URL}/salary-structures/${id}`);
                    if (!response.ok) {
                        const errorData = await response.json();
                        console.error('API Error (fetch salary structure for edit):', errorData);
                        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
                    }
                    const ss = await response.json();
                    
                    editSalaryStructureIdInput.value = ss.id;
                    editEmployeeNameInput.value = employeeMap.get(ss.employee_id) || `ID: ${ss.employee_id} (ไม่พบข้อมูล)`;
                    editBaseSalaryInput.value = ss.base_salary;
                    editEffectiveDateInput.value = formatDateToInput(ss.effective_date);

                    editSalaryStructureModal.style.display = 'flex'; // Show Modal
                } catch (error) {
                    console.error('Error fetching salary structure for edit:', error);
                    showMessage(salaryStructuresMessage, `เกิดข้อผิดพลาดในการโหลดโครงสร้างเงินเดือนเพื่อแก้ไข: ${error.message}`, true);
                }
            });
        });

        document.querySelectorAll('.delete-btn').forEach(button => {
            button.addEventListener('click', async (event) => {
                const id = event.target.dataset.id;
                if (confirm(`คุณแน่ใจหรือไม่ที่ต้องการลบเงินเดือนพื้นฐาน ID: ${id} นี้?`)) {
                    try {
                        const response = await fetch(`${API_BASE_URL}/salary-structures/${id}`, {
                            method: 'DELETE',
                        });
                        if (!response.ok) {
                            const errorData = await response.json();
                            console.error('API Error (delete salary structure):', errorData);
                            throw new Error(errorData.detail || 'เกิดข้อผิดพลาดในการลบเงินเดือนพื้นฐาน');
                        }
                        showMessage(salaryStructuresMessage, 'ลบเงินเดือนพื้นฐานเรียบร้อยแล้ว');
                        fetchSalaryStructures(); // Reload data
                    } catch (error) {
                        console.error('Error deleting salary structure:', error);
                        showMessage(salaryStructuresMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
                    }
                }
            });
        });
    }

    // --- Event Listener for Add Salary Structure Form ---
    addSalaryStructureForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        
        const employeeId = addEmployeeIdSelect.value;
        const baseSalary = parseFloat(addBaseSalaryInput.value);
        const effectiveDate = addEffectiveDateInput.value;

        if (!employeeId || !baseSalary || !effectiveDate) {
            showMessage(addSalaryStructureMessage, 'กรุณากรอกข้อมูลที่จำเป็นทั้งหมด (พนักงาน, เงินเดือนพื้นฐาน, วันที่มีผลบังคับใช้)', true);
            return;
        }

        try {
            const data = {
                employee_id: parseInt(employeeId, 10),
                base_salary: baseSalary,
                effective_date: effectiveDate
            };

            const response = await fetch(`${API_BASE_URL}/salary-structures/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.error('API Error (add salary structure):', errorData);
                if (Array.isArray(errorData.detail) && errorData.detail.length > 0) {
                    const validationErrors = errorData.detail.map(err => `${err.loc.join('.')} - ${err.msg}`).join('\n');
                    throw new Error(`ข้อมูลไม่ถูกต้อง:\n${validationErrors}`);
                }
                throw new Error(errorData.detail || 'เกิดข้อผิดพลาดในการเพิ่มเงินเดือนพื้นฐาน');
            }

            const newSs = await response.json();
            showMessage(addSalaryStructureMessage, `เพิ่มเงินเดือนพื้นฐาน ID: ${newSs.id} เรียบร้อยแล้ว`);
            addSalaryStructureForm.reset(); // Clear form
            addEmployeeIdSelect.value = ''; // Reset dropdown
            fetchSalaryStructures(); // Load new data
        } catch (error) {
            console.error('Final caught error adding salary structure:', error);
            showMessage(addSalaryStructureMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
        }
    });

    // --- Event Listener for Edit Salary Structure Form ---
    editSalaryStructureForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const salaryStructureId = editSalaryStructureIdInput.value;
        
        const baseSalary = parseFloat(editBaseSalaryInput.value);
        const effectiveDate = editEffectiveDateInput.value;

        if (!baseSalary || !effectiveDate) {
            showMessage(editSalaryStructureMessage, 'กรุณากรอกข้อมูลที่จำเป็นทั้งหมด (เงินเดือนพื้นฐาน, วันที่มีผลบังคับใช้)', true);
            return;
        }

        try {
            const data = {
                base_salary: baseSalary,
                effective_date: effectiveDate
            };
            
            // Remove null or empty string fields from data object before sending for partial update
            Object.keys(data).forEach(key => {
                if (data[key] === null || data[key] === '') {
                    delete data[key];
                }
            });

            const response = await fetch(`${API_BASE_URL}/salary-structures/${salaryStructureId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.error('API Error (edit salary structure):', errorData);
                if (Array.isArray(errorData.detail) && errorData.detail.length > 0) {
                    const validationErrors = errorData.detail.map(err => `${err.loc.join('.')} - ${err.msg}`).join('\n');
                    throw new Error(`ข้อมูลไม่ถูกต้อง:\n${validationErrors}`);
                }
                throw new Error(errorData.detail || 'เกิดข้อผิดพลาดในการอัปเดตเงินเดือนพื้นฐาน');
            }

            const updatedSs = await response.json();
            showMessage(salaryStructuresMessage, `อัปเดตเงินเดือนพื้นฐาน ID: ${updatedSs.id} เรียบร้อยแล้ว`);
            editSalaryStructureModal.style.display = 'none'; // Hide Modal
            fetchSalaryStructures(); // Load new data
        } catch (error) {
            console.error('Final caught error updating salary structure:', error);
            showMessage(editSalaryStructureMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
        }
    });

    // --- Event Listener for closing Edit Modal ---
    closeEditModalButton.addEventListener('click', () => {
        editSalaryStructureModal.style.display = 'none';
        editSalaryStructureMessage.textContent = '';
    });

    // Initial loads
    fetchEmployeesForDropdowns();
    fetchSalaryStructures();
});
