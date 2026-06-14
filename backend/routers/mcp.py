"""Archon MCP Server — Model Context Protocol over Streamable HTTP.

Exposes Archon's financial intelligence as MCP tools so M365 Copilot agents,
Claude, and any MCP-compatible client can read and trigger financial analysis
using the standard protocol.

Transport : Streamable HTTP (JSON-RPC 2.0 over POST /mcp)
Protocol  : MCP spec 2024-11-05  https://modelcontextprotocol.io/specification

Tools
-----
list_periods         List reporting periods that have extracted documents.
get_financial_report Retrieve a cached FinancialReport for a period (no re-run).
analyze_period       Trigger the full 7-agent pipeline and return the report.
"""

import json
import logging
import os

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

log = logging.getLogger("archon.mcp")
router = APIRouter()

ANALYSIS_URL = os.getenv("ANALYSIS_ENDPOINT_URL", "http://analysis:8001")

_TOOLS = [
    {
        "name": "list_periods",
        "description": (
            "List reporting periods (YYYY-MM) for which Archon has extracted financial documents "
            "in Azure Blob Storage. Use this to discover available data before fetching reports."
        ),
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_financial_report",
        "description": (
            "Retrieve a cached Archon FinancialReport for a given period. "
            "Returns P&L, cash flow, expense breakdown, payroll reconciliation "
            "(bank net vs. true employer cost including IKA/EFKA), and a "
            "Foundry IQ-grounded executive summary with regulatory citations "
            "(IFRS/IAS 1/IAS 19, Law 4387/2016 EFKA, Greek VAT N.2859/2000). "
            "Returns 404 if no cached report exists — use analyze_period first."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "pattern": "^\\d{4}-\\d{2}$",
                    "description": "Reporting period YYYY-MM (e.g. 2026-01)",
                }
            },
            "required": ["period"],
        },
    },
    {
        "name": "analyze_period",
        "description": (
            "Trigger the full 7-agent Archon analysis pipeline for a period and return the report. "
            "Pipeline: ClassifierAgent → PnLAgent → CashFlowAgent → EmployeeAgent → "
            "ValidatorAgent → ReconciliationAgent → NarratorAgent (Foundry IQ). "
            "Takes 30–90 seconds. Use when no cached report exists or fresh analysis is needed."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "pattern": "^\\d{4}-\\d{2}$",
                    "description": "Reporting period YYYY-MM (e.g. 2026-01)",
                }
            },
            "required": ["period"],
        },
    },
]


async def _analysis_get(path: str) -> dict:
    async with httpx.AsyncClient(timeout=180.0) as client:
        resp = await client.get(f"{ANALYSIS_URL}{path}")
        resp.raise_for_status()
        return resp.json()


async def _analysis_post(path: str, body: dict) -> dict:
    async with httpx.AsyncClient(timeout=180.0) as client:
        resp = await client.post(f"{ANALYSIS_URL}{path}", json=body)
        resp.raise_for_status()
        return resp.json()


async def _dispatch(name: str, arguments: dict) -> str:
    try:
        if name == "list_periods":
            data = await _analysis_get("/periods")
            return json.dumps(data)
        if name == "get_financial_report":
            data = await _analysis_get(f"/reports/{arguments['period']}")
            return json.dumps(data)
        if name == "analyze_period":
            data = await _analysis_post("/analyze", {"period": arguments["period"]})
            return json.dumps(data)
        return json.dumps({"error": f"Unknown tool: {name}"})
    except httpx.HTTPStatusError as exc:
        return json.dumps({"error": f"HTTP {exc.response.status_code}: {exc.response.text[:300]}"})
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def _ok(req_id, result: dict):
    return JSONResponse({"jsonrpc": "2.0", "id": req_id, "result": result})


def _err(req_id, code: int, message: str):
    return JSONResponse({"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}})


@router.get("/mcp")
def mcp_discovery():
    """MCP server discovery — returns server metadata and available tools."""
    return {
        "name": "archon-mcp",
        "version": "1.0.0",
        "description": "Archon Financial Intelligence MCP Server",
        "protocolVersion": "2024-11-05",
        "transport": "streamable-http",
        "endpoint": "/mcp",
        "tools": [t["name"] for t in _TOOLS],
    }


@router.post("/mcp")
async def mcp_endpoint(request: Request):
    """MCP Streamable HTTP transport — handles all MCP JSON-RPC methods."""
    try:
        body = await request.json()
    except Exception:
        return _err(None, -32700, "Parse error")

    req_id = body.get("id")
    method = body.get("method", "")
    params = body.get("params", {})

    log.info("MCP %s id=%s", method, req_id)

    if method == "initialize":
        return _ok(req_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}, "resources": {}},
            "serverInfo": {"name": "archon-mcp", "version": "1.0.0"},
        })

    if method == "tools/list":
        return _ok(req_id, {"tools": _TOOLS})

    if method == "tools/call":
        name = params.get("name", "")
        arguments = params.get("arguments", {})
        log.info("MCP tool call: %s %s", name, arguments)
        text = await _dispatch(name, arguments)
        return _ok(req_id, {"content": [{"type": "text", "text": text}]})

    if method == "resources/list":
        return _ok(req_id, {"resources": []})

    if method.startswith("notifications/"):
        return Response(status_code=204)

    return _err(req_id, -32601, f"Method not found: {method}")
