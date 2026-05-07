#!/bin/bash

set +e

echo "========================================="
echo " Ceph CSI Cleanup Start"
echo "========================================="

#########################################
# 1. Helm Release 제거
#########################################

helm uninstall ceph-csi-rbd -n ceph-csi --wait=false 2>/dev/null || true
helm uninstall ceph-csi-cephfs -n ceph-csi --wait=false 2>/dev/null || true

#########################################
# 2. ceph-csi namespace 강제 삭제
#########################################

kubectl delete ns ceph-csi \
  --force \
  --grace-period=0 \
  --wait=false 2>/dev/null || true

#########################################
# 3. ceph-storage 리소스 강제 제거
#########################################

if kubectl get ns ceph-storage >/dev/null 2>&1; then

  echo "[INFO] Delete Deployments"

  kubectl delete deployment --all \
    -n ceph-storage \
    --force \
    --grace-period=0 \
    --wait=false 2>/dev/null || true

  echo "[INFO] Delete DaemonSets"

  kubectl delete daemonset --all \
    -n ceph-storage \
    --force \
    --grace-period=0 \
    --wait=false 2>/dev/null || true

  echo "[INFO] Delete StatefulSets"

  kubectl delete statefulset --all \
    -n ceph-storage \
    --force \
    --grace-period=0 \
    --wait=false 2>/dev/null || true

  echo "[INFO] Delete Pods"

  for pod in $(kubectl get pod -n ceph-storage -o name 2>/dev/null); do

    kubectl patch $pod -n ceph-storage \
      -p '{"metadata":{"finalizers":[]}}' \
      --type=merge 2>/dev/null || true

    kubectl delete $pod -n ceph-storage \
      --force \
      --grace-period=0 \
      --wait=false 2>/dev/null || true

  done

  #########################################
  # 4. PVC finalizer 제거
  #########################################

  echo "[INFO] Remove PVC Finalizers"

  for pvc in $(kubectl get pvc -n ceph-storage -o name 2>/dev/null); do

    kubectl patch $pvc -n ceph-storage \
      -p '{"metadata":{"finalizers":[]}}' \
      --type=merge 2>/dev/null || true

    kubectl delete $pvc -n ceph-storage \
      --force \
      --grace-period=0 \
      --wait=false 2>/dev/null || true

  done

fi

#########################################
# 5. PV finalizer 제거
#########################################

echo "[INFO] Remove PV Finalizers"

for pv in $(kubectl get pv -o name 2>/dev/null); do

  kubectl patch $pv \
    -p '{"metadata":{"finalizers":[]}}' \
    --type=merge 2>/dev/null || true

  kubectl delete $pv \
    --force \
    --grace-period=0 \
    --wait=false 2>/dev/null || true

done

#########################################
# 6. CSI Driver 제거
#########################################

echo "[INFO] Delete CSI Driver"

kubectl delete csidriver rbd.csi.ceph.com \
  --wait=false 2>/dev/null || true

kubectl delete csidriver cephfs.csi.ceph.com \
  --wait=false 2>/dev/null || true

#########################################
# 7. StorageClass 제거
#########################################

echo "[INFO] Delete StorageClass"

kubectl delete -f storageclass.yaml \
  --wait=false 2>/dev/null || true

#########################################
# 8. ceph-storage namespace 삭제
#########################################

echo "[INFO] Delete Namespace"

kubectl delete ns ceph-storage \
  --force \
  --grace-period=0 \
  --wait=false 2>/dev/null || true

#########################################
# 9. namespace terminating 강제 제거
#########################################

sleep 2

kubectl get namespace ceph-storage -o json 2>/dev/null \
| tr -d "\n" \
| sed 's/"finalizers": \[[^]]\+\]/"finalizers": []/' \
| kubectl replace --raw "/api/v1/namespaces/ceph-storage/finalize" -f - \
2>/dev/null || true

kubectl get namespace ceph-csi -o json 2>/dev/null \
| tr -d "\n" \
| sed 's/"finalizers": \[[^]]\+\]/"finalizers": []/' \
| kubectl replace --raw "/api/v1/namespaces/ceph-csi/finalize" -f - \
2>/dev/null || true


echo ""
echo "========================================="
echo " 정리작업이 완료되었습니다"
echo "========================================="
