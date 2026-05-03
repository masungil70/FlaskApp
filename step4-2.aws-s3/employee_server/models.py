from datetime import datetime
from typing import Optional, List # List is needed for EmployeesResponse
from sqlmodel import Field, SQLModel
from pydantic import BaseModel # Added for EmployeesResponse

class Employee(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    object_key: Optional[str] = Field(default=None, max_length=80)
    full_name: str = Field(max_length=200)
    location: str = Field(max_length=200)
    job_title: str = Field(max_length=200)
    badges: str = Field(max_length=200)
    created_datetime: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

# Define a Pydantic model for the public representation of an Employee
class EmployeePublic(BaseModel):
    id: int
    object_key: Optional[str] = None
    full_name: str
    location: str
    job_title: str
    badges: str
    photo_url: Optional[str] = None # Add photo_url as it's generated in the app

    class Config:
        from_attributes = True # Enable ORM mode for Pydantic to read from SQLModel instances (Pydantic V2)
# Define a type alias for the list response
EmployeesListResponse = List[EmployeePublic]
