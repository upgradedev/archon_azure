#!/usr/bin/env python3
"""
End-to-end live test against the deployed Archon Azure infrastructure.

Usage:
    python scripts/e2e-live.py

Env vars:
    BACKEND_URL                      defaults to live ACA URL
    AZURE_STORAGE_CONNECTION_STRING  if set, seeds demo data before testing
    AZURE_STORAGE_CONTAINER          container name (default: archon)
    PERIOD                           period to test (default: 2026-01)

Deps: stdlib only (azure-storage-blob optional — for seeding only).
Exits 0 on all PASS, 1 on any FAIL.
"""
import json
import os
import sys
import urllib.error
import urllib.request

BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "https://archon-backend.politemeadow-da83e97d.westeurope.azurecontainerapps.io",
).rstrip("/")
PERIOD = os.getenv("PERIOD", "2026-01")

GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

_results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> bool:
    tag    = f"{GREEN}[PASS]{RESET}" if condition else f"{RED}[FAIL]{RESET}"
    suffix = f"  — {detail}" if detail else ""
    print(f"  {tag} {name}{suffix}")
    _results.append((name, condition, detail))
    return condition


def http_get(path: str, timeout: int = 30) -> dict:
    req = urllib.request.Request(f"{BACKEND_URL}{path}")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def http_post(path: str, body: dict, timeout: int = 200) -> dict:
    data = json.dumps(body).encode()
    req  = urllib.request.Request(
        f"{BACKEND_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


# ─────────────────────────────────────────────────────────────────────────────
# Demo data seeding (optional — requires azure-storage-blob)
# ─────────────────────────────────────────────────────────────────────────────

def _seed_demo_data() -> None:
    conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "").strip()
    if not conn_str:
        print(f"  {YELLOW}[SKIP]{RESET} AZURE_STORAGE_CONNECTION_STRING not set — assuming data already in place")
        return

    try:
        from azure.storage.blob import BlobServiceClient
    except ImportError:
        print(f"  {YELLOW}[SKIP]{RESET} azure-storage-blob not installed — run: pip install azure-storage-blob")
        return

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "upload_demo_docs",
        os.path.join(os.path.dirname(__file__), "upload_demo_docs.py"),
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    try:
        container = os.getenv("AZURE_STORAGE_CONTAINER", "archon")
        client    = BlobServiceClient.from_connection_string(conn_str)
        try:
            client.create_container(container)
        except Exception:
            pass

        payload   = {"documents": mod.documents, "upload_id": "demo-upload-001", "period": PERIOD}
        body      = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        blob_name = f"extracted/{PERIOD}/demo-upload-001/documents.json"
        client.get_blob_client(container=container, blob=blob_name).upload_blob(body, overwrite=True)
        print(f"  {GREEN}[OK]{RESET}   Seeded {blob_name}  ({len(mod.documents)} docs, {len(body)} bytes)")
    except Exception as exc:
        print(f"  {RED}[ERR]{RESET}  Seed failed: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# Main test runner
# ─────────────────────────────────────────────────────────────────────────────

def run_e2e() -> bool:
    print(f"\n{BOLD}Archon Azure — E2E Live Test{RESET}")
    print(f"  Backend : {BACKEND_URL}")
    print(f"  Period  : {PERIOD}\n")

    # ── 0. Seed ───────────────────────────────────────────────────────────────
    print(f"{BOLD}0. Demo data seeding{RESET}")
    _seed_demo_data()
    print()

    # ── 1. Health ─────────────────────────────────────────────────────────────
    print(f"{BOLD}1. Health checks{RESET}")
    try:
        h = http_get("/health")
        check("Backend /health → 200", h.get("status") == "ok", f"status={h.get('status')!r}")
    except Exception as exc:
        check("Backend /health → 200", False, str(exc))
        print(f"\n{RED}Backend unreachable — stopping.{RESET}\n")
        return False
    print()

    # ── 2. Analysis trigger ───────────────────────────────────────────────────
    print(f"{BOLD}2. Analysis pipeline  (POST /api/analyze — up to 3 min){RESET}")
    print("  Sending request ...")
    try:
        report = http_post("/api/analyze", {"period": PERIOD}, timeout=200)
        check("POST /api/analyze → 200", True)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:200]
        check("POST /api/analyze → 200", False, f"HTTP {exc.code}: {detail}")
        return False
    except Exception as exc:
        check("POST /api/analyze → 200", False, str(exc))
        return False
    print()

    # ── 3. Report structure ───────────────────────────────────────────────────
    print(f"{BOLD}3. Report structure{RESET}")
    check("period matches",               report.get("period") == PERIOD,                  f"got {report.get('period')!r}")
    check("pnl block present",            bool(report.get("pnl")),                         "")
    check("cashFlow block present",       bool(report.get("cashFlow")),                    "")
    check("payrollEvents present",        isinstance(report.get("payrollEvents"), list),   "")
    check("validationResults present",    isinstance(report.get("validationResults"), list), "")
    check("executiveSummary non-empty",   bool((report.get("executiveSummary") or "").strip()), "")
    print()

    # ── 4. P&L sanity ─────────────────────────────────────────────────────────
    print(f"{BOLD}4. P&L sanity{RESET}")
    pnl      = report.get("pnl") or {}
    revenue  = float(pnl.get("revenue")  or 0)
    expenses = float(pnl.get("expenses") or 0)
    net      = float(pnl.get("netProfit") or 0)
    check("Revenue > 0",             revenue > 0,                          f"€{revenue:,.2f}")
    check("Expenses > 0",            expenses > 0,                         f"€{expenses:,.2f}")
    check("NetProfit = Rev − Exp",   abs(net - (revenue - expenses)) < 1.0, f"net={net:,.2f} vs rev−exp={revenue - expenses:,.2f}")
    print()

    # ── 5. 28 % payroll gap invariant ────────────────────────────────────────
    print(f"{BOLD}5. 28% payroll gap invariant  (employer cost > bank net){RESET}")
    events = report.get("payrollEvents") or []
    if not events:
        check("Payroll event exists", False, "payrollEvents list is empty")
    else:
        ev             = events[0]
        employer_cost  = float(ev.get("employer_cost_total") or 0)
        net_total      = float(ev.get("net_total")           or 0)
        bank_confirmed = ev.get("bank_confirmed", False)

        check("bank_confirmed = True",
              bank_confirmed, "")
        check("employer_cost_total ≈ 6930.00  (payroll register)",
              abs(employer_cost - 6930.00) < 5.0, f"got {employer_cost:,.2f}")
        check("net_total ≈ 3994.74  (real cash from bank confirmation)",
              abs(net_total - 3994.74) < 5.0, f"got {net_total:,.2f}")
        if net_total > 0:
            ratio = employer_cost / net_total
            check("employer_cost / bank_net > 1.25  (gap confirmed)",
                  ratio > 1.25, f"ratio={ratio:.3f}  (demo expects ≈1.73)")
        else:
            check("employer_cost / bank_net > 1.25", False, "net_total is 0")
    print()

    # ── 6. Cash flow — bank drives operating, not payroll register ───────────
    print(f"{BOLD}6. Cash flow correctness{RESET}")
    cf        = report.get("cashFlow") or {}
    operating = float(cf.get("operating") or 0)
    check("cashFlow.operating != 0",
          operating != 0, f"€{operating:,.2f}")
    check("Operating outflow ≠ employer_cost  (register not used for cash)",
          abs(operating - (-6930.00)) > 1.0, f"operating={operating:,.2f}")
    print()

    # ── 7. Validation rules ───────────────────────────────────────────────────
    print(f"{BOLD}7. Cross-document validation rules{RESET}")
    val_results = report.get("validationResults") or []
    rules_seen  = {r.get("rule") for r in val_results}
    check("R1 present  (bank ≈ payslips ±2%)",       "R1" in rules_seen, f"rules seen: {sorted(rules_seen)}")
    check("R2 present  (employer cost ratio 1.25–1.45)", "R2" in rules_seen, "")
    check("At least one rule passed",
          any(r.get("passed") for r in val_results), "")
    print()

    # ── 8. Foundry IQ citations ───────────────────────────────────────────────
    print(f"{BOLD}8. Foundry IQ  — grounded citations{RESET}")
    summary     = report.get("executiveSummary") or ""
    has_sources = "Sources:" in summary
    if os.environ.get("AZURE_AI_PROJECT_CONNECTION_STRING"):
        check("executiveSummary contains 'Sources:'  (Foundry IQ active)", has_sources,
              summary[:100] + "..." if summary else "empty")
    else:
        if has_sources:
            check("executiveSummary contains 'Sources:'  (Foundry IQ active)", True, "")
        else:
            print(f"  {YELLOW}[INFO]{RESET} AZURE_AI_PROJECT_CONNECTION_STRING not set locally")
            print(f"  {YELLOW}[INFO]{RESET} If backend env has it, Foundry IQ is active server-side")
            print(f"  {YELLOW}[INFO]{RESET} Summary: {summary[:120]!r}")
    print()

    # ── 9. Employee analytics ─────────────────────────────────────────────────
    print(f"{BOLD}9. Employee analytics{RESET}")
    employees = report.get("employeeSummaries") or []
    check("At least one employee summary", len(employees) >= 1, f"count={len(employees)}")
    if employees:
        all_names = [e.get("employee_name") for e in employees]
        check("Papadopoulos Nikos present",
              any("Papadopoulos" in (n or "") for n in all_names),
              f"names: {all_names}")
    print()

    # ── Result summary ────────────────────────────────────────────────────────
    passed = sum(1 for _, ok, _ in _results if ok)
    failed = sum(1 for _, ok, _ in _results if not ok)
    total  = len(_results)
    print("─" * 64)
    if failed == 0:
        print(f"{GREEN}{BOLD}ALL {total} CHECKS PASSED{RESET}")
    else:
        print(f"{RED}{BOLD}{failed} / {total} CHECKS FAILED{RESET}")
        print("\nFailed:")
        for name, ok, detail in _results:
            if not ok:
                print(f"  {RED}✗{RESET} {name}" + (f"  — {detail}" if detail else ""))
    print()
    return failed == 0


if __name__ == "__main__":
    sys.exit(0 if run_e2e() else 1)
