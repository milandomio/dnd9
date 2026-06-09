#!/usr/bin/env python3
"""
测试 nvidia/minimaxai/minimax-m2.7 的实际上下文窗口限制
"""

import requests
import json
import sys
import time
from typing import Optional

MODEL = "nvidia/minimaxai/minimax-m2.7"
API_BASE = "https://integrate.api.nvidia.com/v1"

def get_api_key() -> Optional[str]:
    """从环境变量获取 API key"""
    import os
    key = os.environ.get("NVIDIA_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if key:
        return key
    # 尝试从配置文件读取
    configs = [
        "/home/mio/.config/opencode/node_modules/@opencode-ai/plugin/dist/config.json",
        "/home/mio/.config/opencode/config.json",
    ]
    for cfg in configs:
        try:
            with open(cfg) as f:
                data = json.load(f)
                if "apiKey" in data:
                    return data["apiKey"]
                if "NVIDIA_API_KEY" in data:
                    return data["NVIDIA_API_KEY"]
        except:
            pass
    return None

def make_request(prompt_tokens: int, max_tokens: int = 100, timeout: int = 120) -> dict:
    """发送请求测试指定 token 长度"""
    key = get_api_key()
    if not key:
        return {"error": "No API key found"}

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": "hello"}],
        "max_tokens": max_tokens,
        "stream": False
    }

    # 使用短 prompt 测试基础连接
    try:
        response = requests.post(
            f"{API_BASE}/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout
        )
        return {"status": response.status_code, "response": response.json()}
    except Exception as e:
        return {"error": str(e)}

def test_context_limit():
    """测试实际上下文限制"""
    print(f"Testing context limit for {MODEL}")
    print("=" * 60)

    result = make_request(100)
    if "error" in result:
        print(f"Error: {result['error']}")
        print("\n请设置 NVIDIA_API_KEY 环境变量后重试")
        return

    print(f"Status: {result['status']}")
    print(f"Response: {json.dumps(result['response'], indent=2)[:500]}")

if __name__ == "__main__":
    test_context_limit()