---
name: stive-sdlc-preflight
description: Material de soporte de stive-sdlc (no es un agente seleccionable).
user-invocable: false
---

# Stive SDLC — PASO 0: Pre-flight (validación de entorno, según config)

> Referenciado por `agents/stive-sdlc/stive-sdlc.agent.md`. Ejecutar al recibir `implementa`, `continúa` o `verifica requisitos`. **Valida solo lo que la configuración (`/init`) requiere.** Si hay errores → detener, no continuar a PASO 1.

## PASO 0 — Pre-flight config-aware

Lee `.github/stive.config.json` (si no existe, usa defaults `jira.mode=auto`, `github.enabled=false` y sugiere correr `/init`). Valida según el modo.

```bash
PREFLIGHT_ERRORS=0

# 0. Config
if [ -f ".github/stive.config.json" ]; then
  JIRA_MODE=$(python3 -c "import json;print(json.load(open('.github/stive.config.json'))['jira']['mode'])" 2>/dev/null)
  GITHUB_ENABLED=$(python3 -c "import json;print(str(json.load(open('.github/stive.config.json'))['github']['enabled']).lower())" 2>/dev/null)
  echo "  ⚙️  Config: jira.mode=$JIRA_MODE · github.enabled=$GITHUB_ENABLED"
else
  JIRA_MODE="auto"; GITHUB_ENABLED="false"
  echo "  ⚠️  Sin .github/stive.config.json — usando defaults (auto/false). Corre /init para fijarla."
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

# 3. JIRA — según jira.mode
probe_atlassian() {
  python3 -c "
import socket
try:
    socket.setdefaulttimeout(5); socket.socket().connect(('mcp.atlassian.com',443)); print('OK')
except Exception: print('ERR')" 2>/dev/null
}
validate_script() {
  local missing=0
  for v in JIRA_BASE_URL JIRA_USER_EMAIL JIRA_API_TOKEN; do
    [ -n "$(printenv $v)" ] || { echo "     ❌ Falta env var $v (requerida por el script local)"; missing=1; }
  done
  python3 -c "import requests" 2>/dev/null || { echo "     ❌ Falta dependencia 'requests' (pip install -r scripts/requirements.txt)"; missing=1; }
  return $missing
}

EFFECTIVE_JIRA="$JIRA_MODE"
if [ "$JIRA_MODE" = "auto" ]; then
  if [ "$(probe_atlassian)" = "OK" ]; then
    EFFECTIVE_JIRA="mcp"; echo "  ✅ JIRA(auto) → MCP de Atlassian accesible; se usará MCP (OAuth la primera vez)"
  else
    EFFECTIVE_JIRA="script"; echo "  ⚠️ JIRA(auto) → MCP de Atlassian no accesible; se usará el SCRIPT LOCAL. Validando requisitos:"
  fi
fi

if [ "$EFFECTIVE_JIRA" = "mcp" ] && [ "$JIRA_MODE" = "mcp" ]; then
  [ "$(probe_atlassian)" = "OK" ] \
    && echo "  ✅ JIRA(mcp) → Atlassian accesible (OAuth la primera vez con getVisibleJiraProjects)" \
    || { echo "  ❌ JIRA(mcp) → Atlassian no accesible — revisa red/proxy o cambia a 'script' con /init"; PREFLIGHT_ERRORS=$((PREFLIGHT_ERRORS+1)); }
elif [ "$EFFECTIVE_JIRA" = "script" ]; then
  if validate_script; then echo "  ✅ JIRA(script) → env vars + 'requests' OK (scripts/jira_mcp_server.py)"; else PREFLIGHT_ERRORS=$((PREFLIGHT_ERRORS+1)); fi
fi

# 4. GitHub — solo si github.enabled=true
if [ "$GITHUB_ENABLED" = "true" ]; then
  command -v node >/dev/null 2>&1 \
    && echo "  ✅ Node.js $(node --version) (GitHub MCP vía npx)" \
    || { echo "  ❌ Node.js no instalado (requerido para el PR en Etapa 4)"; PREFLIGHT_ERRORS=$((PREFLIGHT_ERRORS+1)); }
  [ -n "$(printenv GITHUB_TOKEN)" ] \
    && echo "  ✅ GITHUB_TOKEN presente" \
    || { echo "  ❌ GITHUB_TOKEN ausente (la cuenta debe permitir generar un PAT)"; PREFLIGHT_ERRORS=$((PREFLIGHT_ERRORS+1)); }
  # Remote git necesario para el PR
  [ -n "$(git remote 2>/dev/null | head -1)" ] \
    && echo "  ✅ Remote git: $(git remote get-url $(git remote|head -1) 2>/dev/null)" \
    || { echo "  ❌ Sin remote git (necesario para push del PR)"; PREFLIGHT_ERRORS=$((PREFLIGHT_ERRORS+1)); }
else
  echo "  ℹ️  GitHub deshabilitado (github.enabled=false) → Etapa 4 hará commit en la rama local; el PR es manual. No se valida Node/PAT."
fi

[ $PREFLIGHT_ERRORS -eq 0 ] && echo "  ✅ Entorno listo (según tu config)" || echo "  ❌ $PREFLIGHT_ERRORS error(es) — corrige antes de continuar"
```

Si `PREFLIGHT_ERRORS > 0` → detener. No continuar a PASO 1. Guarda `EFFECTIVE_JIRA` (mcp | script) para que Etapa 1 sepa qué usar.
