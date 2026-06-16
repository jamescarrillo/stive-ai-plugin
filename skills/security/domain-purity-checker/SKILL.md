---
name: domain-purity-checker
description: Analiza la pureza de la capa de dominio detectando fugas de framework, antipatrones DDD y violaciones de dependencias entre capas. Reporta hallazgos con archivos y líneas exactas.
---

# Skill: Domain Purity Checker

## Propósito

Verificar que la arquitectura hexagonal se mantiene correctamente: dominio puro sin frameworks, dependencias fluyendo hacia adentro, sin antipatrones DDD. Ejecutar antes de cada checkpoint de revisión humana.

## Cuándo ejecutar

- Antes del Checkpoint 3 (revisión de implementación)
- Como parte del `pr-creator` skill (Etapa 4)
- Cuando el desarrollador solicite revisión arquitectónica

---

## Análisis 1 — Pureza del Dominio (CRÍTICO)

```bash
echo "=============================================="
echo "  DOMAIN PURITY CHECKER"
echo "=============================================="

DOMAIN_DIR=$(find src/main/java -type d -name "domain" -not -path "*/test/*" 2>/dev/null | head -1)
if [ -z "$DOMAIN_DIR" ]; then echo "ERROR: No se encontró domain/"; exit 1; fi

BASE_PKG=$(echo "$DOMAIN_DIR" | sed 's|src/main/java/||; s|/domain.*||' | tr '/' '.')
echo "Package: $BASE_PKG | Domain: $DOMAIN_DIR"
FAIL_COUNT=0

echo ""
echo "--- 1.1 Imports prohibidos en domain/ ---"

SPRING=$(rg -n --with-filename "import org\.springframework" "$DOMAIN_DIR" --type java 2>/dev/null)
[ -n "$SPRING" ] && echo "FAIL: Spring imports:" && echo "$SPRING" && FAIL_COUNT=$((FAIL_COUNT+1)) || echo "PASS: Sin imports Spring"

JPA=$(rg -n --with-filename "import (jakarta|javax)\.persistence" "$DOMAIN_DIR" --type java 2>/dev/null)
[ -n "$JPA" ] && echo "FAIL: JPA imports:" && echo "$JPA" && FAIL_COUNT=$((FAIL_COUNT+1)) || echo "PASS: Sin imports JPA"

JACKSON=$(rg -n --with-filename "import com\.fasterxml\.jackson" "$DOMAIN_DIR" --type java 2>/dev/null)
[ -n "$JACKSON" ] && echo "FAIL: Jackson imports:" && echo "$JACKSON" && FAIL_COUNT=$((FAIL_COUNT+1)) || echo "PASS: Sin imports Jackson"

CDI=$(rg -n --with-filename "import (io\.quarkus|jakarta\.enterprise|jakarta\.inject)" "$DOMAIN_DIR" --type java 2>/dev/null)
[ -n "$CDI" ] && echo "FAIL: CDI/Quarkus imports:" && echo "$CDI" && FAIL_COUNT=$((FAIL_COUNT+1)) || echo "PASS: Sin imports CDI"

echo ""
echo "--- 1.2 Anotaciones de framework en domain/ ---"

JPA_ANN=$(rg -n --with-filename "@(Entity|Table|Column|Id|GeneratedValue|OneToMany|ManyToOne|JoinColumn)" "$DOMAIN_DIR" --type java 2>/dev/null)
[ -n "$JPA_ANN" ] && echo "FAIL: Anotaciones JPA:" && echo "$JPA_ANN" && FAIL_COUNT=$((FAIL_COUNT+1)) || echo "PASS: Sin @Entity/@Table/@Column"

SPRING_ANN=$(rg -n --with-filename "@(Service|Component|Repository|Controller|Autowired|Value|Configuration)" "$DOMAIN_DIR" --type java 2>/dev/null)
[ -n "$SPRING_ANN" ] && echo "FAIL: Anotaciones Spring:" && echo "$SPRING_ANN" && FAIL_COUNT=$((FAIL_COUNT+1)) || echo "PASS: Sin @Service/@Component"

LOMBOK_DATA=$(rg -n --with-filename "@Data" "$DOMAIN_DIR" --type java 2>/dev/null)
[ -n "$LOMBOK_DATA" ] && echo "FAIL: @Data Lombok en domain/ (genera setters, viola inmutabilidad):" && echo "$LOMBOK_DATA" && FAIL_COUNT=$((FAIL_COUNT+1)) || echo "PASS: Sin @Data"
```

## Análisis 2 — Dirección de Dependencias

```bash
echo ""
echo "--- 2. Dirección de Dependencias ---"

APP_DIR=$(find src/main/java -type d -name "application" -not -path "*/test/*" 2>/dev/null | head -1)
INFRA_DIR=$(find src/main/java -type d -name "infrastructure" -not -path "*/test/*" 2>/dev/null | head -1)

for layer in domain application infrastructure; do
  LD=$(find src/main/java -type d -name "$layer" -not -path "*/test/*" 2>/dev/null | head -1)
  [ -z "$LD" ] && echo "FAIL: Falta capa $layer/" && FAIL_COUNT=$((FAIL_COUNT+1)) || echo "PASS: Capa $layer/ existe"
done

if [ -n "$APP_DIR" ] && [ -n "$INFRA_DIR" ]; then
  INFRA_PKG=$(echo "$INFRA_DIR" | sed 's|src/main/java/||' | tr '/' '.')
  APP_IMPORTS_INFRA=$(rg -n --with-filename "import $INFRA_PKG" "$APP_DIR" --type java 2>/dev/null)
  [ -n "$APP_IMPORTS_INFRA" ] && echo "FAIL: Application importa Infrastructure — viola hexagonal:" && echo "$APP_IMPORTS_INFRA" && FAIL_COUNT=$((FAIL_COUNT+1)) || echo "PASS: Application no importa Infrastructure"
fi

PORTS_DIR=$(find src/main/java -type d -name "ports" -not -path "*/test/*" 2>/dev/null | head -1)
if [ -n "$PORTS_DIR" ]; then
  JPA_IN_PORTS=$(rg -n --with-filename "extends (JpaRepository|CrudRepository|MongoRepository)" "$PORTS_DIR" --type java 2>/dev/null)
  [ -n "$JPA_IN_PORTS" ] && echo "FAIL: Outbound port hereda JpaRepository — viola hexagonal:" && echo "$JPA_IN_PORTS" && FAIL_COUNT=$((FAIL_COUNT+1)) || echo "PASS: Outbound ports son interfaces puras"
fi
```

## Análisis 3 — Antipatrones de Inyección y DDD

```bash
echo ""
echo "--- 3. Antipatrones ---"

FIELD_INJ=$(rg -n --with-filename "@Autowired" src/main/java --type java 2>/dev/null)
[ -n "$FIELD_INJ" ] && echo "FAIL: @Autowired en campo (usar constructor injection):" && echo "$FIELD_INJ" && FAIL_COUNT=$((FAIL_COUNT+1)) || echo "PASS: Sin @Autowired en campos"

# Quarkus/CDI: @Inject por campo está prohibido en domain/ y application/ (deben usar constructor).
# En infraestructura JAX-RS el @Inject por campo es idiomático, por eso aquí solo se revisan domain/ y application/.
CDI_FIELD_INJ=""
[ -n "$DOMAIN_DIR" ] && CDI_FIELD_INJ="$CDI_FIELD_INJ$(rg -n --with-filename '@Inject' "$DOMAIN_DIR" --type java 2>/dev/null)"
[ -n "$APP_DIR" ] && CDI_FIELD_INJ="$CDI_FIELD_INJ$(rg -n --with-filename '@Inject' "$APP_DIR" --type java 2>/dev/null)"
[ -n "$CDI_FIELD_INJ" ] && echo "FAIL: @Inject en domain/ o application/ (usar constructor injection):" && echo "$CDI_FIELD_INJ" && FAIL_COUNT=$((FAIL_COUNT+1)) || echo "PASS: Sin @Inject en domain/application"

JPA_IN_APP=$(rg -n --with-filename "JpaRepository|CrudRepository" src/main/java --type java 2>/dev/null | grep "/application/")
[ -n "$JPA_IN_APP" ] && echo "FAIL: JPA en application/ (pertenece a infrastructure/):" && echo "$JPA_IN_APP" && FAIL_COUNT=$((FAIL_COUNT+1)) || echo "PASS: JPA solo en infrastructure/"

CTRL_LOGIC=$(rg -n --with-filename "if.*throw|switch.*case" src/main/java --glob "*Controller.java" --type java 2>/dev/null)
[ -n "$CTRL_LOGIC" ] && echo "WARN: Posible lógica de negocio en Controller (verificar):" && echo "$CTRL_LOGIC"
```

## Análisis 4 — BIAN Naming

```bash
echo ""
echo "--- 4. BIAN Naming ---"

# Spring: *Controller.java + @*Mapping("...") · Quarkus: *Resource.java + @Path("...")
# (en Quarkus el verbo BIAN va en @Path del método, no en @GET/@POST)
CONTROLLERS=$(find src/main/java \( -name "*Controller.java" -o -name "*Resource.java" \) -not -path "*/test/*" 2>/dev/null)
BIAN_OK=true
for ctrl in $CONTROLLERS; do
  MAPPINGS=$(rg -n "(PostMapping|GetMapping|PatchMapping|PutMapping)|@Path\(" "$ctrl" 2>/dev/null)
  while IFS= read -r line; do
    [ -n "$line" ] && ! echo "$line" | grep -qiE "initiate|execute|request|update|retrieve" && echo "WARN: $(basename $ctrl) — mapping posiblemente no BIAN: $line" && BIAN_OK=false
  done <<< "$MAPPINGS"
done
$BIAN_OK && echo "PASS: Endpoints usan verbos BIAN"
```

## Reporte Final

```bash
echo ""
echo "=============================================="
echo "  RESULTADO"
echo "=============================================="
if [ "$FAIL_COUNT" -eq 0 ]; then
  echo "✅ APROBADO — Arquitectura hexagonal correcta"
  echo "   Domain puro | Dependencias correctas | Sin antipatrones"
else
  echo "❌ FALLIDO — $FAIL_COUNT violación(es) crítica(s)"
  echo ""
  echo "Correcciones requeridas:"
  echo "  - Eliminar imports de framework en domain/"
  echo "  - Usar constructor injection (eliminar @Autowired en campos)"
  echo "  - Mover JPA a infrastructure/, no en application/"
  echo "  - Outbound ports deben ser interfaces puras, sin extends JpaRepository"
  echo ""
  echo "Referencia: docs/common-errors.md"
fi
```

## Correcciones rápidas

### Import prohibido en domain/:
Mover la clase a la capa correcta:
- Necesita `@Entity` → `infrastructure/adapters/outbound/database/`
- Necesita `@JsonProperty` → `infrastructure/adapters/inbound/rest/dto/`
- Necesita `@Service` → `application/service/` o `infrastructure/`

### @Autowired en campo:
```java
// MAL
@Autowired private AccountRepositoryPort repo;

// BIEN
private final AccountRepositoryPort repo;
public MyService(AccountRepositoryPort repo) { this.repo = Objects.requireNonNull(repo); }
```

### Outbound port hereda JpaRepository:
```java
// MAL — tech leak en puerto
public interface AccountRepositoryPort extends JpaRepository<Account, String> {}

// BIEN — interfaz pura
public interface AccountRepositoryPort {
    Account save(Account account);
    Optional<Account> findByAccountNumber(AccountNumber number);
}
// La impl JpaRepository va en AccountJpaAdapter en infrastructure/
```

# Instrucciones para el Agente

Tu responsabilidad es garantizar que:
1. El núcleo del sistema (`domain/`) se mantenga 100% agnóstico a frameworks, bases de datos o protocolos web.
2. La capa `application/` no tenga anotaciones Spring.
3. Los nombres de paquetes sigan la convención BIAN (`com.jotace.<serviceDomain>`).

DEBES ejecutar este skill de forma autónoma cada vez que crees o modifiques archivos en `domain/` o `application/`.

## 1. Escanear imports prohibidos en dominio

```bash
rg -n "import org\.springframework|import jakarta\.persistence|import javax\.persistence|import com\.fasterxml\.jackson|import lombok\.Data" --glob '**/domain/**' --type java 2>/dev/null || grep -rnE "import org\.springframework|import jakarta\.persistence|import javax\.persistence|import com\.fasterxml\.jackson|import lombok\.Data" --include='*.java' -r .
```

## 2. Escanear anotaciones Spring en capa application

```bash
rg -n "@Service|@Component|@Autowired|@Repository|@RestController" --glob '**/application/**' --type java 2>/dev/null || grep -rnE "@Service|@Component|@Autowired|@Repository|@RestController" --include='*.java' -r . | grep '/application/'
```

## 3. Validar nomenclatura BIAN de paquetes

### 3.1. Detectar el package base real del proyecto

En lugar de usar un patrón hardcoded, detecta dinámicamente el package base del proyecto:

```bash
# Detectar el package base REAL desde la estructura del proyecto
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

echo "Package base detectado: $REAL_BASE_PACKAGE"

if [ -z "$REAL_BASE_PACKAGE" ]; then
    echo "⚠️ No se detectó proyecto Java. Saltando validación BIAN."
    exit 0
fi
```

### 3.2. Validar que todos los packages hijos usen el mismo prefijo

Verifica que todos los archivos Java compartan el mismo prefijo de package:

```bash
# Extraer todos los packages únicos
grep -rh "^package " src/main/java/ --include="*.java" \
    | sed 's/package //; s/;//' \
    | sort -u \
    | while read pkg; do
        if [[ "$pkg" != "$REAL_BASE_PACKAGE"* ]]; then
            echo "⚠️ Package fuera de la jerarquía: $pkg (esperado: $REAL_BASE_PACKAGE.*)"
        fi
    done
```

### 3.3. Validar nombres de capas

Verifica que los sub-paquetes usen los nombres de capa estándar (domain, application, infrastructure):

```bash
# Buscar packages que no sean domain/application/infrastructure bajo el base
grep -rh "^package " src/main/java/ --include="*.java" \
    | sed 's/package //; s/;//' \
    | grep "^$REAL_BASE_PACKAGE\." \
    | grep -v "^$REAL_BASE_PACKAGE\.\(domain\|application\|infrastructure\)" \
    | head -5
```

Si hay resultados, revisa si son válidos o si usan nombres incorrectos (ej. `com.jotace.accountmanagement.api` en lugar de `com.jotace.accountmanagement.infrastructure.adapters.inbound.rest`).

## Evaluación y Corrección

Para cada escaneo:

- **Salida vacía** → Todo correcto.
- **Salida con resultados** → Alerta de antipatrón:
  1. Abre los archivos infractores.
  2. Elimina imports prohibidos o muévelos a la capa correcta.
  3. Si un paquete no sigue `com.jotace.<serviceDomain>`, repáralo.
  4. Vuelve a ejecutar hasta salir limpio.
