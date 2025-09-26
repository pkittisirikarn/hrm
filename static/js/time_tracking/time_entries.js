document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = '/api/v1/time-tracking';
    const DATA_MANAGEMENT_API_BASE_URL = '/api/v1/data-management';

    // Elements for Time Entry Management
    const addTimeEntryForm = document.getElementById('addTimeEntryForm');
    const addTimeEntryMessage = document.getElementById('addTimeEntryMessage');
    const addEmployeeIdSelect = document.getElementById('addEmployeeId');
    const addCheckInTimeInput = document.getElementById('addCheckInTime'); // Changed from addTimestamp
    const addCheckOutTimeInput = document.getElementById('addCheckOutTime'); // New field
    const addNotesInput = document.getElementById('addNotes'); // New field
    const addStatusSelect = document.getElementById('addStatus'); // New field
    
    const timeEntriesTableBody = document.getElementById('timeEntriesTableBody');
    const timeEntriesMessage = document.getElementById('timeEntriesMessage');

    const editTimeEntryModal = document.getElementById('editTimeEntryModal');
    const closeEditModalButton = document.getElementById('closeEditModalButton');
    const editTimeEntryForm = document.getElementById('editTimeEntryForm');
    const editTimeEntryMessage = document.getElementById('editTimeEntryMessage');

    const editTimeEntryIdInput = document.getElementById('editTimeEntryId');
    const editEmployeeIdSelect = document.getElementById('editEmployeeId');
    const editCheckInTimeInput = document.getElementById('editCheckInTime'); // Changed from editTimestamp
    const editCheckOutTimeInput = document.getElementById('editCheckOutTime'); // New field
    const editNotesInput = document.getElementById('editNotes'); // New field
    const editStatusSelect = document.getElementById('editStatus'); // New field

    // --- Elements for CSV Import ---
    const importCsvForm = document.getElementById('importCsvForm');
    const importCsvMessage = document.getElementById('importCsvMessage');
    const importCsvFileInput = document.getElementById('importCsvFile');
    const importCsvPreviewLink = document.getElementById('importCsvPreviewLink');


    // --- Generic Message Display Function ---
    function showMessage(element, message, isError = false) {
        element.textContent = message;
        element.className = `mt-4 text-sm font-medium ${isError ? 'text-red-600' : 'text-green-600'}`;
        setTimeout(() => {
            element.textContent = '';
            element.className = 'mt-4 text-sm font-medium';
        }, 5000);
    }

    // --- Helper for formatting API error detail ---
    async function formatApiErrorDetail(response) {
        let errorMessage = `เกิดข้อผิดพลาดในการดำเนินการ (HTTP Status: ${response.status})`;
        const contentType = response.headers.get('content-type');

        if (contentType && contentType.includes('application/json')) {
            try {
                const errorData = await response.json();
                if (errorData && errorData.detail) {
                    if (typeof errorData.detail === 'string') {
                        errorMessage = errorData.detail;
                    } else if (Array.isArray(errorData.detail)) {
                        errorMessage = 'ข้อมูลไม่ถูกต้อง:\n' + errorData.detail.map(err => {
                            const fieldName = err.loc.length > 1 ? err.loc[1] : err.loc[0];
                            const msg = err.msg;
                            return `(${fieldName}) - ${msg}`;
                        }).join('\n');
                    } else if (typeof errorData.detail === 'object') {
                        errorMessage = JSON.stringify(errorData.detail);
                    }
                }
            } catch (e) {
                console.error("Failed to parse JSON error response:", e);
                errorMessage = `เกิดข้อผิดพลาดในการอ่านรายละเอียดข้อผิดพลาดจากเซิร์ฟเวอร์ (JSON Parse Error). Status: ${response.status}.`;
                try {
                    const text = await response.text();
                    if (text) errorMessage += ` Response Text: ${text.substring(0, 200)}...`;
                } catch (err) { /* ignore */ }
            }
        } else {
            try {
                const text = await response.text();
                errorMessage = `เซิร์ฟเวอร์เกิดข้อผิดพลาด. Status: ${response.status}. `;
                if (text) errorMessage += `รายละเอียด: ${text.substring(0, 200)}...`;
            } catch (e) {
                console.error("Failed to read non-JSON error response:", e);
                errorMessage = `เซิร์ฟเวอร์เกิดข้อผิดพลาดที่ไม่รู้จัก. Status: ${response.status}.`;
            }
        }
        return errorMessage;
    }

    // --- Helper for datetime input formatting (YYYY-MM-DDTHH:MM) ---
    function formatDateTimeLocal(isoString) {
        if (!isoString) return '';
        // Ensure the date string is parsed as UTC if it doesn't have timezone info
        // to prevent issues with local timezone conversion
        const date = new Date(isoString); 
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        return `${year}-${month}-${day}T${hours}:${minutes}`;
    }

    // --- Fetch Employees for dropdown (from Data Management API) ---
    async function fetchEmployeesForDropdown() {
        try {
            const response = await fetch(`${DATA_MANAGEMENT_API_BASE_URL}/employees/`);
            if (!response.ok) {
                const errorMsg = await formatApiErrorDetail(response);
                throw new Error(errorMsg);
            }
            const employees = await response.json();
            
            addEmployeeIdSelect.innerHTML = '<option value="">เลือกพนักงาน</option>';
            editEmployeeIdSelect.innerHTML = '<option value="">เลือกพนักงาน</option>';

            employees.forEach(emp => {
                const optionAdd = document.createElement('option');
                optionAdd.value = emp.id;
                optionAdd.textContent = `${emp.first_name} ${emp.last_name} (${emp.employee_id_number})`;
                addEmployeeIdSelect.appendChild(optionAdd);

                const optionEdit = document.createElement('option');
                optionEdit.value = emp.id;
                optionEdit.textContent = `${emp.first_name} ${emp.last_name} (${emp.employee_id_number})`;
                editEmployeeIdSelect.appendChild(optionEdit);
            });
        } catch (error) {
            console.error('Error fetching employees:', error);
            showMessage(addTimeEntryMessage, `เกิดข้อผิดพลาดในการโหลดข้อมูลพนักงาน: ${error.message}`, true);
        }
    }

    // --- Fetch Time Entries from API and Render Table ---
    async function fetchTimeEntries() {
        timeEntriesTableBody.innerHTML = `
            <tr>
                <td colspan="6" class="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500">
                    กำลังโหลดข้อมูล...
                </td>
            </tr>`;
        try {
            const response = await fetch(`${API_BASE_URL}/time-entries/`);
            if (!response.ok) {
                const errorMsg = await formatApiErrorDetail(response);
                throw new Error(errorMsg);
            }
            const entries = await response.json();
            renderTimeEntriesTable(entries);
        } catch (error) {
            console.error('Error fetching time entries:', error);
            timeEntriesTableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="px-6 py-4 whitespace-nowrap text-center text-sm text-red-600">
                        เกิดข้อผิดพลาดในการโหลดบันทึกเวลา: ${error.message}
                    </td>
                </tr>`;
            showMessage(timeEntriesMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
        }
    }

    // --- Render Time Entries Table (ปรับปรุง) ---
    function renderTimeEntriesTable(entries) {
        timeEntriesTableBody.innerHTML = '';
        if (entries.length === 0) {
            timeEntriesTableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500">
                        ยังไม่มีข้อมูลบันทึกเวลา
                    </td>
                </tr>`;
            return;
        }

        entries.forEach(entry => {
            const row = timeEntriesTableBody.insertRow();
            row.className = 'hover:bg-gray-50';

            // Access employee_id_number from nested employee object
            const employeeIdNumber = entry.employee ? entry.employee.employee_id_number : 'N/A';
            
            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${entry.id}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${employeeIdNumber}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${entry.check_in_time ? new Date(entry.check_in_time).toLocaleString() : '-'}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${entry.check_out_time ? new Date(entry.check_out_time).toLocaleString() : '-'}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${translateTimeEntryStatus(entry.status)}</td>
                <td class="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                    <button data-id="${entry.id}" class="edit-btn bg-yellow-500 hover:bg-yellow-600 text-white py-1 px-3 rounded-md mr-2 transition duration-150">แก้ไข</button>
                    <button data-id="${entry.id}" class="delete-btn bg-red-600 hover:bg-red-700 text-white py-1 px-3 rounded-md transition duration-150">ลบ</button>
                </td>
            `;
        });

        // Add Event Listeners for Edit and Delete buttons
        document.querySelectorAll('.edit-btn').forEach(button => {
            button.addEventListener('click', async (event) => {
                const id = event.target.dataset.id;
                try {
                    const response = await fetch(`${API_BASE_URL}/time-entries/${id}`);
                    if (!response.ok) {
                        const errorMsg = await formatApiErrorDetail(response);
                        throw new Error(errorMsg);
                    }
                    const entry = await response.json();
                    
                    editTimeEntryIdInput.value = entry.id;
                    editEmployeeIdSelect.value = entry.employee.id; // Use entry.employee.id
                    editCheckInTimeInput.value = formatDateTimeLocal(entry.check_in_time);
                    editCheckOutTimeInput.value = entry.check_out_time ? formatDateTimeLocal(entry.check_out_time) : '';
                    editNotesInput.value = entry.notes || '';
                    editStatusSelect.value = entry.status;

                    editTimeEntryModal.style.display = 'flex'; // Show Modal
                } catch (error) {
                    console.error('Error fetching time entry for edit:', error);
                    showMessage(timeEntriesMessage, `เกิดข้อผิดพลาดในการโหลดบันทึกเวลาเพื่อแก้ไข: ${error.message}`, true);
                }
            });
        });

        document.querySelectorAll('.delete-btn').forEach(button => {
            button.addEventListener('click', async (event) => {
                const id = event.target.dataset.id;
                if (confirm(`คุณแน่ใจหรือไม่ที่ต้องการลบบันทึกเวลา ID: ${id} นี้?`)) {
                    try {
                        const response = await fetch(`${API_BASE_URL}/time-entries/${id}`, {
                            method: 'DELETE',
                        });
                        if (!response.ok) {
                            const errorMsg = await formatApiErrorDetail(response);
                            throw new Error(errorMsg);
                        }
                        showMessage(timeEntriesMessage, 'ลบบันทึกเวลาเรียบร้อยแล้ว');
                        fetchTimeEntries(); // Reload data
                    } catch (error) {
                        console.error('Error deleting time entry:', error);
                        showMessage(timeEntriesMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
                    }
                }
            });
        });
    }

    // --- Function to translate TimeEntryStatus enum to Thai (for display) ---
    function translateTimeEntryStatus(status) {
        switch(status) {
            case "Pending": return "รออนุมัติ";
            case "Approved": return "อนุมัติแล้ว";
            case "Rejected": return "ไม่อนุมัติ";
            default: return status;
        }
    }

    // --- Event Listener for Add Time Entry Form (ปรับปรุง) ---
    addTimeEntryForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        
        const employeeId = addEmployeeIdSelect.value;
        const checkInTime = addCheckInTimeInput.value;
        const checkOutTime = addCheckOutTimeInput.value || null;
        const notes = addNotesInput.value.trim() || null;
        const status = addStatusSelect.value;

        if (!employeeId || !checkInTime || !status) {
            showMessage(addTimeEntryMessage, 'กรุณากรอกข้อมูลเวลาเข้างานและสถานะที่จำเป็นให้ครบถ้วน', true);
            return;
        }

        addTimeEntryMessage.textContent = 'กำลังเพิ่มบันทึกเวลา...';
        addTimeEntryMessage.className = 'mt-4 text-sm font-medium text-blue-600';

        try {
            const data = {
                employee_id: parseInt(employeeId),
                check_in_time: checkInTime + ':00Z', // Ensure ISO format with Z for UTC
                check_out_time: checkOutTime ? checkOutTime + ':00Z' : null,
                notes: notes,
                status: status
            };

            const response = await fetch(`${API_BASE_URL}/time-entries/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });

            if (!response.ok) {
                const errorMsg = await formatApiErrorDetail(response);
                console.error('API Error (add time entry):', errorMsg);
                throw new Error(errorMsg);
            }

            const newEntry = await response.json();
            showMessage(addTimeEntryMessage, `เพิ่มบันทึกเวลา ID: ${newEntry.id} เรียบร้อยแล้ว`);
            addTimeEntryForm.reset(); // Clear form
            fetchTimeEntries(); // Reload data
        } catch (error) {
            console.error('Final caught error adding time entry:', error);
            showMessage(addTimeEntryMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
        }
    });

    // --- Event Listener for Edit Time Entry Form (ปรับปรุง) ---
    editTimeEntryForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const entryId = editTimeEntryIdInput.value;
        
        const employeeId = editEmployeeIdSelect.value;
        const checkInTime = editCheckInTimeInput.value;
        const checkOutTime = editCheckOutTimeInput.value || null;
        const notes = editNotesInput.value.trim() || null;
        const status = editStatusSelect.value;

        if (!employeeId || !checkInTime || !status) {
            showMessage(editTimeEntryMessage, 'กรุณากรอกข้อมูลเวลาเข้างานและสถานะที่จำเป็นให้ครบถ้วน', true);
            return;
        }

        editTimeEntryMessage.textContent = 'กำลังอัปเดตบันทึกเวลา...';
        editTimeEntryMessage.className = 'mt-4 text-sm font-medium text-blue-600';

        try {
            const data = {
                employee_id: parseInt(employeeId),
                check_in_time: checkInTime + ':00Z', // Ensure ISO format with Z for UTC
                check_out_time: checkOutTime ? checkOutTime + ':00Z' : null,
                notes: notes,
                status: status
            };

            const response = await fetch(`${API_BASE_URL}/time-entries/${entryId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });

            if (!response.ok) {
                const errorMsg = await formatApiErrorDetail(response);
                throw new Error(errorMsg);
            }

            const updatedEntry = await response.json();
            showMessage(timeEntriesMessage, `อัปเดตบันทึกเวลา ID: ${updatedEntry.id} เรียบร้อยแล้ว`);
            editTimeEntryModal.style.display = 'none'; // Hide Modal
            fetchTimeEntries(); // Reload data
        } catch (error) {
            console.error('Final caught error updating time entry:', error);
            showMessage(editTimeEntryMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
        }
    });

    // --- Event Listener for closing Edit Modal ---
    closeEditModalButton.addEventListener('click', () => {
        editTimeEntryModal.style.display = 'none';
        editTimeEntryMessage.textContent = '';
    });

    // --- Event Listener for CSV Import Form (ไม่มีการเปลี่ยนแปลงในส่วนนี้) ---
    importCsvForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        const file = importCsvFileInput.files[0];
        if (!file) {
            showMessage(importCsvMessage, 'กรุณาเลือกไฟล์ CSV หรือ Excel เพื่อนำเข้า', true);
            return;
        }

        importCsvMessage.textContent = 'กำลังนำเข้าข้อมูล...';
        importCsvMessage.className = 'mt-4 text-sm font-medium text-blue-600';

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch(`${API_BASE_URL}/time-entries/import`, {
                method: 'POST',
                body: formData, // FormData ไม่ต้องตั้ง Content-Type, browser จะทำเอง
            });

            if (!response.ok) {
                const errorMsg = await formatApiErrorDetail(response);
                console.error('API Error (import CSV):', errorMsg);
                throw new Error(errorMsg);
            }

            const result = await response.json();
            showMessage(importCsvMessage, result.message);
            importCsvForm.reset(); // Clear form
            fetchTimeEntries(); // Reload data
        } catch (error) {
            console.error('Final caught error importing CSV:', error);
            showMessage(importCsvMessage, `เกิดข้อผิดพลาดในการนำเข้าข้อมูล: ${error.message}`, true);
        }
    });

    // Initial loads
    fetchEmployeesForDropdown();
    fetchTimeEntries();
});
