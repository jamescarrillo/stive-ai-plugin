# Stive AI — Agent Plugin para VS Code

Plugin de **agentes de IA para el SDLC de microservicios Java** (Spring Boot 3.x / Quarkus 3.x LTS), con arquitectura hexagonal, DDD táctico y APIs BIAN. Se instala como **Agent Plugin de VS Code** (preview) apuntando al código fuente de este repositorio.

> El manifiesto `plugin.json` declara las carpetas `agents/` y `skills/`. VS Code descubre como **agente seleccionable en el picker de Copilot** a cada `*.agent.md` ubicado directamente en `agents/`. Por eso este README vive en la raíz: cualquier `.md` dentro de `agents/` aparecería en el picker como un agente más.

## Instalación (install from source)

Pasa este repositorio al instalador de Agent Plugins de VS Code. El plugin queda registrado bajo `~/.copilot/installed-plugins/` y sus agentes aparecen en el picker del chat de Copilot.

## Agentes del picker

| Agente | Archivo | Propósito |
|---|---|---|
| `stive-sdlc` | `agents/stive-sdlc.agent.md` | Orquesta el flujo `JIRA → Spec → Plan → Código → PR` con 4 checkpoints humanos |
| `stive-auditor` | `agents/stive-auditor.agent.md` | Identifica deuda técnica y oportunidades de mejora; entrega un backlog priorizado (solo reporta) |

## Sub-agentes de implementación (Etapa 3, invocados por stive-sdlc)

| Agente | Framework | Estructuras soportadas |
|---|---|---|
| `spring-engineer` | Spring Boot 3.x | new, hexagonal, traditional, mixed |
| `quarkus-engineer` | Quarkus 3.x LTS | new, hexagonal, traditional, mixed |
| `spring-to-quarkus` | Spring → Quarkus | hexagonal→hexagonal, traditional→traditional (A), traditional→hexagonal (B) |

> Los sub-agentes son `*.agent.md` con **`user-invocable: false`** en el frontmatter, por lo que **no** aparecen en el picker pero `stive-sdlc` sí puede invocarlos por nombre (los declara en su frontmatter `agents:`). El picker expone únicamente `stive-sdlc` y `stive-auditor`.

## Selección automática (plan-generator)

```
framework=spring-boot → spring-engineer
framework=quarkus     → quarkus-engineer
HU de migración       → spring-to-quarkus
```

## Estructura del repositorio

```
plugin.json                      ← Manifiesto del Agent Plugin (declara agents/, skills/ y .mcp.json)
.mcp.json                        ← Config MCP: atlassian (JIRA remoto) + github (npx)
agents/
  stive-sdlc.agent.md            ← Orquestador SDLC (picker)
  stive-sdlc/                    ← Soporte del orquestador
    preflight.md · detection.md · reference.md
  stive-auditor.agent.md         ← Auditor / backlog (picker)
  spring-engineer.agent.md       ← Sub-agente Spring Boot (user-invocable: false)
  spring-engineer/               ← Soporte del sub-agente
    templates-hexagonal.md
    templates-traditional.md
  quarkus-engineer.agent.md      ← Sub-agente Quarkus (user-invocable: false)
  quarkus-engineer/              ← Soporte del sub-agente
    templates-hexagonal.md
    templates-traditional.md
  spring-to-quarkus.agent.md     ← Sub-agente de migración (user-invocable: false)
  spring-to-quarkus/             ← Soporte del sub-agente (guías de migración)
    restructure-guide.md
    dependency-mapping.md · migration-rules.md · checklist.md
skills/                          ← Skills invocables por nombre (spec-generator, plan-generator, pr-creator, ...)
docs/                            ← Contexto de arquitectura / estándares que consumen los agentes
templates/                       ← Plantillas (HU, etc.)
scripts/                         ← jira_mcp_server.py (MCP JIRA local, opcional para pruebas en CLI)
```

### Convención de los sub-agentes (escalable)

Cada sub-agente se compone de:

- **Entry plano** `agents/<nombre>.agent.md` — el "cerebro": reglas, decisiones y cuándo actúa. Va plano en `agents/` porque es lo que el plugin registra (y queda oculto del picker con `user-invocable: false`).
- **Carpeta de soporte** `agents/<nombre>/` — templates y guías que el entry referencia por ruta relativa al plugin. Para escalar (un template nuevo, una regla nueva) agregas un archivo aquí **sin tocar el cerebro del agente**.

## Flujo de integración

```
stive-sdlc.agent.md (orquestador del flujo)
  ↓ PASO 2 detecta framework + projectStructure
  ↓ spec-generator produce el spec técnico
  ↓ plan-generator elige el sub-agente + crea tasks.json
  ↓ [spring-engineer | quarkus-engineer | spring-to-quarkus] implementa
  ↓ pr-creator crea el PR y actualiza JIRA
```

## Artefactos generados (en el repo destino)

El SDLC escribe sus artefactos en el `.github/` del microservicio sobre el que se trabaja:

```
.github/specs/<HU>.md                 ← spec técnico
.github/specs/.metadata/<HU>.json     ← estado del flujo
.github/plans/<HU>/plan.md            ← plan de implementación
.github/plans/<HU>/tasks.json         ← tareas atómicas con estado
```

## Referencia rápida de capacidades

| Agente | New | Feature | Migración | Hexagonal | Tradicional | Mixed |
|---|---|---|---|---|---|---|
| `spring-engineer` | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ |
| `quarkus-engineer` | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ |
| `spring-to-quarkus` | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
