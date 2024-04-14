import os
import sys
from datetime import datetime, timedelta
import subprocess
import shutil

# 数据库清理备份并上传
# 1. 清理备份，保留最近的若干份
# 2. 按要求备份数据，并保存最终备份

BACKUP_PATH = "/backup"
BACKUP_SAVE_NUMS = 3

must_inputs = ["MONGO_URI", "MONGO_FILE_PREFIX", "BACKUP_LATEST_FILE"]
other_inputs = [
    "BACKUP_PATH",
    "BACKUP_SAVE_NUMS",
    "MONGO_DB",
    "MONGO_COLLECTION",
    "MONGO_EXCLUDE_COLLECTIONS",
    "BACKUP_PWD"
]

for key in must_inputs:
    if key not in os.environ or os.environ[key] == '':
        print(key, "must set")
        sys.exit()


def check_var(key):
    if key in os.environ and os.environ[key] != "":
        return True
    return False


# 必填
uri = os.environ["MONGO_URI"]
file_prefix = os.environ["MONGO_FILE_PREFIX"]
backup_latest_file = os.environ["BACKUP_LATEST_FILE"]

# 选填
backup_path = os.environ["BACKUP_PATH"] if check_var("BACKUP_PATH") else BACKUP_PATH
backup_save_nums = int(
    os.environ["BACKUP_SAVE_NUMS"]) if check_var("BACKUP_SAVE_NUMS") else BACKUP_SAVE_NUMS
db = os.environ["MONGO_DB"] if check_var("MONGO_DB") else None
collection = os.environ["MONGO_COLLECTION"] if check_var("MONGO_COLLECTION") else None
excludeCollections = os.environ["MONGO_EXCLUDE_COLLECTIONS"].split(
    ",") if check_var("MONGO_EXCLUDE_COLLECTIONS") else None
backup_pwd = os.environ["BACKUP_PWD"] if check_var("BACKUP_PWD") else None

date = (datetime.utcnow() + timedelta(hours=8)).strftime("%Y%m%d%H%M%S")


def clean_files():
    file = os.listdir(backup_path)
    temp_files = []
    latest_file_name = f'{backup_latest_file}.zip' if backup_pwd else backup_latest_file
    for file_name in file:
        file_path = os.path.join(backup_path, file_name)
        if os.path.isfile(file_path):
            if (backup_pwd and file_name.endswith('.zip')) or (not backup_pwd and file_name.endswith('.tar.gz')):
                if file_name.startswith(file_prefix) and file_name != latest_file_name:
                    temp_files.append({
                        "time": int(file_name.split('.')[0].split('-')[-1]),
                        "path": file_path,
                    })
    if len(temp_files) >= backup_save_nums:
        sort_files = sorted(temp_files, key=lambda d: d['time'])
        for value in sort_files[:(len(temp_files)-backup_save_nums+1)]:
            os.remove(value["path"])
    sys.stdout.flush()
    print("clean end")


def backup_file():
    backup_file_name = f'{file_prefix}-backup-{date}.tar.gz'
    cmd = f'mongodump --uri="{uri}" --gzip --archive="{backup_path}/{backup_file_name}"'
    if db:
        # 指定db后，必须使用 --authenticationDatabase=admin
        backup_file_name = f'{file_prefix}-{db}-backup-{date}.tar.gz'
        cmd = f'mongodump --uri="{uri}" --db={db} --gzip --archive="{backup_path}/{backup_file_name}" --authenticationDatabase=admin'
        if collection:
            backup_file_name = f'{file_prefix}-{db}-{collection}-backup-{date}.tar.gz'
            cmd = f'mongodump --uri="{uri}" --db={db} --collection={collection} --gzip --archive="{backup_path}/{backup_file_name}" --authenticationDatabase=admin'
        elif excludeCollections:
            exclude_cmd = ""
            for key in excludeCollections:
                exclude_cmd += f'--excludeCollection={key} '
            backup_file_name = f'{file_prefix}-{db}-exclude-{"_".join(excludeCollections)}-backup-{date}.tar.gz'
            cmd = f'mongodump --uri="{uri}" --db={db} {exclude_cmd} --gzip --archive="{backup_path}/{backup_file_name}" --authenticationDatabase=admin'
    print(cmd)
    subprocess.call(cmd, shell=True)

    # 复制最新镜像，并重命名
    source = f'{backup_path}/{backup_file_name}'
    dest = f'{backup_path}/{backup_latest_file}'
    shutil.copyfile(source, dest)

    # 加密
    if backup_pwd:
        subprocess.call(f'zip -e {source}.zip -P {backup_pwd} {source}', shell=True)
        subprocess.call(f'zip -e {dest}.zip -P {backup_pwd} {dest}', shell=True)
        os.remove(source)
        os.remove(dest)
    print("backup end")


try:
    if not os.path.exists(backup_path):
        os.makedirs(backup_path)

    # 1. 清理备份，保留最近的若干份
    clean_files()

    # 2. 按要求备份数据
    backup_file()

    print("script end")

except Exception as e:
    print("backup error:", e)
    sys.exit()
