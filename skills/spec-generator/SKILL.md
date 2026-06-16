---
name: spec-generator
description: Enriquece el spec base generado por getJiraIssueDetails (Atlassian MCP) con análisis técnico completo — modelo DDD, puertos hexagonales, endpoints BIAN, pruebas requeridas y riesgos.
---

# Skill: Spec Generator (Enriquecimiento Técnico)

## Propósito

Transformar el spec base (generado desde JIRA vía `getJiraIssueDetails` de Atlassian MCP) en un spec técnico completo que sirva de contrato de implementación. El agente ejecuta este skill **antes** de mostrar el spec al usuario para aprobación.

## Cuándo ejecutar

Inmediatamente después de que Stive recibe el response de `getJiraIssueDetails` y escribe `.github/specs/HU-XXX.md`. El spec base contiene el "qué"; este skill agrega el "cómo".

---

## Proceso paso a paso

### Paso 0 — Leer contexto del proyecto

Antes de analizar el spec, leer del metadata de la HU (`.github/specs/.metadata/HU-XXX.json`):

> **Convención:** en todos los bloques de código de este skill, `HU_KEY` es la clave real
> de la HU (ej. `SCRUM-5`), conocida del contexto de PASO 0. Donde aparezca `HU-XXX` en prosa,
> sustituir por esa clave.

```python
import json
# HU_KEY = clave real de la HU (ej: "SCRUM-5"), del contexto de PASO 0
meta = json.load(open(f'.github/specs/.metadata/{HU_KEY}.json'))
PROJECT_STRUCTURE = meta.get('projectStructure', 'new')   # new | hexagonal | traditional | mixed
FRAMEWORK = meta.get('framework', 'spring-boot')           # spring-boot | quarkus | unknown
BASE_PACKAGE = meta.get('detectedBasePackage', '')
```

Según `projectStructure`, el skill bifurca:

| `projectStructure` | Flujo a seguir |
|---|---|
| `new` | Ejecutar Pasos 1–8 + output DDD/BIAN (flujo estándar, sin inventario previo) |
| `hexagonal` | Ejecutar **Paso 0b** (inventario de código existente) → Pasos 1–8 + output DDD/BIAN con CREAR/MODIFICAR/REUSAR |
| `traditional` | Ejecutar Pasos 1–2 para extraer datos de la HU + output formato tradicional (ver sección al final) |
| `mixed` | Analizar qué partes del proyecto son hexagonales y cuáles tradicionales; aplicar el enfoque correspondiente a cada componente identificado |

---

### Paso 0b — Inventario de código existente (solo `projectStructure == "hexagonal"`)

Antes de diseñar el spec, leer el código actual para saber qué existe y no proponer crear algo que ya está. Usar los paths hexagonales del metadata:

```python
import json
meta = json.load(open(f'.github/specs/.metadata/{HU_KEY}.json'))
HEX_DOMAIN   = meta.get('hexDomainDir', 'domain')
HEX_PORTS    = meta.get('hexPortsDir', 'ports')
HEX_ADAPTERS = meta.get('hexAdaptersDir', 'adapters')
BASE_PKG_PATH = BASE_PACKAGE.replace('.', '/')
```

```bash
echo "=== Inventario de código existente ==="

# Aggregate Roots existentes (clases en domain/ sin @Entity y sin interfaces)
echo "-- Aggregate Roots / Entidades de dominio:"
find src/main/java -path "*/${HEX_DOMAIN}*" -name "*.java" 2>/dev/null | \
  grep -v "Exception\|Event\|Test" | xargs grep -l "class " 2>/dev/null

# Value Objects (records o clases final sin @Entity)
echo "-- Value Objects:"
find src/main/java -path "*/${HEX_DOMAIN}*" -name "*.java" 2>/dev/null | \
  xargs grep -l "^public record\|^public final class" 2>/dev/null

# Inbound Ports (UseCase interfaces)
echo "-- Inbound Ports (UseCases):"
find src/main/java -path "*/${HEX_PORTS}*" -name "*UseCase.java" 2>/dev/null
find src/main/java -path "*/inbound*" -name "*UseCase.java" 2>/dev/null

# Outbound Ports
echo "-- Outbound Ports:"
find src/main/java -path "*/${HEX_PORTS}*" -name "*Port.java" -o -path "*/outbound*" -name "*Port.java" 2>/dev/null

# Application Services existentes
echo "-- Application Services:"
find src/main/java -path "*/application*" -name "*Service*.java" -o -path "*/application*" -name "*UseCase*.java" 2>/dev/null | grep -v test

# Controllers existentes
echo "-- Controllers / REST Adapters:"
find src/main/java -path "*/${HEX_ADAPTERS}*" -name "*Controller*.java" -o -name "*Resource*.java" 2>/dev/null | grep -v test

# Excepciones de dominio existentes
echo "-- Excepciones de dominio:"
find src/main/java -path "*/${HEX_DOMAIN}*" -name "*Exception.java" 2>/dev/null
```

Con este inventario, construir la tabla de contexto para el spec:

```
INVENTARIO EXISTENTE:
| Clase | Tipo | Ubicación |
|-------|------|-----------|
| [NombreClase].java | AggregateRoot / ValueObject / InboundPort / OutboundPort / AppService / Controller / Exception | [path] |
```

Esta tabla se usa en los Pasos 3–6 para marcar cada artefacto como **CREAR**, **MODIFICAR** o **REUSAR** en vez de asumir que todo es nuevo.

---

### Paso 1 — Leer y analizar el spec base

Lee `.github/specs/HU-XXX.md` completamente. Extrae:
- Título de la HU
- Historia "Como... Quiero... Para..."
- Criterios de aceptación (CA-X)
- Requisitos funcionales inferidos

Consulta `docs/architecture.md` para recordar convenciones BIAN, DDD y estructura de paquetes.

---

### Paso 2 — Determinar contexto BIAN y DDD

A partir del título, descripción y criterios de aceptación, determina:

| Metadata | Cómo determinarlo |
|---|---|
| `bianservicedomain` | Service Domain BIAN en PascalCase (AccountManagement, PaymentExecution, CustomerRelationship) |
| `businessobject` | Aggregate Root principal (Account, Payment, Customer) |
| `behaviorqualifier` | Sub-entidad o qualifier de la operación (AccountBalance, PaymentStatus) |
| `bianverb` | Verbo principal: Initiate, Execute, Request, Update, Retrieve |
| `basepackage` | `com.jotace.<serviceDomain en minúscula>` ej. `com.jotace.accountmanagement` |
| `microservicename` | kebab-case del servicio ej. `account-management-service` |
| `estimatedcomplexity` | baja \| media \| alta |

---

### Paso 3 — Diseñar modelo de dominio DDD

#### Aggregate Root principal

Identifica el objeto central de la HU:

```
Nombre: [BusinessObject] — PascalCase, sustantivo singular
Identidad: campo único que lo identifica (ej. accountNumber, paymentId)
Estado: campos que representan su estado interno (ej. status, balance, type)
Comportamiento: métodos de negocio — verbos, con lógica, no solo getters
  ej. initiate(), deposit(Money amount), withdraw(Money amount), close()
Invariantes: reglas que SIEMPRE deben cumplirse (validar en métodos del aggregate)
  ej. "El balance no puede ser negativo", "No se puede cerrar una cuenta activa con saldo"
```

#### Value Objects

Objetos inmutables que se definen por sus atributos, sin identidad propia:

```
Preferir Java record
Validar en el constructor (Objects.requireNonNull, rangos, patrones)
Ej: Money(BigDecimal amount, String currency), AccountNumber(String value), AccountType(enum)
```

#### Excepciones de Dominio

Por cada error de negocio identificado en los criterios de aceptación:

```
[BusinessObject]NotFoundException        → HTTP 404 → ERROR_CODE: [BUSINESS_OBJECT]_NOT_FOUND
[BusinessObject]AlreadyExistsException   → HTTP 409 → ERROR_CODE: [BUSINESS_OBJECT]_ALREADY_EXISTS
Invalid[BusinessObject]StateException    → HTTP 422 → ERROR_CODE: INVALID_[BUSINESS_OBJECT]_STATE
[BusinessObject]ValidationException      → HTTP 400 → ERROR_CODE: [BUSINESS_OBJECT]_VALIDATION_ERROR
```

Todas extienden de `RuntimeException`. Son capturadas por `@RestControllerAdvice`.

#### Domain Events (si aplica)

```
Nombre en pasado: [BusinessObject][AcciónPasada]Event
  ej. AccountInitiatedEvent, MoneyDepositedEvent
Se registran en el aggregate, se publican después de persistir (patrón outbox o ApplicationEvent)
Transportan datos inmutables del aggregate al momento del evento
```

---

### Paso 4 — Definir puertos hexagonales

#### Inbound Ports — `application/ports/inbound/`

Por cada criterio de aceptación o acción BIAN:

```java
// Nombre: [BianVerb][BusinessObject]UseCase
public interface InitiateAccountUseCase {
    Account execute(InitiateAccountCommand command);
}

// Comando (record inmutable — datos del cliente al caso de uso)
public record InitiateAccountCommand(
    String customerId,
    AccountType accountType,
    String currency
) {}
```

Regla: los commands y queries son records inmutables. Solo tipos del dominio, sin DTOs.

#### Outbound Ports — `application/ports/outbound/`

```java
public interface AccountRepositoryPort {
    Account save(Account account);
    Optional<Account> findByAccountNumber(AccountNumber accountNumber);
    List<Account> findByCustomerId(String customerId);
    boolean existsByAccountNumber(AccountNumber accountNumber);
}

// Si hay dependencias externas (otro microservicio):
public interface CustomerServicePort {
    boolean customerExists(String customerId);
}
```

---

### Paso 5 — Definir adaptadores REST

Por cada inbound port, el endpoint BIAN correspondiente:

```
Endpoint: [HTTP_METHOD] /[service-domain]/[behavior-qualifier]/[bianverb]
  Ej: POST /account-management/account-balance/initiate
      GET  /account-management/account-balance/retrieve/{accountNumber}

Controller: [BianVerb][BusinessObject]Controller
  @RestController
  @RequestMapping("/[service-domain]/[behavior-qualifier]")
  Inyección por constructor del inbound port

DTOs (en infrastructure/adapters/inbound/rest/dto/):
  [BianVerb][BusinessObject]Request — entrada con @Valid, @NotNull, @NotBlank, @Pattern
  [BianVerb][BusinessObject]Response — salida JSON

Mapper MapStruct (en infrastructure/adapters/inbound/rest/mapper/):
  toCommand(Request) → Command
  toResponse(DomainObject) → Response
  
Códigos HTTP a cubrir:
  201 / 200 — operación exitosa
  400 — validación de entrada fallida (@Valid)
  404 — recurso no encontrado
  409 — conflicto / duplicado
  422 — estado de negocio inválido
  500 — error interno (no exponer stack)
```

---

### Paso 6 — Definir adaptadores de persistencia

```
Entidad JPA (en infrastructure/adapters/outbound/database/):
  [BusinessObject]Entity
    @Entity, @Table(name="[tabla_snake_case]")
    @Id, @GeneratedValue, @Column
    Sin lógica de negocio

Repositorio Spring Data:
  [BusinessObject]JpaRepository extends JpaRepository<[BusinessObject]Entity, [IdType]>
  Métodos de consulta derivados según los métodos del outbound port

Adapter (implementa el outbound port):
  [BusinessObject]JpaAdapter implements [BusinessObject]RepositoryPort
    @Component, inyección por constructor
    usa JpaRepository + Mapper para traducir entidades ↔ dominio

Mapper MapStruct (en infrastructure/adapters/outbound/database/mapper/):
  [BusinessObject]JpaMapper
    toEntity([BusinessObject]) → [BusinessObject]Entity
    toDomain([BusinessObject]Entity) → [BusinessObject]
```

---

### Paso 7 — Identificar pruebas requeridas

```
UNITARIAS (domain/ y application/):
  [BusinessObject]Test
    - Constructor: validaciones e invariantes
    - Cada método de comportamiento: happy path + errores
    - Cobertura de todas las ramas del aggregate
  
  [BianVerb][BusinessObject]UseCaseTest
    - Happy path con datos válidos
    - Cada excepción de dominio posible
    - Verificar interacciones con outbound ports (Mockito verify)

SLICE TESTS (infrastructure/):
  [BianVerb][BusinessObject]ControllerTest (@WebMvcTest)
    - HTTP 201/200 — body JSON correcto
    - HTTP 400 — validación @Valid
    - HTTP 404, 409, 422 — manejo de excepciones de dominio
    - Usar @MockBean del inbound port

  [BusinessObject]JpaAdapterTest (@DataJpaTest)
    - save(): persistir y recuperar
    - findBy*(): búsquedas, incluido caso not-found

INTEGRACIÓN (opcional, @SpringBootTest + Testcontainers):
  [BusinessObject]IntegrationTest
    - Flujo completo para el criterio de aceptación más crítico
```

---

### Paso 8 — Análisis de riesgos y estimación

```
Riesgos a evaluar:
- ¿Dependencias de otros microservicios? → WebClient + outbound port externo + mock en tests
- ¿Lógica de negocio compleja? → más tests de dominio, validar invariantes
- ¿Transacciones distribuidas? → evaluar SAGA pattern o eventos de dominio
- ¿Datos sensibles? → encriptar en BD, nunca loggear
- ¿Alto volumen? → índices en BD, paginación en endpoints Retrieve

Complejidad:
  BAJA: 1 aggregate, 1-2 casos de uso, sin dependencias externas → ~2-4 hs
  MEDIA: 2-3 aggregates, 3-5 casos de uso, 1 dependencia externa → ~1-2 días
  ALTA: múltiples aggregates, >5 casos de uso, transacciones distribuidas → >2 días
```

---

## Output: Spec técnico completo

Reescribe `.github/specs/HU-XXX.md` reemplazando el contenido con el spec enriquecido usando el siguiente formato. Añade el frontmatter al inicio (requerido por otros skills):

```markdown
---
bianservicedomain: [valor]
businessobject: [valor]
behaviorqualifier: [valor]
bianverb: [valor]
basepackage: [valor]
microservicename: [valor]
estimatedcomplexity: [baja|media|alta]
---

# HU-XXX

## Título
[de JIRA]

## Descripción
**Como:** [rol]
**Quiero:** [acción]
**Para:** [beneficio]

## Criterios de aceptación
### CA-1: [título]
- [item]
- [item]

## Requisitos funcionales
1. [requisito]
2. [requisito]

## Requisitos no funcionales
- **Performance:** respuesta < Xms bajo carga normal
- **Seguridad:** validación de entrada, errores sin exponer stack, nunca loggear datos sensibles
- **Observabilidad:** logging de entrada/salida en cada caso de uso, trazabilidad con IDs de correlación
- **Mantenibilidad:** dominio puro, cobertura ≥ 95%, zero warnings de compilación

## Inventario de artefactos (`projectStructure == "hexagonal"` únicamente)

> Omitir esta sección si `projectStructure == "new"`.

| Artefacto | Clase | Acción | Justificación |
|-----------|-------|--------|---------------|
| Aggregate Root | [NombreClase].java | CREAR / MODIFICAR / REUSAR | [motivo] |
| Value Object | [NombreClase].java | CREAR / MODIFICAR / REUSAR | [motivo] |
| Inbound Port | [NombreUseCase].java | CREAR / MODIFICAR / REUSAR | [motivo] |
| Outbound Port | [NombrePort].java | CREAR / MODIFICAR / REUSAR | [motivo] |
| Application Service | [NombreService].java | CREAR / MODIFICAR / REUSAR | [motivo] |
| Controller | [NombreController].java | CREAR / MODIFICAR / REUSAR | [motivo] |
| JPA Entity | [NombreEntity].java | CREAR / MODIFICAR / REUSAR | [motivo] |
| JPA Adapter | [NombreAdapter].java | CREAR / MODIFICAR / REUSAR | [motivo] |

## Modelo de Dominio DDD

### Aggregate Root: [BusinessObject]
| Campo | Tipo Java | Descripción |
|-------|-----------|-------------|
| [id] | [tipo] | Identidad única |
| [campo] | [tipo] | [descripción] |

**Comportamiento:**
- `[método]([params]): [retorno]` — [qué hace]

**Invariantes:**
- [regla de negocio]

### Value Objects
| Nombre | Tipo Java | Campos | Validaciones |
|--------|-----------|--------|--------------|
| [nombre] | record | [campos] | [validaciones en constructor] |

### Excepciones de Dominio
| Clase | HTTP Status | Código de Error |
|-------|-------------|-----------------|
| [nombre] | [XXX] | [ERROR_CODE] |

### Domain Events
| Evento | Cuándo | Datos transportados |
|--------|--------|---------------------|
| [nombre] | [cuándo] | [campos] |

## Puertos Hexagonales

### Inbound Ports
```java
// [BianVerb][BusinessObject]UseCase
[ReturnType] execute([BianVerb][BusinessObject]Command command);

// Command
record [BianVerb][BusinessObject]Command([params]) {}
```

### Outbound Ports
```java
// [BusinessObject]RepositoryPort
[BusinessObject] save([BusinessObject] obj);
Optional<[BusinessObject]> findBy[Id]([IdType] id);
```

## Adaptadores REST

### [BianVerb][BusinessObject]Controller
```
[HTTP_METHOD] /[service-domain]/[behavior-qualifier]/[bianverb]

Request: [BianVerb][BusinessObject]Request { [campos con validaciones] }
Response: [BianVerb][BusinessObject]Response { [campos] }

HTTP codes: 201/200, 400, 404, 409, 422, 500
```

## Adaptadores de Persistencia

### [BusinessObject]Entity
```
Tabla: [nombre_tabla]
JPA: @Entity, @Table, @Id, @GeneratedValue, @Column
```

## Pruebas Requeridas

### Unitarias
- `[BusinessObject]Test` — invariantes y comportamientos del aggregate
- `[BianVerb][BusinessObject]UseCaseTest` — casos de uso con mocks

### Slice Tests
- `[BianVerb][BusinessObject]ControllerTest` (@WebMvcTest) — HTTP 200, 400, 404, 409, 422
- `[BusinessObject]JpaAdapterTest` (@DataJpaTest) — CRUD y búsquedas

### Integración
- `[BusinessObject]IntegrationTest` (@SpringBootTest + Testcontainers)

## Análisis de Riesgos

| Riesgo | Prob. | Mitigación |
|--------|-------|------------|
| [riesgo] | Alta/Media/Baja | [mitigación] |

## Estimación de Complejidad

**[BAJA/MEDIA/ALTA]** — [justificación breve]

## Definición de terminado (DoD)

- [ ] Spec técnico aprobado por el desarrollador
- [ ] Aggregate Root + Value Objects + Excepciones en `domain/`
- [ ] Inbound + Outbound Ports en `application/ports/`
- [ ] Application Service en `application/service/`
- [ ] REST Controller + DTOs + Mapper en `infrastructure/adapters/inbound/`
- [ ] JPA Entity + Adapter + Mapper en `infrastructure/adapters/outbound/`
- [ ] Tests unitarios con cobertura ≥ 95%
- [ ] Tests slice para controller y JPA
- [ ] Dominio libre de imports Spring/JPA/Jackson
- [ ] APIs BIAN-compliant verificadas
- [ ] PR creado con descripción completa
```

---

## Output: Spec técnico — Proyecto Tradicional

Usar cuando `projectStructure == "traditional"`. Reemplaza el spec base con este formato:

```markdown
---
projectstructure: traditional
framework: [spring-boot|quarkus]
basepackage: [valor detectado]
entityname: [Entidad principal en PascalCase]
servicename: [NombreService]
estimatedcomplexity: [baja|media|alta]
---

# HU-XXX

## Título
[de JIRA]

## Descripción
**Como:** [rol]
**Quiero:** [acción]
**Para:** [beneficio]

## Criterios de aceptación
### CA-1: [título]
- [item]

## Requisitos funcionales
1. [requisito]

## Diseño técnico

### Entidades / Modelos afectados
| Clase | Paquete actual | Acción | Cambio |
|-------|---------------|--------|--------|
| [Entity].java | [paquete] | CREAR/MODIFICAR/REUSAR | [descripción] |
| [DTO].java | [paquete] | CREAR/MODIFICAR/REUSAR | [descripción] |

### Servicios
| Clase | Método nuevo/modificado | Descripción |
|-------|------------------------|-------------|
| [NombreService] | [método(params): tipo] | [qué hace] |

### Repositorios
| Interfaz | Método nuevo/modificado | Descripción |
|----------|------------------------|-------------|
| [NombreRepository] | [método(params): tipo] | [qué busca/guarda] |

### Endpoints REST
| HTTP | Path | Request | Response | Códigos |
|------|------|---------|----------|---------|
| POST | /api/[recurso] | [campos] | [campos] | 201, 400, 409 |
| GET | /api/[recurso]/{id} | — | [campos] | 200, 404 |

### Validaciones de entrada
- `[campo]`: [regla] — error si [condición]

### Errores esperados
| Caso | HTTP | Mensaje sugerido |
|------|------|-----------------|
| [recurso] no encontrado | 404 | "[Entity] not found: {id}" |
| [recurso] ya existe | 409 | "[Entity] already exists: {id}" |
| Entrada inválida | 400 | "Validation failed: {campo}" |

## Pruebas requeridas

### Unitarias (Mockito)
- `[NombreService]Test` — [método]: happy path + cada error de negocio

### Controller / Integration
- `[NombreController]Test` — [HTTP] [path] → [código] + body esperado

### Repository (si aplica)
- `[NombreRepository]Test` (@DataJpaTest) — [método]: caso encontrado + caso not-found

## Análisis de riesgos

| Riesgo | Prob. | Mitigación |
|--------|-------|------------|
| [riesgo] | Alta/Media/Baja | [mitigación] |

## Estimación
**[BAJA/MEDIA/ALTA]** — [justificación breve]

## DoD
- [ ] Spec aprobado por el desarrollador
- [ ] Entidades/modelos creados o modificados
- [ ] Servicios implementados y testeados
- [ ] Endpoints funcionando con códigos HTTP correctos
- [ ] Tests unitarios con cobertura ≥ 80%
- [ ] Tests de controller pasando
- [ ] PR creado
```
