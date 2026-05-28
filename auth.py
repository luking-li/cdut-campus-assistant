"""
认证模块 - 成都理工大学教务系统
支持两种模式:
  1. CAS 登录（通过 cas.paas.cdut.edu.cn）
  2. OpenId 直连（走我平台 cdutdev.zouwo.tech）
"""

import os
import time
from playwright.sync_api import sync_playwright


CAS_URL = (
    "https://cas.paas.cdut.edu.cn/cas/login"
    "?service=http%3A%2F%2Fjw.cdut.edu.cn%2Fsso%2Flogin.jsp"
    "%3FtargetUrl%3Dbase64aHR0cDovL2p3LmNkdXQuZWR1LmNu"
    "L0xvZ29uLmRvP21ldGhvZD1sb2dvblNTT2NkbGdkeA%3D%3D"
)

CHROMIUM_PATH = os.environ.get(
    "CHROMIUM_PATH",
    r"C:\Users\asd\AppData\Local\ms-playwright\chromium-1223\chrome-win64\chrome.exe",
)


def _launch_browser(playwright, headless=True):
    args = ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]
    try:
        browser = playwright.chromium.launch(
            headless=headless, executable_path=CHROMIUM_PATH,
            args=args, timeout=15000,
        )
    except Exception:
        browser = playwright.chromium.launch(
            headless=headless, args=args, timeout=30000,
        )
    return browser


def login_cas(student_id: str, password: str, headless=True):
    """
    通过 CAS 登录教务系统。
    Returns: (pw, browser, context, page)
    """
    pw = sync_playwright().start()
    browser = _launch_browser(pw, headless=headless)
    context = browser.new_context()
    page = context.new_page()

    page.goto(CAS_URL, wait_until="networkidle", timeout=30000)

    page.evaluate(
        """([sid, pwd]) => {
        const vm = document.querySelector('#vue_main').__vue__;
        vm.passwordLoginUsername = sid;
        vm.passwordLoginPassword = pwd;
    }""",
        [student_id, password],
    )

    with page.expect_navigation(timeout=30000, wait_until="load"):
        page.evaluate(r"""() => {
            const vm = document.querySelector('#vue_main').__vue__;
            vm.submitForm();
        }""")

    time.sleep(3)
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass

    current_url = page.url
    is_on_cas = "cas.paas.cdut.edu.cn/cas/login" in current_url

    if is_on_cas:
        for eid in ["loginError1", "loginError2"]:
            el = page.query_selector(f"#{eid}")
            if el:
                txt = el.inner_text().strip()
                if txt:
                    raise RuntimeError(f"CAS 登录失败：{txt}")
        raise RuntimeError("CAS 登录失败：未跳转到教务系统")

    print("[auth] CAS 登录成功，当前URL:", page.url)
    return pw, browser, context, page


def login_openid(open_id: str, headless=True):
    """
    通过 OpenId 直连走我平台（cdutdev.zouwo.tech）。
    Returns: (pw, browser, context, page)
    """
    pw = sync_playwright().start()
    browser = _launch_browser(pw, headless=headless)
    context = browser.new_context()
    page = context.new_page()

    # 设置 OpenId cookie
    context.add_cookies([{
        "name": "OpenId",
        "value": open_id,
        "domain": "cdutdev.zouwo.tech",
        "path": "/",
    }])

    # 模拟微信小程序环境（走我平台会检测）
    page.add_init_script("""
        Object.defineProperty(window, '__wxjs_environment', {
            value: 'miniprogram', writable: false
        });
        if (!window.WeixinJSBridge) {
            window.WeixinJSBridge = { invoke: function(){}, on: function(){} };
        }
    """)

    print("[auth] 使用 OpenId 登录走我平台:", open_id[:20] + "...")
    return pw, browser, context, page


def close(pw, browser, context):
    for obj in (context, browser):
        try:
            obj.close()
        except Exception:
            pass
    try:
        pw.stop()
    except Exception:
        pass
