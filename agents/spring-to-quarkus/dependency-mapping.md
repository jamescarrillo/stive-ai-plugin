# Dependency Mapping

## Spring Boot → Quarkus

- `spring-boot-starter-web` → `quarkus-resteasy-reactive`
- `spring-boot-starter-data-jpa` → `quarkus-hibernate-orm-panache`
- `spring-boot-starter-validation` → `quarkus-hibernate-validator`
- `spring-boot-starter-actuator` → `quarkus-smallrye-health`, `quarkus-smallrye-metrics`
- `spring-webflux` / `WebClient` → `quarkus-rest-client-reactive`
- `resilience4j` → `smallrye-fault-tolerance`
- `springdoc-openapi` → `smallrye-openapi`

## Build y runtime

- `maven spring-boot:run` → `mvn compile quarkus:dev`
- `application.properties` en Spring → `application.properties` en Quarkus con claves Quarkus
