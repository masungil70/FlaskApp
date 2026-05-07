#1. namespace 생성
kubectl create ns ceph-csi
kubectl create ns ceph-storage

#2. Ceph 계정 및 키 생성를 위한 secret.yaml 파일을 적용합니다.
kubectl apply -f secret.yaml

#3. Helm 설치
helm repo add ceph-csi https://ceph.github.io/csi-charts
helm repo update

helm install ceph-csi-rbd ceph-csi/ceph-csi-rbd  -n ceph-csi


#4. 설치된 ceph-csi-cephfs 리릴리즈를 확인한다.
helm list -n ceph-csi

#5. ceph-csi 네임스페이스에 clusterID와 monitors 정보를 담은 configmap.yaml 파일을 적용한다.
kubectl apply -f configmap.yaml

#6. ConfigMap은 생성된 것 확인 
kubectl get cm -n ceph-csi

#7. StorageClass는 생성
kubectl apply -f storageclass.yaml

#8. StorageClass가 생성된 것 확인
kubectl get sc | grep ceph-rbd

echo "10초 대기 후 MariaDB 설정을 시작합니다."
sleep 10

#9. Install MariaDB Galera Cluster using Helm
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# Install MariaDB Galera with custom values in ceph-storage namespace
helm install mariadb bitnami/mariadb-galera -f galera-values.yaml -n ceph-storage
# mariadb 설치 후 30초 대기
sleep 30

#10. 상태 확인
kubectl get all -n ceph-storage

#11. PVC가 생성된 것 확인 (StatefulSet에 의해 자동 생성됨)
kubectl get pvc -n ceph-storage

echo "MariaDB Galera Cluster and Ceph CSI installation completed successfully!"
echo "60초 대기 후 설치된 리소스들을 확인합니다."
sleep 60

