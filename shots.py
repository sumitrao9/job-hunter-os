#!/usr/bin/env python3
"""Capture screenshots of every page for visual review."""
import asyncio
import base64
import importlib.util
import pathlib

_spec = importlib.util.spec_from_file_location(
    "e2e_helpers", "/Users/macbook/Desktop/SUMIT/job-hunter-os/test-e2e.py"
)
_e2e = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_e2e)
Cdp, goto, page_ws = _e2e.Cdp, _e2e.goto, _e2e.page_ws

OUT = pathlib.Path("/Users/macbook/Desktop/SUMIT/job-hunter-os/shots")
OUT.mkdir(exist_ok=True)

PAGES = [
    ("dashboard", "/"),
    ("jobs", "/jobs"),
    ("applications", "/applications"),
    ("apply", "/apply"),
    ("cover-letter", "/cover-letter"),
    ("follow-ups", "/follow-ups"),
    ("resumes", "/resumes"),
    ("profile", "/profile"),
    ("settings", "/settings"),
]


async def main():
    import websockets

    async with websockets.connect(page_ws(), max_size=80_000_000) as ws:
        cdp = Cdp(ws)
        await cdp.send("Page.enable")
        await cdp.send("Runtime.enable")
        try:
            await cdp.send("Emulation.setDeviceMetricsOverride", {
                "width": 1440, "height": 900, "deviceScaleFactor": 2, "mobile": False,
            })
        except Exception as exc:
            print("metrics override failed:", exc)

        for name, path in PAGES:
            await goto(cdp, path, settle=3.0)
            shot = await cdp.send("Page.captureScreenshot", {"format": "png"})
            path_out = OUT / f"{name}.png"
            path_out.write_bytes(base64.b64decode(shot["data"]))
            print("saved", path_out, f"{path_out.stat().st_size//1024}KB")


asyncio.run(main())