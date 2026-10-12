"""
CI Verification harness for Gold Price Dashboard.
Verifies backend routes, core module integrity, and environment sanity.
Outputs manifest.json and execution evidence into output/ci/
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def run_checks():
    evidence_dir = Path("output/ci")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    
    checks = []
    has_failure = False

    # Check 1: Python environment sanity
    py_version = sys.version
    checks.append({
        "name": "Python Environment",
        "status": "PASS",
        "detail": f"Python version {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    })

    # Check 2: Core modules import
    try:
        import api_fastapi
        import data_analyzer
        import data_collector
        checks.append({
            "name": "Core Modules Import",
            "status": "PASS",
            "detail": "api_fastapi, data_analyzer, data_collector imported successfully"
        })
    except Exception as e:
        has_failure = True
        checks.append({
            "name": "Core Modules Import",
            "status": "FAIL",
            "detail": str(e)
        })

    # Check 3: FastAPI Routes Verification
    try:
        from api_fastapi import app
        routes = [route.path for route in app.routes]
        expected_routes = ["/api/current-prices", "/api/historical-prices"]
        missing = [r for r in expected_routes if r not in routes]
        if missing:
            has_failure = True
            checks.append({
                "name": "FastAPI Routes Registration",
                "status": "FAIL",
                "detail": f"Missing expected routes: {missing}"
            })
        else:
            checks.append({
                "name": "FastAPI Routes Registration",
                "status": "PASS",
                "detail": f"Registered {len(routes)} routes correctly"
            })
    except Exception as e:
        has_failure = True
        checks.append({
            "name": "FastAPI Routes Registration",
            "status": "FAIL",
            "detail": str(e)
        })

    # Check 4: Data files check
    data_dir = Path("historical_data")
    if data_dir.exists():
        csv_files = list(data_dir.glob("*.csv"))
        checks.append({
            "name": "Historical Data Store",
            "status": "PASS",
            "detail": f"Found {len(csv_files)} CSV files in historical_data"
        })
    else:
        checks.append({
            "name": "Historical Data Store",
            "status": "PASS",
            "detail": "Data store folder will be initialized dynamically"
        })

    outcome = "FAIL" if has_failure else "PASS"

    manifest = {
        "outcome": outcome,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "code_revision": os.getenv("GITHUB_SHA", "local"),
        "run_id": os.getenv("GITHUB_RUN_ID", "local"),
        "attempt_id": os.getenv("GITHUB_RUN_ATTEMPT", "1"),
        "total_checks": len(checks),
        "passed": sum(1 for c in checks if c["status"] == "PASS"),
        "failed": sum(1 for c in checks if c["status"] == "FAIL"),
        "checks": checks
    }

    manifest_path = evidence_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    summary_path = evidence_dir / "summary.md"
    summary_md = f"""# CI Verification Summary

- **Status:** `{outcome}`
- **Executed at:** {manifest['timestamp']}
- **Run ID:** `{manifest['run_id']}` (Attempt: `{manifest['attempt_id']}`)

| Check | Status | Details |
| :--- | :--- | :--- |
"""
    for c in checks:
        icon = "✅ PASS" if c["status"] == "PASS" else "❌ FAIL"
        summary_md += f"| {c['name']} | {icon} | {c['detail']} |\n"

    summary_path.write_text(summary_md, encoding="utf-8")
    print(summary_md)

    if has_failure:
        sys.exit(1)

if __name__ == "__main__":
    run_checks()
