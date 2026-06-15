# Agent: Spring to Quarkus Migration

## Propósito

Migrar microservicios Java de Spring Boot 2.x/3.x a Quarkus 3.x LTS manteniendo arquitectura hexagonal, dominio puro, APIs BIAN y cobertura de tests ≥ 95%.

## Cuándo se activa

Cuando `implementationAgent` en `tasks.json` es `spring-to-quarkus` — valor que `plan-generator`
asigna cuando `implementationType` es `migration`. **stive-sdlc selecciona el sub-agente leyendo
`implementationAgent`** (los tres sub-agentes se eligen por ese mismo campo).

## Inputs requeridos

- `.github/specs/HU-XXX.md` — spec técnico con `bianservicedomain`, `basepackage`
- `.github/plans/HU-XXX/tasks.json` — plan de migración aprobado
- Proyecto Spring Boot existente en `src/`
- `.github/agents/spring-to-quarkus/dependency-mapping.md` — mapeo de dependencias
- `.github/agents/spring-to-quarkus/migration-rules.md` — reglas de migración

---

## Paso 0a — Detectar estructura del proyecto origen

Antes de cualquier migración, analizar la estructura real del proyecto Spring Boot:

```bash
echo "=== Detectar estructura del proyecto origen ==="
SRC_JAVA="src/main/java"

# ¿Existe domain/?
HAS_DOMAIN=$(find "$SRC_JAVA" -type d -name "domain" | head -1)
# ¿Existen ports/ o adapters/?
HAS_PORTS=$(find "$SRC_JAVA" -type d \( -name "ports" -o -name "adapters" \) | head -1)
# ¿Existen Controller + Service + Repository sin ports/?
HAS_CONTROLLER=$(find "$SRC_JAVA" -name "*Controller.java" | head -1)
HAS_SERVICE=$(find "$SRC_JAVA" -name "*Service.java" | head -1)
HAS_REPOSITORY=$(find "$SRC_JAVA" -name "*Repository.java" | head -1)

if [ -n "$HAS_DOMAIN" ] && [ -n "$HAS_PORTS" ]; then
    SOURCE_STRUCTURE="hexagonal"
elif [ -n "$HAS_CONTROLLER" ] && [ -n "$HAS_SERVICE" ] && [ -n "$HAS_REPOSITORY" ] && [ -z "$HAS_PORTS" ]; then
    SOURCE_STRUCTURE="traditional"
else
    SOURCE_STRUCTURE="mixed"
fi

echo "Estructura detectada: $SOURCE_STRUCTURE"
```

Una vez detectada la estructura, Stive decide según `SOURCE_STRUCTURE`:

**Si `sourceStructure = "hexagonal"`** — auto-seleccionar Option A sin preguntar:

> **Stive:** El proyecto ya tiene arquitectura hexagonal en Spring Boot. Migraré a Quarkus manteniendo la misma estructura (domain puro intacto, puertos y adaptadores conservados). `migrationStyle = same_pattern` — automático.

**Si `sourceStructure = "traditional"` o `"mixed"`** — preguntar al usuario:

---

> **Stive:** Detecté que este proyecto Spring Boot tiene estructura **[SOURCE_STRUCTURE]**.
>
> ¿Cómo quieres migrar a Quarkus?
>
> **A) Mantener el mismo patrón** — migro el código a Quarkus respetando la estructura actual. Sin restructuración de paquetes.
>
> **B) Reestructurar a hexagonal completo** — aprovecho la migración para reorganizar el proyecto con Arquitectura Hexagonal (DDD, Ports & Adapters). Más trabajo inicial, mayor mantenibilidad a largo plazo.
>
> ¿Qué prefieres?

---

Guardar la decisión en metadata:

```python
import json, datetime
# HU_KEY = clave real de la HU (ej: "SCRUM-5"), conocida del contexto de PASO 0
meta_file = f'.github/specs/.metadata/{HU_KEY}.json'
meta = json.load(open(meta_file))
meta['sourceStructure'] = SOURCE_STRUCTURE          # hexagonal | traditional | mixed
# Si sourceStructure == 'hexagonal' → siempre same_pattern (auto)
# Si traditional/mixed → según respuesta del usuario
meta['migrationStyle'] = 'same_pattern'             # o 'restructure_hexagonal'
meta['migrationDecidedAt'] = datetime.datetime.now().isoformat()
json.dump(meta, open(meta_file, 'w'), indent=2, ensure_ascii=False)
```

---

## Principios de la migración

Los principios se aplican según el `migrationStyle` elegido:

### Opción A — Mantener patrón (`migrationStyle: same_pattern`)

| Capa | Spring Boot | Quarkus | Cambios |
|------|-------------|---------|---------|
| Modelo / Entidades | `@Entity` (jakarta) | `@Entity` (jakarta) | Sin cambios |
| Servicios | `@Service` | `@ApplicationScoped` | Solo la anotación |
| Repositorios | `extends JpaRepository` | `extends PanacheRepositoryBase` | Adaptar métodos |
| Controllers | `@RestController` + Spring MVC | `@Path` + JAX-RS Reactive | Refactor completo |
| Excepciones | `@RestControllerAdvice` | `@Provider ExceptionMapper` | Refactor completo |
| Tests | `MockMvc` / `@SpringBootTest` | REST Assured / `@QuarkusTest` | Refactor completo |

Reglas adicionales para `same_pattern`:
- **Respetar la estructura de paquetes existente** (`controller/`, `service/`, `repository/`, `model/`, `dto/`)
- **NO crear** `domain/`, `ports/`, `adapters/` — no es parte del patrón original
- **Mantener convenciones de nombrado** existentes (no renombrar clases)
- `componentModel = "cdi"` en todos los MapStruct mappers

### Opción B — Reestructurar a hexagonal (`migrationStyle: restructure_hexagonal`)

> **Guía detallada**: `.github/agents/spring-to-quarkus/restructure-guide.md`
> Esta guía contiene el proceso completo fase por fase. Leerla antes de iniciar las tareas.

Resumen de fases (detalle en `restructure-guide.md`):

1. **Fase 0 — Auditoría**: mapear todas las clases Spring existentes → tabla de equivalencias hexagonales
2. **Fase 1 — Dominio**: extraer lógica de negocio de `@Service` → Aggregate Roots puros en `domain/`; identificar Value Objects y excepciones de dominio
3. **Fase 2 — Puertos**: definir Inbound Ports desde los endpoints del `@Controller`; Outbound Ports desde los `@Repository`
4. **Fase 3 — Application Services**: implementar con `@ApplicationScoped` (CDI Quarkus); orquestación pura sin lógica de negocio
5. **Fase 4 — Infrastructure Quarkus**: Controllers JAX-RS + `PanacheRepositoryBase` + JPA Adapters + `@Provider ExceptionMapper` (usar templates de `quarkus-engineer/AGENT.md`)
6. **Fase 5 — Tests**: `@QuarkusTest` + REST Assured; Mockito puro para Application Services

Principios para `restructure_hexagonal`:
- `domain/` absolutamente puro: sin `jakarta.enterprise`, sin `jakarta.ws.rs`, sin JPA, sin Jackson
- Application Services con `@ApplicationScoped` (CDI lo requiere — no existe `DomainConfig` en Quarkus)
- APIs BIAN-compliant: mismos paths que el servicio Spring original cuando sea posible (evitar romper clientes existentes)
- MapStruct `componentModel = "cdi"` en todos los mappers
- Test profile H2 configurado en `application.properties` (`%test.*`)
- Cobertura ≥ 95% antes de crear el PR

### Caso especial: proyecto ya hexagonal en Spring (`sourceStructure: hexagonal`)

Si el origen es hexagonal, el `domain/` permanece intacto independientemente de la opción elegida:

```bash
# Verificar pureza del dominio antes de migrar
rg "import org.springframework" src/main/java/[basePackagePath]/domain/ --type java
rg "import jakarta.persistence" src/main/java/[basePackagePath]/domain/ --type java
# Si no hay resultados → el dominio ya es puro, no requiere cambios
```

---

## Protocolo por tarea (reanudación)

Al ejecutar cada paso de migración, actualiza el `tasks.json` para habilitar reanudación:

```python
import json, datetime
# HU_KEY = clave real de la HU (ej: "SCRUM-5" o "HU-123"), conocida del contexto de PASO 0
tasks_file = f'.github/plans/{HU_KEY}/tasks.json'

# Al iniciar un paso:
data = json.load(open(tasks_file))
for t in data['tasks']:
    if t['id'] == 'TASK-X.X':
        t['status'] = 'in_progress'
        t['startedAt'] = datetime.datetime.now().isoformat()
        break
with open(tasks_file, 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

# Al completarlo:
for t in data['tasks']:
    if t['id'] == 'TASK-X.X':
        t['status'] = 'completed'
        t['completedAt'] = datetime.datetime.now().isoformat()
        break
with open(tasks_file, 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

# Marcar el flujo en progreso en el metadata (igual que spring-engineer) —
# necesario para que la reanudación (PASO 1 de stive-sdlc) detecte el estado correcto.
meta_file = f'.github/specs/.metadata/{HU_KEY}.json'
meta = json.load(open(meta_file))
meta['status'] = 'implementation_in_progress'
with open(meta_file, 'w') as f:
    json.dump(meta, f, indent=2, ensure_ascii=False)
```

---

## Proceso de migración paso a paso

### Paso 0 — Análisis pre-migración

Antes de modificar nada, auditar el estado actual:

```bash
echo "=== Detectar package base ==="
DOMAIN_DIR=$(find src/main/java -type d -name "domain" -not -path "*/test/*" | head -1)
BASE_PKG=$(echo "$DOMAIN_DIR" | sed 's|src/main/java/||; s|/domain.*||' | tr '/' '.')
echo "Package: $BASE_PKG"

echo ""
echo "=== Inventario de clases Spring ==="
echo "Controllers (@RestController):"
rg -l "@RestController" src/main/java --type java

echo "Services (@Service):"
rg -l "@Service" src/main/java --type java

echo "Repositories (JpaRepository):"
rg -l "extends JpaRepository" src/main/java --type java

echo "WebClient configs:"
rg -l "WebClient" src/main/java --type java

echo ""
echo "=== Dependencias Spring en pom.xml ==="
grep -E "spring-boot|spring-web|spring-data|spring-security" pom.xml | grep "<artifactId>" | sed 's/.*<artifactId>//; s/<\/artifactId>//'

echo ""
echo "=== Tests existentes ==="
echo "SpringBootTest:"
rg -l "@SpringBootTest" src/test/java --type java
echo "WebMvcTest:"
rg -l "@WebMvcTest" src/test/java --type java
echo "DataJpaTest:"
rg -l "@DataJpaTest" src/test/java --type java
```

Presenta el inventario al desarrollador antes de continuar.

---

### Paso 1 — Migrar pom.xml

Reemplazar el `pom.xml` de Spring Boot por uno Quarkus 3.x LTS:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <groupId>[basePackage]</groupId>
    <artifactId>[microserviceName]</artifactId>
    <version>1.0.0-SNAPSHOT</version>

    <properties>
        <quarkus.platform.version>3.33.2</quarkus.platform.version>
        <java.version>17</java.version>
        <compiler-plugin.version>3.13.0</compiler-plugin.version>
        <mapstruct.version>1.5.5.Final</mapstruct.version>
        <lombok.version>1.18.30</lombok.version>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    </properties>

    <dependencyManagement>
        <dependencies>
            <dependency>
                <groupId>io.quarkus.platform</groupId>
                <artifactId>quarkus-bom</artifactId>
                <version>${quarkus.platform.version}</version>
                <type>pom</type>
                <scope>import</scope>
            </dependency>
        </dependencies>
    </dependencyManagement>

    <dependencies>
        <!-- REST (JAX-RS Reactive) -->
        <dependency>
            <groupId>io.quarkus</groupId>
            <artifactId>quarkus-resteasy-reactive-jackson</artifactId>
        </dependency>
        <dependency>
            <groupId>io.quarkus</groupId>
            <artifactId>quarkus-hibernate-validator</artifactId>
        </dependency>

        <!-- Data (Hibernate ORM + Panache) -->
        <dependency>
            <groupId>io.quarkus</groupId>
            <artifactId>quarkus-hibernate-orm-panache</artifactId>
        </dependency>
        <dependency>
            <groupId>io.quarkus</groupId>
            <artifactId>quarkus-jdbc-postgresql</artifactId>
        </dependency>
        <dependency>
            <groupId>io.quarkus</groupId>
            <artifactId>quarkus-flyway</artifactId>
        </dependency>

        <!-- REST Client Reactive (WebClient replacement) -->
        <dependency>
            <groupId>io.quarkus</groupId>
            <artifactId>quarkus-rest-client-reactive-jackson</artifactId>
        </dependency>

        <!-- Fault Tolerance (Resilience4j replacement) -->
        <dependency>
            <groupId>io.quarkus</groupId>
            <artifactId>quarkus-smallrye-fault-tolerance</artifactId>
        </dependency>

        <!-- OpenAPI -->
        <dependency>
            <groupId>io.quarkus</groupId>
            <artifactId>quarkus-smallrye-openapi</artifactId>
        </dependency>

        <!-- Utilities -->
        <dependency>
            <groupId>org.projectlombok</groupId>
            <artifactId>lombok</artifactId>
            <version>${lombok.version}</version>
            <scope>provided</scope>
        </dependency>
        <dependency>
            <groupId>org.mapstruct</groupId>
            <artifactId>mapstruct</artifactId>
            <version>${mapstruct.version}</version>
        </dependency>

        <!-- Testing -->
        <dependency>
            <groupId>io.quarkus</groupId>
            <artifactId>quarkus-junit5</artifactId>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>io.rest-assured</groupId>
            <artifactId>rest-assured</artifactId>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>io.quarkus</groupId>
            <artifactId>quarkus-junit5-mockito</artifactId>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>io.quarkus</groupId>
            <artifactId>quarkus-test-h2</artifactId>
            <scope>test</scope>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>io.quarkus.platform</groupId>
                <artifactId>quarkus-maven-plugin</artifactId>
                <version>${quarkus.platform.version}</version>
                <extensions>true</extensions>
                <executions>
                    <execution>
                        <goals>
                            <goal>build</goal>
                            <goal>generate-code</goal>
                            <goal>generate-code-tests</goal>
                        </goals>
                    </execution>
                </executions>
            </plugin>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <version>${compiler-plugin.version}</version>
                <configuration>
                    <source>17</source>
                    <target>17</target>
                    <annotationProcessorPaths>
                        <path>
                            <groupId>org.mapstruct</groupId>
                            <artifactId>mapstruct-processor</artifactId>
                            <version>${mapstruct.version}</version>
                        </path>
                        <path>
                            <groupId>org.projectlombok</groupId>
                            <artifactId>lombok</artifactId>
                            <version>${lombok.version}</version>
                        </path>
                        <path>
                            <groupId>org.projectlombok</groupId>
                            <artifactId>lombok-mapstruct-binding</artifactId>
                            <version>0.2.0</version>
                        </path>
                    </annotationProcessorPaths>
                </configuration>
            </plugin>
        </plugins>
    </build>

    <profiles>
        <profile>
            <id>native</id>
            <activation>
                <property>
                    <name>native</name>
                </property>
            </activation>
            <properties>
                <skipITs>false</skipITs>
                <quarkus.native.enabled>true</quarkus.native.enabled>
            </properties>
        </profile>
    </profiles>
</project>
```

---

### Paso 2 — Migrar `application.properties`

Reemplazar `application.yml` (Spring) por `application.properties` (Quarkus):

```properties
# Quarkus Application Config

# HTTP
quarkus.http.port=8080

# DataSource
quarkus.datasource.db-kind=postgresql
quarkus.datasource.username=${DB_USERNAME:postgres}
quarkus.datasource.password=${DB_PASSWORD:postgres}
quarkus.datasource.jdbc.url=jdbc:postgresql://${DB_HOST:localhost}:${DB_PORT:5432}/${DB_NAME:[microserviceName]}

# Hibernate ORM
quarkus.hibernate-orm.database.generation=none
quarkus.hibernate-orm.log.sql=false

# Flyway
quarkus.flyway.migrate-at-start=true
quarkus.flyway.locations=classpath:db/migration

# OpenAPI / Swagger
quarkus.smallrye-openapi.path=/openapi
quarkus.swagger-ui.always-include=true

# Logging
quarkus.log.level=INFO
quarkus.log.category."[basePackage]".level=DEBUG

# Test profile (en application.properties o test/resources/application.properties)
%test.quarkus.datasource.db-kind=h2
%test.quarkus.datasource.jdbc.url=jdbc:h2:mem:testdb;MODE=PostgreSQL
%test.quarkus.hibernate-orm.database.generation=drop-and-create
%test.quarkus.flyway.migrate-at-start=false
```

---

### Paso 3 — Migrar / Crear Dominio

#### Si `migrationStyle = same_pattern` (Opción A)

No existe `domain/` como capa independiente — las entidades JPA son el modelo. Verificar que no haya imports incorrectos en las clases de modelo:

```bash
# No aplica verificación de pureza — en patrón tradicional las entidades tienen JPA
echo "Patrón tradicional — entidades JPA son el modelo. Sin cambios en esta capa."
```

#### Si `migrationStyle = restructure_hexagonal` AND `sourceStructure = hexagonal` (Opción B desde hexagonal)

El dominio permanece exactamente igual — ya es puro. Verificar:

```bash
rg "import org.springframework" src/main/java/[basePackagePath]/domain/ --type java
rg "import jakarta.persistence" src/main/java/[basePackagePath]/domain/ --type java
# Si no hay resultados → sin cambios
```

#### Si `migrationStyle = restructure_hexagonal` AND `sourceStructure = traditional` (Opción B desde tradicional)

Extraer el dominio desde las entidades JPA existentes. Por cada `@Entity`:

1. Crear un Aggregate Root puro en `domain/model/` (sin JPA, sin Spring)
2. Mover la lógica de negocio que estaba en `@Service` → métodos del Aggregate Root
3. Definir Value Objects desde campos que tengan validaciones de negocio
4. Identificar invariantes: ¿qué reglas debe cumplir SIEMPRE este objeto?

```bash
echo "Inventario de entidades JPA a migrar:"
find src/main/java -name "*Entity.java" -o -name "*.java" | xargs rg -l "@Entity" 2>/dev/null
```

---

### Paso 4 — Migrar Application Layer

Los `Application Services` (casos de uso) cambian mínimamente:

| Spring Boot | Quarkus |
|---|---|
| `@Service` | `@ApplicationScoped` |
| `@Transactional` (Spring) | `@Transactional` (jakarta) |
| `@Autowired` (constructor) | `@Inject` (constructor) — o mantener constructor sin anotación (CDI lo detecta) |

```java
// ANTES (Spring Boot)
@Service
public class InitiateAccountService implements InitiateAccountUseCase {
    private final AccountRepositoryPort repository;

    @Autowired  // ← eliminar
    public InitiateAccountService(AccountRepositoryPort repository) { ... }
}

// DESPUÉS (Quarkus)
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.transaction.Transactional;

@ApplicationScoped  // ← reemplaza @Service
public class InitiateAccountService implements InitiateAccountUseCase {
    private final AccountRepositoryPort repository;

    // Sin @Inject en constructor — CDI inyecta por constructor automáticamente si hay 1 solo
    public InitiateAccountService(AccountRepositoryPort repository) { ... }

    @Override
    @Transactional  // ← usar jakarta.transaction, no spring
    public Account execute(InitiateAccountCommand command) { ... }
}
```

---

### Paso 5 — Migrar Controllers REST

| Spring Boot | Quarkus (JAX-RS Reactive) |
|---|---|
| `@RestController` | `@Path("/...")` + `@Produces(MediaType.APPLICATION_JSON)` |
| `@RequestMapping` | `@Path` a nivel de clase |
| `@PostMapping("/initiate")` | `@POST` + `@Path("/initiate")` |
| `@GetMapping("/{id}/retrieve")` | `@GET` + `@Path("/{id}/retrieve")` |
| `@RequestBody @Valid` | `@Valid` sin `@RequestBody` |
| `@PathVariable` | `@PathParam` |
| `@RequestParam` | `@QueryParam` |
| `ResponseEntity<T>` | `Response` o directamente `T` |
| `@Valid` (Spring) | `@Valid` (jakarta.validation) |

```java
// ANTES (Spring Boot)
@RestController
@RequestMapping("/account-management/account-balance")
public class InitiateAccountController {

    @PostMapping("/initiate")
    public ResponseEntity<InitiateAccountResponse> initiate(@Valid @RequestBody InitiateAccountRequest request) {
        var result = useCase.execute(mapper.toCommand(request));
        return ResponseEntity.status(201).body(mapper.toResponse(result));
    }
}

// DESPUÉS (Quarkus)
import jakarta.validation.Valid;
import jakarta.ws.rs.*;
import jakarta.ws.rs.core.*;

@Path("/account-management/account-balance")
@Produces(MediaType.APPLICATION_JSON)
@Consumes(MediaType.APPLICATION_JSON)
public class InitiateAccountController {

    private final InitiateAccountUseCase useCase;
    private final InitiateAccountRestMapper mapper;

    // Inyección por constructor (CDI lo detecta con 1 solo constructor) — sin @Inject por campo
    public InitiateAccountController(InitiateAccountUseCase useCase, InitiateAccountRestMapper mapper) {
        this.useCase = useCase;
        this.mapper = mapper;
    }

    @POST
    @Path("/initiate")
    public Response initiate(@Valid InitiateAccountRequest request) {
        var result = useCase.execute(mapper.toCommand(request));
        return Response.status(Response.Status.CREATED).entity(mapper.toResponse(result)).build();
    }
}
```

---

### Paso 6 — Migrar Adaptadores de Persistencia (JPA → Panache)

| Spring Boot | Quarkus |
|---|---|
| `@Entity` (jakarta) | `@Entity` (jakarta — igual) |
| `extends JpaRepository<E, ID>` | `extends PanacheRepositoryBase<E, ID>` |
| `@Component` en adapter | `@ApplicationScoped` |
| `@Autowired` → constructor | constructor injection (sin `@Inject` por campo) |

```java
// ANTES — Spring Data JPA Repository
public interface AccountJpaRepository extends JpaRepository<AccountEntity, String> {
    Optional<AccountEntity> findByAccountNumber(String accountNumber);
}

// DESPUÉS — Panache Repository
import io.quarkus.hibernate.orm.panache.PanacheRepositoryBase;
import jakarta.enterprise.context.ApplicationScoped;

@ApplicationScoped
public class AccountPanacheRepository implements PanacheRepositoryBase<AccountEntity, String> {

    public Optional<AccountEntity> findByAccountNumber(String accountNumber) {
        return find("accountNumber", accountNumber).firstResultOptional();
    }

    public boolean existsByAccountNumber(String accountNumber) {
        return count("accountNumber", accountNumber) > 0;
    }
}
```

```java
// DESPUÉS — JPA Adapter (sin cambios estructurales, solo cambio de dependencia)
import jakarta.enterprise.context.ApplicationScoped;

@ApplicationScoped  // en lugar de @Component
public class AccountJpaAdapter implements AccountRepositoryPort {

    private final AccountPanacheRepository repository;
    private final AccountJpaMapper mapper;

    public AccountJpaAdapter(AccountPanacheRepository repository, AccountJpaMapper mapper) {
        this.repository = repository;
        this.mapper = mapper;
    }

    // Misma lógica — solo cambia el tipo de repository inyectado
}
```

---

### Paso 7 — Migrar WebClient a REST Client Reactive

| Spring Boot | Quarkus |
|---|---|
| `WebClient.Builder` | `@RegisterRestClient` |
| `Resilience4j @CircuitBreaker` | `@CircuitBreaker` (SmallRye) |
| `@Retry` (Resilience4j) | `@Retry` (SmallRye) |
| `@Timeout` (Resilience4j) | `@Timeout` (SmallRye) |

```java
// ANTES — Spring WebClient
@Component
public class CustomerServiceWebClientAdapter implements CustomerServicePort {

    private final WebClient webClient;

    @CircuitBreaker(name = "customer-service", fallbackMethod = "fallback")
    @Override
    public boolean customerExists(String customerId) {
        return webClient.get()
            .uri("/customers/{id}", customerId)
            .retrieve()
            .bodyToMono(Boolean.class)
            .block();
    }
}

// DESPUÉS — Quarkus REST Client
import jakarta.ws.rs.GET;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.PathParam;
import org.eclipse.microprofile.rest.client.inject.RegisterRestClient;
import org.eclipse.microprofile.faulttolerance.CircuitBreaker;
import org.eclipse.microprofile.faulttolerance.Retry;
import org.eclipse.microprofile.faulttolerance.Timeout;

@RegisterRestClient(configKey = "customer-service")
@Path("/customers")
public interface CustomerRestClient {
    @GET
    @Path("/{id}/exists")
    boolean customerExists(@PathParam("id") String customerId);
}

// Adapter que implementa el outbound port
@ApplicationScoped
public class CustomerServiceAdapter implements CustomerServicePort {

    private final CustomerRestClient client;

    // Inyección por constructor con el qualifier @RestClient — sin @Inject por campo
    public CustomerServiceAdapter(@RestClient CustomerRestClient client) {
        this.client = client;
    }

    @Override
    @CircuitBreaker(requestVolumeThreshold = 5, failureRatio = 0.5, delay = 5000)
    @Retry(maxRetries = 3, delay = 200)
    @Timeout(value = 3000)
    public boolean customerExists(String customerId) {
        return client.customerExists(customerId);
    }
}
```

Configuración en `application.properties`:
```properties
quarkus.rest-client.customer-service.url=${CUSTOMER_SERVICE_URL:http://localhost:8081}
quarkus.rest-client.customer-service.connect-timeout=2000
quarkus.rest-client.customer-service.read-timeout=5000
```

---

### Paso 8 — Migrar Manejo de Errores

| Spring Boot | Quarkus |
|---|---|
| `@RestControllerAdvice` | `@Provider` + `ExceptionMapper<T>` |
| `ProblemDetail` | JSON manual o `@Provider ExceptionMapper` |

```java
// DESPUÉS — Quarkus ExceptionMapper
import jakarta.ws.rs.core.Response;
import jakarta.ws.rs.ext.ExceptionMapper;
import jakarta.ws.rs.ext.Provider;
import java.time.Instant;
import java.util.Map;

@Provider
public class AccountNotFoundExceptionMapper implements ExceptionMapper<AccountNotFoundException> {

    @Override
    public Response toResponse(AccountNotFoundException ex) {
        return Response.status(Response.Status.NOT_FOUND)
            .entity(Map.of(
                "type", "ACCOUNT_NOT_FOUND",
                "detail", ex.getMessage(),
                "timestamp", Instant.now().toString()
            ))
            .build();
    }
}

@Provider
public class ValidationExceptionMapper implements ExceptionMapper<jakarta.validation.ConstraintViolationException> {

    @Override
    public Response toResponse(jakarta.validation.ConstraintViolationException ex) {
        var errors = ex.getConstraintViolations().stream()
            .collect(java.util.stream.Collectors.toMap(
                cv -> cv.getPropertyPath().toString(),
                cv -> cv.getMessage()
            ));
        return Response.status(Response.Status.BAD_REQUEST)
            .entity(Map.of("type", "VALIDATION_ERROR", "errors", errors, "timestamp", Instant.now().toString()))
            .build();
    }
}
```

---

### Paso 9 — Migrar MapStruct

Solo cambiar `componentModel`:

```java
// ANTES (Spring)
@Mapper(componentModel = "spring")

// DESPUÉS (Quarkus CDI)
@Mapper(componentModel = "cdi")
```

---

### Paso 10 — Migrar Tests

| Spring Boot | Quarkus |
|---|---|
| `@SpringBootTest` | `@QuarkusTest` |
| `MockMvc` + `@WebMvcTest` | `REST Assured` + `@QuarkusTest` |
| `@MockBean` | `@InjectMock` |
| `@DataJpaTest` | `@QuarkusTest` + H2 |
| `@ExtendWith(MockitoExtension)` | `@QuarkusTest` + `@InjectMock` |

```java
// ANTES — SpringBootTest
@SpringBootTest
@AutoConfigureMockMvc
class AccountIntegrationTest {
    @Autowired MockMvc mockMvc;

    @Test
    void shouldInitiateAccount() throws Exception {
        mockMvc.perform(post("/account-management/account-balance/initiate")...)
            .andExpect(status().isCreated());
    }
}

// DESPUÉS — QuarkusTest con REST Assured
import io.quarkus.test.junit.QuarkusTest;
import io.restassured.RestAssured;
import static io.restassured.RestAssured.given;
import static org.hamcrest.Matchers.*;

@QuarkusTest
class AccountResourceTest {

    @Test
    void shouldInitiateAccount() {
        given()
            .contentType("application/json")
            .body("""{ "customerId": "CUST-001", "accountType": "SAVINGS" }""")
        .when()
            .post("/account-management/account-balance/initiate")
        .then()
            .statusCode(201)
            .body("accountNumber", notNullValue());
    }

    @Test
    void shouldReturn404WhenNotFound() {
        given()
        .when()
            .get("/account-management/account-balance/inexistente/retrieve")
        .then()
            .statusCode(404)
            .body("type", equalTo("ACCOUNT_NOT_FOUND"));
    }
}
```

Tests unitarios con mocks en Quarkus:

```java
import io.quarkus.test.junit.QuarkusTest;
import io.quarkus.test.junit.mockito.InjectMock;
import org.junit.jupiter.api.Test;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@QuarkusTest
class InitiateAccountServiceTest {

    @InjectMock AccountRepositoryPort repository;
    @Inject InitiateAccountUseCase useCase;  // la implementación real

    @Test
    void shouldInitiateAccount() {
        when(repository.existsByAccountNumber(any())).thenReturn(false);
        when(repository.save(any())).thenAnswer(inv -> inv.getArgument(0));

        var result = useCase.execute(new InitiateAccountCommand("CUST-001", "SAVINGS"));

        assertThat(result).isNotNull();
        verify(repository).save(any());
    }
}
```

---

## Checklist de verificación post-migración

```
□ pom.xml: sin dependencias spring-boot-*, usando quarkus-bom
□ application.properties: formato Quarkus (no YAML, no spring.*)
□ domain/: sin cambios (puro, sin Spring/JPA directo)
□ application/: @ApplicationScoped en lugar de @Service, @Transactional jakarta
□ infrastructure/rest/: @Path, @POST/@GET, Response en lugar de ResponseEntity
□ infrastructure/database/: PanacheRepositoryBase en lugar de JpaRepository
□ infrastructure/client/: @RegisterRestClient + SmallRye Fault Tolerance
□ infrastructure/config/: @Provider ExceptionMapper en lugar de @RestControllerAdvice
□ Mappers MapStruct: componentModel = "cdi"
□ Tests: @QuarkusTest + REST Assured, @InjectMock en lugar de @MockBean
□ Compilación limpia: mvn clean compile
□ Tests pasan: mvn test
□ Cobertura ≥ 95%: mvn verify
□ Endpoints BIAN-compliant: mismos paths que antes
```
