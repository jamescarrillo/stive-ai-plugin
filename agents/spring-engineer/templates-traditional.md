# Spring Engineer — Templates: Modo Tradicional / Adaptación

> Referenciado por `agents/spring-engineer.agent.md`. Aplica en `projectStructure` = `traditional` o `mixed`: respeta la estructura existente del proyecto (no impone hexagonal).

### Modo Adaptación — Proyecto Tradicional o Hexagonal con estructura propia

Antes de generar cualquier código, ejecutar:

```bash
# Mapear estructura real del proyecto
echo "=== Estructura de paquetes Java ==="
find src/main/java -type d | sed "s|src/main/java/||" | sort

echo ""
echo "=== Clases existentes relevantes ==="
find src/main/java -name "*.java" -not -path "*/test/*" | sort | head -50
```

Construir el mapa mental:
```
BASE_PACKAGE: [detectado]
Estructura encontrada:
  controllers/  → [lista de clases]
  services/     → [lista de clases]
  repositories/ → [lista de clases]
  models/       → [lista de clases]
  [otros paquetes encontrados]
```

**Reglas absolutas en Modo Adaptación:**
1. **Respetar naming conventions**: si el proyecto usa `AccountService`, el nuevo servicio para pagos es `PaymentService`, no `InitiatePaymentService`.
2. **Respetar package structure**: si los controllers están en `com.example.web.controllers`, el nuevo controller va ahí, no en `infrastructure/adapters/inbound/rest/`.
3. **Respetar patrones de inyección**: si el proyecto usa `@Autowired` en campos, seguir ese patrón (aunque constructor injection sea preferible).
4. **Respetar el estilo de DTOs**: si el proyecto tiene `AccountDTO`, el nuevo es `PaymentDTO`, no `InitiatePaymentRequest`.
5. **NO imponer hexagonal**: si el proyecto es tradicional, NO crear `domain/`, `ports/`, ni `adapters/`.

### Template genérico Modo Tradicional — Service

```java
// [paquete].service.[NombreService].java  (o ServiceImpl si el proyecto usa ese patrón)
// Anotación según lo que usa el proyecto (@Service, @Component, o ninguna si usa @Bean)
@Service  // reemplazar si el proyecto usa otro patrón
public class [Nombre]Service {

    private final [Nombre]Repository repository;
    // Agregar otras dependencias según necesidad

    // Inyección por constructor (preferido) o por campo si el proyecto lo hace así
    public [Nombre]Service([Nombre]Repository repository) {
        this.repository = repository;
    }

    public [ReturnType] [methodName]([Params]) {
        // 1. Validar entrada
        // 2. Lógica de negocio
        // 3. Persistir o consultar
        // 4. Retornar
    }
}
```

### Template genérico Modo Tradicional — Controller

```java
// [paquete].controller.[Nombre]Controller.java
@RestController
@RequestMapping("/api/[recurso]")  // respetar el prefijo que usa el proyecto (/api, /v1, etc.)
public class [Nombre]Controller {

    private final [Nombre]Service service;

    public [Nombre]Controller([Nombre]Service service) {
        this.service = service;
    }

    @PostMapping
    public ResponseEntity<[Nombre]DTO> create(@Valid @RequestBody [Nombre]Request request) {
        return ResponseEntity.status(HttpStatus.CREATED).body(service.create(request));
    }

    @GetMapping("/{id}")
    public ResponseEntity<[Nombre]DTO> findById(@PathVariable String id) {
        return ResponseEntity.ok(service.findById(id));
    }
}
```

---

