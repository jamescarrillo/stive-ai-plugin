---
name: quarkus-migrator-from-spring
description: Migra un microservicio Spring Boot (2.x/3.x, Java 11+) a Quarkus 3.x LTS manteniendo la misma funcionalidad, arquitectura hexagonal y alineación BIAN.
---

# Instrucciones para el Agente

## Principio Fundamental

**NO elimines funcionalidad.** La migración debe ser funcionalmente transparente. El código existente en `domain/` y `application/` (puertos) **NO debe modificarse** — son capas tecnológicamente neutras. Solo se modifican adaptadores en `infrastructure/` y archivos de configuración/build.

## Pre-migración: Análisis del proyecto origen

Antes de tocar cualquier archivo, ejecuta este análisis completo:

```bash
# 1. Detectar versión de Spring Boot
SPRING_VERSION=$(grep -oP 'spring-boot-starter-parent\s*>\s*\K[^<]+' pom.xml 2>/dev/null || grep -oP 'spring.boot.version\s*=\s*\K[^<]+' pom.xml 2>/dev/null || echo "unknown")

# 2. Detectar versión de Java
JAVA_VERSION=$(grep -oP 'java.version>\K[^<]+' pom.xml 2>/dev/null || echo "unknown")

# 3. Detectar dependencias del proyecto
# Listar todas las dependencias relevantes
grep -oP '<artifactId>[^<]+</artifactId>' pom.xml 2>/dev/null | sed 's/<artifactId>//;s/<\/artifactId>//' | sort -u

# 4. Detectar estructura de paquetes base
PACKAGE_BASE=$(grep -oP 'package \K[a-zA-Z0-9_.]+' src/main/java/**/Application*.java 2>/dev/null | head -1 | sed 's/\.[^.]*$//')

# 5. Detectar anotaciones Spring en infraestructura
echo "=== Spring annotations in infrastructure ==="
grep -rn '@RestController\|@Service\|@Component\|@Repository\|@Autowired\|@Value\|@Configuration\|@Bean\|@RequestMapping\|@GetMapping\|@PostMapping\|@PutMapping\|@DeleteMapping\|@PatchMapping\|@SpringBootApplication\|@SpringBootTest\|@WebMvcTest\|@DataJpaTest\|@MockBean\|@MockitoBean\|@Transactional\|@Entity\|@Table\|@Column' src/main/java/ 2>/dev/null | grep -v '/domain/' | grep -v '/application/'

# 6. Detectar test que usan Spring
echo "=== Spring annotations in tests ==="
grep -rn '@SpringBootTest\|@WebMvcTest\|@DataJpaTest\|@MockBean\|@MockitoBean' src/test/java/ 2>/dev/null
```

## Fases de migración (orden obligatorio)

### Fase 0: Preservación de arquitectura

**REGLAS ESTRICTAS:**

| Capa | ¿Se modifica? | ¿Por qué? |
|---|---|---|
| `domain/` | **NO** | Es puro Java, sin dependencias de framework |
| `application/ports/` | **NO** | Son interfaces, sin dependencias de framework |
| `application/service/` | **SÍ** | Si usan `@Service` de Spring, reemplazar por CDI |
| `infrastructure/` | **SÍ** | Todos los adaptadores cambian de framework |
| `pom.xml` | **SÍ** | Build system completo |
| `src/main/resources/` | **SÍ** | Configuración específica de Spring |

### Fase 1: Build System — pom.xml

Reemplazar el `pom.xml` de Spring Boot por uno de Quarkus.

**Template de pom.xml para Quarkus 3.x LTS:**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <groupId>$JAVA_GROUP_ID</groupId>
    <artifactId>$MICRO_NAME</artifactId>
    <version>1.0.0-SNAPSHOT</version>
    <name>$BIAN_SERVICE_DOMAIN</name>
    <description>BIAN Service Domain: $BIAN_SERVICE_DOMAIN (Migrated to Quarkus)</description>

    <properties>
        <maven.compiler.release>17</maven.compiler.release>
        <maven.compiler.source>17</maven.compiler.source>
        <maven.compiler.target>17</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
        <quarkus.platform.version>3.33.0</quarkus.platform.version>
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
        <!-- RESTEasy Reactive (JAX-RS) -->
        <dependency>
            <groupId>io.quarkus</groupId>
            <artifactId>quarkus-resteasy-reactive</artifactId>
        </dependency>
        <dependency>
            <groupId>io.quarkus</groupId>
            <artifactId>quarkus-resteasy-reactive-jackson</artifactId>
        </dependency>

        <!-- Hibernate ORM + Panache -->
        <dependency>
            <groupId>io.quarkus</groupId>
            <artifactId>quarkus-hibernate-orm-panache</artifactId>
        </dependency>

        <!-- JDBC Driver -->
        <dependency>
            <groupId>$DB_ENGINE_GROUP_ID</groupId>
            <artifactId>$DB_ENGINE_ARTIFACT_ID</artifactId>
        </dependency>

        <!-- Validation -->
        <dependency>
            <groupId>io.quarkus</groupId>
            <artifactId>quarkus-hibernate-validator</artifactId>
        </dependency>

        <!-- Flyway migrations -->
        <dependency>
            <groupId>io.quarkus</groupId>
            <artifactId>quarkus-flyway</artifactId>
        </dependency>

        <!-- OpenAPI / Swagger UI -->
        <dependency>
            <groupId>io.quarkus</groupId>
            <artifactId>quarkus-smallrye-openapi</artifactId>
        </dependency>
        <dependency>
            <groupId>io.quarkus</groupId>
            <artifactId>quarkus-swagger-ui</artifactId>
        </dependency>

        <!-- REST Client Reactive (para comunicación entre microservicios) -->
        <dependency>
            <groupId>io.quarkus</groupId>
            <artifactId>quarkus-rest-client-reactive</artifactId>
        </dependency>
        <dependency>
            <groupId>io.quarkus</groupId>
            <artifactId>quarkus-rest-client-reactive-jackson</artifactId>
        </dependency>

        <!-- Fault Tolerance (CircuitBreaker, Retry, Timeout) -->
        <dependency>
            <groupId>io.quarkus</groupId>
            <artifactId>quarkus-smallrye-fault-tolerance</artifactId>
        </dependency>

        <!-- CDI (Contexts and Dependency Injection) -->
        <dependency>
            <groupId>io.quarkus</groupId>
            <artifactId>quarkus-arc</artifactId>
        </dependency>

        <!-- Health checks -->
        <dependency>
            <groupId>io.quarkus</groupId>
            <artifactId>quarkus-smallrye-health</artifactId>
        </dependency>

        <!-- Metrics -->
        <dependency>
            <groupId>io.quarkus</groupId>
            <artifactId>quarkus-micrometer</artifactId>
        </dependency>

        <!-- Logging (JSON opcional) -->
        <dependency>
            <groupId>io.quarkus</groupId>
            <artifactId>quarkus-logging-json</artifactId>
        </dependency>

        <!-- Config YAML (si el proyecto original usa application.yml) -->
        <dependency>
            <groupId>io.quarkus</groupId>
            <artifactId>quarkus-config-yaml</artifactId>
        </dependency>

        <!-- Test -->
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
            <groupId>org.testcontainers</groupId>
            <artifactId>testcontainers</artifactId>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>org.testcontainers</groupId>
            <artifactId>postgresql</artifactId>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>org.testcontainers</groupId>
            <artifactId>junit-jupiter</artifactId>
            <scope>test</scope>
        </dependency>

        <!-- AssertJ (mantener mismo estilo de aserciones) -->
        <dependency>
            <groupId>org.assertj</groupId>
            <artifactId>assertj-core</artifactId>
            <scope>test</scope>
        </dependency>

        <!-- MapStruct (si el proyecto lo usa) -->
        <dependency>
            <groupId>org.mapstruct</groupId>
            <artifactId>mapstruct</artifactId>
            <version>1.6.3</version>
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
                <configuration>
                    <source>17</source>
                    <target>17</target>
                    <annotationProcessorPaths>
                        <path>
                            <groupId>org.mapstruct</groupId>
                            <artifactId>mapstruct-processor</artifactId>
                            <version>1.6.3</version>
                        </path>
                    </annotationProcessorPaths>
                </configuration>
            </plugin>
            <plugin>
                <groupId>org.jacoco</groupId>
                <artifactId>jacoco-maven-plugin</artifactId>
                <version>0.8.12</version>
                <executions>
                    <execution>
                        <goals><goal>prepare-agent</goal></goals>
                    </execution>
                    <execution>
                        <id>report</id>
                        <phase>test</phase>
                        <goals><goal>report</goal></goals>
                    </execution>
                    <execution>
                        <id>check</id>
                        <phase>verify</phase>
                        <goals><goal>check</goal></goals>
                        <configuration>
                            <rules>
                                <rule>
                                    <element>BUNDLE</element>
                                    <limits>
                                        <limit><counter>LINE</counter><value>COVEREDRATIO</value><minimum>0.95</minimum></limit>
                                        <limit><counter>BRANCH</counter><value>COVEREDRATIO</value><minimum>0.95</minimum></limit>
                                        <limit><counter>INSTRUCTION</counter><value>COVEREDRATIO</value><minimum>0.95</minimum></limit>
                                    </limits>
                                </rule>
                            </rules>
                            <excludes>
                                <exclude>**/config/**</exclude>
                                <exclude>**/dto/**</exclude>
                                <exclude>**/*MapperImpl.*</exclude>
                                <exclude>**/*Application.*</exclude>
                                <exclude>**/domain/exception/**</exclude>
                            </excludes>
                        </configuration>
                    </execution>
                </executions>
            </plugin>
        </plugins>
    </build>
</project>
```

**Resolución de variables de base de datos:**

| `$DB_ENGINE` | `$DB_ENGINE_GROUP_ID` | `$DB_ENGINE_ARTIFACT_ID` |
|---|---|---|
| `postgresql` | `org.postgresql` | `postgresql` |
| `mysql` | `com.mysql` | `mysql-connector-j` |
| `h2` | `com.h2database` | `h2` |

**IMPORTANTE sobre MapStruct:** Si el proyecto usaba MapStruct con `componentModel = "spring"`, debes cambiar a `componentModel = "cdi"` o `componentModel = "default"` (con creación manual en config). Revisa cada mapper en `infrastructure/` y actualiza la anotación.

### Fase 2: Configuration — application.properties

Convertir de `application.yml` o `application.properties` de Spring a formato Quarkus.

**Template de `src/main/resources/application.properties`:**

```properties
# Quarkus Application Name
quarkus.application.name=$MICRO_NAME

# HTTP Server
quarkus.http.port=${PORT:8080}

# Datasource
quarkus.datasource.db-kind=$DB_ENGINE
quarkus.datasource.jdbc.url=${DB_URL:jdbc:$DB_ENGINE://localhost:5432/$MICRO_NAME}
quarkus.datasource.username=${DB_USER:postgres}
quarkus.datasource.password=${DB_PASSWORD:postgres}

# Hibernate ORM
quarkus.hibernate-orm.database.generation=validate

# Flyway
quarkus.flyway.migrate-at-start=true
quarkus.flyway.locations=db/migration
quarkus.flyway.baseline-on-migrate=true

# OpenAPI / Swagger UI
quarkus.swagger-ui.always-include=true
quarkus.swagger-ui.path=/swagger-ui.html
quarkus.smallrye-openapi.path=/api-docs

# CORS (ajustar según entorno)
quarkus.http.cors=true
quarkus.http.cors.origins=*
quarkus.http.cors.methods=GET,POST,PUT,PATCH,DELETE,OPTIONS
quarkus.http.cors.headers=accept,authorization,content-type,x-requested-with

# Logging
quarkus.log.level=INFO
quarkus.log.console.json=false

# Fault Tolerance (SmallRye)
quarkus.fault-tolerance.circuit-breaker.delay=30s
quarkus.fault-tolerance.circuit-breaker.success-threshold=3
quarkus.fault-tolerance.circuit-breaker.failure-threshold=5
quarkus.fault-tolerance.circuit-breaker.request-volume-threshold=10
```

**Migración de propiedades Spring → Quarkus:**

| Spring | Quarkus |
|---|---|
| `server.port` | `quarkus.http.port` |
| `spring.application.name` | `quarkus.application.name` |
| `spring.datasource.url` | `quarkus.datasource.jdbc.url` |
| `spring.datasource.username` | `quarkus.datasource.username` |
| `spring.datasource.password` | `quarkus.datasource.password` |
| `spring.datasource.driver-class-name` | Se infiere de `quarkus.datasource.db-kind` |
| `spring.jpa.hibernate.ddl-auto` | `quarkus.hibernate-orm.database.generation` |
| `spring.flyway.enabled=true` | `quarkus.flyway.migrate-at-start=true` |
| `spring.flyway.locations` | `quarkus.flyway.locations` (sin `classpath:`) |
| `springdoc.api-docs.path` | `quarkus.smallrye-openapi.path` |
| `springdoc.swagger-ui.path` | `quarkus.swagger-ui.path` |
| `spring.profiles.active` | `quarkus.profile` |
| `logging.level.*` | `quarkus.log.level.*` |
| `resilience4j.circuitbreaker.*` | `quarkus.fault-tolerance.circuit-breaker.*` |
| `resilience4j.timelimiter.*` | `quarkus.fault-tolerance.timeout.*` |
| `resilience4j.retry.*` | `quarkus.fault-tolerance.retry.*` |

### Fase 3: Application Service — Inyección de dependencias

Si los servicios de aplicación en `application/service/` usaban `@Service` de Spring, reemplazar por CDI.

**ANTES (Spring):**
```java
package com.jotace.accountmanagement.application.service;

import org.springframework.stereotype.Service;

@Service
public class AccountQueryService implements RetrieveAccountsUseCase {
    // ...
}
```

**DESPUÉS (Quarkus/CDI):**
```java
package com.jotace.accountmanagement.application.service;

import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;

@ApplicationScoped
public class AccountQueryService implements RetrieveAccountsUseCase {
    // ...
}
```

**Reglas de migración CDI:**

| Spring | CDI (Quarkus) |
|---|---|
| `@Service` | `@ApplicationScoped` o `@Singleton` |
| `@Component` | `@Singleton` o `@ApplicationScoped` |
| `@Repository` | `@ApplicationScoped` o `@Singleton` (o directamente con Panache) |
| `@Autowired` | `@Inject` |
| `@Qualifier("name")` | `@Named("name")` |
| `@Value("${prop}")` | `@ConfigProperty(name = "prop")` |
| `@Configuration` + `@Bean` | `@ApplicationScoped` + `@Produces`, o directamente la clase `@ApplicationScoped` |
| `@ConfigurationProperties` | `@ConfigMapping(prefix = "prefix")` |
| `@Transactional` | `@Transactional` (jakarta, funciona igual) |
| `@PostConstruct` | `@PostConstruct` (jakarta, funciona igual) |

### Fase 4: REST Controllers — Spring MVC → JAX-RS

Migrar cada `@RestController` en `infrastructure/adapters/inbound/rest/`.

**ANTES (Spring MVC):**
```java
package com.jotace.accountmanagement.infrastructure.adapters.inbound.rest;

import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;

@RestController
@RequestMapping("/account-management/account")
public class AccountController {

    private final RetrieveAccountsUseCase useCase;
    private final AccountDtoMapper mapper;

    public AccountController(RetrieveAccountsUseCase useCase, AccountDtoMapper mapper) {
        this.useCase = useCase;
        this.mapper = mapper;
    }

    @GetMapping("/retrieve")
    public ResponseEntity<List<AccountResponse>> getAccounts(@RequestParam String cu) {
        var accounts = useCase.findByCustomerId(cu);
        return ResponseEntity.ok(mapper.toResponseList(accounts));
    }

    @PostMapping("/initiate")
    public ResponseEntity<AccountResponse> createAccount(@Valid @RequestBody CreateAccountRequest request) {
        var account = useCase.initiate(mapper.toDomain(request));
        return ResponseEntity.status(201).body(mapper.toResponse(account));
    }
}
```

**DESPUÉS (JAX-RS con Quarkus):**
```java
package com.jotace.accountmanagement.infrastructure.adapters.inbound.rest;

import jakarta.inject.Inject;
import jakarta.validation.Valid;
import jakarta.ws.rs.*;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;

@Path("/account-management/account")
@Produces(MediaType.APPLICATION_JSON)
@Consumes(MediaType.APPLICATION_JSON)
public class AccountResource {

    @Inject
    RetrieveAccountsUseCase useCase;

    @Inject
    AccountDtoMapper mapper;

    @GET
    @Path("/retrieve")
    public Response getAccounts(@QueryParam("cu") String cu) {
        var accounts = useCase.findByCustomerId(cu);
        return Response.ok(mapper.toResponseList(accounts)).build();
    }

    @POST
    @Path("/initiate")
    public Response createAccount(@Valid CreateAccountRequest request) {
        var account = useCase.initiate(mapper.toDomain(request));
        return Response.status(Response.Status.CREATED).entity(mapper.toResponse(account)).build();
    }
}
```

**Tabla de migración REST:**

| Spring MVC | JAX-RS (Quarkus) |
|---|---|
| `@RestController` | `@Path` + `@Produces` + `@Consumes` |
| `@RequestMapping("/path")` | `@Path("/path")` |
| `@GetMapping` | `@GET` |
| `@PostMapping` | `@POST` |
| `@PutMapping` | `@PUT` |
| `@DeleteMapping` | `@DELETE` |
| `@PatchMapping` | `@PATCH` |
| `@RequestParam("name")` | `@QueryParam("name")` |
| `@PathVariable("name")` | `@PathParam("name")` |
| `@RequestBody` | Parámetro del método directamente |
| `@RequestHeader("name")` | `@HeaderParam("name")` |
| `ResponseEntity<T>` | `Response` |
| `ResponseEntity.ok(body)` | `Response.ok(body).build()` |
| `ResponseEntity.status(201).body(b)` | `Response.status(Response.Status.CREATED).entity(b).build()` |
| `@Valid` | `@Valid` (jakarta, funciona igual) |
| `@ExceptionHandler` | Ver Fase 7 |

### Fase 5: Persistencia — Spring Data JPA → Hibernate ORM + Panache

#### 5.1. Entidades JPA

Las entidades JPA (`@Entity`, `@Table`, `@Column`) **NO cambian** — son Jakarta Persistence estándar. Las entidades existentes se mantienen intactas.

**Único cambio:** Verificar que los imports usen `jakarta.persistence.*` (Spring Boot 3.x ya usa Jakarta; Spring Boot 2.x usa `javax.persistence.*` → migrar a `jakarta.persistence.*`).

**Script de verificación:**
```bash
# Detectar imports javax.persistence en el proyecto
grep -rn 'javax\.persistence' src/main/java/ 2>/dev/null

# Detectar imports javax en general (servlet, validation, etc.)
grep -rn 'import javax\.' src/main/java/ 2>/dev/null
```

Si hay `javax.*`, reemplazar por `jakarta.*` en todos los archivos de infraestructura.

#### 5.2. Repositorios

**ANTES (Spring Data JPA):**
```java
package com.jotace.accountmanagement.infrastructure.adapters.outbound.database;

import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

public interface JpaAccountRepository extends JpaRepository<AccountEntity, String> {
    List<AccountEntity> findByCustomerCu(String customerCu);
}
```

**DESPUÉS (Panache):**
```java
package com.jotace.accountmanagement.infrastructure.adapters.outbound.database;

import io.quarkus.hibernate.orm.panache.PanacheRepositoryBase;
import jakarta.enterprise.context.ApplicationScoped;
import java.util.List;

@ApplicationScoped
public class JpaAccountRepository implements PanacheRepositoryBase<AccountEntity, String> {

    public List<AccountEntity> findByCustomerCu(String customerCu) {
        return list("customerCu", customerCu);
    }
}
```

**O si se prefiere PanacheEntity (la entidad extiende PanacheEntity):**
```java
// En la entidad
@Entity
@Table(name = "account")
public class AccountEntity extends PanacheEntityBase {
    @Id
    public String accountNumber;
    public String customerCu;
    // ...
}
```

**Tabla de migración repositorios:**

| Spring Data JPA | Hibernate ORM + Panache |
|---|---|
| `extends JpaRepository<T, ID>` | `implements PanacheRepositoryBase<T, ID>` |
| `extends CrudRepository<T, ID>` | `implements PanacheRepositoryBase<T, ID>` |
| `repository.findById(id)` | `repository.findById(id)` (devuelve `Optional`) |
| `repository.findAll()` | `repository.listAll()` |
| `repository.save(entity)` | `repository.persist(entity)` |
| `repository.delete(entity)` | `repository.delete(entity)` |
| `repository.deleteById(id)` | `repository.deleteById(id)` |
| `repository.count()` | `repository.count()` |
| `repository.existsById(id)` | `repository.findById(id).isPresent()` |
| `findByCustomerCu(String cu)` | `list("customerCu", cu)` |
| `findByCustomerCuAndStatus(String cu, String s)` | `list("customerCu = ?1 and status = ?2", cu, s)` |
| `findByCustomerCuOrderByCreatedAtDesc(String cu)` | `list("customerCu", cu, Sort.by("createdAt").descending())` |

**IMPORTANTE:** El adaptador JPA (`AccountJpaRepositoryAdapter`) que mapea entre `AccountEntity` y `Account` de dominio **no cambia su lógica**, solo la inyección del repositorio (ahora es `@Inject` en lugar de constructor injection de Spring, o se mantiene constructor injection con CDI).

### Fase 6: Mappers (MapStruct)

Si el proyecto usa MapStruct en `infrastructure/` para mapear entre entidades/DTOs y dominio:

**Cambiar `componentModel`:**
```java
// ANTES (Spring)
@Mapper(componentModel = "spring")
public interface AccountEntityMapper {
    Account toDomain(AccountEntity entity);
    AccountEntity toEntity(Account domain);
}

// DESPUÉS (CDI)
@Mapper(componentModel = "cdi")
public interface AccountEntityMapper {
    Account toDomain(AccountEntity entity);
    AccountEntity toEntity(Account domain);
}
```

**O si no se quiere depender de CDI, usar `default` y crear manualmente en config:**
```java
// Mapper sin CDI
@Mapper
public interface AccountEntityMapper {
    Account toDomain(AccountEntity entity);
    AccountEntity toEntity(Account domain);
}

// Config class para crearlo
@Singleton
public class MapperConfig {
    @Produces
    public AccountEntityMapper accountEntityMapper() {
        return Mappers.getMapper(AccountEntityMapper.class);
    }
}
```

### Fase 7: Exception Handling — @RestControllerAdvice → ExceptionMapper

**ANTES (Spring):**
```java
package com.jotace.accountmanagement.infrastructure.config;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(CustomerNotFoundException.class)
    public ResponseEntity<ErrorResponse> handleCustomerNotFound(CustomerNotFoundException ex) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND)
            .body(new ErrorResponse("CUSTOMER_NOT_FOUND", ex.getMessage()));
    }

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<ErrorResponse> handleInvalidArgument(IllegalArgumentException ex) {
        return ResponseEntity.status(HttpStatus.BAD_REQUEST)
            .body(new ErrorResponse("INVALID_ARGUMENT", ex.getMessage()));
    }
}
```

**DESPUÉS (Quarkus/JAX-RS):**
```java
package com.jotace.accountmanagement.infrastructure.config;

import jakarta.ws.rs.core.Response;
import jakarta.ws.rs.ext.ExceptionMapper;
import jakarta.ws.rs.ext.Provider;

@Provider
public class CustomerNotFoundExceptionMapper implements ExceptionMapper<CustomerNotFoundException> {

    @Override
    public Response toResponse(CustomerNotFoundException exception) {
        return Response.status(Response.Status.NOT_FOUND)
            .entity(new ErrorResponse("CUSTOMER_NOT_FOUND", exception.getMessage()))
            .build();
    }
}

@Provider
public class IllegalArgumentExceptionMapper implements ExceptionMapper<IllegalArgumentException> {

    @Override
    public Response toResponse(IllegalArgumentException exception) {
        return Response.status(Response.Status.BAD_REQUEST)
            .entity(new ErrorResponse("INVALID_ARGUMENT", exception.getMessage()))
            .build();
    }
}
```

**O un mapper genérico (similar a `@RestControllerAdvice`):**
```java
@Provider
public class GlobalExceptionMapper implements ExceptionMapper<Exception> {

    @Inject
    Logger log;

    @Override
    public Response toResponse(Exception exception) {
        log.error("Unhandled exception", exception);

        if (exception instanceof CustomerNotFoundException) {
            return Response.status(Response.Status.NOT_FOUND)
                .entity(new ErrorResponse("CUSTOMER_NOT_FOUND", exception.getMessage()))
                .build();
        }
        if (exception instanceof IllegalArgumentException) {
            return Response.status(Response.Status.BAD_REQUEST)
                .entity(new ErrorResponse("INVALID_ARGUMENT", exception.getMessage()))
                .build();
        }
        // ... más casos

        return Response.status(Response.Status.INTERNAL_SERVER_ERROR)
            .entity(new ErrorResponse("INTERNAL_ERROR", "An unexpected error occurred"))
            .build();
    }
}
```

**Tabla de migración Exception Handling:**

| Spring | Quarkus/JAX-RS |
|---|---|
| `@RestControllerAdvice` | `@Provider` + `ExceptionMapper<T>` |
| `@ExceptionHandler(X.class)` | `implements ExceptionMapper<X>` |
| `ResponseEntity.status(s).body(b)` | `Response.status(s).entity(b).build()` |
| `HttpStatus.NOT_FOUND` | `Response.Status.NOT_FOUND` |
| Método por excepción | Una clase por excepción o un mapper genérico |

### Fase 8: Configuration Classes — @Configuration → CDI

**ANTES (Spring):**
```java
package com.jotace.accountmanagement.infrastructure.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class DomainConfig {

    @Bean
    public RetrieveAccountsUseCase retrieveAccountsUseCase(AccountRepositoryPort repository) {
        return new AccountQueryService(repository);
    }
}
```

**DESPUÉS (Quarkus/CDI):**
```java
package com.jotace.accountmanagement.infrastructure.config;

import jakarta.enterprise.context.ApplicationScoped;
import jakarta.enterprise.inject.Produces;
import jakarta.inject.Inject;
import jakarta.inject.Singleton;

@ApplicationScoped
public class DomainConfig {

    @Inject
    AccountRepositoryPort repository;

    @Produces
    @Singleton
    public RetrieveAccountsUseCase retrieveAccountsUseCase() {
        return new AccountQueryService(repository);
    }
}
```

**O si los servicios de aplicación ya usan `@ApplicationScoped` (recomendado), no se necesita config en absoluto** — CDI resuelve las dependencias automáticamente.

### Fase 9: External HTTP Clients — WebClient → REST Client

Si el microservicio se comunica con otros servicios vía HTTP:

**ANTES (Spring WebClient):**
```java
package com.jotace.accountmanagement.infrastructure.adapters.outbound.external;

import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;

@Component
public class CustomerServiceClient {

    private final WebClient webClient;

    public CustomerServiceClient(WebClient.Builder webClientBuilder) {
        this.webClient = webClientBuilder.baseUrl("http://customer-service").build();
    }

    public CustomerResponse getCustomer(String cu) {
        return webClient.get()
            .uri("/customer-management/customer/retrieve?cu={cu}", cu)
            .retrieve()
            .bodyToMono(CustomerResponse.class)
            .block();
    }
}
```

**DESPUÉS (Quarkus REST Client Reactive):**

Primero, definir una interfaz REST Client:

```java
package com.jotace.accountmanagement.infrastructure.adapters.outbound.external;

import jakarta.ws.rs.GET;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.QueryParam;
import org.eclipse.microprofile.rest.client.inject.RegisterRestClient;

@Path("/customer-management/customer")
@RegisterRestClient(configKey = "customer-service")
public interface CustomerServiceRestClient {

    @GET
    @Path("/retrieve")
    CustomerResponse getCustomer(@QueryParam("cu") String cu);
}
```

Luego, configurar en `application.properties`:

```properties
# REST Client configuration
customer-service/mp-rest/url=http://customer-service
customer-service/mp-rest/scope=jakarta.inject.Singleton
```

Y usarlo en el adaptador:

```java
package com.jotace.accountmanagement.infrastructure.adapters.outbound.external;

import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import org.eclipse.microprofile.rest.client.inject.RestClient;

@ApplicationScoped
public class CustomerServiceAdapter {

    @Inject
    @RestClient
    CustomerServiceRestClient client;

    public CustomerResponse getCustomer(String cu) {
        return client.getCustomer(cu);
    }
}
```

**Fault Tolerance con SmallRye:**

```java
@Path("/customer-management/customer")
@RegisterRestClient(configKey = "customer-service")
public interface CustomerServiceRestClient {

    @GET
    @Path("/retrieve")
    @CircuitBreaker(
        requestVolumeThreshold = 5,
        failureRatio = 0.5,
        delay = 30_000L,
        successThreshold = 3
    )
    @Retry(maxRetries = 3, delay = 1000)
    @Timeout(12000)
    CustomerResponse getCustomer(@QueryParam("cu") String cu);
}
```

### Fase 10: Testing — @SpringBootTest → @QuarkusTest

#### 10.1. Tests de Dominio y Aplicación

Los tests de `domain/` y `application/` **NO cambian** — usan JUnit 5 + Mockito sin Spring.

#### 10.2. Tests de REST Controller

**ANTES (Spring — @WebMvcTest):**
```java
@WebMvcTest(AccountController.class)
class AccountControllerTest {
    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private RetrieveAccountsUseCase useCase;

    @Test
    void shouldReturn200WhenAccountsFound() throws Exception {
        when(useCase.findByCustomerId("CU-12345"))
            .thenReturn(List.of(account));

        mockMvc.perform(get("/account-management/account/retrieve")
                .param("cu", "CU-12345"))
            .andExpect(status().isOk());
    }
}
```

**DESPUÉS (Quarkus — @QuarkusTest):**
```java
import io.quarkus.test.junit.QuarkusTest;
import io.quarkus.test.InjectMock;
import static io.restassured.RestAssured.given;
import static org.hamcrest.Matchers.*;

@QuarkusTest
class AccountResourceTest {

    @InjectMock
    RetrieveAccountsUseCase useCase;

    @Test
    void shouldReturn200WhenAccountsFound() {
        when(useCase.findByCustomerId("CU-12345"))
            .thenReturn(List.of(account));

        given()
            .queryParam("cu", "CU-12345")
            .when().get("/account-management/account/retrieve")
            .then()
            .statusCode(200);
    }
}
```

#### 10.3. Tests de Persistencia

**ANTES (Spring — @DataJpaTest + Testcontainers):**
```java
@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@Testcontainers
class AccountJpaRepositoryAdapterTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine");

    @DynamicPropertySource
    static void configure(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUri);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
    }

    @Autowired
    private JpaAccountRepository jpaRepository;
    // ...
}
```

**DESPUÉS (Quarkus — @QuarkusTest + Testcontainers):**
```java
import io.quarkus.test.junit.QuarkusTest;
import io.quarkus.test.common.QuarkusTestResource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.junit.jupiter.api.BeforeEach;
import jakarta.inject.Inject;

@QuarkusTest
@QuarkusTestResource(PostgresTestResource.class)
class AccountJpaRepositoryAdapterTest {

    @Inject
    JpaAccountRepository jpaRepository;

    private AccountJpaRepositoryAdapter adapter;
    // ...
}

// Test Resource Lifecycle Manager
public class PostgresTestResource implements QuarkusTestResourceLifecycleManager {

    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine");

    @Override
    public Map<String, String> start() {
        postgres.start();
        return Map.of(
            "quarkus.datasource.jdbc.url", postgres.getJdbcUrl(),
            "quarkus.datasource.username", postgres.getUsername(),
            "quarkus.datasource.password", postgres.getPassword()
        );
    }

    @Override
    public void stop() {
        postgres.stop();
    }
}
```

**Tabla de migración de Testing:**

| Spring | Quarkus |
|---|---|
| `@SpringBootTest` | `@QuarkusTest` |
| `@WebMvcTest(Controller.class)` | `@QuarkusTest` + REST Assured |
| `@DataJpaTest` | `@QuarkusTest` (con extensión de base de datos) |
| `MockMvc` | REST Assured (`given()...when()...then()`) |
| `@MockBean` / `@MockitoBean` | `@InjectMock` |
| `@DynamicPropertySource` | `QuarkusTestResourceLifecycleManager` |
| `TestRestTemplate` | REST Assured o `WebClient` |
| `@SpringBootTest.WebEnvironment.RANDOM_PORT` | Comportamiento por defecto |

### Fase 11: OpenAPI Documentation

**ANTES (SpringDoc):**
```java
@Tag(name = "Accounts", description = "Account management operations")
@RestController
@RequestMapping("/account-management/account")
public class AccountController {

    @Operation(summary = "Retrieve accounts by customer CU")
    @ApiResponse(responseCode = "200", description = "Accounts found")
    @GetMapping("/retrieve")
    public ResponseEntity<List<AccountResponse>> getAccounts(@RequestParam String cu) {
        // ...
    }
}
```

**DESPUÉS (SmallRye OpenAPI — MicroProfile OpenAPI):**
```java
import org.eclipse.microprofile.openapi.annotations.Operation;
import org.eclipse.microprofile.openapi.annotations.responses.APIResponse;
import org.eclipse.microprofile.openapi.annotations.tags.Tag;

@Path("/account-management/account")
@Tag(name = "Accounts", description = "Account management operations")
public class AccountResource {

    @GET
    @Path("/retrieve")
    @Operation(summary = "Retrieve accounts by customer CU")
    @APIResponse(responseCode = "200", description = "Accounts found")
    public Response getAccounts(@QueryParam("cu") String cu) {
        // ...
    }
}
```

**Eliminar del pom.xml:** La dependencia `springdoc-openapi-starter-webmvc-ui`.
**Agregar:** `quarkus-smallrye-openapi` y `quarkus-swagger-ui` (incluidos en el template de Fase 1).

### Fase 12: Application main class

**ANTES (Spring Boot):**
```java
package com.jotace.accountmanagement;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class AccountManagementApplication {
    public static void main(String[] args) {
        SpringApplication.run(AccountManagementApplication.class, args);
    }
}
```

**DESPUÉS (Quarkus):**
```java
package com.jotace.accountmanagement;

import io.quarkus.runtime.Quarkus;
import io.quarkus.runtime.annotations.QuarkusMain;

@QuarkusMain
public class AccountManagementApplication {
    public static void main(String[] args) {
        Quarkus.run(args);
    }
}
```

**O simplemente eliminar la clase main** — Quarkus no necesita una clase main explícita. El plugin de Maven genera una automáticamente.

## Post-migración: Verificación de código legacy

Después de migrar cada archivo, verificar que no queden anotaciones de Spring:

```bash
# Buscar residuos de Spring en el código fuente (excluyendo domain y application)
echo "=== Spring residues in infrastructure ==="
grep -rn 'org\.springframework\|springframework\.' src/main/java/ 2>/dev/null

echo "=== Spring residues in tests ==="
grep -rn 'org\.springframework\|springframework\.' src/test/java/ 2>/dev/null

echo "=== javax.persistence residues (should be jakarta) ==="
grep -rn 'javax\.persistence' src/main/java/ src/test/java/ 2>/dev/null
```

## Archivos a ELIMINAR (si existen)

```bash
# Archivos específicos de Spring que no tienen equivalente en Quarkus
rm -f src/main/resources/application.yml  # Si se migró a .properties
# Nota: mantener si se agregó quarkus-config-yaml

# Opcional: eliminar código muerto
# spring.factories, spring-devtools, etc.
```

## Archivos a NO TOCAR

```bash
# Migraciones Flyway/Liquibase existentes
# Son SQL estándar, funcionan igual en Quarkus
# Solo verificar la propiedad quarkus.flyway.locations
```

## Compilación y verificación

```bash
# 1. Compilar el proyecto
./mvnw compile -q 2>/dev/null || mvn compile -q

# 2. Ejecutar tests (esperar que fallen por el cambio de framework)
# No te preocupes, los tests se migrarán después

# 3. Verificar que la aplicación arranca
./mvnw quarkus:dev -Dquarkus.http.port=8080 &
sleep 15
curl -s http://localhost:8080/q/health/live | head -20
# Detener
kill %1 2>/dev/null
```

## Migración de tests (orden)

Después de migrar todo el código fuente:

1. Eliminar imports y anotaciones Spring de todos los tests
2. Cambiar `@SpringBootTest` → `@QuarkusTest`
3. Cambiar `MockMvc` → REST Assured
4. Cambiar `@MockBean` → `@InjectMock`
5. Cambiar `@DataJpaTest` → `@QuarkusTest` + `QuarkusTestResourceLifecycleManager`
6. Migrar `@DynamicPropertySource` → `QuarkusTestResourceLifecycleManager`
7. Ejecutar `./mvnw test` y corregir errores

## Errores comunes de migración

### 🔴 MQ-1: javax.persistence en lugar de jakarta.persistence
```java
// ❌ MAL (Spring Boot 2.x legacy)
import javax.persistence.Entity;

// ✅ BIEN (Jakarta namespace estándar)
import jakarta.persistence.Entity;
```

### 🔴 MQ-2: componentModel="spring" en MapStruct
```java
// ❌ MAL
@Mapper(componentModel = "spring")

// ✅ BIEN
@Mapper(componentModel = "cdi")
```

### 🔴 MQ-3: @PostConstruct anidado esperando contexto Spring
```java
// ❌ MAL - El método espera que Spring haya inyectado todo
@PostConstruct
void init() { ... }

// ✅ BIEN - CDI respeta @PostConstruct igual, pero verificar que @Inject se use
```

### 🔴 MQ-4: Uso de ApplicationContext de Spring
```java
// ❌ MAL
import org.springframework.context.ApplicationContext;

// ✅ BIEN - Usar CDI
import jakarta.enterprise.inject.Instance;
import jakarta.enterprise.context.ApplicationScoped;
```

### 🔴 MQ-5: MockMvc en tests migrados
```java
// ❌ MAL
mockMvc.perform(get("/path"))

// ✅ BIEN - Usar REST Assured
given().when().get("/path").then().statusCode(200)
```

### 🔴 MQ-6: RestTemplate o WebClient de Spring
```java
// ❌ MAL
org.springframework.web.reactive.function.client.WebClient

// ✅ BIEN - Usar REST Client
org.eclipse.microprofile.rest.client.inject.RestClient
```

### 🔴 MQ-7: Perder validación @Valid en JAX-RS
```java
// Quarkus con quarkus-hibernate-validator soporta @Valid
// Asegurarse de tener la dependencia

@POST
@Path("/initiate")
public Response createAccount(@Valid CreateAccountRequest request) { ... }
// Si no funciona, agregar @BeanParam
```

### 🔴 MQ-8: Cache de Spring (@Cacheable, @CacheEvict)
```java
// ❌ MAL
import org.springframework.cache.annotation.Cacheable;

// ✅ BIEN - Quarkus tiene su propia extensión de cache
// Agregar quarkus-cache en pom.xml
import io.quarkus.cache.CacheResult;
import io.quarkus.cache.CacheInvalidate;

@CacheResult(cacheName = "accounts")
public List<Account> findByCustomerId(String cu) { ... }

@CacheInvalidate(cacheName = "accounts")
public void createAccount(Account account) { ... }
```

## Resumen de extensiones Quarkus requeridas

| Funcionalidad | Extensión Quarkus |
|---|---|
| REST API | `quarkus-resteasy-reactive`, `quarkus-resteasy-reactive-jackson` |
| Persistencia | `quarkus-hibernate-orm-panache` |
| Driver BD | `quarkus-jdbc-postgresql` (o mysql, h2, etc.) |
| Validación | `quarkus-hibernate-validator` |
| Migraciones | `quarkus-flyway` |
| OpenAPI | `quarkus-smallrye-openapi`, `quarkus-swagger-ui` |
| Cliente HTTP | `quarkus-rest-client-reactive`, `quarkus-rest-client-reactive-jackson` |
| Fault Tolerance | `quarkus-smallrye-fault-tolerance` |
| CDI | `quarkus-arc` (incluido por defecto) |
| Health | `quarkus-smallrye-health` |
| Metrics | `quarkus-micrometer` (o `quarkus-smallrye-metrics`) |
| Cache | `quarkus-cache` |
| YAML config | `quarkus-config-yaml` |
| Test | `quarkus-junit5`, REST Assured |
| Logging JSON | `quarkus-logging-json` |
| Mail | `quarkus-mailer` |
| Scheduler | `quarkus-scheduler` |

---

**NOTA IMPORTANTE:** Si la aplicación usa funcionalidades específicas de Spring Boot que no tienen equivalente directo en Quarkus (como Spring Cloud, Spring Security OAuth2, Spring Batch, Spring Cloud Stream, etc.), consulta la [guía oficial de migración de Spring a Quarkus](https://quarkus.io/guides/spring-di) y el [catálogo de extensiones Quarkus](https://quarkus.io/extensions/) para encontrar alternativas.
