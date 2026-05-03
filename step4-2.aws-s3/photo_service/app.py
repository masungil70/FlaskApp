import os
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse, RedirectResponse
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# =========================================================
# AWS S3 설정
# =========================================================
# 중요 : example.env.tmp 파일을 참고하여 .env 파일에 S3_ENDPOINT, AWS_ACCESS_KEY, AWS_SECRET_KEY 값을 설정해야 합니다.

AWS_REGION = os.getenv("AWS_REGION", "ap-northeast-2")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
AWS_BUCKET = os.getenv("AWS_BUCKET", "mybucket")

s3_client = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
)

# =========================================================
# Bucket 존재 확인 (AWS에서는 생성은 보통 콘솔/CLI)
# =========================================================

def check_bucket_exists():
    try:
        s3_client.head_bucket(Bucket=AWS_BUCKET)
        print(f"Bucket '{AWS_BUCKET}' exists.")
    except ClientError as e:
        raise Exception(f"Bucket not accessible or does not exist: {e}")

check_bucket_exists()

# =========================================================
# 업로드
# =========================================================

@app.post("/upload")
async def upload_photo(file: UploadFile = File(...)):

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    ext = file.filename.split(".")[-1] if "." in file.filename else "bin"
    object_key = f"{uuid.uuid4()}.{ext}"

    try:
        s3_client.upload_fileobj(
            file.file,
            AWS_BUCKET,
            object_key,
            ExtraArgs={
                "ContentType": file.content_type,
                "ACL": "private"
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "message": "Upload success",
        "object_key": object_key,
        "url": f"/photos/{object_key}"
    }

# =========================================================
# 다운로드 (Presigned URL)
# =========================================================

@app.get("/photos/{object_key}")
async def get_photo(object_key: str):

    try:
        s3_client.head_object(Bucket=AWS_BUCKET, Key=object_key)

        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": AWS_BUCKET, "Key": object_key},
            ExpiresIn=3600
        )

        return RedirectResponse(url=url)

    except ClientError:
        raise HTTPException(status_code=404, detail="Photo not found")

# =========================================================
# 삭제
# =========================================================

@app.delete("/photos/{object_key}")
async def delete_photo(object_key: str):

    try:
        s3_client.delete_object(Bucket=AWS_BUCKET, Key=object_key)
        return {"message": "deleted", "object_key": object_key}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =========================================================
# 목록 조회
# =========================================================

@app.get("/photos")
async def list_photos():

    response = s3_client.list_objects_v2(Bucket=AWS_BUCKET)

    files = []
    if "Contents" in response:
        for obj in response["Contents"]:
            files.append({
                "key": obj["Key"],
                "size": obj["Size"]
            })

    return {
        "bucket": AWS_BUCKET,
        "count": len(files),
        "files": files
    }