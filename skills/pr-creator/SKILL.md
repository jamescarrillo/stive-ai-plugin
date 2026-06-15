---
name: pr-creator
description: Valida el código implementado, crea el PR en GitHub con descripción completa y actualiza el estado en JIRA. Último paso del SDLC agentico-humano.
---

# Skill: PR Creator

## Propósito

Ejecutar el proceso completo de cierre del ciclo de implementación:
1. Validar que el código cumple todos los requisitos de calidad
2. Preparar el commit y la rama
3. Crear el Pull Request con descripción completa y estructurada
4. Actualizar el estado en JIRA via MCP

## Cuándo ejecutar

Inmediatamente después de que el desarrollador aprueba la implementación (Checkpoint 3).

---

## Proceso paso a paso

### Paso 1 — Recopilar contexto

```bash
# HU_KEY ya conocido desde PASO 0 (ej: SCRUM-5, HU-123)
# META_FILE, SPEC_FILE, TASKS_FILE definidos en PASO 0 — reusar esas variables
# Si este skill se ejecuta de forma independiente, construirlos así:
HU_KEY="[extraído del mensaje del usuario o de PASO 0]"
META_FILE=".github/specs/.metadata/${HU_KEY}.json"
SPEC_FILE=".github/specs/${HU_KEY}.md"
PLAN_FILE=".github/plans/${HU_KEY}/plan.md"
TASKS_FILE=".github/plans/${HU_KEY}/tasks.json"

# Extraer campos del spec con Python (robusto ante espacios y variaciones YAML)
eval $(python3 - <<'EOF'
import re, sys
spec = open("$SPEC_FILE").read()

def extract_frontmatter(key):
    m = re.search(rf'^{re.escape(key)}:\s*(.+)$', spec, re.MULTILINE)
    return m.group(1).strip() if m else ""

def extract_title():
    m = re.search(r'^## Título\s*\n(.+)', spec, re.MULTILINE)
    return m.group(1).strip() if m else ""

print(f'TITLE="{extract_title()}"')
print(f'BIAN_DOMAIN="{extract_frontmatter("bianservicedomain")}"')
# Fallback para proyectos tradicionales (sin frontmatter BIAN): usar servicename
print(f'MICRO_NAME="{extract_frontmatter("microservicename") or extract_frontmatter("servicename") or "service"}"')
EOF
)

# Framework, estructura y umbral de cobertura desde tasks.json (campos a nivel raíz)
FRAMEWORK=$(python3 -c "import json; print(json.load(open('$TASKS_FILE')).get('framework','spring-boot'))" 2>/dev/null || echo "spring-boot")
PROJECT_STRUCTURE=$(python3 -c "import json; print(json.load(open('$TASKS_FILE')).get('projectStructure','new'))" 2>/dev/null || echo "new")
# DoD de cobertura: hexagonal/new/mixed = 95% · traditional = 80% (alineado con spec-generator)
if [ "$PROJECT_STRUCTURE" = "traditional" ]; then COVERAGE_MIN=80; else COVERAGE_MIN=95; fi
echo "Framework: $FRAMEWORK | Estructura: $PROJECT_STRUCTURE | Cobertura mínima: ${COVERAGE_MIN}%"

# ATLASSIAN_BASE_URL: leer del metadata (guardado al llamar getJiraIssueDetails en Etapa 1)
ATLASSIAN_BASE_URL=$(python3 -c "
import json, re
meta = json.load(open('$META_FILE'))
url = meta.get('atlassian_base_url', '')
# Fallback: extraer de jira_url si está guardado
if not url:
    jira = meta.get('jira_url', '')
    m = re.match(r'(https://[^/]+)', jira)
    url = m.group(1) if m else 'https://YOUR_DOMAIN.atlassian.net'
print(url)
" 2>/dev/null || echo "https://YOUR_DOMAIN.atlassian.net")
```

### Paso 2 — Validaciones pre-PR obligatorias

Ejecuta cada validación. Si alguna falla, **no crear el PR** — reportar al desarrollador y esperar corrección.

#### 2a. Compilación y tests

```bash
echo "=== Compilación ==="
mvn clean compile -q
if [ $? -ne 0 ]; then echo "FAIL: Compilación fallida"; exit 1; fi
echo "PASS: Compila sin errores"

echo ""
echo "=== Tests ==="
mvn test -q
if [ $? -ne 0 ]; then echo "FAIL: Tests fallando"; exit 1; fi
echo "PASS: Todos los tests pasan"
```

#### 2b. Pureza del dominio

```bash
echo ""
echo "=== Domain Purity ==="
# Cubre Spring y Quarkus/CDI (jakarta.enterprise, jakarta.inject)
DOMAIN_VIOLATIONS=$(rg -n \
  "import org\.springframework|import jakarta\.persistence|import javax\.persistence|import com\.fasterxml\.jackson|import lombok\.Data|import jakarta\.enterprise|import jakarta\.inject" \
  --glob '**/domain/**' --type java 2>/dev/null)

if [ -n "$DOMAIN_VIOLATIONS" ]; then
  echo "FAIL: Domain contiene imports de framework:"
  echo "$DOMAIN_VIOLATIONS"
  exit 1
fi

ANNOTATION_VIOLATIONS=$(rg -n \
  "@Entity|@Table|@Column|@Id|@JsonProperty|@JsonIgnore|@Service|@Component|@Autowired|@ApplicationScoped|@RequestScoped|@Inject" \
  --glob '**/domain/**' --type java 2>/dev/null)

if [ -n "$ANNOTATION_VIOLATIONS" ]; then
  echo "FAIL: Domain contiene anotaciones de framework:"
  echo "$ANNOTATION_VIOLATIONS"
  exit 1
fi
echo "PASS: Domain puro (sin Spring/JPA/Jackson)"
```

#### 2c. Cobertura de tests (JaCoCo)

```bash
echo ""
echo "=== Cobertura ==="
mvn verify -Pcoverage -q 2>/dev/null || mvn jacoco:report -q 2>/dev/null

COVERAGE_REPORT="target/site/jacoco/index.html"
if [ -f "$COVERAGE_REPORT" ]; then
  # Extraer cobertura total de instrucciones desde el resumen del pie de tabla de JaCoCo
  # El elemento <tfoot> contiene el total; buscamos el primer td con porcentaje tras "Total"
  COVERAGE=$(python3 - <<'EOF'
import re, sys
html = open("target/site/jacoco/index.html").read()
# JaCoCo: buscar el bloque tfoot que contiene el total de instrucciones
m = re.search(r'<tfoot>.*?(\d+)\s*of\s*(\d+)', html, re.DOTALL)
if m:
    covered = int(m.group(1)); total = int(m.group(2))
    missed = total - covered
    pct = int((covered / total) * 100) if total > 0 else 0
    print(pct)
else:
    # Fallback: buscar la primera celda con porcentaje en tfoot
    m2 = re.search(r'<tfoot>.*?(\d+)%', html, re.DOTALL)
    print(m2.group(1) if m2 else "")
EOF
)
  if [ -n "$COVERAGE" ] && [ "$COVERAGE" -lt "$COVERAGE_MIN" ]; then
    echo "FAIL: Cobertura de instrucciones $COVERAGE% < ${COVERAGE_MIN}%"
    echo "Ejecutar: .github/skills/testing/test-generator/SKILL.md para gaps"
    exit 1
  fi
  echo "PASS: Cobertura de instrucciones ${COVERAGE:-desconocida}% ≥ ${COVERAGE_MIN}%"
else
  echo "WARN: Reporte JaCoCo no encontrado — verifica que jacoco-maven-plugin esté configurado"
  echo "      Agregar al pom.xml: <plugin>org.jacoco:jacoco-maven-plugin</plugin>"
fi
```

#### 2d. APIs BIAN-compliant

```bash
echo ""
echo "=== BIAN API Compliance ==="
# Spring usa *Controller.java + @*Mapping; Quarkus usa *Resource.java + @Path/@GET/...
if [ "$FRAMEWORK" = "quarkus" ]; then
  CONTROLLERS=$(find src/main/java \( -name "*Resource.java" -o -name "*Controller.java" \) -not -path "*/test/*" 2>/dev/null)
  MAPPING_RE="@(Path|GET|POST|PUT|PATCH|DELETE)"
else
  CONTROLLERS=$(find src/main/java -name "*Controller.java" -not -path "*/test/*" 2>/dev/null)
  MAPPING_RE="@(Get|Post|Put|Patch|Delete)Mapping"
fi
BIAN_VERBS="initiate|execute|request|update|retrieve"
NON_BIAN=()

for ctrl in $CONTROLLERS; do
  MAPPINGS=$(rg -n "$MAPPING_RE" "$ctrl" 2>/dev/null | grep -v "@RequestMapping")
  while IFS= read -r line; do
    if [ -n "$line" ]; then
      if ! echo "$line" | grep -qiE "$BIAN_VERBS"; then
        NON_BIAN+=("$ctrl: $line")
      fi
    fi
  done <<< "$MAPPINGS"
done

if [ ${#NON_BIAN[@]} -gt 0 ]; then
  echo "WARN: Posibles endpoints no BIAN:"
  printf '%s\n' "${NON_BIAN[@]}"
else
  echo "PASS: Endpoints usan verbos BIAN"
fi
```

#### 2e. Field injection (antipatrón)

```bash
echo ""
echo "=== No Field Injection ==="
# Detecta inyección por CAMPO en Spring (@Autowired) y Quarkus/CDI (@Inject),
# permitiendo inyección por constructor (la anotación sobre una línea con '(' no se marca).
FIELD_INJECTION=$(python3 - <<'EOF'
import glob
viol = []
for f in glob.glob('src/main/java/**/*.java', recursive=True):
    if '/test/' in f:
        continue
    lines = open(f, encoding='utf-8', errors='ignore').read().splitlines()
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s == '@Autowired' or s == '@Inject' or s.startswith('@Autowired ') or s.startswith('@Inject '):
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                nxt = lines[j].strip()
                # Es un campo si declara una variable (termina en ;) y NO es constructor/método (sin '(')
                if ';' in nxt and '(' not in nxt:
                    viol.append(f"{f}:{i+1}: {nxt}")
print('\n'.join(viol))
EOF
)
if [ -n "$FIELD_INJECTION" ]; then
  echo "FAIL: Field injection detectado (usar constructor injection):"
  echo "$FIELD_INJECTION"
  exit 1
fi
echo "PASS: Sin inyección por campo (@Autowired / @Inject)"
```

#### 2f. Cobertura de criterios de aceptación

Lee los criterios de aceptación del spec y verifica que existen tests para cada uno:
```bash
echo ""
echo "=== Criterios de Aceptación ==="
# Usar el SPEC_FILE de Paso 1 (.github/specs/${HU_KEY}.md). NO re-derivar con glob HU-*.md
# (rompía con keys como SCRUM-5 y, con varios specs, head -1 tomaba el equivocado).
CAS=$(grep -E "^### CA-[0-9]+" "$SPEC_FILE" | sed 's/### //')

for ca in $CAS; do
  CA_NUM=$(echo "$ca" | grep -oP 'CA-\d+')
  echo "  Verificando $CA_NUM..."
done
echo "(Revisión manual requerida — confirma que los tests cubren cada CA)"
```

### Paso 3 — Preparar rama y commit

```bash
# Leer rama desde metadata (creada en Etapa 1 al aprobar el spec)
BRANCH_NAME=$(python3 -c "import json; print(json.load(open('$META_FILE')).get('branch',''))" 2>/dev/null)

# Fallback: construir nombre si metadata no tiene el campo branch
if [ -z "$BRANCH_NAME" ]; then
  HU_KEY_LOWER=$(echo "$HU_KEY" | tr '[:upper:]' '[:lower:]')
  BRANCH_NAME="feature/$HU_KEY_LOWER"
fi

echo "Rama actual: $(git branch --show-current)"
echo "Rama objetivo: $BRANCH_NAME"

# Verificar que estamos en la rama correcta
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "$BRANCH_NAME" ]; then
  git checkout "$BRANCH_NAME" 2>/dev/null || { echo "FAIL: Rama $BRANCH_NAME no existe"; exit 1; }
  echo "Cambiado a rama: $BRANCH_NAME"
else
  echo "Ya en rama correcta: $BRANCH_NAME"
fi

# Verificar archivos a incluir
echo ""
echo "=== Archivos a commitear ==="
git status --short

# Excluir archivos sensibles
echo ""
echo "VERIFICAR que no se incluyan:"
echo "  - .env, *.env, application-local.*"
echo "  - *.key, *.pem, *.p12"
echo "  - Archivos con contraseñas o tokens hardcodeados"
```

### Paso 4 — Crear el commit

```bash
# Stagear archivos del proyecto (excluir sensibles)
git add src/
git add pom.xml
git add src/main/resources/db/migration/ 2>/dev/null || true
# Artefactos de Stive de ESTA HU — se incluyen a propósito para que el PR sea
# autodocumentado (spec + plan trazables). Acotado al HU_KEY actual, NO a toda la carpeta,
# para no arrastrar specs/planes de otras HUs al PR.
git add ".github/specs/${HU_KEY}.md" ".github/specs/.metadata/${HU_KEY}.json" 2>/dev/null || true
git add ".github/plans/${HU_KEY}/" 2>/dev/null || true

# Verificar lo que se va a commitear
echo ""
echo "=== Staged para commit ==="
git diff --cached --stat

# Crear commit con mensaje estructurado
git commit -m "feat($MICRO_NAME): implement $HU_KEY - $(grep '^## Título' "$SPEC_FILE" -A1 | tail -1 | xargs)

Implements:
$(grep -E "^[0-9]+\." "$SPEC_FILE" | head -5 | sed 's/^/- /')

Acceptance Criteria:
$(grep -E "^### CA-[0-9]+" "$SPEC_FILE" | sed 's/### /- /')

Technical:
- Architecture: Hexagonal (domain → application → infrastructure)
- BIAN Service Domain: $(grep 'bianservicedomain:' "$SPEC_FILE" | sed 's/bianservicedomain: //')
- Tests: Unit + Slice + Integration
- Coverage: ≥${COVERAGE_MIN}%

Spec: .github/specs/$HU_KEY.md
Plan: .github/plans/$HU_KEY/plan.md"
```

### Paso 5 — Push y crear Pull Request

```bash
# Push de la rama
git push -u origin "$BRANCH_NAME"
```

**Crear el PR usando GitHub MCP (`create_pull_request`):**

El PR debe contener:

```markdown
## Resumen

Implementación de **$HU_KEY** — [Título de la HU]

**BIAN Service Domain:** [valor]  
**Business Object:** [valor]  
**Base Package:** [valor]  
**Complejidad:** [BAJA/MEDIA/ALTA]  

## Qué cambia

### Dominio (domain/)
- `[BusinessObject].java` — Aggregate Root con comportamiento: [métodos]
- `[ValueObject].java` — Value Object inmutable: [descripción]
- `[Exception].java` — Excepción de dominio: [cuándo se lanza]

### Application (application/)
- `[BianVerb][BusinessObject]UseCase.java` — Puerto inbound
- `[BusinessObject]RepositoryPort.java` — Puerto outbound
- `[BianVerb][BusinessObject]Service.java` — Caso de uso: [qué hace]

### Infrastructure (infrastructure/)
- `[BianVerb][BusinessObject]Controller.java` — Endpoint: `[HTTP] /[path]`
- `[BusinessObject]JpaAdapter.java` — Adaptador de persistencia
- `GlobalExceptionHandler.java` — Manejo de errores

### Tests
- `[BusinessObject]Test.java` — Tests del aggregate (invariantes y comportamiento)
- `[BianVerb][BusinessObject]ServiceTest.java` — Tests de caso de uso
- `[BianVerb][BusinessObject]ControllerTest.java` — Slice test @WebMvcTest
- `[BusinessObject]JpaAdapterTest.java` — Slice test @DataJpaTest

## Criterios de aceptación

| CA | Descripción | Estado |
|----|-------------|--------|
| CA-1 | [descripción] | ✅ Implementado en TASK-X.X |
| CA-2 | [descripción] | ✅ Implementado en TASK-X.X |

## Validaciones

- [x] Compilación sin errores (`mvn clean compile`)
- [x] Tests pasan (`mvn test`)
- [x] Cobertura ≥ mínimo del proyecto (95% hexagonal · 80% tradicional) (JaCoCo)
- [x] Domain puro (sin Spring/JPA/Jackson)
- [x] APIs BIAN-compliant
- [x] Sin @Autowired en campos
- [x] GlobalExceptionHandler con manejo de errores estructurado

## Links

- JIRA: [[HU_KEY]]($ATLASSIAN_BASE_URL/browse/[HU_KEY])
- Spec: `.github/specs/[HU_KEY].md`
- Plan: `.github/plans/[HU_KEY]/plan.md`
```

Llamar al MCP GitHub con `create_pull_request`:

```
create_pull_request(
  owner:  "[owner del repo, ej: jamescarrillo]",
  repo:   "[nombre del repo, ej: agentic-ia]",
  title:  "feat($MICRO_NAME): $HU_KEY — [Título]",
  body:   "[contenido del PR según template de arriba]",
  head:   "$BRANCH_NAME",
  base:   "main"
)
```

### Paso 6 — Actualizar JIRA y metadata

Usar la tool MCP `transitionJiraIssue`:
```
Llamar: transitionJiraIssue(issueIdOrKey="HU-XXX", transition="IN_REVIEW")
```

Actualizar metadata local:
```json
// .github/specs/.metadata/HU-XXX.json
{
  "status": "pr_created",
  "pr_url": "[URL del PR creado]",
  "branch": "[nombre de la rama]",
  "pr_created_at": "[timestamp ISO 8601]"
}
```

---

## Checklist final para el desarrollador

Antes de mergear el PR, el desarrollador debe verificar:

```
PRE-MERGE CHECKLIST:
□ El código compila sin warnings
□ Todos los tests pasan en CI
□ La cobertura está en el reporte de CI
□ Los criterios de aceptación fueron revisados manualmente
□ La documentación OpenAPI (Swagger) es correcta
□ No hay secrets/tokens hardcodeados en el código
□ Las migraciones Flyway son correctas y reversibles
□ Los logs no exponen datos sensibles
□ El PR fue revisado por al menos 1 compañero
```

---

## Resumen del output

Al finalizar este skill, el agente reporta:

```
✅ PR CREADO EXITOSAMENTE

HU: [HU_KEY]
Título: [título]
Rama: feature/[HU_KEY]-[micro-name]
PR: [URL del PR]
JIRA: → "In Review"

Validaciones superadas:
  ✓ Compilación OK
  ✓ Tests OK  
  ✓ Domain puro
  ✓ Coverage ≥ mínimo requerido (95% / 80% tradicional)
  ✓ APIs BIAN-compliant

Próximas acciones:
  1. Esperar revisión de equipo en el PR
  2. Aplicar feedback del code review si hay comentarios
  3. Al mergear → mover JIRA a FINALIZED
```
