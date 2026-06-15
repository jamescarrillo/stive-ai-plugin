---
name: tech-auditor
description: Auditoría técnica maestro para microservicios Java. Analiza arquitectura (hexagonal o tradicional), calidad de código, tests, seguridad, performance, dependencias, BIAN compliance y documentación. Output: reporte priorizado por severidad. Solo identifica y reporta — no crea issues.
---

# Skill: Tech Auditor — Master

## Propósito

Proporcionar al Tech Lead o desarrollador senior una radiografía completa y objetiva de un microservicio Java, independientemente de si tiene arquitectura hexagonal o tradicional. El resultado es un reporte priorizado por severidad con hallazgos accionables.

**Este skill NO modifica ningún archivo del proyecto y NO crea issues en JIRA — solo analiza y reporta.** El reporte es el entregable final.

## Comandos que activan este skill

```
"Stive, analiza el microservicio"
"Stive, analiza el proyecto"
"Stive, identifica deuda técnica"
"Stive, identifica oportunidades de mejora"
"Stive, qué tan saludable está este microservicio"
"Stive, audita el proyecto"
```

---

## Proceso de auditoría

### Paso 0 — Reconocimiento y detección de estructura

Ejecutar antes de cualquier otro paso. Determina qué tipo de auditoría aplicar.

```bash
echo "======================================================"
echo "  RECONOCIMIENTO DEL PROYECTO"
echo "======================================================"

# ── Framework ──────────────────────────────────────────────
if grep -q "spring-boot-starter-parent\|spring-boot-dependencies" pom.xml 2>/dev/null; then
  FRAMEWORK="spring-boot"
  FRAMEWORK_VERSION=$(grep -A2 "spring-boot-starter-parent" pom.xml | grep "<version>" | \
                      sed 's/.*<version>//;s/<\/version>.*//' | tr -d ' ')
elif grep -q "quarkus-bom\|io.quarkus" pom.xml 2>/dev/null; then
  FRAMEWORK="quarkus"
  FRAMEWORK_VERSION=$(grep -A5 "quarkus-bom" pom.xml | grep "<version>" | head -1 | \
                      sed 's/.*<version>//;s/<\/version>.*//' | tr -d ' ')
else
  FRAMEWORK="unknown"
  FRAMEWORK_VERSION="desconocida"
fi

# ── Metadatos del artefacto ────────────────────────────────
ARTIFACT_ID=$(grep -m1 "<artifactId>" pom.xml | sed 's/.*<artifactId>//;s/<\/artifactId>.*//' | tr -d ' ')
JAVA_VERSION=$(grep -m1 "<java.version>\|<maven.compiler.source>" pom.xml | \
               sed 's/.*<[^>]*>//;s/<\/[^>]*>.*//' | tr -d ' ')
GROUP_ID=$(grep -m1 "<groupId>" pom.xml | sed 's/.*<groupId>//;s/<\/groupId>.*//' | tr -d ' ')

# ── Inventario de clases ───────────────────────────────────
TOTAL_JAVA=$(find src/main/java -name "*.java" 2>/dev/null | wc -l | tr -d ' ')
TOTAL_TEST=$(find src/test/java  -name "*.java" 2>/dev/null | wc -l | tr -d ' ')
TOTAL_LINES=$(find src/main/java -name "*.java" 2>/dev/null | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}')

# ── Detectar estructura del proyecto ──────────────────────
HAS_HEX_DOMAIN=$(find src/main/java -type d \( -name "domain" -o -name "core" \) 2>/dev/null | head -1)
HAS_HEX_PORTS=$(find src/main/java -type d \( \
  -name "ports" -o -name "port" -o -name "driven" -o \
  -name "driving" -o -name "primary" -o -name "secondary" \) 2>/dev/null | head -1)
HAS_HEX_ADAPTERS=$(find src/main/java -type d \( -name "adapters" -o -name "adapter" \) 2>/dev/null | head -1)
HAS_USE_CASE=$(find src/main/java \( -name "*UseCase.java" -o -name "*Port.java" \) 2>/dev/null | head -1)
HAS_CONTROLLER=$(find src/main/java -name "*Controller.java" -o -name "*Resource.java" 2>/dev/null | head -1)
HAS_SERVICE=$(find src/main/java -name "*Service.java" -o -name "*ServiceImpl.java" 2>/dev/null | head -1)
HAS_REPOSITORY=$(find src/main/java -name "*Repository.java" 2>/dev/null | head -1)

if [ -n "$HAS_HEX_DOMAIN" ] && { [ -n "$HAS_HEX_PORTS" ] || [ -n "$HAS_USE_CASE" ] || [ -n "$HAS_HEX_ADAPTERS" ]; }; then
  PROJECT_STRUCTURE="hexagonal"
elif [ -n "$HAS_CONTROLLER" ] && [ -n "$HAS_SERVICE" ] && [ -n "$HAS_REPOSITORY" ]; then
  PROJECT_STRUCTURE="traditional"
elif [ -n "$HAS_CONTROLLER" ] || [ -n "$HAS_SERVICE" ]; then
  PROJECT_STRUCTURE="mixed"
else
  PROJECT_STRUCTURE="unknown"
fi

echo "  Artefacto  : $ARTIFACT_ID  ($GROUP_ID)"
echo "  Framework  : $FRAMEWORK $FRAMEWORK_VERSION"
echo "  Java       : $JAVA_VERSION"
echo "  Estructura : $PROJECT_STRUCTURE"
echo "  Clases     : $TOTAL_JAVA producción / $TOTAL_TEST test / ~$TOTAL_LINES líneas totales"
echo ""
echo "  → Aplicando auditoría para estructura: $PROJECT_STRUCTURE"
```

---

### Paso 1 — Auditoría de arquitectura

Este paso bifurca completamente según `PROJECT_STRUCTURE`.

---

#### 1A — Si `PROJECT_STRUCTURE == "hexagonal"`

```bash
echo "======================================================"
echo "  [1] ARQUITECTURA HEXAGONAL"
echo "======================================================"

DOMAIN_DIR="$HAS_HEX_DOMAIN"
echo "  domain/   : $DOMAIN_DIR"
echo "  ports/    : ${HAS_HEX_PORTS:-no encontrado}"
echo "  adapters/ : ${HAS_HEX_ADAPTERS:-no encontrado}"

# ── 1.1 Pureza del dominio ─────────────────────────────────
echo ""
echo "  -- Pureza del dominio --"
SPRING_IN_DOMAIN=$(grep -rl "import org\.springframework" "$DOMAIN_DIR" 2>/dev/null)
JPA_IN_DOMAIN=$(grep -rl "import jakarta\.persistence\|import javax\.persistence" "$DOMAIN_DIR" 2>/dev/null)
JACKSON_IN_DOMAIN=$(grep -rl "import com\.fasterxml\.jackson" "$DOMAIN_DIR" 2>/dev/null)
CDI_IN_DOMAIN=$(grep -rl "import jakarta\.enterprise\|import jakarta\.inject" "$DOMAIN_DIR" 2>/dev/null)
LOMBOK_DATA_DOMAIN=$(grep -rl "@Data" "$DOMAIN_DIR" 2>/dev/null)

[ -n "$SPRING_IN_DOMAIN" ]  && echo "  ❌ CRÍTICO — imports Spring en domain/ — rompe el aislamiento: $(echo $SPRING_IN_DOMAIN | tr '\n' ',')"
[ -n "$JPA_IN_DOMAIN" ]     && echo "  ❌ CRÍTICO — imports JPA/jakarta.persistence en domain/: $(echo $JPA_IN_DOMAIN | tr '\n' ',')"
[ -n "$JACKSON_IN_DOMAIN" ] && echo "  🟠 ALTO — imports Jackson en domain/ (acoplamiento con serialización): $(echo $JACKSON_IN_DOMAIN | tr '\n' ',')"
[ -n "$CDI_IN_DOMAIN" ]     && echo "  🟠 ALTO — imports CDI/Inject en domain/ (acoplamiento con contenedor): $(echo $CDI_IN_DOMAIN | tr '\n' ',')"
[ -n "$LOMBOK_DATA_DOMAIN" ] && echo "  🟡 MEDIO — @Data en domain/ (usar @Getter + @Builder explícitos): $(echo $LOMBOK_DATA_DOMAIN | tr '\n' ',')"

if [ -z "$SPRING_IN_DOMAIN" ] && [ -z "$JPA_IN_DOMAIN" ] && [ -z "$JACKSON_IN_DOMAIN" ] && [ -z "$CDI_IN_DOMAIN" ]; then
  echo "  ✅ Dominio puro — sin imports de infraestructura"
fi

# ── 1.2 Separación de puertos y adaptadores ────────────────
echo ""
echo "  -- Ports & Adapters --"
[ -z "$HAS_HEX_PORTS" ]    && echo "  🟠 ALTO — no se detectaron ports/ — ¿están bajo otro nombre?"
[ -z "$HAS_HEX_ADAPTERS" ] && echo "  🟠 ALTO — no se detectaron adapters/ — ¿están bajo otro nombre?"

# UseCase interfaces
USECASES=$(find src/main/java -name "*UseCase.java" 2>/dev/null | wc -l | tr -d ' ')
PORTS=$(find src/main/java -name "*Port.java" 2>/dev/null | wc -l | tr -d ' ')
echo "  UseCases detectados: $USECASES"
echo "  Ports detectados   : $PORTS"
[ "$USECASES" -eq 0 ] && echo "  🟠 ALTO — no hay interfaces UseCase — los inbound ports no están definidos"
[ "$PORTS" -eq 0 ]    && echo "  🟠 ALTO — no hay interfaces Port — los outbound ports no están definidos"

# ── 1.3 Application Services ───────────────────────────────
echo ""
echo "  -- Application Services --"
if [ "$FRAMEWORK" = "spring-boot" ]; then
  # En Spring Boot hexagonal: deben ser POJO + @Bean en DomainConfig, NO @Service
  SERVICE_ANNO=$(grep -rn "@Service" src/main/java 2>/dev/null | grep -iv "test" | grep -iv "interface")
  DOMAIN_CONFIG=$(find src/main/java -name "DomainConfig.java" 2>/dev/null | head -1)
  [ -n "$SERVICE_ANNO" ] && echo "  🟡 MEDIO — @Service en Application Services (deben ser POJO registrados con @Bean en DomainConfig):"
  [ -n "$SERVICE_ANNO" ] && echo "$SERVICE_ANNO" | head -5
  [ -z "$DOMAIN_CONFIG" ] && [ -n "$HAS_HEX_DOMAIN" ] && echo "  🟡 MEDIO — DomainConfig.java no encontrado (registrar Application Services como @Bean aquí)"
  [ -n "$DOMAIN_CONFIG" ] && echo "  ✅ DomainConfig.java presente: $DOMAIN_CONFIG"
elif [ "$FRAMEWORK" = "quarkus" ]; then
  # En Quarkus hexagonal: deben ser @ApplicationScoped
  APP_SERVICES=$(find src/main/java -path "*/application*" -name "*Service*.java" 2>/dev/null)
  if [ -n "$APP_SERVICES" ]; then
    for f in $APP_SERVICES; do
      grep -q "@ApplicationScoped" "$f" || echo "  🟡 MEDIO — Application Service sin @ApplicationScoped (CDI lo requiere): $f"
    done
  fi
fi

# ── 1.4 Infraestructura invadiendo capas superiores ────────
echo ""
echo "  -- Dirección de dependencias --"
# ¿Application layer importa infraestructura?
APP_DIR=$(find src/main/java -type d -name "application" 2>/dev/null | head -1)
if [ -n "$APP_DIR" ]; then
  INFRA_IN_APP=$(grep -rn "import.*infrastructure\|import.*adapter\|import.*jpa\|import.*rest" "$APP_DIR" 2>/dev/null | grep -v test)
  [ -n "$INFRA_IN_APP" ] && echo "  ❌ CRÍTICO — capa application importa infraestructura (viola dirección de dependencias):" && echo "$INFRA_IN_APP" | head -5
  [ -z "$INFRA_IN_APP" ] && echo "  ✅ Application layer no importa infraestructura"
fi

# ── 1.5 Mappers: manual vs MapStruct ──────────────────────
MAPSTRUCT=$(grep -rn "import org\.mapstruct" src/main/java 2>/dev/null | head -1)
MANUAL_MAP=$(grep -rn "\.set[A-Z].*\.get[A-Z]" src/main/java 2>/dev/null | grep -v test | head -5)
[ -z "$MAPSTRUCT" ] && [ -n "$MANUAL_MAP" ] && echo "  🟡 MEDIO — mapeo manual detectado (usar MapStruct):" && echo "$MANUAL_MAP" | head -3
[ -n "$MAPSTRUCT" ] && echo "  ✅ MapStruct detectado"

# ── 1.6 @Autowired en campo (toda la app) ─────────────────
AUTOWIRED_FIELD=$(grep -rn "@Autowired" src/main/java 2>/dev/null | grep -v "test\|interface\|/\*")
[ -n "$AUTOWIRED_FIELD" ] && echo "  🟡 MEDIO — @Autowired en campo (usar inyección por constructor en todas las capas):" && echo "$AUTOWIRED_FIELD" | head -5
```

---

#### 1B — Si `PROJECT_STRUCTURE == "traditional"`

```bash
echo "======================================================"
echo "  [1] ARQUITECTURA TRADICIONAL (Layered)"
echo "======================================================"

# ── 1.1 Separación de capas ───────────────────────────────
echo "  -- Separación de capas --"

# ¿Controllers llaman directamente a repositories? (saltando service layer)
CTRL_TO_REPO=$(grep -rn "import.*[Rr]epository" src/main/java 2>/dev/null | grep -i "controller\|resource" | grep -v test)
[ -n "$CTRL_TO_REPO" ] && echo "  ❌ CRÍTICO — Controller accede directo a Repository (debe ir por Service):" && echo "$CTRL_TO_REPO" | head -5
[ -z "$CTRL_TO_REPO" ] && echo "  ✅ Controllers no acceden directamente a Repositories"

# ¿Services llaman directamente a otros services del mismo nivel? (posible acoplamiento)
SERVICE_TO_SERVICE=$(grep -rn "@Autowired\|private.*Service " src/main/java 2>/dev/null | grep -i "service" | grep -iv "test\|interface" | head -5)
[ -n "$SERVICE_TO_SERVICE" ] && echo "  🟡 MEDIO — Services acoplados entre sí (verificar si genera dependencias circulares):" && echo "$SERVICE_TO_SERVICE" | head -3

# ── 1.2 Lógica de negocio en capas incorrectas ────────────
echo ""
echo "  -- Lógica de negocio en capas incorrectas --"

# Lógica en Controllers (más de 3 ifs/fors en un controller)
for f in $(find src/main/java -name "*Controller.java" -o -name "*Resource.java" 2>/dev/null | grep -v test); do
  IF_COUNT=$(grep -c "if (\|if(\|switch (\|switch(" "$f" 2>/dev/null || echo 0)
  [ "$IF_COUNT" -gt 3 ] && echo "  🟠 ALTO — lógica de negocio en Controller ($IF_COUNT condiciones): $f"
done

# Lógica en Repositories (métodos con lógica más allá de queries)
for f in $(find src/main/java -name "*Repository*.java" 2>/dev/null | grep -v test); do
  IF_COUNT=$(grep -c "if (\|if(\|for (\|while (" "$f" 2>/dev/null || echo 0)
  [ "$IF_COUNT" -gt 2 ] && echo "  🟡 MEDIO — posible lógica en Repository: $f"
done

# ── 1.3 Exposición de entidades JPA en REST ───────────────
echo ""
echo "  -- Exposición de Entidades JPA --"
ENTITIES=$(find src/main/java -name "*.java" 2>/dev/null | xargs grep -l "@Entity" 2>/dev/null | grep -v test)
for entity in $ENTITIES; do
  ENTITY_NAME=$(basename "$entity" .java)
  # ¿Esta entidad se retorna en algún controller?
  EXPOSED=$(grep -rn "$ENTITY_NAME" src/main/java 2>/dev/null | grep -i "controller\|resource\|ResponseEntity" | grep -v "Dto\|DTO\|test")
  [ -n "$EXPOSED" ] && echo "  🟠 ALTO — @Entity posiblemente expuesta en REST sin DTO: $ENTITY_NAME" && echo "$EXPOSED" | head -2
done

# ── 1.4 @Transactional en capa correcta ──────────────────
echo ""
echo "  -- Gestión de transacciones --"
TRANSACTIONAL_IN_CTRL=$(grep -rn "@Transactional" src/main/java 2>/dev/null | grep -i "controller\|resource" | grep -v test)
TRANSACTIONAL_IN_REPO=$(grep -rn "@Transactional" src/main/java 2>/dev/null | grep -i "repository" | grep -v test)
TRANSACTIONAL_IN_SVC=$(grep -rn "@Transactional" src/main/java 2>/dev/null | grep -i "service" | grep -v test)

[ -n "$TRANSACTIONAL_IN_CTRL" ] && echo "  🟠 ALTO — @Transactional en Controller (debe estar en Service layer):" && echo "$TRANSACTIONAL_IN_CTRL" | head -3
[ -n "$TRANSACTIONAL_IN_REPO" ] && echo "  🟡 MEDIO — @Transactional en Repository (preferible en Service para agrupar operaciones):" && echo "$TRANSACTIONAL_IN_REPO" | head -3
[ -z "$TRANSACTIONAL_IN_SVC" ] && echo "  🟡 MEDIO — no se detectó @Transactional en Service layer — verificar gestión de transacciones"
[ -n "$TRANSACTIONAL_IN_SVC" ] && echo "  ✅ @Transactional en Service layer"

# ── 1.5 Fat Services (God Service) ───────────────────────
echo ""
echo "  -- Fat Services --"
for f in $(find src/main/java -name "*Service*.java" -o -name "*ServiceImpl*.java" 2>/dev/null | grep -v test); do
  LINES=$(wc -l < "$f")
  METHODS=$(grep -c "public\|private\|protected" "$f" 2>/dev/null || echo 0)
  [ "$LINES" -gt 300 ] && echo "  🟠 ALTO — Fat Service ($LINES líneas, ~$METHODS métodos): $f"
  [ "$LINES" -gt 150 ] && [ "$LINES" -le 300 ] && echo "  🟡 MEDIO — Service grande ($LINES líneas): $f"
done

# ── 1.6 Manejo de excepciones ────────────────────────────
echo ""
echo "  -- Manejo de excepciones --"
CONTROLLER_ADVICE=$(grep -rn "@ControllerAdvice\|@RestControllerAdvice\|ExceptionMapper" src/main/java 2>/dev/null | grep -v test | head -1)
[ -z "$CONTROLLER_ADVICE" ] && echo "  🟠 ALTO — no hay @ControllerAdvice/@RestControllerAdvice — los errores pueden exponer stack traces"
[ -n "$CONTROLLER_ADVICE" ] && echo "  ✅ Exception handler global detectado"

CATCH_GENERIC_SVC=$(grep -rn "catch (Exception\|catch (Throwable" src/main/java 2>/dev/null | grep -i "service" | grep -v test | head -5)
[ -n "$CATCH_GENERIC_SVC" ] && echo "  🟡 MEDIO — catch genérico en Service (manejar excepciones específicas):" && echo "$CATCH_GENERIC_SVC" | head -3

# ── 1.7 Validación de entrada ────────────────────────────
echo ""
echo "  -- Validación de entrada --"
VALID_ANNO=$(grep -rn "@Valid\|@Validated\|@NotNull\|@NotBlank" src/main/java 2>/dev/null | grep -iv "test" | head -1)
[ -z "$VALID_ANNO" ] && echo "  🟠 ALTO — no se detectaron anotaciones de validación (@Valid, @NotNull, @NotBlank)"
[ -n "$VALID_ANNO" ] && echo "  ✅ Validaciones de entrada detectadas"

# ── 1.8 @Autowired en campo ──────────────────────────────
AUTOWIRED_FIELD=$(grep -rn "@Autowired" src/main/java 2>/dev/null | grep -v "test\|interface\|/\*")
[ -n "$AUTOWIRED_FIELD" ] && echo "  🟡 MEDIO — @Autowired en campo (usar inyección por constructor):" && echo "$AUTOWIRED_FIELD" | head -5
[ -z "$AUTOWIRED_FIELD" ] && echo "  ✅ Sin @Autowired en campo"

# ── 1.9 @Data de Lombok ───────────────────────────────────
LOMBOK_DATA=$(grep -rn "@Data" src/main/java 2>/dev/null | grep -v test | head -5)
[ -n "$LOMBOK_DATA" ] && echo "  🔵 BAJO — @Data detectado (usar @Getter + @Builder + @ToString explícitos — más control sobre equals/hashCode):" && echo "$LOMBOK_DATA" | head -3

# ── 1.10 MapStruct vs mapeo manual ───────────────────────
MAPSTRUCT=$(grep -rn "import org\.mapstruct" src/main/java 2>/dev/null | head -1)
MANUAL_MAP=$(grep -rn "\.set[A-Z].*\.get[A-Z]" src/main/java 2>/dev/null | grep -v test | head -5)
[ -z "$MAPSTRUCT" ] && [ -n "$MANUAL_MAP" ] && echo "  🟡 MEDIO — mapeo manual entre capas detectado (usar MapStruct):" && echo "$MANUAL_MAP" | head -3
[ -n "$MAPSTRUCT" ] && echo "  ✅ MapStruct detectado"

# ── 1.11 Oportunidad de evolución a hexagonal ────────────
echo ""
echo "  -- Oportunidad de evolución --"
echo "  🔵 OPORTUNIDAD — estructura tradicional identificada. Si el microservicio tiene"
echo "     lógica de negocio compleja, considerar migración a arquitectura hexagonal para:"
echo "     · mayor testabilidad del dominio"
echo "     · aislamiento de cambios de infraestructura"
echo "     · adherencia a BIAN Banking Architecture"
echo "     Usar: 'Stive, implementa [HU de migración]' con spring-to-quarkus si aplica."
```

---

#### 1C — Si `PROJECT_STRUCTURE == "mixed"`

```bash
echo "======================================================"
echo "  [1] ARQUITECTURA MIXTA"
echo "======================================================"
echo "  ⚠️  El proyecto mezcla patrones hexagonales y tradicionales."
echo "  Ejecutando checks de AMBAS arquitecturas..."
echo ""

# Ejecutar auditoría hexagonal para los módulos con domain/ports/adapters
# Ejecutar auditoría tradicional para los módulos con Controller/Service/Repository sin ports
# [Aplicar los bloques 1A y 1B según corresponda a cada módulo detectado]

echo "  🟡 MEDIO — arquitectura mixta dificulta el mantenimiento y la consistencia"
echo "  Recomendación: definir el patrón objetivo y migrar gradualmente"
```

---

### Paso 2 — Auditoría de calidad de tests

Aplica a todas las estructuras.

```bash
echo "======================================================"
echo "  [2] CALIDAD DE TESTS"
echo "======================================================"

# ── 2.1 Ratio test/producción ─────────────────────────────
if [ "$TOTAL_JAVA" -gt 0 ]; then
  TEST_RATIO=$(python3 -c "print(round($TOTAL_TEST / $TOTAL_JAVA * 100))")
  echo "  Ratio test/producción: ${TEST_RATIO}% ($TOTAL_TEST test / $TOTAL_JAVA producción)"
  [ "$TEST_RATIO" -lt 40 ] && echo "  ❌ CRÍTICO — cobertura estimada muy baja (ratio < 40%)"
  [ "$TEST_RATIO" -ge 40 ] && [ "$TEST_RATIO" -lt 70 ] && echo "  🟠 ALTO — cobertura estimada insuficiente (ratio 40-70%)"
  [ "$TEST_RATIO" -ge 70 ] && [ "$TEST_RATIO" -lt 95 ] && echo "  🟡 MEDIO — cobertura aceptable pero por debajo del estándar ≥95%"
  [ "$TEST_RATIO" -ge 95 ] && echo "  ✅ Ratio de tests supera el estándar"
fi

# ── 2.2 Tipos de test presentes ───────────────────────────
echo ""
echo "  -- Tipos de tests --"
HAS_WEBMVCTEST=$(grep -rl "@WebMvcTest" src/test 2>/dev/null | head -1)
HAS_QUARKSTEST=$(grep -rl "@QuarkusTest" src/test 2>/dev/null | head -1)
HAS_DATAJPATEST=$(grep -rl "@DataJpaTest" src/test 2>/dev/null | head -1)
HAS_SPRINGBOOTTEST=$(grep -rl "@SpringBootTest" src/test 2>/dev/null | head -1)
HAS_MOCKITO=$(grep -rl "MockitoExtension\|@Mock\|@InjectMocks" src/test 2>/dev/null | head -1)
HAS_TESTCONTAINERS=$(grep -rl "Testcontainers\|@Container" src/test 2>/dev/null | head -1)
HAS_REST_ASSURED=$(grep -rl "RestAssured\|given()\|\.when()\." src/test 2>/dev/null | head -1)

[ -n "$HAS_WEBMVCTEST" ]    && echo "  ✅ @WebMvcTest — tests de controller slice"
[ -n "$HAS_QUARKSTEST" ]    && echo "  ✅ @QuarkusTest — tests Quarkus"
[ -n "$HAS_DATAJPATEST" ]   && echo "  ✅ @DataJpaTest — tests JPA slice"
[ -n "$HAS_MOCKITO" ]       && echo "  ✅ Mockito — tests unitarios"
[ -n "$HAS_REST_ASSURED" ]  && echo "  ✅ REST Assured — tests de integración REST"
[ -n "$HAS_TESTCONTAINERS" ] && echo "  ✅ Testcontainers — tests con infraestructura real"
[ -n "$HAS_SPRINGBOOTTEST" ] && echo "  ℹ️  @SpringBootTest detectado (costoso — preferir slice tests cuando sea posible)"

[ -z "$HAS_WEBMVCTEST" ] && [ -z "$HAS_QUARKSTEST" ] && echo "  🟠 ALTO — no hay tests de controller"
[ -z "$HAS_DATAJPATEST" ] && [ "$FRAMEWORK" = "spring-boot" ] && echo "  🟡 MEDIO — no hay tests de capa JPA (@DataJpaTest)"
[ -z "$HAS_MOCKITO" ]    && echo "  🟡 MEDIO — no hay tests unitarios con Mockito"

# ── 2.3 Calidad de tests existentes ──────────────────────
echo ""
echo "  -- Calidad de tests --"

# Tests sin asserts (tests vacíos / ilusión de cobertura)
EMPTY_TESTS=$(find src/test -name "*.java" 2>/dev/null | xargs grep -l "@Test" 2>/dev/null | \
              xargs grep -L "assert\|verify\|assertEquals\|assertThat\|given\|expect" 2>/dev/null)
[ -n "$EMPTY_TESTS" ] && echo "  ❌ CRÍTICO — tests sin asserts detectados (falsa cobertura): $(echo $EMPTY_TESTS | tr '\n' ',')"

# Tests que solo prueban getters/setters (valor mínimo)
GETTER_TESTS=$(grep -rn "\.get[A-Z]\|\.set[A-Z]" src/test 2>/dev/null | grep -v "import\|//\|Mock" | wc -l | tr -d ' ')
[ "$GETTER_TESTS" -gt 20 ] && echo "  🟡 MEDIO — alto número de tests de getters/setters ($GETTER_TESTS ocurrencias) — priorizar tests de comportamiento"

# @Ignore / @Disabled tests
IGNORED=$(grep -rn "@Ignore\|@Disabled" src/test 2>/dev/null | grep -v "import")
[ -n "$IGNORED" ] && echo "  🟡 MEDIO — tests ignorados/deshabilitados detectados:" && echo "$IGNORED" | head -5
```

---

### Paso 3 — Auditoría de seguridad

```bash
echo "======================================================"
echo "  [3] SEGURIDAD"
echo "======================================================"

# ── 3.1 Credenciales hardcodeadas ────────────────────────
echo "  -- Credenciales hardcodeadas --"
HARDCODED_PASS=$(grep -rn "password\s*=\s*[\"'][^\"']\|passwd\s*=\s*[\"']\|secret\s*=\s*[\"']" \
                 src/main/java src/main/resources 2>/dev/null | grep -iv "placeholder\|example\|test\|#\|//")
[ -n "$HARDCODED_PASS" ] && echo "  ❌ CRÍTICO — posibles credenciales hardcodeadas:" && echo "$HARDCODED_PASS" | head -5
[ -z "$HARDCODED_PASS" ] && echo "  ✅ No se detectaron credenciales hardcodeadas"

# ── 3.2 Datos sensibles en logs ──────────────────────────
echo ""
echo "  -- Logging de datos sensibles --"
SENSITIVE_LOG=$(grep -rn "log.*password\|log.*passwd\|log.*secret\|log.*token\|log.*credit\|log.*cvv" \
                src/main/java 2>/dev/null | grep -iv "mask\|redact\|//\|/*" | head -5)
[ -n "$SENSITIVE_LOG" ] && echo "  ❌ CRÍTICO — posible logging de datos sensibles:" && echo "$SENSITIVE_LOG" | head -5
[ -z "$SENSITIVE_LOG" ] && echo "  ✅ No se detectó logging de datos sensibles"

# ── 3.3 SQL / JPQL injection ─────────────────────────────
echo ""
echo "  -- SQL / JPQL Injection --"
STRING_CONCAT_QUERY=$(grep -rn "\"SELECT\|\"select\|\"UPDATE\|\"update\|\"DELETE\|\"delete\|\"INSERT\|\"insert" \
                      src/main/java 2>/dev/null | grep "+\s*[a-z]" | grep -v test | head -5)
[ -n "$STRING_CONCAT_QUERY" ] && echo "  ❌ CRÍTICO — concatenación de strings en queries (riesgo SQL injection):" && echo "$STRING_CONCAT_QUERY" | head -5
[ -z "$STRING_CONCAT_QUERY" ] && echo "  ✅ No se detectó concatenación en queries"

# ── 3.4 Stack traces expuestos en respuestas ─────────────
echo ""
echo "  -- Exposición de errores internos --"
STACK_EXPOSED=$(grep -rn "e\.getMessage()\|e\.printStackTrace\|exception\.getMessage()" \
                src/main/java 2>/dev/null | grep -i "response\|return\|body\|message" | grep -v test | head -5)
[ -n "$STACK_EXPOSED" ] && echo "  🟠 ALTO — posibles stack traces o mensajes de excepción en respuesta REST:" && echo "$STACK_EXPOSED" | head -5

# ── 3.5 Endpoints sin validación de entrada ───────────────
echo ""
echo "  -- Validación de entrada en endpoints --"
CTRL_METHODS=$(grep -c "@PostMapping\|@PutMapping\|@PatchMapping" src/main/java 2>/dev/null || echo 0)
VALID_COUNT=$(grep -c "@Valid\|@Validated" src/main/java 2>/dev/null || echo 0)
if [ "$CTRL_METHODS" -gt 0 ] && [ "$VALID_COUNT" -eq 0 ]; then
  echo "  🟠 ALTO — hay $CTRL_METHODS endpoints de escritura sin @Valid / @Validated"
elif [ "$CTRL_METHODS" -gt "$VALID_COUNT" ]; then
  echo "  🟡 MEDIO — solo $VALID_COUNT de $CTRL_METHODS endpoints de escritura tienen @Valid"
else
  echo "  ✅ Validaciones de entrada presentes"
fi
```

---

### Paso 4 — Auditoría de performance

```bash
echo "======================================================"
echo "  [4] PERFORMANCE"
echo "======================================================"

# ── 4.1 FetchType.EAGER ───────────────────────────────────
echo "  -- Fetch strategy --"
FETCH_EAGER=$(grep -rn "FetchType\.EAGER\|fetch = FetchType\.EAGER" src/main/java 2>/dev/null | grep -v test | head -5)
[ -n "$FETCH_EAGER" ] && echo "  🟠 ALTO — FetchType.EAGER detectado (riesgo de queries N+1 y carga excesiva):" && echo "$FETCH_EAGER" | head -5
[ -z "$FETCH_EAGER" ] && echo "  ✅ Sin FetchType.EAGER"

# ── 4.2 Riesgo N+1 ───────────────────────────────────────
echo ""
echo "  -- Riesgo N+1 queries --"
# Loops con llamadas a repository dentro
REPO_IN_LOOP=$(grep -rn "for\|while" src/main/java 2>/dev/null | grep -v test | while read line; do
  FILE=$(echo "$line" | cut -d: -f1)
  LINENUM=$(echo "$line" | cut -d: -f2)
  # Verificar si hay llamada a repository en las siguientes 5 líneas
  sed -n "$((LINENUM+1)),$((LINENUM+5))p" "$FILE" 2>/dev/null | grep -q "repository\|Repository\|findBy\|save(" && echo "$FILE:$LINENUM"
done | head -3)
[ -n "$REPO_IN_LOOP" ] && echo "  🟠 ALTO — posible N+1: acceso a repository dentro de bucle:" && echo "$REPO_IN_LOOP"

# ── 4.3 Endpoints sin paginación ─────────────────────────
echo ""
echo "  -- Paginación --"
FIND_ALL=$(grep -rn "\.findAll()\|findAllBy\b" src/main/java 2>/dev/null | grep -v "test\|Pageable\|Page<" | head -5)
[ -n "$FIND_ALL" ] && echo "  🟡 MEDIO — findAll() sin paginación (riesgo con grandes volúmenes de datos):" && echo "$FIND_ALL" | head -5

HAS_PAGEABLE=$(grep -rn "Pageable\|PageRequest\|Page<" src/main/java 2>/dev/null | grep -v test | head -1)
[ -n "$HAS_PAGEABLE" ] && echo "  ✅ Paginación detectada (Pageable / Page<T>)"

# ── 4.4 Caching ───────────────────────────────────────────
echo ""
echo "  -- Caching --"
HAS_CACHE=$(grep -rn "@Cacheable\|@CacheEvict\|@CachePut" src/main/java 2>/dev/null | grep -v test | head -1)
[ -n "$HAS_CACHE" ] && echo "  ✅ Cache annotations detectadas"

# Endpoints de consulta frecuente sin cache (heurística: métodos retrieve/get sin @Cacheable)
RETRIEVE_NO_CACHE=$(grep -rn "@GetMapping\|@QueryParam.*GET" src/main/java 2>/dev/null | grep -v "test\|@Cacheable" | wc -l | tr -d ' ')
[ "$RETRIEVE_NO_CACHE" -gt 0 ] && [ -z "$HAS_CACHE" ] && echo "  🔵 OPORTUNIDAD — $RETRIEVE_NO_CACHE endpoints GET sin caching — evaluar @Cacheable para endpoints de alta frecuencia"
```

---

### Paso 5 — Auditoría de dependencias y tecnología

```bash
echo "======================================================"
echo "  [5] DEPENDENCIAS Y TECNOLOGÍA"
echo "======================================================"

# ── 5.1 Versión de framework ──────────────────────────────
echo "  -- Versión del framework --"
if [ "$FRAMEWORK" = "spring-boot" ]; then
  python3 -c "
v = '$FRAMEWORK_VERSION'
if not v: print('  ⚠️  No se pudo detectar versión de Spring Boot')
elif v < '3.0.0': print(f'  ❌ CRÍTICO — Spring Boot {v} (EOL) — migrar a 3.x urgente')
elif v < '3.2.0': print(f'  🟡 MEDIO — Spring Boot {v} — considerar actualizar a 3.2+ LTS')
else: print(f'  ✅ Spring Boot {v}')
" 2>/dev/null
elif [ "$FRAMEWORK" = "quarkus" ]; then
  python3 -c "
v = '$FRAMEWORK_VERSION'
if not v: print('  ⚠️  No se pudo detectar versión de Quarkus')
elif v < '3.0.0': print(f'  ❌ CRÍTICO — Quarkus {v} (EOL) — migrar a 3.x')
else: print(f'  ✅ Quarkus {v}')
" 2>/dev/null
fi

# ── 5.2 Versión de Java ───────────────────────────────────
echo ""
echo "  -- Versión de Java --"
python3 -c "
v = '$JAVA_VERSION'
if not v: print('  ⚠️  No se pudo detectar versión de Java')
elif int(v.split('.')[0]) < 17: print(f'  ❌ CRÍTICO — Java {v} (Spring Boot 3.x requiere Java 17+)')
elif v == '17': print(f'  🟡 MEDIO — Java {v} (LTS, pero Java 21 LTS ya disponible)')
elif v == '21': print(f'  ✅ Java {v} (LTS actual)')
else: print(f'  ✅ Java {v}')
" 2>/dev/null

# ── 5.3 Dependencias legacy / deprecadas ─────────────────
echo ""
echo "  -- Dependencias legacy --"
JAVAX_IMPORTS=$(grep -rn "import javax\." src/main/java 2>/dev/null | grep -v "test" | head -5)
[ -n "$JAVAX_IMPORTS" ] && echo "  🟠 ALTO — imports javax.* detectados (migrar a jakarta.* para Spring Boot 3.x / Quarkus 3.x):" && echo "$JAVAX_IMPORTS" | head -5
[ -z "$JAVAX_IMPORTS" ] && echo "  ✅ Sin imports javax.* (usando jakarta.*)"

# Flyway / Liquibase
HAS_FLYWAY=$(grep -q "flyway\|liquibase" pom.xml 2>/dev/null && echo "yes")
[ -z "$HAS_FLYWAY" ] && echo "  🟡 MEDIO — no se detectó Flyway ni Liquibase — ¿las migraciones de BD están versionadas?"
[ -n "$HAS_FLYWAY" ] && echo "  ✅ Migraciones de BD versionadas (Flyway/Liquibase)"

# ── 5.4 @Data de Lombok (toda la app) ────────────────────
echo ""
echo "  -- Lombok --"
LOMBOK_DATA=$(grep -rn "@Data" src/main/java 2>/dev/null | grep -v test | wc -l | tr -d ' ')
[ "$LOMBOK_DATA" -gt 0 ] && echo "  🟡 MEDIO — @Data en $LOMBOK_DATA clases (usar @Getter + @Builder + @ToString explícitos)"
[ "$LOMBOK_DATA" -eq 0 ] && echo "  ✅ Sin @Data"
```

---

### Paso 6 — Auditoría BIAN

```bash
echo "======================================================"
echo "  [6] BIAN COMPLIANCE"
echo "======================================================"

# ── 6.1 Verbos en endpoints ──────────────────────────────
echo "  -- Verbos BIAN en endpoints --"
BIAN_VERBS="initiate|retrieve|execute|update|request|notify|record|register|evaluate|terminate|capture"

if [ "$FRAMEWORK" = "spring-boot" ]; then
  ALL_MAPPINGS=$(grep -rn "@GetMapping\|@PostMapping\|@PutMapping\|@PatchMapping\|@DeleteMapping\|@RequestMapping" \
                 src/main/java 2>/dev/null | grep -v test)
elif [ "$FRAMEWORK" = "quarkus" ]; then
  ALL_MAPPINGS=$(grep -rn "@Path\|@GET\|@POST\|@PUT\|@DELETE" src/main/java 2>/dev/null | grep -v test)
fi

NON_BIAN=$(echo "$ALL_MAPPINGS" | grep -Ev "$BIAN_VERBS" | grep -Ev "//|/\*|import")
[ -n "$NON_BIAN" ] && echo "  🟡 MEDIO — endpoints sin verbos BIAN (verificar naming):" && echo "$NON_BIAN" | head -8
[ -z "$NON_BIAN" ] && [ -n "$ALL_MAPPINGS" ] && echo "  ✅ Endpoints usan verbos BIAN"

# ── 6.2 Package base ─────────────────────────────────────
echo ""
echo "  -- Package base --"
BASE_PKG=$(grep "^package " $(find src/main/java -name "*.java" | head -1) 2>/dev/null | \
           sed 's/^package //;s/;//' | cut -d. -f1-3)
echo "  Base package detectado: $BASE_PKG"
echo "$BASE_PKG" | grep -q "com\.jotace" && echo "  ✅ Package base alineado con convención" || \
  echo "  ℹ️  Verificar si el package base sigue la convención: com.jotace.<serviceDomain>"

# ── 6.3 Versioning en URLs ────────────────────────────────
echo ""
echo "  -- Versioning en URLs --"
VERSION_IN_URL=$(grep -rn "/v[0-9]\|/api/v" src/main/java 2>/dev/null | grep -v test | head -3)
[ -n "$VERSION_IN_URL" ] && echo "  🟡 MEDIO — versión en URL detectada (BIAN prefiere versionado en headers, no en path):" && echo "$VERSION_IN_URL" | head -3
```

---

### Paso 7 — Auditoría de documentación y observabilidad

```bash
echo "======================================================"
echo "  [7] DOCUMENTACIÓN Y OBSERVABILIDAD"
echo "======================================================"

# ── 7.1 OpenAPI / Swagger ────────────────────────────────
echo "  -- OpenAPI / Swagger --"
HAS_OPENAPI=$(grep -q "springdoc\|openapi\|swagger\|smallrye-open-api" pom.xml 2>/dev/null && echo "yes")
HAS_SCHEMA=$(grep -rn "@Schema\|@Operation\|@ApiResponse" src/main/java 2>/dev/null | grep -v test | head -1)
[ -z "$HAS_OPENAPI" ] && echo "  🟡 MEDIO — no se detectó librería OpenAPI (springdoc-openapi / smallrye-open-api)"
[ -n "$HAS_OPENAPI" ] && [ -z "$HAS_SCHEMA" ] && echo "  🔵 BAJO — OpenAPI configurado pero sin anotaciones @Schema/@Operation en DTOs"
[ -n "$HAS_OPENAPI" ] && [ -n "$HAS_SCHEMA" ] && echo "  ✅ OpenAPI con anotaciones de documentación"

# ── 7.2 Logging estructurado ─────────────────────────────
echo ""
echo "  -- Logging --"
SYSOUT=$(grep -rn "System\.out\.print\|System\.err\.print" src/main/java 2>/dev/null | grep -v test | head -5)
[ -n "$SYSOUT" ] && echo "  🟡 MEDIO — System.out.print detectado (usar SLF4J Logger):" && echo "$SYSOUT" | head -3

HAS_LOGGER=$(grep -rn "LoggerFactory\|@Slf4j\|@Log4j2" src/main/java 2>/dev/null | grep -v test | head -1)
[ -n "$HAS_LOGGER" ] && echo "  ✅ Logger SLF4J detectado"
[ -z "$HAS_LOGGER" ] && [ -z "$SYSOUT" ] && echo "  🟡 MEDIO — no se detectó logging en el proyecto"

# ── 7.3 TODOs sin referencia a HU ────────────────────────
echo ""
echo "  -- TODOs pendientes --"
TODOS_NO_HU=$(grep -rn "TODO\|FIXME\|HACK\|XXX" src/main/java src/test 2>/dev/null | \
              grep -v "HU-\|SCRUM-\|JIRA-" | grep -v "//.*import\|import " | head -8)
[ -n "$TODOS_NO_HU" ] && echo "  🔵 BAJO — TODOs/FIXMEs sin referencia a HU:" && echo "$TODOS_NO_HU" | head -5

# ── 7.4 God Classes (generales) ──────────────────────────
echo ""
echo "  -- Tamaño de clases --"
find src/main/java -name "*.java" 2>/dev/null | while read f; do
  LINES=$(wc -l < "$f")
  [ "$LINES" -gt 500 ] && echo "  🟠 ALTO — God Class ($LINES líneas): $f"
  [ "$LINES" -gt 300 ] && [ "$LINES" -le 500 ] && echo "  🟡 MEDIO — clase grande ($LINES líneas): $f"
done
```

---

### Paso 8 — Reporte consolidado

Con todos los hallazgos recolectados, generar el reporte en formato estructurado:

```
╔══════════════════════════════════════════════════════════════════╗
║  REPORTE DE AUDITORÍA TÉCNICA                                    ║
║  Microservicio : [ARTIFACT_ID]                                   ║
║  Fecha         : [fecha actual]                                  ║
╚══════════════════════════════════════════════════════════════════╝

📊 RESUMEN DEL PROYECTO
  Framework  : [FRAMEWORK] [FRAMEWORK_VERSION]
  Java       : [JAVA_VERSION]
  Estructura : [hexagonal | traditional | mixed]
  Clases     : [TOTAL_JAVA] producción / [TOTAL_TEST] test (ratio: [TEST_RATIO]%)
  Líneas     : ~[TOTAL_LINES] LOC

══════════════════════════════════════════════════════════════════

❌ CRÍTICO — bloquea calidad, seguridad o correctitud
──────────────────────────────────────────────────────
[hallazgos críticos con archivo:línea cuando aplica]
· Si ninguno → ✅ Sin hallazgos críticos

🟠 ALTO — impacta mantenibilidad, correctitud o seguridad
──────────────────────────────────────────────────────────
[hallazgos altos]
· Si ninguno → ✅ Sin hallazgos altos

🟡 MEDIO — deuda técnica que se acumula con el tiempo
───────────────────────────────────────────────────────
[hallazgos medios]

🔵 BAJO / OPORTUNIDAD — mejoras de largo plazo
───────────────────────────────────────────────
[hallazgos bajos y oportunidades]

══════════════════════════════════════════════════════════════════

📋 PLAN DE ACCIÓN RECOMENDADO
  (ordenado por impacto / urgencia)

  1. [acción más urgente — qué hacer, dónde, estimación]
  2. [segunda acción]
  3. [tercera acción]
  ...

══════════════════════════════════════════════════════════════════

📈 SCORE DE SALUD DEL MICROSERVICIO
  Arquitectura  : [A/B/C/D] — [justificación breve]
  Tests         : [A/B/C/D] — [justificación breve]
  Seguridad     : [A/B/C/D] — [justificación breve]
  Performance   : [A/B/C/D] — [justificación breve]
  BIAN          : [A/B/C/D] — [justificación breve]
  Documentación : [A/B/C/D] — [justificación breve]
  ──────────────────────────────────────────────────
  Score global  : [A/B/C/D]

  A = excelente  B = bueno, mejoras menores  C = deuda significativa  D = requiere atención urgente

══════════════════════════════════════════════════════════════════
Hallazgos: [N] ❌  [N] 🟠  [N] 🟡  [N] 🔵
Esfuerzo estimado para resolver deuda crítica+alta: [BAJA <2d | MEDIA 3-10d | ALTA >10d]
══════════════════════════════════════════════════════════════════
```

---

### Paso 9 — Fin de la auditoría

El **reporte consolidado del Paso 8 es el entregable final**. Una vez presentado, la auditoría termina.

**No ejecutar ninguna acción posterior:** no crear archivos, no crear issues en JIRA ni en ningún otro sistema, no modificar el proyecto. Stive Auditor solo identifica y reporta.

> 🗓️ **Planificado para un release futuro:** el envío automático de hallazgos a JIRA (crear HUs de deuda técnica desde el reporte) está en el backlog. Cuando el MCP de Atlassian exponga un tool de creación de issues, este paso generará las HUs tras la confirmación explícita del usuario. Por ahora, si el usuario quiere registrar los hallazgos en JIRA, debe hacerlo manualmente a partir del reporte.

---

## Limitaciones conocidas

| Limitación | Alternativa |
|---|---|
| Cobertura % estimada por ratio de archivos, no JaCoCo | Para cobertura exacta: `mvn verify` con JaCoCo configurado |
| N+1 detectado por heurística de loops + repository — puede tener falsos positivos | Confirmar con explain de queries en entorno real |
| BIAN compliance verificado por naming — no semántica del contrato | Revisión manual de contratos BIAN |
| God Classes por líneas — no por responsabilidades (SRP) | Revisión manual de cohesión |
| Credenciales hardcodeadas por patrones de string — puede tener falsos positivos | Revisar manualmente los archivos señalados |
| El reporte no se envía a JIRA automáticamente (planificado para un release futuro) | Registrar los hallazgos manualmente en JIRA a partir del reporte |
