document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = '/api/v1/time-tracking';
    const DATA_MGMT_API_BASE_URL = '/api/v1/data-management';

    // --- Element Selectors ---
    const addLeaveRequestForm = document.getElementById('addLeaveRequestForm');
    const addLeaveRequestMessage = document.getElementById('addLeaveRequestMessage');
    const addEmployeeIdSelect = document.getElementById('addEmployeeId');
    const addLeaveTypeIdSelect = document.getElementById('addLeaveTypeId');
    const addStartDateInput = document.getElementById('addStartDate');
    const addEndDateInput = document.getElementById('addEndDate');
    const addReasonInput = document.getElementById('addReason');

    const leaveRequestsTableBody = document.getElementById('leaveRequestsTableBody');
    const leaveRequestsMessage = document.getElementById('leaveRequestsMessage');

    const editLeaveRequestModal = document.getElementById('editLeaveRequestModal');
    const closeEditModalButton = document.getElementById('closeEditModalButton');
    const editLeaveRequestForm = document.getElementById('editLeaveRequestForm');
    const editLeaveRequestMessage = document.getElementById('editLeaveRequestMessage');

    const editLeaveRequestIdInput = document.getElementById('editLeaveRequestId');
    const editEmployeeIdSelect = document.getElementById('editEmployeeId');
    const editLeaveTypeIdSelect = document.getElementById('editLeaveTypeId');
    const editStartDateInput = document.getElementById('editStartDate');
    const editEndDateInput = document.getElementById('editEndDate');
    const editReasonInput = document.getElementById('editReason');
    const editStatusSelect = document.getElementById('editStatus');

    // --- Helper Functions ---
    function showMessage(element, message, isError = false) {
        if (!element) return;
        element.textContent = message;
        element.className = `mt-4 text-sm font-medium ${isError ? 'text-red-600' : 'text-green-600'}`;
        setTimeout(() => { element.textContent = ''; }, 5000);
    }

    function formatDateTimeLocal(isoString) {
        if (!isoString) return '';
        const date = new Date(isoString);
        // Adjust for timezone offset to display correctly in the user's local time
        date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
        // Format to 'YYYY-MM-DDTHH:mm'
        return date.toISOString().slice(0, 16);
    }

    // --- Data Fetching and Population ---
    async function fetchDropdownData() {
        try {
            const [empResponse, leaveTypeResponse] = await Promise.all([
                fetch(`${DATA_MGMT_API_BASE_URL}/employees/`),
                fetch(`${API_BASE_URL}/leave-types/`)
            ]);

            if (!empResponse.ok) throw new Error(`Failed to fetch employees: ${empResponse.statusText}`);
            if (!leaveTypeResponse.ok) throw new Error(`Failed to fetch leave types: ${leaveTypeResponse.statusText}`);

            const employees = await empResponse.json();
            const leaveTypes = await leaveTypeResponse.json();

            populateEmployeeDropdown(addEmployeeIdSelect, employees);
            populateLeaveTypeDropdown(addLeaveTypeIdSelect, leaveTypes);
            populateEmployeeDropdown(editEmployeeIdSelect, employees);
            populateLeaveTypeDropdown(editLeaveTypeIdSelect, leaveTypes);
        } catch (error) {
            console.error('Error fetching dropdown data:', error);
            showMessage(addLeaveRequestMessage, `ไม่สามารถโหลดข้อมูล: ${error.message}`, true);
        }
    }

    function populateEmployeeDropdown(selectElement, employees) {
        selectElement.innerHTML = '<option value="">-- เลือกพนักงาน --</option>';
        employees.forEach(employee => {
            const option = document.createElement('option');
            option.value = employee.id;
            option.textContent = `${employee.first_name} ${employee.last_name}`;
            selectElement.appendChild(option);
        });
    }

    function populateLeaveTypeDropdown(selectElement, leaveTypes) {
        selectElement.innerHTML = '<option value="">-- เลือกประเภทการลา --</option>';
        leaveTypes.forEach(leaveType => {
            const option = document.createElement('option');
            option.value = leaveType.id;
            option.textContent = leaveType.name;
            selectElement.appendChild(option);
        });
    }

    async function fetchLeaveRequests() {
        leaveRequestsTableBody.innerHTML = `<tr><td colspan="8" class="text-center p-4">กำลังโหลด...</td></tr>`;
        try {
            const response = await fetch(`${API_BASE_URL}/leave-requests/`);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const leaveRequests = await response.json();
            renderLeaveRequestsTable(leaveRequests);
        } catch (error) {
            leaveRequestsTableBody.innerHTML = `<tr><td colspan="8" class="text-center p-4 text-red-600">เกิดข้อผิดพลาดในการโหลดข้อมูล</td></tr>`;
            showMessage(leaveRequestsMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
        }
    }

    async function renderLeaveRequestsTable(leaveRequests) {
        leaveRequestsTableBody.innerHTML = '';
        if (leaveRequests.length === 0) {
            leaveRequestsTableBody.innerHTML = `<tr><td colspan="8" class="text-center p-4">ยังไม่มีข้อมูลคำขอลา</td></tr>`;
            return;
        }

        const employeeMap = new Map();
        const leaveTypeMap = new Map();
        try {
            const [empResponse, leaveTypeResponse] = await Promise.all([
                fetch(`${DATA_MGMT_API_BASE_URL}/employees/`),
                fetch(`${API_BASE_URL}/leave-types/`)
            ]);
            const employees = await empResponse.json();
            const leaveTypes = await leaveTypeResponse.json();
            employees.forEach(emp => employeeMap.set(emp.id, `${emp.first_name} ${emp.last_name}`));
            leaveTypes.forEach(lt => leaveTypeMap.set(lt.id, lt.name));
        } catch (error) {
            showMessage(leaveRequestsMessage, 'ไม่สามารถโหลดชื่อพนักงาน/ประเภทการลาได้', true);
        }

        leaveRequests.forEach(request => {
            const row = leaveRequestsTableBody.insertRow();
            row.className = 'hover:bg-gray-50';
            
            const employeeName = employeeMap.get(request.employee_id) || `ID: ${request.employee_id}`;
            const leaveTypeName = leaveTypeMap.get(request.leave_type_id) || `ID: ${request.leave_type_id}`;
            const numDaysDisplay = request.num_days ? request.num_days.toFixed(2) : 'N/A';
            
            let statusClass = '';
            if (request.status === 'Approved') statusClass = 'bg-green-100 text-green-800';
            else if (request.status === 'Rejected' || request.status === 'Cancelled') statusClass = 'bg-red-100 text-red-800';
            else statusClass = 'bg-yellow-100 text-yellow-800';

            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${request.id}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${employeeName}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${leaveTypeName}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${new Date(request.start_date).toLocaleString('th-TH')} ถึง ${new Date(request.end_date).toLocaleString('th-TH')}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${numDaysDisplay}</td>
                <td class="px-6 py-4 whitespace-normal text-sm text-gray-700 max-w-xs overflow-hidden text-ellipsis">${request.reason || '-'}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700"><span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${statusClass}">${request.status}</span></td>
                <td class="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                    <button data-id="${request.id}" class="edit-btn bg-yellow-500 hover:bg-yellow-600 text-white py-1 px-3 rounded-md mr-2">แก้ไข</button>
                    <button data-id="${request.id}" class="delete-btn bg-red-600 hover:bg-red-700 text-white py-1 px-3 rounded-md">ลบ</button>
                </td>
            `;
        });
        attachTableButtonListeners();
    }

    function attachTableButtonListeners() {
        document.querySelectorAll('.edit-btn').forEach(button => {
            button.addEventListener('click', async (event) => {
                const id = event.target.dataset.id;
                try {
                    const response = await fetch(`${API_BASE_URL}/leave-requests/${id}`);
                    if (!response.ok) throw new Error('Failed to fetch leave request details');
                    const request = await response.json();
                    
                    editLeaveRequestIdInput.value = request.id;
                    editEmployeeIdSelect.value = request.employee_id;
                    editLeaveTypeIdSelect.value = request.leave_type_id;
                    editStartDateInput.value = formatDateTimeLocal(request.start_date);
                    editEndDateInput.value = formatDateTimeLocal(request.end_date);
                    editReasonInput.value = request.reason || '';
                    editStatusSelect.value = request.status;

                    editLeaveRequestModal.style.display = 'flex';
                } catch (error) {
                    showMessage(leaveRequestsMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
                }
            });
        });

        document.querySelectorAll('.delete-btn').forEach(button => {
            button.addEventListener('click', async (event) => {
                const id = event.target.dataset.id;
                if (confirm(`คุณแน่ใจหรือไม่ที่ต้องการลบคำขอลา ID: ${id} นี้?`)) {
                    try {
                        const response = await fetch(`${API_BASE_URL}/leave-requests/${id}`, { method: 'DELETE' });
                        if (!response.ok) {
                            const errorData = await response.json();
                            throw new Error(errorData.detail || 'เกิดข้อผิดพลาดในการลบ');
                        }
                        showMessage(leaveRequestsMessage, 'ลบคำขอลาเรียบร้อยแล้ว');
                        fetchLeaveRequests();
                    } catch (error) {
                        showMessage(leaveRequestsMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
                    }
                }
            });
        });
    }

    addLeaveRequestForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const data = {
            employee_id: parseInt(addEmployeeIdSelect.value),
            leave_type_id: parseInt(addLeaveTypeIdSelect.value),
            start_date: addStartDateInput.value,
            end_date: addEndDateInput.value,
            reason: addReasonInput.value,
        };
        if (!data.employee_id || !data.leave_type_id || !data.start_date || !data.end_date || !data.reason) {
            showMessage(addLeaveRequestMessage, 'กรุณากรอกข้อมูลที่จำเป็นทั้งหมด', true);
            return;
        }
        try {
            const response = await fetch(`${API_BASE_URL}/leave-requests/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'เกิดข้อผิดพลาดในการยื่นคำขอลา');
            }
            const newRequest = await response.json();
            showMessage(addLeaveRequestMessage, `ยื่นคำขอลา ID: ${newRequest.id} เรียบร้อยแล้ว`);
            addLeaveRequestForm.reset();
            fetchLeaveRequests();
        } catch (error) {
            showMessage(addLeaveRequestMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
        }
    });

    editLeaveRequestForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const id = editLeaveRequestIdInput.value;
        const data = {
            employee_id: parseInt(editEmployeeIdSelect.value),
            leave_type_id: parseInt(editLeaveTypeIdSelect.value),
            start_date: editStartDateInput.value,
            end_date: editEndDateInput.value,
            reason: editReasonInput.value,
            status: editStatusSelect.value,
        };
        try {
            const response = await fetch(`${API_BASE_URL}/leave-requests/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'เกิดข้อผิดพลาดในการอัปเดต');
            }
            showMessage(leaveRequestsMessage, `อัปเดตคำขอลา ID: ${id} เรียบร้อยแล้ว`);
            editLeaveRequestModal.style.display = 'none';
            fetchLeaveRequests();
        } catch (error) {
            showMessage(editLeaveRequestMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
        }
    });

    closeEditModalButton.addEventListener('click', () => {
        editLeaveRequestModal.style.display = 'none';
    });

    // --- Initial Page Load ---
    fetchDropdownData();
    fetchLeaveRequests();
});
