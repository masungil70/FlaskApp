from typing import List, Optional
from sqlmodel import create_engine, Session, select
from sqlalchemy.pool import QueuePool
import config
from models import Employee # Employee 모델 임포트

# 데이터베이스 연결 URL 생성
DATABASE_URL = (
    f"mysql+mysqlconnector://{config.DATABASE_USER}:{config.DATABASE_PASSWORD}@"
    f"{config.DATABASE_HOST}/{config.DATABASE_DB_NAME}"
)

# 커넥션 풀을 사용하는 데이터베이스 엔진 생성
# pool_size: 풀에서 유지할 최소한의 커넥션 수
# max_overflow: 풀 크기를 초과하여 열 수 있는 커넥션 수
# pool_recycle: 지정된 시간(초)이 지나면 커넥션을 재활용하여 오래된 커넥션 문제 방지
engine = create_engine(
    DATABASE_URL,
    echo=False, # True로 설정 시 실행되는 SQL 구문 출력
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600 # 1시간 후 커넥션 재활용
)

def create_db_and_tables():
    """SQLModel 메타데이터를 기반으로 데이터베이스 테이블을 생성합니다."""
    # 실제 테이블 생성은 외부 SQL 스크립트로 관리하는 것이 더 나을 수 있습니다.
    # 이 함수는 주로 엔진 설정을 확인하는 역할을 합니다.
    pass

def get_session():
    """데이터베이스 세션을 얻기 위한 의존성 함수입니다."""
    with Session(engine) as session:
        yield session

def list_employees() -> List[Employee]:
    """데이터베이스에서 모든 직원 목록을 조회합니다."""
    with Session(engine) as session:
        statement = select(Employee).order_by(Employee.full_name.desc())
        employees = session.exec(statement).all()
        return employees

def load_employee(employee_id: int) -> Optional[Employee]:
    """데이터베이스에서 특정 직원 한 명의 정보를 조회합니다."""
    with Session(engine) as session:
        employee = session.get(Employee, employee_id)
        return employee

def add_employee(employee_data: Employee) -> Employee:
    """데이터베이스에 직원을 추가합니다."""
    with Session(engine) as session:
        session.add(employee_data)
        session.commit()
        session.refresh(employee_data)
        return employee_data

def update_employee(employee_id: int, employee_data: Employee) -> Optional[Employee]:
    """데이터베이스의 직원 정보를 수정합니다."""
    with Session(engine) as session:
        existing_employee = session.get(Employee, employee_id)
        if not existing_employee:
            return None
        
        # employee_data에서 제공된 필드만 업데이트
        for key, value in employee_data.dict(exclude_unset=True).items():
            setattr(existing_employee, key, value)
        
        session.add(existing_employee)
        session.commit()
        session.refresh(existing_employee)
        return existing_employee

def delete_employee(employee_id: int):
    """데이터베이스에서 직원을 삭제합니다."""
    with Session(engine) as session:
        employee = session.get(Employee, employee_id)
        if employee:
            session.delete(employee)
            session.commit()
