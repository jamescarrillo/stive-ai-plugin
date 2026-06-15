#!/usr/bin/env python3
"""
MCP Server for JIRA integration — Atlassian-compatible interface.

Expone los mismos nombres de tools que el Atlassian Remote MCP (mcp.atlassian.com)
para que las pruebas en Claude Code CLI sean idénticas al flujo en VS Code Copilot.

Protocol: JSON-RPC 2.0 over stdio (MCP spec 2024-11-05)

Environment:
  JIRA_BASE_URL      e.g. https://yourcompany.atlassian.net
  JIRA_USER_EMAIL    e.g. user@example.com
  JIRA_API_TOKEN     Atlassian API Token (https://id.atlassian.com/manage-profile/security/api-tokens)
"""

import json
import sys
import os
import re
import requests
from pathlib import Path
from datetime import datetime
from typing import Any

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
JIRA_BASE = os.environ.get("JIRA_BASE_URL", "").rstrip("/")
EMAIL = os.environ.get("JIRA_USER_EMAIL", "")
API_TOKEN = os.environ.get("JIRA_API_TOKEN", "")

SPECS_DIR = Path(".github/specs")
METADATA_DIR = SPECS_DIR / ".metadata"
PLAN_DIR = Path(".github/modernize")


# ---------------------------------------------------------------------------
# JIRA REST helpers
# ---------------------------------------------------------------------------
def _jira_headers() -> dict:
    return {"Accept": "application/json", "Content-Type": "application/json"}


def _jira_auth():
    return (EMAIL, API_TOKEN) if EMAIL and API_TOKEN else None


def _jira_get(path: str, params: dict = None) -> dict:
    url = f"{JIRA_BASE}/rest/api/3{path}"
    resp = requests.get(url, auth=_jira_auth(), headers=_jira_headers(), params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def _jira_post(path: str, payload: dict) -> requests.Response:
    url = f"{JIRA_BASE}/rest/api/3{path}"
    resp = requests.post(url, auth=_jira_auth(), headers=_jira_headers(), json=payload, timeout=15)
    resp.raise_for_status()
    return resp


def _jira_search(jql: str, max_results: int, fields: list) -> dict:
    """Search JIRA issues using POST /search/jql (Atlassian Cloud v3+)."""
    payload = {"jql": jql, "maxResults": max_results, "fields": fields}
    resp = _jira_post("/search/jql", payload)
    return resp.json()


# ---------------------------------------------------------------------------
# ADF → Markdown
# ---------------------------------------------------------------------------
def _adf_to_markdown(adf: dict) -> str:
    if not isinstance(adf, dict):
        return str(adf)

    def _render_inline(node):
        if not isinstance(node, dict):
            return str(node) if node else ""
        t = node.get("type", "")
        if t == "text":
            text = node.get("text", "")
            for m in node.get("marks", []):
                mt = m.get("type")
                if mt == "code":
                    text = f"`{text}`"
                elif mt == "em":
                    text = f"*{text}*"
                elif mt == "strong":
                    text = f"**{text}**"
                elif mt == "link":
                    href = m.get("attrs", {}).get("href", "")
                    text = f"[{text}]({href})"
                elif mt == "strike":
                    text = f"~~{text}~~"
            return text
        if "text" in node:
            return node["text"]
        return ""

    def _render_block(node, indent=0):
        if not isinstance(node, dict):
            return []
        t = node.get("type", "")
        content = node.get("content", [])
        lines = []

        if t in ("paragraph", "heading"):
            if t == "heading":
                level = node.get("attrs", {}).get("level", 1)
                prefix = "#" * level + " "
            else:
                prefix = ""
            text = "".join(_render_inline(c) for c in content)
            if text.strip():
                lines.append(prefix + text)

        elif t in ("bulletList", "orderedList"):
            is_ordered = t == "orderedList"
            for i, item in enumerate(content, 1):
                for sub in item.get("content", []):
                    sub_lines = _render_block(sub, indent + 1)
                    bullet = f"{i}." if is_ordered else "-"
                    pad = "  " * indent + bullet + " "
                    for sl in sub_lines:
                        lines.append(pad + sl)

        elif t in ("blockquote", "panel", "infoPanel", "notePanel", "warningPanel"):
            qlines = []
            for child in content:
                qlines.extend(_render_block(child, indent))
            for ql in qlines:
                lines.append("> " + ql)
            if not qlines:
                for child in content:
                    lines.extend(_render_block(child, indent))

        elif t == "codeBlock":
            lang = node.get("attrs", {}).get("language", "")
            lines.append(f"```{lang}")
            lines.append("".join(c.get("text", "") for c in content))
            lines.append("```")

        elif t == "rule":
            lines.append("---")

        elif t == "table":
            rows = []
            for row in content:
                if row.get("type") != "tableRow":
                    continue
                cells = []
                for cell in row.get("content", []):
                    cell_text = " ".join(_render_block(cell))
                    cells.append(cell_text)
                rows.append(cells)
            if rows:
                for cells in rows:
                    lines.append("| " + " | ".join(cells) + " |")
                lines.insert(1, "| " + " | ".join(["---"] * len(rows[0])) + " |")

        else:
            for child in content:
                lines.extend(_render_block(child, indent))
            if not lines:
                text = node.get("text", "")
                if text:
                    lines.append(text)

        return lines

    return "\n\n".join(l for l in _render_block(adf) if l.strip())


# ---------------------------------------------------------------------------
# Spec builder
# ---------------------------------------------------------------------------
def _parse_description(text: str) -> dict:
    parts = {"como": "", "quiero": "", "para": "", "api_contrato": "", "criterios_aceptacion": ""}
    if not text:
        return parts

    next_section = r"(?:Quiero|Para|API\s+Contrato|Criterios\s+de\s+Aceptación)"

    m = re.search(
        r"(?:^|\n)\s*Como[:\s]+([\s\S]*?)(?=\n\s*(?:" + next_section + r"))",
        text, re.IGNORECASE | re.MULTILINE
    )
    if m:
        parts["como"] = m.group(1).strip()

    m = re.search(
        r"(?:^|\n)\s*Quiero[:\s]+([\s\S]*?)(?=\n\s*(?:Para|API\s+Contrato|Criterios\s+de\s+Aceptación))",
        text, re.IGNORECASE | re.MULTILINE
    )
    if m:
        parts["quiero"] = m.group(1).strip()

    m = re.search(
        r"(?:^|\n)\s*Para[:\s]+([\s\S]*?)(?=\n\s*(?:API\s+Contrato|Criterios\s+de\s+Aceptación))",
        text, re.IGNORECASE | re.MULTILINE
    )
    if m:
        parts["para"] = m.group(1).strip()

    m = re.search(r"API\s+Contrato[:\s]+(https?://\S+)", text, re.IGNORECASE)
    if m:
        parts["api_contrato"] = m.group(1).strip()

    m = re.search(r"Criterios\s+de\s+Aceptación[:\s]*\n([\s\S]*)", text, re.IGNORECASE)
    if m:
        parts["criterios_aceptacion"] = m.group(1).strip()

    return parts


def _parse_criteria(criteria_text: str) -> list:
    if not criteria_text:
        return []
    criteria = []
    current = None
    for line in criteria_text.split("\n"):
        stripped = line.strip()
        ca_match = re.match(
            r"\*?\s*((?:CA|Criterio)\s+\d+)[:\s)]+\*?\s*(.*)", stripped, re.IGNORECASE
        )
        if ca_match:
            if current:
                criteria.append(current)
            current = {"id": ca_match.group(1).strip(), "title": ca_match.group(2).strip(), "items": []}
        elif current and stripped:
            clean = re.sub(r"^[-*]\s*", "", stripped).strip()
            if clean:
                current["items"].append(clean)
    if current:
        criteria.append(current)
    return criteria


def _format_criteria_md(criteria: list) -> str:
    if not criteria:
        return "- No se definieron criterios de aceptación.\n"
    lines = []
    for c in criteria:
        lines.append(f'### {c["id"]}: {c["title"]}')
        lines.append("")
        for item in c["items"]:
            lines.append(f"- {item}")
        lines.append("")
    return "\n".join(lines)


def _infer_functional_reqs(summary: str, criteria: list) -> list:
    reqs = set()
    for c in criteria:
        for item in c["items"]:
            lower = item.lower()
            if "endpoint" in lower or "post" in lower or "api" in lower:
                ep = re.search(r"[A-Z]+\s+((?:/[a-z-]+)+)", item, re.IGNORECASE)
                if ep:
                    reqs.add(f"Crear endpoint {ep.group(0)}")
                else:
                    reqs.add("Implementar endpoint REST según API Contract")
            elif "validar" in lower or "inválido" in lower or "no existe" in lower:
                reqs.add(f"Validación: {item.split('.')[0].strip()}")
            elif "código de error" in lower or "error" in lower:
                code = re.search(r"`?([A-Z_]+)`?", item)
                if code:
                    reqs.add(f"Manejo de error {code.group(1)} con HTTP status code adecuado")
            elif "catálogo" in lower:
                reqs.add(f"Implementar catálogo de {item.split('de')[-1].strip() if 'de' in item else 'valores'}")
            elif "accountnumber" in lower or "generado" in lower:
                reqs.add("Generación automática de accountNumber")
            elif "status" in lower or "balance" in lower:
                reqs.add("Asignación de valores iniciales (status, balance)")
    if not reqs:
        reqs.add("Implementar funcionalidad descrita en la HU")
    return sorted(reqs)


def _build_spec(issue_key: str, issue_json: dict) -> str:
    fields = issue_json.get("fields", {})
    summary = fields.get("summary", "")
    description = fields.get("description") or ""
    if isinstance(description, dict) and description.get("type") == "doc":
        description_md = _adf_to_markdown(description)
    else:
        description_md = str(description)

    parsed = _parse_description(description_md)
    criteria_list = _parse_criteria(parsed["criterios_aceptacion"])
    criteria_md = _format_criteria_md(criteria_list)
    functional_reqs = _infer_functional_reqs(summary, criteria_list)
    reqs_md = "\n".join(f"{i}. {r}" for i, r in enumerate(functional_reqs, 1))

    context_lines = []
    if parsed["como"]:
        context_lines.append(f"**Como:** {parsed['como']}")
    if parsed["quiero"]:
        context_lines.append(f"**Quiero:** {parsed['quiero']}")
    if parsed["para"]:
        context_lines.append(f"**Para:** {parsed['para']}")
    if parsed["api_contrato"]:
        context_lines.append(f"**API Contrato:** [{parsed['api_contrato'].split('/')[-1]}]({parsed['api_contrato']})")
    context_md = "\n\n".join(context_lines)

    api_contrato_url = parsed.get("api_contrato", "")

    return f"""# {issue_key}

## Título

{summary}

## Descripción

{context_md}

## Criterios de aceptación

{criteria_md}
## Requisitos funcionales

{reqs_md}

## Requisitos no funcionales

- API RESTful con respuestas JSON estándar
- Códigos de error semánticos y consistentes
- Seguridad: validación de entrada
- Observabilidad: logging de operaciones

## Arquitectura propuesta

- Microservicio con arquitectura hexagonal (domain → application → infrastructure)
- Puertos inbound/outbound para desacoplamiento
- Adaptadores REST y persistencia JPA
- Mapeo MapStruct entre capas

## Notas técnicas

- API Contract: {api_contrato_url if api_contrato_url else 'Pendiente de definir'}
- Seguir convenciones BIAN para naming de endpoints
- Dominio puro sin anotaciones de framework

## Definición de terminado (DoD)

- [ ] Código implementado en `domain`, `application`, `infrastructure`
- [ ] Pruebas unitarias para todos los casos de uso
- [ ] Pruebas de integración para adaptadores REST y JPA
- [ ] Validación de errores con códigos específicos
- [ ] APIs BIAN-compliant
- [ ] Cobertura de pruebas >= 95%
- [ ] Dominio puro sin anotaciones Spring/JPA/Jackson
- [ ] Código listo para revisión humana
"""


# ---------------------------------------------------------------------------
# NL → JQL converter
# ---------------------------------------------------------------------------
def _nl_to_jql(query: str) -> str:
    """Converts natural language query to JQL."""
    q = query.strip()

    # Extract project key (uppercase token of 2+ chars, often followed by space or end)
    project_match = re.search(r'\b([A-Z][A-Z0-9_]{1,})\b', q)
    project = project_match.group(1) if project_match else None

    jql_parts = []

    if project:
        jql_parts.append(f"project = {project}")

    q_lower = q.lower()
    if any(w in q_lower for w in ["pendiente", "pending", "to do", "to_do", "por hacer", "backlog"]):
        jql_parts.append('status = "To Do"')
    elif any(w in q_lower for w in ["en progreso", "in progress", "in_progress", "en curso", "activo"]):
        jql_parts.append('status = "In Progress"')
    elif any(w in q_lower for w in ["en revisión", "in review", "in_review", "review"]):
        jql_parts.append('status = "In Review"')
    elif any(w in q_lower for w in ["completado", "done", "finalizado", "terminado", "finalized"]):
        jql_parts.append('status = "Done"')

    if not jql_parts:
        jql_parts = ["project is not EMPTY"]

    return " AND ".join(jql_parts) + " ORDER BY created DESC"


# ---------------------------------------------------------------------------
# MCP Tool implementations
# ---------------------------------------------------------------------------
class MCPError(Exception):
    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data


def _require_credentials():
    if not JIRA_BASE or not EMAIL or not API_TOKEN:
        raise MCPError(
            -32000,
            "JIRA credentials not configured. "
            "Set environment variables: JIRA_BASE_URL, JIRA_USER_EMAIL, JIRA_API_TOKEN"
        )


def _tool_get_issue_details(issue_id_or_key: str) -> dict:
    _require_credentials()
    issue = _jira_get(f"/issue/{issue_id_or_key}")
    content = _build_spec(issue_id_or_key, issue)

    SPECS_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)

    spec_path = SPECS_DIR / f"{issue_id_or_key}.md"
    spec_path.write_text(content, encoding="utf-8")

    meta = {
        "issue_key": issue_id_or_key,
        "timestamp": datetime.now().isoformat(),
        "spec_file": str(spec_path),
        "atlassian_url": JIRA_BASE,
        "status": "spec_generated",
    }
    meta_path = METADATA_DIR / f"{issue_id_or_key}.json"
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    fields = issue.get("fields", {})
    return {
        "issueKey": issue_id_or_key,
        "summary": fields.get("summary", ""),
        "status": fields.get("status", {}).get("name", ""),
        "assignee": (fields.get("assignee") or {}).get("displayName", "Unassigned"),
        "priority": (fields.get("priority") or {}).get("name", ""),
        "specFile": str(spec_path),
        "metadataFile": str(meta_path),
        "atlassianUrl": f"{JIRA_BASE}/browse/{issue_id_or_key}",
        "message": f"Spec generado: {spec_path}",
    }


def _tool_search_jql(jql: str, max_results: int = 20) -> dict:
    _require_credentials()
    fields = ["summary", "status", "priority", "assignee"]
    data = _jira_search(jql, max_results, fields)
    issues = []
    for iss in data.get("issues", []):
        f = iss.get("fields", {})
        issues.append({
            "key": iss["key"],
            "summary": f.get("summary", ""),
            "status": f.get("status", {}).get("name", ""),
            "priority": (f.get("priority") or {}).get("name", ""),
            "assignee": (f.get("assignee") or {}).get("displayName", "Unassigned"),
            "url": f"{JIRA_BASE}/browse/{iss['key']}",
        })
    return {
        "jql": jql,
        "total": data.get("total", 0),
        "returned": len(issues),
        "issues": issues,
    }


def _tool_search_natural_language(query: str, max_results: int = 20) -> dict:
    jql = _nl_to_jql(query)
    result = _tool_search_jql(jql, max_results)
    result["naturalLanguageQuery"] = query
    result["derivedJql"] = jql
    return result


def _tool_get_visible_projects() -> dict:
    _require_credentials()
    data = _jira_get("/project/search", params={"maxResults": 50, "orderBy": "name"})
    projects = []
    for proj in data.get("values", []):
        projects.append({
            "key": proj.get("key"),
            "name": proj.get("name"),
            "type": proj.get("projectTypeKey"),
            "url": f"{JIRA_BASE}/projects/{proj.get('key')}",
        })
    return {"total": len(projects), "projects": projects}


def _tool_transition_issue(issue_id_or_key: str, transition: str) -> dict:
    _require_credentials()

    transitions_resp = _jira_get(f"/issue/{issue_id_or_key}/transitions")
    transitions = transitions_resp.get("transitions", [])

    if not transitions:
        raise MCPError(-32000, f"No transitions available for {issue_id_or_key}")

    target = None
    for t in transitions:
        t_name = t.get("to", {}).get("name", "")
        if t_name.lower() == transition.lower():
            target = t
            break

    if target is None:
        available = [t.get("to", {}).get("name", "") for t in transitions]
        raise MCPError(
            -32000,
            f"Transition '{transition}' not available for {issue_id_or_key}. "
            f"Available: {available}"
        )

    _jira_post(f"/issue/{issue_id_or_key}/transitions", {"transition": {"id": target["id"]}})

    # Sync metadata
    meta_path = METADATA_DIR / f"{issue_id_or_key}.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta["jira_status"] = transition
            meta["jira_status_updated_at"] = datetime.now().isoformat()
            meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    return {
        "issueKey": issue_id_or_key,
        "newStatus": transition,
        "transitionId": target["id"],
        "url": f"{JIRA_BASE}/browse/{issue_id_or_key}",
        "message": f"{issue_id_or_key} transicionado a '{transition}' exitosamente",
    }


# ---------------------------------------------------------------------------
# MCP Tool registry (Atlassian-compatible names)
# ---------------------------------------------------------------------------
TOOLS = [
    {
        "name": "getJiraIssueDetails",
        "description": "Obtiene detalles de un issue de JIRA y genera el spec .md en .github/specs/",
        "inputSchema": {
            "type": "object",
            "properties": {
                "issueIdOrKey": {
                    "type": "string",
                    "description": "ID o Key del issue. Ej: SCRUM-5, HU-123",
                }
            },
            "required": ["issueIdOrKey"],
        },
    },
    {
        "name": "searchJiraIssuesUsingJQL",
        "description": "Busca issues en JIRA usando JQL (JIRA Query Language)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "jql": {
                    "type": "string",
                    "description": "Query JQL. Ej: project = SCRUM AND status = 'To Do' ORDER BY created DESC",
                },
                "maxResults": {
                    "type": "integer",
                    "description": "Máximo número de resultados (default 20)",
                },
            },
            "required": ["jql"],
        },
    },
    {
        "name": "searchJiraIssuesUsingNaturalLanguage",
        "description": "Busca issues en JIRA usando lenguaje natural. Convierte la consulta a JQL automáticamente.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Consulta en lenguaje natural. Ej: 'HUs pendientes en proyecto PY_AGENTIC_IA'",
                },
                "maxResults": {
                    "type": "integer",
                    "description": "Máximo número de resultados (default 20)",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "getVisibleJiraProjects",
        "description": "Lista todos los proyectos de JIRA accesibles con las credenciales configuradas",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "transitionJiraIssue",
        "description": "Transiciona un issue de JIRA al estado indicado. Estados válidos: TO_DO, IN_PROGRESS, IN_REVIEW, FINALIZED",
        "inputSchema": {
            "type": "object",
            "properties": {
                "issueIdOrKey": {
                    "type": "string",
                    "description": "ID o Key del issue. Ej: SCRUM-5, HU-123",
                },
                "transition": {
                    "type": "string",
                    "description": "Nombre del estado destino. Ej: IN_PROGRESS, IN_REVIEW, FINALIZED",
                },
            },
            "required": ["issueIdOrKey", "transition"],
        },
    },
]


def _handle_tool_call(name: str, args: dict) -> Any:
    if name == "getJiraIssueDetails":
        return _tool_get_issue_details(args["issueIdOrKey"])
    elif name == "searchJiraIssuesUsingJQL":
        return _tool_search_jql(args["jql"], args.get("maxResults", 20))
    elif name == "searchJiraIssuesUsingNaturalLanguage":
        return _tool_search_natural_language(args["query"], args.get("maxResults", 20))
    elif name == "getVisibleJiraProjects":
        return _tool_get_visible_projects()
    elif name == "transitionJiraIssue":
        return _tool_transition_issue(args["issueIdOrKey"], args["transition"])
    else:
        raise MCPError(-32601, f"Unknown tool: {name}")


# ---------------------------------------------------------------------------
# MCP Transport (JSON-RPC 2.0 stdio)
# ---------------------------------------------------------------------------
def _send(msg: dict):
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def _recv() -> dict | None:
    line = sys.stdin.readline()
    if not line:
        return None
    return json.loads(line)


def _handle_request(req: dict) -> dict | None:
    req_id = req.get("id")
    method = req.get("method", "")
    params = req.get("params", {})

    try:
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "jira-atlassian-compatible", "version": "3.0.0"},
                },
            }
        elif method == "notifications/initialized":
            return None
        elif method == "tools/list":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}
        elif method == "tools/call":
            result = _handle_tool_call(params.get("name", ""), params.get("arguments", {}))
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, indent=2, ensure_ascii=False)}]
                },
            }
        else:
            raise MCPError(-32601, f"Method not found: {method}")

    except MCPError as e:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": e.code, "message": e.message}}
    except Exception as e:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32603, "message": str(e)}}


def main():
    if not JIRA_BASE or not EMAIL or not API_TOKEN:
        print(
            "[MCP ERROR] Credenciales JIRA no configuradas.\n"
            "  export JIRA_BASE_URL=https://your-domain.atlassian.net\n"
            "  export JIRA_USER_EMAIL=your@email.com\n"
            "  export JIRA_API_TOKEN=your_api_token",
            file=sys.stderr
        )

    print(f"[MCP] jira-atlassian-compatible v3.0.0 — {JIRA_BASE or 'NO CONFIGURADO'}", file=sys.stderr)
    print("[MCP] Tools: getJiraIssueDetails, searchJiraIssuesUsingJQL, searchJiraIssuesUsingNaturalLanguage, getVisibleJiraProjects, transitionJiraIssue", file=sys.stderr)

    while True:
        try:
            req = _recv()
            if req is None:
                break
            resp = _handle_request(req)
            if resp is not None:
                _send(resp)
        except json.JSONDecodeError:
            _send({"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}})
        except (EOFError, KeyboardInterrupt):
            break
        except Exception as e:
            _send({"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}})


if __name__ == "__main__":
    main()
