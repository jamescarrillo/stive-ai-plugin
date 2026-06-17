---
name: stive-sdlc-preflight
description: Material de soporte de stive-sdlc (no es un agente seleccionable).
user-invocable: false
---

# Stive SDLC — PASO 0: Pre-flight (validación de entorno, según config)

> Referenciado por `agents/stive-sdlc/stive-sdlc.agent.md`. Ejecutar al recibir `implementa`, `continúa` o `verifica requisitos`. **Valida solo lo que la configuración (`/init`) requiere.** Si hay errores → detener, no continuar a PASO 1.

## PASO 0 — Pre-flight config-aware

Lee `.github/stive.config.json` (si no existe, usa defaults `jira.mode=remote`, `github.createPr=false` y sugiere correr `/init`). Valida según la selección.

```bash
PREFLIGHT_ERRORS=0

# 0. Config
if [ -f ".github/stive.config.json" ]; then
  JIRA_MODE=$(python3 -c "import json;print(json.load(open('.github/stive.config.json'))['jira']['mode'])" 2>/dev/null)
  GITHUB_PR=$(python3 -c "import json;print(str(json.load(open('.github/stive.config.json'))['github']['createPr']).lower())" 2>/dev/null)
  echo "  ⚙️  Config: jira.mode=$JIRA_MODE · github.createPr=$GITHUB_PR"
else
  JIRA_MODE="remote"; GITHUB_PR="false"
  echo "  ⚠️  Sin .github/stive.config.json — usando defaults (remote/commit). Corre /init para fijarla."
fi

# 1. Python 3.8+ (siempre)
PY_VERSION=$(python3 --version 2>&1)
python3 -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)" 2>/dev/null \
  && echo "  ✅ $PY_VERSION" \
  || { echo "  ❌ Python 3.8+ requerido — encontrado: $PY_VERSION"; PREFLIGHT_ERRORS=$((PREFLIGHT_ERRORS+1)); }

# 2. Repositorio git (siempre)
git rev-parse --is-inside-work-tree >/dev/null 2>&1 \
  && echo "  ✅ Repo git válido (rama: $(git branch --show-current))" \
  || { echo "  ❌ No estás dentro de un repositorio git"; PREFLIGHT_ERRORS=$((PREFLIGHT_ERRORS+1)); }

# 3. JIRA — según jira.mode (remote | local)
if [ "$JIRA_MODE" = "remote" ]; then
  python3 -c "import socket; socket.setdefaulttimeout(5); socket.socket().connect(('mcp.atlassian.com',443))" 2>/dev/null \
    && echo "  ✅ JIRA(remote) → Atlassian alcanzable (OAuth en la 1ª llamada con getVisibleJiraProjects)" \
    || { echo "  ❌ JIRA(remote) → no se alcanza mcp.atlassian.com (¿proxy/red?). Cambia a 'local' con /init si el OAuth está bloqueado."; PREFLIGHT_ERRORS=$((PREFLIGHT_ERRORS+1)); }
elif [ "$JIRA_MODE" = "local" ]; then
  JERR=0
  for v in JIRA_BASE_URL JIRA_USER_EMAIL JIRA_API_TOKEN; do
    [ -n "$(printenv $v)" ] || { echo "  ❌ JIRA(local) → falta env var $v"; JERR=1; }
  done
  python3 -c "import requests" 2>/dev/null || { echo "  ❌ JIRA(local) → falta 'requests' (pip install -r scripts/requirements.txt)"; JERR=1; }
  if [ $JERR -eq 0 ]; then
    # Test REAL de autenticación
    python3 - <<'PY' && echo "  ✅ JIRA(local) → API token autentica" || { echo "  ❌ JIRA(local) → el API token no autenticó"; exit 1; }
import os,base64,urllib.request
b=os.environ["JIRA_BASE_URL"].rstrip("/");a=base64.b64encode(f'{os.environ["JIRA_USER_EMAIL"]}:{os.environ["JIRA_API_TOKEN"]}'.encode()).decode()
urllib.request.urlopen(urllib.request.Request(f"{b}/rest/api/3/myself",headers={"Authorization":f"Basic {a}"}),timeout=15)
PY
    [ $? -eq 0 ] || PREFLIGHT_ERRORS=$((PREFLIGHT_ERRORS+1))
  else
    PREFLIGHT_ERRORS=$((PREFLIGHT_ERRORS+1))
  fi
else
  echo "  ❌ jira.mode desconocido: '$JIRA_MODE' (usa 'remote' o 'local' con /init)"; PREFLIGHT_ERRORS=$((PREFLIGHT_ERRORS+1))
fi

# 4. GitHub — solo si github.createPr=true (MCP remoto oficial de GitHub)
if [ "$GITHUB_PR" = "true" ]; then
  [ -n "$(printenv GITHUB_TOKEN)" ] \
    && echo "  ✅ GITHUB_TOKEN presente" \
    || { echo "  ❌ GITHUB_TOKEN ausente — define un PAT (scope 'repo') o elige 'commit' con /init"; PREFLIGHT_ERRORS=$((PREFLIGHT_ERRORS+1)); }
  [ -n "$(git remote 2>/dev/null | head -1)" ] \
    && echo "  ✅ Remote git: $(git remote get-url $(git remote|head -1) 2>/dev/null)" \
    || { echo "  ❌ Sin remote git (necesario para el PR)"; PREFLIGHT_ERRORS=$((PREFLIGHT_ERRORS+1)); }
else
  echo "  ℹ️  GitHub en modo commit (github.createPr=false) → Etapa 4 hace commit local; el PR es manual. No se valida Node/PAT."
fi

[ $PREFLIGHT_ERRORS -eq 0 ] && echo "  ✅ Entorno listo (según tu config)" || echo "  ❌ $PREFLIGHT_ERRORS error(s) — corrige antes de continuar"
```

Si `PREFLIGHT_ERRORS > 0` → detener. No continuar a PASO 1.
