---
name: stive-sdlc-init
description: Material de soporte de stive-sdlc (no es un agente seleccionable).
user-invocable: false
---

# Stive SDLC — Comando `/init`: configuración y scaffolding

> Referenciado por `agents/stive-sdlc/stive-sdlc.agent.md`. Se ejecuta cuando el usuario escribe `/init`, `init`, `configura` o `inicializa stive`. Crea la configuración del proyecto y las carpetas de artefactos en el repo destino.

## Objetivo
1. Preguntar **en el chat** las preferencias de conexión.
2. Guardar `.github/stive.config.json`.
3. Crear las carpetas de artefactos.

## Esquema del config — `.github/stive.config.json`
```json
{
  "jira":   { "mode": "auto" },
  "github": { "enabled": false }
}
```
| Campo | Valores | Significado |
|---|---|---|
| `jira.mode` | `mcp` | Solo Atlassian MCP remoto (OAuth en navegador). |
| | `script` | Solo el script local `scripts/jira_mcp_server.py` (API token vía env vars). |
| | `auto` (default) | Intenta MCP; si no conecta, cae al script (validando sus requisitos). Recomendado en entornos restringidos. |
| `github.enabled` | `false` (default) | La creación de PR **no** es parte del flujo. Etapa 4 hace commit + rama local y deja el PR manual. |
| | `true` | Intenta crear el PR vía GitHub MCP (requiere `GITHUB_TOKEN`). |

## Flujo interactivo (presentar en el chat)

**Paso 1 — Conexión a JIRA.** Preguntar:
```
¿Cómo conectarás Stive con JIRA?
  1) auto    → intenta el MCP de Atlassian (OAuth); si no conecta, usa el script local. (Recomendado)
  2) mcp     → solo MCP de Atlassian (OAuth en el navegador).
  3) script  → solo script local con API token (JIRA_BASE_URL, JIRA_USER_EMAIL, JIRA_API_TOKEN).
Responde 1, 2 o 3.
```
→ mapear a `"auto" | "mcp" | "script"`.

**Paso 2 — GitHub en el flujo.** Preguntar:
```
¿Habilitar la creación de Pull Request en GitHub al final del flujo?
  • No (default)  → Stive hace commit en la rama local; el PR lo creas tú manualmente.
  • Sí            → Stive intenta crear el PR vía GitHub MCP (requiere un PAT en GITHUB_TOKEN).
Responde "no" o "sí".
```
→ mapear a `false | true`. Si responde "sí", **advertir**: si la cuenta es administrada por la empresa y no permite PAT, la creación de PR fallará; puede dejarse en `false`.

**Paso 3 — Escribir config y crear carpetas.**
```python
import json
from pathlib import Path
cfg = {"jira": {"mode": JIRA_MODE}, "github": {"enabled": GITHUB_ENABLED}}
Path(".github").mkdir(exist_ok=True)
Path(".github/stive.config.json").write_text(json.dumps(cfg, indent=2))
for d in [".github/specs", ".github/specs/.metadata", ".github/plans"]:
    Path(d).mkdir(parents=True, exist_ok=True)
```

**Paso 4 — Confirmar.** Mostrar:
```
╔══════════════════════════════════════════════════════════════╗
║  STIVE INICIALIZADO ✅                                        ║
╠══════════════════════════════════════════════════════════════╣
║  Config: .github/stive.config.json                           ║
║   • JIRA   : [mode]                                          ║
║   • GitHub : [enabled]                                        ║
║  Carpetas: .github/specs · .github/specs/.metadata · .github/plans ║
╚══════════════════════════════════════════════════════════════╝
Siguiente paso: "verifica requisitos" (valida solo lo que tu config necesita).
```

## Lectura del config (otros pasos del flujo)
Cualquier etapa lee la config así (si no existe, usar defaults `auto` / `false` e indicar que conviene correr `/init`):
```python
import json
from pathlib import Path
p = Path(".github/stive.config.json")
cfg = json.loads(p.read_text()) if p.exists() else {"jira": {"mode": "auto"}, "github": {"enabled": False}}
JIRA_MODE = cfg["jira"]["mode"]
GITHUB_ENABLED = cfg["github"]["enabled"]
```
