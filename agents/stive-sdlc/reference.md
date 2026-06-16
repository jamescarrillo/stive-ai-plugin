---
name: stive-sdlc-reference
description: Material de soporte de stive-sdlc (no es un agente seleccionable).
user-invocable: false
---

# Stive SDLC — Catálogo de herramientas, skills y sub-agentes

> Referenciado por `agents/stive-sdlc.agent.md`. Directorio de los tools MCP y de los skills/sub-agentes que el orquestador invoca por nombre en cada etapa.

## Herramientas MCP

### Atlassian MCP (`mcp.atlassian.com` — OAuth2 automático)

| Tool | Cuándo |
|------|--------|
| `getJiraIssueDetails` | Etapa 1 — extraer datos de la HU |
| `searchJiraIssuesUsingJQL` | Buscar HUs por JQL |
| `searchJiraIssuesUsingNaturalLanguage` | Buscar HUs en lenguaje natural |
| `transitionJiraIssue` | Etapa 1 aprobada → `IN_PROGRESS` \| Etapa 4 → `IN_REVIEW` |
| `getVisibleJiraProjects` | Ver proyectos disponibles |

### GitHub MCP (`npx @modelcontextprotocol/server-github` — PAT via VS Code)

| Tool | Cuándo |
|------|--------|
| `create_pull_request` | Etapa 4 — crear PR |
| `create_branch` | Etapa 1 — crear rama feature |
| `push_files` | Etapa 4 — push de cambios |
| `get_file_contents` | Consultar archivos del repo |
| `list_commits` | Verificar historial antes del PR |

---

## Skills y sub-agentes disponibles

> Los **skills** y **sub-agentes** se invocan **por nombre** (el plugin los auto-descubre vía `plugin.json`). Las **guías companion** se leen por ruta relativa a la raíz del plugin.

| Recurso | Tipo | Etapa |
|---------|------|-------|
| `spec-generator` | skill | 1 |
| `plan-generator` | skill | 2 |
| `spring-engineer` | sub-agente | 3 (Spring Boot) |
| `quarkus-engineer` | sub-agente | 3 (Quarkus) |
| `spring-to-quarkus` | sub-agente | 3 (migración) |
| `agents/spring-to-quarkus/restructure-guide.md` | guía companion | 3 (Opción B) |
| `domain-purity-checker` | skill | 3 (validación) |
| `coverage-enforcer` | skill | 3 (validación) |
| `test-generator` | skill | 3 (gap de tests) |
| `pr-creator` | skill | 4 |
| `code-reviewer` | skill | Pre-modificación |
| `mock-strategist` | skill | 3 (tests) |
| `local-deployment-verifier` | skill | Post-3 |
| `spring-use-case-implementer` | skill | 3 (TASK-2.x) |
| `spring-webclient-configurator` | skill | 3 (TASK-4.5) |
| `quarkus-migrator-from-spring` | skill | 3 (migración) |

