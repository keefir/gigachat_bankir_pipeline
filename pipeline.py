"""Пайплайн обращения к GigaChat с поддержкой инструментов."""

import json
import logging

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import BaseTool
from langchain_gigachat import GigaChat

from config import Settings
from tools import load_tools

logger = logging.getLogger(__name__)


class GigaChatPipeline:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings = settings or Settings.load()
        self.llm = GigaChat(**settings.gigachat_kwargs())
        loaded = load_tools(settings.tools, settings.tool_schemas_dir)
        self.tools: dict[str, BaseTool] = {t.name: t.impl for t in loaded}
        # Обёртка {"type": "function", ...} — чтобы langchain_gigachat отправил
        # схему из schemas/ без преобразований
        self.runnable = (
            self.llm.bind_tools([{"type": "function", "function": t.schema} for t in loaded])
            if loaded
            else self.llm
        )
        logger.info("Модель: %s, инструменты: %s", settings.model.name, list(self.tools))

    def run(self, query: str, history: list[BaseMessage] | None = None) -> AIMessage:
        """Отправляет запрос и выполняет цикл вызова инструментов,
        пока модель не вернёт финальный ответ."""
        messages: list[BaseMessage] = []
        if self.settings.system_prompt:
            messages.append(SystemMessage(self.settings.system_prompt))
        messages.extend(history or [])
        messages.append(HumanMessage(query))

        for _ in range(self.settings.max_tool_iterations):
            response: AIMessage = self.runnable.invoke(messages)
            messages.append(response)
            if not response.tool_calls:
                return response
            for call in response.tool_calls:
                messages.append(self._call_tool(call))

        logger.warning("Достигнут лимит итераций MAX_TOOL_ITERATIONS")
        return self.llm.invoke(messages)

    def _call_tool(self, call: dict) -> ToolMessage:
        name, args = call["name"], call["args"]
        logger.info("Вызов инструмента %s(%s)", name, args)
        tool = self.tools.get(name)
        if tool is None:
            content = f"Инструмент {name!r} недоступен"
        else:
            try:
                result = tool.invoke(args)
                content = result if isinstance(result, str) else json.dumps(
                    result, ensure_ascii=False
                )
            except Exception as exc:
                content = f"Ошибка инструмента {name}: {exc}"
        logger.info("Результат %s: %s", name, content)
        return ToolMessage(content=content, tool_call_id=call["id"], name=name)
