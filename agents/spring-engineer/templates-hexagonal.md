---
name: spring-engineer-templates-hexagonal
description: Material de soporte de spring-engineer (no es un agente seleccionable).
user-invocable: false
---

# Spring Engineer — Templates: Modo Hexagonal

> Referenciado por `agents/spring-engineer/spring-engineer.agent.md`. Aplica en `projectStructure` = `new` o `hexagonal`: flujo completo TASK-1.x … TASK-7.x (domain → application → infraestructura → tests).

## Flujo de implementación (ejecutar en orden)

Ejecuta las tareas del `tasks.json` en orden de `dependsOn`. Para actualizar el estado de cada tarea (antes/después), aplica el **`## Protocolo de tarea`** definido en el entry `agents/spring-engineer/spring-engineer.agent.md` — es transversal a todos los modos. Implementa el código de cada tarea con los templates de abajo.

Reportar al usuario después de cada tarea:
```
✅ TASK-X.X completada — [nombre de la tarea]
   Archivos: [lista de archivos creados/modificados]
   → Próxima: TASK-X.X — [nombre]
```

> **Reanudación**: Si el agente se interrumpe, la próxima vez que el usuario diga "implementa HU-XXX" leerá el `tasks.json` y continuará desde la primera tarea con `status: "pending"` o `status: "in_progress"`.

---

### TASK-1.x: Capa Domain

#### Template Aggregate Root

```java
// domain/model/[BusinessObject].java
package [basePackage].domain.model;

import [basePackage].domain.exception.[BusinessObject]NotFoundException;
import lombok.Builder;
import lombok.Getter;
import lombok.ToString;
import java.util.Objects;

@Getter
@ToString
@Builder(toBuilder = true)
public class [BusinessObject] {

    private final [IdType] [idField];
    private final [FieldType] [field];
    // ... otros campos

    // Constructor de validación (llamado por Builder.build())
    private [BusinessObject]([IdType] [idField], [FieldType] [field]) {
        this.[idField] = Objects.requireNonNull([idField], "[idField] is required");
        this.[field] = Objects.requireNonNull([field], "[field] is required");
        // Invariante de negocio:
        // if (condición) throw new InvalidXxxStateException("mensaje");
    }

    // Método estático factory (para Initiate/Create)
    public static [BusinessObject] initiate([IdType] id, [FieldType] field) {
        return [BusinessObject].builder()
            .[idField](id)
            .[field](field)
            .build();
    }

    // Métodos de comportamiento con lógica de negocio
    public [BusinessObject] update([FieldType] newField) {
        Objects.requireNonNull(newField, "newField is required");
        return this.toBuilder()
            .[field](newField)
            .build();
    }
}
```

#### Template Value Object (Java record)

```java
// domain/model/[ValueObject].java
package [basePackage].domain.model;

import java.util.Objects;

public record [ValueObject]([FieldType] value) {

    public [ValueObject] {
        Objects.requireNonNull(value, "[ValueObject] value is required");
        // Validaciones adicionales:
        // if (value.isBlank()) throw new IllegalArgumentException("[ValueObject] cannot be blank");
        // if (!value.matches("[patrón]")) throw new IllegalArgumentException("Invalid [ValueObject] format");
    }

    public static [ValueObject] of([FieldType] value) {
        return new [ValueObject](value);
    }
}
```

#### Template Excepción de Dominio

```java
// domain/exception/[BusinessObject]NotFoundException.java
package [basePackage].domain.exception;

public class [BusinessObject]NotFoundException extends RuntimeException {

    private final String [idField];

    public [BusinessObject]NotFoundException(String [idField]) {
        super("[[BUSINESS_OBJECT]_NOT_FOUND] [BusinessObject] not found: " + [idField]);
        this.[idField] = [idField];
    }

    public String get[IdField]() {
        return [idField];
    }
}
```

---

### TASK-2.x: Capa Application

#### Template Inbound Port + Command

```java
// application/ports/inbound/[BianVerb][BusinessObject]UseCase.java
package [basePackage].application.ports.inbound;

import [basePackage].domain.model.[BusinessObject];

public interface [BianVerb][BusinessObject]UseCase {
    [BusinessObject] execute([BianVerb][BusinessObject]Command command);
}
```

```java
// application/ports/inbound/[BianVerb][BusinessObject]Command.java
package [basePackage].application.ports.inbound;

public record [BianVerb][BusinessObject]Command(
    String [param1],
    String [param2]
    // Solo tipos primitivos o tipos de dominio. Nunca DTOs de infra.
) {}
```

#### Template Outbound Port

```java
// application/ports/outbound/[BusinessObject]RepositoryPort.java
package [basePackage].application.ports.outbound;

import [basePackage].domain.model.[BusinessObject];
import java.util.Optional;
import java.util.List;

public interface [BusinessObject]RepositoryPort {
    [BusinessObject] save([BusinessObject] [object]);
    Optional<[BusinessObject]> findBy[Id]([IdType] id);
    List<[BusinessObject]> findAll();
    boolean existsBy[Id]([IdType] id);
}
```

#### Template Application Service

```java
// application/service/[BianVerb][BusinessObject]Service.java
// ADR-2: NO usar @Service aquí. Esta clase se registra como @Bean en infrastructure/config/DomainConfig.java
package [basePackage].application.service;

import [basePackage].application.ports.inbound.[BianVerb][BusinessObject]UseCase;
import [basePackage].application.ports.inbound.[BianVerb][BusinessObject]Command;
import [basePackage].application.ports.outbound.[BusinessObject]RepositoryPort;
import [basePackage].domain.model.[BusinessObject];
import [basePackage].domain.exception.[BusinessObject]AlreadyExistsException;
import org.springframework.transaction.annotation.Transactional;
import java.util.Objects;

public class [BianVerb][BusinessObject]Service implements [BianVerb][BusinessObject]UseCase {

    private final [BusinessObject]RepositoryPort repository;

    public [BianVerb][BusinessObject]Service([BusinessObject]RepositoryPort repository) {
        this.repository = Objects.requireNonNull(repository);
    }

    @Override
    @Transactional
    public [BusinessObject] execute([BianVerb][BusinessObject]Command command) {
        Objects.requireNonNull(command, "command is required");

        if (repository.existsBy[Id](command.[param1]())) {
            throw new [BusinessObject]AlreadyExistsException(command.[param1]());
        }

        [BusinessObject] [object] = [BusinessObject].initiate(
            command.[param1](),
            command.[param2]()
        );

        return repository.save([object]);
    }
}
```

#### Template DomainConfig (registro de Application Services — ADR-2)

```java
// infrastructure/config/DomainConfig.java
package [basePackage].infrastructure.config;

import [basePackage].application.ports.inbound.[BianVerb][BusinessObject]UseCase;
import [basePackage].application.ports.outbound.[BusinessObject]RepositoryPort;
import [basePackage].application.service.[BianVerb][BusinessObject]Service;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class DomainConfig {

    @Bean
    public [BianVerb][BusinessObject]UseCase [bianVerb][BusinessObject]UseCase(
            [BusinessObject]RepositoryPort [businessObject]RepositoryPort) {
        return new [BianVerb][BusinessObject]Service([businessObject]RepositoryPort);
    }

    // Agregar un @Bean por cada Application Service de la HU
}
```

---

### TASK-3.x: Infrastructure — REST

#### Template Request DTO

```java
// infrastructure/adapters/inbound/rest/dto/[BianVerb][BusinessObject]Request.java
package [basePackage].infrastructure.adapters.inbound.rest.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record [BianVerb][BusinessObject]Request(
    @NotBlank(message = "[field] is required")
    @Size(min = 1, max = 100)
    String [field1],

    @NotNull(message = "[field2] is required")
    @Pattern(regexp = "[patrón]", message = "Invalid [field2] format")
    String [field2]
) {}
```

#### Template Response DTO

```java
// infrastructure/adapters/inbound/rest/dto/[BianVerb][BusinessObject]Response.java
package [basePackage].infrastructure.adapters.inbound.rest.dto;

import java.time.LocalDateTime;

public record [BianVerb][BusinessObject]Response(
    String [idField],
    String [field1],
    String [field2],
    LocalDateTime createdAt
) {}
```

#### Template Mapper REST (MapStruct)

```java
// infrastructure/adapters/inbound/rest/mapper/[BianVerb][BusinessObject]RestMapper.java
package [basePackage].infrastructure.adapters.inbound.rest.mapper;

import [basePackage].application.ports.inbound.[BianVerb][BusinessObject]Command;
import [basePackage].infrastructure.adapters.inbound.rest.dto.[BianVerb][BusinessObject]Request;
import [basePackage].infrastructure.adapters.inbound.rest.dto.[BianVerb][BusinessObject]Response;
import [basePackage].domain.model.[BusinessObject];
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;

@Mapper(componentModel = "spring")
public interface [BianVerb][BusinessObject]RestMapper {

    [BianVerb][BusinessObject]Command toCommand([BianVerb][BusinessObject]Request request);

    @Mapping(source = "[idField]", target = "[idField]")
    [BianVerb][BusinessObject]Response toResponse([BusinessObject] [object]);
}
```

#### Template Controller

```java
// infrastructure/adapters/inbound/rest/[BianVerb][BusinessObject]Controller.java
package [basePackage].infrastructure.adapters.inbound.rest;

import [basePackage].application.ports.inbound.[BianVerb][BusinessObject]UseCase;
import [basePackage].infrastructure.adapters.inbound.rest.dto.[BianVerb][BusinessObject]Request;
import [basePackage].infrastructure.adapters.inbound.rest.dto.[BianVerb][BusinessObject]Response;
import [basePackage].infrastructure.adapters.inbound.rest.mapper.[BianVerb][BusinessObject]RestMapper;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.util.Objects;

@RestController
@RequestMapping("/[service-domain]/[behavior-qualifier]")
public class [BianVerb][BusinessObject]Controller {

    private final [BianVerb][BusinessObject]UseCase useCase;
    private final [BianVerb][BusinessObject]RestMapper mapper;

    public [BianVerb][BusinessObject]Controller(
            [BianVerb][BusinessObject]UseCase useCase,
            [BianVerb][BusinessObject]RestMapper mapper) {
        this.useCase = Objects.requireNonNull(useCase);
        this.mapper = Objects.requireNonNull(mapper);
    }

    @PostMapping("/initiate")
    public ResponseEntity<[BianVerb][BusinessObject]Response> initiate(
            @Valid @RequestBody [BianVerb][BusinessObject]Request request) {
        var command = mapper.toCommand(request);
        var result = useCase.execute(command);
        return ResponseEntity.status(HttpStatus.CREATED).body(mapper.toResponse(result));
    }

    @GetMapping("/{id}/retrieve")
    public ResponseEntity<[BianVerb][BusinessObject]Response> retrieve(@PathVariable String id) {
        // implementar según spec
    }
}
```

---

### TASK-4.x: Infrastructure — Persistencia

#### Template Entity JPA

```java
// infrastructure/adapters/outbound/database/[BusinessObject]Entity.java
package [basePackage].infrastructure.adapters.outbound.database;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import java.time.LocalDateTime;

@Entity
@Table(name = "[nombre_tabla]")
@Getter
@Setter
@NoArgsConstructor
public class [BusinessObject]Entity {

    @Id
    @Column(name = "[id_column]", nullable = false, unique = true)
    private String [idField];

    @Column(name = "[campo]", nullable = false)
    private String [campo];

    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    @PrePersist
    protected void onCreate() { createdAt = LocalDateTime.now(); }

    @PreUpdate
    protected void onUpdate() { updatedAt = LocalDateTime.now(); }
}
```

#### Template JPA Repository

```java
// infrastructure/adapters/outbound/database/[BusinessObject]JpaRepository.java
package [basePackage].infrastructure.adapters.outbound.database;

import org.springframework.data.jpa.repository.JpaRepository;
import java.util.Optional;

public interface [BusinessObject]JpaRepository extends JpaRepository<[BusinessObject]Entity, String> {
    Optional<[BusinessObject]Entity> findBy[IdField](String [idField]);
    boolean existsBy[IdField](String [idField]);
}
```

#### Template Mapper JPA (MapStruct)

```java
// infrastructure/adapters/outbound/database/mapper/[BusinessObject]JpaMapper.java
package [basePackage].infrastructure.adapters.outbound.database.mapper;

import [basePackage].domain.model.[BusinessObject];
import [basePackage].infrastructure.adapters.outbound.database.[BusinessObject]Entity;
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;

@Mapper(componentModel = "spring")
public interface [BusinessObject]JpaMapper {

    @Mapping(source = "[campo]", target = "[campo]")
    [BusinessObject]Entity toEntity([BusinessObject] domain);

    @Mapping(source = "[campo]", target = "[campo]")
    [BusinessObject] toDomain([BusinessObject]Entity entity);
}
```

#### Template JPA Adapter

```java
// infrastructure/adapters/outbound/database/[BusinessObject]JpaAdapter.java
package [basePackage].infrastructure.adapters.outbound.database;

import [basePackage].application.ports.outbound.[BusinessObject]RepositoryPort;
import [basePackage].domain.model.[BusinessObject];
import [basePackage].infrastructure.adapters.outbound.database.mapper.[BusinessObject]JpaMapper;
import org.springframework.stereotype.Component;
import java.util.List;
import java.util.Objects;
import java.util.Optional;

@Component
public class [BusinessObject]JpaAdapter implements [BusinessObject]RepositoryPort {

    private final [BusinessObject]JpaRepository repository;
    private final [BusinessObject]JpaMapper mapper;

    public [BusinessObject]JpaAdapter([BusinessObject]JpaRepository repository, [BusinessObject]JpaMapper mapper) {
        this.repository = Objects.requireNonNull(repository);
        this.mapper = Objects.requireNonNull(mapper);
    }

    @Override
    public [BusinessObject] save([BusinessObject] domain) {
        return mapper.toDomain(repository.save(mapper.toEntity(domain)));
    }

    @Override
    public Optional<[BusinessObject]> findBy[Id](String id) {
        return repository.findBy[IdField](id).map(mapper::toDomain);
    }

    @Override
    public List<[BusinessObject]> findAll() {
        return repository.findAll().stream().map(mapper::toDomain).toList();
    }

    @Override
    public boolean existsBy[Id](String id) {
        return repository.existsBy[IdField](id);
    }
}
```

---

### TASK-5.x: GlobalExceptionHandler

```java
// infrastructure/config/GlobalExceptionHandler.java
package [basePackage].infrastructure.config;

import [basePackage].domain.exception.[BusinessObject]NotFoundException;
import [basePackage].domain.exception.[BusinessObject]AlreadyExistsException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import java.net.URI;
import java.time.Instant;
import java.util.stream.Collectors;

@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler([BusinessObject]NotFoundException.class)
    public ProblemDetail handleNotFound([BusinessObject]NotFoundException ex) {
        var detail = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, ex.getMessage());
        detail.setType(URI.create("[BUSINESS_OBJECT]_NOT_FOUND"));
        detail.setProperty("timestamp", Instant.now());
        return detail;
    }

    @ExceptionHandler([BusinessObject]AlreadyExistsException.class)
    public ProblemDetail handleConflict([BusinessObject]AlreadyExistsException ex) {
        var detail = ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT, ex.getMessage());
        detail.setType(URI.create("[BUSINESS_OBJECT]_ALREADY_EXISTS"));
        detail.setProperty("timestamp", Instant.now());
        return detail;
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ProblemDetail handleValidation(MethodArgumentNotValidException ex) {
        var errors = ex.getBindingResult().getFieldErrors().stream()
            .collect(Collectors.toMap(FieldError::getField, FieldError::getDefaultMessage));
        var detail = ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, "Validation failed");
        detail.setType(URI.create("VALIDATION_ERROR"));
        detail.setProperty("errors", errors);
        detail.setProperty("timestamp", Instant.now());
        return detail;
    }

    @ExceptionHandler(Exception.class)
    public ProblemDetail handleGeneric(Exception ex) {
        var detail = ProblemDetail.forStatusAndDetail(HttpStatus.INTERNAL_SERVER_ERROR, "Internal server error");
        detail.setType(URI.create("INTERNAL_ERROR"));
        detail.setProperty("timestamp", Instant.now());
        return detail;
    }
}
```

---

### TASK-6.x: Tests — Domain y Application

#### Template Test del Aggregate

```java
// test/.../domain/[BusinessObject]Test.java
package [basePackage].domain;

import [basePackage].domain.model.[BusinessObject];
import org.junit.jupiter.api.*;
import static org.assertj.core.api.Assertions.*;

@DisplayName("[BusinessObject] — Domain Unit Tests")
class [BusinessObject]Test {

    @Test
    @DisplayName("should create [BusinessObject] with valid parameters")
    void shouldCreateWithValidParameters() {
        var [object] = [BusinessObject].initiate("[idValue]", "[fieldValue]");
        assertThat([object].[getIdField]()).isEqualTo("[idValue]");
        assertThat([object].[getField]()).isEqualTo("[fieldValue]");
    }

    @Test
    @DisplayName("should throw when [idField] is null")
    void shouldThrowWhenIdIsNull() {
        assertThatNullPointerException()
            .isThrownBy(() -> [BusinessObject].initiate(null, "[fieldValue]"))
            .withMessageContaining("[idField] is required");
    }

    @Test
    @DisplayName("should enforce business invariant: [invariante]")
    void shouldEnforceInvariant() {
        assertThatThrownBy(() -> [BusinessObject].initiate("[id]", "[valorInválido]"))
            .isInstanceOf(IllegalArgumentException.class);
    }
}
```

#### Template Test del Application Service

```java
// test/.../application/[BianVerb][BusinessObject]ServiceTest.java
package [basePackage].application;

import [basePackage].application.ports.inbound.[BianVerb][BusinessObject]Command;
import [basePackage].application.ports.outbound.[BusinessObject]RepositoryPort;
import [basePackage].application.service.[BianVerb][BusinessObject]Service;
import [basePackage].domain.model.[BusinessObject];
import [basePackage].domain.exception.[BusinessObject]AlreadyExistsException;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.*;
import org.mockito.junit.jupiter.MockitoExtension;
import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
@DisplayName("[BianVerb][BusinessObject]Service — Use Case Tests")
class [BianVerb][BusinessObject]ServiceTest {

    @Mock private [BusinessObject]RepositoryPort repository;
    @InjectMocks private [BianVerb][BusinessObject]Service service;

    @Test
    @DisplayName("should [bianVerb] [businessObject] successfully")
    void shouldExecuteSuccessfully() {
        var command = new [BianVerb][BusinessObject]Command("[param1]", "[param2]");
        var expected = [BusinessObject].initiate("[param1]", "[param2]");
        when(repository.existsBy[Id]("[param1]")).thenReturn(false);
        when(repository.save(any())).thenReturn(expected);

        var result = service.execute(command);

        assertThat(result).isNotNull();
        verify(repository).save(any([BusinessObject].class));
    }

    @Test
    @DisplayName("should throw when [BusinessObject] already exists")
    void shouldThrowWhenAlreadyExists() {
        var command = new [BianVerb][BusinessObject]Command("[param1]", "[param2]");
        when(repository.existsBy[Id]("[param1]")).thenReturn(true);

        assertThatThrownBy(() -> service.execute(command))
            .isInstanceOf([BusinessObject]AlreadyExistsException.class);

        verify(repository, never()).save(any());
    }
}
```

---

### TASK-7.x: Tests — Infrastructure

#### Template Controller Test (@WebMvcTest)

```java
// test/.../infrastructure/[BianVerb][BusinessObject]ControllerTest.java
package [basePackage].infrastructure;

import [basePackage].application.ports.inbound.[BianVerb][BusinessObject]UseCase;
import [basePackage].domain.exception.[BusinessObject]NotFoundException;
import [basePackage].infrastructure.adapters.inbound.rest.[BianVerb][BusinessObject]Controller;
import [basePackage].infrastructure.adapters.inbound.rest.mapper.[BianVerb][BusinessObject]RestMapper;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest([BianVerb][BusinessObject]Controller.class)
@DisplayName("[BianVerb][BusinessObject]Controller — Web Layer Tests")
class [BianVerb][BusinessObject]ControllerTest {

    @Autowired MockMvc mockMvc;
    @Autowired ObjectMapper objectMapper;
    @MockBean [BianVerb][BusinessObject]UseCase useCase;
    @MockBean [BianVerb][BusinessObject]RestMapper mapper;

    @Test
    @DisplayName("POST /[service-domain]/[behavior-qualifier]/initiate → 201")
    void shouldReturn201OnSuccess() throws Exception {
        when(mapper.toCommand(any())).thenReturn(null);
        when(useCase.execute(any())).thenReturn(null);
        when(mapper.toResponse(any())).thenReturn(null);

        mockMvc.perform(post("/[service-domain]/[behavior-qualifier]/initiate")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(new Object())))
            .andExpect(status().isCreated());
    }

    @Test
    @DisplayName("POST /initiate with invalid body → 400")
    void shouldReturn400OnValidationError() throws Exception {
        mockMvc.perform(post("/[service-domain]/[behavior-qualifier]/initiate")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{}"))
            .andExpect(status().isBadRequest());
    }

    @Test
    @DisplayName("GET /retrieve/{id} when not found → 404")
    void shouldReturn404WhenNotFound() throws Exception {
        when(useCase.execute(any())).thenThrow(new [BusinessObject]NotFoundException("id-inexistente"));

        mockMvc.perform(get("/[service-domain]/[behavior-qualifier]/id-inexistente/retrieve"))
            .andExpect(status().isNotFound())
            .andExpect(jsonPath("$.type").value("[BUSINESS_OBJECT]_NOT_FOUND"));
    }
}
```

---

