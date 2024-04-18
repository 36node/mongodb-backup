import os
import re
import sys
from datetime import datetime, timedelta
import subprocess

# 数据库还原

DEFAULT_BACKUP_PATH = "/backup"
DEFAULT_BACKUP_SAVE_NUMS = 3

must_inputs = ["MONGO_URI"]
other_inputs = [
    "FILE_PREFIX",
    "BACKUP_PATH",
    "BACKUP_PWD",
]

for key in must_inputs:
    if key not in os.environ or os.environ[key] == "":
        print(key, "must set")
        sys.exit()


def check_var(key):
    if key in os.environ and os.environ[key] != "":
        return True
    return False


# 必填
uri = os.environ["MONGO_URI"]

# 选填
backup_path = os.environ["BACKUP_PATH"] if check_var("BACKUP_PATH") else BACKUP_PATH
backup_pwd = os.environ["BACKUP_PWD"] if check_var("BACKUP_PWD") else None

date = (datetime.utcnow() + timedelta(hours=8)).strftime("%Y%m%d%H%M%S")


def get_files():
    # 构造正则表达式
    regex_pattern = f"^.*(\\d{{14}})\\.tar\\.gz(\\.crypt)?$"
    compiled_regex = re.compile(regex_pattern)

    # 列出备份文件夹中所有的文件
    all_files = os.listdir(backup_path)

    # 筛选出符合正则表达式的文件
    matched_files = [file for file in all_files if compiled_regex.match(file)]

    # 根据文件名排序（这使得最新的备份文件位于列表的末尾）
    matched_files.sort(reverse=True)
    return matched_files


def restore_file(file_path):
    is_crypt_file = file_path.endswith(".crypt")
    restore_path = file_path if not is_crypt_file else file_path[:-6]

    if is_crypt_file and not backup_pwd:
        print("need set BACKUP_PWD")
        sys.exit()

    if is_crypt_file and backup_pwd:
        # 先解密
        unzip_path = os.path.dirname(file_path)
        # -o 覆盖已有文件，-j 不保留文件夹
        subprocess.call(f"unzip -P {backup_pwd} -oj {file_path} -d {unzip_path}", shell=True)

    # 恢复数据
    cmd = f'mongorestore --uri="{uri}" --gzip --archive={restore_path}'
    subprocess.call(cmd, shell=True)

    if is_crypt_file and backup_pwd:
        # 删除解密文件
        os.remove(restore_path)


try:
    # 1. 获取备份文件列表
    backup_files = get_files()

    input_cmd = "请选择要还原的备份文件：\n"
    for index, item in enumerate(backup_files):
        input_cmd += f"{index + 1}. {item}\n"
    value = input(input_cmd)
    file = f"{backup_path}/{backup_files[int(value) - 1]}"

    restore_file(file)

    print("script end")
except Exception as e:
    print("restore error:", e)
    sys.exit()
