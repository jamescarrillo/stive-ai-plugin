---
name: plan-generator
description: Genera plan.md y tasks.json desde un spec técnico aprobado, descomponiendo la implementación en tareas atómicas por capa con estimaciones y dependencias.
---

# Skill: Plan Generator

## Propósito

Convertir el spec técnico aprobado (`.github/specs/HU-XXX.md`) en un plan de implementación ejecutable, con dos artefactos:
- `plan.md` — legible por el desarrollador para revisión
- `tasks.json` — estructurado para que el agente de codificación los ejecute en orden

## Cuándo ejecutar

Inmediatamente después de que el desarrollador aprueba el spec (Checkpoint 1).

---

## Proceso paso a paso

### Paso 1 — Leer el spec aprobado

Lee `.github/specs/HU-XXX.md` completamente. Extrae:
- Frontmatter: `bianservicedomain`, `businessobject`, `behaviorqualifier`, `bianverb`, `basepackage`, `microservicename`, `estimatedcomplexity`
- Aggregate Root + Value Objects + Excepciones de dominio
- Inbound + Outbound Ports
- Adaptadores REST y JPA
- Pruebas requeridas
- Criterios de aceptación (para verificar que el plan los cubre todos)

### Paso 2 — Identificar el tipo de implementación

Leer del metadata de la HU los campos `framework`, `projectStructure` y `detectedBasePackage`:

```python
import json
# HU_KEY = clave real de la HU (ej: "SCRUM-5"), del contexto de PASO 0.
# En este skill, sustituir cualquier `HU-XXX` de prosa por esa clave.
meta = json.load(open(f'.github/specs/.metadata/{HU_KEY}.json'))
PROJECT_STRUCTURE = meta.get('projectStructure', 'new')
FRAMEWORK = meta.get('framework', 'spring-boot')
BASE_PACKAGE = meta.get('detectedBasePackage', '')
```

Determina la naturaleza del trabajo combinando esta información con los indicadores de la HU:

| `projectStructure` | `framework` | Agente | `implementationType` |
|---|---|---|---|
| `new` | `spring-boot` | `spring-engineer` | `new_microservice` |
| `new` | `quarkus` | `quarkus-engineer` | `new_microservice` |
| `hexagonal` o `mixed` | `spring-boot` | `spring-engineer` | `new_feature` |
| `hexagonal` o `mixed` | `quarkus` | `quarkus-engineer` | `new_feature` |
| `traditional` | `spring-boot` | `spring-engineer` (modo adaptación) | `new_feature_traditional` |
| `traditional` | `quarkus` | `quarkus-engineer` (modo adaptación) | `new_feature_traditional` |
| cualquiera | — (HU de migración) | `spring-to-quarkus` | `migration` |

> **Nota:** Si la HU menciona migración, Quarkus como destino, o hay Spring Boot existente con intención de migrar, el tipo siempre es `migration` independientemente de `projectStructure`.

> **Nota Quarkus:** Para `framework = "unknown"` y el proyecto no tiene un pom.xml estándar, preguntar al usuario: "No pude detectar el framework. ¿Es Spring Boot o Quarkus?"

Escribe el tipo en `tasks.json` como `"implementationType"`, y también guarda `"projectStructure"` y `"framework"` a nivel raíz del JSON.

### Paso 2b — Analizar código existente (solo si `new_feature`, `new_feature_traditional` o `migration`)

**Omitir este paso si `implementationType == new_microservice`** — no hay código previo que analizar.

Para `new_feature` y `new_feature_traditional`, leer el contenido de `src/main/java/` y construir el inventario del estado actual según la estructura detectada:

#### Inventario del dominio existente — condicional por `PROJECT_STRUCTURE`

**Si `PROJECT_STRUCTURE == "hexagonal"`:**

Primero leer los paths detectados del metadata (guardados por PASO 2). Si el proyecto usa
nombres no estándar (ej: `core/` en vez de `domain/`, `driven/` en vez de `outbound/`),
los find commands se adaptan automáticamente:

```python
import json
meta = json.load(open(f'.github/specs/.metadata/{HU_KEY}.json'))
HEX_DOMAIN   = meta.get('hexDomainDir', 'domain')    # domain | core
HEX_PORTS    = meta.get('hexPortsDir', 'ports')       # ports | driven | primary
HEX_ADAPTERS = meta.get('hexAdaptersDir', 'adapters') # adapters | secondary
```

```bash
# Usando los paths reales del proyecto (no siempre son los de Stive)
HEX_DOMAIN="[valor de metadata, ej: domain o core]"
HEX_PORTS="[valor de metadata, ej: ports o driven]"
HEX_ADAPTERS="[valor de metadata, ej: adapters o secondary]"

# Qué Aggregate Roots ya existen
find src/main/java -name "*.java" -path "*/${HEX_DOMAIN}/model/*" 2>/dev/null | grep -v "Entity\|Exception\|Event"
# Fallback si no hay model/: buscar en el domain dir directamente
find src/main/java -name "*.java" -path "*/${HEX_DOMAIN}/*" 2>/dev/null | grep -v "Exception\|Event\|UseCase\|Port"

# Qué excepciones de dominio ya existen
find src/main/java -name "*Exception.java" -path "*/${HEX_DOMAIN}/*" 2>/dev/null

# Qué puertos inbound ya existen (UseCases)
find src/main/java -name "*UseCase.java" 2>/dev/null
find src/main/java -name "*.java" -path "*/${HEX_PORTS}/inbound/*" 2>/dev/null
find src/main/java -name "*.java" -path "*/${HEX_PORTS}/in/*" 2>/dev/null

# Qué puertos outbound ya existen
find src/main/java -name "*Port.java" 2>/dev/null
find src/main/java -name "*.java" -path "*/${HEX_PORTS}/outbound/*" 2>/dev/null
find src/main/java -name "*.java" -path "*/${HEX_PORTS}/out/*" 2>/dev/null

# Qué Application Services ya existen
find src/main/java -name "*Service.java" -path "*/application/service/*" 2>/dev/null
# Fallback — buscar services fuera del patrón estándar
find src/main/java -name "*Service.java" -not -name "*Entity*" -not -path "*/test/*" 2>/dev/null

# Qué controllers ya existen
find src/main/java -name "*Controller.java" -path "*/${HEX_ADAPTERS}/*" 2>/dev/null
find src/main/java -name "*Controller.java" -not -path "*/test/*" 2>/dev/null

# Qué entidades JPA ya existen
find src/main/java -name "*Entity.java" -path "*/${HEX_ADAPTERS}/*" 2>/dev/null
find src/main/java -name "*Entity.java" -not -path "*/test/*" 2>/dev/null
```

> **Si los find commands retornan vacío** aunque el proyecto claramente tiene código hexagonal:
> el proyecto usa una estructura diferente a las variantes conocidas. En ese caso, preguntar
> al usuario: "Detecté que el proyecto es hexagonal pero no reconozco la estructura de directorios.
> ¿Me puedes indicar el directorio del dominio y el de ports/adapters?"

**Si `PROJECT_STRUCTURE == "traditional"`:**

```bash
# Qué controllers ya existen
find src/main/java -name "*Controller.java" -not -path "*/test/*"

# Qué servicios ya existen
find src/main/java \( -name "*Service.java" -o -name "*ServiceImpl.java" \) -not -path "*/test/*"

# Qué repositorios ya existen
find src/main/java -name "*Repository.java" -not -path "*/test/*"

# Qué entidades/modelos ya existen
find src/main/java \( -name "*Entity.java" -o -name "*Model.java" \) -not -path "*/test/*"

# Qué DTOs ya existen
find src/main/java \( -name "*DTO.java" -o -name "*Dto.java" -o -name "*Request.java" -o -name "*Response.java" \) -not -path "*/test/*"
```

**Si `PROJECT_STRUCTURE == "mixed"`:**

```bash
# Ejecutar ambos conjuntos de find y presentar inventario diferenciado

echo "=== Zona Hexagonal ==="
find src/main/java -name "*.java" -path "*/domain/model/*" | grep -v "Entity\|Exception\|Event"
find src/main/java -name "*UseCase.java" -path "*/ports/inbound/*"
find src/main/java -name "*Port.java" -path "*/ports/outbound/*"
find src/main/java -name "*Controller.java" -path "*/infrastructure/*"

echo ""
echo "=== Zona Tradicional ==="
find src/main/java -name "*Controller.java" -not -path "*/infrastructure/*" -not -path "*/test/*"
find src/main/java \( -name "*Service.java" -o -name "*ServiceImpl.java" \) -not -path "*/application/service/*" -not -path "*/test/*"
find src/main/java -name "*Repository.java" -not -path "*/test/*"
```

Para cada componente encontrado, determinar:

| Componente existente | ¿Reusar? | ¿Modificar? | ¿Qué agregar? |
|----------------------|----------|-------------|---------------|
| `[Aggregate].java`   | Sí/No    | Sí/No       | [nuevos métodos de negocio] |
| `[X]RepositoryPort.java` | Sí/No | Sí/No    | [nuevos métodos de consulta] |
| `[X]JpaAdapter.java` | Sí/No   | Sí/No       | [implementar nuevos métodos] |
| `[X]Controller.java` | Sí/No   | Sí/No       | [nuevos endpoints] |
| `[X]Entity.java`     | Sí/No   | Sí/No       | [nuevas columnas] |

#### Identificar refactorizaciones necesarias

Antes de crear las tareas, evaluar si algún código existente bloquea la implementación:

```
Para cada requisito de la HU:
  ¿Puede implementarse sin modificar código existente? → tarea CREAR
  ¿Requiere agregar métodos a una clase existente?     → tarea MODIFICAR
  ¿Requiere cambiar la firma de un método existente?   → tarea REFACTORIZAR (documentar impacto)
  ¿Requiere cambiar el esquema de BD?                  → tarea MIGRACIÓN FLYWAY
```

**Regla de scope para refactoring**: si una refactorización necesaria afecta código fuera del bounded context de esta HU (otros módulos, otros servicios), NO incluirla en las tareas — reportarla como riesgo en `plan.md` y proponer una HU separada.

#### Resultado del análisis

Antes de generar las tareas, producir este resumen en `plan.md`:

```markdown
## Análisis de Código Existente

| Componente | Estado | Acción en esta HU |
|------------|--------|-------------------|
| `Account.java` | ✅ Existe | MODIFICAR — agregar método `block()` |
| `AccountRepositoryPort.java` | ✅ Existe | MODIFICAR — agregar `findByStatus()` |
| `AccountJpaAdapter.java` | ✅ Existe | MODIFICAR — implementar `findByStatus()` |
| `InitiateAccountController.java` | ✅ Existe | REUSAR sin cambios |
| `BlockAccountController.java` | ❌ No existe | CREAR |
| `V2__add_blocked_status.sql` | ❌ No existe | CREAR (Flyway migration) |

### Refactorizaciones identificadas
- [si hay]: [descripción del impacto y justificación]
- [si no hay]: Ninguna — la feature se implementa agregando componentes nuevos.
```

### Paso 3 — Descomponer en tareas

Descompona la implementación en tareas atómicas con este orden obligatorio (nunca omitas el orden de capas):

#### Grupo 0: Scaffold (solo si es microservicio nuevo)
```
TASK-0.1: Inicializar estructura del proyecto
  - Si framework = "spring-boot":
    pom.xml con spring-boot-starter-parent 3.x + dependencias del spec
    application.yml base (datasource, logging, springdoc)
    Clase principal @SpringBootApplication
    (El scaffold ya existe — PORT lo generó. Esta tarea configura pom.xml y application.yml si faltan dependencias.)

  - Si framework = "quarkus":
    pom.xml con quarkus-bom 3.33 + dependencias del spec (RESTEasy Reactive, Panache, etc.)
    application.properties base (quarkus.http, quarkus.datasource, Flyway)
    Sin clase principal explícita — Quarkus auto-detecta
    Test profile H2 en application.properties (%test.*)

  Ambos casos:
  - Estructura de paquetes vacía: domain/, application/ports/inbound/, application/ports/outbound/,
    application/service/, infrastructure/adapters/inbound/rest/, infrastructure/adapters/outbound/database/,
    infrastructure/config/
```

#### Grupo 1: Capa Domain
```
TASK-1.1: Crear Value Objects
  - Para cada Value Object del spec:
    [Nombre].java como Java record en domain/model/
    Con validaciones en constructor compacto

TASK-1.2: Crear Aggregate Root y Entities
  - [BusinessObject].java en domain/model/
  - Constructor privado con Builder pattern (no usar @Data)
  - Métodos de comportamiento con lógica de negocio e invariantes
  - Sin anotaciones Spring/JPA/Jackson

TASK-1.3: Crear Excepciones de Dominio
  - [BusinessObject]NotFoundException.java
  - [BusinessObject]AlreadyExistsException.java
  - [Otras según el spec]
  - Todas en domain/exception/, extienden RuntimeException

TASK-1.4: Crear Domain Events (si aplica)
  - [BusinessObject][Acción]Event.java como record en domain/event/
  - Un event por cada acción de negocio que otros bounded contexts deben conocer
```

#### Grupo 2: Capa Application
```
TASK-2.1: Crear Inbound Ports (interfaces)
  - Un UseCase por cada acción del spec
  - [BianVerb][BusinessObject]UseCase.java en application/ports/inbound/
  - Command/Query como record junto al UseCase

TASK-2.2: Crear Outbound Ports (interfaces)
  - [BusinessObject]RepositoryPort.java en application/ports/outbound/
  - [ExternalService]Port.java si hay dependencias externas
  - Solo tipos de dominio, sin tecnología

TASK-2.3: Implementar Application Services (casos de uso)
  - [BianVerb][BusinessObject]Service.java en application/service/
  - Implements el Inbound Port correspondiente
  - Solo orquestación: valida entrada → llama dominio → llama outbound port → retorna
  - Sin lógica de negocio (eso va en el Aggregate)
  - SIN @Service (ADR-2) — inyección por constructor; registrado en TASK-2.4

TASK-2.4: Registrar Application Services en DomainConfig (ADR-2)
  - infrastructure/config/DomainConfig.java (crear o actualizar si ya existe)
  - @Configuration con un @Bean por cada Application Service de la HU
  - Cada @Bean recibe sus OutboundPorts por constructor (Spring los inyecta vía tipo)
  - Referencia: spring-engineer → "Template DomainConfig"
```

#### Grupo 3: Capa Infrastructure — Inbound (REST)
```
TASK-3.1: Crear DTOs
  - [BianVerb][BusinessObject]Request.java en infrastructure/adapters/inbound/rest/dto/
    Con validaciones @NotNull, @NotBlank, @Pattern, @Size
  - [BianVerb][BusinessObject]Response.java
    Solo campos de salida

TASK-3.2: Crear Mapper REST (MapStruct)
  - [BianVerb][BusinessObject]RestMapper.java en infrastructure/adapters/inbound/rest/mapper/
    @Mapper(componentModel = "spring")
    toCommand(Request) → Command
    toResponse(DomainObject) → Response

TASK-3.3: Crear Controller REST
  - [BianVerb][BusinessObject]Controller.java en infrastructure/adapters/inbound/rest/
    @RestController
    @RequestMapping("/[service-domain]/[behavior-qualifier]")
    @Validated
    Inyección por constructor del UseCase
    Método con anotación HTTP correcta y @Valid en parámetro
    Delega al UseCase, retorna ResponseEntity<Response>
```

#### Grupo 4: Capa Infrastructure — Outbound (Persistencia)
```
TASK-4.1: Crear Entidad JPA
  - [BusinessObject]Entity.java en infrastructure/adapters/outbound/database/
    @Entity, @Table(name="[tabla]")
    @Id, @GeneratedValue(strategy = GenerationType.UUID o IDENTITY)
    @Column para cada campo
    Sin lógica de negocio

TASK-4.2: Crear JPA Repository
  - [BusinessObject]JpaRepository.java
    Extends JpaRepository<[BusinessObject]Entity, [IdType]>
    Métodos de consulta adicionales si se requieren

TASK-4.3: Crear Mapper JPA (MapStruct)
  - [BusinessObject]JpaMapper.java en infrastructure/adapters/outbound/database/mapper/
    @Mapper(componentModel = "spring")
    toEntity([BusinessObject]) → [BusinessObject]Entity
    toDomain([BusinessObject]Entity) → [BusinessObject]

TASK-4.4: Crear JPA Adapter
  - [BusinessObject]JpaAdapter.java en infrastructure/adapters/outbound/database/
    @Component
    Implements [BusinessObject]RepositoryPort
    Inyección por constructor de JpaRepository + Mapper
    Delegación completa, sin lógica de negocio

TASK-4.5: Crear adaptador externo (si hay servicios externos)
  - [ExternalService]WebClientAdapter.java
    Implements [ExternalService]Port
    Usar WebClient + Resilience4j CircuitBreaker
    Referencia: `spring-webclient-configurator`
```

#### Grupo 5: Manejo global de errores
```
TASK-5.1: Crear/actualizar GlobalExceptionHandler
  - GlobalExceptionHandler.java en infrastructure/config/
    @RestControllerAdvice
    Handler para cada excepción de dominio del spec
    Retorna ErrorResponse estandarizado con: status, code, message, timestamp
    Handler genérico para Exception (500 sin stack)
```

#### Grupo 6: Pruebas — Domain y Application
```
TASK-6.1: Tests unitarios del Aggregate
  - [BusinessObject]Test.java en src/test/.../domain/
    Test de constructor (happy path + valores inválidos)
    Test de cada método de comportamiento (happy path + excepciones)
    Test de invariantes

TASK-6.2: Tests unitarios de Application Service
  - [BianVerb][BusinessObject]ServiceTest.java en src/test/.../application/
    @ExtendWith(MockitoExtension.class)
    Mocks de todos los outbound ports
    Happy path: verifica resultado y verify() de interacciones
    Casos de error: cada excepción de dominio
```

#### Grupo 7: Pruebas — Infrastructure
```
TASK-7.1: Tests de Controller (Slice)
  - [BianVerb][BusinessObject]ControllerTest.java en src/test/.../infrastructure/
    @WebMvcTest([BianVerb][BusinessObject]Controller.class)
    @MockBean del UseCase
    Test HTTP 201/200 — body JSON correcto
    Test HTTP 400 — validación @Valid falla
    Test HTTP 404, 409, 422 — excepciones de dominio mapeadas

TASK-7.2: Tests de JPA Adapter (Slice)
  - [BusinessObject]JpaAdapterTest.java
    @DataJpaTest
    Test save() + findBy*() + existsBy*()
    Test caso not-found (Optional.empty())

TASK-7.3: Test de Integración (opcional — alta complejidad)
  - [BusinessObject]IntegrationTest.java
    @SpringBootTest
    @Testcontainers con @Container PostgreSQL
    Flujo completo: HTTP request → BD → HTTP response
    Al menos 1 criterio de aceptación end-to-end
```

#### Grupo 8: Configuración y OpenAPI
```
TASK-8.1: Configuración de la aplicación
  - application.yml / application.properties
    spring.datasource (con credenciales de entorno)
    logging.level
    springdoc.api-docs y swagger-ui si no existe

TASK-8.2: Migraciones de base de datos
  - src/main/resources/db/migration/V[N]__create_[tabla].sql
    CREATE TABLE con todos los campos
    Índices en columnas de búsqueda frecuente
    Verificar que flyway o liquibase esté en pom.xml; si no, agregar la dependencia.
```

> Los Grupos 0–8 aplican a `implementationType == new_microservice | new_feature | migration` con estructura hexagonal.
> Para `implementationType == new_feature_traditional`, usar los siguientes grupos en lugar de los grupos 1–8:

#### Grupo T1: Modelos y DTOs (tradicional)
```
TASK-T1.1: Crear/modificar entidad o modelo principal
  - Respetar el paquete donde viven las demás entidades del proyecto
  - Agregar campos requeridos por la HU

TASK-T1.2: Crear/modificar DTOs de request/response
  - Respetar naming conventions existentes (AccountDTO, AccountRequest, etc.)
  - Agregar validaciones @NotNull, @NotBlank según corresponda
```

#### Grupo T2: Repositorio (tradicional)
```
TASK-T2.1: Crear/modificar interface de repositorio
  - Respetar el paquete donde viven los demás repositorios
  - Extends JpaRepository (Spring) o PanacheRepositoryBase (Quarkus)

TASK-T2.2: Agregar métodos de consulta derivados
  - Métodos findBy*, existsBy*, countBy* según necesidades de la HU
```

#### Grupo T3: Servicio (tradicional)
```
TASK-T3.1: Crear/modificar interface de servicio (si el proyecto usa interfaces)
  - Solo si el proyecto tiene un patrón [NombreService] + [NombreServiceImpl]

TASK-T3.2: Implementar/modificar clase de servicio
  - Respetar el paquete y naming conventions del proyecto
  - Inyección por constructor (preferido) o seguir el patrón existente
  - @Service o @ApplicationScoped según el framework
```

#### Grupo T4: Controller (tradicional)
```
TASK-T4.1: Crear/modificar controller con endpoints
  - Respetar el prefijo de rutas que usa el proyecto (/api, /v1, etc.)
  - Seguir el naming del controller más cercano funcionalmente

TASK-T4.2: Agregar manejo de errores (@ControllerAdvice si no existe)
  - Verificar si ya existe un @RestControllerAdvice / @ControllerAdvice global
  - Si no existe, crear uno mínimo para los errores de esta HU
  - Si existe, agregar los handlers faltantes
```

#### Grupo T5: Tests (tradicional)
```
TASK-T5.1: Tests unitarios del servicio (Mockito)
  - [NombreService]Test con @ExtendWith(MockitoExtension.class)
  - Happy path + cada caso de error de negocio

TASK-T5.2: Tests del controller (@WebMvcTest o REST Assured)
  - [NombreController]Test: códigos HTTP + body esperado
  - Spring: @WebMvcTest | Quarkus: @QuarkusTest + REST Assured

TASK-T5.3: Tests del repositorio (@DataJpaTest, si aplica)
  - [NombreRepository]Test con @DataJpaTest
  - Caso encontrado + caso not-found para cada método personalizado
```

#### Grupo T6: Configuración (tradicional)
```
TASK-T6.1: application.yml/properties (si aplica)
  - Solo si la HU requiere nueva configuración (nuevas propiedades, datasource secundario, etc.)

TASK-T6.2: Flyway migration (si hay cambios de BD)
  - src/main/resources/db/migration/V[N]__[accion]_[tabla].sql
  - CREATE TABLE, ALTER TABLE, o INSERT de datos iniciales
```

### Paso 4 — Verificar cobertura de criterios de aceptación

Para cada criterio de aceptación del spec, verifica que al menos una tarea lo cubra:
```
CA-1: [descripción] → cubierto por TASK-X.X y TASK-Y.Y (tests en TASK-6.X)
CA-2: [descripción] → cubierto por TASK-X.X
...
```

Si algún CA no tiene cobertura, agrega la tarea faltante.

### Paso 5 — Calcular dependencias y estimación

```
Dependencias de tareas:
  TASK-1.x → no depende de nadie (primero en ejecutarse)
  TASK-2.x → depende de TASK-1.x
  TASK-2.4 → depende de TASK-2.3 (DomainConfig — siempre después de Application Services)
  TASK-3.x → depende de TASK-2.4
  TASK-4.x → depende de TASK-2.4 (paralelo con TASK-3.x)
  TASK-5.x → depende de TASK-3.x
  TASK-6.x → depende de TASK-1.x y TASK-2.x
  TASK-7.x → depende de TASK-3.x, TASK-4.x y TASK-6.x
  TASK-8.x → puede hacerse en paralelo con TASK-0.x

Estimación total (usar estimatedcomplexity del spec):
  BAJA:  2-4 hs
  MEDIA: 1-2 días
  ALTA:  3-5 días
```

---

## Output: Crear los artefactos del plan

Crea el directorio `.github/plans/HU-XXX/` y escribe dos archivos:

### Artefacto 1: `plan.md`

```markdown
# Plan de Implementación: HU-XXX — [Título]

**Tipo:** [Nuevo microservicio | Nueva feature | Migración]
**Agente de implementación:** [spring-engineer | quarkus-engineer | spring-to-quarkus]
**Complejidad:** [BAJA | MEDIA | ALTA]
**Estimación total:** [X hs / días]
**Spec aprobado:** .github/specs/HU-XXX.md

---

## Contexto técnico

| Parámetro | Valor |
|-----------|-------|
| BIAN Service Domain | [valor] |
| Business Object | [valor] |
| Base Package | [valor] |
| Microservice Name | [valor] |

---

## Cobertura de Criterios de Aceptación

| CA | Descripción | Tarea(s) | Tests |
|----|-------------|----------|-------|
| CA-1 | [descripción] | TASK-X.X | TASK-6.X / TASK-7.X |
| CA-2 | [descripción] | TASK-X.X | TASK-6.X / TASK-7.X |

---

## Tareas de Implementación

### Grupo 0: Scaffold (si aplica)
- [ ] TASK-0.1 — [descripción] (~ X min)

### Grupo 1: Domain Layer
- [ ] TASK-1.1 — Value Objects: [lista] (~ X min)
- [ ] TASK-1.2 — Aggregate Root: [BusinessObject] (~ X min)
- [ ] TASK-1.3 — Excepciones de dominio: [lista] (~ X min)
- [ ] TASK-1.4 — Domain Events: [lista] (~ X min, si aplica)

### Grupo 2: Application Layer
- [ ] TASK-2.1 — Inbound Ports: [lista de UseCases] (~ X min)
- [ ] TASK-2.2 — Outbound Ports: [lista] (~ X min)
- [ ] TASK-2.3 — Application Services: [lista] (~ X min)
- [ ] TASK-2.4 — DomainConfig.java: registrar servicios como @Bean (~ X min)

### Grupo 3: Infrastructure — REST
- [ ] TASK-3.1 — DTOs: [Request/Response] (~ X min)
- [ ] TASK-3.2 — Mapper REST: [nombre] (~ X min)
- [ ] TASK-3.3 — Controller: [nombre] (~ X min)

### Grupo 4: Infrastructure — Persistencia
- [ ] TASK-4.1 — Entity JPA: [BusinessObject]Entity (~ X min)
- [ ] TASK-4.2 — JPA Repository: [nombre] (~ X min)
- [ ] TASK-4.3 — Mapper JPA: [nombre] (~ X min)
- [ ] TASK-4.4 — JPA Adapter: [nombre] (~ X min)
- [ ] TASK-4.5 — WebClient Adapter: [nombre] (~ X min, si aplica)

### Grupo 5: Error Handling
- [ ] TASK-5.1 — GlobalExceptionHandler (~ X min)

### Grupo 6: Tests — Domain y Application
- [ ] TASK-6.1 — [BusinessObject]Test (~ X min)
- [ ] TASK-6.2 — [BianVerb][BusinessObject]ServiceTest (~ X min)

### Grupo 7: Tests — Infrastructure
- [ ] TASK-7.1 — [BianVerb][BusinessObject]ControllerTest (@WebMvcTest) (~ X min)
- [ ] TASK-7.2 — [BusinessObject]JpaAdapterTest (@DataJpaTest) (~ X min)
- [ ] TASK-7.3 — [BusinessObject]IntegrationTest (si aplica) (~ X min)

### Grupo 8: Configuración
- [ ] TASK-8.1 — application.yml (~ X min)
- [ ] TASK-8.2 — Flyway migration V[N]__... (~ X min)

---

## Orden de ejecución recomendado

```
TASK-0.1 →
  TASK-1.1 → TASK-1.2 → TASK-1.3 → TASK-1.4 →
    TASK-2.1 → TASK-2.2 → TASK-2.3 → TASK-2.4 →
      TASK-3.1 → TASK-3.2 → TASK-3.3 ──┐
      TASK-4.1 → TASK-4.2 → TASK-4.3 → TASK-4.4 ──┤
                                                    TASK-5.1 →
    TASK-6.1 → TASK-6.2 ──────────────────────────────────────────┐
    TASK-7.1 → TASK-7.2 → TASK-7.3 (si aplica) ──────────────────┘
  TASK-8.1 + TASK-8.2 (paralelo con lo anterior)
```

---

## Archivos a crear/modificar

> Para `new_microservice`: todos los archivos son CREAR.
> Para `new_feature`: usar CREAR, MODIFICAR o REUSAR según el análisis del Paso 2b.

| Archivo | Capa | Tipo (`new_microservice` / `new_feature`) |
|---------|------|------------------------------------------|
| `src/main/java/[basePackage]/domain/model/[BusinessObject].java` | domain | CREAR / CREAR\|MODIFICAR |
| `src/main/java/[basePackage]/domain/model/[ValueObject].java` | domain | CREAR / CREAR\|REUSAR |
| `src/main/java/[basePackage]/domain/exception/[...]Exception.java` | domain | CREAR / CREAR |
| `src/main/java/[basePackage]/application/ports/inbound/[...]UseCase.java` | application | CREAR / CREAR |
| `src/main/java/[basePackage]/application/ports/outbound/[...]Port.java` | application | CREAR / CREAR\|MODIFICAR |
| `src/main/java/[basePackage]/application/service/[...]Service.java` | application | CREAR / CREAR |
| `src/main/java/[basePackage]/infrastructure/adapters/inbound/rest/[...]Controller.java` | infra | CREAR / CREAR |
| `src/main/java/[basePackage]/infrastructure/adapters/inbound/rest/dto/[...]Request.java` | infra | CREAR / CREAR |
| `src/main/java/[basePackage]/infrastructure/adapters/inbound/rest/dto/[...]Response.java` | infra | CREAR / CREAR |
| `src/main/java/[basePackage]/infrastructure/adapters/inbound/rest/mapper/[...]RestMapper.java` | infra | CREAR / CREAR\|MODIFICAR |
| `src/main/java/[basePackage]/infrastructure/adapters/outbound/database/[...]Entity.java` | infra | CREAR / MODIFICAR |
| `src/main/java/[basePackage]/infrastructure/adapters/outbound/database/[...]JpaRepository.java` | infra | CREAR / MODIFICAR |
| `src/main/java/[basePackage]/infrastructure/adapters/outbound/database/mapper/[...]JpaMapper.java` | infra | CREAR / MODIFICAR |
| `src/main/java/[basePackage]/infrastructure/adapters/outbound/database/[...]JpaAdapter.java` | infra | CREAR / MODIFICAR |
| `src/main/java/[basePackage]/infrastructure/config/GlobalExceptionHandler.java` | infra | CREAR / MODIFICAR |
| `src/main/resources/db/migration/V[N]__[accion]_[tabla].sql` | config | CREAR / CREAR |
| `src/test/java/.../domain/[BusinessObject]Test.java` | test | CREAR / CREAR\|MODIFICAR |
| `src/test/java/.../application/[...]ServiceTest.java` | test | CREAR / CREAR |
| `src/test/java/.../infrastructure/[...]ControllerTest.java` | test | CREAR / CREAR |
| `src/test/java/.../infrastructure/[...]JpaAdapterTest.java` | test | CREAR / CREAR\|MODIFICAR |
```

### Artefacto 2: `tasks.json`

```json
{
  "huKey": "HU-XXX",
  "title": "[título]",
  "implementationType": "new_microservice|new_feature|new_feature_traditional|migration",
  "implementationAgent": "spring-engineer|quarkus-engineer|spring-to-quarkus",
  "projectStructure": "new|hexagonal|traditional|mixed",
  "framework": "spring-boot|quarkus|unknown",
  "bianServiceDomain": "[valor]",
  "businessObject": "[valor]",
  "behaviorQualifier": "[valor]",
  "bianVerb": "[valor]",
  "basePackage": "[valor]",
  "microserviceName": "[valor]",
  "estimatedComplexity": "baja|media|alta",
  "specFile": ".github/specs/HU-XXX.md",
  "status": "plan_approved",
  "tasks": [
    {
      "id": "TASK-1.1",
      "group": "domain",
      "action": "CREAR|MODIFICAR|REUSAR",
      "name": "Crear Value Objects",
      "description": "Crear [lista de Value Objects] como Java records en domain/model/",
      "existingFile": null,
      "files": ["domain/model/[ValueObject].java"],
      "dependsOn": [],
      "estimateMin": 15,
      "status": "pending",
      "startedAt": null,
      "completedAt": null,
      "acceptanceCriteria": ["CA-1"]
    },
    {
      "id": "TASK-1.2",
      "group": "domain",
      "action": "CREAR|MODIFICAR|REUSAR",
      "name": "Crear Aggregate Root: [BusinessObject]",
      "description": "Implementar [BusinessObject] con constructor builder, métodos de negocio e invariantes",
      "existingFile": "src/main/java/.../[BusinessObject].java",
      "files": ["domain/model/[BusinessObject].java"],
      "dependsOn": ["TASK-1.1"],
      "estimateMin": 30,
      "status": "pending",
      "startedAt": null,
      "completedAt": null,
      "acceptanceCriteria": ["CA-1", "CA-2"]
    }
  ],
  "createdAt": "[timestamp ISO 8601]",
  "specApprovedAt": "[timestamp ISO 8601]",
  "planApprovedAt": null
}

// NOTA: Todas las tareas generadas deben incluir:
// "status": "pending", "startedAt": null, "completedAt": null
// Esto permite al sistema de reanudación detectar exactamente
// dónde se interrumpió el flujo.
```

Después de escribir ambos archivos, actualiza el metadata:
```python
import json, datetime
# HU_KEY = clave real de la HU (ej: "SCRUM-5"), del contexto de PASO 0
meta_path = f'.github/specs/.metadata/{HU_KEY}.json'
meta = json.load(open(meta_path))
meta['status'] = 'plan_generated'
meta['plan_file'] = f'.github/plans/{HU_KEY}/plan.md'
meta['tasks_file'] = f'.github/plans/{HU_KEY}/tasks.json'
meta['plan_generated_at'] = datetime.datetime.now().isoformat()
with open(meta_path, 'w') as f:
    json.dump(meta, f, indent=2, ensure_ascii=False)
```

Cuando el usuario **apruebe el plan** (Checkpoint 2), actualizar:
```python
meta['status'] = 'plan_approved'
meta['plan_approved_at'] = datetime.datetime.now().isoformat()
# También actualizar tasks.json:
data = json.load(open(f'.github/plans/{HU_KEY}/tasks.json'))
data['planApprovedAt'] = datetime.datetime.now().isoformat()
data['status'] = 'plan_approved'
with open(f'.github/plans/{HU_KEY}/tasks.json', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
```
