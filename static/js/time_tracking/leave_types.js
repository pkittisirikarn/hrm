document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = '/api/v1/time-tracking';

    // Elements for Adding Leave Type
    const addLeaveTypeForm = document.getElementById('addLeaveTypeForm');
    const addLeaveTypeMessage = document.getElementById('addLeaveTypeMessage');
    const addNameInput = document.getElementById('addName');
    const addDescriptionInput = document.getElementById('addDescription');
    const addMaxDaysPerYearInput = document.getElementById('addMaxDaysPerYear');
    const addIsPaidLeaveCheckbox = document.getElementById('addIsPaidLeave');

    // Elements for Listing Leave Types
    const leaveTypesTableBody = document.getElementById('leaveTypesTableBody');
    const leaveTypesMessage = document.getElementById('leaveTypesMessage');

    // Elements for Editing Leave Type Modal
    const editLeaveTypeModal = document.getElementById('editLeaveTypeModal');
    const closeEditModalButton = document.getElementById('closeEditModalButton');
    const editLeaveTypeForm = document.getElementById('editLeaveTypeForm');
    const editLeaveTypeMessage = document.getElementById('editLeaveTypeMessage');

    // Edit Form Fields
    const editLeaveTypeIdInput = document.getElementById('editLeaveTypeId');
    const editNameInput = document.getElementById('editName');
    const editDescriptionInput = document.getElementById('editDescription');
    const editMaxDaysPerYearInput = document.getElementById('editMaxDaysPerYear');
    const editIsPaidLeaveCheckbox = document.getElementById('editIsPaidLeave');

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

    // --- Fetch Leave Types from API and Render Table ---
    async function fetchLeaveTypes() {
        leaveTypesTableBody.innerHTML = `
            <tr>
                <td colspan="6" class="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500">
                    กำลังโหลดข้อมูล...
                </td>
            </tr>`;
        try {
            const response = await fetch(`${API_BASE_URL}/leave-types/`);
            if (!response.ok) {
                const errorMsg = await formatApiErrorDetail(response);
                throw new Error(errorMsg);
            }
            const leaveTypes = await response.json();
            renderLeaveTypesTable(leaveTypes);
        } catch (error) {
            console.error('Error fetching leave types:', error);
            leaveTypesTableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="px-6 py-4 whitespace-nowrap text-center text-sm text-red-600">
                        เกิดข้อผิดพลาดในการโหลดข้อมูลประเภทการลา: ${error.message}
                    </td>
                </tr>`;
            showMessage(leaveTypesMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
        }
    }

    // --- Render Leave Types Table ---
    function renderLeaveTypesTable(leaveTypes) {
        leaveTypesTableBody.innerHTML = '';
        if (leaveTypes.length === 0) {
            leaveTypesTableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500">
                        ยังไม่มีข้อมูลประเภทการลา
                    </td>
                </tr>`;
            return;
        }

        leaveTypes.forEach(leaveType => {
            const row = leaveTypesTableBody.insertRow();
            row.className = 'hover:bg-gray-50';

            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${leaveType.id}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${leaveType.name}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${leaveType.description || '-'}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${leaveType.max_days_per_year} วัน</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${leaveType.is_paid_leave ? 'ใช่' : 'ไม่ใช่'}</td>
                <td class="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                    <button data-id="${leaveType.id}" class="edit-btn bg-yellow-500 hover:bg-yellow-600 text-white py-1 px-3 rounded-md mr-2 transition duration-150">แก้ไข</button>
                    <button data-id="${leaveType.id}" class="delete-btn bg-red-600 hover:bg-red-700 text-white py-1 px-3 rounded-md transition duration-150">ลบ</button>
                </td>
            `;
        });

        // Add Event Listeners for Edit and Delete buttons
        document.querySelectorAll('.edit-btn').forEach(button => {
            button.addEventListener('click', async (event) => {
                const id = event.target.dataset.id;
                try {
                    const response = await fetch(`${API_BASE_URL}/leave-types/${id}`);
                    if (!response.ok) {
                        const errorMsg = await formatApiErrorDetail(response);
                        throw new Error(errorMsg);
                    }
                    const leaveType = await response.json();
                    
                    editLeaveTypeIdInput.value = leaveType.id;
                    editNameInput.value = leaveType.name;
                    editDescriptionInput.value = leaveType.description || '';
                    editMaxDaysPerYearInput.value = leaveType.max_days_per_year;
                    editIsPaidLeaveCheckbox.checked = leaveType.is_paid_leave;

                    editLeaveTypeModal.style.display = 'flex'; // Show Modal
                } catch (error) {
                    console.error('Error fetching leave type for edit:', error);
                    showMessage(leaveTypesMessage, `เกิดข้อผิดพลาดในการโหลดประเภทการลาเพื่อแก้ไข: ${error.message}`, true);
                }
            });
        });

        document.querySelectorAll('.delete-btn').forEach(button => {
            button.addEventListener('click', async (event) => {
                const id = event.target.dataset.id;
                if (confirm(`คุณแน่ใจหรือไม่ที่ต้องการลบประเภทการลา ID: ${id} นี้?`)) {
                    try {
                        const response = await fetch(`${API_BASE_URL}/leave-types/${id}`, {
                            method: 'DELETE',
                        });
                        if (!response.ok) {
                            const errorMsg = await formatApiErrorDetail(response);
                            throw new Error(errorMsg);
                        }
                        showMessage(leaveTypesMessage, 'ลบประเภทการลาเรียบร้อยแล้ว');
                        fetchLeaveTypes(); // Reload data
                    } catch (error) {
                        console.error('Error deleting leave type:', error);
                        showMessage(leaveTypesMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
                    }
                }
            });
        });
    }

    // --- Event Listener for Add Leave Type Form ---
    addLeaveTypeForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        
        const name = addNameInput.value.trim();
        const description = addDescriptionInput.value.trim() || null;
        const maxDaysPerYear = parseInt(addMaxDaysPerYearInput.value);
        const isPaidLeave = addIsPaidLeaveCheckbox.checked;

        if (!name) {
            showMessage(addLeaveTypeMessage, 'กรุณากรอกชื่อประเภทการลา', true);
            return;
        }

        addLeaveTypeMessage.textContent = 'กำลังเพิ่มประเภทการลา...';
        addLeaveTypeMessage.className = 'mt-4 text-sm font-medium text-blue-600';

        try {
            const data = {
                name: name,
                description: description,
                max_days_per_year: maxDaysPerYear,
                is_paid_leave: isPaidLeave
            };

            const response = await fetch(`${API_BASE_URL}/leave-types/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });

            if (!response.ok) {
                const errorMsg = await formatApiErrorDetail(response);
                console.error('API Error (add leave type):', errorMsg);
                throw new Error(errorMsg);
            }

            const newLeaveType = await response.json();
            showMessage(addLeaveTypeMessage, `เพิ่มประเภทการลา "${newLeaveType.name}" เรียบร้อยแล้ว`);
            addLeaveTypeForm.reset(); // Clear form
            fetchLeaveTypes(); // Reload data
        } catch (error) {
            console.error('Final caught error adding leave type:', error);
            showMessage(addLeaveTypeMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
        }
    });

    // --- Event Listener for Edit Leave Type Form ---
    editLeaveTypeForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const leaveTypeId = editLeaveTypeIdInput.value;
        
        const name = editNameInput.value.trim();
        const description = editDescriptionInput.value.trim() || null;
        const maxDaysPerYear = parseInt(editMaxDaysPerYearInput.value);
        const isPaidLeave = editIsPaidLeaveCheckbox.checked;

        if (!name) {
            showMessage(editLeaveTypeMessage, 'กรุณากรอกชื่อประเภทการลา', true);
            return;
        }

        editLeaveTypeMessage.textContent = 'กำลังอัปเดตประเภทการลา...';
        editLeaveTypeMessage.className = 'mt-4 text-sm font-medium text-blue-600';

        try {
            const data = {
                name: name,
                description: description,
                max_days_per_year: maxDaysPerYear,
                is_paid_leave: isPaidLeave
            };

            const response = await fetch(`${API_BASE_URL}/leave-types/${leaveTypeId}`, {
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

            const updatedLeaveType = await response.json();
            showMessage(leaveTypesMessage, `อัปเดตประเภทการลา "${updatedLeaveType.name}" เรียบร้อยแล้ว`);
            editLeaveTypeModal.style.display = 'none'; // Hide Modal
            fetchLeaveTypes(); // Reload data
        } catch (error) {
            console.error('Final caught error updating leave type:', error);
            showMessage(editLeaveTypeMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
        }
    });

    // --- Event Listener for closing Edit Modal ---
    closeEditModalButton.addEventListener('click', () => {
        editLeaveTypeModal.style.display = 'none';
        editLeaveTypeMessage.textContent = '';
    });

    // Initial loads
    fetchLeaveTypes();
});
