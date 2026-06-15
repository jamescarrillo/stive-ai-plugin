# Migración Spring Boot → Quarkus

## Reglas clave

- Mantén el dominio puro. No conviertas modelos de dominio en clases Panache.
- Reemplaza `@RestController` por JAX-RS `@Path` y recursos reactivos cuando sea posible.
- Sustituye `Spring Data JPA` por `Hibernate ORM + Panache` o `PanacheRepository` según el caso.
- Reemplaza `WebClient` y Resilience4j por SmallRye Reactive Client y SmallRye Fault Tolerance.
- Configura propiedades en `application.properties` o `application.yaml` con los nombres de Quarkus.
- Conserva los contratos REST y los paths BIAN.
- Adapta `@Transactional` a Quarkus CDI cuando sea necesario.
