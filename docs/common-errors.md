# Memory: Architecture Decision Records & Common Anti-Patterns

Este documento registra las decisiones arquitectónicas clave (ADRs) y los errores más frecuentes para evitar regresiones o propuestas de código que rompan el diseño base.

## ADR 1: Adopción estricta de Arquitectura Hexagonal
* **Contexto:** Necesitamos aislar las reglas de negocio de los cambios tecnológicos (Bases de Datos, APIs, Frameworks).
* **Decisión:** El núcleo de la aplicación (`domain`) no debe tener dependencias externas. Toda comunicación hacia afuera se hace mediante interfaces (`ports/outbound`), y toda comunicación hacia adentro mediante interfaces (`ports/inbound`).
* **Consecuencia:** Se requiere crear clases de mapeo entre los DTOs/Entidades JPA y los modelos de Dominio, lo que aumenta la cantidad de clases, pero garantiza el desacoplamiento.

## ADR 2: Inyección de Dependencias de los Servicios de Aplicación

* **Contexto:** Este proyecto implementa migración activa de Spring Boot → Quarkus. `@Service` es una anotación de Spring (`org.springframework.stereotype.Service`). Si los Application Services la usan, al migrar hay que tocarlos aunque su lógica no cambió.

* **Decisión:** Los Application Services en `application/service/` **no usan `@Service`**. Son POJO puros con constructor. Se registran como `@Bean` en `infrastructure/config/DomainConfig.java`.

* **Por qué esto importa en este proyecto (razón concreta):**

  | Sin ADR-2 (`@Service`) | Con ADR-2 (`@Bean`) |
  |------------------------|----------------------|
  | Al migrar a Quarkus: cambiar `@Service` → `@ApplicationScoped` en cada Application Service | Al migrar a Quarkus: solo cambia `DomainConfig.java` → `DomainConfig` con CDI |
  | El Application Service conoce Spring | El Application Service no conoce ningún framework |
  | Fácil de testear igual (`new MiService(mock)`) | Fácil de testear igual (`new MiService(mock)`) |

  > **Nota:** En proyectos sin migración pendiente, `@Service` en application layer es aceptable según Tom Hombergs ("Get Your Hands Dirty on Clean Architecture"). La restricción de este proyecto obedece al roadmap Quarkus, no a purismo arquitectónico.

* **Cómo aplicarlo:**

  ```java
  // ❌ MAL para este proyecto — Spring en la capa de aplicación
  @Service
  public class InitiateAccountService implements InitiateAccountUseCase { ... }

  // ✅ BIEN — POJO puro, registrado desde infrastructure
  public class InitiateAccountService implements InitiateAccountUseCase { ... }
  ```

  ```java
  // infrastructure/config/DomainConfig.java
  @Configuration
  public class DomainConfig {

      @Bean
      public InitiateAccountUseCase initiateAccountUseCase(AccountRepositoryPort repo) {
          return new InitiateAccountService(repo);
      }

      // Un @Bean por cada Application Service del bounded context
  }
  ```

* **Consecuencia:** Una clase `DomainConfig.java` por bounded context en `infrastructure/config/`. Al migrar a Quarkus, esta es la única clase que cambia para ese bounded context.

## ADR 3: Manejo de Excepciones de Negocio
* **Contexto:** Las excepciones de dominio deben propagarse hasta la capa REST para ser transformadas en respuestas HTTP con estructura JSON estandarizada, sin que el dominio conozca HTTP.
* **Decisión:** Las excepciones de negocio heredan de `RuntimeException` y viven en `domain/exception/`. Un `@RestControllerAdvice` en infraestructura captura cada tipo y mapea al código HTTP correspondiente (404, 409, 422).
* **Estructura JSON de error:**
  ```json
  {
    "status": 404,
    "code": "CUSTOMER_NOT_FOUND",
    "message": "Customer with CU CU-99999 not found",
    "timestamp": "2026-05-24T10:30:00Z"
  }
  ```

## ADR 4: Alineación con BIAN Service Domains
* **Contexto:** El banco adopta BIAN como estándar arquitectónico. Cada microservicio debe corresponder a un Service Domain BIAN.
* **Decisión:** El package base será `com.jotace.<serviceDomain>` (ej. `com.jotace.accountmanagement`). Los Inbound Ports se nombran con verbos BIAN (Retrieve, Execute, Initiate, etc.).
* **Consecuencia:** No usar nombres genéricos como `api`, `common` o `core` como paquete raíz.

---

## Common Anti-Patterns (Errores Frecuentes)

### 🔴 AP-1: Inyección por Campo (Field Injection)
```java
// ❌ MAL - Viola el principio de inmutabilidad y dificulta el testing
@RestController
public class AccountController {
    @Autowired
    private RetrieveAccountUseCase useCase;
}
// ✅ BIEN - Constructor injection
public class AccountController {
    private final RetrieveAccountUseCase useCase;
    public AccountController(RetrieveAccountUseCase useCase) {
        this.useCase = useCase;
    }
}
```

### 🔴 AP-2: Usar `@Data` de Lombok en el Dominio
```java
// ❌ MAL - @Data genera equals/hashCode frágil, setters públicos rompen inmutabilidad
@Data
public class Account { ... }

// ✅ BIEN - @Getter + @Builder + constructor privado
@Getter
@Builder
public class Account {
    private final String accountNumber;
    private final Money balance;
}
```

### 🔴 AP-3: Excepciones Técnicas Filtrándose al Cliente
```java
// ❌ MAL - Dejar que Spring devuelva el stacktrace crudo
throw new RuntimeException("Connection refused");

// ✅ BIEN - Capturar en @RestControllerAdvice y devolver JSON estandarizado
@ExceptionHandler(CustomerNotFoundException.class)
public ResponseEntity<ErrorResponse> handleCustomerNotFound(CustomerNotFoundException ex) {
    return ResponseEntity.status(HttpStatus.NOT_FOUND)
        .body(new ErrorResponse("CUSTOMER_NOT_FOUND", ex.getMessage()));
}
```

### 🔴 AP-4: Puerto de Salida con Anotaciones Spring
```java
// ❌ MAL - El outbound port está en application/ports/outbound/ y no debe tener Spring
public interface AccountRepositoryPort extends JpaRepository<Account, String> { }

// ✅ BIEN - Interfaz pura en application, implementación con Spring en infrastructure
// application/ports/outbound/AccountRepositoryPort.java
public interface AccountRepositoryPort {
    List<Account> findByCustomerId(String customerId);
}
// infrastructure/adapters/outbound/database/JpaAccountRepository.java
@Repository
public interface JpaAccountRepository extends JpaRepository<AccountEntity, String> { }
```

### 🔴 AP-5: Mapeo Manual Repetitivo Sin MapStruct
```java
// ❌ MAL - Mapeo manual verboso y propenso a errores
Account account = new Account(entity.getAccountNumber(), entity.getBalance());

// ✅ BIEN - MapStruct generate el mapper en infrastructure
@Mapper(componentModel = "spring")
public interface AccountEntityMapper {
    Account toDomain(AccountEntity entity);
    AccountEntity toEntity(Account domain);
}
```

### 🔴 AP-6: Endpoints sin Versionado
```java
// ❌ MAL - Sin versionado, rompe clientes existentes al cambiar
@GetMapping("/account/retrieve")

// ✅ BIEN - Versionado explícito
@GetMapping("/v1/account-management/account/retrieve")
```

### 🔴 AP-7: Lógica de Negocio en Controladores
```java
// ❌ MAL - Lógica de negocio mezclada con el adaptador REST
@GetMapping("/account-management/account/retrieve")
public List<Account> getAccounts(@RequestParam String cu) {
    if (cu == null || cu.isBlank()) throw new IllegalArgumentException(...);
    return accountRepositoryPort.findByCustomerId(cu);
}

// ✅ BIEN - El controlador solo delega al Inbound Port
@GetMapping("/account-management/account/retrieve")
public List<AccountResponse> getAccounts(@RequestParam String cu) {
    return accountMapper.toResponse(retrieveAccountUseCase.byCustomerCU(cu));
}
```