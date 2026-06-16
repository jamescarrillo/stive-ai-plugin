#!/usr/bin/env python3
"""
Validador del Agent Plugin de Stive AI.

Verifica las convenciones de descubrimiento y referencia de VS Code Agent Plugins,
para que añadir agentes/skills no rompa el picker ni deje recursos sin cargar.

Uso:
    python3 scripts/validate.py        # desde la raíz del repo

Sale con código != 0 si hay errores (✗). Las advertencias (⚠) no bloquean.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
errors: list[str] = []
warns: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warns.append(msg)


def frontmatter(path: Path) -> dict:
    """Parser mínimo de frontmatter YAML (clave: valor de una línea)."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    fm: dict = {}
    for line in text[3:end].splitlines():
        if ":" in line and not line.lstrip().startswith("#"):
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm


# ---------------------------------------------------------------------------
# 1. Manifiestos JSON
# ---------------------------------------------------------------------------
plugin = {}
try:
    plugin = json.loads((ROOT / "plugin.json").read_text())
except Exception as e:  # noqa: BLE001
    err(f"plugin.json no parsea: {e}")

try:
    json.loads((ROOT / ".mcp.json").read_text())
except FileNotFoundError:
    warn(".mcp.json no existe (¿sin servidores MCP?)")
except Exception as e:  # noqa: BLE001
    err(f".mcp.json no parsea: {e}")


def as_list(v) -> list[str]:
    if v is None:
        return []
    return [v] if isinstance(v, str) else list(v)


agent_roots = [r.rstrip("/") for r in as_list(plugin.get("agents"))]
skill_roots = [r.rstrip("/") for r in as_list(plugin.get("skills"))]

for r in agent_roots + skill_roots:
    if not (ROOT / r).is_dir():
        err(f"plugin.json declara una raíz inexistente: {r}")

# ---------------------------------------------------------------------------
# 2. Agentes: cada carpeta con *.agent.md debe estar declarada; frontmatter ok
# ---------------------------------------------------------------------------
agent_files = list((ROOT / "agents").rglob("*.agent.md"))
agent_names: dict[str, Path] = {}
visible: list[str] = []

for f in agent_files:
    rel_folder = str(f.parent.relative_to(ROOT))
    if rel_folder not in agent_roots:
        err(f"Agente NO declarado en plugin.json: {rel_folder} "
            f"(añade \"{rel_folder}\" al array agents)")
    fm = frontmatter(f)
    name = fm.get("name")
    if not name:
        err(f"Agente sin 'name' en frontmatter: {f.relative_to(ROOT)}")
        continue
    if name in agent_names:
        err(f"Nombre de agente duplicado '{name}': {f.relative_to(ROOT)} "
            f"y {agent_names[name].relative_to(ROOT)}")
    agent_names[name] = f
    if f.parent.name != name:
        warn(f"Agente '{name}' no coincide con su carpeta '{f.parent.name}'")
    if fm.get("user-invocable", "true").lower() != "false":
        visible.append(name)

# Soporte: todo .md (no *.agent.md) dentro de una carpeta de agente debe ir oculto
for root in agent_roots:
    for f in (ROOT / root).glob("*.md"):
        if f.name.endswith(".agent.md"):
            continue
        fm = frontmatter(f)
        if fm.get("user-invocable", "true").lower() != "false":
            err(f"Archivo de soporte sin 'user-invocable: false' (saldría en el "
                f"picker): {f.relative_to(ROOT)}")

# ---------------------------------------------------------------------------
# 2b. Nombres de tools válidos (los no reconocidos se ignoran en silencio)
# ---------------------------------------------------------------------------
VALID_TOOLS = {
    "execute", "read", "edit", "search", "agent", "web", "todo",
    "shell", "bash", "powershell", "notebookread", "multiedit", "write",
    "notebookedit", "grep", "glob", "custom-agent", "task",
    "websearch", "webfetch", "todowrite",
}
for f in agent_files:
    raw = frontmatter(f).get("tools")
    if not raw:
        continue
    for t in re.findall(r"[A-Za-z0-9_./-]+", raw):
        if t == "*" or "/" in t:  # comodín o tool de MCP (server/tool)
            continue
        if t not in VALID_TOOLS:
            warn(f"{f.relative_to(ROOT)}: tool '{t}' no es un alias válido "
                 f"(se ignoraría en silencio)")

# ---------------------------------------------------------------------------
# 3. Skills: un nivel bajo una raíz declarada; name == carpeta
# ---------------------------------------------------------------------------
skill_names: set[str] = set()
for f in (ROOT / "skills").rglob("SKILL.md"):
    parent = f.parent.name
    grandparent = str(f.parent.parent.relative_to(ROOT))
    fm = frontmatter(f)
    name = fm.get("name")
    skill_names.add(parent)
    if name != parent:
        err(f"Skill '{f.relative_to(ROOT)}': name '{name}' != carpeta '{parent}'")
    if grandparent not in skill_roots:
        err(f"Skill no cubierto por ninguna raíz declarada: {f.relative_to(ROOT)} "
            f"(añade \"{grandparent}\" al array skills)")

# ---------------------------------------------------------------------------
# 4. Referencias por ruta a recursos del plugin deben resolver
#    (se excluyen .github/ que son artefactos de salida del workspace destino)
# ---------------------------------------------------------------------------
ref_re = re.compile(r"(?:agents|skills|docs|templates)/[A-Za-z0-9_./-]+\.(?:md|py|json)")
for md in ROOT.rglob("*.md"):
    if "/.git/" in str(md):
        continue
    for m in set(ref_re.findall(md.read_text(encoding="utf-8"))):
        ref = m.rstrip("`).,")
        if not (ROOT / ref).is_file():
            err(f"Referencia por ruta rota en {md.relative_to(ROOT)}: {ref}")

# ---------------------------------------------------------------------------
# 5. Sub-agentes declarados en `agents:` de cada entry deben existir
# ---------------------------------------------------------------------------
for f in agent_files:
    fm = frontmatter(f)
    raw = fm.get("agents")
    if not raw:
        continue
    for sub in re.findall(r"[a-z0-9-]+", raw):
        if sub and sub not in agent_names:
            err(f"{f.relative_to(ROOT)} declara sub-agente inexistente: '{sub}'")

# ---------------------------------------------------------------------------
# 6. Advertencias: skills huérfanos (no referenciados por ningún agente)
# ---------------------------------------------------------------------------
# Se referencian desde cualquier .md del árbol agents/ (entries o soporte como reference.md)
agents_text = "\n".join(
    f.read_text(encoding="utf-8") for f in (ROOT / "agents").rglob("*.md")
)
for sk in sorted(skill_names):
    if f"`{sk}`" not in agents_text:
        warn(f"Skill '{sk}' no referenciado por ningún agente (¿huérfano?)")

# ---------------------------------------------------------------------------
# Reporte
# ---------------------------------------------------------------------------
print(f"Agentes visibles en el picker: {sorted(visible)}")
print(f"Agentes ocultos: {sorted(set(agent_names) - set(visible))}")
print(f"Skills descubribles: {len(skill_names)}")
print()

for w in warns:
    print(f"  ⚠  {w}")
for e in errors:
    print(f"  ✗  {e}")

if errors:
    print(f"\n✗ {len(errors)} error(es), {len(warns)} advertencia(s).")
    sys.exit(1)
print(f"\n✓ Sin errores ({len(warns)} advertencia(s)).")
