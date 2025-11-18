# --- 기본 라이브러리 및 모듈 임포트 ---
import os
import shutil
import uuid
import jwt
import datetime
import time
from typing import List, Optional
from io import BytesIO

# --- FastAPI 및 관련 라이브러리 임포트 ---
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, status, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordBearer

# --- 내부 모듈 임포트 ---
import config
import util
import database
from models import Employee, EmployeePublic, EmployeesListResponse

# --- Pydantic 모델 정의 ---

# 로그인 요청 시 사용될 데이터 모델
class LoginRequest(BaseModel):
    username: str
    password: str

# --- FastAPI 앱 초기화 ---

app = FastAPI()

# CORS (Cross-Origin Resource Sharing) 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 출처에서의 요청 허용
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메소드 허용
    allow_headers=["*"],  # 모든 HTTP 헤더 허용
)

# --- 사진 서비스 로직 (Photo Service Logic) ---

PHOTOS_DIR = config.PHOTOS_DIR
os.makedirs(PHOTOS_DIR, exist_ok=True) # 사진 저장 디렉토리 생성

# 내부적으로 사용될 사진 업로드 함수
async def internal_upload_photo(filename: str, image_bytes: bytes):
    if not filename:
        raise HTTPException(status_code=400, detail="No file selected")

    file_extension = filename.split(".")[-1] if "." in filename else "bin"
    object_key = f"{uuid.uuid4()}.{file_extension}" # 고유한 파일 키 생성
    file_path = os.path.join(PHOTOS_DIR, object_key)

    try:
        with open(file_path, "wb") as buffer:
            buffer.write(image_bytes) # 이미지 바이트를 파일에 쓰기
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not upload file: {e}")

    return {"object_key": object_key}

# 내부적으로 사용될 사진 삭제 함수
async def internal_delete_photo(object_key: str):
    file_path = os.path.join(PHOTOS_DIR, object_key)
    if not os.path.exists(file_path):
        print(f"Warning: Photo not found for deletion: {object_key}")
        return
    
    try:
        os.remove(file_path)
    except Exception as e:
        print(f"Error: Could not delete file: {e}")

# 사진 파일을 클라이언트에게 제공하는 API 엔드포인트
@app.get("/photos/{object_key}")
async def get_photo(object_key: str):
    file_path = os.path.join(PHOTOS_DIR, object_key)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Photo not found")
    return FileResponse(file_path)


# --- 인증 서비스 로직 (Auth Service Logic) ---

SECRET_KEY = config.JWT_SECRET_KEY
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login") # 토큰 URL 지정

# 로그인 API 엔드포인트
@app.post('/api/auth/login')
async def login(user_credentials: LoginRequest):
    # 간단한 하드코딩된 사용자 정보 확인
    if user_credentials.username == 'admin' and user_credentials.password == 'password':
        # JWT 토큰 생성
        token = jwt.encode({
            'user': user_credentials.username,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1) # 1시간 유효
        }, SECRET_KEY, algorithm=ALGORITHM)
        return {'token': token}
    raise HTTPException(status_code=401, detail="Invalid credentials")

# 현재 인증된 사용자를 확인하는 의존성 함수
async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]) # 토큰 디코딩
        username: str = payload.get("user")
        if username is None:
            raise credentials_exception
        return username
    except jwt.ExpiredSignatureError: # 토큰 만료 시
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError: # 그 외 JWT 오류
        raise credentials_exception

# --- 직원 서비스 로직 (Employee Service Logic) ---

# 애플리케이션 시작 시 데이터베이스 테이블 생성
@app.on_event("startup")
async def on_startup():
    database.create_db_and_tables()

# 사진 URL을 생성하는 헬퍼 함수
def get_photo_url(object_key: str):
    return f"/photos/{object_key}"

# 모든 직원 목록을 조회하는 API 엔드포인트
@app.get("/api/employee/employees", response_model=EmployeesListResponse)
async def get_employees(current_user: str = Depends(get_current_user)):
    start_time = time.time()
    employees: List[Employee] = database.list_employees()
    employees_public_data = []
    for employee in employees:
        emp_public = EmployeePublic.from_orm(employee)
        if employee.object_key:
            emp_public.photo_url = get_photo_url(employee.object_key)
        employees_public_data.append(emp_public)
    
    execution_time = (time.time() - start_time) * 1000
    print(f"get_employees executed in {execution_time:.2f} ms")
    return employees_public_data

# 특정 직원 정보를 조회하는 API 엔드포인트
@app.get("/api/employee/employee/{employee_id}", response_model=EmployeePublic, responses={404: {"description": "Employee not found"}})
async def get_employee(employee_id: int, current_user: str = Depends(get_current_user)):
    employee: Optional[Employee] = database.load_employee(employee_id)
    if employee:
        emp_public = EmployeePublic.from_orm(employee)
        if employee.object_key:
            emp_public.photo_url = get_photo_url(employee.object_key)
        return emp_public
    raise HTTPException(status_code=404, detail="Employee not found")

# 직원을 생성하거나 수정하는 API 엔드포인트
@app.post("/api/employee/employee", response_model=Employee, responses={400: {"detail": "Missing required fields"}, 500: {"detail": "Could not save image"}})
async def save_employee(
    full_name: str = Form(...),
    location: str = Form(...),
    job_title: str = Form(...),
    badges: str = Form(""),
    employee_id: Optional[int] = Form(None),
    photo: Optional[UploadFile] = File(None),
    current_user: str = Depends(get_current_user)
):
    key = None
    if photo and photo.filename != '':
        image_bytes = util.resize_image(photo.file, (120, 160)) # 이미지 리사이징
        if image_bytes:
            # 리사이징된 이미지 업로드
            upload_result = await internal_upload_photo(photo.filename, image_bytes)
            key = upload_result.get("object_key")

    employee_data = Employee(
        id=employee_id,
        object_key=key,
        full_name=full_name,
        location=location,
        job_title=job_title,
        badges=badges
    )

    if employee_id: # 직원 정보 수정
        if key: # 새 사진이 업로드된 경우
            old_employee: Optional[Employee] = database.load_employee(employee_id)
            if old_employee and old_employee.object_key:
                await internal_delete_photo(old_employee.object_key) # 이전 사진 삭제
        
        updated_employee = database.update_employee(employee_id, employee_data)
        if updated_employee:
            return updated_employee
        raise HTTPException(status_code=404, detail="Employee not found for update")
    else: # 새 직원 생성
        new_employee = database.add_employee(employee_data)
        return new_employee

# 직원을 삭제하는 API 엔드포인트
@app.delete("/api/employee/employee/{employee_id}", responses={404: {"description": "Employee not found"}, 200: {"description": "Employee deleted"}})
async def delete_employee_route(employee_id: int, current_user: str = Depends(get_current_user)):
    employee: Optional[Employee] = database.load_employee(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    if employee.object_key:
        await internal_delete_photo(employee.object_key) # 사진 파일 삭제

    database.delete_employee(employee_id) # 데이터베이스에서 직원 정보 삭제
    return JSONResponse(status_code=status.HTTP_200_OK, content={"success": True, "message": f"Employee {employee_id} deleted."})

# --- 게이트웨이 로직 (Gateway Logic - Static Files & Root) ---

STATIC_DIR = 'static'
# 정적 파일 (HTML, CSS, JS) 제공을 위한 마운트
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# 루트 경로('/') 요청 시 index.html 파일을 제공
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="index.html not found")
    with open(index_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

# --- Uvicorn 실행 가이드 ---
# 이 앱을 실행하려면 터미널에 다음 명령어를 입력하세요:
# uvicorn app:app --host 0.0.0.0 --port 5000 --reload
