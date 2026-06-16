# Coding Standards

Este documento define los estándares de código para los agentes en `.github`.

## Java

- Usa Java 17+ (Spring Boot 4.x requiere **Java 21+**; usa la versión que detecte `frameworkMajor`).
- En el dominio, evita anotaciones de framework y dependencias de librerías externas.
- Prefiere inmutabilidad y builders en modelos de dominio.
- Usa nombres de clases y paquetes descriptivos y alineados con BIAN.
- No uses `@Data` de Lombok en el dominio.
- Inyección de dependencias por constructor, nunca por campo.

## Fechas y Tiempos

- **Usa `LocalDateTime` para todas las fechas en el dominio y DTOs.** Nunca `Instant` ni `ZonedDateTime` en capas de dominio o application.
- `Instant` solo se permite en entidades JPA (`@Column` con `TIMESTAMPTZ`) cuando el ORM lo requiere explícitamente.
- Al mapear entre dominio (`LocalDateTime`) y persistencia (`Instant` en JPA), el mapper (MapStruct) debe hacer la conversión explícitamente con `Instant.now()` / `LocalDateTime.now()`.
- Los records de eventos de dominio (ej: `AccountInitiatedEvent`) usan `LocalDateTime createdAt`.
- Para Quarkus: Panache maneja `LocalDateTime` directamente con `@Column` estándar.

## Tests

- Escribe JUnit 5 para lógica de dominio y casos de uso.
- Usa Mockito para mocks de puertos y dependencias externas.
- Testcontainers para pruebas de integración con base de datos.
- Usa `@WebMvcTest` y `@DataJpaTest` en Spring Boot cuando corresponda.
- Usa `@QuarkusTest` y `@InjectMock` en Quarkus.
