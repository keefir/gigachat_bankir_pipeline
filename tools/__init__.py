"""Реестр инструментов.

Реализация инструмента — функция с декоратором @tool (или экземпляр BaseTool)
в любом модуле папки tools/; подхватывается автоматически по `name`.

Схема инструмента для модели — файл <имя>.json в папке схем (schemas/)
в формате функции GigaChat: name, description, parameters,
return_parameters, few_shot_examples. Схема отправляется в GigaChat как есть.
"""

import importlib
import json
import pkgutil
from dataclasses import dataclass
from pathlib import Path

from langchain_core.tools import BaseTool


@dataclass
class LoadedTool:
    schema: dict
    impl: BaseTool

    @property
    def name(self) -> str:
        return self.schema["name"]


def discover_tools() -> dict[str, BaseTool]:
    """Импортирует все модули пакета tools и собирает найденные реализации."""
    registry: dict[str, BaseTool] = {}
    for module_info in pkgutil.iter_modules(__path__):
        if module_info.name.startswith("_"):
            continue
        module = importlib.import_module(f"{__name__}.{module_info.name}")
        for obj in vars(module).values():
            if isinstance(obj, BaseTool):
                if obj.name in registry and registry[obj.name] is not obj:
                    raise ValueError(f"Дублирующееся имя инструмента: {obj.name!r}")
                registry[obj.name] = obj
    return registry


def load_schema(name: str, schemas_dir: Path) -> dict:
    path = schemas_dir / f"{name}.json"
    if not path.exists():
        raise ValueError(f"Нет схемы для инструмента {name!r}: {path}")
    schema = json.loads(path.read_text(encoding="utf-8"))
    if schema.get("name") != name:
        raise ValueError(f"{path}: поле name={schema.get('name')!r} не совпадает с {name!r}")
    if not schema.get("description"):
        raise ValueError(f"{path}: поле description обязательно")
    return schema


def _check_args(schema: dict, impl: BaseTool) -> None:
    """Аргументы из схемы должны совпадать с аргументами реализации."""
    schema_args = set((schema.get("parameters") or {}).get("properties") or {})
    impl_args = set(impl.args)
    if schema_args != impl_args:
        raise ValueError(
            f"Инструмент {impl.name!r}: аргументы в схеме {sorted(schema_args)} "
            f"не совпадают с аргументами функции {sorted(impl_args)}"
        )


def load_tools(names: list[str], schemas_dir: Path) -> list[LoadedTool]:
    """Возвращает инструменты (схема + реализация) по списку имён из конфига."""
    registry = discover_tools()
    missing = [name for name in names if name not in registry]
    if missing:
        raise ValueError(
            f"Реализации инструментов не найдены: {missing}. Доступные: {sorted(registry)}"
        )
    loaded = []
    for name in names:
        schema = load_schema(name, schemas_dir)
        _check_args(schema, registry[name])
        loaded.append(LoadedTool(schema=schema, impl=registry[name]))
    return loaded
