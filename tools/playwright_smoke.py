import os
import re
import sys
import time
import traceback
from urllib.request import urlopen
from urllib.error import URLError

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
ADMIN_PATH = os.getenv("ADMIN_PATH", "admin/").strip("/")
SYSTEM_PATH = os.getenv("SYSTEM_PATH", "system/").strip("/")
REPORT_PATH = "playwright_report.txt"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def check_server():
    try:
        with urlopen(BASE + "/health/", timeout=5) as resp:
            if resp.status >= 400:
                raise RuntimeError(f"Health returned {resp.status}")
    except Exception as exc:
        print(f"Server check failed: {exc}")
        sys.exit(2)


def write_report(lines):
    with open(REPORT_PATH, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def safe_goto(page, url, label, errors):
    try:
        resp = page.goto(url, wait_until="domcontentloaded", timeout=15000)
        status = resp.status if resp else None
        if status and status >= 400:
            raise RuntimeError(f"HTTP {status}")
        return True
    except Exception as exc:
        errors.append((label, f"Navigation failed: {exc}"))
        return False


def login(page, username, password, errors, label):
    if not safe_goto(page, BASE + "/accounts/login/", f"{label}: login page", errors):
        return False
    page.fill("input[name='username']", username)
    page.fill("input[name='password']", password)
    page.click("button[type='submit']")
    page.wait_for_timeout(1000)
    if "/accounts/login/" in page.url:
        errors.append((label, "Login failed (still on login page)."))
        return False
    return True


def click_first(locator):
    if locator.count() == 0:
        return False
    locator.nth(0).click()
    return True


def test_cashier_flow(page, errors):
    label = "Cashier POS flow"
    page.add_init_script("""
(() => {
  const originalFetch = window.fetch;
  window.__fetchLogs = [];
  window.fetch = async (...args) => {
    try {
      const res = await originalFetch(...args);
      window.__fetchLogs.push({ url: res.url, status: res.status });
      return res;
    } catch (err) {
      const url = typeof args[0] === 'string' ? args[0] : (args[0] && args[0].url) || 'unknown';
      window.__fetchLogs.push({ url, error: String(err) });
      throw err;
    }
  };
})();
""")
    if not safe_goto(page, BASE + "/pos/", label, errors):
        return

    request_trace = {"sent": False, "failed": "", "status": None}
    console_errors = []
    def on_console(msg):
        if msg.type in ("error", "warning", "log"):
            console_errors.append(f"{msg.type}: {msg.text}")
    def on_page_error(exc):
        console_errors.append(f"pageerror: {exc}")
    def on_request(req):
        if "/orders/api/create/" in req.url:
            request_trace["sent"] = True
    def on_request_failed(req):
        if "/orders/api/create/" in req.url:
            failure = req.failure or {}
            request_trace["failed"] = failure.get("errorText", "") if isinstance(failure, dict) else str(failure)
    def on_response(resp):
        if "/orders/api/create/" in resp.url:
            request_trace["status"] = resp.status

    page.on("request", on_request)
    page.on("requestfailed", on_request_failed)
    page.on("response", on_response)
    page.on("console", on_console)
    page.on("pageerror", on_page_error)

    try:
        online_flag = page.evaluate("navigator.onLine")
        if not online_flag:
            errors.append((label, "Browser reports offline before payment."))
    except Exception:
        pass

    try:
        page.evaluate(
            "(() => { if (window.Alpine) { const d = Alpine.$data(document.querySelector('.pos-screen')); if (d && !d.__confirmWrapped) { const orig = d.confirmPayment; d.confirmPayment = async function(...args) { console.log('confirmPayment called'); return orig.apply(this, args); }; d.__confirmWrapped = true; } } })()"
        )
    except Exception:
        pass

    try:
        cookies = page.context.cookies(BASE)
        csrf_cookie = next((c for c in cookies if c.get("name") == "csrftoken"), None)
        if not csrf_cookie:
            errors.append((label, "CSRF cookie not found before payment."))
    except Exception:
        pass

    # Wait for products
    product_buttons = page.locator("button.btn.btn-light.border")
    try:
        product_buttons.first.wait_for(state="visible", timeout=15000)
    except Exception as exc:
        errors.append((label, f"No products visible: {exc}"))
        return

    click_first(product_buttons)
    # Confirm cart updated
    try:
        page.locator(".cart-list strong").first.wait_for(state="visible", timeout=5000)
    except Exception as exc:
        errors.append((label, f"Cart did not update after adding product: {exc}"))
        return

    # Confirm order -> payment
    confirm_btn = page.get_by_role("button", name=re.compile("تأكيد الطلب|Confirm Order", re.IGNORECASE))
    if confirm_btn.count() == 0:
        errors.append((label, "Confirm order button not found."))
        return
    confirm_btn.click()
    try:
        alpine_online = page.evaluate("document.querySelector('.pos-screen').__x?.$data?.online")
        if alpine_online is False:
            errors.append((label, "Alpine online flag is false after confirm."))
    except Exception:
        pass
    try:
        checkout_ready = page.evaluate(
            "window.Alpine ? Alpine.$data(document.querySelector('.pos-screen')).activeOrder?.checkoutReady : null"
        )
        if checkout_ready is not True:
            errors.append((label, f"checkoutReady not true after confirm (value={checkout_ready})."))
    except Exception:
        pass
    try:
        serialize_check = page.evaluate(
            "(() => { const d = Alpine.$data(document.querySelector('.pos-screen')); const o = d.activeOrder; const payload = {client_order_uuid: o?.client_order_uuid, created_at: new Date().toISOString(), branch_id: o?.branch_id || d.activeBranchId, order_type: o?.orderType, customer: null, items: (o?.cart || []).map(x => ({product_id: x.product_id, quantity: x.quantity})), payments: [{method: 'cash', amount: o?.preview?.total}], totals: o?.preview}; try { JSON.stringify(payload); return 'ok'; } catch (e) { return String(e); } })()"
        )
        if serialize_check != "ok":
            errors.append((label, f"Payload JSON stringify failed: {serialize_check}"))
    except Exception:
        pass
    manual_fetch = None
    try:
        manual_fetch = page.evaluate(
            "(() => { const d = Alpine.$data(document.querySelector('.pos-screen')); const o = d.activeOrder; const payload = {client_order_uuid: o?.client_order_uuid, created_at: new Date().toISOString(), branch_id: o?.branch_id || d.activeBranchId, order_type: o?.orderType, customer: null, items: (o?.cart || []).map(x => ({product_id: x.product_id, quantity: x.quantity})), payments: [{method: 'cash', amount: o?.preview?.total}], totals: o?.preview}; return fetch('/orders/api/create/', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': (window.getCsrfToken ? window.getCsrfToken() : '')}, body: JSON.stringify(payload)}).then(r => r.status).catch(e => 'error:' + String(e)); })()"
        )
    except Exception:
        manual_fetch = None

    # Choose payment method (cash)
    payment_btn = page.get_by_role("button", name=re.compile("نقدي|Cash", re.IGNORECASE))
    if payment_btn.count() == 0:
        errors.append((label, "Payment method button not found."))
        return
    # Capture create order response if it happens
    response_text = ""
    status_code = None
    try:
        with page.expect_response(lambda r: "/orders/api/create/" in r.url, timeout=15000) as resp_info:
            payment_btn.first.click()
            confirm_payment_btn = page.get_by_role("button", name=re.compile("تأكيد الدفع|Confirm Payment", re.IGNORECASE))
            if confirm_payment_btn.count() > 0:
                confirm_payment_btn.first.click()
            try:
                page.evaluate("Alpine.$data(document.querySelector('.pos-screen')).confirmPayment()")
            except Exception:
                pass
        resp = resp_info.value
        status_code = resp.status
        if status_code >= 400:
            response_text = resp.text()
    except Exception:
        # If no network response captured, still continue to UI check
        payment_btn.first.click()
        confirm_payment_btn = page.get_by_role("button", name=re.compile("تأكيد الدفع|Confirm Payment", re.IGNORECASE))
        if confirm_payment_btn.count() > 0:
            confirm_payment_btn.first.click()
        try:
            page.evaluate("Alpine.$data(document.querySelector('.pos-screen')).confirmPayment()")
        except Exception:
            pass

    # Wait for printing buttons to show
    try:
        page.get_by_role("button", name=re.compile("طباعة إيصال للعميل|Print Customer Receipt", re.IGNORECASE)).wait_for(timeout=15000)
    except Exception:
        err_text = ""
        alert = page.locator(".alert.alert-danger")
        if alert.count() > 0:
            err_text = alert.first.inner_text().strip()
        offline_notice = page.locator(".alert.alert-warning")
        offline_text = offline_notice.first.inner_text().strip() if offline_notice.count() > 0 else ""
        response_info = f"create_status={status_code}" if status_code is not None else "create_status=unknown"
        if response_text:
            response_info += f", response={response_text[:200]}"
        trace_info = f"request_sent={request_trace['sent']} request_failed={request_trace['failed']} request_status={request_trace['status']}"
        state_info = ""
        try:
            state = page.evaluate(
                "(() => { const d = Alpine.$data(document.querySelector('.pos-screen')); const o = d.activeOrder; return {cart: o?.cart?.length || 0, checkoutReady: o?.checkoutReady, branchId: o?.branch_id, paymentMethod: o?.paymentMethod, status: o?.status, previewTotal: o?.preview?.total, confirmPaymentType: typeof d.confirmPayment, csrfToken: (window.getCsrfToken ? window.getCsrfToken() : null)}; })()"
            )
            state["manualFetch"] = manual_fetch
            state_info = f" state={state}"
        except Exception:
            pass
        try:
            fetch_logs = page.evaluate("window.__fetchLogs || []")
            if fetch_logs:
                response_info += f", fetch_logs={fetch_logs[-3:]}"
        except Exception:
            pass
        console_info = (" console=" + " | ".join(console_errors[:3])) if console_errors else ""
        errors.append((label, f"Printing buttons not visible after payment. {err_text} {offline_text} {response_info} {trace_info}{state_info}{console_info}"))
        return


def test_kitchen_flow(page, errors):
    label = "Kitchen screen"
    if not safe_goto(page, BASE + "/orders/kitchen/", label, errors):
        return
    # If there are actions, try one
    actions = page.locator(".kitchen-action")
    if actions.count() > 0:
        actions.first.click()
        page.wait_for_timeout(1000)
        error_box = page.locator("#kitchenError")
        if error_box.count() and not error_box.first.get_attribute("class").endswith("d-none"):
            errors.append((label, f"Kitchen action error: {error_box.first.inner_text().strip()}"))


def run():
    check_server()
    errors = []
    checks = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(service_workers="block")
        page = context.new_page()

        # Public pages
        for path in ["/", "/features/", "/pricing/"]:
            ok = safe_goto(page, BASE + path, f"Public {path}", errors)
            checks.append((f"Public {path}", ok))

        # System owner
        if login(page, "system_owner_demo", "SystemOwner@123", errors, "SystemOwner"):
            checks.append(("SystemOwner login", True))
            ok = safe_goto(page, f\"{BASE}/{SYSTEM_PATH}/\", \"System dashboard\", errors)
            checks.append(("System dashboard", ok))
            ok = safe_goto(page, f\"{BASE}/{SYSTEM_PATH}/tenants/new/\", \"System add restaurant\", errors)
            checks.append(("System add restaurant", ok))

        # Restaurant owner basic navigation
        context = browser.new_context(service_workers="block")
        page = context.new_page()
        if login(page, "demo-pro_owner", "DemoUser@123", errors, "RestaurantOwner"):
            checks.append(("Owner login", True))
            for path in ["/dashboard/", "/orders/", "/menu/products/", "/inventory/ingredients/", "/hr/employees/", "/reports/", "/restaurants/branches/"]:
                ok = safe_goto(page, BASE + path, f"Owner {path}", errors)
                checks.append((f"Owner {path}", ok))

        # Cashier flow
        context = browser.new_context(service_workers="block")
        page = context.new_page()
        if login(page, "demo-pro_cashier_main", "DemoUser@123", errors, "Cashier"):
            checks.append(("Cashier login", True))
            test_cashier_flow(page, errors)

        # Kitchen flow
        context = browser.new_context(service_workers="block")
        page = context.new_page()
        if login(page, "demo-pro_kitchen_main", "DemoUser@123", errors, "Kitchen"):
            checks.append(("Kitchen login", True))
            test_kitchen_flow(page, errors)

        # Inventory role
        context = browser.new_context(service_workers="block")
        page = context.new_page()
        if login(page, "demo-pro_inventory_main", "DemoUser@123", errors, "Inventory"):
            checks.append(("Inventory login", True))
            for path in ["/inventory/ingredients/", "/inventory/stock/"]:
                ok = safe_goto(page, BASE + path, f"Inventory {path}", errors)
                checks.append((f"Inventory {path}", ok))

        # Accountant role
        context = browser.new_context(service_workers="block")
        page = context.new_page()
        if login(page, "demo-pro_accountant", "DemoUser@123", errors, "Accountant"):
            checks.append(("Accountant login", True))
            for path in ["/reports/", "/reports/accounting/"]:
                ok = safe_goto(page, BASE + path, f"Accountant {path}", errors)
                checks.append((f"Accountant {path}", ok))

        browser.close()

    lines = ["Playwright UI smoke report", "==========================", ""]
    lines.append("Checks:")
    for name, ok in checks:
        lines.append(f"- {name}: {'PASS' if ok else 'FAIL'}")
    lines.append("")
    if errors:
        lines.append("Errors:")
        for name, err in errors:
            lines.append(f"- {name}: {err}")
    else:
        lines.append("Errors: none")

    write_report(lines)
    print("\n".join(lines))
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    run()

