from pydantic import BaseModel
import uuid

class UploadedResponse(BaseModel):
    id: uuid.UUID
    filename: str
    status: str

class DocumentCheck(BaseModel):
    filename: str
    file_size: int
    status: str