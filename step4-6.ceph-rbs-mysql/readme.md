# **“Ceph + Kubernetes + RBD CSI 운영 구조”**

# 🧠 0. 전체 구조

```text id="ceph_cluster"
ceph1 = MON + MGR + OSD + RGW (core)
ceph2 = MON + OSD
ceph3 = MON + OSD
```

그리고 Kubernetes는 보통:

```text id="k8s_cluster"
k8s-master = control plane
k8s-node1~n = worker
```

---

# 🚀 1. 작업 위치 정리

## 🟢 Ceph 서버에서 하는 작업

👉 반드시 **ceph1 (또는 ceph CLI 가능한 노드)**

| 작업           | 서버  |
| ------------   | ----- |
| RBD pool 생성  | ceph1 |
| Ceph user 생성 | ceph1 |
| auth key 생성  | ceph1 |

---

## 🟡 Kubernetes master에서 하는 작업

👉 반드시 **k8s-master**

| 작업                   | 서버       |
| --------------------   | ---------- |
| CSI driver 설치        | k8s-master |
| StorageClass 생성      | k8s-master |
| PVC 생성               | k8s-master |
| Deployment (MySQL 등)  | k8s-master |

---

## 🔵 Kubernetes 모든 node에서 하는 작업

| 작업              | 서버      |
| ----------------- | -------   |
| ceph-common 설치  | 모든 node |
| rbd kernel module | 모든 node |

---

# ⚙️ STEP 1: Ceph (ceph1) 설정

## 1-1 RBD Pool 생성

```bash id="ceph_pool"
ceph osd pool create kube_rbd 32
ceph osd pool set kube_rbd size 3
rbd pool init kube_rbd
```

---

## 1-2 Kubernetes용 Ceph 사용자 생성

```bash id="ceph_user"
ceph auth get-or-create client.k8s \
mon 'profile rbd' \
osd 'profile rbd' \
mgr 'profile rbd' \
-o /etc/ceph/ceph.client.k8s.keyring
```

---

## 1-3 key 추출 (K8s용)

```bash id="ceph_key"
ceph auth get-key client.k8s

출력:
AQDJvPhpUQ2VIxAAZwcc/FCU3gs2L71i5tMQQw==
```

👉 이 값을 복사 (다음 단계에서 사용)

---

# ⚙️ STEP 2: Kubernetes Node 준비

## 📌 서버: k8s-master + all nodes

---

## 2-1 Ceph client 설치 (모든 node)

```bash id="node_install"
apt update
apt install -y ceph-common
```

---

## 2-2 rbd kernel module 확인

```bash id="rbd_mod"
modprobe rbd
lsmod | grep rbd
```

---

# ⚙️ STEP 3: Kubernetes Secret 생성

계정 아이디와 키를 Secret 객체로 생성해야 합니다.

## 📌 서버: k8s-master

---

## 3-1 base64 key 생성

```bash id="base64"
echo -n "k8s" | base64

결과 : 
azhz

---

echo -n "AQDJvPhpUQ2VIxAAZwcc/FCU3gs2L71i5tMQQw==" | base64

결과 : 
QVFEdk5QdHB3cTVlRUJBQTIyZWk2dVp4dTRDL01RUW9rR1c2ekE9PQ==

```

---

## 3-2 Secret YAML

vi secret.yaml

```yaml id="secret_yaml"
apiVersion: v1
kind: Secret
metadata:
  name: ceph-secret
  namespace: ceph-storage
type: Opaque
data:
# base64 k8s: echo -n "k8s" | base64  
# base64 k8s의  key : echo -n "k8s-key" | base64
  userID: azhz
  userKey: QVFEdk5QdHB3cTVlRUJBQTIyZWk2dVp4dTRDL01RUW9rR1c2ekE9PQ==
      
```

---

```bash id="apply_secret"
kubectl apply -f secret.yaml
```

---

# ⚙️ STEP 4: StorageClass 생성

## 📌 서버: k8s-master

vi storageclass.yaml

```yaml id="storageclass_yaml"
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ceph-rbd
provisioner: rbd.csi.ceph.com
parameters:
  clusterID: 36edd2cc-4621-11f1-9004-a7cd2b580b3e
  pool: kube_rbd
  imageFormat: "2"
  imageFeatures: layering

  csi.storage.k8s.io/provisioner-secret-name: ceph-secret
  csi.storage.k8s.io/provisioner-secret-namespace: ceph-storage
  csi.storage.k8s.io/node-stage-secret-name: ceph-secret
  csi.storage.k8s.io/node-stage-secret-namespace: ceph-storage

reclaimPolicy: Delete
allowVolumeExpansion: true
volumeBindingMode: Immediate
mountOptions:
  - discard

```

```bash id="apply_sc"
kubectl apply -f storageclass.yaml
```

---

# ⚙️ STEP 5: PVC 생성

## 📌 서버: k8s-master

vi pvc.yaml

```yaml id="pvc_yaml"
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: mysql-pvc
  namespace: ceph-storage
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: ceph-rbd
  resources:
    requests:
      storage: 10Gi

```

```bash id="apply_pvc"
kubectl apply -f pvc.yaml
```

---

# ⚙️ STEP 6: MySQL 배포

## 📌 서버: k8s-master에서 진행

## mysql root 비밀번호 secret으로 생성

### 비밀번호 생성 절차

```bash
echo -n "kosa1004" | base64

결과:
a29zYTEwMDQ=
```

vi mysql-secret.yaml

```yaml id="mysql-secret.yaml"
apiVersion: v1
kind: Secret
metadata:
  name: mysql-secret
  namespace: ceph-storage
type: Opaque
data:
  MYSQL_ROOT_PASSWORD: a29zYTEwMDQ=     # kosa1004

```

### 비밀번호 secret 객체 생성

```bash
kubectl apply -f mysql-secret.yaml
```

---

## mysql deployment  파일 생성

vi mysql-deploy.yaml

```yaml id="mysql-deploy.yaml"
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mysql
  namespace: ceph-storage
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mysql
  strategy:
    type: Recreate
  template:
    metadata:
      labels:
        app: mysql
    spec:
      containers:
        - name: mysql
          image: mysql:8.0
          args:
            - "--default-authentication-plugin=mysql_native_password"
          envFrom:
            - secretRef:
                name: mysql-secret
          ports:
            - containerPort: 3306
          volumeMounts:
            - name: mysql-storage
              mountPath: /var/lib/mysql
      volumes:
        - name: mysql-storage
          persistentVolumeClaim:
            claimName: mysql-pvc

```

### deployment 생성

```bash id="apply_mysql"
kubectl apply -f mysql-deploy.yaml
```

## 외부접속을 위한 서비스  파일 생성

```bash
apiVersion: v1
kind: Service
metadata:
  name: mysql
  namespace: ceph-storage
spec:
  selector:
    app: mysql
  ports:
    - port: 3306
      targetPort: 3306

```

## 외부접속을 위한 서비스 생성

```bash id="apply_service"
kubectl apply -f mysql-service.yaml
```

---

## 일괄 생성

```bash
bash install.sh 
```

## 일괄 삭제

```bash
bash clean.sh 
```

---

# 💥 최종 구조

```text id="final"
MySQL Pod
   ↓
PVC
   ↓
RBD CSI Driver
   ↓
Ceph RBD Pool
   ↓
Ceph Cluster (3 nodes)
```

---
