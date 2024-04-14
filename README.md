# mongodb-backup

用于备份数据库、备份清理、备份恢复

- 支持保留备份数
- 支持全量备份
- 支持单数据库备份
- 支持单集合备份
- 支持忽略若干集合备份
- 支持选择备份恢复

### 使用

使用 ansible 部署 helm-chart，按要求定时备份数据库

#### 恢复

```shell
kubectl -n mongodb-backup get pod

# 选择适当的备份进行恢复
kubectl -n mongodb-backup exec -it restore-xxx-xxx -- python3 /app/restore.py
```

#### 存储

支持 挂载磁盘 或 PVC，容器内的挂载路径默认为 `/backup`

- 磁盘，指定 nodeSelector 及 hostPath
- PVE，指定 existingClaim

### 测试方法

#### docker

```shell
docker pull 36node/mongodb-backup:main

# backup
docker run -e SCRIPT_NAME=backup -e MONGO_URI="mongodb://localhost" \
 -e MONGO_FILE_PREFIX=tmp -e BACKUP_LATEST_FILE="tmp.tar.gz" -e BACKUP_SAVE_NUMS=3 \
 -e MONGO_DB=test -e MONGO_COLLECTION=test \
 -v ~/Downloads/mongodb/test:/backup 36node/mongodb-backup:main

# restore
docker run -d -e SCRIPT_NAME=restore -e MONGO_URI="mongodb://localhost" \
 -e MONGO_FILE_PREFIX=tmp -e BACKUP_LATEST_FILE="tmp.tar.gz" \
 -v /Users/cc-mac/Downloads/mongodb/test:/backup cc3630/test:main

docker ps -a
docker exec -it xxx python3 /app/restore.py
```

#### helm-chart

```shell
# 查看 yaml 文件
helm install mongodb-backup ~/mongodb-backup/helm-chart -f values.yaml -n test --dry-run --debug
```

#### 涉及命令说明

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

### 环境变量说明

#### backup

- MONGO_URI: 必填，uri，例如 mongodb://root:it_is_a_secret@mongodb-0.mongodb-headless
- MONGO_FILE_PREFIX: 必填，备份文件前缀，例如 fcp
- BACKUP_LATEST_FILE: 必填，最新备份文件名，例如 api.tar.gz
- BACKUP_SAVE_NUMS: 非必填，备份保存数量，例如 3，默认保存 3 份
- MONGO_DB: 非必填，数据库名称，例如 api，若为空，则备份所有数据库
- MONGO_COLLECTION: 非必填，集合名称，不支持多个，例如 gantry，若不为空，则需保证 MONGO_DB 也存在
- MONGO_EXCLUDE_COLLECTIONS: 非必填，忽略的集合名称，支持多个，例如 test1,test2，若不为空，则需保证 MONGO_DB 也存在，且若 MONGO_COLLECTION 不为空，则忽略该参数
- BACKUP_PWD: 非必填，加密密码，备份文件可用 zip 加密

#### restore

同 backup 的变量

- MONGO_URI
- MONGO_FILE_PREFIX
- BACKUP_LATEST_FILE
- BACKUP_PWD

### 样例

#### 部署样例

```yaml
- name: deploy mongodb backup
  hosts: localhost
  gather_facts: false

  environment:
    K8S_AUTH_CONTEXT: "{{ cluster_name }}"

  vars:
    chart: ~/mongodb-backup/helm-chart
    namespace: mongodb-backup

    image_registry: harbor.example.com
    image_repo: test/test
    image_tag: main

    mongo_uri: "mongodb://local:27017"
    mongo_file_prefix: tmp
    mongo_latest_file: tmp.tar.gz
    mongo_backup_pwd: 123456
    node_selector: "worker-1"

  tasks:
    - name: mongodb backup and restore
      kubernetes.core.helm:
        state: present
        name: mongodb-backup
        namespace: "{{ namespace }}"
        create_namespace: true
        chart_ref: "{{ chart }}"
        values:
          global:
            imageRegistry: "{{ image_registry }}"
          backup:
            enabled: true
            schedule: "0 0 * * *"
            hostPath: /opt
            nodeSelector:
              kubernetes.io/hostname: "{{ node_selector}}"
            image:
              repository: "{{ image_repo }}"
              tag: "{{ image_tag }}"
            env:
              MONGO_URI: "{{ mongo_uri }}"
              MONGO_FILE_PREFIX: "{{ mongo_file_prefix }}"
              BACKUP_LATEST_FILE: "{{ mongo_latest_file }}"
              BACKUP_SAVE_NUMS: 3
              MONGO_DB: test
              MONGO_COLLECTION: test
              BACKUP_PWD: "{{ mongo_backup_pwd }}"
          restore:
            enabled: true
            hostPath: /opt
            nodeSelector:
              kubernetes.io/hostname: "{{ node_selector}}"
            image:
              repository: "{{ image_repo }}"
              tag: "{{ image_tag }}"
            env:
              MONGO_URI: "{{ mongo_uri }}"
              MONGO_FILE_PREFIX: "{{ mongo_file_prefix }}"
              BACKUP_LATEST_FILE: "{{ mongo_latest_file }}"
              BACKUP_PWD: "{{ mongo_backup_pwd }}"
```

#### helm values.yaml 样例

```yaml
global:
  imageRegistry: "repo.com"
backup:
  enabled: true
  schedule: "0 0 * * *"
  hostPath: /opt
  nodeSelector:
    kubernetes.io/hostname: "worker-1"
  image:
    repository: test/test
  env:
    MONGO_URI: "mongodb://localhost:27017"
    MONGO_FILE_PREFIX: tmp
    BACKUP_LATEST_FILE: tmp.tar.gz
    BACKUP_SAVE_NUMS: 3
    MONGO_DB: test
    MONGO_COLLECTION: test
restore:
  enabled: true
  hostPath: /opt
  nodeSelector:
    kubernetes.io/hostname: "worker-1"
  image:
    repository: test/test
  env:
    MONGO_URI: "mongodb://localhost:27017"
    MONGO_FILE_PREFIX: tmp
    BACKUP_LATEST_FILE: tmp.tar.gz
```
