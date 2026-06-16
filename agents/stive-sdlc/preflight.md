# Stive SDLC — PASO 0: Pre-flight (validación de entorno)

> Referenciado por `agents/stive-sdlc.agent.md`. Ejecutar al recibir `implementa`, `continúa` o `verifica requisitos`. Si hay errores → detener, no continuar a PASO 1.

## PASO 0 — Pre-flight: validar entorno

Ejecutar siempre al recibir `"implementa HU-XXX"`, `"continúa HU-XXX"` o `"verifica requisitos"`. Si hay errores, detener y mostrar reporte correctivo.

```bash
PREFLIGHT_ERRORS=0

# 1. Python 3.8+
PY_VERSION=$(python3 --version 2>&1)
if python3 -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)" 2>/dev/null; then
  echo "  ✅ $PY_VERSION"
else
  echo "  ❌ Python 3.8+ requerido — encontrado: $PY_VERSION"
  PREFLIGHT_ERRORS=$((PREFLIGHT_ERRORS+1))
fi

# 2. Atlassian MCP accesible
ATLASSIAN_REACHABLE=$(python3 -c "
import socket
try:
    socket.setdefaulttimeout(5)
    socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(('mcp.atlassian.com', 443))
    print('OK')
except Exception:
    print('ERR')
" 2>/dev/null)
if [ "$ATLASSIAN_REACHABLE" = "OK" ]; then
  echo "  ✅ Atlassian MCP accesible — autenticar con getVisibleJiraProjects() si es la primera vez"
else
  echo "  ❌ Atlassian MCP no accesible — verifica tu conexión"
  PREFLIGHT_ERRORS=$((PREFLIGHT_ERRORS+1))
fi

# 3. Repositorio git
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "  ✅ Repo git válido (rama: $(git branch --show-current))"
else
  echo "  ❌ No estás dentro de un repositorio git"
  PREFLIGHT_ERRORS=$((PREFLIGHT_ERRORS+1))
fi

# 4. Remote git
REMOTE=$(git remote 2>/dev/null | head -1)
if [ -n "$REMOTE" ]; then
  echo "  ✅ Remote '$REMOTE': $(git remote get-url "$REMOTE" 2>/dev/null)"
else
  echo "  ❌ No hay remote git configurado (necesario para push del PR)"
  PREFLIGHT_ERRORS=$((PREFLIGHT_ERRORS+1))
fi

# 5. Node.js (GitHub MCP via npx)
if command -v node >/dev/null 2>&1; then
  echo "  ✅ Node.js $(node --version) — GitHub MCP solicitará PAT en primer uso"
else
  echo "  ❌ Node.js no instalado (requerido para crear PRs en Etapa 4)"
  PREFLIGHT_ERRORS=$((PREFLIGHT_ERRORS+1))
fi

[ $PREFLIGHT_ERRORS -eq 0 ] && echo "  ✅ Entorno listo" || echo "  ❌ $PREFLIGHT_ERRORS error(s) — corrige antes de continuar"
```

Si `PREFLIGHT_ERRORS > 0` → detener. No continuar a PASO 1.
