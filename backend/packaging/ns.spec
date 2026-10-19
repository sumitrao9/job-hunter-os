# -*- mode: python ; coding: utf-8 -*-
import os
import sys

# Resolve paths relative to this spec file.
backend_dir = os.path.dirname(os.path.abspath(SPECPATH))
frontend_dist = os.path.join(os.path.dirname(backend_dir), "frontend", "dist")
upload_dir = os.path.join(backend_dir, "uploads")

# Ensure upload dir exists at runtime.
for d in [upload_dir]:
    os.makedirs(d, exist_ok=True)

datas = [
    (upload_dir, "uploads"),
]
if os.path.isdir(frontend_dist):
    datas.insert(0, (frontend_dist, "frontend/dist"))

# Ship a .env template, never the developer's real .env: baking API keys into
# the bundle would leak them to everyone who installs the app.
env_example = os.path.join(backend_dir, ".env.example")
if os.path.exists(env_example):
    datas.append((env_example, "."))

hiddenimports = [
    "app",
    "app.main",
    "app.router",
    "app.routers",
    "app.models",
    "app.database",
    "app.config",
    "app.application_submission",
    "app.services.llm",
    "app.services.ollama",
    "app.services.knowledge_base",
    "app.services.matching",
    "app.services.resume_parser",
    "app.services.application_prep",
    "app.services.documents",
    "app.services.multi_discovery",
    "app.services.auto_apply_workflow",
]

# Optional imports that may not be present.
optional_imports = []
for mod in ["litellm", "sklearn", "jobspy", "remotive", "usajobs"]:
    try:
        __import__(mod)
        optional_imports.append(mod)
    except ImportError:
        pass

# Include litellm data files (JSON configs needed at import time).
import glob
try:
    import litellm
    litellm_dir = os.path.dirname(litellm.__file__)
    litellm_data = [
        (os.path.join(litellm_dir, "model_prices_and_context_window_backup.json"), "litellm"),
        (os.path.join(litellm_dir, "provider_endpoints_support_backup.json"), "litellm"),
        (os.path.join(litellm_dir, "policy_templates_backup.json"), "litellm"),
    ]
    datas += [(src, dst) for src, dst in litellm_data if os.path.exists(src)]
except ImportError:
    pass

a = Analysis(
    [os.path.join(backend_dir, "app", "main.py")],
    pathex=[backend_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports + optional_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "pytest-asyncio", "tests"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ns",
    debug=True,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="NS",
)
