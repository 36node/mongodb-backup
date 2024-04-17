import os
import sys
from datetime import datetime, timedelta
import subprocess

# 数据库还原

BACKUP_PATH = "/backup"

must_inputs = ["MONGO_URI", "MONGO_FILE_PREFIX", "BACKUP_LATEST_FILE"]
other_inputs = [
    "BACKUP_PATH",
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
backup_pwd = os.environ["BACKUP_PWD"] if check_var("BACKUP_PWD") else None

date = (datetime.utcnow() + timedelta(hours=8)).strftime("%Y%m%d%H%M%S")


def get_files():
    file = os.listdir(backup_path)
    temp_files = []
    latest_file_name = f'{backup_latest_file}.zip' if backup_pwd else backup_latest_file
    for file_name in file:
        file_path = os.path.join(backup_path, file_name)
        if os.path.isfile(file_path):
            # 有密码备份文件为tar.gz.zip格式，无密码备份文件为tar.gz格式
            if (backup_pwd and file_name.endswith('.zip')) or (not backup_pwd and file_name.endswith('.tar.gz')):
                if file_name.startswith(file_prefix) and file_name != latest_file_name:
                    temp_files.append({
                        "time": int(file_name.split('.')[0].split('-')[-1]),
                        "path": file_path,
                        "name": file_name
                    })
    files = sorted(temp_files, key=lambda d: d['time'], reverse=True)
    files.insert(0, {
        "path": os.path.join(backup_path, latest_file_name),
        "name": latest_file_name
    })
    return files


def restore_file(file_path):
    restore_path = ".".join(file_path.split('.')[:-1]) if backup_pwd else file_path
    if backup_pwd:
        # 先解密
        unzip_path = os.path.dirname(file_path)
        # -o 覆盖已有文件，-j 不保留文件夹
        subprocess.call(f'unzip -P {backup_pwd} -oj {file_path} -d {unzip_path}', shell=True)

    # 恢复数据
    cmd = f'mongorestore --uri="{uri}" --gzip --archive={restore_path} --authenticationDatabase=admin'
    subprocess.call(cmd, shell=True)

    if backup_pwd:
        # 删除解密文件
        os.remove(restore_path)


try:
    # 1. 清理备份，保留最近的若干份
    backup_files = get_files()

    input_cmd = "请选择要还原的备份文件：\n"
    for index, item in enumerate(backup_files):
        input_cmd += f'{index + 1}. {item["name"]}\n'
    value = input(input_cmd)

    restore_file(backup_files[int(value) - 1]["path"])

    print("script end")
except Exception as e:
    print("restore error:", e)
    sys.exit()
