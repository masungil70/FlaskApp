#ceph 3s를 구성하고 사진 첨부 파일을 ceph 3s 저장할 수 있게 수정된 버전 


VMware 환경에서 Ceph 기반 S3(Object Storage)를 구현하는 가장 일반적인 구조는 다음과 같습니다.

* VMware Workstation pro 또는 vSphere 위에 Linux VM 생성
* VM 내부에 Ceph Cluster 구축
* Ceph Object Gateway(RGW) 활성화
* S3 API 제공
* MinIO 대체 또는 AWS S3 호환 저장소로 사용

실무에서는 다음 2가지 방식이 가장 많습니다.

1. “테스트/교육용” 단일 노드 Ceph-S3
2. “운영용” 3~5노드 Ceph Cluster + RGW

아래는 VMware 기반 실무형 구조입니다.

---

# 1. 전체 구조

```text
             ┌───────────────────────────────┐
             │ VMware Workstation Pro/vSphere│
             └────────────────┬──────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
 ┌───────▼────────┐ ┌────────▼────────┐ ┌────────▼────────┐
 │ ceph-node1 VM  │ │ ceph-node2 VM   │ │ ceph-node3 VM   │
 │ MON + MGR + OSD│ │ MON + OSD       │ │ MON + OSD       │
 └───────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         └───────────────────┴───────────────────┘
                             │
                     ┌───────▼────────┐
                     │ Ceph RGW (S3)  │
                     │ port : 7480    │
                     └───────┬────────┘
                             │
                   S3 API Endpoint 제공
                             │
          http://ceph-rgw:7480
```

---

# 2. VMware VM 구성 권장 사항

테스트 환경 기준:

| 항목      | 권장                          |
| ------- | --------------------------- |
| VM 수    | 3대                          |
| OS      | Ubuntu 22.04                |
| vCPU    | 4Core 이상                    |
| RAM     | 8GB 이상                      |
| Disk    | OS 40GB + OSD Disk 50GB 이상 |
| Network | 1G 이상                       |

운영 환경:

| 항목               | 권장       |
| ---------------- | -------- |
| NIC              | 10G 이상   |
| OSD Disk         | SSD/NVMe |
| WAL/DB           | 별도 NVMe  |
| VM Anti-affinity | 필수       |
| Jumbo Frame      | MTU 9000 |

---

# 3. VMware VM 생성

VMware에서 VM 생성 시:

## OS Disk

```text
40GB
```

## OSD Disk 추가

가상머신 선택 -> Settings -> Add -> Hard Disk -> SCSI -> Create a new virtual disk ->  용량 (50GB~1TB) 확인하여 disk을 추가합니다

Ceph 저장용 디스크:

```text
50GB~1TB
```

예:

```text
/dev/sdb
/dev/sdc
```

---

# 4. Ubuntu 기본 설정시 반드시 root로 진행 해주세요

모든 노드 공통:

## hostname 설정

node1:

```bash
hostnamectl set-hostname ceph1
```

node2:

```bash
hostnamectl set-hostname ceph2
```

node3:

```bash
hostnamectl set-hostname ceph3
```

---

## hosts 설정(모든 모드에서 진행 합니다)

```bash
cat <<EOF >> /etc/hosts
192.168.80.140 ceph1
192.168.80.141 ceph2
192.168.80.142 ceph3
EOF
```

---

# 5. Ceph 설치

가장 쉬운 방법:

## 모든 노드에서:

```bash
apt update

apt install -y \
podman \
lvm2 \
chrony \
curl \
docker.io

```

# cephadm 사용 (추천)

## cephadm 설치

ceph1에서:

```bash
apt update

curl --silent --remote-name \
https://download.ceph.com/rpm-reef/el9/noarch/cephadm

chmod +x cephadm
mv cephadm /usr/local/bin/
```

---

# 6. Bootstrap

```bash
cephadm bootstrap \
  --mon-ip 192.168.80.140
```

성공 시:

관리자 계정 비밀번호 변경

```bash

# ceph 관리자 셀로 집입합니다 
# 반드시 root로 진행 해주세요

cephadm shell

# 1. 비밀번호 파일생성
echo "kosa1004" > /root/pass.txt

# 2. 사용자 생성
ceph dashboard ac-user-create admin administrator -i /root/pass.txt

# 3. 사용자 비밀번호 변경 
ceph dashboard ac-user-set-password admin -i /root/pass.txt

```

## 웹 브라우저 ceph 관리하기

```text
Dashboard URL:
https://ceph1:8443
```

로그인은 위 계정과 비밀번호를 사용하여 접속하면 됩니다

---

# 7. 노드 추가

SSH Key 생성 ceph1에서:

```bash
ssh-keygen -t rsa -b 4096

```

cephadm SSH Key 생성 (ceph1에서 실행:)

```bash
ceph cephadm generate-key
ssh-keygen -t rsa -b 4096 -f /etc/ceph/ceph -N ""
```

배포:

```bash
ssh-copy-id root@ceph2
ssh-copy-id root@ceph3

# cephadm에 private key 등록
ceph config-key set mgr/cephadm/ssh_identity_key -i /etc/ceph/ceph
# cephadm에 공개키도 등록
ceph config-key set mgr/cephadm/ssh_identity_pub -i /etc/ceph/ceph.pub


ssh-copy-id -f -i /etc/ceph/ceph.pub root@ceph2
ssh-copy-id -f -i /etc/ceph/ceph.pub root@ceph3

cat /etc/ceph/ceph.pub을 내용을 ceph2, ceph3의 /root/.ssh/authorized_keys에 마지막 위치에 추가해줍니다 
 
ceph orch restart mgr

```

---

## 노드 등록

```bash
ceph orch host add ceph2 192.168.80.141
ceph orch host add ceph3 192.168.80.142
```

---

# 8. OSD 생성

디스크 확인:

```bash
lsblk
```

예:

```text
sdb
sdc
```

OSD 생성:

```bash
ceph orch daemon add osd ceph1:/dev/sdb
ceph orch daemon add osd ceph2:/dev/sdb
ceph orch daemon add osd ceph3:/dev/sdb
```

---

# 9. Ceph 상태 확인

```bash
ceph -s
```

정상 예시:

```text
HEALTH_OK
```

---

# 10. S3(Object Gateway) 구성

Ceph RGW 설치:

```bash
ceph orch apply rgw s3 \
  --placement="3 ceph1 ceph2 ceph3"
```

---

# 11. RGW 포트 확인

```bash
ceph orch ps
```

보통:

```text
7480
```

---

# 12. S3 User 생성

```bash
radosgw-admin user create \
  --uid=kosa \
  --display-name="s3 user kosa"
```

결과:

```json
{
  "keys": [
    {
        "user": "kosa",
        "access_key": "BGQCBZ6ITRDPD17VLKQ3",
        "secret_key": "br33jw830MktvJ5ZOuUIO3PlPOI7WU4ixWHoRB8F"  
    }
  ]
}
```

이 키가 AWS S3 API Key 역할입니다.

---

# 13. AWS CLI 설치

Client PC 에서 진행:

```bash id="w108"
#최신 버전의 aws cli을 다운로드합니다 
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"

#unzip 패키지를 설치합니다 
sudo apt install -y unzip

# awscliv2.zip 압축 파일을 현재 폴더에 풀어줍니다 
unzip awscliv2.zip

# awscliv2설치합니다 
sudo ./aws/install

.profile 파일의 PATH에 /usr/local/bin 경로를 추가합니다 

vi ~/.profile
...
#마직막 출에 아래 내용 추가해줍니다 
export PATH=$PATH:/usr/local/bin


#저장하고 설정해줍니다 

. ~/.profile

```

---

# 14. S3 연결 테스트

```bash
aws configure
```

입력:

| 항목       | 값              |
| ---------- | -------------- |
| Access Key | 생성된 access_key |
| Secret Key | 생성된 secret_key |
| Region     | ap-northeast-2    |
| Output     | json           |

Ceph-S3 endpoint 사용

중요:

```bash id="w110"
aws --endpoint-url http://192.168.80.140 s3 ls
```

---

# 15. Bucket 생성

```bash id="w111"
# 리전 환경 변수 제거
unset AWS_DEFAULT_REGION

# mybucket 생성 
/usr/local/bin/aws \
  --endpoint-url http://192.168.80.140 \
  s3api create-bucket \
  --bucket mybucket
```

---

# 16. Bucket 확인

```bash id="w112"
/usr/local/bin/aws --endpoint-url http://192.168.80.140 s3 ls
```

---

# 17. 파일 업로드

```bash id="w113"
echo hello > test.txt
```

```bash id="w114"
aws --endpoint-url http://192.168.80.140 s3 cp test.txt s3://mybucket/
```

---

# 18. 다운로드 테스트

```bash id="w115"
#test.txt 파일 삭제 
rm test.txt

#cehp s3에 저장된 test.txt를 현재 폴더로 복사합니다   
aws --endpoint-url http://192.168.80.140 s3 cp s3://mybucket/test.txt .

#다운받은 파일을 확인 합니다 
cat test.txt
hello

```
---

# 19. mybucket 목록 확인

```
aws --endpoint-url http://192.168.80.140 s3 ls mybucket

2026-05-02 23:19:13          6 test.txt

```
---

# 20. 프로젝트 실행

1. ceph 아닌 다른 vm에서 실행합니다
2. docker를 설치합니다.
3. docker compose -d up 으로 실행합니다
4. 실행중인 vm 의 ip 를 확인합니다 
5. 윈도우에서 vm의 ip : 8080으로 접속하여 직원 정보를 등록해봅니다 
6. ceph의 버킷에 등록된 파일 목록을 확인입니다.

---

# 21. 실행

```bash
docker compose up -d

# ip 주소 확인 
ip a
```

---

# 22. 실행 결과 확인

```bash
윈도우 브라우저 실행 후 
주소창에 http://client 서버의 ip:8080 으로 접속하여 직원 정보를 등록한다

```
