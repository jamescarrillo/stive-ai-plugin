---
name: code-reviewer
description: Realiza una revisión completa del código existente antes de hacer cualquier modificación, identificando antipatrones, fugas de arquitectura y puntos de impacto.
---

# Instrucciones para el Agente

Este skill DEBE ejecutarse al inicio de cualquier tarea de modificación de código, antes de escribir una sola línea nueva. El objetivo es entender el estado actual del código y detectar problemas existentes.

## Workflow de revisión

### 1. Identificar el alcance del cambio
- Usa la variable `$SPEC_FILE` del contexto si se proporcionó (el usuario especificó un archivo de spec). Si no, toma el primer spec de `.github/specs/`.
- Lee los criterios de aceptación del spec para entender el alcance.
- Identifica qué archivos/capas se verán afectados (domain, application, infrastructure).

### 2. Revisar la capa de dominio (`domain/`)
```bash
# Buscar imports prohibidos en dominio
rg -n "import org\.springframework|import jakarta\.persistence|import javax\.persistence|import com\.fasterxml\.jackson" --glob '**/domain/**' --type java
# Buscar anotaciones de framework en dominio
rg -n "@Entity|@Table|@Column|@Id|@JsonProperty|@JsonIgnore|@Service|@Component|@Autowired" --glob '**/domain/**' --type java
# Buscar lombok.Data (antipatrón en dominio)
rg -n "@Data" --glob '**/domain/**' --type java
```

### 3. Revisar la capa de aplicación (`application/`)
```bash
# Buscar anotaciones Spring en capa de aplicación
rg -n "@Service|@Component|@Autowired|@Repository|@RestController|@GetMapping|@PostMapping" --glob '**/application/**' --type java
# Verificar que los outbound ports sean interfaces sin tecnología
rg -n "extends (JpaRepository|CrudRepository|MongoRepository)" --glob '**/ports/outbound/**' --type java
```

### 4. Revisar inyección de dependencias
```bash
# Buscar field injection (@Autowired en campos)
rg -n "@Autowired" --type java
# Buscar @MockBean (prohibido en tests unitarios de dominio/aplicación)
rg -n "@MockBean" --type java
```

### 5. Revisar manejo de errores
- ¿Existe un `@RestControllerAdvice`? Si no, es una falta.
- ¿Las excepciones de dominio heredan de `RuntimeException`?
- ¿Los errores se devuelven con estructura JSON estandarizada?

### 6. Revisar nomenclatura BIAN

Detecta dinámicamente el package base del proyecto y verifica consistencia:

```bash
# 6a. Detectar el package base real del proyecto
DOMAIN_DIR=$(find src/main/java -type d -name "domain" -not -path "*/test/*" 2>/dev/null | head -1)
if [ -n "$DOMAIN_DIR" ]; then
    REAL_BASE_PACKAGE=$(echo "$DOMAIN_DIR" | sed 's|src/main/java/||; s|/domain.*||' | tr '/' '.')
else
    REAL_BASE_PACKAGE=$(grep -rh "^package " src/main/java/ --include="*.java" 2>/dev/null \
        | sed 's/package //; s/;//' \
        | sort -u \
        | awk -F'.' '{
            if (NR == 1) { split($0, common, "."); next }
            for (i = 1; i <= length(common); i++)
                if (common[i] != $i) { delete common[i]; break }
          }
          END { for (i in common) printf "%s.", common[i]; print "" }' \
        | sed 's/\.$//')
fi

if [ -n "$REAL_BASE_PACKAGE" ]; then
    echo "Package base detectado: $REAL_BASE_PACKAGE"

    # 6b. Verificar que el spec coincida (si existe)
    # Usa $SPEC_FILE del contexto si se proporcionó, o toma el primer spec
    SPEC_FILE="${SPEC_FILE:-$(ls .github/specs/*.md 2>/dev/null | head -1)}"
    if [ -n "$SPEC_FILE" ] && [ -f "$SPEC_FILE" ]; then
        SPEC_PACKAGE=$(sed -n 's/^basepackage: //p' "$SPEC_FILE")
        if [ -n "$SPEC_PACKAGE" ] && [ "$REAL_BASE_PACKAGE" != "$SPEC_PACKAGE" ]; then
            echo "⚠️  MISMATCH: spec '$SPEC_FILE' dice '$SPEC_PACKAGE' pero el proyecto usa '$REAL_BASE_PACKAGE'"
        fi
    fi

    # 6c. Verificar que la estructura de capas sea correcta
    for layer in domain application infrastructure; do
        if [ ! -d "src/main/java/${REAL_BASE_PACKAGE//.//}/$layer" ]; then
            echo "⚠️  Falta capa $layer/ en el package $REAL_BASE_PACKAGE"
        fi
    done
fi
```

### 7. Reporte de hallazgos
Presenta un resumen con:
- ✅ **Pasos correctos** (lo que está bien y no se debe modificar)
- ⚠️ **Antipatrones detectados** (referencia al ID del antipatrón en `common-errors.md`)
- 🔧 **Archivos a modificar** (lista con ruta y motivo del cambio)
- 📦 **Dependencias externas identificadas** (WebClient, Redis, Kafka, etc.)

No modifiques nada aún. Solo reporta. El desarrollador (o el workflow) tomará acción después.
