from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel
from pydantic import BaseModel

# 'employee' 테이블과 매핑되는 데이터베이스 모델
class Employee(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True) # 직원 ID (기본 키)
    object_key: Optional[str] = Field(default=None, max_length=80) # 사진 파일의 고유 키
    full_name: str = Field(max_length=200) # 직원의 전체 이름
    location: str = Field(max_length=200) # 근무지
    job_title: str = Field(max_length=200) # 직책
    badges: str = Field(max_length=200) # 직원이 가진 배지 (쉼표로 구분)
    created_datetime: datetime = Field(default_factory=datetime.now) # 생성 일시

    class Config:
        # JSON 직렬화 시 datetime 객체를 ISO 형식 문자열로 변환
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

# API를 통해 외부에 노출될 직원의 공개 정보를 위한 Pydantic 모델
class EmployeePublic(BaseModel):
    id: int
    object_key: Optional[str] = None
    full_name: str
    location: str
    job_title: str
    badges: str
    photo_url: Optional[str] = None # 사진에 접근할 수 있는 URL (동적으로 생성)

    class Config:
        from_attributes = True # SQLModel 같은 ORM 객체로부터 Pydantic 모델을 생성할 수 있도록 함

# 직원 목록 API 응답을 위한 타입 별칭
EmployeesListResponse = List[EmployeePublic]
