import os
import sys
import boto3
from botocore.client import Config

# S3测试脚本
# 用于测试 S3 连接配置是否正确

DEFAULT_S3_PREFIX = ""

inputs = [
    "UPLOAD_FILE",
    "S3_EP",
    "S3_EP_VIRTUAL",
    "S3_ACCESS_KEY",
    "S3_ACCESS_SECRET",
    "S3_REGION",
    "S3_BUCKET",
    "S3_PREFIX",
]


def check_var(key):
    if key in os.environ and os.environ[key] != "":
        return True
    return False


def check_bool(key):
    if os.environ[key].lower() == "true":
        return True
    return False


upload_file = os.environ["UPLOAD_FILE"] if check_var("UPLOAD_FILE") else False
s3_ep = os.environ["S3_EP"] if check_var("S3_EP") else None
s3_ep_virtual = check_bool("S3_EP_VIRTUAL") if check_var("S3_EP_VIRTUAL") else False
s3_access_key = os.environ["S3_ACCESS_KEY"] if check_var("S3_ACCESS_KEY") else None
s3_access_secret = (
    os.environ["S3_ACCESS_SECRET"] if check_var("S3_ACCESS_SECRET") else None
)
s3_bucket = os.environ["S3_BUCKET"] if check_var("S3_BUCKET") else None
s3_prefix = os.environ["S3_PREFIX"] if check_var("S3_PREFIX") else DEFAULT_S3_PREFIX
s3_region = os.environ["S3_REGION"] if check_var("S3_REGION") else None


try:
    if not upload_file:
        print("UPLOAD_FILE must set")
        sys.exit()

    # config
    config_s3 = {}
    if s3_ep_virtual:
        config_s3["addressing_style"] = "virtual"

    if s3_region:
        config = Config(s3=config_s3, region_name=s3_region)
    else:
        config = Config(s3=config_s3)

    client = boto3.client(
        "s3",
        endpoint_url=s3_ep,
        aws_access_key_id=s3_access_key,
        aws_secret_access_key=s3_access_secret,
        config=config,
    )

    file_name = os.path.basename(upload_file)
    upload_path = f"{s3_prefix}/{file_name}" if s3_prefix else file_name
    client.upload_file(upload_file, s3_bucket, upload_path)

    print("upload success")

except Exception as e:
    print("test error:", e)
    sys.exit()
