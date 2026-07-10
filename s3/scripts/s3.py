#!/usr/bin/env python3
"""
S3 兼容对象存储操作 CLI
支持上传、下载（生成下载链接）、删除、列表、文件信息查询等操作。

环境变量:
  S3_ENDPOINT   - S3 兼容存储端点地址（必填）
  S3_BUCKET     - 存储桶名称（必填）
  S3_REGION     - 区域（默认 us-east-1）
  AWS_ACCESS_KEY_ID     - 访问密钥（boto3 自动读取）
  AWS_SECRET_ACCESS_KEY - 访问密钥（boto3 自动读取）
"""

import argparse
import json
import os
import sys
from pathlib import Path

import boto3
import requests
from botocore.config import Config as BotoConfig
from dotenv import load_dotenv

# ============================================================
# 配置（从环境变量读取）
# ============================================================

S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "").rstrip("/")
S3_BUCKET = os.environ.get("S3_BUCKET", "")
S3_REGION = os.environ.get("S3_REGION", "us-east-1")


def get_s3_client():
    """创建 S3 客户端（凭证由 boto3 从默认凭证链自动获取）"""
    if not S3_ENDPOINT:
        die("环境变量 S3_ENDPOINT 未设置")
    if not S3_BUCKET:
        die("环境变量 S3_BUCKET 未设置")

    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        config=BotoConfig(signature_version="s3v4", region_name=S3_REGION),
        region_name=S3_REGION,
    )


def die(msg):
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(1)


# ============================================================
# 操作函数
# ============================================================

def cmd_upload(args):
    """上传本地文件到 S3"""
    local = args.local
    remote = args.remote or Path(local).name

    path = Path(local)
    if not path.exists():
        die(f"文件不存在: {local}")

    size_mb = path.stat().st_size / (1024 * 1024)
    s3 = get_s3_client()

    if args.presigned:
        # Presigned URL 上传
        put_url = s3.generate_presigned_url(
            "put_object",
            Params={"Bucket": S3_BUCKET, "Key": remote},
            ExpiresIn=3600,
        )
        print(f"📤 通过 presigned URL 上传: {remote} ({size_mb:.1f} MB)")
        with open(path, "rb") as f:
            resp = requests.put(put_url, data=f, timeout=600)
        if resp.status_code != 200:
            die(f"上传失败 (HTTP {resp.status_code}): {resp.text[:200]}")
    else:
        # boto3 upload_file（可能因签名问题失败，留作备选尝试）
        print(f"📤 通过 boto3 上传: {remote} ({size_mb:.1f} MB)")
        try:
            s3.upload_file(str(path), S3_BUCKET, remote)
        except Exception as e:
            die(f"boto3 上传失败（尝试 --presigned）: {e}")

    print(f"✅ 上传完成: {S3_ENDPOINT}/{S3_BUCKET}/{remote}")


def cmd_download(args):
    """从 S3 下载到本地"""
    remote = args.remote
    local = args.local or Path(remote).name

    s3 = get_s3_client()

    # 先用 presigned GET URL 下载（因为 bucket 禁止公开读取）
    try:
        get_url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": remote},
            ExpiresIn=3600,
        )
        print(f"📥 下载: {remote} → {local}")
        resp = requests.get(get_url, timeout=600)
        if resp.status_code != 200:
            die(f"下载失败 (HTTP {resp.status_code})")
        Path(local).parent.mkdir(parents=True, exist_ok=True)
        with open(local, "wb") as f:
            f.write(resp.content)
    except Exception as e:
        die(f"下载失败: {e}")

    size_kb = Path(local).stat().st_size / 1024
    print(f"✅ 下载完成: {local} ({size_kb:.1f} KB)")


def cmd_gen_url(args):
    """生成 presigned 下载/上传 URL"""
    remote = args.remote
    expire = args.expire
    s3 = get_s3_client()

    params = {"Bucket": S3_BUCKET, "Key": remote}

    if args.upload:
        url = s3.generate_presigned_url("put_object", Params=params, ExpiresIn=expire)
        print(f"🔗 Presigned 上传 URL (有效期 {expire}s):")
    else:
        url = s3.generate_presigned_url("get_object", Params=params, ExpiresIn=expire)
        print(f"🔗 Presigned 下载 URL (有效期 {expire}s):")

    print(url)
    return url


def cmd_list(args):
    """列出存储桶中的文件"""
    s3 = get_s3_client()
    prefix = args.prefix or ""

    kwargs = {"Bucket": S3_BUCKET, "Prefix": prefix}

    if args.max_keys:
        kwargs["MaxKeys"] = args.max_keys

    if args.limit:
        kwargs["MaxKeys"] = args.limit

    try:
        resp = s3.list_objects_v2(**kwargs)
    except Exception as e:
        die(f"列出失败: {e}")

    if "Contents" not in resp:
        print("📭 存储桶为空（或无匹配前缀）")
        return

    total = len(resp["Contents"])
    print(f"📋 共 {total} 个文件:")
    print()
    for obj in resp["Contents"]:
        key = obj["Key"]
        size = obj["Size"]
        last_mod = obj["LastModified"].strftime("%Y-%m-%d %H:%M:%S")
        size_str = f"{size/1024:.1f} KB" if size < 1024*1024 else f"{size/(1024*1024):.1f} MB"
        print(f"  {key}")
        print(f"    ├── 大小: {size_str}")
        print(f"    └── 修改时间: {last_mod}")
        print()

    if resp.get("IsTruncated"):
        print("⚠️  结果已截断，还有更多文件。用 --prefix 缩小范围。")


def cmd_delete(args):
    """删除 S3 上的文件"""
    remote = args.remote
    s3 = get_s3_client()

    # 先确认
    if not args.yes:
        confirm = input(f"⚠️  确认删除 [{remote}]? (y/N): ").strip().lower()
        if confirm != "y":
            print("已取消")
            return

    try:
        s3.delete_object(Bucket=S3_BUCKET, Key=remote)
        print(f"🗑️  已删除: {remote}")
    except Exception as e:
        die(f"删除失败: {e}")


def cmd_info(args):
    """查询文件元信息"""
    remote = args.remote
    s3 = get_s3_client()

    try:
        resp = s3.head_object(Bucket=S3_BUCKET, Key=remote)
    except Exception as e:
        die(f"查询失败: {e}")

    print(f"📄 文件信息: {remote}")
    print(f"  大小: {resp['ContentLength']/1024:.1f} KB")
    print(f"  ETag: {resp.get('ETag', '-')}")
    print(f"  最后修改: {resp['LastModified'].strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Content-Type: {resp.get('ContentType', '-')}")

    meta = resp.get("Metadata", {})
    if meta:
        print(f"  Metadata: {json.dumps(meta, ensure_ascii=False)}")


# ============================================================
# CLI
# ============================================================

def main():
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="S3 兼容存储操作工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
子命令:
  upload   <本地文件> [--remote <路径>] [--presigned]
          上传文件到 S3（默认使用 boto3，失败时用 --presigned）

  download <remote路径> [--local <本地路径>]
          从 S3 下载文件

  gen-url  <remote路径> [--expire <秒>] [--upload]
          生成 presigned 下载/上传 URL

  list     [--prefix <前缀>] [--limit <数量>]
          列出文件

  delete   <remote路径> [-y]
          删除文件（需确认）

  info     <remote路径>
          查看文件元信息

示例:
  s3.py upload meeting.mp3
  s3.py upload meeting.mp3 --remote records/jan/meeting.mp3 --presigned
  s3.py download records/jan/meeting.mp3 --local ./got.mp3
  s3.py gen-url share.zip --expire 86400
  s3.py gen-url upload_target.zip --upload --expire 7200
  s3.py list --prefix records/ --limit 20
  s3.py delete old/temp.mp3 -y
  s3.py info backup/data.json
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # upload
    pu = subparsers.add_parser("upload", help="上传文件")
    pu.add_argument("local", help="本地文件路径")
    pu.add_argument("--remote", help="远程路径（默认=文件名）")
    pu.add_argument("--presigned", action="store_true",
                    help="强制使用 presigned URL 上传")

    # download
    pd = subparsers.add_parser("download", help="下载文件")
    pd.add_argument("remote", help="远程路径")
    pd.add_argument("--local", help="本地保存路径（默认=文件名）")

    # gen-url
    pg = subparsers.add_parser("gen-url", help="生成 presigned URL")
    pg.add_argument("remote", help="远程路径")
    pg.add_argument("--expire", type=int, default=3600,
                    help="URL 有效期（秒，默认 3600）")
    pg.add_argument("--upload", action="store_true",
                    help="生成上传 URL（默认生成下载 URL）")

    # list
    pl = subparsers.add_parser("list", help="列出文件")
    pl.add_argument("--prefix", help="前缀过滤")
    pl.add_argument("--limit", type=int, default=50, help="最大返回数（默认 50）")
    pl.add_argument("--max-keys", type=int, help="同 --limit")

    # delete
    pdel = subparsers.add_parser("delete", help="删除文件")
    pdel.add_argument("remote", help="远程路径")
    pdel.add_argument("-y", "--yes", action="store_true", help="跳过确认")

    # info
    pinfo = subparsers.add_parser("info", help="文件信息")
    pinfo.add_argument("remote", help="远程路径")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    command_map = {
        "upload": cmd_upload,
        "download": cmd_download,
        "gen-url": cmd_gen_url,
        "list": cmd_list,
        "delete": cmd_delete,
        "info": cmd_info,
    }

    command_map[args.command](args)


if __name__ == "__main__":
    main()
