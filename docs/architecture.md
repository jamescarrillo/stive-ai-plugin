# Context: Hexagonal Architecture (Ports and Adapters) — BIAN-aligned

## 1. Core Philosophy
Este proyecto se rige por la **Arquitectura Hexagonal**. El objetivo principal es mantener la Lógica de Negocio (Dominio) completamente aislada de los detalles técnicos (Bases de datos, Frameworks web, colas de mensajería, APIs externas). 

Todas las dependencias apuntan hacia el interior (hacia el Dominio). El Dominio no sabe nada sobre cómo se persisten los datos o cómo se exponen los servicios al exterior.

## 2. BIAN Reference Architecture
Cada microservicio representa un **Service Domain** de BIAN. La convención de nombres es:

| Concepto BIAN | Implementación |
|---|---|
| Service Domain | `com.jotace.<serviceDomain>` (ej. `com.jotace.accountmanagement`) |
| Business Object | Aggregate Root en `domain/model/` (ej. `Account`) |
| Behavior Qualifier | Sub-entidad o Value Object asociado |
| Service Operation | Inbound Port en `application/ports/inbound/` (ej. `RetrieveAccountUseCase`) |

## 3. DDD Tactical Patterns Mapping

Este proyecto aplica **Domain-Driven Design (DDD)** táctico sobre la arquitectura hexagonal. Cada patrón DDD tiene una ubicación y responsabilidad específica:

| Patrón DDD | ¿Qué es? | Ubicación | Ejemplo |
|---|---|---|---|
| **Value Object** | Objeto inmutable, se define por sus atributos, sin identidad propia | `domain/model/*.java` | `CustomerCu`, `Money`, `AccountNumber` — como Java `record` |
| **Entity** | Objeto con identidad única y ciclo de vida (mutabilidad controlada) | `domain/model/*.java` | `Account` — identificado por `accountNumber` |
| **Aggregate Root** | Entidad raíz que garantiza la consistencia del Aggregate | `domain/model/*.java` | `Account` — contiene las reglas de negocio (`deposit()`, `withdraw()`) |
| **Domain Service** | Lógica de negocio que no pertenece a una sola Entity/Value Object | `domain/service/*.java` | `AccountTransferService` — transfiere entre cuentas |
| **Repository** | Contrato para recuperar/persistir Aggregates (Outbound Port) | `application/ports/outbound/*.java` | `AccountRepositoryPort` |
| **Domain Event** | Algo que ocurrió en el dominio y es relevante para otros Bounded Contexts | `domain/event/*.java` | `MoneyDeposited`, `AccountCreated` |
| **Factory** | Encapsula la creación compleja de Aggregates/Value Objects | `domain/model/*Factory.java` o en el propio Aggregate | Método estático `Account.open(...)` o Builder |

**Reglas DDD:**
- Los **Value Objects** son inmutables (campos `final`, sin setters). Preferir Java `record`.
- Las **Entities** tienen métodos de negocio que operan sobre su estado y lanzan excepciones de dominio. No son anémicas (no solo getters/setters).
- Los **Aggregate Roots** son la única puerta de entrada para modificar su Aggregate. Todo cambio pasa por métodos del Aggregate.
- Los **Domain Events** se registran dentro del Aggregate y se publican después de ser persistidos (patrón outbox o evento de aplicación).

## 4. Standard Directory Structure (DDD-aligned)
Todos los microservicios deben seguir estrictamente esta jerarquía de paquetes base. Ejemplo para el Service Domain `AccountManagement`:

```text
com.jotace.accountmanagement/
├── domain/                      # [NÚCLEO] DDD Tactical Patterns
│   ├── model/                  # Aggregate Roots, Entities, Value Objects
│   ├── event/                  # Domain Events (inmutables, en pasado)
│   ├── exception/              # Excepciones de negocio (lenguaje ubicuo)
│   └── service/                # Domain Services (lógica multi-aggregate)
│
├── application/                 # [PUERTOS] Casos de uso y orquestación
│   ├── ports/
│   │   ├── inbound/            # Inbound Ports (Casos de Uso BIAN)
│   │   └── outbound/           # Outbound Ports (Repositories)
│   └── service/                # Application Services (orquestan, no tienen lógica de negocio)
│
└── infrastructure/              # [ADAPTADORES] Frameworks y tecnología
    ├── adapters/
    │   ├── inbound/            # Entrada (REST Controllers)
    │   │   ├── dto/            # DTOs de entrada/salida (independientes del dominio)
    │   │   ├── mapper/         # Mapeadores DTO ↔ Domain
    │   │   └── rest/           # Controladores Spring @RestController
    │   └── outbound/           # Salida (JPA, WebClient, etc.)
    │       ├── database/       # Spring Data JPA, Entidades @Entity
    │       ├── external/       # WebClient a otros microservicios
    │       └── mapper/         # Mapeadores JPA Entity ↔ Domain
    └── config/                  # Configuración Spring (Beans, WebClientConfig)
```

## 5. BIAN REST API Naming Convention

### Comportamientos estándar (Standard Actions)
BIAN define 5 acciones estándar. Mapeo a HTTP:

| Acción BIAN | HTTP | Path |
|---|---|---|
| Initiate | `POST` | `/{service-domain}/{behavior-qualifier}/initiate` |
| Execute | `POST` | `/{service-domain}/{behavior-qualifier}/execute` |
| Request | `POST` | `/{service-domain}/{behavior-qualifier}/request` |
| Update | `PATCH` | `/{service-domain}/{behavior-qualifier}/update` |
| Retrieve | `GET` | `/{service-domain}/{behavior-qualifier}/retrieve` |

### Consultas simplificadas (no BIAN-strict)
Para endpoints de consulta simple sin behavior qualifier:

| Propósito | HTTP | Path |
|---|---|---|
| Listar recursos | `GET` | `/{service-domain}/{behavior-qualifier}/retrieve` |
| Obtener por ID | `GET` | `/{service-domain}/{behavior-qualifier}/retrieve` |

## 6. Flujo de Datos Hexagonal + DDD

```
[Cliente HTTP]
      ↓
[Controller] REST → @Valid DTO
      ↓
[Inbound Mapper] DTO → Domain Model
      ↓
[Inbound Port] Interface (RetrieveAccountUseCase)
      ↓
[Application Service] Implementación del caso de uso
      ↓
[Outbound Port] Interface (AccountRepositoryPort)
      ↓
[Outbound Adapter] JPA / REST Client / etc.
      ↓
[Outbound Mapper] Entity ↔ Domain Model
      ↓
[Base de datos / API externa]
```