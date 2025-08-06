import os
import re
import sys
from datetime import datetime, timedelta
import subprocess
from urllib.parse import urlparse
import boto3
from botocore.client import Config
import requests

# 数据库清理备份脚本
# 1. 按要求备份数据，并保存到指定路径
# 2. 清理备份，保留最近的若干份
# 3. 将备份文件上传到 S3，并清理 S3 上的多余备份文件

DEFAULT_FILE_PREFIX = ""
DEFAULT_BACKUP_PATH = "/backup"
DEFAULT_BACKUP_SAVE_NUMS = 3

DEFAULT_S3_PREFIX = ""

must_inputs = ["MONGO_URI"]
other_inputs = [
    "FILE_PREFIX",
    "BACKUP_PATH",
    "BACKUP_SAVE_NUMS",
    "MONGO_COLLECTION",
    "MONGO_EXCLUDE_COLLECTIONS",
    "BACKUP_PWD",
    # S3 CONFIG
    "S3_ENABLE",
    "S3_EP",
    "S3_EP_VIRTUAL",
    "S3_ACCESS_KEY",
    "S3_ACCESS_SECRET",
    "S3_REGION",
    "S3_BUCKET",
    "S3_PREFIX",
    "FEISHU_TOKEN",
]

for key in must_inputs:
    if key not in os.environ or os.environ[key] == "":
        print(key, "must set")
        sys.exit()


def check_var(key):
    if key in os.environ and os.environ[key] != "":
        return True
    return False


def check_bool(key):
    if os.environ[key].lower() == "true":
        return True
    return False


# 必填
uri = os.environ["MONGO_URI"]

# 选填
file_prefix = (
    os.environ["FILE_PREFIX"] if check_var("FILE_PREFIX") else DEFAULT_FILE_PREFIX
)
backup_path = (
    os.environ["BACKUP_PATH"] if check_var("BACKUP_PATH") else DEFAULT_BACKUP_PATH
)
backup_save_nums = (
    int(os.environ["BACKUP_SAVE_NUMS"])
    if check_var("BACKUP_SAVE_NUMS")
    else DEFAULT_BACKUP_SAVE_NUMS
)
collection = os.environ["MONGO_COLLECTION"] if check_var("MONGO_COLLECTION") else None
excludeCollections = (
    os.environ["MONGO_EXCLUDE_COLLECTIONS"].split(",")
    if check_var("MONGO_EXCLUDE_COLLECTIONS")
    else None
)
backup_pwd = os.environ["BACKUP_PWD"] if check_var("BACKUP_PWD") else None

s3_enable = check_bool("S3_ENABLE") if check_var("S3_ENABLE") else False
s3_ep = os.environ["S3_EP"] if check_var("S3_EP") else None
s3_ep_virtual = check_bool("S3_EP_VIRTUAL") if check_var("S3_EP_VIRTUAL") else False
s3_access_key = os.environ["S3_ACCESS_KEY"] if check_var("S3_ACCESS_KEY") else None
s3_access_secret = (
    os.environ["S3_ACCESS_SECRET"] if check_var("S3_ACCESS_SECRET") else None
)
s3_bucket = os.environ["S3_BUCKET"] if check_var("S3_BUCKET") else None
s3_prefix = os.environ["S3_PREFIX"] if check_var("S3_PREFIX") else DEFAULT_S3_PREFIX
s3_region = os.environ["S3_REGION"] if check_var("S3_REGION") else None
s3_region = os.environ["S3_REGION"] if check_var("S3_REGION") else None
s3_signature_version = (
    os.environ["S3_SIGNATURE_VERSION"] if check_var("S3_SIGNATURE_VERSION") else None
)

feishu_notify_token = (
    os.environ["FEISHU_NOTIFY_TOKEN"] if check_var("FEISHU_NOTIFY_TOKEN") else None
)
feishu_notify_title = (
    os.environ["FEISHU_NOTIFY_TITLE"] if check_var("FEISHU_NOTIFY_TITLE") else None
)

# 计算当前日期，按照 年月日时分 格式
date = (datetime.now() + timedelta(hours=8)).strftime("%Y%m%d%H%M%S")


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


def upload_s3(prefix):
    # config
    config_s3 = {}
    if s3_ep_virtual:
        config_s3["addressing_style"] = "virtual"

    if s3_region and s3_signature_version:
        config = Config(s3=config_s3, signature_version="s3", region_name=s3_region)
    elif s3_region:
        config = Config(s3=config_s3, region_name=s3_region)
    elif s3_signature_version:
        config = Config(s3=config_s3, signature_version=s3_signature_version)
    else:
        config = Config(s3=config_s3)

    client = boto3.client(
        "s3",
        endpoint_url=s3_ep,
        aws_access_key_id=s3_access_key,
        aws_secret_access_key=s3_access_secret,
        config=config,
    )

    # 上传备份文件
    file_name = (
        f"{prefix}{date}.tar.gz.crypt" if backup_pwd else f"{prefix}{date}.tar.gz"
    )
    upload_path = f"{s3_prefix}/{file_name}" if s3_prefix else file_name
    client.upload_file(f"{backup_path}/{file_name}", s3_bucket, upload_path)

    # 清理 S3 上的多余备份文件
    list_prefix = f"{s3_prefix}/" if s3_prefix else ""
    resp = client.list_objects_v2(Bucket=s3_bucket, Prefix=list_prefix, Delimiter="/")
    if "Contents" in resp:
        objects = resp["Contents"]

        file_prefix = f"{list_prefix}{prefix}"
        # 构造正则表达式
        regex_pattern = f"^{re.escape(file_prefix)}(\\d{{14}})\\.tar\\.gz(\\.crypt)?$"
        compiled_regex = re.compile(regex_pattern)
        keys = [
            object["Key"] for object in objects if compiled_regex.match(object["Key"])
        ]

        # 根据文件名排序（这使得最新的备份文件位于列表的末尾）
        keys.sort()

        # 确定需要删除的文件（保留最后N个文件，这里是backup_save_nums）
        keys_to_remove = keys[:-backup_save_nums]

        # 删除旧的备份文件
        if keys_to_remove:
            client.delete_objects(
                Bucket=s3_bucket,
                Delete={"Objects": [{"Key": key} for key in keys_to_remove]},
            )
            print(f"Deleted s3 old backup files: {keys_to_remove}")


def send_feishu_notify(msg):
    data = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": f"{feishu_notify_title} mongodb 备份出错",
                    "content": [
                        [
                            {
                                "tag": "text",
                                "text": msg,
                            }
                        ]
                    ],
                }
            }
        },
    }
    try:
        requests.post(
            f"https://open.feishu.cn/open-apis/bot/v2/hook/{feishu_notify_token}",
            json=data,
        )
    except Exception as e:
        print("Feishu notify error:", e)


try:
    if not os.path.exists(backup_path):
        os.makedirs(backup_path)

    db = get_dbname_from_mongo_uri(uri)
    print("db: ", db)

    final_prefix = calculate_file_prefix(db, collection, file_prefix)
    print("final_prefix: ", final_prefix)

    # 1. 按要求备份数据，并保存到指定路径
    backup_file(final_prefix)
    print("backup end")

    # 2. 清理备份，保留最近的若干份
    cleanup_files(final_prefix)
    print("cleanup end")

    if s3_enable:
        # 3. 将备份文件上传到 S3，并清理 S3 上的多余备份文件
        upload_s3(final_prefix)
        print("upload s3 end")

    print("script end")

except Exception as e:
    print("backup error:", e)

    if feishu_notify_token:
        send_feishu_notify(f"错误信息: {e}")

    sys.exit()
