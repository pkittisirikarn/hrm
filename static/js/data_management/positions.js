document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = '/api/v1/data-management'; // Base URL สำหรับ API ของ Data Management

    const addPositionForm = document.getElementById('addPositionForm');
    const positionNameInput = document.getElementById('positionName');
    const addPositionMessage = document.getElementById('addPositionMessage');
    const positionsTableBody = document.getElementById('positionsTableBody');
    const positionsMessage = document.getElementById('positionsMessage');

    const editPositionModal = document.getElementById('editPositionModal');
    const closeEditModalButton = document.getElementById('closeEditModal');
    const editPositionForm = document.getElementById('editPositionForm');
    const editPositionIdInput = document.getElementById('editPositionId');
    const editPositionNameInput = document.getElementById('editPositionName');
    const editPositionMessage = document.getElementById('editPositionMessage');

    // --- ฟังก์ชันสำหรับแสดงข้อความแจ้งเตือน ---
    function showMessage(element, message, isError = false) {
        element.textContent = message;
        element.className = `mt-4 text-sm font-medium ${isError ? 'text-red-600' : 'text-green-600'}`;
        setTimeout(() => {
            element.textContent = '';
            element.className = 'mt-4 text-sm font-medium';
        }, 5000); // ข้อความจะหายไปใน 5 วินาที
    }

    // --- ฟังก์ชันสำหรับดึงข้อมูลตำแหน่งจาก API และแสดงผลในตาราง ---
    async function fetchPositions() {
        positionsTableBody.innerHTML = `
            <tr>
                <td colspan="3" class="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500">
                    กำลังโหลดข้อมูล...
                </td>
            </tr>`;
        try {
            const response = await fetch(`${API_BASE_URL}/positions/`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const positions = await response.json();
            renderPositionsTable(positions);
        } catch (error) {
            console.error('Error fetching positions:', error);
            positionsTableBody.innerHTML = `
                <tr>
                    <td colspan="3" class="px-6 py-4 whitespace-nowrap text-center text-sm text-red-600">
                        เกิดข้อผิดพลาดในการโหลดข้อมูลตำแหน่ง: ${error.message}
                    </td>
                </tr>`;
            showMessage(positionsMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
        }
    }

    // --- ฟังก์ชันสำหรับ Render ตารางตำแหน่ง ---
    function renderPositionsTable(positions) {
        positionsTableBody.innerHTML = ''; // เคลียร์ข้อมูลเก่า
        if (positions.length === 0) {
            positionsTableBody.innerHTML = `
                <tr>
                    <td colspan="3" class="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500">
                        ยังไม่มีข้อมูลตำแหน่ง
                    </td>
                </tr>`;
            return;
        }

        positions.forEach(position => {
            const row = positionsTableBody.insertRow();
            row.className = 'hover:bg-gray-50';
            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${position.id}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${position.name}</td>
                <td class="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                    <button data-id="${position.id}" data-name="${position.name}" class="edit-btn bg-yellow-500 hover:bg-yellow-600 text-white py-1 px-3 rounded-md mr-2 transition duration-150">แก้ไข</button>
                    <button data-id="${position.id}" class="delete-btn bg-red-600 hover:bg-red-700 text-white py-1 px-3 rounded-md transition duration-150">ลบ</button>
                </td>
            `;
        });

        // เพิ่ม Event Listeners สำหรับปุ่มแก้ไขและลบ
        document.querySelectorAll('.edit-btn').forEach(button => {
            button.addEventListener('click', (event) => {
                const id = event.target.dataset.id;
                const name = event.target.dataset.name;
                editPositionIdInput.value = id;
                editPositionNameInput.value = name;
                editPositionModal.classList.remove('hidden'); // แสดง Modal
            });
        });

        document.querySelectorAll('.delete-btn').forEach(button => {
            button.addEventListener('click', async (event) => {
                const id = event.target.dataset.id;
                if (confirm(`คุณแน่ใจหรือไม่ที่ต้องการลบตำแหน่ง ID: ${id} นี้?`)) {
                    try {
                        const response = await fetch(`${API_BASE_URL}/positions/${id}`, {
                            method: 'DELETE',
                        });
                        if (!response.ok) {
                            const errorData = await response.json();
                            throw new Error(errorData.detail || 'เกิดข้อผิดพลาดในการลบตำแหน่ง');
                        }
                        showMessage(positionsMessage, 'ลบตำแหน่งเรียบร้อยแล้ว');
                        fetchPositions(); // โหลดข้อมูลใหม่
                    } catch (error) {
                        console.error('Error deleting position:', error);
                        showMessage(positionsMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
                    }
                }
            });
        });
    }

    // --- Event Listener สำหรับ Form เพิ่มตำแหน่ง ---
    addPositionForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const positionName = positionNameInput.value.trim();
        if (!positionName) {
            showMessage(addPositionMessage, 'กรุณากรอกชื่อตำแหน่ง', true);
            return;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/positions/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ name: positionName }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'เกิดข้อผิดพลาดในการเพิ่มตำแหน่ง');
            }

            const newPosition = await response.json();
            showMessage(addPositionMessage, `เพิ่มตำแหน่ง "${newPosition.name}" (ID: ${newPosition.id}) เรียบร้อยแล้ว`);
            positionNameInput.value = ''; // เคลียร์ฟอร์ม
            fetchPositions(); // โหลดข้อมูลใหม่
        } catch (error) {
            console.error('Error adding position:', error);
            showMessage(addPositionMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
        }
    });

    // --- Event Listener สำหรับ Form แก้ไขตำแหน่ง ---
    editPositionForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const positionId = editPositionIdInput.value;
        const newPositionName = editPositionNameInput.value.trim();

        if (!newPositionName) {
            showMessage(editPositionMessage, 'กรุณากรอกชื่อตำแหน่ง', true);
            return;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/positions/${positionId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ name: newPositionName }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'เกิดข้อผิดพลาดในการอัปเดตตำแหน่ง');
            }

            const updatedPosition = await response.json();
            showMessage(positionsMessage, `อัปเดตตำแหน่ง ID: ${updatedPosition.id} เป็น "${updatedPosition.name}" เรียบร้อยแล้ว`);
            editPositionModal.classList.add('hidden'); // ซ่อน Modal
            fetchPositions(); // โหลดข้อมูลใหม่
        } catch (error) {
            console.error('Error updating position:', error);
            showMessage(editPositionMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
        }
    });

    // --- Event Listener สำหรับปิด Modal แก้ไข ---
    closeEditModalButton.addEventListener('click', () => {
        editPositionModal.classList.add('hidden');
        editPositionMessage.textContent = ''; // เคลียร์ข้อความ
    });

    // โหลดข้อมูลตำแหน่งเมื่อหน้าเว็บโหลดเสร็จ
    fetchPositions();
});
