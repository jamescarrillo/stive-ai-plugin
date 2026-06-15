# Agentes de Stive

Esta carpeta contiene los **dos agentes seleccionables en el picker de Copilot** y los **sub-agentes de implementación** que ellos invocan internamente.

## Agentes del picker

| Agente | Archivo | Propósito |
|---|---|---|
| `stive-sdlc` | `stive-sdlc.agent.md` | Orquesta el flujo `JIRA → Spec → Plan → Código → PR` con 4 checkpoints humanos |
| `stive-auditor` | `stive-auditor.agent.md` | Identifica deuda técnica y mejoras; entrega un reporte priorizado (solo reporta) |

## Sub-agentes de implementación (Etapa 3, invocados por stive-sdlc)

| Agente | Framework | Estructuras soportadas |
|---|---|---|
| `spring-engineer` | Spring Boot 3.x | new, hexagonal, traditional, mixed |
| `quarkus-engineer` | Quarkus 3.x LTS | new, hexagonal, traditional, mixed |
| `spring-to-quarkus` | Spring → Quarkus | hexagonal→hexagonal, traditional→traditional (A), traditional→hexagonal (B) |

> Los sub-agentes usan `AGENT.md` (no `*.agent.md`), por lo que **no** aparecen en el picker: `stive-sdlc` los selecciona según el framework detectado.

## Selección automática (plan-generator)

```
framework=spring-boot → spring-engineer
framework=quarkus     → quarkus-engineer
HU de migración       → spring-to-quarkus
```

## Archivos por agente

```
spring-engineer/
  AGENT.md                  ← Templates Spring Boot (domain, app, infra, tests)

quarkus-engineer/
  AGENT.md                  ← Templates Quarkus (JAX-RS, CDI, Panache, REST Assured)

spring-to-quarkus/
  AGENT.md                  ← Orquestador de migración (detección + pregunta al usuario)
  restructure-guide.md      ← Opción B: traditional Spring → hexagonal Quarkus
  dependency-mapping.md     ← Mapeo de dependencias Spring → Quarkus
  migration-rules.md        ← Reglas de migración por capa
  checklist.md              ← Checklist post-migración

```

## Flujo de integración

```
stive-sdlc.agent.md (orquestador del flujo)
  ↓ PASO 2 detecta framework + projectStructure
  ↓ spec-generator produce spec técnico
  ↓ plan-generator elige agente + crea tasks.json
  ↓ [spring-engineer | quarkus-engineer | spring-to-quarkus] implementa
  ↓ pr-creator crea PR y actualiza JIRA
```

> `copilot-instructions.md` ya no es el orquestador: ahora solo aporta contexto del repositorio (stack, arquitectura, MCP). El flujo vive completo dentro de `stive-sdlc.agent.md`.

## Referencia rápida de capacidades

| Agente | New | Feature | Migración | Hexagonal | Tradicional | Mixed |
|---|---|---|---|---|---|---|
| `spring-engineer` | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ |
| `quarkus-engineer` | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ |
| `spring-to-quarkus` | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
