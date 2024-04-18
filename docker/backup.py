import os
import re
import sys
from datetime import datetime, timedelta
import subprocess
import shutil
from urllib.parse import urlparse

# 数据库清理备份脚本
# 1. 清理备份，保留最近的若干份
# 2. 按要求备份数据，并保存最终备份

DEFAULT_FILE_PREFIX = ""
DEFAULT_BACKUP_PATH = "/backup"
DEFAULT_BACKUP_SAVE_NUMS = 3

must_inputs = ["MONGO_URI"]
other_inputs = [
    "FILE_PREFIX",
    "BACKUP_PATH",
    "BACKUP_SAVE_NUMS",
    "MONGO_COLLECTION",
    "MONGO_EXCLUDE_COLLECTIONS",
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
file_prefix = os.environ["FILE_PREFIX"] if check_var("FILE_PREFIX") else DEFAULT_FILE_PREFIX
backup_path = os.environ["BACKUP_PATH"] if check_var("BACKUP_PATH") else DEFAULT_BACKUP_PATH
backup_save_nums = int(os.environ["BACKUP_SAVE_NUMS"]) if check_var("BACKUP_SAVE_NUMS") else DEFAULT_BACKUP_SAVE_NUMS
collection = os.environ["MONGO_COLLECTION"] if check_var("MONGO_COLLECTION") else None
excludeCollections = (
    os.environ["MONGO_EXCLUDE_COLLECTIONS"].split(",") if check_var("MONGO_EXCLUDE_COLLECTIONS") else None
)
backup_pwd = os.environ["BACKUP_PWD"] if check_var("BACKUP_PWD") else None

# 计算当前日期，按照 年月日时分 格式
date = (datetime.utcnow() + timedelta(hours=8)).strftime("%Y%m%d%H%M%S")


def get_dbname_from_mongo_uri(uri):
    """
    从 MongoDB URI 中解析并返回数据库名称
    """
    # 使用urlparse解析URI
    parsed_uri = urlparse(uri)

    # 获取路径部分，并分割斜杠 '/'
    # 数据库名是路径的第一个分隔部分（忽略第一个空字符串）
    path = parsed_uri.path
    if path.startswith("/"):
        dbname = path[1:].split("/")[0]
    else:
        dbname = path.split("/")[0]

    return dbname


def calculate_file_prefix(db=None, collection=None, file_prefix=None):
    # 初始化最终的前缀字符串
    final_prefix = ""

    # 检查file_prefix是否非空，如果是则添加到最终前缀
    if file_prefix:
        final_prefix = f"{file_prefix}-"

    # 在db存在的基础上构造前缀
    if db:
        final_prefix += f"{db}-"

        # 在db和collection都存在的情况下构造前缀
        if collection:
            final_prefix += f"{collection}-"

    return final_prefix


def cleanup_files(prefix):
    # 构造正则表达式
    regex_pattern = f"^{re.escape(prefix)}(\\d{{14}})\\.tar\\.gz(\\.crypt)?$"
    compiled_regex = re.compile(regex_pattern)

    # 列出备份文件夹中所有的文件
    all_files = os.listdir(backup_path)

    # 筛选出符合正则表达式的文件
    matched_files = [file for file in all_files if compiled_regex.match(file)]

    # 根据文件名排序（这使得最新的备份文件位于列表的末尾）
    matched_files.sort()

    # 确定需要删除的文件（保留最后N个文件，这里是backup_save_nums）
    files_to_remove = matched_files[:-backup_save_nums]

    # 删除旧的备份文件
    for file in files_to_remove:
        os.remove(os.path.join(backup_path, file))
        print(f"Deleted old backup file: {file}")


def backup_file(prefix):
    backup_file_name = f"{prefix}{date}.tar.gz"
    cmd = f'mongodump --uri="{uri}" --gzip --archive="{backup_path}/{backup_file_name}"'
    if collection:
        cmd = f'mongodump --uri="{uri}" --collection={collection} --gzip --archive="{backup_path}/{backup_file_name}"'
    elif excludeCollections:
        exclude_cmd = ""
        for key in excludeCollections:
            exclude_cmd += f"--excludeCollection={key} "
        cmd = f'mongodump --uri="{uri}" {exclude_cmd} --gzip --archive="{backup_path}/{backup_file_name}"'
    print(cmd)
    subprocess.call(cmd, shell=True)

    # 加密
    if backup_pwd:
        source = f"{backup_path}/{backup_file_name}"
        subprocess.call(f"zip -e {source}.crypt -P {backup_pwd} {source}", shell=True)
        os.remove(source)
    print("backup end")


try:
    if not os.path.exists(backup_path):
        os.makedirs(backup_path)

    db = get_dbname_from_mongo_uri(uri)
    print("db: ", db)

    final_prefix = calculate_file_prefix(db, collection, file_prefix)
    print("final_prefix: ", final_prefix)

    # 1. 按要求备份数据
    backup_file(final_prefix)
    print("backup end")

    # 1. 清理备份，保留最近的若干份
    cleanup_files(final_prefix)
    print("cleanup end")

    print("script end")

except Exception as e:
    print("backup error:", e)
    sys.exit()
