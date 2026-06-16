---
name: restructure-guide
description: Guía paso a paso para migrar un proyecto Spring Boot tradicional a Quarkus con restructuración a arquitectura hexagonal (Opción B del agente spring-to-quarkus).
---

# Guía: Migración + Restructuración a Hexagonal Quarkus (Opción B)

## Cuándo usar esta guía

Cuando el usuario elige **Opción B** en `spring-to-quarkus`:
- Origen: Spring Boot **tradicional** (`sourceStructure = "traditional"`)
- Destino: Quarkus **hexagonal** (`migrationStyle = "restructure_hexagonal"`)

Esta guía combina dos transformaciones simultáneas:
1. **Migración tecnológica**: Spring Boot → Quarkus (stack)
2. **Restructuración arquitectónica**: tradicional → hexagonal (estructura)

> **Prerequisito**: el proyecto Quarkus de destino debe existir vacío antes de iniciar. Ver el agente `spring-to-quarkus` (Paso 1) para crear el `pom.xml` Quarkus desde cero.

---

## Fase 0 — Auditoría del proyecto Spring tradicional

Antes de restructurar, mapear completamente el código existente:

```bash
echo "=== Entidades Spring (modelo de datos) ==="
find src/main/java -name "*Entity.java" -o -name "*.java" | xargs grep -l "@Entity" 2>/dev/null

echo ""
echo "=== Servicios Spring (@Service) ==="
find src/main/java -name "*Service.java" -o -name "*ServiceImpl.java" 2>/dev/null

echo ""
echo "=== Repositorios Spring ==="
find src/main/java -name "*Repository.java" 2>/dev/null

echo ""
echo "=== Controllers Spring ==="
find src/main/java -name "*Controller.java" 2>/dev/null

echo ""
echo "=== DTOs existentes ==="
find src/main/java \( -name "*DTO.java" -o -name "*Dto.java" -o -name "*Request.java" -o -name "*Response.java" \) 2>/dev/null

echo ""
echo "=== Métodos de negocio en los @Service ==="
grep -rn "public.*(" src/main/java --include="*Service.java" --include="*ServiceImpl.java" 2>/dev/null | grep -v "@" | grep -v "class " | head -40
```

Producir una tabla de mapeo antes de continuar:

| Clase Spring original | Tipo | → Equivalente hexagonal Quarkus |
|---|---|---|
| `[Nombre]Entity.java` | `@Entity` | → `[Nombre].java` (Aggregate Root en `domain/model/`) + `[Nombre]Entity.java` (infra) |
| `[Nombre]Service.java` | `@Service` | → Separar: lógica negocio → `domain/model/`, orquestación → `application/service/` |
| `[Nombre]Repository.java` | `JpaRepository` | → `[Nombre]RepositoryPort.java` (outbound port) + `[Nombre]PanacheRepository.java` (infra) |
| `[Nombre]Controller.java` | `@RestController` | → `[BianVerb][Nombre]Controller.java` con JAX-RS en `infrastructure/adapters/inbound/rest/` |
| `[Nombre]DTO.java` | DTO | → Separar: Command/Query (application) + Request/Response (infra) |

---

## Fase 1 — Extraer el Dominio

### 1.1 Identificar el Aggregate Root

De cada `@Entity` Spring, crear el equivalente puro en `domain/model/`:

```
Regla: Si [NombreEntity] tiene:
  - Un identificador único → es candidato a Aggregate Root o Value Object
  - Relaciones con otras entidades → evaluarlas como parte del aggregate o como entidades separadas
  - Métodos de negocio en el @Service → moverlos al Aggregate Root
```

Template de extracción:

```java
// ANTES: Lógica de negocio dispersa en @Service Spring
@Service
public class AccountService {
    public Account openAccount(String customerId, String type) {
        var entity = new AccountEntity();
        entity.setCustomerId(customerId);
        entity.setType(type);
        entity.setStatus("ACTIVE");
        entity.setBalance(BigDecimal.ZERO);
        // validaciones mezcladas aquí
        return repository.save(entity);
    }
}

// DESPUÉS: Aggregate Root puro en domain/model/
// (sin Spring, sin JPA, sin Jackson)
@Getter
@Builder(access = AccessLevel.PRIVATE)
public class Account {

    private final String accountNumber;
    private final String customerId;
    private final AccountType type;
    private AccountStatus status;
    private Money balance;

    // Fábrica estática — la lógica de creación vive aquí
    public static Account open(String customerId, AccountType type) {
        Objects.requireNonNull(customerId, "customerId requerido");
        Objects.requireNonNull(type, "type requerido");
        return Account.builder()
                .accountNumber(UUID.randomUUID().toString())
                .customerId(customerId)
                .type(type)
                .status(AccountStatus.ACTIVE)
                .balance(Money.zero("COP"))
                .build();
    }

    // Comportamientos de negocio
    public void deposit(Money amount) {
        if (amount.isNegativeOrZero()) throw new InvalidAmountException(amount);
        this.balance = this.balance.add(amount);
    }

    public void close() {
        if (!this.balance.isZero()) throw new AccountNotEmptyException(this.accountNumber);
        this.status = AccountStatus.CLOSED;
    }
}
```

### 1.2 Extraer Value Objects

Identificar campos con validaciones propias o semántica rica:

```
Candidatos a Value Object:
  - Campos de dinero (amount + currency) → Money record
  - Campos con formato específico (email, phone, accountNumber) → Value Object con validación en constructor
  - Enums con comportamiento → considerar clase en lugar de enum
```

```java
// Value Object como Java record (validación en constructor compacto)
public record Money(BigDecimal amount, String currency) {

    public Money {
        Objects.requireNonNull(amount, "amount requerido");
        Objects.requireNonNull(currency, "currency requerido");
        if (amount.compareTo(BigDecimal.ZERO) < 0) {
            throw new InvalidAmountException("El monto no puede ser negativo");
        }
        if (currency.length() != 3) {
            throw new IllegalArgumentException("Currency debe ser código ISO 4217 de 3 letras");
        }
    }

    public static Money zero(String currency) { return new Money(BigDecimal.ZERO, currency); }
    public Money add(Money other) { /* validar misma currency */ return new Money(this.amount.add(other.amount), this.currency); }
    public boolean isZero() { return amount.compareTo(BigDecimal.ZERO) == 0; }
    public boolean isNegativeOrZero() { return amount.compareTo(BigDecimal.ZERO) <= 0; }
}
```

### 1.3 Identificar excepciones de dominio

Por cada validación de negocio en el `@Service` original que lanzaba excepciones:

```java
// domain/exception/
public class AccountNotFoundException extends RuntimeException {
    public AccountNotFoundException(String accountNumber) {
        super("Account not found: " + accountNumber);
    }
}

public class AccountAlreadyExistsException extends RuntimeException {
    public AccountAlreadyExistsException(String accountNumber) {
        super("Account already exists: " + accountNumber);
    }
}

public class InvalidAmountException extends RuntimeException {
    public InvalidAmountException(Money amount) {
        super("Invalid amount: " + amount.amount() + " " + amount.currency());
    }
}
```

---

## Fase 2 — Definir los Puertos

### 2.1 Inbound Ports — desde los métodos del @Controller original

Por cada endpoint del `@RestController` Spring:

```
Regla de mapeo:
  @PostMapping → BianVerb: Initiate o Execute
  @GetMapping  → BianVerb: Retrieve
  @PutMapping  → BianVerb: Update
  @PatchMapping → BianVerb: Update (parcial)
```

```java
// application/ports/inbound/
public interface OpenAccountUseCase {
    Account execute(OpenAccountCommand command);
}

public record OpenAccountCommand(String customerId, AccountType type, String currency) {}

public interface RetrieveAccountUseCase {
    Account byAccountNumber(String accountNumber);
    List<Account> byCustomerId(String customerId);
}
```

### 2.2 Outbound Ports — desde los @Repository originales

```java
// application/ports/outbound/
public interface AccountRepositoryPort {
    Account save(Account account);
    Optional<Account> findByAccountNumber(String accountNumber);
    List<Account> findByCustomerId(String customerId);
    boolean existsByAccountNumber(String accountNumber);
}
```

---

## Fase 3 — Application Services (Quarkus)

Combinar la lógica de orquestación del @Service original con los puertos definidos:

```java
// application/service/
@ApplicationScoped  // CDI requiere scope para inyección
public class OpenAccountService implements OpenAccountUseCase {

    private final AccountRepositoryPort repository;

    public OpenAccountService(AccountRepositoryPort repository) {
        this.repository = repository;
    }

    @Override
    @Transactional
    public Account execute(OpenAccountCommand command) {
        if (repository.existsByAccountNumber(/* generar número */)) {
            throw new AccountAlreadyExistsException(/* número */);
        }
        var account = Account.open(command.customerId(), command.type());
        return repository.save(account);
    }
}
```

---

## Fase 4 — Infrastructure Quarkus

Esta fase sigue exactamente los templates de `quarkus-engineer`:
- **Inbound**: Controllers JAX-RS (`@Path`, `@POST`, `@GET`) + DTOs + MapStruct `componentModel="cdi"`
- **Outbound**: `[Nombre]Entity` (JPA sin cambios) + `[Nombre]PanacheRepository` + `[Nombre]JpaAdapter`
- **Error handling**: `@Provider ExceptionMapper<T>` por cada excepción de dominio

Ver secciones "Templates: Modo Hexagonal" en `quarkus-engineer`.

---

## Fase 5 — Migrar Tests

| Test Spring (origen) | Equivalente Quarkus hexagonal |
|---|---|
| `@SpringBootTest` + `MockMvc` | `@QuarkusTest` + REST Assured |
| `@MockBean` de `@Service` | `@InjectMock` del `UseCase` (Inbound Port) |
| `@DataJpaTest` del `@Repository` | `@QuarkusTest` + H2 en test profile + `[Nombre]JpaAdapter` |
| Test unitario del `@Service` | Test unitario del `Application Service` (puro Mockito — sin `@QuarkusTest`) |
| Test del Aggregate no existía | `[BusinessObject]Test` — nuevo (invariantes y comportamiento) |

---

## Checklist de validación Opción B

```
□ Aggregate Root en domain/ — sin imports jakarta.enterprise, jakarta.ws.rs, io.quarkus
□ Value Objects como records con validaciones en constructor compacto
□ Excepciones de dominio en domain/exception/ — extienden RuntimeException
□ Inbound Ports (UseCases) con Commands/Queries como records en application/ports/inbound/
□ Outbound Ports en application/ports/outbound/ — solo tipos de dominio
□ Application Services con @ApplicationScoped — sin lógica de negocio (eso va en el Aggregate)
□ Controllers JAX-RS con @Path, @Produces/@Consumes JSON
□ PanacheRepositoryBase en infrastructure/adapters/outbound/database/
□ JpaAdapter implementa el OutboundPort
□ @Provider ExceptionMapper por cada excepción de dominio
□ MapStruct componentModel = "cdi" en todos los mappers
□ Tests: @QuarkusTest + REST Assured para controllers; Mockito puro para Application Services
□ Test profile con H2 configurado en application.properties
□ mvn clean compile → sin errores
□ mvn test → todos los tests pasan
□ Domain puro verificado (sin imports de framework en domain/)
□ BIAN paths en los endpoints (initiate, retrieve, update, execute, request)
```
