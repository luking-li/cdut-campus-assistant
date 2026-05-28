"""
推送模块 - Server酱
通过 Server酱 将通知推送到个人微信。
官网: https://sct.ftqq.com/
"""

import os
import requests


def _get_key() -> str:
    key = os.environ.get("SERVERCHAN_KEY", "")
    if not key:
        raise RuntimeError(
            "未配置 SERVERCHAN_KEY。\n"
            "请访问 https://sct.ftqq.com/ 注册并获取 SendKey，"
            "然后配置到 GitHub Secrets 或 .env 文件。"
        )
    return key


def send_message(title: str, content: str) -> bool:
    key = _get_key()
    url = "https://sctapi.ftqq.com/%s.send" % key
    payload = {"title": title, "desp": content}

    try:
        resp = requests.post(url, json=payload, timeout=15)
        if resp.status_code == 200:
            result = resp.json()
            if result.get("code") == 0:
                print("[push] ✅ 推送成功: %s" % title)
                return True
            else:
                print("[push] ⚠️ 推送失败: %s" % result.get("message", "未知错误"))
                return False
        else:
            print("[push] ⚠️ HTTP 错误: %d" % resp.status_code)
            return False
    except Exception as e:
        print("[push] ⚠️ 推送异常: %s" % e)
        return False
