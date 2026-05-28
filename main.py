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
        with open(env_path, "r", encoding="utf-8-sig") as f:
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
    return {"exam_ids": [], "grade_ids": [], "timetable_hash": "", "first_run": True}


def save_cache(cache: dict):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def format_exam_message(exams: list[dict]) -> str:
    lines = ["\U0001f4dd **考试安排更新**"]
    for e in exams:
        lines.append("")
        lines.append("\U0001f4d6 %s" % e.get("course", ""))
        if e.get("status"):
            lines.append("\U0001f4cb %s" % e["status"])
        if e.get("time_str"):
            lines.append("\u23f0 %s" % e["time_str"])
        if e.get("classroom"):
            lines.append("\U0001f3eb %s" % e["classroom"])
        if e.get("teachers"):
            lines.append("\U0001f468\u200d\U0001f3eb %s" % e["teachers"])
    return "\n".join(lines)


def format_grade_message(grades: list[dict]) -> str:
    lines = ["\U0001f4ca **新成绩发布**"]
    for g in grades:
        lines.append("")
        line = "\U0001f4d6 %s" % g.get("course", "")
        if g.get("score"):
            line += " \u2014 %s\u5206" % g["score"]
        lines.append(line)
        details = []
        if g.get("credit"):
            details.append("\u5b66\u5206: %s" % g["credit"])
        if g.get("gpa"):
            details.append("\u7ee9\u70b9: %s" % g["gpa"])
        if details:
            lines.append("  %s" % " | ".join(details))
    return "\n".join(lines)


def format_timetable_message(items: list[dict]) -> str:
    lines = ["\U0001f4c5 **课表更新**"]
    for item in items:
        lines.append("")
        lines.append("\U0001f4d6 %s" % item.get("course", ""))
        if item.get("classroom"):
            lines.append("\U0001f3eb %s" % item["classroom"])
    return "\n".join(lines)


def main():
    print("=" * 50)
    print("\U0001f393 CDUT 校园信息助手 - %s" % datetime.now().strftime("%Y-%m-%d %H:%M"))
    print("=" * 50)

    open_id = os.environ.get("OPEN_ID", "")
    if not open_id:
        print("\u274c 错误: 请配置 OPEN_ID 环境变量或 .env 文件")
        sys.exit(1)

    pw, browser, context, page = None, None, None, None

    try:
        print("\n--- 登录走我平台 ---")
        pw, browser, context, page = auth.login_openid(open_id)
        scraper.init_session(page, open_id)

        cache = load_cache()
        is_first_run = cache.get("first_run", True)
        has_new_content = False

        if is_first_run:
            print("\n\u23f3 首次运行，仅缓存当前数据，不发送通知。")

        # --- 考试安排 ---
        print("\n--- 检查考试安排 ---")
        try:
            current_exams = scraper.fetch_exams(page, open_id)
            cached_exam_ids = set(cache.get("exam_ids", []))
            new_exams = [e for e in current_exams
                         if e.get("course", "") + "|" + e.get("time_str", "") not in cached_exam_ids]

            if new_exams:
                print("发现 %d 条新考试安排！" % len(new_exams))
                if not is_first_run:
                    msg = format_exam_message(new_exams)
                    notifier.send_message("\U0001f4dd 考试安排更新", msg)
                    has_new_content = True
                else:
                    print("  (首次运行，跳过推送)")

            cache["exam_ids"] = [
                e.get("course", "") + "|" + e.get("time_str", "") for e in current_exams
            ]
        except Exception as e:
            print("\u26a0\ufe0f 考试安排检查失败: %s" % e)

        # --- 成绩 ---
        print("\n--- 检查成绩 ---")
        try:
            current_grades = scraper.fetch_grades(page, open_id)
            cached_grade_ids = set(cache.get("grade_ids", []))
            new_grades = [g for g in current_grades
                          if g.get("course", "") + "|" + g.get("score", "") not in cached_grade_ids]

            if new_grades:
                print("发现 %d 条新成绩！" % len(new_grades))
                if not is_first_run:
                    msg = format_grade_message(new_grades)
                    notifier.send_message("\U0001f4ca 新成绩发布", msg)
                    has_new_content = True
                else:
                    print("  (首次运行，跳过推送)")

            cache["grade_ids"] = [
                g.get("course", "") + "|" + g.get("score", "") for g in current_grades
            ]
        except Exception as e:
            print("\u26a0\ufe0f 成绩检查失败: %s" % e)

        # --- 课表 ---
        print("\n--- 检查课表 ---")
        try:
            current_timetable = scraper.fetch_timetable(page, open_id)
            timetable_str = json.dumps(current_timetable, ensure_ascii=False, sort_keys=True)
            timetable_hash = hashlib.md5(timetable_str.encode()).hexdigest()

            if timetable_hash != cache.get("timetable_hash", "") and cache.get("timetable_hash"):
                print("课表有变动！")
                if not is_first_run:
                    msg = format_timetable_message(current_timetable)
                    notifier.send_message("\U0001f4c5 课表变动", msg)
                    has_new_content = True
                else:
                    print("  (首次运行，跳过推送)")

            cache["timetable_hash"] = timetable_hash
        except Exception as e:
            print("\u26a0\ufe0f 课表检查失败: %s" % e)

        cache["first_run"] = False
        save_cache(cache)

        print("\n" + "=" * 50)
        if has_new_content:
            print("\u2705 检查完成，有新内容已推送！")
        else:
            print("\u2705 检查完成，暂无新内容。")
        print("=" * 50)

    finally:
        auth.close(pw, browser, context)


if __name__ == "__main__":
    main()
