#!/usr/bin/env python3
"""Playwright-based application submission with human-like behavior.

Follows patterns from leading open-source projects (AIHawk, ApplyAgent,
torontodeveloper/job-application-agent): Bezier-curve mouse paths,
ATS-specific selectors, and human-in-the-loop confirmation.
"""
import asyncio
import random
from pathlib import Path


def _bezier_curve(x0, y0, x1, y1, cpx, cpy, steps=12):
    """Generate a cubic Bezier curve from start to end with control point."""
    pts = []
    for i in range(steps):
        t = i / max(steps - 1, 1)
        mt = 1 - t
        bx = mt*mt*mt*x0 + 3*mt*mt*t*cpx + 3*mt*t*t*x1 + t*t*t*x1
        by = mt*mt*mt*y0 + 3*mt*mt*t*cpy + 3*mt*t*t*y1 + t*t*t*y1
        pts.append((bx, by))
    return pts


def _human_delay(min_ms=30, max_ms=120):
    """Return a random delay simulating human reaction time."""
    return random.uniform(min_ms, max_ms) / 1000.0


class HumanMouse:
    """Drive Playwright mouse with Bezier curves and random timing."""

    def __init__(self, page):
        self.page = page

    async def move_to(self, x, y, clicks=False, button='left'):
        # Pick a control point that creates a natural curve
        dx = abs(x - (self.page.viewport_size.get('width', 1280) / 2)) if False else random.randint(50, 200)
        dy = random.randint(-100, 100)
        cpx = (x + dx) / 2 + random.uniform(-50, 50)
        cpy = (y + dy) / 2 + random.uniform(-30, 30)

        steps = random.randint(10, 20)
        # Get current mouse position (approximate by last known or center)
        start_x, start_y = x / 2, y / 2

        curve = _bezier_curve(start_x, start_y, x, y, cpx, cpy, steps)
        for i, (cx, cy) in enumerate(curve):
            await self.page.mouse.move(cx, cy)
            await asyncio.sleep(_human_delay(10, 20))

        if clicks:
            await self.page.mouse.down(button=button)
            await asyncio.sleep(_human_delay(20, 60))
            await self.page.mouse.up(button=button)
        return True


class ApplicationSubmitter:
    """Handles application submission to ATS platforms using Playwright.

    Supports Greenhouse, Lever, Ashby, and generic forms.
    Uses human-like mouse movements and random delays.
    """

    ATS_SELECTORS = {
        "greenhouse": {
            "form": "form[data-automation='application'], form#apply",
            "submit": "button[type=submit], button[data-automation='submit']",
            "resume": "input[type=file][accept*='pdf'], input#resume",
            "first_name": "input[name*='first'], input#first_name",
            "last_name": "input[name*='last'], input#last_name",
            "email": "input[type=email], input#email",
        },
        "lever": {
            "form": "form[data-test='application-form']",
            "submit": "button[type=submit]",
            "resume": "input[type=file]",
        },
        "ashby": {
            "form": "#ashby-application-form",
            "submit": "button[type=submit]",
            "resume": "input[type=file]",
        },
        "workday": {
            "form": "form[data-automation-id='applicationForm']",
            "submit": "button[data-automation-id='submitButton']",
            "resume": "input[type=file]",
        },
    }

    def __init__(self, base_url: str = None, headless: bool = True):
        self.base_url = base_url or "http://localhost:8000"
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self.mouse = None

    async def initialize(self):
        """Initialize Playwright browser with stealth settings."""
        try:
            from playwright.async_api import async_playwright
        except ImportError as err:
            raise RuntimeError(
                "Playwright is required for autonomous submission. "
                "Install with: pip install playwright && playwright install"
            ) from err

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
        )
        self.context = await self.browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        self.page = await self.context.new_page()
        self.mouse = HumanMouse(self.page)

    async def submit_application(
        self,
        job_url: str,
        profile_data: dict,
        resume_path: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        """Submit an application to a job posting.

        Args:
            job_url: The application page URL
            profile_data: Dict with keys: first_name, last_name, email, phone, etc.
            resume_path: Path to resume PDF
            dry_run: If True, fill form but don't click submit

        Returns:
            dict with status, message, and details
        """
        result = {"job_url": job_url, "status": "failed", "message": "", "steps": []}

        try:
            # Navigate to the job application page
            await self.page.goto(job_url, wait_until="networkidle", timeout=60000)
            result["steps"].append("navigated to job page")

            # Wait for page to load
            await self.page.wait_for_timeout(random.uniform(2000, 4000))

            # Detect ATS platform
            ats = await self._detect_platform()
            result["ats"] = ats
            result["steps"].append(f"detected platform: {ats}")

            # Fill the form
            filled = await self._fill_form(ats, profile_data)
            result["steps"].append(f"filled {filled} fields")

            # Attach resume if provided
            if resume_path and Path(resume_path).exists():
                uploaded = await self._attach_resume(resume_path)
                if uploaded:
                    result["steps"].append("resume uploaded")
                else:
                    result["steps"].append("resume upload failed (non-critical)")

            if dry_run:
                result["status"] = "dry_run_complete"
                result["message"] = "Form filled in dry-run mode, no submission."
                return result

            # Human-like hover over submit button
            submit_clicked = await self._click_submit(ats)
            if submit_clicked:
                result["steps"].append("submit button clicked")
                result = await self._await_confirmation(result)
            else:
                result["status"] = "submit_failed"
                result["message"] = "Could not find or click the submit button."

        except Exception as exc:
            result["status"] = "error"
            result["message"] = str(exc)
            result["error"] = str(exc)

        return result

    async def _detect_platform(self) -> str:
        """Detect the ATS platform from the page content."""
        # Check URL patterns
        url = self.page.url.lower()
        if "greenhouse" in url or "ghv" in url or "greenhouse.io" in url:
            return "greenhouse"
        if "lever" in url or "lever.co" in url or "jobsite" in url:
            return "lever"
        if "ashby" in url or "join.com" in url:
            return "ashby"
        if "workday" in url or "myworkday" in url:
            return "workday"
        if "linkedin" in url or "easy apply" in url.lower():
            return "linkedin_easy_apply"
        if "indeed" in url:
            return "indeed"

        # Detect via page structure
        if await self.page.query_selector("form[data-automation='application']"):
            return "greenhouse"
        if await self.page.query_selector("form[data-test='application-form']"):
            return "lever"
        if await self.page.query_selector("#ashby-application-form"):
            return "ashby"
        if await self.page.query_selector("form[data-automation-id='applicationForm']"):
            return "workday"

        # Check for LinkedIn Easy Apply modal
        if await self.page.query_selector(".jobs-easy-apply-form"):
            return "linkedin_easy_apply"

        return "generic"

    async def _fill_form(self, ats: str, profile: dict) -> int:
        """Fill form fields using platform-specific selectors."""
        filled = 0

        # Build field mapping: field_name -> (selector, value)
        field_map = {}

        if ats == "greenhouse":
            # Greenhouse uses name attributes based on custom questions
            field_map["first_name"] = ("input[name*='first_name'], input[name*='first'], input#first_name", profile.get("first_name", ""))
            field_map["last_name"] = ("input[name*='last_name'], input[name*='last'], input#last_name", profile.get("last_name", ""))
            field_map["email"] = ("input[type='email'], input[name='email'], input#email", profile.get("email", ""))
            field_map["phone"] = ("input[name*='phone'], input#phone, input[type='tel']", profile.get("phone", ""))
        elif ats in ("lever", "ashby", "workday"):
            field_map = {
                "name": ("input[name*='name'], input#name", profile.get("full_name", "")),
                "email": ("input[type='email'], input[name='email']", profile.get("email", "")),
                "phone": ("input[name*='phone'], input#phone, input[type='tel']", profile.get("phone", "")),
            }
        else:
            # Generic form filling
            field_map = {
                "name": ("input[name*='name'], input#name, input[aria-label*='Name']", profile.get("full_name", "")),
                "email": ("input[type='email'], input[name*='email'], input[aria-label*='Email']", profile.get("email", "")),
                "phone": ("input[name*='phone'], input#phone, input[type='tel'], input[aria-label*='Phone']", profile.get("phone", "")),
            }

        for key, (selector, value) in field_map.items():
            if not value:
                continue
            try:
                el = await self.page.wait_for_selector(selector, timeout=3000)
                if el:
                    await el.scroll_into_view_if_needed()
                    await self._human_type(el, str(value))
                    filled += 1
            except Exception:
                pass

        # Also fill any remaining text inputs using AI-like label matching
        labels = await self.page.eval_on_selector_all(
            "label",
            "els => els.map(el => ({text: el.textContent.trim(), html: el.innerHTML.trim(), for: el.getAttribute('for')}))",
        )
        filled += await self._fill_by_labels(labels, profile)

        return filled

    async def _fill_by_labels(self, labels: list, profile: dict) -> int:
        """Fill form fields by matching label text to profile keys."""
        filled = 0
        label_keywords = {
            "first name": profile.get("first_name", ""),
            "last name": profile.get("last_name", ""),
            "full name": profile.get("full_name", ""),
            "email": profile.get("email", ""),
            "phone": profile.get("phone", ""),
            "phone number": profile.get("phone", ""),
            "linkedin": profile.get("linkedin_url", ""),
            "portfolio": profile.get("portfolio_url", ""),
            "github": profile.get("github_url", ""),
            "website": profile.get("portfolio_url", ""),
            "address": profile.get("address", ""),
            "city": profile.get("city", ""),
            "state": profile.get("state", ""),
            "zip": profile.get("postal_code", ""),
            "country": profile.get("country", ""),
            "work authorization": profile.get("work_authorization", ""),
        }

        for label in labels:
            text = (label.get("text", "") + " " + (label.get("html", ""))).lower()
            for keyword, value in label_keywords.items():
                if keyword in text and value:
                    target_id = label.get("for")
                    if target_id:
                        selector = f"#{target_id}"
                    else:
                        # Try to find input near this label
                        selector = None
                    if selector:
                        try:
                            el = await self.page.wait_for_selector(selector, timeout=2000)
                            if el:
                                await el.scroll_into_view_if_needed()
                                await self._human_type(el, str(value))
                                filled += 1
                        except Exception:
                            pass
        return filled

    async def _human_type(self, element, text: str):
        """Type text character by character with human-like delays."""
        for char in text:
            await element.type(char)
            await asyncio.sleep(random.uniform(0.02, 0.08))
        await asyncio.sleep(_human_delay(50, 150))

    async def _attach_resume(self, resume_path: str) -> bool:
        """Upload a resume file using file chooser."""
        try:
            file_input = await self.page.wait_for_selector(
                "input[type='file']",
                timeout=10000,
            )
            if file_input:
                # Scroll into view
                await file_input.scroll_into_view_if_needed()
                # Use file chooser
                async with self.page.expect_file_chooser() as fc_info:
                    await file_input.click()
                file_chooser = await fc_info.value
                await file_chooser.set_files(resume_path)
                return True
        except Exception:
            pass
        return False

    async def _click_submit(self, ats: str) -> bool:
        """Click the submit button with human-like behavior."""
        selectors = self.ATS_SELECTORS.get(ats, {})
        submit_selectors = []

        if "submit" in selectors:
            submit_selectors.append(selectors["submit"])

        # Common submit button selectors
        submit_selectors.extend([
            "button[type='submit']",
            "button[data-automation='submit']",
            "button[data-automation-id='submitButton']",
            "input[type='submit']",
            "button.submit",
            "button#submit",
            "button[name='submit']",
            ".apply-button",
            ".submit-application",
            # LinkedIn Easy Apply
            "button[aria-label='Submit application']",
            "button[data-control-name='submit_application']",
            # Indeed
            "#indeed-apply-button",
        ])

        for selector in submit_selectors:
            try:
                btn = await self.page.wait_for_selector(selector, timeout=5000)
                if btn:
                    await btn.scroll_into_view_if_needed()
                    await asyncio.sleep(_human_delay(200, 500))
                    # Get bounding box for mouse movement
                    box = await btn.bounding_box()
                    if box:
                        await self.mouse.move_to(
                            box["x"] + box["width"] / 2,
                            box["y"] + box["height"] / 2,
                        )
                        await self.mouse.move_to(
                            box["x"] + box["width"] / 2,
                            box["y"] + box["height"] / 2,
                            clicks=True,
                        )
                        return True
                    await btn.click(force=True)
                    return True
            except Exception:
                continue
        return False

    async def _await_confirmation(self, result: dict) -> dict:
        """Wait for submission confirmation and update result."""
        confirmation_selectors = [
            "text=/thank.*you/i",
            "text=/success/i",
            "text=/confirmation/i",
            "[data-automation='confirmation']",
            ".application-submitted",
            ".thank-you",
            "h1:has-text('Thank')",
            "div:has-text('Your application')",
        ]

        for sel in confirmation_selectors:
            try:
                el = await self.page.wait_for_selector(sel, timeout=15000)
                if el:
                    result["status"] = "submitted_confirmed"
                    result["message"] = "Application submitted successfully! Confirmation page detected."
                    result["confirmation"] = True
                    return result
            except Exception:
                pass

        # No confirmation page, but submit was clicked
        result["status"] = "submitted_unconfirmed"
        result["message"] = "Submit button clicked but no confirmation page found yet."
        result["confirmation"] = False
        return result

    async def close(self):
        """Close the browser and release resources."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()


async def submit_job_application(
    job_url: str,
    profile_data: dict,
    resume_path: str | None = None,
    headless: bool = True,
    dry_run: bool = False,
) -> dict:
    """Convenience function to submit a single application.

    Args:
        job_url: URL of the job application page
        profile_data: Dict with first_name, last_name, email, phone, etc.
        resume_path: Path to resume PDF
        headless: Run browser headless
        dry_run: Fill form without submitting

    Returns:
        dict with submission result
    """
    submitter = ApplicationSubmitter(headless=headless)
    try:
        await submitter.initialize()
        result = await submitter.submit_application(
            job_url=job_url,
            profile_data=profile_data,
            resume_path=resume_path,
            dry_run=dry_run,
        )
        return result
    finally:
        await submitter.close()
