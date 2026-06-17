# Stive AI — Agent Plugin para VS Code

Plugin de **agentes de IA para el SDLC de microservicios Java** (Spring Boot 3.x/4.x / Quarkus 3.x LTS), con arquitectura hexagonal, DDD táctico y APIs BIAN. Se instala como **Agent Plugin de VS Code** (preview) apuntando al código fuente de este repositorio.

> El manifiesto `plugin.json` declara, en arrays, la **carpeta de cada agente** y las **raíces de skills**. VS Code registra como agente **cada `.md`** dentro de una carpeta de agente declarada; por eso los entries que deben quedar fuera del picker llevan `user-invocable: false`. Seleccionables en el picker de Copilot: solo `stive-sdlc` y `stive-auditor`. Ver **Reglas de descubrimiento** más abajo.

## Instalación (install from source)

Pasa este repositorio al instalador de Agent Plugins de VS Code. El plugin queda registrado bajo `~/.copilot/installed-plugins/` y sus agentes aparecen en el picker del chat de Copilot.

## Configuración (`/init`) y servidores MCP

La primera vez en un repo, pídele a `stive-sdlc`: **`/init`**. Presenta **2 selectores** que confirmas — tipo de JIRA y modo de GitHub — prueba la conexión, crea `.github/stive.config.json` y las carpetas de artefactos. **Los requisitos a cumplir dependen de esta config.**

```json
{ "jira": { "mode": "remote" }, "github": { "createPr": false } }
```

| Opción | Valores | Significado |
|---|---|---|
| `jira.mode` | `remote` (default) | JIRA vía MCP remoto de Atlassian (OAuth en el navegador). Servidor `atlassian`. |
| | `local` | JIRA vía script local `scripts/jira_mcp_server.py` (API token). Servidor `jira-local`. |
| `github.createPr` | `false` (default) | Etapa 4 hace **commit en la rama local**; el PR lo creas tú. |
| | `true` | Stive crea el PR vía GitHub MCP (requiere un PAT en `GITHUB_TOKEN`). |

### Servidores MCP declarados (`.mcp.json`)

| Servidor | Tipo | Se usa cuando | Cómo arranca |
|---|---|---|---|
| `atlassian` | Remoto (HTTP, Atlassian) | `jira.mode` = `remote` | VS Code abre **OAuth en el navegador** la 1ª vez. No requiere token. |
| `jira-local` | Local (Python) | `jira.mode` = `local` | VS Code ejecuta `scripts/jira_mcp_server.py` con **API token** (env vars). |
| `github` | Local (npx) | `github.createPr` = `true` | VS Code lanza `npx` bajo demanda; requiere **`GITHUB_TOKEN`** y Node.js. |

> No se arrancan a mano — VS Code gestiona el ciclo de vida.

### Requisitos según tu config

| Si tu config es… | Necesitas |
|---|---|
| `jira.mode = remote` | Conexión a `mcp.atlassian.com` + autorizar el OAuth. **Nada de tokens.** |
| `jira.mode = local` | Python 3.8+ con `requests` (`pip install -r scripts/requirements.txt`) y las env vars `JIRA_BASE_URL`, `JIRA_USER_EMAIL`, `JIRA_API_TOKEN`. |
| `github.createPr = false` | Nada extra (commit local, PR manual). |
| `github.createPr = true` | Node.js + `GITHUB_TOKEN` (PAT con scope `repo`). |

Siempre: estar dentro de un repo git. Verifica con **`verifica requisitos`** (el pre-flight valida solo lo que tu config necesita).

### Generar un API token de Atlassian (para `jira.mode = local`)

El MCP **remoto** no requiere token (usa OAuth). El **script local** sí — útil en entornos donde el OAuth/MCP remoto está bloqueado pero la cuenta sí permite API tokens:

1. Ve a **https://id.atlassian.com/manage-profile/security/api-tokens**.
2. **Create API token** → ponle un nombre (ej. `stive`) → copia el token.
3. Exporta las env vars (en tu shell / perfil):
   ```bash
   export JIRA_BASE_URL="https://tu-dominio.atlassian.net"
   export JIRA_USER_EMAIL="tu-correo@empresa.com"
   export JIRA_API_TOKEN="<token-pegado>"
   ```
4. `pip install -r scripts/requirements.txt` y corre `verifica requisitos`.

### Nota sobre GitHub

`github.createPr` está en `false` (commit local) por defecto porque muchas cuentas corporativas **no permiten generar PAT**. Si la tuya sí: crea un PAT (scope `repo`), ponlo en la env var `GITHUB_TOKEN` y elige `PR` en `/init` (`github.createPr = true`). El paquete `@modelcontextprotocol/server-github` está deprecado pero funciona vía npx; alternativa oficial: MCP remoto `https://api.githubcopilot.com/mcp` o el binario `github-mcp-server`.

## Agentes del picker

| Agente | Archivo | Propósito |
|---|---|---|
| `stive-sdlc` | `agents/stive-sdlc/stive-sdlc.agent.md` | Orquesta el flujo `JIRA → Spec → Plan → Código → PR` con 4 checkpoints humanos |
| `stive-auditor` | `agents/stive-auditor/stive-auditor.agent.md` | Identifica deuda técnica y oportunidades de mejora; entrega un backlog priorizado (solo reporta) |

## Sub-agentes de implementación (Etapa 3, invocados por stive-sdlc)

| Agente | Framework | Estructuras soportadas |
|---|---|---|
| `spring-engineer` | Spring Boot 3.x / 4.x | new, hexagonal, traditional, mixed |
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
plugin.json                      ← Manifiesto: declara las carpetas de agentes, las raíces de skills y .mcp.json
.mcp.json                        ← Config MCP: atlassian (remoto) · jira-local (script) · github (npx)
agents/
  stive-sdlc/                    ← Orquestador SDLC (PICKER)
    stive-sdlc.agent.md            entry visible
    init.md · preflight.md · detection.md · reference.md   (user-invocable: false)
  stive-auditor/                 ← Auditor / backlog (PICKER)
    stive-auditor.agent.md         entry visible
  spring-engineer/               ← Sub-agente Spring Boot (oculto)
    spring-engineer.agent.md       (user-invocable: false)
    templates-hexagonal.md · templates-traditional.md   (user-invocable: false)
  quarkus-engineer/              ← Sub-agente Quarkus (oculto)
    quarkus-engineer.agent.md      (user-invocable: false)
    templates-hexagonal.md · templates-traditional.md   (user-invocable: false)
  spring-to-quarkus/             ← Sub-agente de migración (oculto)
    spring-to-quarkus.agent.md     (user-invocable: false)
    restructure-guide.md · dependency-mapping.md · migration-rules.md · checklist.md
skills/                          ← Skills invocables por nombre (raíz + categorías declaradas en plugin.json)
  spec-generator/ · plan-generator/ · pr-creator/ · tech-auditor/
  security/    → code-reviewer · domain-purity-checker · mock-strategist
  testing/     → coverage-enforcer · local-deployment-verifier · test-generator · test-runner
  spring-boot/ → spring-use-case-implementer · spring-webclient-configurator
  quarkus/     → quarkus-migrator-from-spring
docs/                            ← Lineamientos compartidos (arquitectura, estándares, BIAN) que consumen los agentes
templates/                       ← Plantillas (HU, etc.)
scripts/                         ← validate.py (lint de convenciones) · jira_mcp_server.py (MCP JIRA local de pruebas)
```

### Convención de agentes (escalable)

Cada agente vive en **su propia carpeta** `agents/<nombre>/`, declarada explícitamente en el array `agents` de `plugin.json`:

- **Entry** `agents/<nombre>/<nombre>.agent.md` — el "cerebro": reglas, decisiones y cuándo actúa.
- **Archivos de soporte** en la misma carpeta — templates, guías y scripts que el entry referencia por ruta relativa al plugin.

> ⚠️ **Regla de oro del picker:** al declarar una carpeta en `agents`, VS Code registra como agente **cada `.md` que contenga**. Por eso **todo archivo de soporte lleva `user-invocable: false`** en su frontmatter, y solo los entries de `stive-sdlc` y `stive-auditor` quedan visibles.

### Reglas de descubrimiento (importantes, no obvias)

El descubrimiento de VS Code **NO es recursivo**: solo mira un nivel dentro de cada carpeta declarada en `plugin.json`. Por eso:

- **Agentes** — cada agente debe estar declarado: `agents/<nombre>/<nombre>.agent.md`, con la carpeta listada en el array `agents`.
- **Skills** — cada skill debe estar **exactamente un nivel** bajo una raíz declarada: `<raíz>/<skill>/SKILL.md`, y el `name` del frontmatter **debe** coincidir con el nombre de su carpeta (si no, el skill no se carga). Las categorías (`security/`, `testing/`, ...) se habilitan declarándolas como raíces en el array `skills`.

### Cómo extender (checklist)

**Añadir un agente:**
1. `agents/<nombre>/<nombre>.agent.md` con frontmatter (`name`, `description`, `tools`).
2. Añade `"agents/<nombre>"` al array `agents` de `plugin.json`.
3. `user-invocable: false` en el entry si NO debe salir en el picker, y en **todos** sus archivos de soporte.
4. Si es un sub-agente que invoca el orquestador, añade su `name` al frontmatter `agents:` de `stive-sdlc`.

**Añadir un skill:**
1. `skills/<categoría>/<skill>/SKILL.md` con `name: <skill>` (igual al nombre de la carpeta).
2. Si la categoría es nueva, añade `"skills/<categoría>"` al array `skills` de `plugin.json`.
3. Referéncialo por **nombre** desde el agente que lo use.

**Añadir un framework / sub-agente de implementación nuevo** (ej. `node-engineer`) — toca varios puntos porque el orquestador y el planificador necesitan conocer la opción:
1. Crea el sub-agente: `agents/<framework>-engineer/<framework>-engineer.agent.md` con `user-invocable: false` (+ su carpeta de soporte, todo blindado).
2. Decláralo en el array `agents` de `plugin.json`.
3. Añade su `name` al frontmatter `agents:` de `stive-sdlc`.
4. Enseña a detectarlo: añade la regla de detección en `agents/stive-sdlc/detection.md` (cómo se reconoce el framework).
5. Enseña a seleccionarlo: añade el caso en `skills/plan-generator/SKILL.md` (qué `implementationAgent` asignar).
6. Verifica con el validador (abajo).

### Validación

Antes de commitear cambios, corre el validador — comprueba que todo agente esté declarado, los soportes blindados, los skills cubiertos por una raíz, las referencias resuelvan y no haya nombres rotos:

```bash
python3 scripts/validate.py
```

Sale con código `!= 0` si hay errores. Ideal como pre-commit hook.

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
