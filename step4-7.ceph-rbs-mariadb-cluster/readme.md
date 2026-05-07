# **“Ceph + Kubernetes + RBD CSI 운영 구조 (MariaDB Galera Cluster)”**

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
| MariaDB Galera 설정    | k8s-master |

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

# ⚙️ STEP 3: Kubernetes Secret 생성 (Ceph용)

계정 아이디와 키를 Secret 객체로 생성해야 합니다.

## 📌 서버: k8s-master

---

## 3-1 base64 key 생성

```bash id="base64"
echo -n "k8s" | base64
# 결과 : azhz

echo -n "AQDJvPhpUQ2VIxAAZwcc/FCU3gs2L71i5tMQQw==" | base64
# 결과 : QVFEdk5QdHB3cTVlRUJBQTIyZWk2dVp4dTRDL01RUW9rR1c2ekE9PQ==
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

# ⚙️ STEP 5: MariaDB Galera Cluster 배포 (Helm)

## 📌 서버: k8s-master에서 진행

MariaDB Galera Cluster는 Bitnami Helm 차트를 사용하여 배포하며, `galera-values.yaml` 설정 파일에 정의된 대로 **3대**의 노드로 구성됩니다. 각 노드는 `ceph-rbd` StorageClass를 통해 독립적인 볼륨을 할당받습니다.

## 5-1 Helm 레포지토리 추가 및 업데이트

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
```

---

## 5-2 MariaDB Galera Cluster 설치

`galera-values.yaml` 파일을 사용하여 `ceph-storage` 네임스페이스에 설치합니다.

```bash id="apply_mariadb"
helm install mariadb bitnami/mariadb-galera \
  -n ceph-storage \
  -f galera-values.yaml
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
MariaDB Galera Cluster (3 Pods)
   ↓
PVCs (Individual RBD per Pod via volumeClaimTemplates)
   ↓
RBD CSI Driver
   ↓
Ceph RBD Pool
   ↓
Ceph Cluster (3 nodes)
```
