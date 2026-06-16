---
name: stive-sdlc-detection
description: Material de soporte de stive-sdlc (no es un agente seleccionable).
user-invocable: false
---

# Stive SDLC — PASO 2: Detección de framework y estructura

> Referenciado por `agents/stive-sdlc.agent.md`. Ejecutar solo cuando `STATUS == "new"`. Detecta framework + projectStructure, resuelve base package y paths hexagonales, y guarda todo en el metadata.

## PASO 2 — Detección de framework y estructura

Ejecutar solo cuando `STATUS == "new"`.

```bash
# Framework
if grep -q "spring-boot-starter-parent\|spring-boot-dependencies" pom.xml 2>/dev/null; then
  FRAMEWORK="spring-boot"
elif grep -q "quarkus-bom\|io.quarkus" pom.xml 2>/dev/null; then
  FRAMEWORK="quarkus"
else
  FRAMEWORK="unknown"
fi

# Estructura
JAVA_FILES=$(find src/main/java -name "*.java" 2>/dev/null | wc -l | tr -d ' ')
HAS_HEX_DOMAIN=$(find src/main/java -type d \( -name "domain" -o -name "core" \) 2>/dev/null | head -1)
HAS_HEX_PORTS=$(find src/main/java -type d \( -name "ports" -o -name "port" -o -name "driven" -o -name "driving" -o -name "primary" -o -name "secondary" \) 2>/dev/null | head -1)
HAS_HEX_ADAPTERS=$(find src/main/java -type d \( -name "adapters" -o -name "adapter" \) 2>/dev/null | head -1)
HAS_USE_CASE=$(find src/main/java \( -name "*UseCase.java" -o -name "*Port.java" \) 2>/dev/null | head -1)
HAS_CONTROLLER=$(find src/main/java -name "*Controller.java" 2>/dev/null | head -1)
HAS_SERVICE=$(find src/main/java \( -name "*Service.java" -o -name "*ServiceImpl.java" \) 2>/dev/null | head -1)
HAS_REPOSITORY=$(find src/main/java -name "*Repository.java" 2>/dev/null | head -1)

if [ "$JAVA_FILES" -eq 0 ]; then
  PROJECT_STRUCTURE="new"
elif [ -n "$HAS_HEX_DOMAIN" ] && { [ -n "$HAS_HEX_PORTS" ] || [ -n "$HAS_HEX_ADAPTERS" ] || [ -n "$HAS_USE_CASE" ]; }; then
  PROJECT_STRUCTURE="hexagonal"
elif [ -n "$HAS_CONTROLLER" ] && [ -n "$HAS_SERVICE" ] && [ -n "$HAS_REPOSITORY" ]; then
  PROJECT_STRUCTURE="traditional"
else
  PROJECT_STRUCTURE="mixed"
fi

# Base package
FIRST_JAVA=$(find src/main/java -name "*.java" -not -path "*/test/*" 2>/dev/null | head -1)
BASE_PACKAGE=$(grep "^package " "$FIRST_JAVA" 2>/dev/null | head -1 | sed 's/^package //; s/;//' | rev | cut -d. -f2- | rev)

# Paths hexagonales (para plan-generator)
HEX_DOMAIN_DIR=$(echo "$HAS_HEX_DOMAIN" | sed "s|src/main/java/||" | sed "s|.*\/||")
HEX_PORTS_DIR=$(echo "$HAS_HEX_PORTS" | sed "s|src/main/java/||" | sed "s|.*\/||")
HEX_ADAPTERS_DIR=$(echo "$HAS_HEX_ADAPTERS" | sed "s|src/main/java/||" | sed "s|.*\/||")
```

Guardar detección en metadata:
```python
import json, datetime
from pathlib import Path
Path(".github/specs/.metadata").mkdir(parents=True, exist_ok=True)
meta = {
    "issue_key": HU_KEY,
    "timestamp": datetime.datetime.now().isoformat(),
    "status": "new",
    "framework": FRAMEWORK,
    "projectStructure": PROJECT_STRUCTURE,
    "detectedBasePackage": BASE_PACKAGE,
    "hexDomainDir": HEX_DOMAIN_DIR or "domain",
    "hexPortsDir": HEX_PORTS_DIR or "ports",
    "hexAdaptersDir": HEX_ADAPTERS_DIR or "adapters"
}
Path(f".github/specs/.metadata/{HU_KEY}.json").write_text(json.dumps(meta, indent=2))
```

Mostrar al usuario:
```
╔══════════════════════════════════════════════════════════════╗
║  DETECCIÓN DE PROYECTO                                        ║
║  Framework:    [spring-boot | quarkus | unknown]             ║
║  Estructura:   [new | hexagonal | traditional | mixed]        ║
║  Base Package: [valor detectado]                             ║
╚══════════════════════════════════════════════════════════════╝
```
