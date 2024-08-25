# mongodb-backup

用于备份数据库、备份清理、备份恢复

- 支持保留备份数
- 支持全量备份
- 支持单数据库备份
- 支持单集合备份
- 支持忽略若干集合备份
- 支持选择备份恢复
- 支持加密备份

## Quick Start

支持三种方式使用

- 命令行
- docker
- helm chart

### 使用命令行

全量数据库备份和恢复

```shell
# 使用文件备份
MONGO_URI=mongodb://username:password@192.168.1.20 BACKUP_PATH=./backup FILE_PREFIX=tmp python docker/backup.py
# 启用 s3 备份
MONGO_URI=mongodb://username:password@192.168.1.20 BACKUP_PATH=./backup FILE_PREFIX=tmp S3_ENABLE=1 S3_EP="https://minio-api.36node.com" S3_ACCESS_KEY="xxxx" S3_ACCESS_SECRET="xxxx" S3_BUCKET="test" S3_PREFIX="prefix" python docker/backup.py

# 使用文件恢复
MONGO_URI=mongodb://username:password@192.168.1.21 BACKUP_PATH=./backup python docker/restore.py
# 使用 s3 恢复
MONGO_URI=mongodb://username:password@192.168.1.21 RESTORE_FROM_S3=1 S3_EP="https://minio-api.36node.com" S3_ACCESS_KEY="xxxx" S3_ACCESS_SECRET="xxxx" S3_BUCKET="test" S3_PREFIX="prefix" python docker/restore.py
```

单个数据库备份和恢复

```shell
# 使用文件备份
MONGO_URI=mongodb://username:password@192.168.1.20/some-db?authSource=admin BACKUP_PATH=./backup python docker/backup.py
# 启用 s3 备份
MONGO_URI=mongodb://username:password@192.168.1.20/some-db?authSource=admin BACKUP_PATH=./backup FILE_PREFIX=tmp S3_ENABLE=1 S3_EP="https://minio-api.36node.com" S3_ACCESS_KEY="xxxx" S3_ACCESS_SECRET="xxxx" S3_BUCKET="test" S3_PREFIX="prefix" python docker/backup.py

# 使用文件恢复
MONGO_URI=mongodb://username:password@192.168.1.21/some-db?authSource=admin BACKUP_PATH=./backup python docker/restore.py
# 使用 s3 恢复
MONGO_URI=mongodb://username:password@192.168.1.21/some-db?authSource=admin RESTORE_FROM_S3=1 S3_EP="https://minio-api.36node.com" S3_ACCESS_KEY="xxxx" S3_ACCESS_SECRET="xxxx" S3_BUCKET="test" S3_PREFIX="prefix" python docker/restore.py
```

备份时忽略某些集合

```shell
MONGO_URI=mongodb://localhost/some-db MONGO_EXCLUDE_COLLECTIONS=col_a,col_b BACKUP_PATH=./backup python docker/backup.py
```

### 使用 docker

```shell
# backup
docker run -it --rm \
  -e MONGO_URI="mongodb://localhost/some-db" \
  -v ./some-dir:/backup \
  36node/mongodb-backup

# restore
docker run -it --rm \
  -e MONGO_URI="mongodb://localhost" \
  -v ./some-dir:/backup \
  36node/mongodb-backup \
  /app/restore.py
```

### 使用 helm-chart

```shell
# 确保你的 helm 客户端支持 oci
export HELM_EXPERIMENTAL_OCI=1

# 安装
helm -n mongodb-backup-chart install mongodb-backup oci://harbor.36node.com/common/mongodb-backup:1.3.0 -f values.yaml
```

values 样例

```yaml
backup:
  enabled: true
  schedule: "0 0 * * *"
  hostPath: /opt
  nodeSelector:
    kubernetes.io/hostname: "worker-1"
  env:
    MONGO_URI: "mongodb://localhost:27017/some-db"
    FILE_PREFIX: xsjj
    BACKUP_SAVE_NUMS: 3
restore:
  enabled: true
  hostPath: /opt
  nodeSelector:
    kubernetes.io/hostname: "worker-1"
  env:
    MONGO_URI: "mongodb://localhost:27017"
```

恢复

```shell
## 启动一个容器用于执行恢复脚本
kubectl -n mongodb-backup scale deployment restore --replicas=1

## 查看这个容器启动的 pod
kubectl -n mongodb-backup get pod

# 选择适当的备份进行恢复
kubectl -n mongodb-backup exec -it restore-xxx-xxx -- python3 /app/restore.py
```

#### 存储

支持 挂载磁盘 或 PVC，容器内的挂载路径默认为 `/backup`

- 本地磁盘，指定 nodeSelector 及 hostPath
- PVC，指定 existingClaim
- comming feature 支持 storage_class

## 环境变量说明

### backup

- MONGO_URI: 必填，uri，例如 `mongodb://root:it_is_a_secret@mongodb-0.mongodb-headless/some-db?authSource=admin`
- FILE_PREFIX: 选填，备份文件前缀，例如 fcp
- BACKUP_SAVE_NUMS: 选填，备份保存数量，例如 3，默认保存 3 份
- MONGO_COLLECTION: 选填，集合名称，不支持多个，例如 gantry，若不为空，则需保证 MONGO_DB 也存在
- MONGO_EXCLUDE_COLLECTIONS: 选填，忽略的集合名称，支持多个，例如 test1,test2，若不为空，则需保证 MONGO_DB 也存在，且若 MONGO_COLLECTION 不为空，则忽略该参数
- BACKUP_PWD: 选填，加密密码，备份文件可用 zip 加密

- S3_ENABLE: 选填，是否启用 S3 存储备份，不为空值即认为启用，例如 1 视为启用 S3
- S3_EP: 选填，S3 url，例如 https://minio-api.36node.com
- S3_ACCESS_KEY: 选填，S3 access key
- S3_ACCESS_SECRET: 选填，S3 access secret
- S3_BUCKET: 选填，要存储的桶名
- S3_PREFIX: 选填，要存储的前缀

### restore

- RESTORE_FROM_S3: 选填，是否从 S3 中进行恢复，不为空值即认为启用，例如 1 视为从 S3 中进行恢复

同 backup 的变量

- MONGO_URI
- MONGO_FILE_PREFIX
- BACKUP_LATEST_FILE
- BACKUP_PWD

- S3_EP
- S3_ACCESS_KEY
- S3_ACCESS_SECRET
- S3_BUCKET
- S3_PREFIX

## Development

开发相关的涉及命令

```shell
# mongodump
mongodump --uri="mongodb://localhost:27017" --db=test --collection=test --gzip --archive="/backup/test-test-test-backup-202400101000000.tar.gz" --authenticationDatabase=admin

# mongostore
mongorestore --uri="mongodb://localhost:27017" --gzip --archive="/backup/test-test-test-backup-202400101000000.tar.gz" --authenticationDatabase=admin

# zip
zip -e test.tar.gz.zip -P 123456 test.tar.gz
unzip -P 123456 test.tar.gz.zip

# docker
docker build -t exmaple/mongodb-backup:main .
docker push exmaple/mongodb-backup:main
```

