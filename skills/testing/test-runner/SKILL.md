---
name: test-runner
description: Ejecuta las pruebas unitarias, de arquitectura y de integración del proyecto, detectando automáticamente el gestor de builds.
---

# Instrucciones para el Agente

Ejecuta este skill después de implementar cambios en cualquier capa. Valida que todo compile y las pruebas pasen.

## Detectar gestor de builds

```bash
ls build.gradle* settings.gradle* pom.xml mvnw gradlew 2>/dev/null
```

| Si existe | Comando |
|---|---|
| `mvnw` | `./mvnw clean test` |
| `pom.xml` (sin mvnw) | `mvn clean test` |
| `gradlew` | `./gradlew clean test` |
| `build.gradle` (sin gradlew) | `gradle clean test` |

## Tipos de pruebas según la capa

| Capa | Framework | Prohibido |
|---|---|---|
| `domain/` | JUnit 5 + Mockito | `@SpringBootTest`, `@MockBean` |
| `application/` | JUnit 5 + Mockito | `@SpringBootTest`, `@MockBean` |
| `infrastructure/` (REST) | `@WebMvcTest` + `@MockBean` | Levantar contexto completo |
| `infrastructure/` (BD) | `@DataJpaTest` + Testcontainers | H2 en memoria para prod |
| `infrastructure/` (API client) | WireMock | Llamadas reales |

## Pruebas de arquitectura (ArchUnit)
Si el proyecto incluye ArchUnit, ejecútalas. No ignores fallos estructurales.

```bash
rg -l "ArchUnit|archunit|@ArchTest" --type java 2>/dev/null
```

## Pasos
1. Ejecuta el comando según el gestor detectado.
2. Si falla compilación → corrige y repite.
3. Si fallan tests → lee el error, corrige y repite.
4. Si Testcontainers falla → verifica que Docker esté corriendo.
5. Si ArchUnit falla → la arquitectura está violada, corrige antes de continuar.
6. Todo en verde → ejecuta `coverage-enforcer` para verificar cobertura.
