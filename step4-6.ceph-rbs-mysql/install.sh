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

echo "10초 대기 후 PVC를 생성합니다."
sleep 10

#9. PVC 생성
kubectl apply -f pvc.yaml

echo "5초 대기 후 mysql-secret.yaml 파일을 적용합니다."
sleep 5

#10. mysql root 비밀번호를 mysql-secret.yaml 파일을 적용한다.
kubectl apply -f mysql-secret.yaml

#11. mysql-deploy.yaml 파일을 적용한다.
kubectl apply -f mysql-deploy.yaml

#12. mysql-secret.yaml 파일이 적용된 것 확인
kubectl apply -f mysql-service.yaml

echo "5초 대기 후 ceph-storage 네임스페이스를 확인합니다."
sleep 5

#13. mysql-deploy.yaml 파일이 적용된 것 확인
kubectl get all -n ceph-storage

#14. PVC가 생성된 것 확인
kubectl get pvc -n ceph-storage

#15. 서비스의 아이피와 포트 확인 확인하고 mysql에 접속한다.
echo "mysql -h <서비스의 아이피> -P <서비스의 포트> -u root -p"

