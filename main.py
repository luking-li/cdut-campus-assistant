"""
成都理工大学校园信息助手 - 主程序
自动监控考试安排、成绩发布、课表变动，推送到个人微信。
"""

import os
import json
import sys
import hashlib
from datetime import datetime

# 加载 .env 文件（本地运行时自动读取）
def _load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    key, val = key.strip(), val.strip()
                    if key and val and key not in os.environ:
                        os.environ[key] = val

_load_env()

import auth
import scraper
import notifier


CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache.json")


def load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"exam_ids": [], "grade_ids": [], "timetable_hash": ""}


def save_cache(cache: dict):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def format_exam_message(exams: list[dict]) -> str:
    lines = ["📝 **考试安排更新**"]
    for e in exams:
        lines.append("")
        lines.append("📖 %s" % e.get("course", ""))
        if e.get("status"):
            lines.append("📋 %s" % e["status"])
        if e.get("time_str"):
            lines.append("⏰ %s" % e["time_str"])
        if e.get("classroom"):
            lines.append("🏫 %s" % e["classroom"])
        if e.get("teachers"):
            lines.append("👨‍🏫 %s" % e["teachers"])
    return "\n".join(lines)


def format_grade_message(grades: list[dict]) -> str:
    lines = ["📊 **新成绩发布**"]
    for g in grades:
        lines.append("")
        line = "📖 %s" % g.get("course", "")
        if g.get("score"):
            line += " — %s分" % g["score"]
        lines.append(line)
        details = []
        if g.get("credit"):
            details.append("学分: %s" % g["credit"])
        if g.get("gpa"):
            details.append("绩点: %s" % g["gpa"])
        if details:
            lines.append("  %s" % " | ".join(details))
    return "\n".join(lines)


def format_timetable_message(items: list[dict]) -> str:
    lines = ["📅 **课表更新**"]
    for item in items:
        lines.append("")
        lines.append("📖 %s" % item.get("course", ""))
        if item.get("classroom"):
            lines.append("🏫 %s" % item["classroom"])
    return "\n".join(lines)


def main():
    print("=" * 50)
    print("🎓 CDUT 校园信息助手 - %s" % datetime.now().strftime("%Y-%m-%d %H:%M"))
    print("=" * 50)

    open_id = os.environ.get("OPEN_ID", "")
    if not open_id:
        print("❌ 错误: 请配置 OPEN_ID 环境变量或 .env 文件")
        sys.exit(1)

    pw, browser, context, page = None, None, None, None

    try:
        print("\n--- 登录走我平台 ---")
        pw, browser, context, page = auth.login_openid(open_id)
        scraper.init_session(page, open_id)

        cache = load_cache()
        has_new_content = False

        # --- 考试安排 ---
        print("\n--- 检查考试安排 ---")
        try:
            current_exams = scraper.fetch_exams(page, open_id)
            cached_exam_ids = set(cache.get("exam_ids", []))
            new_exams = [e for e in current_exams
                         if e.get("course", "") + "|" + e.get("time_str", "") not in cached_exam_ids]

            if new_exams:
                print("发现 %d 条新考试安排！" % len(new_exams))
                msg = format_exam_message(new_exams)
                notifier.send_message("📝 考试安排更新", msg)
                has_new_content = True

            cache["exam_ids"] = [
                e.get("course", "") + "|" + e.get("time_str", "") for e in current_exams
            ]
        except Exception as e:
            print("⚠️ 考试安排检查失败: %s" % e)

        # --- 成绩 ---
        print("\n--- 检查成绩 ---")
        try:
            current_grades = scraper.fetch_grades(page, open_id)
            cached_grade_ids = set(cache.get("grade_ids", []))
            new_grades = [g for g in current_grades
                          if g.get("course", "") + "|" + g.get("score", "") not in cached_grade_ids]

            if new_grades:
                print("发现 %d 条新成绩！" % len(new_grades))
                msg = format_grade_message(new_grades)
                notifier.send_message("📊 新成绩发布", msg)
                has_new_content = True

            cache["grade_ids"] = [
                g.get("course", "") + "|" + g.get("score", "") for g in current_grades
            ]
        except Exception as e:
            print("⚠️ 成绩检查失败: %s" % e)

        # --- 课表 ---
        print("\n--- 检查课表 ---")
        try:
            current_timetable = scraper.fetch_timetable(page, open_id)
            timetable_str = json.dumps(current_timetable, ensure_ascii=False, sort_keys=True)
            timetable_hash = hashlib.md5(timetable_str.encode()).hexdigest()

            if timetable_hash != cache.get("timetable_hash", "") and cache.get("timetable_hash"):
                print("课表有变动！")
                msg = format_timetable_message(current_timetable)
                notifier.send_message("📅 课表变动", msg)
                has_new_content = True

            cache["timetable_hash"] = timetable_hash
        except Exception as e:
            print("⚠️ 课表检查失败: %s" % e)

        save_cache(cache)

        print("\n" + "=" * 50)
        if has_new_content:
            print("✅ 检查完成，有新内容已推送！")
        else:
            print("✅ 检查完成，暂无新内容。")
        print("=" * 50)

    finally:
        auth.close(pw, browser, context)


if __name__ == "__main__":
    main()
