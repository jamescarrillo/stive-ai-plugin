---
name: spring-use-case-implementer
description: Dado un spec en .github/specs/, genera el stack hexagonal completo: modelo de dominio, puertos, servicio de aplicación, adaptadores (JPA + REST), mappers y tests.
---

# Instrucciones para el Agente

Este skill es el **corazón de la implementación**. Se ejecuta en el paso 3 del workflow cuando el requerimiento implica exponer APIs REST. Toma un archivo de spec (`.github/specs/<nombre>.md`) y genera todo el código siguiendo Arquitectura Hexagonal + BIAN.

## 0. Prerequisito: proyecto con scaffold existente

Este skill **siempre opera sobre un proyecto existente**. El scaffold (pom.xml, clase Main, application.yml) debe existir antes de activar este skill — generado por el equipo desde PORT (Internal Developer Portal) o Spring Initializr.

```bash
# Verificar que el proyecto existe
if [ ! -d "src/main/java" ]; then
  echo "ERROR: No se encontró src/main/java/ — el proyecto debe existir antes de continuar."
  echo "Generar el scaffold desde PORT o Spring Initializr y volver a intentar."
  exit 1
fi
echo "Proyecto existente detectado — procediendo con la implementación."
```

## 1. Leer el spec (YAML front matter)

**IMPORTANTE:** Este skill trabaja con **1 spec a la vez**. Usa la variable `$SPEC_FILE` para identificar el archivo de spec.

Si el usuario especificó la ruta del spec en su petición (ej. "usa el spec de `.github/specs/HU-123.md`"), úsala directamente. Si no la especificó:

```bash
# Contar cuántos specs hay
SPEC_COUNT=$(ls .github/specs/*.md 2>/dev/null | wc -l)

if [ "$SPEC_COUNT" -eq 0 ]; then
    echo "ERROR: No hay archivos de spec en .github/specs/"
    exit 1
elif [ "$SPEC_COUNT" -eq 1 ]; then
    # Solo hay uno, usarlo automáticamente
    SPEC_FILE=$(ls .github/specs/*.md | head -1)
    echo "Usando único spec encontrado: $SPEC_FILE"
else
    # Hay múltiples — preguntar al usuario cuál usar
    echo "Múltiples specs disponibles. Específica cuál usar:"
    ls .github/specs/*.md
    echo "Ejemplo: .github/specs/HU-123.md"
    # Esperar respuesta del usuario
fi
```

Extrae los metadatos del **YAML front matter** (las líneas entre `---` al inicio del archivo):

| Campo YAML | Propósito | Ejemplo |
|---|---|---|
| `bianservicedomain` | Service Domain BIAN (CamelCase) | `AccountManagement` |
| `basepackage` | Paquete base Java | `com.jotace.accountmanagement` |
| `microservicename` | Nombre del microservicio (kebab-case) | `account-management` |
| `businessobject` | Aggregate Root (PascalCase) | `Account` |
| `behaviorqualifier` | Behavior Qualifier BIAN (lowercase) | `account` |
| `bianverb` | Verbo BIAN (Retrieve, Initiate, Execute...) | `Retrieve` |
| `buildtool` | Gestor de builds | `maven` o `gradle` |
| `database` | Motor BD | `postgresql` |
| `migration` | Herramienta de migraciones | `flyway` o `liquibase` |

Si el spec **no tiene** front matter, determina los valores así:
- **Modo A:** Extráelos del proyecto existente (primer `package` en `src/main/java`)
- **Modo B:** Pregunta al usuario o usa defaults

Además del front matter, el spec debe contener:
- User story (Como/Quiero/Para)
- Contrato de API (método HTTP, path, request params, response body)
- Field Mapping (tabla: campo Java ↔ DTO ↔ columna BD)
- Definición de constantes (enums, types)
- Tabla de base de datos (columnas, tipos, restricciones)
- Criterios de aceptación (CA 1, CA 2, ...)

## 2. Determinar el Service Domain BIAN

Del front matter del spec (o inferido del proyecto), determina:

| Concepto | Fuente | Ejemplo |
|---|---|---|
| Service Domain | `bianservicedomain` del YAML | `AccountManagement` |
| Paquete base | `basepackage` del YAML | `com.jotace.accountmanagement` |
| Business Object (Aggregate) | `businessobject` del YAML | `Account` |
| Behavior Qualifier | `behaviorqualifier` del YAML | `account` |
| Verbo BIAN principal | `bianverb` del YAML | `Retrieve` |

## 3. Validar package real del proyecto (solo Modo A)

En Modo A (proyecto existente), el package real del proyecto SIEMPRE tiene prioridad sobre el YAML del spec.

```bash
# Detectar el package base REAL desde la estructura del proyecto
# Busca el directorio que contiene las capas domain/application/infrastructure
DOMAIN_DIR=$(find src/main/java -type d -name "domain" -not -path "*/test/*" 2>/dev/null | head -1)
if [ -n "$DOMAIN_DIR" ]; then
    # Extraer package: quitar src/main/java/ y el sufijo /domain
    REAL_BASE_PACKAGE=$(echo "$DOMAIN_DIR" | sed 's|src/main/java/||; s|/domain.*||' | tr '/' '.')
else
    # Fallback: buscar cualquier .java y tomar el prefijo común
    REAL_BASE_PACKAGE=$(grep -rh "^package " src/main/java/ --include="*.java" 2>/dev/null \
        | sed 's/package //; s/;//' \
        | sort -u \
        | awk -F'.' '{
            if (NR == 1) { split($0, common, "."); next }
            for (i = 1; i <= length(common); i++)
                if (common[i] != $i) { delete common[i]; break }
          }
          END { for (i in common) printf "%s.", common[i]; print "" }' \
        | sed 's/\.$//')
fi

echo "Package real detectado: $REAL_BASE_PACKAGE"

# Si no se pudo detectar, usar el del spec
if [ -z "$REAL_BASE_PACKAGE" ]; then
    echo "No se pudo detectar package del proyecto. Usando el del spec."
    REAL_BASE_PACKAGE=$SPEC_BASE_PACKAGE
fi
```

Donde `$SPEC_BASE_PACKAGE` viene del YAML front matter del spec (sección 1).

### 3.1. Validación de consistencia

Compara el package real del proyecto con el del spec:

```bash
SPEC_BASE_PACKAGE=$(sed -n 's/^basepackage: //p' "$SPEC_FILE")

if [ "$REAL_BASE_PACKAGE" != "$SPEC_BASE_PACKAGE" ] && [ -n "$SPEC_BASE_PACKAGE" ]; then
    echo "⚠️  WARNING: El package del spec ($SPEC_BASE_PACKAGE) NO coincide"
    echo "   con el package real del proyecto ($REAL_BASE_PACKAGE)."
    echo "   → Usando package del proyecto: $REAL_BASE_PACKAGE"
fi
```

**Regla:** `$REAL_BASE_PACKAGE` (proyecto) manda sobre `$SPEC_BASE_PACKAGE` (spec). Todas las clases generadas usarán `$REAL_BASE_PACKAGE`.

### 3.2. Determinar Service Domain del proyecto

Del `$REAL_BASE_PACKAGE`, extrae el Service Domain BIAN automáticamente:

```bash
# Extraer el último segmento del package como Service Domain
# ej: com.jotace.accountmanagement → accountmanagement
# ej: com.banco.cuentas → cuentas
BIAN_SERVICE_DOMAIN=$(echo "$REAL_BASE_PACKAGE" | awk -F'.' '{print $NF}')
```

**IMPORTANTE:** Usa `$REAL_BASE_PACKAGE` en lugar de `$FINAL_PACKAGE` en todos los templates de código de la sección 4.

### 3.3. Detectar archivos existentes (Modo A — no sobrescribir)

En Modo A (proyecto existente), algunos archivos del dominio pueden YA existir si es el segundo spec que se implementa sobre el mismo microservicio. **No los sobrescribas.** Solo genera los que falten.

```bash
echo "=== Escaneando archivos existentes ==="
PACKAGE_DIR=$(echo "$REAL_BASE_PACKAGE" | tr '.' '/')
BASE_SRC="src/main/java/$PACKAGE_DIR"

# Archivos del dominio que PODRÍAN existir (compartidos entre specs)
EXISTING_FILES=()

for file in \
    "domain/model/${BUSINESS_OBJECT}.java" \
    "domain/model/${BUSINESS_OBJECT}Type.java" \
    "domain/model/${BUSINESS_OBJECT}Status.java" \
    "domain/event/DomainEvent.java" \
    "application/ports/outbound/${BUSINESS_OBJECT}RepositoryPort.java" \
    "infrastructure/adapters/outbound/database/${BUSINESS_OBJECT}Entity.java" \
    "infrastructure/adapters/outbound/database/Jpa${BUSINESS_OBJECT}Repository.java" \
    "infrastructure/adapters/outbound/mapper/${BUSINESS_OBJECT}EntityMapper.java" \
    "infrastructure/config/RestExceptionHandler.java" \
    "infrastructure/config/DomainConfig.java"; do

    FILE_PATH="$BASE_SRC/$file"
    if [ -f "$FILE_PATH" ]; then
        echo "  SKIP: $file (ya existe)"
        EXISTING_FILES+=("$file")
    else
        echo "  GENERATE: $file (nuevo)"
    fi
done

echo "→ ${#EXISTING_FILES[@]} archivo(s) existente(s) serán omitidos"
echo ""
```

**Regla:** Si un archivo ya existe, NO lo generes ni modifiques. Solo genera los archivos nuevos del spec actual (inbound port, application service, controller, DTOs, DTO mapper, y migración si aplica).

## 4. Verificar dependencias en pom.xml

Antes de generar código, verificar que el pom.xml del proyecto tiene las dependencias requeridas por el spec. Si faltan, agregarlas:

```bash
# Dependencias mínimas Spring Boot 3.x hexagonal
MISSING_DEPS=""
grep -q "spring-boot-starter-web"        pom.xml || MISSING_DEPS="$MISSING_DEPS spring-starter-web"
grep -q "spring-boot-starter-data-jpa"   pom.xml || MISSING_DEPS="$MISSING_DEPS spring-starter-jpa"
grep -q "mapstruct"                       pom.xml || MISSING_DEPS="$MISSING_DEPS mapstruct"
grep -q "lombok"                          pom.xml || MISSING_DEPS="$MISSING_DEPS lombok"
grep -q "springdoc-openapi"              pom.xml || MISSING_DEPS="$MISSING_DEPS springdoc-openapi"
grep -q "flyway\|liquibase"              pom.xml || MISSING_DEPS="$MISSING_DEPS flyway"

[ -n "$MISSING_DEPS" ] && echo "⚠️  Dependencias faltantes en pom.xml: $MISSING_DEPS — agregar antes de continuar"
[ -z "$MISSING_DEPS" ] && echo "✅ Dependencias OK"
```

Si faltan dependencias, agregarlas al pom.xml antes de generar código. Usar las versiones alineadas con el Spring Boot parent del proyecto.

## 5. Generar el stack completo por capas

### 5.0. Determinar el package a usar en el código generado

```bash
# Package final para TODAS las clases generadas:
# - Modo A: $REAL_BASE_PACKAGE (detectado del proyecto)
# - Modo B: $BASE_PACKAGE (del spec o del scaffold)
FINAL_PACKAGE="${REAL_BASE_PACKAGE:-$BASE_PACKAGE}"
echo "Package final para generación: $FINAL_PACKAGE"
```

Genera los siguientes archivos **en orden**, SIN usar Lombok `@Data` en dominio, SIN anotaciones Spring en dominio/aplicación.

**IMPORTANTE:** En todos los templates de código de esta sección, reemplaza `$FINAL_PACKAGE` por el valor real. NO uses `$FINAL_PACKAGE`.

### Capa 5.1 — Domain (DDD Tactical Patterns)

#### 5.1.1. Value Objects (DDD)

Por cada campo del **Field Mapping** que encapsule una regla de negocio o identidad, crea un Value Object como Java `record`. Los Value Objects son **inmutables** y no tienen identidad propia.

Usa el Field Mapping del spec para identificar candidatos a Value Object: campos con formato específico, validación de negocio, o que representan conceptos del lenguaje ubicuo (CustomerCu, AccountNumber, Money, CCI, DocumentNumber, Email, Phone).

```java
package $FINAL_PACKAGE.domain.model;

import java.math.BigDecimal;
import java.util.Currency;

public record Money(BigDecimal amount, Currency currency) {

    public Money {
        if (amount == null) throw new IllegalArgumentException("amount must not be null");
        if (currency == null) throw new IllegalArgumentException("currency must not be null");
        if (amount.compareTo(BigDecimal.ZERO) < 0) throw new IllegalArgumentException("amount must not be negative");
    }

    public Money add(Money other) {
        if (!this.currency.equals(other.currency)) throw new IllegalArgumentException("Currency mismatch");
        return new Money(this.amount.add(other.amount), this.currency);
    }

    public Money subtract(Money other) {
        if (!this.currency.equals(other.currency)) throw new IllegalArgumentException("Currency mismatch");
        return new Money(this.amount.subtract(other.amount), this.currency);
    }

    public boolean isGreaterThanOrEqual(Money other) {
        if (!this.currency.equals(other.currency)) throw new IllegalArgumentException("Currency mismatch");
        return this.amount.compareTo(other.amount) >= 0;
    }
}
```

Para Value Objects simples que solo envuelven un String con validación, usar un `record` más sencillo:

```java
package $FINAL_PACKAGE.domain.model;

public record CustomerCu(String value) {
    public CustomerCu {
        if (value == null || value.isBlank()) throw new IllegalArgumentException("Customer CU must not be blank");
    }
}
```

#### 5.1.2. Enum de negocio

Basado en las constantes del spec y su Field Mapping. Crea el enum con los valores exactos del spec.

Archivo: `domain/model/<BusinessObject>Type.java`

```java
package $FINAL_PACKAGE.domain.model;

public enum <BusinessObject>Type {
    SALARY,
    FIXED_TERM,
    CTS,
    CURRENT
}
```

#### 5.1.3. Aggregate Root (DDD Entity con comportamiento)

Usa el **Field Mapping** del spec para determinar los campos exactos y sus tipos. El Aggregate Root debe tener **comportamiento de negocio**, no solo getters.

Reglas DDD:
- Los campos identificadores son Value Objects (CustomerCu, AccountNumber, etc.)
- Los métodos reflejan el **lenguaje ubicuo** del negocio (`deposit()`, `withdraw()`, `open()`, `close()`)
- Las invariantes se validan dentro del Aggregate (saldo suficiente, estado válido, etc.)
- Los Domain Events se registran en `domain.event.*` y se recolectan en el Aggregate para publicación posterior

Archivo: `domain/model/<BusinessObject>.java`

```java
package $FINAL_PACKAGE.domain.model;

import $FINAL_PACKAGE.domain.event.DomainEvent;
import $FINAL_PACKAGE.domain.exception.InsufficientBalanceException;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class <BusinessObject> {
    private final String <field1>;  // identity field — usar Value Object si aplica
    private final String <field2>;
    private BigDecimal <field3>;     // mutable si cambia con operaciones de negocio
    private <BusinessObject>Type type;
    private final List<DomainEvent> domainEvents = new ArrayList<>();

    private <BusinessObject>(Builder builder) {
        this.<field1> = builder.<field1>;
        this.<field2> = builder.<field2>;
        this.<field3> = builder.<field3>;
        this.type = builder.type;
    }

    // --- Business behavior (Ubiquitous Language) ---
    // Métodos de ejemplo — adaptar al spec concreto
    public void deposit(BigDecimal amount) {
        if (amount.compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalArgumentException("Deposit amount must be positive");
        }
        this.<field3> = this.<field3>.add(amount);
        registerEvent(new MoneyDeposited(this.<field1>, amount));
    }

    public void withdraw(BigDecimal amount) {
        if (amount.compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalArgumentException("Withdraw amount must be positive");
        }
        if (this.<field3>.compareTo(amount) < 0) {
            throw new InsufficientBalanceException("Insufficient balance: " + this.<field3> + " < " + amount);
        }
        this.<field3> = this.<field3>.subtract(amount);
        registerEvent(new MoneyWithdrawn(this.<field1>, amount));
    }

    // --- Domain Events ---
    public List<DomainEvent> getDomainEvents() {
        return Collections.unmodifiableList(domainEvents);
    }

    public void clearEvents() {
        domainEvents.clear();
    }

    private void registerEvent(DomainEvent event) {
        domainEvents.add(event);
    }

    // --- Getters (solo lectura, el comportamiento está en los métodos) ---
    public String get<Field1>() { return <field1>; }
    public String get<Field2>() { return <field2>; }
    public BigDecimal get<Field3>() { return <field3>; }
    public <BusinessObject>Type getType() { return type; }

    public static Builder builder() { return new Builder(); }

    public static class Builder {
        private String <field1>;
        private String <field2>;
        private BigDecimal <field3>;
        private <BusinessObject>Type type;

        public Builder <field1>(String <field1>) { this.<field1> = <field1>; return this; }
        public Builder <field2>(String <field2>) { this.<field2> = <field2>; return this; }
        public Builder <field3>(BigDecimal <field3>) { this.<field3> = <field3>; return this; }
        public Builder type(<BusinessObject>Type type) { this.type = type; return this; }
        public <BusinessObject> build() { return new <BusinessObject>(this); }
    }
}
```

#### 5.1.4. Domain Event (DDD)

Crea un evento de dominio por cada acción significativa del negocio. Los Domain Events son **inmutables** y usan nomenclatura en **pasado** (`MoneyDeposited`, `AccountCreated`, `MoneyWithdrawn`).

Archivo: `domain/event/DomainEvent.java` (interface base)

```java
package $FINAL_PACKAGE.domain.event;

import java.time.Instant;

public interface DomainEvent {
    Instant occurredOn();
}
```

Archivo: `domain/event/<BusinessVerb>Event.java` (evento concreto)

```java
package $FINAL_PACKAGE.domain.event;

import java.math.BigDecimal;
import java.time.Instant;

public record MoneyDeposited(String accountNumber, BigDecimal amount, Instant occurredOn) implements DomainEvent {

    public MoneyDeposited(String accountNumber, BigDecimal amount) {
        this(accountNumber, amount, Instant.now());
    }

    @Override
    public Instant occurredOn() { return occurredOn; }
}
```

#### 5.1.5. Excepción de negocio (DDD — lenguaje ubicuo)

Por cada condición de error del spec, crea una excepción que use el **lenguaje ubicuo** del dominio bancario.

Archivo: `domain/exception/<ErrorName>Exception.java`

```java
package $FINAL_PACKAGE.domain.exception;

public class <ErrorName>Exception extends RuntimeException {
    public <ErrorName>Exception(String message) {
        super(message);
    }
}
```

### Capa 4.2 — Application (`application/`)

#### 4.2.1. Puerto de salida (Outbound Port — DDD Repository)

El Outbound Port es el **Repository** de DDD. Define contratos para recuperar y persistir Aggregates. Usa Value Objects en los parámetros cuando aplique.

Archivo: `application/ports/outbound/<BusinessObject>RepositoryPort.java`

```java
package $FINAL_PACKAGE.application.ports.outbound;

import $FINAL_PACKAGE.domain.model.<BusinessObject>;
import $FINAL_PACKAGE.domain.model.CustomerCu;
import java.util.List;
import java.util.Optional;

public interface <BusinessObject>RepositoryPort {
    List<<BusinessObject>> findByCustomerId(CustomerCu customerCu);
    Optional<<BusinessObject>> findByAccountNumber(String accountNumber);
    <BusinessObject> save(<BusinessObject> account);
}
```

#### 4.2.2. Puerto de entrada (Inbound Port — DDD Use Case)

El Inbound Port es el **Caso de Uso** de DDD. Usa el valor de `bianverb` del YAML front matter (Retrieve, Initiate, Execute, etc.). Recibe Value Objects del dominio cuando sea necesario.

Archivo: `application/ports/inbound/<BianVerb><BusinessObject>sUseCase.java`

```java
package $FINAL_PACKAGE.application.ports.inbound;

import $FINAL_PACKAGE.domain.model.<BusinessObject>;
import $FINAL_PACKAGE.domain.model.Money;
import java.util.List;

public interface <BianVerb><BusinessObject>sUseCase {
    List<<BusinessObject>> findByCustomerId(String customerId);

    // Para comandos (Initiate, Execute) usar Value Objects del dominio
    void execute(String accountNumber, Money amount);
}
```

#### 4.2.3. Servicio de aplicación (Application Service)

Orquesta los casos de uso. **No contiene lógica de negocio** — esa va en el Aggregate Root o Domain Service.

Archivo: `application/service/<BusinessObject>Service.java`

Para **consultas (Retrieve):** el servicio delega en el repositorio y devuelve los Aggregates:

```java
package $FINAL_PACKAGE.application.service;

import $FINAL_PACKAGE.application.ports.inbound.<BianVerb><BusinessObject>sUseCase;
import $FINAL_PACKAGE.application.ports.outbound.<BusinessObject>RepositoryPort;
import $FINAL_PACKAGE.domain.model.<BusinessObject>;
import java.util.List;

public class <BusinessObject>QueryService implements <BianVerb><BusinessObject>sUseCase {

    private final <BusinessObject>RepositoryPort repository;

    public <BusinessObject>QueryService(<BusinessObject>RepositoryPort repository) {
        this.repository = repository;
    }

    @Override
    public List<<BusinessObject>> findByCustomerId(String customerId) {
        return repository.findByCustomerId(customerId);
    }
}
```

Para **comandos (Initiate, Execute):** el servicio recupera el Aggregate, ejecuta el método de negocio y persiste:

```java
package $FINAL_PACKAGE.application.service;

import $FINAL_PACKAGE.application.ports.inbound.<BianVerb><BusinessObject>sUseCase;
import $FINAL_PACKAGE.application.ports.outbound.<BusinessObject>RepositoryPort;
import $FINAL_PACKAGE.domain.model.<BusinessObject>;
import $FINAL_PACKAGE.domain.model.Money;

public class <BusinessObject>CommandService implements <BianVerb><BusinessObject>sUseCase {

    private final <BusinessObject>RepositoryPort repository;

    public <BusinessObject>CommandService(<BusinessObject>RepositoryPort repository) {
        this.repository = repository;
    }

    @Override
    public void execute(String accountNumber, Money amount) {
        var account = repository.findByAccountNumber(accountNumber);
        // El Application Service orquesta, el Aggregate ejecuta la lógica de negocio
        account.withdraw(amount);           // ← método de negocio en el Aggregate
        repository.save(account);           // ← persiste el estado y los eventos
        // Los domain events se publican después (opcional en POC)
        account.getDomainEvents().forEach(event -> { /* eventPublisher.publish(event) */ });
        account.clearEvents();
    }
}
```

### Capa 4.3 — Infrastructure (`infrastructure/`)

#### 4.3.1. Entidad JPA (para BD)

Usa la tabla del spec y el Field Mapping para determinar columnas exactas.

Archivo: `infrastructure/adapters/outbound/database/<BusinessObject>Entity.java`

```java
package $FINAL_PACKAGE.infrastructure.adapters.outbound.database;

import jakarta.persistence.*;
import java.math.BigDecimal;

@Entity
@Table(name = "<table_name>")
public class <BusinessObject>Entity {

    @Id
    private String id;
    private String customerCu;
    @Column(unique = true)
    private String accountNumber;
    private String currency;
    private String cci;
    private BigDecimal balance;
    private String type;

    public <BusinessObject>Entity() {}

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public String getCustomerCu() { return customerCu; }
    public void setCustomerCu(String customerCu) { this.customerCu = customerCu; }
    public String getAccountNumber() { return accountNumber; }
    public void setAccountNumber(String accountNumber) { this.accountNumber = accountNumber; }
    public String getCurrency() { return currency; }
    public void setCurrency(String currency) { this.currency = currency; }
    public String getCci() { return cci; }
    public void setCci(String cci) { this.cci = cci; }
    public BigDecimal getBalance() { return balance; }
    public void setBalance(BigDecimal balance) { this.balance = balance; }
    public String getType() { return type; }
    public void setType(String type) { this.type = type; }
}
```

#### 4.3.2. Repositorio Spring Data JPA

Archivo: `infrastructure/adapters/outbound/database/Jpa<BusinessObject>Repository.java`

```java
package $FINAL_PACKAGE.infrastructure.adapters.outbound.database;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface Jpa<BusinessObject>Repository extends JpaRepository<<BusinessObject>Entity, String> {
    List<<BusinessObject>Entity> findByCustomerCu(String customerCu);
}
```

#### 4.3.3. Mapper de entidad JPA a dominio (Outbound Mapper)

Archivo: `infrastructure/adapters/outbound/mapper/<BusinessObject>EntityMapper.java`

```java
package $FINAL_PACKAGE.infrastructure.adapters.outbound.mapper;

import $FINAL_PACKAGE.domain.model.<BusinessObject>;
import $FINAL_PACKAGE.domain.model.<BusinessObject>Type;
import $FINAL_PACKAGE.infrastructure.adapters.outbound.database.<BusinessObject>Entity;
import org.springframework.stereotype.Component;

@Component
public class <BusinessObject>EntityMapper {

    public <BusinessObject> toDomain(<BusinessObject>Entity entity) {
        if (entity == null) return null;
        return <BusinessObject>.builder()
            .accountNumber(entity.getAccountNumber())
            .currency(entity.getCurrency())
            .cci(entity.getCci())
            .balance(entity.getBalance())
            .type(<BusinessObject>Type.valueOf(entity.getType()))
            .build();
    }

    public <BusinessObject>Entity toEntity(<BusinessObject> domain) {
        if (domain == null) return null;
        <BusinessObject>Entity entity = new <BusinessObject>Entity();
        entity.setAccountNumber(domain.getAccountNumber());
        entity.setCurrency(domain.getCurrency());
        entity.setCci(domain.getCci());
        entity.setBalance(domain.getBalance());
        entity.setType(domain.getType().name());
        return entity;
    }
}
```

#### 4.3.4. Adaptador JPA (implementa Outbound Port)

Archivo: `infrastructure/adapters/outbound/database/<BusinessObject>JpaRepositoryAdapter.java`

```java
package $FINAL_PACKAGE.infrastructure.adapters.outbound.database;

import $FINAL_PACKAGE.application.ports.outbound.<BusinessObject>RepositoryPort;
import $FINAL_PACKAGE.domain.model.<BusinessObject>;
import $FINAL_PACKAGE.infrastructure.adapters.outbound.mapper.<BusinessObject>EntityMapper;
import org.springframework.stereotype.Component;
import java.util.List;

@Component
public class <BusinessObject>JpaRepositoryAdapter implements <BusinessObject>RepositoryPort {

    private final Jpa<BusinessObject>Repository jpaRepository;
    private final <BusinessObject>EntityMapper mapper;

    public <BusinessObject>JpaRepositoryAdapter(Jpa<BusinessObject>Repository jpaRepository,
                                                 <BusinessObject>EntityMapper mapper) {
        this.jpaRepository = jpaRepository;
        this.mapper = mapper;
    }

    @Override
    public List<<BusinessObject>> findByCustomerId(String customerId) {
        return jpaRepository.findByCustomerCu(customerId)
            .stream()
            .map(mapper::toDomain)
            .toList();
    }
}
```

#### 4.3.5. DTO de entrada/salida (Request/Response)

Usa el Field Mapping del spec para determinar campos exactos.

Archivo: `infrastructure/adapters/inbound/dto/<BusinessObject>Response.java`

```java
package $FINAL_PACKAGE.infrastructure.adapters.inbound.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.math.BigDecimal;

public record <BusinessObject>Response(
    @JsonProperty("accountNumber") String accountNumber,
    @JsonProperty("currency") String currency,
    @JsonProperty("cci") String cci,
    @JsonProperty("balance") BigDecimal balance,
    @JsonProperty("type") String type
) {}
```

#### 4.3.6. Mapper de dominio a DTO (Inbound Mapper)

Archivo: `infrastructure/adapters/inbound/mapper/<BusinessObject>DtoMapper.java`

```java
package $FINAL_PACKAGE.infrastructure.adapters.inbound.mapper;

import $FINAL_PACKAGE.domain.model.<BusinessObject>;
import $FINAL_PACKAGE.infrastructure.adapters.inbound.dto.<BusinessObject>Response;
import org.springframework.stereotype.Component;
import java.util.List;

@Component
public class <BusinessObject>DtoMapper {

    public <BusinessObject>Response toResponse(<BusinessObject> domain) {
        return new <BusinessObject>Response(
            domain.getAccountNumber(),
            domain.getCurrency(),
            domain.getCci(),
            domain.getBalance(),
            domain.getType().name()
        );
    }

    public List<<BusinessObject>Response> toResponseList(List<<BusinessObject>> domainList) {
        return domainList.stream()
            .map(this::toResponse)
            .toList();
    }
}
```

#### 4.3.7. Controlador REST (con OpenAPI documentation)

Sigue la nomenclatura BIAN del `architecture.md`. Genera el path siguiendo el patrón BIAN: `/<microservicename>/<behaviorqualifier>/<bianverb>`.

**Mapeo verbo BIAN → HTTP:**
| `<BianVerb>` | `@<HttpMethod>` |
|---|---|
| `Retrieve` | `GetMapping` |
| `Initiate` | `PostMapping` |
| `Execute` | `PostMapping` |

Todas las API REST generadas deben incluir anotaciones `@Tag`, `@Operation` y `@ApiResponse` de **springdoc-openapi** para generar documentación Swagger/OpenAPI automáticamente.

Archivo: `infrastructure/adapters/inbound/rest/<BusinessObject>Controller.java`

```java
package $FINAL_PACKAGE.infrastructure.adapters.inbound.rest;

import $FINAL_PACKAGE.application.ports.inbound.<BianVerb><BusinessObject>sUseCase;
import $FINAL_PACKAGE.infrastructure.adapters.inbound.dto.<BusinessObject>Response;
import $FINAL_PACKAGE.infrastructure.adapters.inbound.mapper.<BusinessObject>DtoMapper;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController
@Tag(name = "<BusinessObject>s", description = "REST API for <BusinessObject> operations")
public class <BusinessObject>Controller {

    private final <BianVerb><BusinessObject>sUseCase useCase;
    private final <BusinessObject>DtoMapper mapper;

    public <BusinessObject>Controller(<BianVerb><BusinessObject>sUseCase useCase,
                                       <BusinessObject>DtoMapper mapper) {
        this.useCase = useCase;
        this.mapper = mapper;
    }

    @<HttpMethod>("/<microservicename>/<behaviorqualifier>/<bianVerbLower>")
    @Operation(summary = "<BianVerb> <BusinessObject>s", description = "<BianVerb>s <BusinessObject>s for a given customer")
    @ApiResponses({
        @ApiResponse(responseCode = "200", description = "Successful <BianVerb> of <BusinessObject> list"),
        @ApiResponse(responseCode = "404", description = "Customer not found"),
        @ApiResponse(responseCode = "400", description = "Invalid request parameters")
    })
    public ResponseEntity<List<<BusinessObject>Response>> get<BusinessObject>s(
            @RequestParam String cu) {
        var accounts = useCase.findByCustomerId(cu);
        return ResponseEntity.ok(mapper.toResponseList(accounts));
    }
}
```

#### 4.3.8. Configuración Spring (DomainConfig)

Archivo: `infrastructure/config/DomainConfig.java`

```java
package $FINAL_PACKAGE.infrastructure.config;

import $FINAL_PACKAGE.application.ports.inbound.<BianVerb><BusinessObject>sUseCase;
import $FINAL_PACKAGE.application.ports.outbound.<BusinessObject>RepositoryPort;
import $FINAL_PACKAGE.application.service.<BusinessObject>QueryService;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class DomainConfig {

    @Bean
    public <BianVerb><BusinessObject>sUseCase <bianVerbFirstLower><BusinessObject>sUseCase(
            <BusinessObject>RepositoryPort repository) {
        return new <BusinessObject>QueryService(repository);
    }
}
```

#### 4.3.9. Global Exception Handler (si no existe ya)

Archivo: `infrastructure/config/RestExceptionHandler.java`

```java
package $FINAL_PACKAGE.infrastructure.config;

import $FINAL_PACKAGE.domain.exception.CustomerNotFoundException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import java.time.Instant;
import java.util.Map;

@RestControllerAdvice
public class RestExceptionHandler {

    @ExceptionHandler(CustomerNotFoundException.class)
    public ResponseEntity<Map<String, Object>> handleCustomerNotFound(CustomerNotFoundException ex) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND)
            .body(Map.of(
                "status", 404,
                "code", "CUSTOMER_NOT_FOUND",
                "message", ex.getMessage(),
                "timestamp", Instant.now().toString()
            ));
    }
}
```

#### 4.3.10. Archivo de ejemplos CURL para Postman

Generar o actualizar el archivo `api-<microservicename>-examples.md` en la raíz del proyecto con ejemplos CURL para el endpoint recién creado.

**Reglas:**
- Si el archivo **NO existe** → créalo completo (header + requisitos + endpoint)
- Si el archivo **YA existe** → solo añade la sección del nuevo endpoint al final (no dupliques header ni requisitos)

```bash
API_FILE="api-${MICRO_NAME}-examples.md"

# Detalles del endpoint actual
HTTP_METHOD=$(sed -n 's/.*\*\*Método HTTP:\*\* \(.*\)/\1/p' "$SPEC_FILE" | head -1)
API_PATH=$(sed -n 's/.*\*\*Path:\*\* \(.*\)/\1/p' "$SPEC_FILE" | head -1)

# Construir sección del endpoint
ENDPOINT_SECTION="

---

## ${BIAN_VERB} ${BUSINESS_OBJECT}

$(echo "$DESCRIPTION" | head -1)

### Request

\`\`\`
${HTTP_METHOD} {{BASE_URL}}${API_PATH}
\`\`\`

### CURL

\`\`\`bash
curl -X ${HTTP_METHOD} \"{{BASE_URL}}${API_PATH}\" \\
  -H \"Accept: application/json\"
\`\`\`

### Ejemplo de Response (200 OK)

\`\`\`json
<response_example>
\`\`\`

### Ejemplo de Response (Error)

\`\`\`json
{
  \"status\": 404,
  \"code\": \"NOT_FOUND\",
  \"message\": \"Resource not found\",
  \"timestamp\": \"2026-05-25T10:00:00Z\"
}
\`\`\`
"

if [ ! -f "$API_FILE" ]; then
    # Crear archivo completo
    cat > "$API_FILE" << EOF
# ${BUSINESS_OBJECT} API — Ejemplos CURL

> Endpoints del microservicio \`${MICRO_NAME}\` (Service Domain: \`${BIAN_SERVICE_DOMAIN}\`)
> Generado automáticamente — Reemplaza \`{{BASE_URL}}\` con la URL del entorno correspondiente.

## Requisitos

- **Base URL:** \`{{BASE_URL}}\$ (ej: \`http://localhost:8080\`)
- **Headers requeridos:**
  - \`Content-Type: application/json\`
  - \`Accept: application/json\`

EOF
    echo "Creado $API_FILE"
fi

# Añadir sección del endpoint (siempre al final)
echo "$ENDPOINT_SECTION" >> "$API_FILE"
echo "→ Endpoint añadido a $API_FILE"
```

Donde:
- `<response_example>` → un JSON de ejemplo basado en el Field Mapping del spec
- `$DESCRIPTION` → el texto descriptivo del spec
- `$HTTP_METHOD` → GET, POST, etc.
- `$API_PATH` → path BIAN del spec (ej: `/account-management/account/retrieve`)

## 5. Verificar compilación

Después de generar todos los archivos:

```bash
# Detectar gestor de builds
if [ -f "mvnw" ]; then
  ./mvnw compile -q
elif [ -f "gradlew" ]; then
  ./gradlew compileJava
elif [ -f "pom.xml" ]; then
  mvn compile -q
elif [ -f "build.gradle" ]; then
  gradle compileJava
else
  echo "WARN: No se detectó gestor de builds. Compila manualmente."
fi
```

Si falla la compilación, corrige errores de tipos, imports, nombres, o sintaxis antes de continuar.

## 6. Post-implementación

1. **OBLIGATORIO: Generar tests** → Ejecuta `test-generator` para crear tests unitarios (JUnit 5 + Mockito) y de integración (@WebMvcTest, @DataJpaTest + Testcontainers) para **cada archivo .java** generado. No continúes sin tests.
2. Ejecuta `domain-purity-checker` para validar que no haya fugas de framework en domain/application.
3. Crear migración Flyway: `src/main/resources/db/migration/V[N]__create_[tabla].sql` con la tabla definida en el spec. Verificar que flyway esté en pom.xml; si no, agregarlo.
4. **Generar documentación OpenAPI:** Verifica que la dependencia `springdoc-openapi-starter-webmvc-ui` esté en el `pom.xml`. Si no está, agregarla directamente al pom.xml con la versión compatible con el Spring Boot parent del proyecto.
5. **Generar/actualizar api-examples.md:** Ejecuta la sección 4.3.10 para crear o añadir el endpoint al archivo `api-<microservicename>-examples.md`. Si el archivo ya existe de una implementación anterior, solo añade la nueva sección al final.

## 7. Integración con otro microservicio vía HTTP

Si el caso de uso requiere que este microservicio consuma APIs de **otro microservicio** (ej: AccountManagement llama a CustomerRegistration para validar el CU), el adaptador outbound HTTP debe generarse con `spring-webclient-configurator`.

Flujo:
1. `spring-use-case-implementer` genera el puerto outbound (`<BusinessObject>RepositoryPort`) y el servicio de aplicación.
2. **En lugar de** implementar el adaptador con JPA, ejecuta `spring-webclient-configurator` para crear el adaptador outbound con `WebClient` + `@CircuitBreaker` + fallback.
3. `spring-webclient-configurator` crea `infrastructure/adapters/outbound/external/<ExternalService>Client.java` que implementa el Outbound Port.
4. `spring-webclient-configurator` agrega las dependencias `spring-boot-starter-webflux` y `resilience4j-spring-boot3` al `pom.xml`.
5. `spring-webclient-configurator` configura las properties de CircuitBreaker en `application.yml`.

**Cuándo usar JPA vs WebClient:**
| Si necesita... | Usar |
|---|---|
| Persistir datos localmente | Adaptador JPA + migración Flyway (generados por este skill) |
| Consultar datos de otro microservicio | `spring-webclient-configurator` para el adaptador outbound HTTP |
| Ambos (datos locales + remotos) | Adaptador JPA para lo local + `spring-webclient-configurator` para lo remoto |

## 8. Post-implementación (verificación final)

Después de completar los pasos 1-7, verifica que ningún archivo .java nuevo en `src/main/java/` carezca de su correspondiente test en `src/test/java/`:

```bash
echo "Verificando que todo .java en main tenga su test..."
find src/main/java -name "*.java" | while read src; do
  test_file="src/test/java${src#src/main/java}"
  test_file="${test_file%.java}Test.java"
  if [ ! -f "$test_file" ]; then
    echo "MISSING TEST: $src"
  fi
done
echo "Verificación completada."
```

Si hay archivos sin test, ejecuta `test-generator` para generarlos antes de continuar.
