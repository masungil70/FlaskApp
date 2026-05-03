# Docker Compose에서 **MariaDB(MySQL) 데이터를 Ceph 저장소로 사용**하려면 핵심은 “컨테이너 볼륨을 Ceph 기반 볼륨으로 바꾸는 것”입니다.

## **CephFS 클라이언트 구성**

Ceph에서 CephFS는 RBD/S3와 다르게 **클라이언트 마운트 준비 작업**이 따로 필요합니다.

---

## 0. 사전 준비 작업

1. 아래의 모든 작업은 ceph 1의 모드에서 진행합니다.
2. root 권한으로 진행합니다.
3. cephamd shell로 진행합니다.

```bash
sudo su -
cephamd shell
```

---

## 1. CephFS 기본 구성 확인 (필수)

먼저 파일시스템이 존재해야 합니다.

```bash
ceph fs ls
```

없으면 생성:

```bash
ceph fs volume create cephfs
```

또는 legacy 방식:

```bash
ceph fs new cephfs cephfs_metadata cephfs_data
```

ceph 상태를 확인합니다(중간 중간 확인 필요)

```
ceph -s
```

결과 (HEALTH_OK 상태인지  확인 필요) :
...

health: HEALTH_OK
...


---

## 2. MDS 확인 (필수)

Ceph에서 MDS (Metadata Server) 는 CephFS(파일 시스템)를 구성할 때 핵심 역할을 하는 “메타데이터 전용 서버”입니다.
CephFS는 MDS가 반드시 필요합니다.

### 1. MDS란 무엇인가?

MDS = Metadata Server

CephFS에서:

- 파일 이름
- 디렉토리 구조
- 권한 (permission)
- 파일 위치 정보

같은 “파일의 정보(메타데이터)”만 관리하는 서버입니다.

```bash
ceph orch ps | grep mds
```

없으면 배포:

```bash
ceph orch apply mds cephfs --placement="ceph1,ceph2,ceph3"
```

---

## 3. 클라이언트 패키지 설치 (클라이언트 PC / VM)

Ubuntu 기준:

```bash
sudo apt update
sudo apt install -y ceph-common 
```

👉 여기서 중요한 포인트:

* `ceph-common` = CephFS / RBD / S3 client tool 포함

---

## 4. 인증 키 생성 (필수)

ceph 1의 root 계정으로 cephadm shell 실행 환경에서 진행 :

```bash

ceph auth get-or-create client.fs \
mon 'allow r' \
mds 'allow rw fsname=cephfs path=/' \
osd 'allow rw tag cephfs data=cephfs'

#결과:
[client.fs]
        key = AQB...

```

결과 파일 확인

```text
ceph auth get client.fs

[client.fs]
        key = AQB...
        caps mds = "allow rw fsname=cephfs"
        caps mon = "allow r fsname=cephfs"
        caps osd = "allow rw tag cephfs data=cephfs"

```

계정 삭제 방법 후 위 계정 생성 다시 시작 할 수 있음

```bash
ceph auth del client.fs
```

---

## 5. Ceph config 전달 Client에 전달

ceph 1의 root 계정으로 cephadm shell 실행 환경에서 진행 :

```bash
scp /etc/ceph/ceph.conf root@client:/etc/ceph/

#키 얻기 확인 하고 client에 전달합니다 
ceph auth get client.fs 

scp /etc/ceph/ceph.client.fs.keyring root@client:/etc/ceph/
```

client 에서 /etc/ceph/ceph.client.fs.keyring 생성
```bash
vi /etc/ceph/ceph.client.fs.keyring
[client.fs]
        key = AQB...


vi /etc/ceph/ceph.client.fs.secret
AQB...

```

---

## 6. 클라이언트에서 마운트

```bash
# 마운트 폴더 생성 
mkdir /mnt/cephfs
chmod 777 /mnt/cephfs
chown nobody:nogroup /mnt/cephfs

# ceph 마운트을 합니다 
sudo mount -t ceph :/ /mnt/cephfs \
-o name=fs,secretfile=/etc/ceph/ceph.client.fs.secret

```

---

## 8. 정상 확인

```bash
df -h | grep ceph

192.168.80.140:6789,192.168.80.141:6789,192.168.80.142:6789:/   48G  188M   47G   1% /mnt/cephfs
```

3대 서버가 50G로 구성되고 복제본이 3개으로 48G로 표시됩니다


또는 파일 생성 후 확인

```bash
touch /mnt/cephfs/test.txt

ls -l /mnt/cephfs/test.txt

```

---

## 9. 자동 마운트 설정

### 1) mount 디렉토리 생성

```bash id="r105"
sudo mkdir -p /mnt/cephfs
```

---

### 2) /etc/fstab 설정

```bash id="r106"

192.168.80.140:6789,192.168.80.141:6789,192.168.80.142:6789:/  /mnt/cephfs  ceph  name=fs,secretfile=/etc/ceph/ceph.client.fs.secret,fs=cephfs,_netdev,noatime  0  0
```

✔️ 옵션 설명

- name=fs → Ceph client key 이름
- secretfile=... → 인증 키
- fs=cephfs → 파일시스템 이름
- _netdev → 네트워크 올라온 뒤 마운트
- noatime → 성능 최적화

---

### 3) reboot 테스트

```bash id="r112"
sudo reboot
```

부팅 후:

```bash id="r113"
df -h | grep ceph

#결과 : 
192.168.80.140:6789,192.168.80.141:6789,192.168.80.142:6789:/   48G  188M   47G   1% /mnt/cephfs

```

---

## 10. 구조 이해

CephFS는 이렇게 동작합니다:

```
Client
  ↓
MDS (metadata)
  ↓
OSD (data storage)
```

---

## 11. S3와 차이

| 항목            | S3 (RGW)       | CephFS       |
| ------------- | -------------- | ------------ |
| 접근 방식         | HTTP API       | POSIX FS     |
| 사용            | Object Storage | File Storage |
| Kubernetes    | S3 backend     | PVC storage  |
| Docker volume | X              | O            |

---

## 12. CephFS 방식을 Docker에 bind mount 방식이 연결 (권장)

## 🔧 docker-compose 수정 (db 서비스만 변경)

```yaml
  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: kosa1004
      MYSQL_DATABASE: employees
    ports:
      - "3306:3306"
    volumes:
      - /mnt/cephfs/mysql-data:/var/lib/mysql
      - ./employee_server/database_create_tables.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - app-network
```

---

## 13. 실행

```bash
docker compose up -d

# ip 주소 확인 
ip a
```

## 14. 실행 결과 확인

```bash
윈도우 브라우저 실행 후 
주소창에 http://client 서버의 ip:8080 으로 접속하여 직원 정보를 등록한다


```
