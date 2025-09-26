document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = '/api/v1/time-tracking';

    const searchForm = document.getElementById('searchForm');
    const searchEmployeeIdInput = document.getElementById('searchEmployeeId');
    const searchDateInput = document.getElementById('searchDate');
    const clearSearchBtn = document.getElementById('clearSearchBtn');
    const reportTableBody = document.getElementById('reportTableBody');
    const reportMessage = document.getElementById('reportMessage');

    function showMessage(message, isError = false) {
        reportMessage.textContent = message;
        reportMessage.className = `mt-4 text-sm font-medium ${isError ? 'text-red-600' : 'text-green-600'}`;
    }

    async function fetchReportData() {
        reportTableBody.innerHTML = `<tr><td colspan="6" class="text-center p-4">กำลังโหลดข้อมูล...</td></tr>`;
        
        const employeeId = searchEmployeeIdInput.value.trim();
        const entryDate = searchDateInput.value;

        const params = new URLSearchParams();
        if (employeeId) {
            params.append('employee_id_number', employeeId);
        }
        if (entryDate) {
            params.append('entry_date', entryDate);
        }

        try {
            const response = await fetch(`${API_BASE_URL}/report/data?${params.toString()}`);
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'เกิดข้อผิดพลาดในการโหลดข้อมูล');
            }
            const data = await response.json();
            renderTable(data);
        } catch (error) {
            console.error('Error fetching report data:', error);
            reportTableBody.innerHTML = `<tr><td colspan="6" class="text-center p-4 text-red-600">${error.message}</td></tr>`;
        }
    }

    function renderTable(entries) {
        reportTableBody.innerHTML = '';
        if (entries.length === 0) {
            reportTableBody.innerHTML = `<tr><td colspan="6" class="text-center p-4">ไม่พบข้อมูล</td></tr>`;
            return;
        }

        entries.forEach(entry => {
            const row = reportTableBody.insertRow();
            const employee = entry.employee;

            const checkIn = new Date(entry.check_in_time).toLocaleString('th-TH');
            const checkOut = entry.check_out_time ? new Date(entry.check_out_time).toLocaleString('th-TH') : '-';

            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${entry.id}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${employee.employee_id_number}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${employee.first_name} ${employee.last_name}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${checkIn}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${checkOut}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${entry.status}</td>
            `;
        });
    }

    searchForm.addEventListener('submit', (e) => {
        e.preventDefault();
        fetchReportData();
    });

    clearSearchBtn.addEventListener('click', () => {
        searchForm.reset();
        fetchReportData();
    });

    // Initial data load
    fetchReportData();
});
