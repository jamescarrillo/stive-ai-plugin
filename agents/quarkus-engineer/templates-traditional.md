# Quarkus Engineer — Templates: Modo Tradicional / Adaptación

> Referenciado por `agents/quarkus-engineer.agent.md`. Aplica en `projectStructure` = `traditional` o `mixed`: respeta la estructura existente del proyecto.

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

