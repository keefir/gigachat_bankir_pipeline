"""CLI: python main.py "вопрос" — один запрос, без аргументов — интерактивный чат."""

import logging
import sys

from langchain_core.messages import BaseMessage, HumanMessage

from pipeline import GigaChatPipeline


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    pipeline = GigaChatPipeline()

    if len(sys.argv) > 1:
        print(pipeline.run(" ".join(sys.argv[1:])).content)
        return

    history: list[BaseMessage] = []
    while True:
        try:
            query = input("\nВы: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not query:
            continue
        answer = pipeline.run(query, history)
        print(f"GigaChat: {answer.content}")
        history += [HumanMessage(query), answer]


if __name__ == "__main__":
    main()
