# GigaChat pipeline

Пайплайн обращения к GigaChat через [`langchain_gigachat`](https://github.com/ai-forever/langchain-gigachat)
с поддержкой инструментов (function calling). Схемы инструментов задаются JSON-файлами
в формате GigaChat и отправляются в API без изменений.

## Быстрый старт

```bash
sudo apt install -y python3-venv python3-pip   # если ещё не установлены
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env    # и вписать GIGACHAT_CREDENTIALS
```

Запуск:

```bash
python main.py "Сколько будет 17*23 и который сейчас час?"   # один запрос
python main.py                                               # интерактивный чат с историей
```

Из кода:

```python
from pipeline import GigaChatPipeline

pipeline = GigaChatPipeline()
print(pipeline.run("Посчитай 15% от 2400").content)
```

## Структура

```
.env / .env.example    авторизация и подключение (секреты)
config.yaml            модель, параметры генерации, промпты, список тулов
prompts/system.md      системный промпт
schemas/<tool>.json    схемы инструментов — то, что видит модель
tools/<module>.py      реализации инструментов — то, что выполняется
config.py              загрузка .env и config.yaml
pipeline.py            GigaChatPipeline: цикл модель → тулы → модель
main.py                CLI
```

## Конфигурация

Настройки разделены на два файла:

- **`.env`** — только то, что относится к авторизации и окружению. Не коммитится (`.gitignore`).
- **`config.yaml`** — всё, что меняется часто.

### `.env`

| Переменная | Описание |
|---|---|
| `GIGACHAT_CREDENTIALS` | Ключ авторизации (Authorization key) из личного кабинета |
| `GIGACHAT_SCOPE` | `GIGACHAT_API_PERS` — физлица, `GIGACHAT_API_B2B` / `GIGACHAT_API_CORP` — юрлица |
| `GIGACHAT_VERIFY_SSL_CERTS` | Проверка SSL-сертификатов. Для продакшена установите сертификат Минцифры и укажите `true` |
| `GIGACHAT_CA_BUNDLE_FILE` | Путь к CA-бандлу (необязательно) |
| `GIGACHAT_BASE_URL` | Адрес API (необязательно, по умолчанию `https://api.giga.chat/v1`) |
| `CONFIG_PATH` | Путь к другому `config.yaml` (необязательно) |

Пустые переменные `GIGACHAT_*` игнорируются, и SDK использует свои значения по умолчанию.

### `config.yaml`

```yaml
model:
  name: GigaChat-2
  temperature: 0.7
  top_p: 0.9
  max_tokens: 1024
  repetition_penalty: 1.0
  profanity_check: false
  streaming: false
  timeout: 60

prompts:
  system: prompts/system.md     # путь относительно config.yaml

pipeline:
  max_tool_iterations: 5        # сколько раз подряд модель может вызвать тулы

tools:                          # какие инструменты подключать; пусто — без тулов
  - get_current_datetime
  - calculator

tool_schemas_dir: schemas
```

- Закомментированный параметр в `model` не передаётся, и действует значение по умолчанию из библиотеки.
- Опечатка в имени параметра (например, `temprature`) даёт ошибку при запуске.
- Можно держать несколько конфигов и выбирать нужный: `CONFIG_PATH` в `.env`
  или `GigaChatPipeline(Settings.load("config.prod.yaml"))`.

## Инструменты

Инструмент состоит из двух частей с одинаковым именем:

1. **Реализация** — функция с декоратором `@tool` в любом модуле папки `tools/`.
   Модули подхватываются автоматически.
2. **Схема** — `schemas/<имя>.json` в формате функции GigaChat.

### Добавить инструмент

`tools/weather.py`:

```python
from langchain_core.tools import tool


@tool
def get_weather(city: str) -> dict:
    """Погода. Схема для модели — schemas/get_weather.json."""
    return {"temperature": 12, "description": "облачно"}
```

`schemas/get_weather.json`:

```json
{
  "name": "get_weather",
  "description": "Возвращает текущую погоду в указанном городе.",
  "parameters": {
    "type": "object",
    "properties": {
      "city": {"type": "string", "description": "Название города, например \"Москва\""}
    },
    "required": ["city"]
  },
  "return_parameters": {
    "type": "object",
    "properties": {
      "temperature": {"type": "number", "description": "Температура, °C"},
      "description": {"type": "string", "description": "Описание погоды"}
    }
  },
  "few_shot_examples": [
    {"request": "Какая погода в Казани?", "params": {"city": "Казань"}}
  ]
}
```

После этого добавьте `get_weather` в `tools:` в `config.yaml`.

### Важно

- **Модель видит только схему.** `description` берётся из JSON, а докстринг функции в GigaChat
  не отправляется. Короткий докстринг всё равно нужен: без него `@tool` не создаёт инструмент.
- **Возвращайте данные в формате `return_parameters`.** Если результат не строка
  (например, dict), он сериализуется в JSON. Схема результата служит модели подсказкой
  и не проверяется.
- **При запуске проверяется**, что для каждого тула из конфига есть реализация и схема,
  `name` в схеме совпадает с именем файла, а аргументы в `parameters.properties`
  совпадают с аргументами функции.
- **Ошибки при выполнении** тула не роняют пайплайн: текст ошибки передаётся модели как результат.

Посмотреть, что уходит в API:

```python
from config import Settings
from tools import load_tools

for t in load_tools(Settings.load().tools, Settings.load().tool_schemas_dir):
    print(t.schema)
```
