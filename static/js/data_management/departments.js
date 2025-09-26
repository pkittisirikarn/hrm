document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = '/api/v1/data-management'; // Base URL สำหรับ API ของ Data Management

    const addDepartmentForm = document.getElementById('addDepartmentForm');
    const departmentNameInput = document.getElementById('departmentName');
    const addDepartmentMessage = document.getElementById('addDepartmentMessage');
    const departmentsTableBody = document.getElementById('departmentsTableBody');
    const departmentsMessage = document.getElementById('departmentsMessage');

    const editDepartmentModal = document.getElementById('editDepartmentModal');
    const closeEditModalButton = document.getElementById('closeEditModal');
    const editDepartmentForm = document.getElementById('editDepartmentForm');
    const editDepartmentIdInput = document.getElementById('editDepartmentId');
    const editDepartmentNameInput = document.getElementById('editDepartmentName');
    const editDepartmentMessage = document.getElementById('editDepartmentMessage');

    // --- ฟังก์ชันสำหรับแสดงข้อความแจ้งเตือน ---
    function showMessage(element, message, isError = false) {
        element.textContent = message;
        element.className = `mt-4 text-sm font-medium ${isError ? 'text-red-600' : 'text-green-600'}`;
        setTimeout(() => {
            element.textContent = '';
            element.className = 'mt-4 text-sm font-medium';
        }, 5000); // ข้อความจะหายไปใน 5 วินาที
    }

    // --- ฟังก์ชันสำหรับดึงข้อมูลแผนกจาก API และแสดงผลในตาราง ---
    async function fetchDepartments() {
        departmentsTableBody.innerHTML = `
            <tr>
                <td colspan="3" class="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500">
                    กำลังโหลดข้อมูล...
                </td>
            </tr>`;
        try {
            const response = await fetch(`${API_BASE_URL}/departments/`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const departments = await response.json();
            renderDepartmentsTable(departments);
        } catch (error) {
            console.error('Error fetching departments:', error);
            departmentsTableBody.innerHTML = `
                <tr>
                    <td colspan="3" class="px-6 py-4 whitespace-nowrap text-center text-sm text-red-600">
                        เกิดข้อผิดพลาดในการโหลดข้อมูลแผนก: ${error.message}
                    </td>
                </tr>`;
            showMessage(departmentsMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
        }
    }

    // --- ฟังก์ชันสำหรับ Render ตารางแผนก ---
    function renderDepartmentsTable(departments) {
        departmentsTableBody.innerHTML = ''; // เคลียร์ข้อมูลเก่า
        if (departments.length === 0) {
            departmentsTableBody.innerHTML = `
                <tr>
                    <td colspan="3" class="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500">
                        ยังไม่มีข้อมูลแผนก
                    </td>
                </tr>`;
            return;
        }

        departments.forEach(department => {
            const row = departmentsTableBody.insertRow();
            row.className = 'hover:bg-gray-50';
            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${department.id}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${department.name}</td>
                <td class="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                    <button data-id="${department.id}" data-name="${department.name}" class="edit-btn bg-yellow-500 hover:bg-yellow-600 text-white py-1 px-3 rounded-md mr-2 transition duration-150">แก้ไข</button>
                    <button data-id="${department.id}" class="delete-btn bg-red-600 hover:bg-red-700 text-white py-1 px-3 rounded-md transition duration-150">ลบ</button>
                </td>
            `;
        });

        // เพิ่ม Event Listeners สำหรับปุ่มแก้ไขและลบ
        document.querySelectorAll('.edit-btn').forEach(button => {
            button.addEventListener('click', (event) => {
                const id = event.target.dataset.id;
                const name = event.target.dataset.name;
                editDepartmentIdInput.value = id;
                editDepartmentNameInput.value = name;
                editDepartmentModal.classList.remove('hidden'); // แสดง Modal
            });
        });

        document.querySelectorAll('.delete-btn').forEach(button => {
            button.addEventListener('click', async (event) => {
                const id = event.target.dataset.id;
                if (confirm(`คุณแน่ใจหรือไม่ที่ต้องการลบแผนก ID: ${id} นี้?`)) {
                    try {
                        const response = await fetch(`${API_BASE_URL}/departments/${id}`, {
                            method: 'DELETE',
                        });
                        if (!response.ok) {
                            const errorData = await response.json();
                            throw new Error(errorData.detail || 'เกิดข้อผิดพลาดในการลบแผนก');
                        }
                        showMessage(departmentsMessage, 'ลบแผนกเรียบร้อยแล้ว');
                        fetchDepartments(); // โหลดข้อมูลใหม่
                    } catch (error) {
                        console.error('Error deleting department:', error);
                        showMessage(departmentsMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
                    }
                }
            });
        });
    }

    // --- Event Listener สำหรับ Form เพิ่มแผนก ---
    addDepartmentForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const departmentName = departmentNameInput.value.trim();
        if (!departmentName) {
            showMessage(addDepartmentMessage, 'กรุณากรอกชื่อแผนก', true);
            return;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/departments/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ name: departmentName }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'เกิดข้อผิดพลาดในการเพิ่มแผนก');
            }

            const newDepartment = await response.json();
            showMessage(addDepartmentMessage, `เพิ่มแผนก "${newDepartment.name}" (ID: ${newDepartment.id}) เรียบร้อยแล้ว`);
            departmentNameInput.value = ''; // เคลียร์ฟอร์ม
            fetchDepartments(); // โหลดข้อมูลใหม่
        } catch (error) {
            console.error('Error adding department:', error);
            showMessage(addDepartmentMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
        }
    });

    // --- Event Listener สำหรับ Form แก้ไขแผนก ---
    editDepartmentForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const departmentId = editDepartmentIdInput.value;
        const newDepartmentName = editDepartmentNameInput.value.trim();

        if (!newDepartmentName) {
            showMessage(editDepartmentMessage, 'กรุณากรอกชื่อแผนก', true);
            return;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/departments/${departmentId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ name: newDepartmentName }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'เกิดข้อผิดพลาดในการอัปเดตแผนก');
            }

            const updatedDepartment = await response.json();
            showMessage(departmentsMessage, `อัปเดตแผนก ID: ${updatedDepartment.id} เป็น "${updatedDepartment.name}" เรียบร้อยแล้ว`);
            editDepartmentModal.classList.add('hidden'); // ซ่อน Modal
            fetchDepartments(); // โหลดข้อมูลใหม่
        } catch (error) {
            console.error('Error updating department:', error);
            showMessage(editDepartmentMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
        }
    });

    // --- Event Listener สำหรับปิด Modal แก้ไข ---
    closeEditModalButton.addEventListener('click', () => {
        editDepartmentModal.classList.add('hidden');
        editDepartmentMessage.textContent = ''; // เคลียร์ข้อความ
    });

    // โหลดข้อมูลแผนกเมื่อหน้าเว็บโหลดเสร็จ
    fetchDepartments();
});
