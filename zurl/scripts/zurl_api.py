#!/usr/bin/env python3
"""
Zurl 短链接管理 API 封装。
API 地址：环境变量 ZURL_APIURL
Token：环境变量 ZURL_TOKEN

Content-Type 分配：
  - application/json: shorten_url, update_url, search, delete/urls (批量)
  - application/x-www-form-urlencoded: delete_url (单个), get_url_metadata
"""

import json
import os
import random
import string
import sys
import urllib.parse
import urllib.request
import urllib.error
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.environ.get("ZURL_APIURL", "").rstrip("/")
# 对外展示的短链接域名列表（逗号分隔，末尾不带斜杠）
# 不设置时默认使用 ZURL_APIURL 的值
_DISPLAY_RAW = os.environ.get("ZURL_DISPLAY_URLS", "").strip()
DISPLAY_URLS = (
    [u.strip() for u in _DISPLAY_RAW.split(",") if u.strip()]
    if _DISPLAY_RAW
    else [BASE_URL]
)


if not BASE_URL:
    print("Error: ZURL_APIURL environment variable is not set", file=sys.stderr)
    sys.exit(1)


class ZurlAPI:
    def __init__(self):
        self.token = os.environ.get("ZURL_TOKEN", "")

    def _request(self, method, path, data=None, content_type="application/json"):
        """发送 HTTP 请求。"""
        url = f"{BASE_URL}{path}"
        headers = {"Content-Type": content_type}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        if data and content_type == "application/json":
            body = json.dumps(data).encode("utf-8")
        elif data and content_type == "application/x-www-form-urlencoded":
            body = urllib.parse.urlencode(data).encode("utf-8")
        else:
            body = None

        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            try:
                err_json = json.loads(err_body)
                return {"error": True, "status": e.code, "detail": err_json}
            except json.JSONDecodeError:
                return {"error": True, "status": e.code, "detail": err_body}
        except Exception as e:
            return {"error": True, "detail": str(e)}

    def _generate_short_code(self, length=4):
        """生成随机短链接代号（大小写字母 + 数字）。"""
        chars = string.ascii_letters + string.digits
        return "".join(random.choice(chars) for _ in range(length))

    def _expand_urls(self, short_url):
        """将 short_url 扩展为三个域名的完整短链接列表。"""
        return [f"{domain}/{short_url}" for domain in DISPLAY_URLS]

    def _is_success(self, result):
        """判断 API 返回是否成功。"""
        if result.get("error"):
            return False
        code = result.get("code", result.get("status", 0))
        return code == 200

    def _extract_items(self, result, field="data"):
        """从 API 返回中提取数据列表。"""
        data = result.get(field, {})
        if isinstance(data, dict):
            return data.get("urls", data.get("items", []))
        return data if isinstance(data, list) else []

    # ========== 公开 API 方法 ==========

    def shorten(self, long_url, short_url=None, title=None, description=None, ttl_days=None):
        """
        创建短链接 (application/json)。
        - long_url: 原始长链接（必填）
        - short_url: 自定义短链接代号，不填则自动生成4位随机字符
        - title / description / ttl_days: 可选
        """
        if not short_url:
            short_url = self._generate_short_code()

        payload = {"long_url": long_url, "short_url": short_url}
        if title:
            payload["title"] = title
        if description:
            payload["description"] = description
        if ttl_days is not None:
            payload["ttl_days"] = ttl_days

        result = self._request("POST", "/api/shorten_url", payload)
        if self._is_success(result):
            actual_short = result.get("data", {}).get("short_url", short_url)
            result["short_links"] = self._expand_urls(actual_short)
        return result

    def update(self, url_id, **kwargs):
        """
        更新短链接 (application/json)。
        - url_id: 短链接 ID（必填）
        可选字段：long_url, short_url, title, description, ttl_days
        注意：short_url 必须传有效值，空字符串会导致 500。
        """
        allowed = ("long_url", "short_url", "title", "description", "ttl_days")
        payload = {k: v for k, v in kwargs.items() if k in allowed and v is not None and v != ""}

        result = self._request("POST", f"/api/update_url/{url_id}", payload)
        if self._is_success(result):
            actual_short = kwargs.get("short_url") or result.get("data", {}).get("short_url", "")
            if actual_short:
                result["short_links"] = self._expand_urls(actual_short)
        return result

    def delete(self, short_url):
        """
        删除单个短链接 (POST, application/x-www-form-urlencoded)。
        """
        return self._request("POST", "/api/delete/url",
                             {"short_url": short_url},
                             content_type="application/x-www-form-urlencoded")

    def delete_batch(self, ids):
        """
        批量删除短链接 (application/json)。
        """
        return self._request("POST", "/api/delete/urls", {"ids": ids})

    def list_urls(self, page=1, limit=10):
        """获取短链接列表 (GET)。"""
        result = self._request("GET", f"/api/urls?page={page}&limit={limit}")
        if self._is_success(result):
            for item in self._extract_items(result):
                s = item.get("short_url", "")
                if s:
                    item["short_links"] = self._expand_urls(s)
        return result

    def search(self, keyword, filter_type="all"):
        """
        搜索短链接 (application/json)。
        - filter_type: all / long_url / short_url / title
        """
        payload = {"keyword": keyword, "filter": filter_type}
        result = self._request("POST", "/api/search", payload)
        if self._is_success(result):
            for item in self._extract_items(result):
                s = item.get("short_url", "")
                if s:
                    item["short_links"] = self._expand_urls(s)
        return result

    def get_metadata(self, url):
        """
        获取 URL 元数据 (POST, application/x-www-form-urlencoded)。
        返回目标网页的标题和描述。
        """
        return self._request("POST", "/api/get_url_metadata",
                             {"url": url},
                             content_type="application/x-www-form-urlencoded")


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": True, "detail": "Usage: zurl_api.py <action> [args...]"}))
        sys.exit(1)

    action = sys.argv[1]
    api = ZurlAPI()

    if action == "shorten":
        # zurl_api.py shorten <long_url> [short_url] [title] [description] [ttl_days]
        long_url = sys.argv[2] if len(sys.argv) > 2 else ""
        short_url = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] else None
        title = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] else None
        description = sys.argv[5] if len(sys.argv) > 5 and sys.argv[5] else None
        ttl_days = int(sys.argv[6]) if len(sys.argv) > 6 and sys.argv[6] else None
        print(json.dumps(api.shorten(long_url, short_url, title, description, ttl_days), ensure_ascii=False))

    elif action == "update":
        # zurl_api.py update <id> [long_url] [short_url] [title] [description] [ttl_days]
        url_id = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        kwargs = {}
        if len(sys.argv) > 3 and sys.argv[3]:
            kwargs["long_url"] = sys.argv[3]
        if len(sys.argv) > 4 and sys.argv[4]:
            kwargs["short_url"] = sys.argv[4]
        if len(sys.argv) > 5 and sys.argv[5]:
            kwargs["title"] = sys.argv[5]
        if len(sys.argv) > 6 and sys.argv[6]:
            kwargs["description"] = sys.argv[6]
        if len(sys.argv) > 7 and sys.argv[7]:
            kwargs["ttl_days"] = int(sys.argv[7])
        print(json.dumps(api.update(url_id, **kwargs), ensure_ascii=False))

    elif action == "delete":
        # zurl_api.py delete <short_url>
        short_url = sys.argv[2] if len(sys.argv) > 2 else ""
        print(json.dumps(api.delete(short_url), ensure_ascii=False))

    elif action == "delete_batch":
        # zurl_api.py delete_batch <short_url1,short_url2,...>
        short_urls = [x.strip() for x in sys.argv[2].split(",")]
        # 先查列表找到每个 short_url 对应的 id
        result = api.list_urls(1, 100)
        ids = []
        if api._is_success(result):
            url_map = {u["short_url"]: u["id"] for u in result["data"].get("urls", [])}
            for s in short_urls:
                if s in url_map:
                    ids.append(url_map[s])
        if ids:
            print(json.dumps(api.delete_batch(ids), ensure_ascii=False))
        else:
            print(json.dumps({"error": True, "detail": "未找到匹配的短链接"}, ensure_ascii=False))

    elif action == "list":
        # zurl_api.py list [page] [limit]
        page = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        print(json.dumps(api.list_urls(page, limit), ensure_ascii=False))

    elif action == "search":
        # zurl_api.py search <keyword> [filter_type]
        keyword = sys.argv[2] if len(sys.argv) > 2 else ""
        filter_type = sys.argv[3] if len(sys.argv) > 3 else "all"
        print(json.dumps(api.search(keyword, filter_type), ensure_ascii=False))

    elif action == "metadata":
        # zurl_api.py metadata <url>
        url = sys.argv[2] if len(sys.argv) > 2 else ""
        print(json.dumps(api.get_metadata(url), ensure_ascii=False))

    else:
        print(json.dumps({"error": True, "detail": f"Unknown action: {action}"}))


if __name__ == "__main__":
    main()
