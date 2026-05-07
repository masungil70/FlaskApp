#!/bin/bash

set +e

echo "========================================="
echo " MariaDB Galera & Ceph CSI Cleanup Start"
echo "========================================="

#########################################
# 1. MariaDB Galera Cluster 리소스 제거
#########################################
echo "[INFO] Delete MariaDB Galera Resources"

# Helm Release 삭제
helm uninstall mariadb -n ceph-storage --wait=false 2>/dev/null || true

# 이름 기반으로 서비스 명시적 삭제 (라벨이 다르거나 Helm에서 관리되지 않는 경우 대비)
kubectl delete service mariadb mariadb-headless mysql -n ceph-storage --ignore-not-found=true

# Helm 삭제 후에도 남을 수 있는 리소스들 라벨 기반으로 삭제
kubectl delete all -l app.kubernetes.io/name=mariadb-galera -n ceph-storage --ignore-not-found=true
kubectl delete all -l app=mariadb -n ceph-storage --ignore-not-found=true
kubectl delete all -l app=mysql -n ceph-storage --ignore-not-found=true
kubectl delete pvc -l app.kubernetes.io/name=mariadb-galera -n ceph-storage --ignore-not-found=true
kubectl delete configmap -l app.kubernetes.io/name=mariadb-galera -n ceph-storage --ignore-not-found=true
kubectl delete secret -l app.kubernetes.io/name=mariadb-galera -n ceph-storage --ignore-not-found=true

#########################################
# 2. Helm Release 제거 (Ceph CSI)
#########################################
echo "[INFO] Uninstall Ceph CSI Helm Charts"
helm uninstall ceph-csi-rbd -n ceph-csi --wait=false 2>/dev/null || true
helm uninstall ceph-csi-cephfs -n ceph-csi --wait=false 2>/dev/null || true

#########################################
# 3. ceph-csi namespace 및 관련 리소스 제거
#########################################
echo "[INFO] Delete Ceph CSI Config & StorageClass"
kubectl delete -f configmap.yaml --ignore-not-found=true
kubectl delete -f storageclass.yaml --ignore-not-found=true
kubectl delete -f secret.yaml --ignore-not-found=true

#########################################
# 4. ceph-storage namespace 내 남은 리소스 강제 제거
#########################################
if kubectl get ns ceph-storage >/dev/null 2>&1; then
  echo "[INFO] Force Cleaning ceph-storage namespace"
  
  # 남은 포드들 강제 삭제
  for pod in $(kubectl get pod -n ceph-storage -o name 2>/dev/null); do
    kubectl patch $pod -n ceph-storage -p '{"metadata":{"finalizers":[]}}' --type=merge 2>/dev/null || true
    kubectl delete $pod -n ceph-storage --force --grace-period=0 --wait=false 2>/dev/null || true
  done

  # 남은 PVC들 강제 삭제 (혹시 남아있을 경우)
  for pvc in $(kubectl get pvc -n ceph-storage -o name 2>/dev/null); do
    kubectl patch $pvc -n ceph-storage -p '{"metadata":{"finalizers":[]}}' --type=merge 2>/dev/null || true
    kubectl delete $pvc -n ceph-storage --force --grace-period=0 --wait=false 2>/dev/null || true
  done
fi

#########################################
# 5. PV 강제 제거
#########################################
echo "[INFO] Remove Remaining PVs"
for pv in $(kubectl get pv -o name 2>/dev/null); do
  # Ceph RBD 관련 PV만 선택적으로 삭제하거나 전체 삭제 (상황에 따라 조절)
  kubectl patch $pv -p '{"metadata":{"finalizers":[]}}' --type=merge 2>/dev/null || true
  kubectl delete $pv --force --grace-period=0 --wait=false 2>/dev/null || true
done

#########################################
# 6. Namespace 삭제
#########################################
echo "[INFO] Delete Namespaces"
kubectl delete ns ceph-storage --force --grace-period=0 --wait=false 2>/dev/null || true
kubectl delete ns ceph-csi --force --grace-period=0 --wait=false 2>/dev/null || true

# Namespace가 Terminating 상태에서 멈추는 경우를 대비한 finalizer 제거
sleep 2
for ns in ceph-storage ceph-csi; do
  kubectl get namespace $ns -o json 2>/dev/null \
  | tr -d "\n" \
  | sed 's/"finalizers": \[[^]]\+\]/"finalizers": []/' \
  | kubectl replace --raw "/api/v1/namespaces/$ns/finalize" -f - \
  2>/dev/null || true
done

echo ""
echo "========================================="
echo " MariaDB Galera Cluster 정리 완료"
echo "========================================="
