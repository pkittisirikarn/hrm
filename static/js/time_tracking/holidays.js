document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = '/api/v1/time-tracking';

    // Elements for Adding Holiday
    const addHolidayForm = document.getElementById('addHolidayForm');
    const addHolidayMessage = document.getElementById('addHolidayMessage');
    const addNameInput = document.getElementById('addName');
    const addHolidayDateInput = document.getElementById('addHolidayDate');
    const addIsRecurringCheckbox = document.getElementById('addIsRecurring');
    const addIsActiveCheckbox = document.getElementById('addIsActive');

    // Elements for Listing Holidays
    const holidaysTableBody = document.getElementById('holidaysTableBody');
    const holidaysMessage = document.getElementById('holidaysMessage');

    // Elements for Editing Holiday Modal
    const editHolidayModal = document.getElementById('editHolidayModal');
    const closeEditModalButton = document.getElementById('closeEditModalButton');
    const editHolidayForm = document.getElementById('editHolidayForm');
    const editHolidayMessage = document.getElementById('editHolidayMessage');

    // Edit Form Fields
    const editHolidayIdInput = document.getElementById('editHolidayId');
    const editNameInput = document.getElementById('editName');
    const editHolidayDateInput = document.getElementById('editHolidayDate');
    const editIsRecurringCheckbox = document.getElementById('editIsRecurring');
    const editIsActiveCheckbox = document.getElementById('editIsActive');

    // --- Generic Message Display Function ---
    function showMessage(element, message, isError = false) {
        element.textContent = message;
        element.className = `mt-4 text-sm font-medium ${isError ? 'text-red-600' : 'text-green-600'}`;
        setTimeout(() => {
            element.textContent = '';
            element.className = 'mt-4 text-sm font-medium';
        }, 5000);
    }

    // --- Fetch Holidays from API and Render Table ---
    async function fetchHolidays() {
        holidaysTableBody.innerHTML = `
            <tr>
                <td colspan="6" class="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500">
                    กำลังโหลดข้อมูล...
                </td>
            </tr>`;
        try {
            const response = await fetch(`${API_BASE_URL}/holidays/`);
            if (!response.ok) {
                const errorData = await response.json();
                console.error('API Error (fetch holidays):', errorData);
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            const holidays = await response.json();
            renderHolidaysTable(holidays);
        } catch (error) {
            console.error('Error fetching holidays:', error);
            holidaysTableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="px-6 py-4 whitespace-nowrap text-center text-sm text-red-600">
                        เกิดข้อผิดพลาดในการโหลดวันหยุด: ${error.message}
                    </td>
                </tr>`;
            showMessage(holidaysMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
        }
    }

    // --- Render Holidays Table ---
    function renderHolidaysTable(holidays) {
        holidaysTableBody.innerHTML = '';
        if (holidays.length === 0) {
            holidaysTableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500">
                        ยังไม่มีข้อมูลวันหยุด
                    </td>
                </tr>`;
            return;
        }

        holidays.sort((a, b) => new Date(a.holiday_date) - new Date(b.holiday_date)); // Sort by date

        holidays.forEach(holiday => {
            const row = holidaysTableBody.insertRow();
            row.className = 'hover:bg-gray-50';
            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${holiday.id}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${holiday.name}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${holiday.holiday_date}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${holiday.is_recurring ? 'ใช่' : 'ไม่ใช่'}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${holiday.is_active ? 'ใช้งาน' : 'ไม่ใช้งาน'}</td>
                <td class="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                    <button data-id="${holiday.id}" class="edit-btn bg-yellow-500 hover:bg-yellow-600 text-white py-1 px-3 rounded-md mr-2 transition duration-150">แก้ไข</button>
                    <button data-id="${holiday.id}" class="delete-btn bg-red-600 hover:bg-red-700 text-white py-1 px-3 rounded-md transition duration-150">ลบ</button>
                </td>
            `;
        });

        // Add Event Listeners for Edit and Delete buttons
        document.querySelectorAll('.edit-btn').forEach(button => {
            button.addEventListener('click', async (event) => {
                const id = event.target.dataset.id;
                try {
                    const response = await fetch(`${API_BASE_URL}/holidays/${id}`);
                    if (!response.ok) {
                        const errorData = await response.json();
                        console.error('API Error (fetch holiday for edit):', errorData);
                        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
                    }
                    const holiday = await response.json();
                    
                    editHolidayIdInput.value = holiday.id;
                    editNameInput.value = holiday.name;
                    editHolidayDateInput.value = holiday.holiday_date; // Date input value expects YYYY-MM-DD
                    editIsRecurringCheckbox.checked = holiday.is_recurring;
                    editIsActiveCheckbox.checked = holiday.is_active;

                    editHolidayModal.style.display = 'flex'; // Show Modal
                } catch (error) {
                    console.error('Error fetching holiday for edit:', error);
                    showMessage(holidaysMessage, `เกิดข้อผิดพลาดในการโหลดวันหยุดเพื่อแก้ไข: ${error.message}`, true);
                }
            });
        });

        document.querySelectorAll('.delete-btn').forEach(button => {
            button.addEventListener('click', async (event) => {
                const id = event.target.dataset.id;
                if (confirm(`คุณแน่ใจหรือไม่ที่ต้องการลบวันหยุด ID: ${id} นี้?`)) {
                    try {
                        const response = await fetch(`${API_BASE_URL}/holidays/${id}`, {
                            method: 'DELETE',
                        });
                        if (!response.ok) {
                            const errorData = await response.json();
                            console.error('API Error (delete holiday):', errorData);
                            throw new Error(errorData.detail || 'เกิดข้อผิดพลาดในการลบวันหยุด');
                        }
                        showMessage(holidaysMessage, 'ลบวันหยุดเรียบร้อยแล้ว');
                        fetchHolidays(); // Reload data
                    } catch (error) {
                        console.error('Error deleting holiday:', error);
                        showMessage(holidaysMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
                    }
                }
            });
        });
    }

    // --- Event Listener for Add Holiday Form ---
    addHolidayForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        
        const name = addNameInput.value.trim();
        const holidayDate = addHolidayDateInput.value;
        const isRecurring = addIsRecurringCheckbox.checked;
        const isActive = addIsActiveCheckbox.checked;

        if (!name || !holidayDate) {
            showMessage(addHolidayMessage, 'กรุณากรอกชื่อและวันที่สำหรับวันหยุด', true);
            return;
        }

        try {
            const data = {
                name: name,
                holiday_date: holidayDate,
                is_recurring: isRecurring,
                is_active: isActive
            };

            const response = await fetch(`${API_BASE_URL}/holidays/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.error('API Error (add holiday):', errorData);
                if (Array.isArray(errorData.detail) && errorData.detail.length > 0) {
                    const validationErrors = errorData.detail.map(err => `${err.loc.join('.')} - ${err.msg}`).join('\n');
                    throw new Error(`ข้อมูลไม่ถูกต้อง:\n${validationErrors}`);
                }
                throw new Error(errorData.detail || 'เกิดข้อผิดพลาดในการเพิ่มวันหยุด');
            }

            const newHoliday = await response.json();
            showMessage(addHolidayMessage, `เพิ่มวันหยุด "${newHoliday.name}" (ID: ${newHoliday.id}) เรียบร้อยแล้ว`);
            addHolidayForm.reset(); // Clear form
            fetchHolidays(); // Load new data
        } catch (error) {
            console.error('Final caught error adding holiday:', error);
            showMessage(addHolidayMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
        }
    });

    // --- Event Listener for Edit Holiday Form ---
    editHolidayForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const holidayId = editHolidayIdInput.value;
        
        const name = editNameInput.value.trim();
        const holidayDate = editHolidayDateInput.value;
        const isRecurring = editIsRecurringCheckbox.checked;
        const isActive = editIsActiveCheckbox.checked;

        if (!name || !holidayDate) {
            showMessage(editHolidayMessage, 'กรุณากรอกชื่อและวันที่สำหรับวันหยุด', true);
            return;
        }

        try {
            const data = {
                name: name,
                holiday_date: holidayDate,
                is_recurring: isRecurring,
                is_active: isActive
            };
            
            // Remove null or empty string fields from data object before sending for partial update
            Object.keys(data).forEach(key => {
                if (data[key] === null || data[key] === '') {
                    delete data[key];
                }
            });

            const response = await fetch(`${API_BASE_URL}/holidays/${holidayId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.error('API Error (edit holiday):', errorData);
                if (Array.isArray(errorData.detail) && errorData.detail.length > 0) {
                    const validationErrors = errorData.detail.map(err => `${err.loc.join('.')} - ${err.msg}`).join('\n');
                    throw new Error(`ข้อมูลไม่ถูกต้อง:\n${validationErrors}`);
                }
                throw new Error(errorData.detail || 'เกิดข้อผิดพลาดในการอัปเดตวันหยุด');
            }

            const updatedHoliday = await response.json();
            showMessage(holidaysMessage, `อัปเดตวันหยุด "${updatedHoliday.name}" (ID: ${updatedHoliday.id}) เรียบร้อยแล้ว`);
            editHolidayModal.style.display = 'none'; // Hide Modal
            fetchHolidays(); // Load new data
        } catch (error) {
            console.error('Final caught error updating holiday:', error);
            showMessage(editHolidayMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
        }
    });

    // --- Event Listener for closing Edit Modal ---
    closeEditModalButton.addEventListener('click', () => {
        editHolidayModal.style.display = 'none';
        editHolidayMessage.textContent = '';
    });

    // Initial load
    fetchHolidays();
});
