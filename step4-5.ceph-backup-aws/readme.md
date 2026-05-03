# Hot/Warm/Cold Data 분리 및 S3 하이브리드 백업 아키텍처

이 프로젝트는 온프레미스(Ceph RGW)와 퍼블릭 클라우드(AWS S3)를 혼합하여 비용 효율적이고 안정적인 이미지 관리 시스템을 구현합니다.

## 1. 아키텍처 및 백업 전략

### 저장소 계층화 (Tiering)

| Tier | 의미 | 저장소 | 전략 |
| :--- | :--- | :--- | :--- |
| **Hot** | 최근 7일 이내 생성/조회 | **Ceph RGW (S3)** | 빠른 접근 속도, 로컬 네트워크 활용 |
| **Warm** | 7일 경과 데이터 | **AWS S3 (Standard)** | 가용성 보장 및 로컬 저장 공간 확보 |
| **Cold** | 거의 접근 없는 데이터 | **AWS S3 (Glacier)** | 장기 보관 및 비용 절감 (추후 확장) |

### 백업을 수행하는 이유
1. **비용 최적화**: 모든 데이터를 퍼블릭 클라우드에 두지 않고, 자주 사용하는 데이터는 내부 Ceph(무료)에, 오래된 데이터는 AWS(안정성)에 분산하여 비용을 절감합니다.
2. **저장 공간 관리**: 로컬 스토리지(Ceph)의 용량 한계를 극복하기 위해 오래된 데이터를 클라우드로 이관합니다.
3. **데이터 생명주기 관리**: `last_access_time`을 기준으로 데이터의 가치를 판단하여 최적의 위치로 자동 이동시킵니다.

---

## 2. 구현 방법

### DB 스키마 확장 (`employee` 테이블)
데이터의 위치와 상태를 추적하기 위해 다음 컬럼을 사용합니다.
* `storage_type`: `ceph` 또는 `s3` (저장소 구분)
* `object_key`: 파일명 또는 AWS S3 전체 URI (`s3://bucket/key`)
* `last_access_time`: 마지막 조회 시각 (백업 판단 기준)
* `backup_status`: 백업 완료 여부 (0: 미백업, 1: 완료)

MySQL 테이블 필드 추가 예시:
```sql
ALTER TABLE employee
ADD COLUMN storage_type NVARCHAR(50) DEFAULT 'ceph' NULL COMMENT 'ceph/aws',
ADD COLUMN backup_status TINYINT(1) DEFAULT 0 COMMENT 'backup 여부',
ADD COLUMN upload_time DATETIME NULL COMMENT '업로드 시간',
ADD COLUMN last_access_time DATETIME DEFAULT now() COMMENT '마지막 접근';
```

### 백업 프로세스 (`aws_backup.py`)
1. **대상 추출**: `last_access_time`이 현재 기준 7일 이전이고 `backup_status`가 0인 데이터를 조회합니다.
2. **데이터 이관**: Ceph S3에서 파일을 다운로드하여 AWS S3로 업로드합니다.
3. **로컬 삭제**: 업로드 성공 후 Ceph S3에서 원본 파일을 삭제합니다.
4. **정보 갱신**: DB의 `storage_type`을 `s3`로, `object_key`를 AWS S3 URI 형식으로 업데이트합니다.

---

## 3. 투명한 이미지 처리 (Storage Agnostic Retrieval)

데이터가 Ceph에서 AWS로 이동하더라도 사용자나 다른 서비스는 이를 의식하지 않고 동일한 방식으로 이미지를 조회/삭제할 수 있도록 `photo_service`를 개선했습니다.

### 주요 구현 로직 (`photo_service/app.py`)

*   **동적 클라이언트 라우팅**: 요청된 `object_key`의 접두사를 분석하여 적절한 S3 클라이언트를 선택합니다.
    *   `s3://`로 시작하는 경우: **AWS S3 클라이언트** 사용
    *   일반 UUID 형식인 경우: **Ceph S3 클라이언트** 사용
*   **경로 처리 최적화**: S3 URI에 포함된 슬래시(`/`)를 경로 매개변수로 올바르게 인식하도록 FastAPI 설정을 보완했습니다. (`/photos/{object_key:path}`)
*   **멀티 자격 증명 관리**: 한 서비스 내에서 Ceph와 AWS의 인증 정보를 동시에 관리하여 중단 없는 서비스를 제공합니다.

### 조회의 흐름
1. 사용자가 이미지 요청 -> `gateway` -> `photo_service`.
2. `photo_service`가 DB에서 넘어온 키를 확인.
3. AWS URI라면 AWS에서, 일반 키라면 Ceph에서 Presigned URL 생성 후 리다이렉트.
4. **결과**: 사용자는 데이터의 실제 위치에 상관없이 항상 이미지를 볼 수 있습니다.

---

## 4. 실행 및 확인

### 컨테이너 빌드 및 실행
```bash
docker compose up -d --build
```

### DB 상태 확인
```sql
-- 백업된 데이터와 현재 Ceph에 있는 데이터 확인
SELECT full_name, storage_type, object_key FROM employees.employee;
```
