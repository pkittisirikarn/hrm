document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = '/api/v1/data-management';

    // Elements for Adding Employee
    const addEmployeeForm = document.getElementById('addEmployeeForm');
    const addEmployeeMessage = document.getElementById('addEmployeeMessage');
    const addEmployeeIdNumberInput = document.getElementById('addEmployeeIdNumber');
    const addFirstNameInput = document.getElementById('addFirstName');
    const addLastNameInput = document.getElementById('addLastName');
    const addDateOfBirthInput = document.getElementById('addDateOfBirth');
    const addAddressInput = document.getElementById('addAddress');
    const addIdCardNumberInput = document.getElementById('addIdCardNumber'); // optional
    const addEmailInput = document.getElementById('addEmail');               // ✅ NEW
    const addPhoneNumberInput = document.getElementById('addPhoneNumber');   // ✅ NEW
    const addProfilePictureFileInput = document.getElementById('addProfilePictureFile');
    const addProfilePicturePreview = document.getElementById('addProfilePicturePreview');
    const addApplicationDocumentsFilesInput = document.getElementById('addApplicationDocumentsFiles');
    const addApplicationDocumentsPreview = document.getElementById('addApplicationDocumentsPreview');
    const addBankAccountNumberInput = document.getElementById('addBankAccountNumber');
    const addBankNameInput = document.getElementById('addBankName');
    const addHireDateInput = document.getElementById('addHireDate');
    const addTerminationDateInput = document.getElementById('addTerminationDate');
    const addEmployeeStatusSelect = document.getElementById('addEmployeeStatus');
    const addDepartmentIdSelect = document.getElementById('addDepartmentId');
    const addPositionIdSelect = document.getElementById('addPositionId');

    // Elements for Listing Employees
    const employeesTableBody = document.getElementById('employeesTableBody');
    const employeesMessage = document.getElementById('employeesMessage');

    // Elements for Editing Employee Modal
    const editEmployeeModal = document.getElementById('editEmployeeModal');
    const closeEditModalButton = document.getElementById('closeEditModalButton');
    const editEmployeeForm = document.getElementById('editEmployeeForm');
    const editEmployeeMessage = document.getElementById('editEmployeeMessage');

    // Edit Form Fields
    const editEmployeeIdInput = document.getElementById('editEmployeeId');
    const editEmployeeIdNumberInput = document.getElementById('editEmployeeIdNumber');
    const editFirstNameInput = document.getElementById('editFirstName');
    const editLastNameInput = document.getElementById('editLastName');
    const editDateOfBirthInput = document.getElementById('editDateOfBirth');
    const editAddressInput = document.getElementById('editAddress');
    const editIdCardNumberInput = document.getElementById('editIdCardNumber'); // optional
    const editEmailInput = document.getElementById('editEmail');               // ✅ NEW
    const editPhoneNumberInput = document.getElementById('editPhoneNumber');   // ✅ NEW
    const editProfilePictureFileInput = document.getElementById('editProfilePictureFile');
    const editProfilePicturePreview = document.getElementById('editProfilePicturePreview');
    const clearEditProfilePictureButton = document.getElementById('clearEditProfilePicture');
    const editApplicationDocumentsFilesInput = document.getElementById('editApplicationDocumentsFiles');
    const editApplicationDocumentsPreview = document.getElementById('editApplicationDocumentsPreview');
    const clearEditApplicationDocumentsButton = document.getElementById('clearEditApplicationDocuments');
    const editBankAccountNumberInput = document.getElementById('editBankAccountNumber');
    const editBankNameInput = document.getElementById('editBankName');
    const editHireDateInput = document.getElementById('editHireDate');
    const editTerminationDateInput = document.getElementById('editTerminationDate');
    const editEmployeeStatusSelect = document.getElementById('editEmployeeStatus');
    const editDepartmentIdSelect = document.getElementById('editDepartmentId');
    const editPositionIdSelect = document.getElementById('editPositionId');

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

    // --- Helper for date input formatting (YYYY-MM-DD) ---
    function formatDate(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    // --- Preview function for single image file ---
    function previewImage(inputElement, imgElement) {
        if (inputElement.files && inputElement.files[0]) {
            const reader = new FileReader();
            reader.onload = (e) => {
                imgElement.src = e.target.result;
                imgElement.style.display = 'block';
            };
            reader.readAsDataURL(inputElement.files[0]);
        } else {
            imgElement.src = '#';
            imgElement.style.display = 'none';
        }
    }

    // --- Preview function for multiple PDF files ---
    function previewPdfFiles(inputElement, previewContainer) {
        previewContainer.innerHTML = '';
        if (inputElement.files && inputElement.files.length > 0) {
            Array.from(inputElement.files).forEach(file => {
                const fileItem = document.createElement('div');
                fileItem.className = 'file-list-item';
                fileItem.innerHTML = `
                    <svg class="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6a2 2 0 01.586 1.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 0h4l4 4v10H6V4z" clip-rule="evenodd"></path></svg>
                    <span>${file.name}</span>
                `;
                previewContainer.appendChild(fileItem);
            });
        }
    }

    // --- Fetch dropdowns ---
    async function fetchDepartmentsForDropdown() {
        try {
            const response = await fetch(`${API_BASE_URL}/departments/`);
            if (!response.ok) throw new Error(await formatApiErrorDetail(response));
            const departments = await response.json();

            addDepartmentIdSelect.innerHTML = '<option value="">เลือกแผนก</option>';
            editDepartmentIdSelect.innerHTML = '';

            departments.forEach(dept => {
                const optionAdd = document.createElement('option');
                optionAdd.value = dept.id;
                optionAdd.textContent = dept.name;
                addDepartmentIdSelect.appendChild(optionAdd);

                const optionEdit = document.createElement('option');
                optionEdit.value = dept.id;
                optionEdit.textContent = dept.name;
                editDepartmentIdSelect.appendChild(optionEdit);
            });
        } catch (error) {
            console.error('Error fetching departments:', error);
            showMessage(addEmployeeMessage, `เกิดข้อผิดพลาดในการโหลดข้อมูลแผนก: ${error.message}`, true);
        }
    }

    async function fetchPositionsForDropdown() {
        try {
            const response = await fetch(`${API_BASE_URL}/positions/`);
            if (!response.ok) throw new Error(await formatApiErrorDetail(response));
            const positions = await response.json();

            addPositionIdSelect.innerHTML = '<option value="">เลือกตำแหน่ง</option>';
            editPositionIdSelect.innerHTML = '';

            positions.forEach(pos => {
                const optionAdd = document.createElement('option');
                optionAdd.value = pos.id;
                optionAdd.textContent = pos.name;
                addPositionIdSelect.appendChild(optionAdd);

                const optionEdit = document.createElement('option');
                optionEdit.value = pos.id;
                optionEdit.textContent = pos.name;
                editPositionIdSelect.appendChild(optionEdit);
            });
        } catch (error) {
            console.error('Error fetching positions:', error);
            showMessage(addEmployeeMessage, `เกิดข้อผิดพลาดในการโหลดข้อมูลตำแหน่ง: ${error.message}`, true);
        }
    }

    // --- Fetch Employees and Render Table ---
    async function fetchEmployees() {
        employeesTableBody.innerHTML = `
            <tr>
                <td colspan="12" class="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500">
                    กำลังโหลดข้อมูล...
                </td>
            </tr>`;
        try {
            const response = await fetch(`${API_BASE_URL}/employees/`);
            if (!response.ok) throw new Error(await formatApiErrorDetail(response));
            const employees = await response.json();
            renderEmployeesTable(employees);
        } catch (error) {
            console.error('Error fetching employees:', error);
            employeesTableBody.innerHTML = `
                <tr>
                    <td colspan="12" class="px-6 py-4 whitespace-nowrap text-center text-sm text-red-600">
                        เกิดข้อผิดพลาดในการโหลดพนักงาน: ${error.message}
                    </td>
                </tr>`;
            showMessage(employeesMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
        }
    }

    // --- Render Employees Table ---
    function renderEmployeesTable(employees) {
        employeesTableBody.innerHTML = '';
        if (employees.length === 0) {
            employeesTableBody.innerHTML = `
                <tr>
                    <td colspan="12" class="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500">
                        ยังไม่มีข้อมูลพนักงาน
                    </td>
                </tr>`;
            return;
        }

        employees.forEach(employee => {
            const row = employeesTableBody.insertRow();
            row.className = 'hover:bg-gray-50';

            const profilePictureHtml = employee.profile_picture_path
                ? `<img src="${employee.profile_picture_path}" alt="Profile" class="profile-img-preview mx-auto">`
                : `<span class="text-gray-500 text-xs">ไม่มีรูป</span>`;

            let documentsHtml = '<span class="text-gray-500 text-xs">ไม่มีเอกสาร</span>';
            if (employee.application_documents_paths) {
                try {
                    const docs = JSON.parse(employee.application_documents_paths);
                    if (Array.isArray(docs) && docs.length > 0) {
                        documentsHtml = docs.map(docPath => {
                            const filename = docPath.split('/').pop();
                            return `<a href="${docPath}" target="_blank" class="text-blue-600 hover:underline block text-xs truncate" title="${filename}">${filename}</a>`;
                        }).join('');
                    }
                } catch (e) {
                    console.error("Failed to parse application_documents_paths:", e);
                    documentsHtml = `<span class="text-red-500 text-xs">ข้อผิดพลาด JSON</span>`;
                }
            }

            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${employee.id}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${employee.employee_id_number}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${employee.first_name} ${employee.last_name}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${employee.id_card_number || '-'}</td>
                <!-- ✅ New columns -->
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${employee.email || '-'}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${employee.phone_number || '-'}</td>
                <td class="px-6 py-4 text-center">
                    ${profilePictureHtml}
                </td>
                <td class="px-6 py-4 text-sm text-gray-700">
                    ${documentsHtml}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${employee.department.name}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${employee.position.name}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${translateEmployeeStatus(employee.employee_status)}</td>
                <td class="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                    <button data-id="${employee.id}" class="edit-btn bg-yellow-500 hover:bg-yellow-600 text-white py-1 px-3 rounded-md mr-2 transition duration-150">แก้ไข</button>
                    <button data-id="${employee.id}" class="delete-btn bg-red-600 hover:bg-red-700 text-white py-1 px-3 rounded-md transition duration-150">ลบ</button>
                </td>
            `;
        });

        // Edit buttons
        document.querySelectorAll('.edit-btn').forEach(button => {
            button.addEventListener('click', async (event) => {
                const id = event.target.dataset.id;
                try {
                    const response = await fetch(`${API_BASE_URL}/employees/${id}`);
                    if (!response.ok) throw new Error(await formatApiErrorDetail(response));
                    const employee = await response.json();

                    editEmployeeIdInput.value = employee.id;
                    editEmployeeIdNumberInput.value = employee.employee_id_number;
                    editFirstNameInput.value = employee.first_name;
                    editLastNameInput.value = employee.last_name;
                    editDateOfBirthInput.value = formatDate(employee.date_of_birth);
                    editAddressInput.value = employee.address;
                    editIdCardNumberInput.value = employee.id_card_number || '';

                    // ✅ New fields
                    editEmailInput.value = employee.email || '';
                    editPhoneNumberInput.value = employee.phone_number || '';

                    // Profile picture preview
                    if (employee.profile_picture_path) {
                        editProfilePicturePreview.src = employee.profile_picture_path;
                        editProfilePicturePreview.style.display = 'block';
                    } else {
                        editProfilePicturePreview.src = '#';
                        editProfilePicturePreview.style.display = 'none';
                    }
                    editProfilePictureFileInput.value = '';

                    // Application documents preview
                    editApplicationDocumentsPreview.innerHTML = '';
                    editApplicationDocumentsFilesInput.value = '';
                    if (employee.application_documents_paths) {
                        try {
                            const docs = JSON.parse(employee.application_documents_paths);
                            if (Array.isArray(docs) && docs.length > 0) {
                                docs.forEach(docPath => {
                                    const filename = docPath.split('/').pop();
                                    const fileItem = document.createElement('div');
                                    fileItem.className = 'file-list-item';
                                    fileItem.innerHTML = `
                                        <svg class="w-4 h-4 text-blue-500" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6a2 2 0 01.586 1.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 0h4l4 4v10H6V4z" clip-rule="evenodd"></path></svg>
                                        <a href="${docPath}" target="_blank" class="text-blue-600 hover:underline block text-sm truncate" title="${filename}">${filename}</a>
                                    `;
                                    editApplicationDocumentsPreview.appendChild(fileItem);
                                });
                            }
                        } catch (e) {
                            console.error("Failed to parse application_documents_paths for edit:", e);
                            editApplicationDocumentsPreview.innerHTML = `<span class="text-red-500 text-xs">ข้อผิดพลาด JSON ในเอกสารเดิม</span>`;
                        }
                    }

                    editBankAccountNumberInput.value = employee.bank_account_number || '';
                    editBankNameInput.value = employee.bank_name || '';
                    editHireDateInput.value = formatDate(employee.hire_date);
                    editTerminationDateInput.value = employee.termination_date ? formatDate(employee.termination_date) : '';
                    editEmployeeStatusSelect.value = employee.employee_status;
                    editDepartmentIdSelect.value = employee.department_id;
                    editPositionIdSelect.value = employee.position_id;

                    editEmployeeModal.style.display = 'flex';
                } catch (error) {
                    console.error('Error fetching employee for edit:', error);
                    showMessage(employeesMessage, `เกิดข้อผิดพลาดในการโหลดพนักงานเพื่อแก้ไข: ${error.message}`, true);
                }
            });
        });

        // Add form previews
        addProfilePictureFileInput.addEventListener('change', () => {
            previewImage(addProfilePictureFileInput, addProfilePicturePreview);
        });
        addApplicationDocumentsFilesInput.addEventListener('change', () => {
            previewPdfFiles(addApplicationDocumentsFilesInput, addApplicationDocumentsPreview);
        });

        // Edit form previews
        editProfilePictureFileInput.addEventListener('change', () => {
            previewImage(editProfilePictureFileInput, editProfilePicturePreview);
        });
        editApplicationDocumentsFilesInput.addEventListener('change', () => {
            previewPdfFiles(editApplicationDocumentsFilesInput, editApplicationDocumentsPreview);
        });

        // Clear buttons for edit form
        clearEditProfilePictureButton.addEventListener('click', () => {
            editProfilePictureFileInput.value = '';
            editProfilePicturePreview.src = '#';
            editProfilePicturePreview.style.display = 'none';
            clearEditProfilePictureButton.dataset.cleared = 'true';
        });

        clearEditApplicationDocumentsButton.addEventListener('click', () => {
            editApplicationDocumentsFilesInput.value = '';
            editApplicationDocumentsPreview.innerHTML = '';
            clearEditApplicationDocumentsButton.dataset.cleared = 'true';
        });

        // Delete buttons
        document.querySelectorAll('.delete-btn').forEach(button => {
            button.addEventListener('click', async (event) => {
                const id = event.target.dataset.id;
                if (confirm(`คุณแน่ใจหรือไม่ที่ต้องการลบพนักงาน ID: ${id} นี้?`)) {
                    try {
                        const response = await fetch(`${API_BASE_URL}/employees/${id}`, { method: 'DELETE' });
                        if (!response.ok) throw new Error(await formatApiErrorDetail(response));
                        showMessage(employeesMessage, 'ลบพนักงานเรียบร้อยแล้ว');
                        fetchEmployees();
                    } catch (error) {
                        console.error('Error deleting employee:', error);
                        showMessage(employeesMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
                    }
                }
            });
        });
    }

    // --- Translate EmployeeStatus ---
    function translateEmployeeStatus(status) {
        switch(status) {
            case "Active": return "ใช้งาน";
            case "Inactive": return "ไม่ใช้งาน";
            case "On Leave": return "ลา";
            case "Terminated": return "พ้นสภาพ";
            default: return status;
        }
    }

    // --- Upload helpers ---
    async function uploadFile(employeeId, fileType, file) {
        if (!file) return null;

        const formData = new FormData();
        formData.append('file', file);

        const url = (fileType === 'profile_picture')
            ? `${API_BASE_URL}/employees/${employeeId}/upload-profile-picture`
            : `${API_BASE_URL}/employees/${employeeId}/upload-documents`;

        try {
            const response = await fetch(url, { method: 'POST', body: formData });
            if (!response.ok) throw new Error(await formatApiErrorDetail(response));
            const result = await response.json();
            return result.file_path;
        } catch (error) {
            console.error(`Error during file upload (${file.name}, ${fileType}):`, error);
            throw error;
        }
    }

    async function uploadMultipleFiles(employeeId, files) {
        if (!files || files.length === 0) return [];
        const formData = new FormData();
        Array.from(files).forEach(file => formData.append('files', file));
        const url = `${API_BASE_URL}/employees/${employeeId}/upload-documents`;
        try {
            const response = await fetch(url, { method: 'POST', body: formData });
            if (!response.ok) throw new Error(await formatApiErrorDetail(response));
            const result = await response.json();
            return result.uploaded_files;
        } catch (error) {
            console.error('Error during multiple file upload (documents):', error);
            throw error;
        }
    }

    // --- Add Employee ---
    addEmployeeForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        const employeeIdNumber = addEmployeeIdNumberInput.value.trim();
        const firstName = addFirstNameInput.value.trim();
        const lastName = addLastNameInput.value.trim();
        const dateOfBirth = addDateOfBirthInput.value;
        const address = addAddressInput.value.trim();
        const idCardNumber = addIdCardNumberInput.value.trim();
        const email = (addEmailInput.value || '').trim();                 // ✅ NEW
        const phoneNumber = (addPhoneNumberInput.value || '').trim();     // ✅ NEW
        const profilePictureFile = addProfilePictureFileInput.files[0];
        const applicationDocumentsFiles = addApplicationDocumentsFilesInput.files;
        const bankAccountNumber = addBankAccountNumberInput.value.trim();
        const bankName = addBankNameInput.value.trim();
        const hireDate = addHireDateInput.value;
        const terminationDate = addTerminationDateInput.value;
        const employeeStatus = addEmployeeStatusSelect.value;
        const departmentId = addDepartmentIdSelect.value;
        const positionId = addPositionIdSelect.value;

        // Required validation
        if (!employeeIdNumber || !firstName || !lastName || !dateOfBirth || !address || !hireDate || !employeeStatus || !departmentId || !positionId) {
            showMessage(addEmployeeMessage, 'กรุณากรอกข้อมูลที่จำเป็นให้ครบถ้วน', true);
            return;
        }
        if (idCardNumber && (idCardNumber.length !== 13 || !/^\d{13}$/.test(idCardNumber))) {
            showMessage(addEmployeeMessage, 'เลขบัตรประชาชนต้องเป็นตัวเลข 13 หลัก (ถ้ามี)', true);
            return;
        }
        // Quick client-side check for phone pattern (matches input pattern)
        if (phoneNumber && !/^\+?[0-9\- ]{7,20}$/.test(phoneNumber)) {
            showMessage(addEmployeeMessage, 'รูปแบบหมายเลขโทรศัพท์ไม่ถูกต้อง', true);
            return;
        }

        addEmployeeMessage.textContent = 'กำลังอัปโหลดไฟล์และสร้างพนักงาน...';
        addEmployeeMessage.className = 'mt-4 text-sm font-medium text-blue-600';

        try {
            let tempEmployeeData = {
                employee_id_number: employeeIdNumber,
                first_name: firstName,
                last_name: lastName,
                date_of_birth: dateOfBirth,
                address: address,
                id_card_number: idCardNumber || null,
                email: email || null,               // ✅ NEW
                phone_number: phoneNumber || null,  // ✅ NEW
                profile_picture_path: null,
                application_documents_paths: null,
                bank_account_number: bankAccountNumber || null,
                bank_name: bankName || null,
                hire_date: hireDate,
                termination_date: terminationDate || null,
                employee_status: employeeStatus,
                department_id: parseInt(departmentId),
                position_id: parseInt(positionId)
            };

            const createResponse = await fetch(`${API_BASE_URL}/employees/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(tempEmployeeData),
            });

            if (!createResponse.ok) throw new Error(await formatApiErrorDetail(createResponse));
            const newEmployee = await createResponse.json();
            const newEmployeeId = newEmployee.id;

            let uploadedProfilePicturePath = null;
            let uploadedDocumentPaths = [];

            if (profilePictureFile) {
                uploadedProfilePicturePath = await uploadFile(newEmployeeId, 'profile_picture', profilePictureFile);
            }
            if (applicationDocumentsFiles.length > 0) {
                uploadedDocumentPaths = await uploadMultipleFiles(newEmployeeId, applicationDocumentsFiles);
            }

            // Update with uploaded paths
            const updateData = {
                profile_picture_path: uploadedProfilePicturePath,
                application_documents_paths: uploadedDocumentPaths.length > 0 ? JSON.stringify(uploadedDocumentPaths) : null,
            };

            const updateResponse = await fetch(`${API_BASE_URL}/employees/${newEmployeeId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updateData),
            });
            if (!updateResponse.ok) throw new Error(await formatApiErrorDetail(updateResponse));

            showMessage(addEmployeeMessage, `เพิ่มพนักงาน "${newEmployee.first_name} ${newEmployee.last_name}" (ID: ${newEmployeeId}) พร้อมไฟล์เรียบร้อยแล้ว`);
            addEmployeeForm.reset();
            addProfilePicturePreview.style.display = 'none';
            addProfilePicturePreview.src = '#';
            addApplicationDocumentsPreview.innerHTML = '';
            fetchEmployees();
        } catch (error) {
            console.error('Final caught error adding employee with files:', error);
            showMessage(addEmployeeMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
        }
    });

    // --- Edit Employee ---
    editEmployeeForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const employeeId = editEmployeeIdInput.value;

        const employeeIdNumber = editEmployeeIdNumberInput.value.trim();
        const firstName = editFirstNameInput.value.trim();
        const lastName = editLastNameInput.value.trim();
        const dateOfBirth = editDateOfBirthInput.value;
        const address = editAddressInput.value.trim();
        const idCardNumber = editIdCardNumberInput.value.trim();
        const email = (editEmailInput.value || '').trim();               // ✅ NEW
        const phoneNumber = (editPhoneNumberInput.value || '').trim();   // ✅ NEW
        const profilePictureFile = editProfilePictureFileInput.files[0];
        const applicationDocumentsFiles = editApplicationDocumentsFilesInput.files;
        const bankAccountNumber = editBankAccountNumberInput.value.trim();
        const bankName = editBankNameInput.value.trim();
        const hireDate = editHireDateInput.value;
        const terminationDate = editTerminationDateInput.value;
        const employeeStatus = editEmployeeStatusSelect.value;
        const departmentId = editDepartmentIdSelect.value;
        const positionId = editPositionIdSelect.value;

        if (!employeeIdNumber || !firstName || !lastName || !dateOfBirth || !address || !hireDate || !employeeStatus || !departmentId || !positionId) {
            showMessage(editEmployeeMessage, 'กรุณากรอกข้อมูลที่จำเป็นให้ครบถ้วน', true);
            return;
        }
        if (idCardNumber && (idCardNumber.length !== 13 || !/^\d{13}$/.test(idCardNumber))) {
            showMessage(editEmployeeMessage, 'เลขบัตรประชาชนต้องเป็นตัวเลข 13 หลัก (ถ้ามี)', true);
            return;
        }
        if (phoneNumber && !/^\+?[0-9\- ]{7,20}$/.test(phoneNumber)) {
            showMessage(editEmployeeMessage, 'รูปแบบหมายเลขโทรศัพท์ไม่ถูกต้อง', true);
            return;
        }

        editEmployeeMessage.textContent = 'กำลังอัปโหลดไฟล์และอัปเดตพนักงาน...';
        editEmployeeMessage.className = 'mt-4 text-sm font-medium text-blue-600';

        try {
            let uploadedProfilePicturePath = null;
            let uploadedDocumentPaths = [];
            let updateDocuments = false;

            if (profilePictureFile) {
                uploadedProfilePicturePath = await uploadFile(employeeId, 'profile_picture', profilePictureFile);
            } else if (clearEditProfilePictureButton.dataset.cleared === 'true') {
                uploadedProfilePicturePath = null;
            } else {
                uploadedProfilePicturePath = (editProfilePicturePreview.src !== '#' && editProfilePicturePreview.style.display !== 'none')
                    ? editProfilePicturePreview.src
                    : null;
            }

            if (applicationDocumentsFiles.length > 0) {
                uploadedDocumentPaths = await uploadMultipleFiles(employeeId, applicationDocumentsFiles);
                updateDocuments = true;
            } else if (clearEditApplicationDocumentsButton.dataset.cleared === 'true') {
                uploadedDocumentPaths = null;
                updateDocuments = true;
            } else {
                updateDocuments = false;
            }

            let updateData = {
                employee_id_number: employeeIdNumber,
                first_name: firstName,
                last_name: lastName,
                date_of_birth: dateOfBirth,
                address: address,
                id_card_number: idCardNumber || null,
                email: email || null,               // ✅ NEW
                phone_number: phoneNumber || null,  // ✅ NEW
                bank_account_number: bankAccountNumber || null,
                bank_name: bankName || null,
                hire_date: hireDate,
                termination_date: terminationDate || null,
                employee_status: employeeStatus,
                department_id: parseInt(departmentId),
                position_id: parseInt(positionId),
                profile_picture_path: uploadedProfilePicturePath
            };

            if (updateDocuments) {
                updateData.application_documents_paths = (uploadedDocumentPaths && uploadedDocumentPaths.length > 0)
                    ? JSON.stringify(uploadedDocumentPaths)
                    : null;
            } else {
                const originalEmployeeResponse = await fetch(`${API_BASE_URL}/employees/${employeeId}`);
                if (!originalEmployeeResponse.ok) {
                    throw new Error(`เกิดข้อผิดพลาดในการดึงข้อมูลพนักงานเดิมสำหรับเอกสาร: ${await formatApiErrorDetail(originalEmployeeResponse)}`);
                }
                const originalEmployee = await originalEmployeeResponse.json();
                updateData.application_documents_paths = originalEmployee.application_documents_paths;
            }

            // reset flags
            clearEditProfilePictureButton.dataset.cleared = 'false';
            clearEditApplicationDocumentsButton.dataset.cleared = 'false';

            const response = await fetch(`${API_BASE_URL}/employees/${employeeId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updateData),
            });

            if (!response.ok) throw new Error(await formatApiErrorDetail(response));

            const updatedEmployee = await response.json();
            showMessage(employeesMessage, `อัปเดตพนักงาน "${updatedEmployee.first_name} ${updatedEmployee.last_name}" (ID: ${updatedEmployee.id}) เรียบร้อยแล้ว`);
            editEmployeeModal.style.display = 'none';
            fetchEmployees();
        } catch (error) {
            console.error('Final caught error updating employee with files:', error);
            showMessage(editEmployeeMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
        }
    });

    // --- Close Edit Modal ---
    closeEditModalButton.addEventListener('click', () => {
        editEmployeeModal.style.display = 'none';
        editEmployeeMessage.textContent = '';
        clearEditProfilePictureButton.dataset.cleared = 'false';
        clearEditApplicationDocumentsButton.dataset.cleared = 'false';
    });

    // Initial loads
    fetchDepartmentsForDropdown();
    fetchPositionsForDropdown();
    fetchEmployees();
});
