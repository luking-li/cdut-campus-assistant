"""
PushPlus 推送模块
通过 PushPlus 将通知推送到个人微信。
PushPlus 官网: https://www.pushplus.plus/
"""

import os
import requests


PUSHPLUS_API = "http://www.pushplus.plus/send"


def get_token() -> str:
    """从环境变量获取 PushPlus Token"""
    token = os.environ.get("PUSHPLUS_TOKEN", "")
    if not token:
        raise RuntimeError(
            "未配置 PUSHPLUS_TOKEN 环境变量。\n"
            "请访问 https://www.pushplus.plus/ 注册并获取 Token，"
            "然后在 GitHub Secrets 中添加 PUSHPLUS_TOKEN。"
        )
    return token


def send_message(title: str, content: str, template: str = "markdown") -> bool:
    """
    通过 PushPlus 发送消息。

    Args:
        title: 消息标题
        content: 消息内容（支持 Markdown 或 HTML）
        template: 模板类型，可选 "html"、"markdown"、"txt"

    Returns:
        是否发送成功
    """
    token = get_token()

    payload = {
        "token": token,
        "title": title,
        "content": content,
        "template": template,
    }

    try:
        resp = requests.post(PUSHPLUS_API, json=payload, timeout=15)
        if resp.status_code == 200:
            result = resp.json()
            if result.get("code") == 200:
                print(f"[push] ✅ 推送成功: {title}")
                return True
            else:
                print(f"[push] ⚠️ 推送失败: {result.get('msg', '未知错误')}")
                return False
        else:
            print(f"[push] ⚠️ HTTP 错误: {resp.status_code}")
            return False
    except Exception as e:
        print(f"[push] ⚠️ 推送异常: {e}")
        return False


def send_exam_update(content: str) -> bool:
    """推送考试安排更新"""
    return send_message("📝 考试安排更新", content)


def send_exam_reminder(content: str) -> bool:
    """推送考试提醒"""
    return send_message("⏰ 考试提醒", content)


def send_grade_update(content: str) -> bool:
    """推送成绩更新"""
    return send_message("📊 新成绩发布", content)


def send_notice_update(content: str) -> bool:
    """推送教务通知"""
    return send_message("📢 教务通知", content)


def test_push() -> bool:
    """发送测试消息"""
    content = (
        "🎉 **校园助手测试消息**\n\n"
        "如果你看到这条消息，说明 PushPlus 推送配置成功！\n\n"
        "---\n"
        "来自 CDUT 校园信息助手"
    )
    return send_message("✅ 校园助手测试", content)
