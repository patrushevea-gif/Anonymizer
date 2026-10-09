# Anonymizer

Локальный сервис обезличивания данных для Windows. Находит персональные
данные в документах, заменяет их псевдонимами перед отправкой в облачные
ИИ-сервисы и восстанавливает оригинальные значения из ответов.

## Ключевой принцип: Zero Network

Приложение не выполняет никаких сетевых запросов. Все модели и словари
включены в установщик. Проверка — юнит-тест `tests/test_zero_network.py`.

## Статус

Итерация 0 — каркас проекта:

- PySide6-скелет с двумя полями (обезличивание и обратная замена).
- In-memory `MappingStore` с консистентными псевдонимами.
- Заглушки детекторов (regex и Natasha) — реальная логика появится в MVP.
- Юнит-тесты zero-network: статический скан и runtime-проверка.
- CI: Linux-тесты + Windows-сборка `.exe` через PyInstaller.

## Разработка

```bash
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
python -m anonymizer
```

## Сборка Windows `.exe`

Локально на Windows:

```powershell
pip install -e ".[dev,ner,io,crypto]"
pyinstaller build.spec
# Результат: dist\Anonymizer\Anonymizer.exe
```

Через CI: push в ветку — workflow `Build Windows` соберёт артефакт.

## Структура

```
src/anonymizer/
    app.py              — точка входа Qt
    gui/main_window.py  — главное окно
    core/
        entities.py     — типы сущностей
        mapping.py      — хранилище псевдонимов
        masking.py      — замена по спанам
        reverse.py      — обратная замена
        pipeline.py     — оркестратор
        detectors/      — regex, реквизиты по меткам, ФИО (словарь),
                          адреса, организации, должности, Natasha NER
        persons.py      — связывание форм одного ФИО
        postprocess.py  — фильтры, сквозная замена
    io/ooxml.py         — полная обработка DOCX с сохранением форматирования
    io/                 — загрузчики форматов (iter 2+)
    crypto/             — шифрование проектов (iter 2)
tests/
    test_zero_network.py
    test_smoke.py
```

## Roadmap

- **Iter 0** (готово): каркас + CI.
- **Iter 1**: regex-детекторы, Natasha NER, режим «Маска», обратная замена.
- **Iter 2**: .docx / .xlsx, зашифрованные `.anon`-проекты, таблица правки.
- **Iter 3**: .pdf, batch, правдоподобные замены.
