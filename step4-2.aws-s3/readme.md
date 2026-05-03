#aws 3s를 이용하여 사진 첨부 파일을 저장할 수 있게 수정된 버전 

---

# ☁️ 1. AWS S3 버킷 생성 절차

## ✅ 1단계: S3 버킷 생성

AWS Console → S3 → Create bucket

설정:

* Bucket name: `employee-photo-bucket-kosa-0` (전세계 유일한 이름으로 생성해야됨)
* Region: `ap-northeast-2 (서울)`
* Block Public Access: ✔ 유지 (권장)
* Versioning: 선택
* Encryption: SSE-S3 또는 SSE-KMS

---

## ✅ 2단계: 권한 설정 (IAM 기반)

S3는 **버킷 직접 접근이 아니라 IAM 권한으로 제어**

### ✔ IAM 정책 예시

IAM → Policies → Create policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::employee-photo-bucket-kosa-0",
        "arn:aws:s3:::employee-photo-bucket-kosa-0/*"
      ]
    }
  ]
}
```

이름 : employee-photo-bucket-kosa-policy

---

## ✅ 3단계: IAM 사용자 생성

IAM → Users → Create user

* 이름: `kosa`
* Access type: ✔ Programmatic access

권한 연결:

* 위에서 만든 policy 연결

---

# 🔑 2. Access Key 생성 방법

## ✅ AWS CLI / Console 방식

IAM → Users → kosa

### → Security credentials 탭

* Create access key 클릭
* 선택: **Application running outside AWS**
* 생성 완료 후:

```text
AWS_ACCESS_KEY_ID = AKIAxxxxxxxx
AWS_SECRET_ACCESS_KEY = xxxxxxxxxxxxx
```

⚠️ 이 키는 한 번만 표시됨 → 반드시 저장

---

# 🧠 3. .env 설정 예시

```env
AWS_REGION=ap-northeast-2
AWS_ACCESS_KEY=AKIAxxxxxxxxxxxx
AWS_SECRET_KEY=xxxxxxxxxxxxxxxx
S3_BUCKET=employee-photo-bucket-kosa-0
```

---

# 🚀 4. 운영 구조 추천 (실무)

AWS S3에서는 이렇게 운영하는 게 표준입니다:

### ✔ 구조

```
FastAPI
   ↓
Presigned URL 생성
   ↓
Client 직접 S3 업로드/다운로드
```

👉 지금 구조도 좋지만, 확장하면:

* 업로드 → S3 직접 업로드 (presigned PUT)
* 다운로드 → presigned GET
* FastAPI는 인증/권한만 처리

---

# ⚡ 5. Ceph vs AWS S3 차이 핵심

| 항목           | Ceph RGW | AWS S3  |
| ------------ | -------- | ------- |
| endpoint_url | 필요       | 불필요     |
| 유지관리         | 직접       | AWS 관리  |
| 확장성          | 직접 구성    | 무제한     |
| IAM          | 자체       | AWS IAM |

---


---

# 6. 실행

```bash
docker compose up -d

# ip 주소 확인 
ip a
```

---

# 7. 실행 결과 확인

```bash
윈도우 브라우저 실행 후 
주소창에 http://client 서버의 ip:8080 으로 접속하여 직원 정보를 등록한다

```
