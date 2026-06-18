---
name: stive-sdlc-detection
description: Material de soporte de stive-sdlc (no es un agente seleccionable).
user-invocable: false
---

# Stive SDLC — PASO 2: Detección de framework y estructura

> Referenciado por `agents/stive-sdlc/stive-sdlc.agent.md`. Ejecutar solo cuando `STATUS == "new"`. Detecta framework + projectStructure, resuelve base package y paths hexagonales, y guarda todo en el metadata.

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

# Versión del framework (distingue Spring Boot 3.x vs 4.x)
FRAMEWORK_VERSION=""
if [ "$FRAMEWORK" = "spring-boot" ]; then
  # 1) versión del parent  2) property <spring-boot.version>
  FRAMEWORK_VERSION=$(grep -A2 'spring-boot-starter-parent' pom.xml 2>/dev/null | grep -oE '<version>[0-9]+\.[0-9]+\.[0-9]+[^<]*' | head -1 | sed 's|<version>||')
  [ -z "$FRAMEWORK_VERSION" ] && FRAMEWORK_VERSION=$(grep -oE '<spring-boot\.version>[0-9]+\.[0-9]+\.[0-9]+[^<]*' pom.xml 2>/dev/null | head -1 | sed 's|<spring-boot\.version>||')
elif [ "$FRAMEWORK" = "quarkus" ]; then
  FRAMEWORK_VERSION=$(grep -oE '<quarkus\.platform\.version>[0-9][^<]*' pom.xml 2>/dev/null | head -1 | sed 's|<quarkus\.platform\.version>||')
fi
FRAMEWORK_MAJOR=$(echo "$FRAMEWORK_VERSION" | cut -d. -f1)   # ej "3" o "4"
# Para Spring Boot: major 4 ⇒ Java 21, Jakarta EE 11, JUnit 5 only, RestClient. Ver spring-engineer.

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
    "frameworkVersion": FRAMEWORK_VERSION,   # ej "3.4.1" o "4.1.1-SNAPSHOT"
    "frameworkMajor": FRAMEWORK_MAJOR,        # ej "3" o "4" — lo usa spring-engineer
    "projectStructure": PROJECT_STRUCTURE,
    "detectedBasePackage": BASE_PACKAGE,
    "hexDomainDir": HEX_DOMAIN_DIR or "domain",
    "hexPortsDir": HEX_PORTS_DIR or "ports",
    "hexAdaptersDir": HEX_ADAPTERS_DIR or "adapters",
    # Panel de control (ver "Control de flujo" en el agente). Aquí ya pasó el
    # gate (config+preflight); la conexión MCP se confirma en Etapa 1.0.
    "control": {
        "config": True, "preflight": True, "jiraStarted": False,
        "jiraConnected": False, "stage": "spec"
    }
}
Path(f".github/specs/.metadata/{HU_KEY}.json").write_text(json.dumps(meta, indent=2))
```

Mostrar al usuario:
```
╔══════════════════════════════════════════════════════════════╗
║  DETECCIÓN DE PROYECTO                                        ║
║  Framework:    [spring-boot | quarkus | unknown] [versión]   ║
║  Estructura:   [new | hexagonal | traditional | mixed]        ║
║  Base Package: [valor detectado]                             ║
╚══════════════════════════════════════════════════════════════╝
```
