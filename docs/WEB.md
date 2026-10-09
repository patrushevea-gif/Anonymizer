# ANONYMIZER ROSSILBER — веб-версия

Веб-версия — это тот же Python-движок, что и в настольной программе:
все детекторы, связывание ФИО, сквозная замена, полная обработка DOCX
с сохранением форматирования, контроль утечек и точное восстановление.
К нему добавлены:

* **HTTP API** — стандартное WSGI-приложение (`anonymizer.web.app`);
* **нейросеть** — библиотека Natasha (модели Navec и Slovnet, работают на
  процессоре, без интернета); в интерфейсе она называется
  «ROSSILBER Intelligence»;
* **страница** `index.html` — один файл без внешних зависимостей,
  которую можно открыть напрямую или встроить в сайт через `<iframe>`.

```
Браузер (index.html) ──JSON──▶ anonymizer.web (WSGI) ──▶ движок anonymizer.core / io
```

## Принципы безопасности

* **Сервер ничего не хранит.** Таблица псевдонимов возвращается в браузер
  и передаётся обратно с каждым запросом. На сервере не остаётся ни
  документов, ни персональных данных, ни сессий.
* **Содержимое запросов не логируется**, пишутся только метод, путь и статус.
* **Страница не обращается к внешним сайтам**: строгий CSP
  (`default-src 'none'; connect-src 'self'`), без CDN и шрифтов из сети.
* Все ответы с `Cache-Control: no-store`, чтобы браузеры и прокси
  не кэшировали персональные данные.
* Таблицу псевдонимов можно сохранить на компьютер только в зашифрованном
  виде (AES-256-GCM, ключ из пароля — PBKDF2-SHA256, 600 000 итераций).
  Для этого страница должна открываться по HTTPS.
* Выгрузка DOCX проходит **контроль утечек**. Если в готовом файле
  найдены исходные значения, сервер отвечает `422` и файл не выдаёт.

## Быстрый запуск

Требуется Python 3.11 или 3.12.

```bash
python -m venv .venv
. .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install "setuptools<81"       # pymorphy2 использует pkg_resources
pip install ".[ner,io,web]"
python -m anonymizer.web --host 127.0.0.1 --port 8080
```

Откройте `http://127.0.0.1:8080/`. При старте загружаются модели Natasha
(Navec + Slovnet NER/Morph, ~30 МБ на диске). Это занимает 1–2 секунды
на обычном сервере, на медленном диске дольше. Состояние сервиса видно
в шапке страницы.

Параметры: `--host`, `--port`, `--threads` (по умолчанию 8),
`--no-ner` (только правила, без нейросети — быстрее и экономнее по памяти).

### Docker

```bash
docker build -t anonymizer-rossilber-web .
docker run -d --name anonymizer -p 8080:8080 anonymizer-rossilber-web
```

### Промышленный WSGI-сервер

Приложение создаётся фабрикой `anonymizer.web.app:create_app()`:

```bash
# Linux
gunicorn --workers 2 --threads 4 --timeout 300 -b 127.0.0.1:8080 \
  'anonymizer.web.app:create_app()'

# Windows / Linux (уже входит в extra «web»)
waitress-serve --threads 8 --listen 127.0.0.1:8080 --call anonymizer.web.app:create_app
```

Каждый процесс (worker) загружает модели отдельно: около 210 МБ ОЗУ на
процесс (замер: Python + Natasha + словарь pymorphy2), плюс память на
обрабатываемый документ.
Большие документы обрабатываются до 30–60 секунд, поэтому таймаут нужен не
меньше 300 секунд.

## Настройки (переменные окружения)

| Переменная | По умолчанию | Назначение |
|---|---|---|
| `ANONYMIZER_HOST` / `ANONYMIZER_PORT` | `127.0.0.1` / `8080` | адрес встроенного сервера |
| `ANONYMIZER_USE_NER` | `1` | `0` — без нейросети, только правила |
| `ANONYMIZER_PRELOAD` | `1` | загружать модель при старте, а не при первом запросе |
| `ANONYMIZER_MAX_BODY` | `62914560` (60 МБ) | максимальный размер запроса (файл в base64 больше исходного на ~33 %) |
| `ANONYMIZER_FRAME_ANCESTORS` | `'self'` | какие сайты могут встраивать страницу в `<iframe>`, например `https://portal.company.ru` |
| `ANONYMIZER_CORS_ORIGIN` | не задано | разрешить вызовы API со страницы другого домена |

## Встраивание в сайт

### Вариант 1. Под путём основного сайта (рекомендуется)

Сервис работает за обратным прокси того же домена, тогда CORS не нужен.
Пример для nginx:

```nginx
location /tools/anonymizer/ {
    proxy_pass         http://127.0.0.1:8080/;
    proxy_read_timeout 300s;
    client_max_body_size 64m;
    # авторизация портала — по вашим правилам, например:
    # auth_request /auth;
}
```

Страница обращается к API по относительному пути `api/…`, поэтому она
работает под любым префиксом. Важно: адрес должен заканчиваться слешем
(`/tools/anonymizer/`).

Встраивание в страницу портала:

```html
<iframe src="/tools/anonymizer/" title="Обезличивание документов"
        style="width:100%;height:1400px;border:0"
        sandbox="allow-scripts allow-same-origin allow-downloads allow-modals"></iframe>
```

`allow-downloads` нужен для скачивания DOCX, `allow-modals` — для запроса
пароля при сохранении таблицы псевдонимов.

### Вариант 2. Страница на портале, API на отдельном адресе

Скопируйте `src/anonymizer/web/static/index.html` в портал и укажите адрес API:

```html
<html lang="ru" data-api-base="https://anonymizer.company.ru/">
```

На сервере API задайте `ANONYMIZER_CORS_ORIGIN=https://portal.company.ru`.
Если портал задаёт свою CSP, добавьте адрес API в `connect-src`.

## API

Все вызовы — `POST` с JSON, файлы передаются в base64. Ответ — JSON.
Ошибки приходят как `{"error": "текст для пользователя"}` с кодом 4xx/5xx.

| Метод | Запрос | Ответ |
|---|---|---|
| `GET /api/health` | — | `{status, ner, kinds, uploads}` |
| `POST /api/file/open` | `{filename, file}` | `{text, format}` — полный текст файла; для DOCX все области под заголовками |
| `POST /api/anonymize` | `{text, options}` | `{masked_text, spans, counts, mapping}` |
| `POST /api/remask` | `{text, spans, mapping, disabled:[псевдонимы]}` | то же, без отключённых сущностей |
| `POST /api/docx/export` | `{file, spans, mapping}` | `{file, report}`; `422` при непройденном контроле утечек |
| `POST /api/restore` | `{text, mapping}` | `{text}` |
| `POST /api/docx/restore` | `{file, mapping}` | `{file, restored}` |

`options`: `use_ner` (bool), `disabled_kinds` (список кодов: `"ТЕЛ"`, `"ФИО"`…),
`allowlist` (исключения), `manual` (`[{start, end, kind}]` — ручная разметка).

Сценарий для DOCX: `file/open` → `anonymize` с полученным текстом →
(при необходимости `remask`) → `docx/export` с исходным файлом, `spans`
и `mapping` из последнего ответа.

## Проверка

```bash
pip install ".[ner,io,web,dev]"
pytest tests/test_web.py tests/test_acceptance_docx.py
```
