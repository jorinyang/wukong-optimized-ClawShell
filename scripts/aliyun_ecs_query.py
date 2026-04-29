#!/usr/bin/env python3
"""
阿里云 ECS API 调用工具
用法: python3 aliyun_ecs_query.py [action] [region]
示例: python3 aliyun_ecs_query.py DescribeInstances cn-hangzhou
"""

import json
import os
import hmac
import hashlib
import base64
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

# 加载凭证
CREDENTIALS_FILE = os.path.expanduser("~/.openclaw/credentials/aliyun-ecs.json")

def load_credentials():
    with open(CREDENTIALS_FILE) as f:
        data = json.load(f)
    return data["aliyun"]["access_key_id"], data["aliyun"]["access_key_secret"]

ACCESS_KEY_ID, ACCESS_KEY_SECRET = load_credentials()

def generate_signature(method, path, params, secret):
    """生成 HMAC-SHA1 签名"""
    sorted_params = sorted(params.items())
    canonicalized_query = "&".join([f"{k}={urllib.parse.quote(str(v), safe='')}" for k, v in sorted_params])
    string_to_sign = f"{method}&{urllib.parse.quote(path, safe='')}&{urllib.parse.quote(canonicalized_query, safe='')}"
    h = hmac.new(f"{secret}&".encode(), string_to_sign.encode(), hashlib.sha1)
    return base64.b64encode(h.digest()).decode()

def call_aliyun_api(action, region="cn-hangzhou"):
    """调用阿里云 API"""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    params = {
        "Format": "JSON",
        "Version": "2014-05-26",
        "SignatureMethod": "HMAC-SHA1",
        "Timestamp": timestamp,
        "SignatureVersion": "1.0",
        "SignatureNonce": str(int(datetime.now().timestamp() * 1000)),
        "AccessKeyId": ACCESS_KEY_ID,
        "Action": action,
        "RegionId": region,
    }
    
    # 生成签名
    signature = generate_signature("POST", "/", params, ACCESS_KEY_SECRET)
    params["Signature"] = signature
    
    # 发送请求
    url = f"https://ecs.{region}.aliyuncs.com/"
    data = urllib.parse.urlencode(params).encode()
    
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import sys
    
    action = sys.argv[1] if len(sys.argv) > 1 else "DescribeInstances"
    region = sys.argv[2] if len(sys.argv) > 2 else "cn-hangzhou"
    
    print(f"调用阿里云 ECS API: {action} (Region: {region})")
    print(f"AccessKey ID: {ACCESS_KEY_ID[:8]}...")
    print()
    
    result = call_aliyun_api(action, region)
    
    if "error" in result:
        print(f"错误: {result['error']}")
    elif "Message" in result and "Code" in result:
        print(f"API错误: {result['Code']} - {result['Message']}")
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))
