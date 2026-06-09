"""Lumi tool registry.

Each tool is a top-level function in one of the tools/*.py modules, decorated
with @tool(name=..., description=..., parameters=...). Decoration registers
the function into REGISTRY and generates the OpenAI-compatible JSON schema.

  from tools import tool

  @tool(
      name="open_app",
      description="Launch an application by name on Windows.",
      parameters={
          "type": "object",
          "properties": {
              "name": {"type": "string", "description": "App name, e.g. 'notepad'"},
          },
          "required": ["name"],
      },
  )
  def open_app(name: str) -> str:
      ...
      return "opened notepad"

The string the tool returns is what the LLM sees as the tool result. Tools may
raise — the executor catches and reports the exception text to the model.

Importing this package (`import tools`) eagerly imports every tools/*.py
module so all decorators run, populating REGISTRY for the executor.
"""
from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]    # JSON Schema for the args object
    func: Callable[..., Any]
    module: str
    confirm: bool = False         # if True, executor refuses unless user opted in

    def to_openai_schema(self) -> dict[str, Any]:
        """Format expected by the chat/completions `tools` parameter."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


REGISTRY: dict[str, ToolSpec] = {}


def tool(
    *,
    name: str,
    description: str,
    parameters: dict[str, Any],
    confirm: bool = False,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator that registers a function as an LLM-callable tool."""

    def deco(func: Callable[..., Any]) -> Callable[..., Any]:
        if name in REGISTRY:
            raise RuntimeError(f"tool name collision: {name!r} already registered "
                               f"by {REGISTRY[name].module}")
        REGISTRY[name] = ToolSpec(
            name=name,
            description=description,
            parameters=parameters,
            func=func,
            module=func.__module__,
            confirm=confirm,
        )
        return func

    return deco


def _autoload_submodules() -> None:
    """Import every tools.* submodule so their @tool decorators run.

    Avoids the foot-gun of forgetting to update an __init__ when adding a tool.
    """
    pkg = __name__
    for mod_info in pkgutil.iter_modules(__path__):
        if mod_info.name.startswith("_"):
            continue
        try:
            importlib.import_module(f"{pkg}.{mod_info.name}")
        except Exception as e:  # noqa: BLE001
            # Don't kill the whole load on a broken tool — log and continue.
            print(f"[tools] WARNING: failed to load tools.{mod_info.name}: {e}")


_autoload_submodules()
