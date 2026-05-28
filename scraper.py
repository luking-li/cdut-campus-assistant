"""
页面抓取模块 - Playwright 渲染 Blazor 页面 + 文本提取
目标站点: cdutdev.zouwo.tech（走我平台，Blazor Server 架构）
"""

import re
import time
from playwright.sync_api import Page


ZOUWO_BASE = "https://cdutdev.zouwo.tech"


def init_session(page: Page, open_id: str):
    """打开首页，建立 Blazor 会话。"""
    print("[scraper] 建立 Blazor 会话...")
    page.goto(
        ZOUWO_BASE + "/?q=" + open_id,
        wait_until="networkidle",
        timeout=30000,
    )
    time.sleep(3)
    try:
        page.wait_for_selector("text=成绩单", timeout=15000)
        print("[scraper] 会话建立成功")
    except Exception:
        print("[scraper] ⚠️ 未检测到导航菜单")

    # 关闭隐私弹窗
    try:
        accept_btn = page.query_selector("#accept-btn")
        if accept_btn and accept_btn.is_visible():
            accept_btn.click()
            time.sleep(1)
            print("[scraper] 已关闭隐私弹窗")
    except Exception:
        pass


def _go_home(page: Page, open_id: str):
    """回到首页"""
    page.goto(ZOUWO_BASE + "/?q=" + open_id, wait_until="networkidle", timeout=30000)
    time.sleep(3)


def _navigate_and_extract(page: Page, link_text: str, open_id: str = "", wait_sec: float = 15) -> str:
    """通过点击链接导航到目标页面，返回页面文本。"""
    # 如果不在首页，先回去
    if "/?q=" not in page.url:
        _go_home(page, open_id)

    print("[scraper] 导航到: %s" % link_text)
    page.click("text=%s" % link_text, timeout=8000)
    time.sleep(wait_sec)
    text = page.inner_text("body")
    print("[scraper] 文本长度: %d" % len(text))
    return text


# ==================== 考试安排 ====================

def fetch_exams(page: Page, open_id: str = "") -> list[dict]:
    """抓取考试安排"""
    print("\n[scraper] === 抓取考试安排 ===")
    text = _navigate_and_extract(page, "考试安排", open_id)

    exams = []
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    i = 0
    while i < len(lines):
        line = lines[i]

        # 寻找考试状态行
        if re.search(r"\d+\s*天后(开始|结束)|已结束|进行中", line):
            exam = {
                "course": lines[i - 1] if i > 0 else "",
                "status": line,
                "time_str": "",
                "classroom": "",
                "teachers": "",
            }

            for j in range(i + 1, min(i + 6, len(lines))):
                l = lines[j]
                if re.search(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", l) or re.search(r"\d{1,2}:\d{2}~", l):
                    exam["time_str"] = l
                elif l.startswith("🏠") or re.match(r"^[EBCA]\d", l):
                    exam["classroom"] = l
                elif "🧑" in l or "🏫" in l:
                    exam["teachers"] = l.replace("🧑\u200d🏫 ", "")
                elif re.search(r"\d+\s*天后|已结束|进行中", l):
                    break

            if exam["course"]:
                exams.append(exam)
        i += 1

    print("[scraper] 解析出 %d 条考试" % len(exams))
    return exams


# ==================== 成绩 ====================

def fetch_grades(page: Page, open_id: str = "") -> list[dict]:
    """抓取成绩（制表符分隔格式）"""
    print("\n[scraper] === 抓取成绩 ===")
    text = _navigate_and_extract(page, "成绩单", open_id)

    grades = []
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    current_semester = ""
    for line in lines:
        # 检测学期标识
        if re.match(r"^\d{4}-\d{4}-\d$", line):
            current_semester = line
            continue

        # 跳过表头和统计行
        if line.startswith("课程 ") or line.startswith("学期平均"):
            continue
        if line in ("成绩分析", "详细成绩", "必修", "选修", "公选"):
            continue
        if re.match(r"^课程数\t", line):
            continue

        # 成绩行：制表符分隔，至少有 课程名\t成绩\t学分\t绩点
        parts = line.split("\t")
        if len(parts) >= 4 and current_semester:
            course = parts[0].strip()
            score = parts[1].strip()
            credit = parts[2].strip()
            gpa = parts[3].strip()

            # 验证：成绩应该是数字或"优"等
            if course and (score.replace(".", "").isdigit() or score in ("优", "良", "中", "及格", "不及格")):
                grade = {
                    "course": course,
                    "score": score,
                    "credit": credit,
                    "gpa": gpa,
                    "type": parts[4].strip() if len(parts) > 4 else "",
                    "semester": current_semester,
                }
                grades.append(grade)

    print("[scraper] 解析出 %d 条成绩" % len(grades))
    return grades


# ==================== 课表 ====================

def fetch_timetable(page: Page, open_id: str = "") -> list[dict]:
    """抓取课表"""
    print("\n[scraper] === 抓取课表 ===")
    text = _navigate_and_extract(page, "课表 入口 #1", open_id, wait_sec=20)

    items = []
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # 课表是周历视图，课程名和教室交替出现
    i = 0
    while i < len(lines):
        line = lines[i]

        # 跳过时间/周次/导航标识
        if (re.match(r"^\d+:\d+$", line) or re.match(r"^\d+ 月$", line)
                or line in ("🏠", "周一", "周二", "周三", "周四", "周五", "周六", "周日")
                or re.match(r"^\d{1,2}$", line)):
            i += 1
            continue

        # 课程名后面跟着教室
        if i + 1 < len(lines):
            next_line = lines[i + 1]
            # 教室特征：以 E/C/B/A 开头，或包含"篮球场""操场"等
            is_classroom = (re.match(r"^[EBCA]\d", next_line) or "篮球场" in next_line
                           or "操场" in next_line or "体育馆" in next_line)
            # 排除导航文本
            is_nav = any(kw in line for kw in ("成绩", "课程表", "设置", "入口", "Simple", "课表", "关于"))

            if len(line) > 1 and is_classroom and not is_nav:
                items.append({"course": line, "classroom": next_line})
                i += 2
                continue

        i += 1

    # 去重
    seen = set()
    unique = []
    for item in items:
        key = "%s|%s" % (item["course"], item["classroom"])
        if key not in seen:
            seen.add(key)
            unique.append(item)

    print("[scraper] 解析出 %d 门课（去重后）" % len(unique))
    return unique
