---
name: quarkus-engineer-templates-hexagonal
description: Material de soporte de quarkus-engineer (no es un agente seleccionable).
user-invocable: false
---

# Quarkus Engineer — Templates: Modo Hexagonal

> Referenciado por `agents/quarkus-engineer/quarkus-engineer.agent.md`. Aplica en `projectStructure` = `new` o `hexagonal` (CDI, JAX-RS, Panache, REST Assured).

## Templates: Modo Hexagonal

### Application Service (`@ApplicationScoped`)

```java
package [basePackage].application.service;

import [basePackage].application.ports.inbound.[BianVerb][BusinessObject]UseCase;
import [basePackage].application.ports.outbound.[BusinessObject]RepositoryPort;
import [basePackage].domain.exception.[BusinessObject]NotFoundException;
import [basePackage].domain.model.[BusinessObject];
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.transaction.Transactional;

// Nota: @ApplicationScoped es requerido por CDI para inyección automática.
// No hay DomainConfig en Quarkus — CDI descubre este bean por su scope.
@ApplicationScoped
public class [BianVerb][BusinessObject]Service implements [BianVerb][BusinessObject]UseCase {

    private final [BusinessObject]RepositoryPort repository;

    // CDI inyecta por constructor cuando hay exactamente uno — sin @Inject necesario
    public [BianVerb][BusinessObject]Service([BusinessObject]RepositoryPort repository) {
        this.repository = repository;
    }

    @Override
    @Transactional  // jakarta.transaction.Transactional (NO Spring)
    public [BusinessObject] execute([BianVerb][BusinessObject]Command command) {
        // 1. Validar que el recurso no exista (si aplica)
        if (repository.existsBy[Id](command.[id]())) {
            throw new [BusinessObject]AlreadyExistsException(command.[id]());
        }
        // 2. Crear el Aggregate Root con lógica de dominio
        var [businessObject] = [BusinessObject].[bianVerb](command.[param1](), command.[param2]());
        // 3. Persistir y retornar
        return repository.save([businessObject]);
    }
}
```

### Controller JAX-RS

```java
package [basePackage].infrastructure.adapters.inbound.rest;

import [basePackage].application.ports.inbound.[BianVerb][BusinessObject]UseCase;
import [basePackage].infrastructure.adapters.inbound.rest.dto.[BianVerb][BusinessObject]Request;
import [basePackage].infrastructure.adapters.inbound.rest.dto.[BianVerb][BusinessObject]Response;
import [basePackage].infrastructure.adapters.inbound.rest.mapper.[BianVerb][BusinessObject]RestMapper;
import jakarta.validation.Valid;
import jakarta.ws.rs.*;
import jakarta.ws.rs.core.*;
import org.eclipse.microprofile.openapi.annotations.Operation;
import org.eclipse.microprofile.openapi.annotations.tags.Tag;

@Path("/[service-domain]/[behavior-qualifier]")
@Produces(MediaType.APPLICATION_JSON)
@Consumes(MediaType.APPLICATION_JSON)
@Tag(name = "[BusinessObject]", description = "[descripción del recurso]")
public class [BianVerb][BusinessObject]Controller {

    private final [BianVerb][BusinessObject]UseCase useCase;
    private final [BianVerb][BusinessObject]RestMapper mapper;

    // CDI inyecta por constructor cuando hay exactamente uno — sin @Inject por campo
    public [BianVerb][BusinessObject]Controller([BianVerb][BusinessObject]UseCase useCase,
                                                [BianVerb][BusinessObject]RestMapper mapper) {
        this.useCase = useCase;
        this.mapper = mapper;
    }

    @POST
    @Path("/[bianverb]")
    @Operation(summary = "[descripción de la operación]")
    public Response [bianVerb](@Valid [BianVerb][BusinessObject]Request request) {
        var result = useCase.execute(mapper.toCommand(request));
        return Response.status(Response.Status.CREATED)
                .entity(mapper.toResponse(result))
                .build();
    }

    @GET
    @Path("/{id}/retrieve")
    @Operation(summary = "Recuperar [BusinessObject] por ID")
    public Response retrieve(@PathParam("id") String id) {
        // Para operaciones Retrieve, el Use Case retorna el dominio
        var result = useCase.execute(new Retrieve[BusinessObject]Query(id));
        return Response.ok(mapper.toResponse(result)).build();
    }
}
```

### ExceptionMapper (`@Provider`)

```java
package [basePackage].infrastructure.config;

import [basePackage].domain.exception.[BusinessObject]NotFoundException;
import jakarta.ws.rs.core.Response;
import jakarta.ws.rs.ext.ExceptionMapper;
import jakarta.ws.rs.ext.Provider;
import java.time.Instant;
import java.util.Map;

@Provider
public class [BusinessObject]NotFoundExceptionMapper implements ExceptionMapper<[BusinessObject]NotFoundException> {

    @Override
    public Response toResponse([BusinessObject]NotFoundException ex) {
        return Response.status(Response.Status.NOT_FOUND)
                .entity(Map.of(
                    "status", 404,
                    "code", "[BUSINESS_OBJECT]_NOT_FOUND",
                    "message", ex.getMessage(),
                    "timestamp", Instant.now().toString()
                ))
                .build();
    }
}

// Repetir para cada excepción de dominio del spec.
// Errores de validación (ConstraintViolationException) — mapper genérico:
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
                .entity(Map.of(
                    "status", 400,
                    "code", "VALIDATION_ERROR",
                    "errors", errors,
                    "timestamp", Instant.now().toString()
                ))
                .build();
    }
}
```

### JPA Entity (sin cambios respecto a Spring)

Las entidades JPA usan `jakarta.persistence` en ambos frameworks — sin cambios:

```java
package [basePackage].infrastructure.adapters.outbound.database;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name = "[tabla_snake_case]")
@Getter
@Setter
@NoArgsConstructor
public class [BusinessObject]Entity {

    @Id
    @Column(name = "id", nullable = false, length = 36)
    private String id;

    @Column(name = "[campo]", nullable = false)
    private [tipo] [campo];

    // ... más campos

    public [BusinessObject]Entity(String id, [tipo] [campo]) {
        this.id = id;
        this.[campo] = [campo];
    }
}
```

### Panache Repository (`PanacheRepositoryBase`)

```java
package [basePackage].infrastructure.adapters.outbound.database;

import io.quarkus.hibernate.orm.panache.PanacheRepositoryBase;
import jakarta.enterprise.context.ApplicationScoped;
import java.util.List;
import java.util.Optional;

@ApplicationScoped
public class [BusinessObject]PanacheRepository implements PanacheRepositoryBase<[BusinessObject]Entity, String> {

    public Optional<[BusinessObject]Entity> findBy[Id](String [id]) {
        return find("[campo_id]", [id]).firstResultOptional();
    }

    public List<[BusinessObject]Entity> findBy[OtroFiltro](String valor) {
        return list("[campo]", valor);
    }

    public boolean existsBy[Id](String [id]) {
        return count("[campo_id]", [id]) > 0;
    }
}
```

### JPA Adapter (implementa el Outbound Port)

```java
package [basePackage].infrastructure.adapters.outbound.database;

import [basePackage].application.ports.outbound.[BusinessObject]RepositoryPort;
import [basePackage].domain.model.[BusinessObject];
import [basePackage].infrastructure.adapters.outbound.database.mapper.[BusinessObject]JpaMapper;
import jakarta.enterprise.context.ApplicationScoped;
import java.util.List;
import java.util.Optional;

@ApplicationScoped
public class [BusinessObject]JpaAdapter implements [BusinessObject]RepositoryPort {

    private final [BusinessObject]PanacheRepository repository;
    private final [BusinessObject]JpaMapper mapper;

    public [BusinessObject]JpaAdapter([BusinessObject]PanacheRepository repository,
                                       [BusinessObject]JpaMapper mapper) {
        this.repository = repository;
        this.mapper = mapper;
    }

    @Override
    public [BusinessObject] save([BusinessObject] domain) {
        var entity = mapper.toEntity(domain);
        repository.persistAndFlush(entity);
        return mapper.toDomain(entity);
    }

    @Override
    public Optional<[BusinessObject]> findBy[Id](String [id]) {
        return repository.findBy[Id]([id]).map(mapper::toDomain);
    }

    @Override
    public boolean existsBy[Id](String [id]) {
        return repository.existsBy[Id]([id]);
    }
}
```

### MapStruct (CDI)

```java
package [basePackage].infrastructure.adapters.outbound.database.mapper;

import [basePackage].domain.model.[BusinessObject];
import [basePackage].infrastructure.adapters.outbound.database.[BusinessObject]Entity;
import org.mapstruct.Mapper;

// IMPORTANTE: componentModel = "cdi" en Quarkus (no "spring")
@Mapper(componentModel = "cdi")
public interface [BusinessObject]JpaMapper {
    [BusinessObject]Entity toEntity([BusinessObject] domain);
    [BusinessObject] toDomain([BusinessObject]Entity entity);
}
```

```java
// REST Mapper
@Mapper(componentModel = "cdi")
public interface [BianVerb][BusinessObject]RestMapper {
    [BianVerb][BusinessObject]Command toCommand([BianVerb][BusinessObject]Request request);
    [BianVerb][BusinessObject]Response toResponse([BusinessObject] domain);
}
```

### Tests `@QuarkusTest` + REST Assured

```java
// Test de Controller / Integration (REST Assured)
package [basePackage].infrastructure.adapters.inbound.rest;

import io.quarkus.test.junit.QuarkusTest;
import io.quarkus.test.junit.mockito.InjectMock;
import org.junit.jupiter.api.Test;
import static io.restassured.RestAssured.given;
import static org.hamcrest.Matchers.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@QuarkusTest
class [BianVerb][BusinessObject]ControllerTest {

    @InjectMock
    [BianVerb][BusinessObject]UseCase useCase;

    @Test
    void should[BianVerb][BusinessObject]Successfully() {
        when(useCase.execute(any())).thenReturn(/* domain object */);

        given()
            .contentType("application/json")
            .body("""
                {
                    "[campo1]": "[valor1]",
                    "[campo2]": "[valor2]"
                }
                """)
        .when()
            .post("/[service-domain]/[behavior-qualifier]/[bianverb]")
        .then()
            .statusCode(201)
            .body("[campo]", notNullValue());
    }

    @Test
    void shouldReturn400WhenInvalidRequest() {
        given()
            .contentType("application/json")
            .body("{}")  // campos requeridos faltantes
        .when()
            .post("/[service-domain]/[behavior-qualifier]/[bianverb]")
        .then()
            .statusCode(400)
            .body("code", equalTo("VALIDATION_ERROR"));
    }

    @Test
    void shouldReturn404When[BusinessObject]NotFound() {
        when(useCase.execute(any()))
            .thenThrow(new [BusinessObject]NotFoundException("id-inexistente"));

        given()
        .when()
            .get("/[service-domain]/[behavior-qualifier]/id-inexistente/retrieve")
        .then()
            .statusCode(404)
            .body("code", equalTo("[BUSINESS_OBJECT]_NOT_FOUND"));
    }
}
```

```java
// Test unitario de Application Service (puro Mockito — sin @QuarkusTest)
package [basePackage].application.service;

import [basePackage].application.ports.outbound.[BusinessObject]RepositoryPort;
import [basePackage].domain.exception.[BusinessObject]AlreadyExistsException;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)  // Puro Mockito — más rápido que @QuarkusTest
class [BianVerb][BusinessObject]ServiceTest {

    @Mock
    [BusinessObject]RepositoryPort repository;

    @InjectMocks
    [BianVerb][BusinessObject]Service service;

    @Test
    void should[BianVerb]Successfully() {
        when(repository.existsBy[Id](any())).thenReturn(false);
        when(repository.save(any())).thenAnswer(inv -> inv.getArgument(0));

        var result = service.execute(new [BianVerb][BusinessObject]Command(/* params */));

        assertThat(result).isNotNull();
        verify(repository).save(any());
    }

    @Test
    void shouldThrowWhen[BusinessObject]AlreadyExists() {
        when(repository.existsBy[Id](any())).thenReturn(true);

        assertThatThrownBy(() -> service.execute(new [BianVerb][BusinessObject]Command(/* params */)))
            .isInstanceOf([BusinessObject]AlreadyExistsException.class);

        verify(repository, never()).save(any());
    }
}
```

```java
// Test de JPA Adapter (requiere datasource — usar @QuarkusTest con H2 en test profile)
package [basePackage].infrastructure.adapters.outbound.database;

import io.quarkus.test.junit.QuarkusTest;
import jakarta.inject.Inject;
import jakarta.transaction.Transactional;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.*;

@QuarkusTest
class [BusinessObject]JpaAdapterTest {

    @Inject
    [BusinessObject]JpaAdapter adapter;

    @Test
    @Transactional
    void shouldSaveAndRetrieve[BusinessObject]() {
        var domain = /* crear objeto de dominio */;
        var saved = adapter.save(domain);

        var found = adapter.findBy[Id](saved.[getId]());
        assertThat(found).isPresent();
        assertThat(found.get().[getCampo]()).isEqualTo(domain.[getCampo]());
    }

    @Test
    void shouldReturnEmptyWhenNotFound() {
        var result = adapter.findBy[Id]("id-inexistente");
        assertThat(result).isEmpty();
    }
}
```

> **Nota test profile**: en `src/main/resources/application.properties`:
> ```properties
> %test.quarkus.datasource.db-kind=h2
> %test.quarkus.datasource.jdbc.url=jdbc:h2:mem:testdb;MODE=PostgreSQL
> %test.quarkus.hibernate-orm.database.generation=drop-and-create
> %test.quarkus.flyway.migrate-at-start=false
> ```

---

