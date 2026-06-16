# Context: Dependency Rules per Layer

Si el proyecto es un proyecto multi-módulo de Maven/Gradle o un proyecto de un solo módulo dividido por paquetes, debes aplicar estas restricciones de dependencias de manera estricta:

## 1. Módulo / Paquete: `domain`
* **Permitido:** * Java Base (`java.lang`, `java.util`, `java.math`, etc.).
  * **DDD Value Objects:** Preferir Java `record` para inmutabilidad. Los Value Objects deben implementar `equals()` y `hashCode()` basados en todos sus atributos.
  * **DDD Domain Events:** Clases inmutables con nomenclatura en pasado (`AccountCreated`, `MoneyDeposited`).
  * **DDD Entities/Aggregates:** Métodos de negocio con nombre del lenguaje ubicuo (`withdraw()`, `deposit()`, `open()`, `close()`).
  * Lombok (opcional, solo para `@Getter`, `@Builder`, `@ToString`. No uses `@Data`).
* **PROHIBIDO:** * `spring-boot-starter-*` o cualquier clase de `org.springframework`.
  * `jakarta.persistence.*`, `hibernate.*` (nada de JPA).
  * `com.fasterxml.jackson.*` (nada de anotaciones de serialización como `@JsonProperty`).
  * `jakarta.validation.*` (nada de `@NotNull`, `@Size` para validación de DTOs).
  * **Modelos anémicos:** Las Entities/Agregates NO deben ser solo contenedores de datos (getters/setters). Deben tener comportamiento de negocio.

## 2. Módulo / Paquete: `application`
* **Permitido:** * Dependencia directa del paquete/módulo `domain`.
  * Librerías de utilidades estándar de Java.
  * Slf4j / Logback (para logs dentro de los servicios si es necesario).
* **PROHIBIDO:** * Cualquier tecnología de persistencia (JPA, JDBC, Mongo).
  * Frameworks web o de red (Spring Web, HTTP clients, etc.).
  * Anotaciones de Spring como `@Service`, `@Component`, `@Autowired`.

## 3. Módulo / Paquete: `infrastructure`
* **Permitido:** * Dependencia directa de `application` y `domain`.
  * Spring Boot starters (`spring-boot-starter-web`, `spring-boot-starter-data-jpa`, `spring-boot-starter-security`, etc.).
  * Spring Boot starters reactivos (`spring-boot-starter-webflux` para WebClient en comunicación inter-servicios).
  * Resilience4j (`resilience4j-spring-boot3`, `spring-boot-starter-aop`) para CircuitBreaker en llamadas HTTP.
  * Drivers de bases de datos y ORMs (PostgreSQL, MySQL, Hibernate).
  * MapStruct u otras librerías de mapeo de objetos.
  * `jakarta.validation-api` e `hibernate-validator` (para validación en controladores).
  * Clientes HTTP externos: en **Spring Boot 3.x** usa `WebClient`; en **4.x** prefiere `RestClient` (sync) o interfaces `@HttpExchange`. Prohibido `RestTemplate` y Feign para código nuevo.

## 4. Estilo de Pruebas (Testing Rules)

### 4.1. Pruebas de Dominio y Aplicación (`domain` y `application`)
* Deben ser pruebas unitarias puras.
* **Tecnologías:** **JUnit 5** y **Mockito**.
* **PROHIBIDO:** Usar `@SpringBootTest`, `@MockBean`, o levantar cualquier contexto de Spring. Los puertos de salida deben ser simulados con `@Mock` de Mockito estándar.

### 4.2. Pruebas de Infraestructura (`infrastructure`)
* Pruebas de integración o de rebanada (slice tests).
* **Controladores:** Uso de `@WebMvcTest` junto con `@MockBean` para simular los Inbound Ports.
* **Persistencia:** Uso de `@DataJpaTest` junto con **Testcontainers** para levantar una base de datos real en Docker (evitar H2 en memoria si el entorno real usa bases de datos relacionales complejas).