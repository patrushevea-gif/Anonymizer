"""Help / About dialog.

Documents the full feature set and shows the copyright banner so the user
always has a way to remind a third party that the software is proprietary.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QLabel,
    QTextBrowser,
    QVBoxLayout,
)

from anonymizer import __version__

_HELP_HTML = """
<style>
  body  {{ color: #e8e8e8; font-family: 'Segoe UI', sans-serif; font-size: 14px; }}
  h2    {{ color: #00d4ff; font-size: 14px; letter-spacing: 1.5px;
          margin: 18px 0 6px 0; text-transform: uppercase; }}
  h3    {{ color: #ffffff; font-size: 13px; margin: 10px 0 4px 0; }}
  p, li {{ line-height: 1.55; }}
  ul    {{ margin-top: 4px; }}
  code  {{ background-color: #1c1c1c; padding: 1px 5px; border-radius: 2px;
          font-family: 'Consolas', monospace; font-size: 12px; }}
  .dim  {{ color: #888; font-size: 12px; }}
</style>

<h2>О программе</h2>
<p><b>ANONYMIZER ROSSILBER</b> — локальное приложение для обезличивания
персональных и конфиденциальных данных в документах перед отправкой их
во внешние ИИ-сервисы. Все операции выполняются на вашем компьютере:
программа <b>не отправляет данные в сеть</b>.</p>

<h2>Основные функции</h2>
<h3>Обезличивание</h3>
<ul>
  <li>Вставьте текст в поле «Исходный текст» или перетащите файл
      (<code>.txt</code>, <code>.docx</code>, <code>.xlsx</code>, <code>.pdf</code>).</li>
  <li>Нажмите <b>Обезличить</b> (<code>Ctrl+Enter</code>) — программа
      найдёт чувствительные данные и заменит их на псевдонимы вида
      <code>ФИО1</code>, <code>ТЕЛ1</code>, и т.п.</li>
  <li>Скопируйте обезличенный текст в буфер (<code>Ctrl+Shift+C</code>)
      и отправьте его в любой ИИ-сервис.</li>
  <li>Найденное значение заменяется <b>везде</b>, где встречается в документе,
      в том числе в других падежах фамилии.</li>
</ul>

<h3>Документы Word (.docx)</h3>
<ul>
  <li>Документ читается <b>целиком</b>: основной текст, таблицы, верхние и
      нижние колонтитулы, комментарии, сноски, надписи, скрытый текст,
      гиперссылки, поля и свойства файла. Каждая область видна в поле
      «Исходный текст» под своим заголовком.</li>
  <li><b>Сохранить результат</b> в формате Word — псевдонимы встают на место
      исходных данных, <b>форматирование сохраняется</b> (шрифт, жирный,
      курсив, цвет, подчёркивание, таблицы, стили); скрытый текст остаётся
      скрытым.</li>
  <li>Из файла удаляются автор, последний редактор, организация, менеджер,
      авторы комментариев и исправлений, пользовательские свойства,
      миниатюра первой страницы и путь к шаблону.</li>
  <li>После сохранения выполняется <b>контроль утечек</b>: готовый файл
      перечитывается и проверяется на остатки каждого заменённого значения
      во всех частях. Если что-то найдено, файл не сохраняется.</li>
  <li>Текст на изображениях и во встроенных объектах не распознаётся —
      программа предупредит, если они есть в документе.</li>
</ul>

<h3>Восстановление</h3>
<ul>
  <li>Вставьте ответ ИИ в поле «Ответ ИИ».</li>
  <li>Нажмите <b>Восстановить оригинальные данные</b> — программа
      развернёт все псевдонимы обратно в исходные значения. Неизменённый
      текст восстанавливается посимвольно точно, каждое упоминание — в своей
      исходной форме.</li>
  <li><b>Восстановить файл Word…</b> — вернуть исходные данные в
      обезличенный (или отредактированный ИИ) документ .docx с сохранением
      форматирования.</li>
</ul>

<h3>Редактирование маппингов</h3>
<ul>
  <li>Таблица «Маппинги сущностей» показывает, что было заменено.</li>
  <li>Снимите галочку «Активно» — данные вернутся в исходном виде во всех
      формах и местах документа (полезно для ложных срабатываний).</li>
</ul>

<h3>Ручная разметка</h3>
<ul>
  <li>Выделите текст в поле «Исходный текст».</li>
  <li>ПКМ → «Пометить выделенное как…» → выберите тип.</li>
  <li>Нажмите <b>Обезличить</b> — ручные пометки имеют
      максимальный приоритет.</li>
</ul>

<h3>Шифрованные проекты <code>.anon</code></h3>
<ul>
  <li><b>Сохранить проект</b> (<code>Ctrl+Shift+S</code>) — сохраняет
      исходный и обезличенный текст + маппинги в файл, зашифрованный
      AES-256-GCM с ключом, производным от пароля (Argon2id).</li>
  <li><b>Загрузить проект</b> (<code>Ctrl+L</code>) — восстанавливает
      сохранённую сессию после ввода пароля.</li>
</ul>

<h3>Пакетная обработка</h3>
<ul>
  <li><b>Пакетная обработка</b> (<code>Ctrl+B</code>) — выбираете папку
      с документами и папку для результатов. Программа рекурсивно
      обработает все поддерживаемые файлы. Документы Word сохраняются как
      .docx с исходным форматированием и проходят контроль утечек.</li>
</ul>

<h3>Настройки</h3>
<ul>
  <li><b>Настройки</b> (<code>Ctrl+,</code>) — включайте и выключайте
      типы детекторов. Сгруппированы по категориям: персональные,
      документы, финансы, технические данные и т.д.</li>
  <li><b>Исключения</b> — слова и названия, которые никогда не обезличиваются
      (например, название вашей компании).</li>
  <li>Тема оформления: светлая / тёмная.</li>
</ul>

<h2>Поддерживаемые типы данных</h2>
<ul>
  <li><b>Персональные:</b> ФИО во всех падежах и формах записи (Фамилия Имя
      Отчество, Имя Отчество Фамилия, Фамилия И.О., И.О. Фамилия, ПРОПИСНЫМИ),
      должность с подразделением, дата рождения (только если она так
      обозначена — даты договоров не трогаются).</li>
  <li><b>Организации</b> (с кавычками и организационно-правовой формой) и
      <b>почтовые адреса</b> целиком: индекс, город, улица, дом, квартира/офис.</li>
  <li><b>Контакты:</b> телефон (РФ, городские, международные), email, сайты и
      URL, IP-адрес.</li>
  <li><b>По подписи:</b> любые значения после «ИНН», «КПП», «ОГРН», «БИК»,
      «р/с», «к/с», «СНИЛС», «паспорт», «тел.», «пароль:», «токен:» —
      даже если контрольная сумма не сходится.</li>
  <li><b>Документы РФ:</b> ИНН, СНИЛС, паспорт, ОГРН/ОГРНИП, КПП,
      полис ОМС, водительское удостоверение.</li>
  <li><b>Финансы:</b> номера карт (с проверкой Луна), расчётные счета,
      IBAN (с mod-97), БИК.</li>
  <li><b>Транспорт:</b> автомобильные номера.</li>
  <li><b>Технические:</b> API-ключи (OpenAI, Anthropic, GitHub, AWS,
      Google, Stripe, Slack, Telegram bot, JWT, закрытые ключи PEM…),
      химические формулы (целиком, включая индексы и кристаллогидраты:
      <code>CuSO₄·5H₂O</code>), наименования химических реактивов и веществ.</li>
</ul>

<h2>Горячие клавиши</h2>
<ul>
  <li><code>Ctrl+O</code> — открыть файл</li>
  <li><code>Ctrl+S</code> — сохранить результат</li>
  <li><code>Ctrl+Shift+S</code> — сохранить зашифрованный проект</li>
  <li><code>Ctrl+L</code> — загрузить проект</li>
  <li><code>Ctrl+Enter</code> — обезличить</li>
  <li><code>Ctrl+Shift+C</code> — скопировать результат</li>
  <li><code>Ctrl+B</code> — пакетная обработка</li>
  <li><code>Ctrl+,</code> — настройки</li>
</ul>

<h2>Безопасность</h2>
<ul>
  <li>Приложение работает полностью <b>оффлайн</b>. В исходном коде
      отсутствуют импорты сетевых библиотек, это проверяется
      автоматическим тестом при каждой сборке.</li>
  <li>Проекты <code>.anon</code> шифруются AES-256-GCM, ключ выводится
      из пароля через Argon2id (64 MB памяти, 3 итерации).</li>
  <li>Логи приложения пишутся локально в <code>AppData\\Local\\Anonymizer\\logs</code>.</li>
</ul>

<h2>Копирайт</h2>
<p><b>© Patrushev E.</b>, {year}. Все права защищены.</p>
<p class="dim">Программа является проприетарным ПО. Копирование, модификация,
распространение и публикация исходного кода или бинарных сборок без
письменного разрешения правообладателя запрещены.</p>

<p class="dim">Версия: {version}</p>
"""


class HelpDialog(QDialog):
    def __init__(self, parent=None, theme_is_dark: bool = True) -> None:
        super().__init__(parent)
        self.setObjectName("help")
        self.setWindowTitle("Справка — ANONYMIZER ROSSILBER")
        self.resize(720, 760)
        self._theme_is_dark = theme_is_dark

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 14)
        root.setSpacing(12)

        title = QLabel("ANONYMIZER ROSSILBER")
        title.setObjectName("brand")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        root.addWidget(title)

        divider = QFrame()
        divider.setObjectName("divider")
        root.addWidget(divider)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(False)
        browser.setHtml(
            _HELP_HTML.format(year=2026, version=__version__)
        )
        browser.setFrameShape(QFrame.Shape.NoFrame)
        root.addWidget(browser, stretch=1)

        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.button(QDialogButtonBox.StandardButton.Close).setText("Закрыть")
        close.rejected.connect(self.reject)
        close.accepted.connect(self.accept)
        close.clicked.connect(lambda _b: self.accept())
        root.addWidget(close)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        from anonymizer.gui.theme import apply_native_titlebar
        apply_native_titlebar(self, dark=self._theme_is_dark)


class AboutDialog(QDialog):
    """Compact About dialog — shown on demand from a tiny '?' chip."""

    def __init__(self, parent=None, theme_is_dark: bool = True) -> None:
        super().__init__(parent)
        self.setObjectName("help")
        self.setWindowTitle("О программе")
        self.resize(520, 360)
        self._theme_is_dark = theme_is_dark

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 20)
        root.setSpacing(10)

        brand = QLabel("ANONYMIZER ROSSILBER")
        brand.setObjectName("brand")
        brand.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        root.addWidget(brand)

        version = QLabel(f"Версия {__version__}")
        version.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        root.addWidget(version)

        root.addSpacing(10)

        description = QLabel(
            "Локальное обезличивание персональных и конфиденциальных данных "
            "перед отправкой документов во внешние ИИ-сервисы.\n\n"
            "Zero-network, AES-256, поддержка .txt / .docx / .xlsx / .pdf."
        )
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        root.addWidget(description)

        root.addStretch()

        copyright_label = QLabel(
            "© Patrushev E., 2026\n"
            "Все права защищены"
        )
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        root.addWidget(copyright_label)

        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.button(QDialogButtonBox.StandardButton.Close).setText("Закрыть")
        close.rejected.connect(self.reject)
        close.clicked.connect(lambda _b: self.accept())
        root.addWidget(close)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        from anonymizer.gui.theme import apply_native_titlebar
        apply_native_titlebar(self, dark=self._theme_is_dark)
