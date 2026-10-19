#!/usr/bin/env python3
"""End-to-end frontend verification over CDP.

Drives the real UI with human-like pointer movement and asserts that
navigation, data loading, search filtering, and the apply flow all work.
"""
import asyncio
import json
import sys
import time

import requests
import websockets

BASE = "http://localhost:5173"
API = "http://127.0.0.1:8000"


def page_ws():
    tabs = requests.get("http://127.0.0.1:9222/json/list", timeout=10).json()
    for tab in tabs:
        if tab.get("type") == "page" and tab.get("url", "").startswith(BASE):
            return tab["webSocketDebuggerUrl"]
    raise SystemExit("no app tab found in Chrome")


class Cdp:
    def __init__(self, ws):
        self.ws = ws
        self.msg_id = 0
        self.events = []

    async def send(self, method, params=None, timeout=30):
        self.msg_id += 1
        mid = self.msg_id
        await self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        while True:
            raw = await asyncio.wait_for(self.ws.recv(), timeout=timeout)
            data = json.loads(raw)
            if data.get("id") == mid:
                if "error" in data:
                    raise RuntimeError(f"{method}: {data['error']}")
                return data.get("result", {})
            if "method" in data:
                self.events.append(data)

    async def eval(self, expr, timeout=30):
        res = await self.send(
            "Runtime.evaluate",
            {"expression": expr, "returnByValue": True, "awaitPromise": True},
            timeout=timeout,
        )
        return res.get("result", {}).get("value")


async def wait_for(cdp, expression, timeout=15.0, interval=0.25, label=""):
    """Poll until an expression is truthy, instead of sleeping a fixed amount.

    Fixed sleeps make the suite report failures that are really just slow
    responses, and pass by luck when the machine happens to be fast.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if await cdp.eval(expression):
                return True
        except Exception:
            pass
        await asyncio.sleep(interval)
    if label:
        print(f"      (wait timeout: {label})")
    return False


async def goto(cdp, path, settle=2.2):
    await cdp.send("Page.navigate", {"url": f"{BASE}{path}"})
    await asyncio.sleep(settle)


async def text(cdp):
    return (await cdp.eval("document.body.innerText")) or ""


async def _locate(cdp, js_matcher):
    """Scroll a matched element into view and return a clickable point.

    Scrolling is instant, not smooth: smooth scrolling moves the element after
    the coordinates are read, so the click lands on whatever is now underneath.
    The point is also verified with elementFromPoint so a silent miss cannot be
    mistaken for a successful click.
    """
    info = await cdp.eval(
        f"""(() => {{
          const el = (() => {{ {js_matcher} }})();
          if (!el) return {{found: false}};
          el.scrollIntoView({{block: 'center', inline: 'center', behavior: 'auto'}});
          const r = el.getBoundingClientRect();
          const x = r.x + r.width / 2;
          const y = r.y + r.height / 2;
          const inView = x >= 0 && y >= 0 &&
                          x <= window.innerWidth && y <= window.innerHeight;
          const hit = inView && document.elementFromPoint(x, y);
          return {{
            found: true,
            x, y, inView,
            label: (el.innerText || el.getAttribute('aria-label') || '').trim().slice(0, 60),
            hitTarget: hit ? (hit === el || el.contains(hit) || hit.contains(el)) : false,
            covered: hit ? (hit.tagName + '.' + (hit.className || '').toString().slice(0, 40)) : null
          }};
        }})()"""
    )
    return info


async def _dispatch_click(cdp, x, y, curved=True):
    """Move the pointer along a curved path, then press and release."""
    if curved:
        sx, sy = x - 60, y + 45
        steps = 15
        for i in range(1, steps + 1):
            t = i / steps
            ease = t * t * (3 - 2 * t)
            await cdp.send(
                "Input.dispatchMouseEvent",
                {"type": "mouseMoved", "x": sx + (x - sx) * ease,
                 "y": sy + (y - sy) * ease, "buttons": 0},
            )
            await asyncio.sleep(0.015 + (i % 3) * 0.01)
    await asyncio.sleep(0.12)
    await cdp.send("Input.dispatchMouseEvent",
                   {"type": "mouseMoved", "x": x, "y": y, "buttons": 0})
    await asyncio.sleep(0.1)
    await cdp.send("Input.dispatchMouseEvent",
                   {"type": "mousePressed", "x": x, "y": y, "button": "left",
                    "clickCount": 1, "buttons": 1})
    await asyncio.sleep(0.07)
    await cdp.send("Input.dispatchMouseEvent",
                   {"type": "mouseReleased", "x": x, "y": y, "button": "left",
                    "clickCount": 1, "buttons": 0})


CLICK_COUNTER = "window.__jhClicks"


async def _click_count(cdp):
    """Install (once) and read a capture-phase click counter.

    Synthetic input events can be dropped entirely when the browser window is
    not frontmost, which looks identical to a broken button. Counting the
    events the page actually received lets the harness tell those apart.
    """
    await cdp.eval(
        f"""(() => {{
          if (!{CLICK_COUNTER}) {{
            {CLICK_COUNTER} = 0;
            document.addEventListener('click', () => {{ {CLICK_COUNTER}++; }}, true);
          }}
        }})()"""
    )
    return await cdp.eval(f"{CLICK_COUNTER} || 0")


async def _click(cdp, js_matcher, curved=True, attempts=3):
    """Click a control, preferring real pointer input and verifying it landed.

    Falls back to a DOM click when the page never received the synthetic events.
    """
    last = None
    for attempt in range(attempts):
        last = await _locate(cdp, js_matcher)
        if not last.get("found"):
            return False, last

        if not (last.get("inView") and last.get("hitTarget")):
            await asyncio.sleep(0.3)
            continue

        before = await _click_count(cdp)
        await _dispatch_click(cdp, last["x"], last["y"], curved=curved)
        await asyncio.sleep(0.25)
        after = await _click_count(cdp)

        if after > before:
            return True, last

        # The pointer events never reached the page; use a DOM click instead.
        fired = await cdp.eval(
            f"""(() => {{
              const el = (() => {{ {js_matcher} }})();
              if (!el) return false;
              el.click();
              return true;
            }})()"""
        )
        await asyncio.sleep(0.25)
        final = await _click_count(cdp)
        if fired and final > after:
            last["viaDomClick"] = True
            return True, last

    return False, last


async def click_text(cdp, label, selector="button"):
    """Click a control matched on its visible text, with human-like pointer motion."""
    matcher = (
        f"const el = Array.from(document.querySelectorAll({json.dumps(selector)}))\n"
        f"  .find(e => (e.innerText || '').toLowerCase().includes({json.dumps(label.lower())}));\n"
        f"return el;"
    )
    ok, info = await _click(cdp, matcher, curved=True)
    return ok


async def click_aria(cdp, aria_prefix):
    """Click a control matched on aria-label rather than visible text."""
    matcher = (
        f"const el = Array.from(document.querySelectorAll('button'))\n"
        f"  .find(b => (b.getAttribute('aria-label') || '').toLowerCase()"
        f".startsWith({json.dumps(aria_prefix.lower())}));\n"
        f"return el;"
    )
    ok, info = await _click(cdp, matcher, curved=False)
    return ok


async def set_input(cdp, selector, value):
    """Set a React controlled input's value and fire the event React listens for.

    React overrides the DOM value setter, so assigning el.value directly is
    ignored. The native setter plus a bubbling input event is what actually
    triggers onChange. Synthetic key events without key codes are unreliable
    here, so they are not used.
    """
    return await cdp.eval(
        f"""(() => {{
          const el = document.querySelector({json.dumps(selector)});
          if (!el) return 'no-element';
          el.scrollIntoView({{block: 'center', behavior: 'auto'}});
          el.focus();
          const proto = el instanceof HTMLTextAreaElement
            ? HTMLTextAreaElement.prototype
            : window.HTMLInputElement.prototype;
          Object.getOwnPropertyDescriptor(proto, 'value').set.call(
            el, {json.dumps(value)}
          );
          el.dispatchEvent(new Event('input', {{ bubbles: true }}));
          return el.value === {json.dumps(value)} ? 'ok' : 'value-mismatch:' + el.value;
        }})()"""
    )


async def main():
    results = []

    def check(name, ok, detail=""):
        results.append((name, ok, detail))
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))

    async with websockets.connect(page_ws(), max_size=64 * 1024 * 1024) as ws:
        cdp = Cdp(ws)
        await cdp.send("Page.enable")
        await cdp.send("Runtime.enable")
        # Without this, no Network.responseReceived events are emitted and the
        # failed-API check would silently pass having observed nothing.
        await cdp.send("Network.enable")
        # Frontmost tabs receive synthetic input; background tabs silently drop it.
        try:
            await cdp.send("Page.bringToFront")
        except Exception:
            pass
        await cdp.send("Network.enable")

        print("=" * 66)
        print("FRONTEND E2E VERIFICATION")
        print("=" * 66)

        # 1. Every route renders with content.
        routes = ["/", "/jobs", "/applications", "/follow-ups", "/cover-letter", "/apply", "/resumes", "/settings", "/profile"]
        for path in routes:
            await goto(cdp, path)
            body = await text(cdp)
            path_ok = await cdp.eval("location.pathname")
            ok = path_ok == path and len(body.strip()) > 40 and "NS" in body
            check(f"route {path}", ok, f"len={len(body.strip())}")

        # 2. Job Discovery loads real sources from the API.
        await goto(cdp, "/jobs")
        source_count = await cdp.eval(
            "document.querySelectorAll('[aria-pressed]').length"
        )
        check("discovery sources loaded from API", (source_count or 0) >= 5, f"{source_count} toggleable sources")

        # 3. Job cards rendered from the database.
        cards = await cdp.eval("document.querySelectorAll('h3').length")
        check("job cards rendered", (cards or 0) > 3, f"{cards} cards")

        # 4. Search queries the server, so it finds jobs outside the first page.
        before = await cdp.eval("document.querySelectorAll('h3').length")
        companies_before = await cdp.eval(
            """JSON.stringify(Array.from(document.querySelectorAll('h3 + p'))
                 .map(e => e.textContent.trim()))"""
        )
        await set_input(cdp, 'input[aria-label="Search jobs"]', "Stripe")
        # Wait for the filtered result set rather than guessing a delay.
        await wait_for(
            cdp,
            """(() => {
                 const ps = Array.from(document.querySelectorAll('h3 + p'));
                 return ps.length > 0 && ps.every(e => /stripe/i.test(e.textContent));
               })()""",
            timeout=15,
            label="results filtered to Stripe",
        )
        after = await cdp.eval("document.querySelectorAll('h3').length")
        companies_after = await cdp.eval(
            """JSON.stringify(Array.from(document.querySelectorAll('h3 + p'))
                 .map(e => e.textContent.trim()))"""
        )
        body = await text(cdp)
        has_stripe = "Stripe" in body
        # Every visible card must now belong to the searched company. Asserting
        # only that "Stripe" appears somewhere would also pass unfiltered.
        only_stripe = bool(companies_after) and all(
            "stripe" in c.lower() for c in json.loads(companies_after)
        )
        changed = json.loads(companies_before) != json.loads(companies_after)
        check("server-side search filters to Stripe",
              has_stripe and only_stripe and changed and (after or 0) > 0,
              f"{before} -> {after} cards, all Stripe={only_stripe}, "
              f"list changed={changed}")

        # 5. Empty search result shows the clear-filters empty state.
        await set_input(cdp, 'input[aria-label="Search jobs"]', "zzzznotarealcompany")
        settled = await wait_for(
            cdp,
            "document.body.innerText.includes('No jobs match your filters')",
            timeout=15,
            label="empty state for nonsense search",
        )
        body = await text(cdp)
        check("no-match empty state", settled and "No jobs match your filters" in body)
        await set_input(cdp, 'input[aria-label="Search jobs"]', "")
        await wait_for(cdp, "document.querySelectorAll('h3').length > 0",
                       timeout=15, label="job cards to return")

        # 6. Theme toggle flips the root class (light mode was broken before).
        theme_before = await cdp.eval("document.documentElement.className")
        want_light = "light" not in theme_before
        toggled = await click_aria(cdp, "switch to")
        await wait_for(
            cdp,
            f"document.documentElement.className.contains('{'light' if want_light else 'dark'}')",
            timeout=8,
            label="theme class to flip",
        )
        theme_after = await cdp.eval("document.documentElement.className")
        flipped = ("light" in theme_after) != ("light" in theme_before)
        check("theme toggle flips theme", toggled and flipped, f"{theme_before!r} -> {theme_after!r}")
        await click_aria(cdp, "switch to")
        await asyncio.sleep(0.5)

        # 7. Dashboard shows the real activity chart, not fabricated data.
        await goto(cdp, "/")
        body = await text(cdp)
        has_trend = "Activity (last 14 days)" in body
        no_fake = "Weekly trend" not in body
        check("dashboard uses real activity chart", has_trend and no_fake)

        # 8. Dashboard date filters are labelled.
        labelled = await cdp.eval(
            "Array.from(document.querySelectorAll('label')).filter(l => l.innerText.trim() === 'From' || l.innerText.trim() === 'To').length"
        )
        check("dashboard date filters labelled", (labelled or 0) >= 2, f"{labelled} labels")

        # 9. Apply flow: pick a job, prepare, confirm a cover letter renders.
        await goto(cdp, "/apply")
        option_count = await cdp.eval("document.querySelectorAll('select option').length")
        check("apply targets populated", (option_count or 0) > 1, f"{option_count} options")

        picked = await cdp.eval(
            """(() => {
              const sel = document.querySelectorAll('select')[0];
              const opt = Array.from(sel.options).find(o => o.value);
              if (!opt) return null;
              const setter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value').set;
              setter.call(sel, opt.value);
              sel.dispatchEvent(new Event('change', { bubbles: true }));
              return opt.text;
            })()"""
        )
        await asyncio.sleep(0.6)
        clicked = await click_text(cdp, "Prepare application")
        ready = await wait_for(
            cdp,
            """(() => {
                 const t = document.body.innerText;
                 return t.includes('Cover letter') && t.includes('Form answers');
               })()""",
            timeout=20,
            label="application package to render",
        )
        body = await text(cdp)
        ok = "Cover letter" in body and "Form answers" in body and "Submit" in body
        check("apply prepares package", clicked and ok,
              f"target={picked}" if picked else "no target")

        # 10. Human-in-the-loop guarantee is surfaced on the submit card.
        check("apply states human submits", "never submits on your behalf" in body)

        # 10b. With a tracked application selected, the user can record that they
        # submitted it, so the pipeline reflects reality instead of guessing.
        # The Job and Application selects are mutually exclusive, so pick the
        # application list explicitly.
        await cdp.eval(
            """(() => {
              const sel = document.querySelectorAll('select')[1];
              if (!sel) return 'no-select';
              const opt = Array.from(sel.options).find(o => o.value);
              if (!opt) return 'no-options';
              const setter = Object.getOwnPropertyDescriptor(
                window.HTMLSelectElement.prototype, 'value').set;
              setter.call(sel, opt.value);
              sel.dispatchEvent(new Event('change', { bubbles: true }));
              return 'ok';
            })()"""
        )
        await wait_for(
            cdp,
            """(() => {
                 const b = Array.from(document.querySelectorAll('button'))
                   .find(x => x.textContent.trim() === 'Prepare application');
                 return b && !b.disabled;
               })()""",
            timeout=10,
            label="application target to become selectable",
        )
        await click_text(cdp, "Prepare application")
        await wait_for(
            cdp,
            "document.body.innerText.includes('Cover letter')",
            timeout=20,
            label="package for application target",
        )
        offered = "Mark as submitted" in await text(cdp)
        ok, detail = False, "no button shown for application target"
        if offered:
            marked = await click_text(cdp, "Mark as submitted")
            await wait_for(
                cdp,
                "document.body.innerText.includes('Marked as submitted')",
                timeout=15,
                label="submitted confirmation",
            )
            after = await text(cdp)
            ok = marked and "Marked as submitted" in after
            detail = "confirmed" if ok else "no confirmation after click"
        check("apply records user-submitted", ok, detail)

        # 11. Resume upload rejects oversize client-side.
        await goto(cdp, "/resumes")
        body = await text(cdp)
        check("resumes page has limits copy", "Max 10MB" in body)

        # 12. Settings masks the API key and probes n8n server-side.
        await goto(cdp, "/settings")
        key_type = await cdp.eval(
            """(() => {
              const el = document.querySelector('input[type=password]');
              return el ? el.type : null;
            })()"""
        )
        check("api key field is masked", key_type == "password", f"type={key_type}")

        n8n = await click_text(cdp, "Test")
        # The probe hits the backend, which may have to wait out a connection
        # timeout before reporting the real result.
        await wait_for(
            cdp,
            """(() => {
                 const t = document.body.innerText;
                 return t.includes('Not reachable') || t.includes('Reachable');
               })()""",
            timeout=25,
            label="n8n probe result",
        )
        body = await text(cdp)
        check("n8n probe reports real result",
              n8n and ("Not reachable" in body or "Reachable" in body))

        # 13. No uncaught exceptions anywhere in the run.
        exceptions = [
            e for e in cdp.events if e.get("method") == "Runtime.exceptionThrown"
        ]
        check("no uncaught JS exceptions", len(exceptions) == 0, f"{len(exceptions)} exceptions")

        # 14. No failed API calls.
        api = [
            e["params"]["response"]
            for e in cdp.events
            if e.get("method") == "Network.responseReceived"
            # In dev the browser calls the Vite origin, which proxies /api to
            # the backend, so match the path rather than the backend host.
            and "/api/" in e["params"]["response"]["url"]
        ]
        failed = [r for r in api if r["status"] >= 400]
        # Require real traffic: an empty set means the check proved nothing.
        check("api traffic observed and healthy", len(api) > 0 and len(failed) == 0,
              f"{len(api)} calls, {len(failed)} failed"
              + (f" -> {[(r['status'], r['url'].split('/api/')[-1]) for r in failed[:5]]}"
                 if failed else ""))

    print("=" * 66)
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"RESULT: {passed}/{total} checks passed")
    if passed != total:
        print("\nFailures:")
        for name, ok, detail in results:
            if not ok:
                print(f"  - {name}: {detail}")
    print("=" * 66)
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    asyncio.run(main())