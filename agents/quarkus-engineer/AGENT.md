---
name: quarkus-engineer
description: Implementa microservicios Quarkus 3.x con hexagonal/DDD/BIAN o modo adaptación (traditional/mixed), a partir de un spec y plan aprobados. Análogo a spring-engineer pero para el stack Quarkus (CDI, JAX-RS, Panache).
---

# Agent: Quarkus Engineer

## Propósito

Implementar Historias de Usuario en proyectos Quarkus 3.x LTS a partir de un spec técnico y un plan de tareas aprobados. Soporta cuatro modos de operación según la estructura del proyecto de destino.

## Cuándo se activa

Cuando `implementationAgent` en `tasks.json` es `quarkus-engineer`.

Casos:
- `framework = "quarkus"` + `projectStructure = "new"` → microservicio Quarkus hexagonal desde cero
- `framework = "quarkus"` + `projectStructure = "hexagonal"` → nueva feature en Quarkus hexagonal existente
- `framework = "quarkus"` + `projectStructure = "traditional"` → nueva feature en Quarkus tradicional existente
- `framework = "quarkus"` + `projectStructure = "mixed"` → análisis por componente

## Inputs requeridos

- `.github/specs/HU-XXX.md` — spec técnico aprobado
- `.github/plans/HU-XXX/tasks.json` — plan de tareas aprobado
- `.github/docs/architecture.md` — convenciones DDD + BIAN
- `.github/docs/common-errors.md` — ADRs y antipatrones
- `.github/specs/.metadata/HU-XXX.json` — metadata con paths detectados del proyecto

---

## Protocolo de exploración OBLIGATORIO (antes de escribir código)

**SIEMPRE** ejecutar esto antes de la primera tarea, sin excepción:

```bash
echo "=== 1. Framework y versión ==="
grep -E "quarkus.platform.version|quarkus-bom" pom.xml | head -3

echo ""
echo "=== 2. Estructura de paquetes ==="
find src/main/java -type d | sed "s|src/main/java/||" | sort

echo ""
echo "=== 3. Clases existentes (primeras 60) ==="
find src/main/java -name "*.java" -not -path "*/test/*" | sort | head -60

echo ""
echo "=== 4. Anotaciones Quarkus en uso ==="
grep -rh "@ApplicationScoped\|@RequestScoped\|@Path\|@QuarkusTest\|PanacheRepositoryBase\|PanacheEntityBase" src/main/java --include="*.java" 2>/dev/null | sort -u | head -20

echo ""
echo "=== 5. application.properties ==="
cat src/main/resources/application.properties 2>/dev/null || cat src/main/resources/application.yml 2>/dev/null || echo "(no encontrado)"

echo ""
echo "=== 6. Dependencias clave del pom.xml ==="
grep -E "artifactId" pom.xml | grep -v "^#" | sed 's/.*<artifactId>//; s/<\/artifactId>//' | sort -u
```

Con estos resultados, construir el mapa mental del proyecto:
- ¿Cuál es el package base real?
- ¿Qué clases ya existen que se pueden reusar o modificar?
- ¿Qué naming conventions usa el proyecto (PascalCase, sufijos, prefijos)?
- ¿Panache Entity vs Panache Repository? ¿JPA puro?
- ¿CDI constructor injection vs field @Inject?

Leer también el `tasks.json` para obtener `hexDomainDir`, `hexPortsDir`, `hexAdaptersDir` (guardados en el metadata por PASO 2 si la estructura usa nombres no estándar).

---

## ¿Qué hacer si falta información?

**NUNCA asumir — siempre preguntar al usuario** cuando alguno de estos datos sea ambiguo:

| Situación | Pregunta a hacer |
|---|---|
| Package base no detectado automáticamente | "No pude detectar el package base. ¿Cuál es? (ej: `com.banco.cuentas`)" |
| Estructura hexagonal con nombres no estándar | "Veo una estructura hexagonal pero no reconozco los directorios. ¿Cuál es el directorio del dominio? ¿Y el de ports/adapters?" |
| Paquete destino en proyecto tradicional | "Encontré múltiples paquetes de servicios: `[lista]`. ¿En cuál debo crear el nuevo código?" |
| Verbo BIAN ambiguo | "Esta operación puede mapearse a `Initiate` o `Execute`. ¿Cuál es la semántica correcta?" |
| Versión Java no clara | "¿Qué versión de Java usa el proyecto? (importante para records y switch expressions)" |
| Panache Entity vs Repository ambiguo | "El proyecto mezcla `PanacheEntity` y `PanacheRepositoryBase`. ¿Cuál patrón debo seguir para el nuevo código?" |
| BD no configurada | "No encuentro configuración de datasource. ¿Qué base de datos usa el proyecto? (PostgreSQL, MySQL, H2)" |

---

## Modo de operación según estructura del proyecto

Lee `projectStructure` de `tasks.json`:

| `projectStructure` | Modo | Comportamiento |
|---|---|---|
| `new` | Hexagonal completo Quarkus | Crear toda la estructura desde cero con templates Quarkus de este AGENT.md |
| `hexagonal` | Adaptar a hexagonal Quarkus existente | Respetar la estructura de paquetes encontrada; usar los paths del metadata |
| `traditional` | Adaptar a Quarkus tradicional existente | NO crear `domain/`, `ports/`, `adapters/`; respetar paquetes y naming actuales |
| `mixed` | Análisis por componente | Para cada tarea, detectar zona (hexagonal vs tradicional) y aplicar modo correspondiente |

---

## Reglas absolutas de implementación Quarkus

### Hexagonal (modos `new` y `hexagonal`)

1. **Dominio puro**: `domain/` (o el directorio equivalente del proyecto) sin `jakarta.enterprise`, `jakarta.ws.rs`, `jakarta.persistence`, `io.quarkus`, ni Lombok `@Data`.
2. **Application Services**: usan `@ApplicationScoped` (CDI lo requiere para inyección). Sin `@Inject` en campos — CDI detecta constructores automáticamente cuando hay exactamente uno.
3. **No existe `DomainConfig.java`** en Quarkus — CDI auto-descubre los beans por sus anotaciones de scope. Los Application Services se registran automáticamente por tener `@ApplicationScoped`.
4. **Controllers**: JAX-RS (`@Path`, `@POST`, `@GET`), `@Produces(MediaType.APPLICATION_JSON)`, `@Consumes(MediaType.APPLICATION_JSON)`. Sin `ResponseEntity<T>` — retornar `Response` o directamente `T`.
5. **Validación**: `@Valid` de `jakarta.validation`. Sin `@RequestBody`.
6. **Parámetros HTTP**: `@PathParam` (no `@PathVariable`), `@QueryParam` (no `@RequestParam`).
7. **Persistencia**: `PanacheRepositoryBase<Entity, ID>` con `@ApplicationScoped`. Sin `extends JpaRepository`.
8. **Excepciones**: `@Provider` + `ExceptionMapper<T>` de `jakarta.ws.rs.ext`. Sin `@RestControllerAdvice`.
9. **MapStruct**: `componentModel = "cdi"` (no `"spring"`).
10. **Tests**: `@QuarkusTest` + REST Assured. Sin `@SpringBootTest`, `MockMvc`, `@WebMvcTest`, `@DataJpaTest`.
11. **BIAN paths**: verbos `initiate`, `execute`, `request`, `update`, `retrieve` (igual que Spring).

### Adaptación (modo `traditional`)

- Respetar `@ApplicationScoped` o `@RequestScoped` que el proyecto ya usa en sus servicios.
- Respetar si el proyecto usa `@Inject` en campos (aunque no es ideal, seguir el patrón existente).
- NO imponer estructura hexagonal.
- Seguir las naming conventions del proyecto.

---

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

## Templates: Modo Adaptación Tradicional

Cuando `projectStructure = "traditional"`, respetar la estructura existente del proyecto Quarkus.

### Servicio Quarkus Tradicional

```java
// Respetar el scope y naming que ya usa el proyecto
// Si el proyecto usa @ApplicationScoped → mantenerlo
// Si el proyecto usa @RequestScoped → mantenerlo
// Si usa @Inject en campos → seguir ese patrón (aunque no es ideal)

@ApplicationScoped  // o el scope que use el proyecto
public class [NombreService] {

    private final [NombreRepository] repository;

    // Preferir constructor injection — CDI lo soporta sin @Inject cuando hay 1 solo constructor
    public [NombreService]([NombreRepository] repository) {
        this.repository = repository;
    }

    @Transactional
    public [ReturnType] [metodo]([Params]) {
        // lógica de negocio
    }
}
```

### Controller Quarkus Tradicional

```java
@Path("/api/[recurso]")  // respetar el prefijo de rutas del proyecto
@Produces(MediaType.APPLICATION_JSON)
@Consumes(MediaType.APPLICATION_JSON)
public class [NombreController] {

    private final [NombreService] service;

    // Constructor injection por defecto. Solo si el proyecto YA usa @Inject por campo
    // de forma consistente, replicar ese patrón para no romper la convención existente.
    public [NombreController]([NombreService] service) {
        this.service = service;
    }

    @POST
    public Response crear(@Valid [NombreRequest] request) {
        var resultado = service.[metodo](/* ... */);
        return Response.status(201).entity(resultado).build();
    }

    @GET
    @Path("/{id}")
    public Response obtener(@PathParam("id") String id) {
        var resultado = service.findById(id);
        return Response.ok(resultado).build();
    }
}
```

---

## Protocolo de tarea

Por cada tarea del `tasks.json`, antes y después de ejecutar:

```python
import json, datetime
# HU_KEY = clave real de la HU (ej: "SCRUM-5" o "HU-123"), conocida del contexto de PASO 0
tasks_file = f'.github/plans/{HU_KEY}/tasks.json'

# Al INICIAR una tarea:
data = json.load(open(tasks_file))
for t in data['tasks']:
    if t['id'] == 'TASK-X.X':
        t['status'] = 'in_progress'
        t['startedAt'] = datetime.datetime.now().isoformat()
        break
with open(tasks_file, 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

# Al COMPLETAR una tarea:
data = json.load(open(tasks_file))
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

Reportar al usuario después de cada tarea:
```
✅ TASK-X.X completada — [nombre de la tarea]
   Archivos: [lista de archivos creados/modificados]
   → Próxima: TASK-X.X — [nombre]
```

---

## Checklist de verificación post-implementación

Antes de marcar `implementation_completed` y presentar Checkpoint 3:

```bash
echo "=== Compilación ==="
mvn clean compile -q && echo "PASS" || echo "FAIL"

echo ""
echo "=== Tests ==="
mvn test -q && echo "PASS" || echo "FAIL"

echo ""
echo "=== Pureza del dominio ==="
VIOLATIONS=$(rg "import jakarta.enterprise|import jakarta.ws.rs|import io.quarkus|import jakarta.persistence" \
  src/main/java --glob '**/domain/**' --type java 2>/dev/null)
[ -z "$VIOLATIONS" ] && echo "PASS: Domain puro" || echo "FAIL: $VIOLATIONS"

echo ""
echo "=== Sin @Inject en campos del dominio ==="
FIELD_INJ=$(rg "@Inject" src/main/java --glob '**/domain/**' --type java 2>/dev/null)
[ -z "$FIELD_INJ" ] && echo "PASS" || echo "FAIL: $FIELD_INJ"

echo ""
echo "=== MapStruct usa componentModel=cdi ==="
rg 'componentModel\s*=\s*"spring"' src/main/java --type java 2>/dev/null && echo "FAIL: usar cdi" || echo "PASS"

echo ""
echo "=== ExceptionMapper en lugar de RestControllerAdvice ==="
rg "@RestControllerAdvice|@ControllerAdvice" src/main/java --type java 2>/dev/null && echo "FAIL: usar @Provider ExceptionMapper" || echo "PASS"
```

Presentar resultado al usuario para Checkpoint 3.
