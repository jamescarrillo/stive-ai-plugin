---
name: stive-sdlc-init
description: Material de soporte de stive-sdlc (no es un agente seleccionable).
user-invocable: false
---

# Stive SDLC — Comando `/init`: configuración y scaffolding

> Referenciado por `agents/stive-sdlc/stive-sdlc.agent.md`. Se ejecuta cuando el usuario escribe `/init`, `init`, `configura` o `inicializa stive`. Pregunta dos selecciones (que el usuario confirma), prueba la conexión, guarda la config y crea las carpetas de artefactos.

## Esquema del config — `.github/stive.config.json`
```json
{
  "jira":   { "mode": "remote" },
  "github": { "createPr": false }
}
```
| Campo | Valores | Significado |
|---|---|---|
| `jira.mode` | `remote` | JIRA vía MCP remoto de Atlassian (OAuth en el navegador). Servidor `atlassian`. |
| | `local` | JIRA vía script local `scripts/jira_mcp_server.py` (API token). Servidor `jira-local`. |
| `github.createPr` | `false` (default) | Etapa 4 = **commit en la rama local**; el PR lo crea el usuario. |
| | `true` | Etapa 4 = **crea el PR** vía GitHub MCP (requiere `GITHUB_TOKEN`). |

## Flujo interactivo (presentar en el chat y esperar confirmación)

### Selector 1 — Tipo de JIRA
```
¿Qué JIRA quieres usar?
  1) remoto  → MCP de Atlassian (OAuth en el navegador). Sin tokens en archivos.
  2) local   → script con API token (JIRA_BASE_URL, JIRA_USER_EMAIL, JIRA_API_TOKEN).
Responde 1 (remoto) o 2 (local).
```
→ mapear a `JIRA_MODE = "remote" | "local"`.

**Tras la selección, prueba la conexión** (feedback inmediato):
```bash
if [ "$JIRA_MODE" = "remote" ]; then
  python3 -c "import socket; socket.setdefaulttimeout(5); socket.socket().connect(('mcp.atlassian.com',443))" 2>/dev/null \
    && echo "  ✅ Atlassian alcanzable. El OAuth se abrirá en la primera llamada (o en 'verifica requisitos')." \
    || echo "  ⚠️ No se alcanza mcp.atlassian.com (¿proxy/red?). Considera 'local' si el OAuth está bloqueado."
else
  # Test REAL de autenticación con el API token
  python3 - <<'PY'
import os,base64,json,urllib.request
miss=[v for v in ("JIRA_BASE_URL","JIRA_USER_EMAIL","JIRA_API_TOKEN") if not os.environ.get(v)]
if miss: print("  ⚠️ Faltan env vars:", ", ".join(miss), "— ver README (generar API token de Atlassian)."); raise SystemExit
b=os.environ["JIRA_BASE_URL"].rstrip("/"); a=base64.b64encode(f'{os.environ["JIRA_USER_EMAIL"]}:{os.environ["JIRA_API_TOKEN"]}'.encode()).decode()
try:
    d=json.load(urllib.request.urlopen(urllib.request.Request(f"{b}/rest/api/3/myself",headers={"Authorization":f"Basic {a}"}),timeout=15))
    print(f"  ✅ Conexión local OK — autenticado como {d.get('displayName')}")
except Exception as e:
    print(f"  ⚠️ El API token no autenticó: {e}")
PY
fi
```
Si la prueba falla, **avisar** pero permitir continuar (el usuario puede corregir y reintentar con `verifica requisitos`).

### Selector 2 — GitHub (PR o commit)
```
Al terminar la implementación, ¿qué hace Stive?
  1) commit  → commit en la rama local; tú creas el PR. (Default, recomendado si no puedes generar PAT)
  2) PR      → crea el Pull Request en GitHub (requiere un PAT en GITHUB_TOKEN).
Responde 1 (commit) o 2 (PR).
```
→ mapear a `GITHUB_CREATE_PR = false | true`. Si elige `PR`, advertir: si la cuenta es corporativa y no permite PAT, fallará; puede quedar en `commit`.

### Escribir config + crear carpetas
```python
import json
from pathlib import Path
cfg = {"jira": {"mode": JIRA_MODE}, "github": {"createPr": GITHUB_CREATE_PR}}
Path(".github").mkdir(exist_ok=True)
Path(".github/stive.config.json").write_text(json.dumps(cfg, indent=2))
for d in [".github/specs", ".github/specs/.metadata", ".github/plans"]:
    Path(d).mkdir(parents=True, exist_ok=True)
```

### Confirmar
```
╔══════════════════════════════════════════════════════════════╗
║  STIVE INICIALIZADO ✅                                        ║
╠══════════════════════════════════════════════════════════════╣
║   • JIRA   : [remote | local]                               ║
║   • GitHub : [PR | commit local]                            ║
║   Config   : .github/stive.config.json                       ║
║   Carpetas : .github/specs · .metadata · .github/plans       ║
╚══════════════════════════════════════════════════════════════╝
Siguiente: "verifica requisitos" (valida según tu config) o "implementa SCRUM-XX".
```

## Lectura del config (otros pasos del flujo)
Si no existe, usar defaults `remote` / `createPr=false` e indicar que conviene correr `/init`.
```python
import json
from pathlib import Path
p = Path(".github/stive.config.json")
cfg = json.loads(p.read_text()) if p.exists() else {"jira": {"mode": "remote"}, "github": {"createPr": False}}
JIRA_MODE = cfg["jira"]["mode"]            # remote | local
GITHUB_CREATE_PR = cfg["github"]["createPr"]
```
