// DOM 콘텐츠가 모두 로드되면 스크립트를 실행합니다.
document.addEventListener('DOMContentLoaded', () => {
    // --- DOM 요소 가져오기 ---
    const authSection = document.getElementById('auth-section');
    const employeeSection = document.getElementById('employee-section');
    const loginForm = document.getElementById('login-form');
    const logoutButton = document.getElementById('logout-button');
    const authMessage = document.getElementById('auth-message');
    const loggedInUserSpan = document.getElementById('logged-in-user');
    const employeeListDiv = document.getElementById('employee-list');
    const employeeForm = document.getElementById('employee-form');
    const refreshEmployeesButton = document.getElementById('refresh-employees');
    const employeeMessage = document.getElementById('employee-message');
    const cancelEditButton = document.getElementById('cancel-edit');
    const loadingIndicator = document.getElementById('loading-indicator');
    const photoInput = document.getElementById('photo');
    const photoPreview = document.getElementById('photo-preview');
    const badgesCheckboxesDiv = document.getElementById('badges-checkboxes');

    // 로컬 스토리지에서 JWT 토큰을 가져옵니다.
    let jwtToken = localStorage.getItem('jwtToken');

    // --- 상수 정의 ---
    const API_BASE_URL = ''; // API 요청의 기본 URL (동일 출처이므로 상대 경로 사용)
    const DEFAULT_PHOTO_PLACEHOLDER = '/static/no_photo.png'; // 기본 프로필 사진 경로

    // --- 유틸리티 함수 ---

    // 사용자에게 메시지를 표시하는 함수
    function showMessage(element, message, isError = false) {
        element.textContent = message;
        element.style.color = isError ? 'red' : 'green';
        setTimeout(() => {
            element.textContent = '';
        }, 5000); // 5초 후에 메시지 사라짐
    }

    // 로딩 인디케이터를 표시하는 함수
    function showLoading() {
        loadingIndicator.style.display = 'block';
    }

    // 로딩 인디케이터를 숨기는 함수
    function hideLoading() {
        loadingIndicator.style.display = 'none';
    }

    // 로그인 상태에 따라 UI를 설정하는 함수
    function setAuthUI(loggedIn) {
        if (loggedIn) {
            authSection.style.display = 'none'; // 로그인 폼 숨기기
            employeeSection.style.display = 'block'; // 직원 관리 섹션 보이기
            const payload = JSON.parse(atob(jwtToken.split('.')[1])); // 토큰에서 사용자 정보 파싱
            loggedInUserSpan.textContent = payload.user;
            fetchEmployees(); // 직원 목록 가져오기
        } else {
            authSection.style.display = 'block'; // 로그인 폼 보이기
            employeeSection.style.display = 'none'; // 직원 관리 섹션 숨기기
            loggedInUserSpan.textContent = '';
            employeeListDiv.innerHTML = '';
            resetEmployeeForm();
        }
    }

    // API 요청에 필요한 인증 헤더를 반환하는 함수
    function getAuthHeaders() {
        if (jwtToken) {
            return {
                'Authorization': `Bearer ${jwtToken}`
            };
        }
        return {};
    }

    // 직원 정보 입력 폼을 초기화하는 함수
    function resetEmployeeForm() {
        employeeForm.reset();
        document.getElementById('employee-id').value = '';
        cancelEditButton.style.display = 'none';
        employeeForm.querySelector('button[type="submit"]').textContent = 'Save Employee';
        photoPreview.src = DEFAULT_PHOTO_PLACEHOLDER; // 사진 미리보기 초기화
        // 모든 배지 체크박스 해제
        badgesCheckboxesDiv.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
            checkbox.checked = false;
        });
    }

    // --- 인증 관련 기능 ---

    // 로그인 폼 제출 이벤트 리스너
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault(); // 폼 기본 동작 방지
        showLoading();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;

        try {
            const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            const data = await response.json();

            if (response.ok) {
                jwtToken = data.token;
                localStorage.setItem('jwtToken', jwtToken); // 토큰을 로컬 스토리지에 저장
                showMessage(authMessage, 'Login successful!');
                setAuthUI(true); // 로그인 성공 UI로 변경
            } else {
                showMessage(authMessage, data.detail || 'Login failed', true);
            }
        } catch (error) {
            showMessage(authMessage, `Error: ${error.message}`, true);
        } finally {
            hideLoading();
        }
    });

    // 로그아웃 버튼 클릭 이벤트 리스너
    logoutButton.addEventListener('click', () => {
        jwtToken = null;
        localStorage.removeItem('jwtToken'); // 로컬 스토리지에서 토큰 제거
        showMessage(authMessage, 'Logged out successfully.');
        setAuthUI(false); // 로그아웃 UI로 변경
    });

    // --- 이미지 미리보기 기능 ---

    // 사진 파일 입력 변경 이벤트 리스너
    photoInput.addEventListener('change', (event) => {
        const file = event.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                photoPreview.src = e.target.result; // 선택한 파일로 미리보기 업데이트
            };
            reader.readAsDataURL(file);
        } else {
            photoPreview.src = DEFAULT_PHOTO_PLACEHOLDER; // 파일 선택 안됐으면 기본 이미지로
        }
    });

    // --- 직원 관리 기능 ---

    // 서버에서 직원 목록을 가져와 화면에 표시하는 함수
    async function fetchEmployees() {
        showLoading();
        try {
            const response = await fetch(`${API_BASE_URL}/api/employee/employees`, {
                method: 'GET',
                headers: getAuthHeaders()
            });

            if (response.status === 401) { // 인증 실패 시
                showMessage(employeeMessage, 'Unauthorized. Please log in again.', true);
                logoutButton.click(); // 강제 로그아웃
                return;
            }

            const employees = await response.json();

            if (response.ok) {
                employeeListDiv.innerHTML = '';
                if (employees.length === 0) {
                    employeeListDiv.innerHTML = '<p>No employees found.</p>';
                    return;
                }
                // 각 직원을 화면에 렌더링
                employees.forEach(emp => {
                    const empDiv = document.createElement('div');
                    empDiv.className = 'employee-item';
                    empDiv.innerHTML = `
                        <img src="${emp.photo_url ? API_BASE_URL + emp.photo_url : DEFAULT_PHOTO_PLACEHOLDER}" alt="${emp.full_name}" width="120" height="160">
                        <div>
                            <h4>${emp.full_name} (${emp.job_title})</h4>
                            <p>Location: ${emp.location}</p>
                            <p>Badges: ${emp.badges || 'N/A'}</p>
                            <button class="edit-employee" data-id="${emp.id}">Edit</button>
                            <button class="delete-employee" data-id="${emp.id}">Delete</button>
                        </div>
                    `;
                    employeeListDiv.appendChild(empDiv);
                });
                addEmployeeEventListeners(); // 수정/삭제 버튼에 이벤트 리스너 추가
            } else {
                showMessage(employeeMessage, employees.detail || 'Failed to fetch employees', true);
            }
        } catch (error) {
            showMessage(employeeMessage, `Error fetching employees: ${error.message}`, true);
        } finally {
            hideLoading();
        }
    }

    // 직원 목록의 수정/삭제 버튼에 이벤트 리스너를 추가하는 함수
    function addEmployeeEventListeners() {
        // 수정 버튼
        document.querySelectorAll('.edit-employee').forEach(button => {
            button.addEventListener('click', async (e) => {
                showLoading();
                const id = e.target.dataset.id;
                try {
                    const response = await fetch(`${API_BASE_URL}/api/employee/employee/${id}`, {
                        method: 'GET',
                        headers: getAuthHeaders()
                    });
                    const employee = await response.json();
                    if (response.ok) {
                        // 폼에 기존 직원 정보 채우기
                        document.getElementById('employee-id').value = employee.id;
                        document.getElementById('full_name').value = employee.full_name;
                        document.getElementById('location').value = employee.location;
                        document.getElementById('job_title').value = employee.job_title;
                        photoPreview.src = employee.photo_url ? API_BASE_URL + employee.photo_url : DEFAULT_PHOTO_PLACEHOLDER;
                        badgesCheckboxesDiv.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
                            checkbox.checked = employee.badges.includes(checkbox.value);
                        });

                        cancelEditButton.style.display = 'inline-block';
                        employeeForm.querySelector('button[type="submit"]').textContent = 'Update Employee';
                    } else {
                        showMessage(employeeMessage, employee.detail || 'Failed to load employee for edit', true);
                    }
                } catch (error) {
                    showMessage(employeeMessage, `Error loading employee: ${error.message}`, true);
                } finally {
                    hideLoading();
                }
            });
        });

        // 삭제 버튼
        document.querySelectorAll('.delete-employee').forEach(button => {
            button.addEventListener('click', async (e) => {
                const id = e.target.dataset.id;
                if (confirm('Are you sure you want to delete this employee?')) {
                    showLoading();
                    try {
                        const response = await fetch(`${API_BASE_URL}/api/employee/employee/${id}`, {
                            method: 'DELETE',
                            headers: getAuthHeaders()
                        });
                        const data = await response.json();
                        if (response.ok) {
                            showMessage(employeeMessage, data.message || 'Employee deleted successfully.');
                            fetchEmployees(); // 목록 새로고침
                        } else {
                            showMessage(employeeMessage, data.detail || 'Failed to delete employee', true);
                        }
                    } catch (error) {
                        showMessage(employeeMessage, `Error deleting employee: ${error.message}`, true);
                    } finally {
                        hideLoading();
                    }
                }
            });
        });
    }

    // 직원 생성/수정 폼 제출 이벤트 리스너
    employeeForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        showLoading();
        const id = document.getElementById('employee-id').value;
        const full_name = document.getElementById('full_name').value;
        const location = document.getElementById('location').value;
        const job_title = document.getElementById('job_title').value;
        const selectedBadges = Array.from(badgesCheckboxesDiv.querySelectorAll('input[type="checkbox"]:checked'))
                                    .map(cb => cb.value)
                                    .join(',');
        const photo = document.getElementById('photo').files[0];

        const formData = new FormData(); // 파일 업로드를 위해 FormData 사용
        if (id) formData.append('employee_id', id);
        formData.append('full_name', full_name);
        formData.append('location', location);
        formData.append('job_title', job_title);
        formData.append('badges', selectedBadges);
        if (photo) formData.append('photo', photo);

        try {
            const response = await fetch(`${API_BASE_URL}/api/employee/employee`, {
                method: 'POST',
                headers: getAuthHeaders(), // 인증 헤더 포함
                body: formData
            });

            if (response.status === 401) {
                showMessage(employeeMessage, 'Unauthorized. Please log in again.', true);
                logoutButton.click();
                return;
            }

            const data = await response.json();

            if (response.ok) {
                showMessage(employeeMessage, `Employee ${id ? 'updated' : 'added'} successfully!`);
                resetEmployeeForm();
                fetchEmployees(); // 목록 새로고침
            } else {
                showMessage(employeeMessage, data.detail || `Failed to ${id ? 'update' : 'add'} employee`, true);
            }
        } catch (error) {
            showMessage(employeeMessage, `Error saving employee: ${error.message}`, true);
        } finally {
            hideLoading();
        }
    });

    // 새로고침 버튼과 수정 취소 버튼 이벤트 리스너
    refreshEmployeesButton.addEventListener('click', fetchEmployees);
    cancelEditButton.addEventListener('click', resetEmployeeForm);

    // --- 초기화 ---
    // 페이지 로드 시 토큰 유무에 따라 초기 UI 설정
    if (jwtToken) {
        setAuthUI(true);
    } else {
        setAuthUI(false);
    }
});