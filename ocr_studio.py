# -*- coding: utf-8 -*-
"""
Единый Робот v43.17.73 LOWERCASE FIO FIX — восстановление ФИО с ошибочным регистром
FIX v43.17.73:
- Фамилия с ошибочно распознанной строчной первой буквой восстанавливается перед строгой проверкой ФИО.
- Исправление ограничено трёхсловными ФИО с характерным окончанием отчества, чтобы не принимать обычный текст.
- Для бланков со строкой «квартира №…, машино-место №…, комната №…» номер квартиры ищется по подписи, а не по фиксированной позиции шаблона.
- Двухсловные ФИО разрешены для всех шаблонов внутри обученной зоны ФИО или найденной строки собственника.
- Бланк 101 использует быстрые расширенные ROI: шаблон не перебирает всю базу и не запускает тяжёлый каскад из-за узких сохранённых зон.
- Логика внесения полностью сохранена из v43.17.60 без изменений.
- внесение RobotHelper остаётся дословно из v60;
- если шаблон найден, но его зона ФИО не прочиталась, выполняется один
  резервный поиск строки собственника до отправки документа в проверку;
- вспомогательному Tesseract дано 9 секунд вместо слишком жёстких 6 секунд.

FIX v43.17.71:
- весь класс внесения RobotHelper дословно перенесён из рабочей v43.17.60;
- внутри внесения нет проверок, ожиданий и навигации из v67-v70;
- улучшения OCR, скорости и шаблонов v69 сохранены вне RobotHelper.

FIX v43.17.69:
- точные дубли layout-шаблонов удаляются автоматически с резервной копией;
- одинаковые кандидаты больше не занимают весь список лучших совпадений;
- предыдущий шаблон используется без полного поиска только при сильном
  геометрическом и структурном совпадении;
- при неуверенном совпадении проверяется расширенный список кандидатов.

FIX v43.17.68:
- во время внесения OCR сохраняет качество, но выполняет тяжёлые Tesseract-проходы
  последовательно, не отбирая процессор у Chrome;
- исправлена установка низкого приоритета постоянного OCR worker в Windows;
- ожидание необязательного поля e-mail сокращено без изменения порядка внесения.

FIX v43.17.67:
  • Переход к бюллетеню выполняется через неблокирующую навигацию Chrome CDP.
  • Ответ поиска собственника ожидается явно; переходы больше не опираются на паузы 0,05 с.
  • Во время внесения OCR получает минимальный фоновый приоритет, освобождая Chrome.
  • Порядок действий и отправки голоса сохранён.
FIX v43.17.66:
  • «Инструменты» открывают отдельную надёжную панель вместо системного popup-меню.
  • Панель можно повторно поднять поверх главного окна; все прежние команды сохранены.
FIX v43.17.65:
  • Внесение закреплено за одной вкладкой Chrome; обычная задержка портала больше
    не создаёт и не переключает вкладки.
  • Динамическая кнопка «Продолжить» и форма собственника ожидаются в текущей
    вкладке без повторной перезагрузки страницы на каждом коротком тайм-ауте.
  • Порядок и логика шагов внесения не изменены.
FIX v43.17.64:
  • «Инструменты» переведены на штатный Menubutton: меню открывается напрямую.
  • Подсказки больше не перекрывают кнопки и не перехватывают щелчок мыши.
FIX v43.17.63:
  • OCR worker запускается один раз и переиспользуется для всей партии.
  • 130-МБ templates.json загружается один раз и обновляется при изменении файла.
  • Отмена/тайм-аут безопасно перезапускают worker; логика OCR и внесения не изменена.
FIX v43.17.62:
  • Уникальные документы отделены от повторных попыток внесения.
  • Размер очереди обновляется, если OCR добавляет документы после запуска.
  • Дневные счётчики обновляются в шапке сразу после успешного действия.
  • OCR worker больше не перезаписывает daily_stats.json при старте.
FIX v43.17.61:
  • Chrome использует стратегию загрузки eager и не ждёт второстепенные ресурсы.
  • После тайм-аута сохраняется уже загруженный DOM; зависшая вкладка заменяется
    новой вкладкой той же сессии без потери авторизации и порядка очереди.
  • Дочерний OCR получает пониженный приоритет, пока работает внесение.
FIX v43.17.54 (без потери качества):
  • Параллельные Tesseract-проходы: FIO + Room, expansion, smart-verify,
    turbo-room — там, где раньше вызовы шли строго последовательно.
  • ORB-дескрипторы шаблонов предвычисляются один раз и хранятся numpy-массивами.
  • Дополнительных проверок/порогов не добавлено — качество идентично v43.17.53.
FIX v43.17.53:
  • SCRIPT_DIR больше не перезаписывается папкой задания в --ocr-job режиме.
  • _run_job читает worker.log и показывает диагностику дочернего процесса.
  • Дочерний процесс запускается с -u; лимит времени 200/300 с.
FIX v43.17.52: анализ и удаление дублей обученных шаблонов.
FIX v43.17.51: обучение шаблона работает; адаптивное расширение ROI.
Порядок шагов внесения и Аналитика не изменялись.
"""
import os, sys, shutil, re, json, time, threading, tkinter as tk, hashlib, queue, subprocess, tempfile, zipfile
from urllib.parse import urlparse
from tkinter import ttk, messagebox, simpledialog, filedialog
from PIL import Image, ImageTk, ImageEnhance, ImageFilter, ImageOps
import pytesseract
from pdf2image import convert_from_path
from datetime import datetime, timedelta
import winsound, logging
from functools import partial
from concurrent.futures import ThreadPoolExecutor
import warnings
warnings.filterwarnings("ignore")
OCR_WORKER_MODE = '--ocr-job' in sys.argv or '--ocr-worker' in sys.argv

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except Exception: NUMPY_AVAILABLE = False
try:
    import cv2
    OPENCV_AVAILABLE = True
except Exception: OPENCV_AVAILABLE = False
easyocr = None
EASYOCR_AVAILABLE = False
if OCR_WORKER_MODE:
    SELENIUM_AVAILABLE = False
    EXCEL_AVAILABLE = False
else:
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.chrome.service import Service as ChromeService
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, NoSuchElementException
        from webdriver_manager.chrome import ChromeDriverManager
        SELENIUM_AVAILABLE = True
    except Exception: SELENIUM_AVAILABLE = False
    try:
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
        EXCEL_AVAILABLE = True
    except Exception: EXCEL_AVAILABLE = False

PROGRAM_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))

def _working_data_score(path):
    """Return how likely *path* is the existing OCR Studio data directory."""
    if not path or not os.path.isdir(path):
        return -1
    score = 0
    for filename, weight in (
            ('templates.json', 12), ('roi_data.json', 10),
            ('learning_data.json', 8), ('ocr_session_v43.json', 6),
            ('stats.json', 3)):
        if os.path.isfile(os.path.join(path, filename)):
            score += weight
    for dirname, weight in (('source', 5), ('ready', 3), ('processed', 2)):
        folder = os.path.join(path, dirname)
        if os.path.isdir(folder):
            score += weight
            try:
                if os.listdir(folder):
                    score += weight
            except OSError:
                pass
    if os.path.isdir(os.path.join(path, 'poppler-25.07.0')):
        score += 5
    return score

def _resolve_working_data_dir():
    configured = os.environ.get('OCR_STUDIO_DATA_DIR', '').strip()
    if configured and os.path.isdir(configured):
        return os.path.abspath(configured)
    candidates = [
        PROGRAM_DIR,
        os.path.dirname(PROGRAM_DIR),
        os.path.join(os.path.expanduser('~'), 'Desktop', 'Python_scripts'),
    ]
    unique = []
    for candidate in candidates:
        normalized = os.path.abspath(candidate)
        if normalized not in unique and os.path.isdir(normalized):
            unique.append(normalized)
    if not unique:
        return PROGRAM_DIR
    best = max(unique, key=_working_data_score)
    return best if _working_data_score(best) > 0 else PROGRAM_DIR

# Код можно запускать из другой папки, но рабочие source/ready и обученные
# шаблоны должны оставаться в существующем каталоге OCR Studio.
SCRIPT_DIR = _resolve_working_data_dir()
OCR_JOB_DIR = None
if '--ocr-job' in sys.argv:
    try:
        OCR_JOB_DIR = os.path.abspath(sys.argv[sys.argv.index('--ocr-job') + 1])
    except Exception:
        OCR_JOB_DIR = None
LOG_DIR = os.path.join(SCRIPT_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
log_filename = f"robot_{datetime.now().strftime('%Y%m%d')}.log"
log_path = os.path.join(LOG_DIR, log_filename)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler(log_path, encoding='utf-8'), logging.StreamHandler()])
logger = logging.getLogger(__name__)

_BUNDLE_DIR = getattr(sys, '_MEIPASS', SCRIPT_DIR)
_BUNDLED_TESSERACT = os.path.join(_BUNDLE_DIR, 'Tesseract-OCR', 'tesseract.exe')
TESSERACT_PATH = _BUNDLED_TESSERACT if os.path.isfile(_BUNDLED_TESSERACT) else r'C:\Program Files\Tesseract-OCR\tesseract.exe'
_BUNDLED_POPPLER = os.path.join(_BUNDLE_DIR, "poppler-25.07.0", "Library", "bin")
POPPLER_BIN_PATH = _BUNDLED_POPPLER if os.path.isdir(_BUNDLED_POPPLER) else os.path.join(SCRIPT_DIR, "poppler-25.07.0", "Library", "bin")
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
os.environ['PATH'] = POPPLER_BIN_PATH + os.pathsep + os.environ.get('PATH', '')
os.environ.setdefault('OMP_THREAD_LIMIT', '1')

PDF_FOLDER_PATH = os.path.join(SCRIPT_DIR, "pdf")
SOURCE_FOLDER_PATH = os.path.join(SCRIPT_DIR, "source")
READY_FOLDER_PATH = os.path.join(SCRIPT_DIR, "ready")
DUPLICATES_FOLDER_PATH = os.path.join(SCRIPT_DIR, "duplicates")
PROBLEMS_FOLDER_PATH = os.path.join(SCRIPT_DIR, "problems")
LEARNING_DATA_PATH = os.path.join(SCRIPT_DIR, "learning_data.json")
ROI_DATA_PATH = os.path.join(SCRIPT_DIR, "roi_data.json")
PROGRESS_FILE_PATH = os.path.join(SCRIPT_DIR, "progress.json")
STATS_FILE_PATH = os.path.join(SCRIPT_DIR, "stats.json")
TEMPLATES_PATH = os.path.join(SCRIPT_DIR, "templates.json")
TRAINING_BACKUP_DIR = os.path.join(SCRIPT_DIR, "backup_training")
DAILY_STATS_PATH = os.path.join(SCRIPT_DIR, "daily_stats.json")
FIO_DATABASE_PATH = os.path.join(SCRIPT_DIR, "fio_database.txt")
DEV_AUTH_PATH = os.path.join(SCRIPT_DIR, ".robot_dev_auth.json")
PROCESSED_FOLDER_PATH = os.path.join(SCRIPT_DIR, "processed")
OCR_REVIEW_THRESHOLD = 82.0
MANUAL_ROI_BATCH_THRESHOLD = 65.0
FAST_RENDER_DPI = 220
DEEP_RENDER_DPI = 260
SMART_FIO_MIN_CONFIDENCE = 0.0
SMART_TEMPLATE_MIN_SCORE = 0.88
SMART_VERIFIED_CONFIDENCE = 86.0
FIO_PARTICLES = frozenset({'оглы', 'оглу', 'кызы', 'улы', 'уулу'})
# FIX_v43.17.54: сколько потоков разрешаем для параллельных Tesseract-вызовов.
# Tesseract сам по себе однопоточный и запускается как отдельный процесс,
# поэтому параллелизм по ROI и по вариантам preprocessing даёт реальный выигрыш
# на 4+ ядерной машине без изменения самих вызовов и без потери качества.
OCR_PARALLEL_WORKERS = max(2, min(4, (os.cpu_count() or 2)))

INPUT_PRIORITY_PATH = os.path.join(SCRIPT_DIR, '.ocr_studio_input_active')

def _input_priority_active():
    return os.path.isfile(INPUT_PRIORITY_PATH)

def _ocr_max_workers(requested):
    """Do not let background OCR starve Chrome while votes are being entered."""
    try:
        requested = max(1, int(requested))
    except (TypeError, ValueError):
        requested = 1
    return 1 if _input_priority_active() else requested

def _set_input_priority(active):
    try:
        if active:
            with open(INPUT_PRIORITY_PATH, 'w', encoding='ascii') as marker:
                marker.write(str(os.getpid()))
        elif os.path.isfile(INPUT_PRIORITY_PATH):
            os.remove(INPUT_PRIORITY_PATH)
    except OSError:
        logger.debug('Не удалось обновить маркер приоритета внесения', exc_info=True)

# Маркер мог остаться только после аварийного закрытия прошлого запуска.
if not OCR_WORKER_MODE:
    _set_input_priority(False)

_SOURCE_ARCHIVE_LOCK = threading.Lock()
_MAX_ARCHIVE_PDFS = 5000
_MAX_ARCHIVE_PDF_SIZE = 512 * 1024 * 1024
_MAX_ARCHIVE_TOTAL_SIZE = 5 * 1024 * 1024 * 1024

def _stream_sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()

def _archive_candidate(path):
    if not os.path.isfile(path):
        return False
    if os.path.splitext(path)[1].casefold() == '.zip':
        return True
    # Иногда загрузчик оставляет ZIP с именем, оканчивающимся на .pdf.
    try:
        with open(path, 'rb') as stream:
            return stream.read(4).startswith(b'PK\x03\x04')
    except OSError:
        return False

def _unique_pdf_target(folder, filename, source_hash):
    safe_name = os.path.basename(str(filename or '')).strip()
    safe_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', safe_name).rstrip(' .')
    if not safe_name.casefold().endswith('.pdf'):
        return None, False
    if not safe_name:
        safe_name = 'document.pdf'
    stem, extension = os.path.splitext(safe_name)
    candidate = os.path.join(folder, safe_name)
    index = 2
    while os.path.exists(candidate):
        try:
            if _stream_sha256(candidate) == source_hash:
                return candidate, True
        except OSError:
            pass
        candidate = os.path.join(folder, f'{stem}_{index}{extension}')
        index += 1
    return candidate, False

def _extract_pdf_archive(archive_path, destination):
    """Safely flatten PDF members into one OSS folder; remove ZIP only on success."""
    temporary_paths = []
    extracted = 0
    duplicates = 0
    try:
        with zipfile.ZipFile(archive_path, 'r') as archive:
            members = [item for item in archive.infolist()
                       if not item.is_dir() and item.filename.casefold().endswith('.pdf')]
            if not members:
                logger.warning('Архив оставлен: PDF внутри нет: %s', archive_path)
                return 0, 0, False
            if len(members) > _MAX_ARCHIVE_PDFS:
                raise ValueError(f'слишком много PDF в архиве: {len(members)}')
            total_size = sum(max(0, item.file_size) for item in members)
            if total_size > _MAX_ARCHIVE_TOTAL_SIZE:
                raise ValueError('слишком большой распакованный размер')
            os.makedirs(destination, exist_ok=True)
            for member in members:
                if member.flag_bits & 0x1:
                    raise ValueError('архив защищён паролем')
                if member.file_size > _MAX_ARCHIVE_PDF_SIZE:
                    raise ValueError(f'PDF слишком большой: {member.filename}')
                digest = hashlib.sha256()
                temp_path = os.path.join(
                    destination,
                    f'.ocr_unpack_{os.getpid()}_{threading.get_ident()}_{extracted + duplicates}.tmp')
                temporary_paths.append(temp_path)
                with archive.open(member, 'r') as source, open(temp_path, 'wb') as target:
                    signature = source.read(5)
                    if not signature.startswith(b'%PDF-'):
                        raise ValueError(f'файл не является PDF: {member.filename}')
                    target.write(signature)
                    digest.update(signature)
                    copied = len(signature)
                    while True:
                        chunk = source.read(1024 * 1024)
                        if not chunk:
                            break
                        copied += len(chunk)
                        if copied > _MAX_ARCHIVE_PDF_SIZE:
                            raise ValueError(f'PDF превысил лимит: {member.filename}')
                        target.write(chunk)
                        digest.update(chunk)
                final_path, already_exists = _unique_pdf_target(
                    destination, member.filename, digest.hexdigest())
                if final_path is None:
                    raise ValueError(f'некорректное имя PDF: {member.filename}')
                if already_exists:
                    os.remove(temp_path)
                    temporary_paths.remove(temp_path)
                    duplicates += 1
                else:
                    os.replace(temp_path, final_path)
                    temporary_paths.remove(temp_path)
                    extracted += 1
        os.remove(archive_path)
        logger.info('Автораспаковка: %s — PDF: %s, дублей: %s; ZIP удалён',
                    archive_path, extracted, duplicates)
        return extracted, duplicates, True
    except (OSError, zipfile.BadZipFile, RuntimeError, ValueError):
        logger.exception('Архив не удалён: ошибка распаковки %s', archive_path)
        return extracted, duplicates, False
    finally:
        for temp_path in temporary_paths:
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except OSError:
                logger.debug('Не удалось убрать временный файл %s', temp_path, exc_info=True)

def import_source_archives():
    """Import ZIP packages already copied to source/<OSS>."""
    if not os.path.isdir(SOURCE_FOLDER_PATH):
        return 0
    imported = 0
    with _SOURCE_ARCHIVE_LOCK:
        try:
            oss_folders = [entry.path for entry in os.scandir(SOURCE_FOLDER_PATH)
                           if entry.is_dir() and re.fullmatch(r'\d+', entry.name)]
        except OSError:
            logger.exception('Не удалось просмотреть source для архивов')
            return 0
        for folder in oss_folders:
            try:
                candidates = [entry.path for entry in os.scandir(folder)
                              if entry.is_file() and _archive_candidate(entry.path)]
            except OSError:
                logger.exception('Не удалось просмотреть папку ОСС: %s', folder)
                continue
            for archive_path in candidates:
                extracted, duplicates, completed = _extract_pdf_archive(archive_path, folder)
                if completed:
                    imported += extracted + duplicates
    return imported

def create_folders():
    for folder in ["pdf", "source", "ready", "duplicates", "problems", "processed", "logs", "backup_training"]:
        path = os.path.join(SCRIPT_DIR, folder)
        if not os.path.exists(path): os.makedirs(path, exist_ok=True)
    import_source_archives()
    try:
        for item in os.listdir(SOURCE_FOLDER_PATH):
            item_path = os.path.join(SOURCE_FOLDER_PATH, item)
            if (os.path.isdir(item_path) and re.fullmatch(r'\d+', item)
                    and not os.listdir(item_path)):
                os.rmdir(item_path)
    except OSError:
        logger.debug('Не удалось убрать пустые папки source при запуске', exc_info=True)
if not OCR_WORKER_MODE:
    create_folders()

def atomic_json_save(path, data):
    tmp = f"{path}.tmp"
    try:
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass
        os.replace(tmp, path)
        return True
    except Exception:
        logger.exception("Не удалось сохранить JSON: %s", path)
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass
        return False

def atomic_json_save_compact(path, data):
    tmp = f"{path}.tmp"
    try:
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
            f.flush()
        os.replace(tmp, path)
        return True
    except Exception:
        logger.exception("Не удалось сохранить компактный JSON: %s", path)
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass
        return False

def safe_json_load(path, default):
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                value = json.load(f)
                return value
    except Exception:
        logger.exception("Не удалось прочитать JSON: %s", path)
    return default

def sanitize_filename_component(value, fallback="Без имени"):
    value = re.sub(r'[\\/*?:"<>|]+', ' ', str(value or ''))
    value = re.sub(r'\s+', ' ', value).strip(' .')
    return value[:150] or fallback

class DailyStats:
    def __init__(self):
        self._lock = threading.RLock()
        self.stats_file = DAILY_STATS_PATH
        self.data = self.load()
        self.today = datetime.now().strftime('%Y-%m-%d')
        self.data.setdefault('days', {})
        if self.data.get('date') != self.today:
            self.data = {'date': self.today, 'ocr_daily': 0, 'input_daily': 0,
                         'days': self.data.get('days', {})}
        self.data['days'].setdefault(self.today, {
            'ocr': int(self.data.get('ocr_daily', 0) or 0),
            'input': int(self.data.get('input_daily', 0) or 0)})
        if not OCR_WORKER_MODE:
            self.save()
    def load(self):
        return safe_json_load(self.stats_file, {'date': datetime.now().strftime('%Y-%m-%d'), 'ocr_daily': 0, 'input_daily': 0, 'days': {}})
    def save(self):
        atomic_json_save(self.stats_file, self.data)
    def add_ocr(self, count=1):
        with self._lock:
            self._rollover_day()
            self.data['ocr_daily'] = self.data.get('ocr_daily', 0) + count
            self.data.setdefault('days', {}).setdefault(self.today, {'ocr': 0, 'input': 0})['ocr'] += count
            self.save()
    def add_input(self, count=1):
        with self._lock:
            self._rollover_day()
            self.data['input_daily'] = self.data.get('input_daily', 0) + count
            self.data.setdefault('days', {}).setdefault(self.today, {'ocr': 0, 'input': 0})['input'] += count
            self.save()
    def _rollover_day(self):
        today = datetime.now().strftime('%Y-%m-%d')
        if self.today != today:
            self.today = today
            day = self.data.setdefault('days', {}).setdefault(today, {'ocr': 0, 'input': 0})
            self.data.update(date=today, ocr_daily=day['ocr'], input_daily=day['input'])
            self.save()
    def get_ocr(self):
        with self._lock:
            self._rollover_day()
            return self.data.get('ocr_daily', 0)
    def get_input(self):
        with self._lock:
            self._rollover_day()
            return self.data.get('input_daily', 0)
    def history_text(self, limit=7):
        days = self.data.get('days', {})
        rows = []
        for day in sorted(days.keys(), reverse=True)[:limit]:
            item = days[day]
            rows.append(f"{day}: OCR {int(item.get('ocr', 0))}, ввод {int(item.get('input', 0))}")
        return '  •  '.join(rows) or 'Нет данных'
    def reset(self):
        self.today = datetime.now().strftime('%Y-%m-%d')
        self.data = {'date': datetime.now().strftime('%Y-%m-%d'), 'ocr_daily': 0, 'input_daily': 0,
                     'days': {datetime.now().strftime('%Y-%m-%d'): {'ocr': 0, 'input': 0}}}
        self.save()
daily_stats = DailyStats()

class Theme:
    DARK = {"bg": "#0d1119", "fg": "#eef2ff", "accent": "#7c6df2", "success": "#27c7a5", "warning": "#f6b94a", "error": "#f0647e", "btn": "#202735", "entry": "#151b26", "bg_secondary": "#121823", "card_bg": "#171e2a", "border": "#2b3444", "hover": "#2b3446", "shadow": "#080b11", "progress_bg": "#7c6df2", "progress_fg": "#7c6df2"}
    LIGHT = {"bg": "#f3f5fa", "fg": "#202536", "accent": "#6657dc", "success": "#119b7e", "warning": "#c77b12", "error": "#d74762", "btn": "#edf0f6", "entry": "#ffffff", "bg_secondary": "#fafbfe", "card_bg": "#ffffff", "border": "#dfe3ec", "hover": "#e4e8f2", "shadow": "#cbd1dc", "progress_bg": "#6657dc", "progress_fg": "#6657dc"}
    current_theme = "dark"
    colors = DARK
    @classmethod
    def toggle(cls):
        cls.colors = cls.LIGHT if cls.current_theme == "dark" else cls.DARK
        cls.current_theme = "light" if cls.current_theme == "dark" else "dark"
        return cls.current_theme
    @classmethod
    def set(cls, name):
        cls.current_theme = "light" if str(name).casefold() == "light" else "dark"
        cls.colors = cls.LIGHT if cls.current_theme == "light" else cls.DARK
        return cls.current_theme

class Statistics:
    def __init__(self):
        self.data = {'ocr': {'total':0,'created':0,'skipped':0,'errors':0,'time':0,'sessions':[],'total_votes':0,'avg_time_per_vote':0,
                             'oss_batches':[]},
                     'input':{'total':0,'processed':0,'errors':0,'time':0,'sessions':[],'total_votes':0,'avg_time_per_vote':0}}
        self.load()
    def load(self):
        if os.path.exists(STATS_FILE_PATH):
            try:
                with open(STATS_FILE_PATH, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                    for key in self.data:
                        if key in saved:
                            for sub in self.data[key]:
                                if sub in saved[key]:
                                    self.data[key][sub] = saved[key][sub]
            except Exception:
                logger.debug("Не критичная ошибка очистки", exc_info=True)
    def save(self):
        try:
            with open(STATS_FILE_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception: pass
    def update_ocr(self, created, skipped, elapsed, total_votes=0):
        self.data['ocr']['total'] += created + skipped
        self.data['ocr']['created'] += created
        self.data['ocr']['skipped'] += skipped
        self.data['ocr']['time'] += elapsed
        self.data['ocr']['total_votes'] += total_votes
        avg_time = elapsed / total_votes if total_votes > 0 else 0
        self.data['ocr']['avg_time_per_vote'] = avg_time
        self.data['ocr']['sessions'].append({'created': created, 'skipped': skipped, 'time': elapsed,
                                              'timestamp': datetime.now().isoformat(), 'total_votes': total_votes, 'avg_time_per_vote': avg_time})
        self.save()
        daily_stats.add_ocr(created)
    def update_input(self, processed, errors, elapsed, total_votes=0):
        self.data['input']['total'] += processed + errors
        self.data['input']['processed'] += processed
        self.data['input']['errors'] += errors
        self.data['input']['time'] += elapsed
        self.data['input']['total_votes'] += total_votes
        avg_time = elapsed / total_votes if total_votes > 0 else 0
        self.data['input']['avg_time_per_vote'] = avg_time
        self.data['input']['sessions'].append({'processed': processed, 'errors': errors, 'time': elapsed,
                                                'timestamp': datetime.now().isoformat(), 'total_votes': total_votes, 'avg_time_per_vote': avg_time})
        self.save()
    def get_summary(self):
        ocr = self.data['ocr']; inp = self.data['input']
        return {'ocr_total': ocr['total'], 'ocr_created': ocr['created'], 'ocr_skipped': ocr['skipped'],
                'ocr_time': ocr['time'], 'ocr_sessions': len(ocr['sessions']), 'ocr_total_votes': ocr.get('total_votes',0),
                'ocr_avg_time_per_vote': ocr.get('avg_time_per_vote',0),
                'input_total': inp['total'], 'input_processed': inp['processed'], 'input_errors': inp['errors'],
                'input_time': inp['time'], 'input_sessions': len(inp['sessions']), 'input_total_votes': inp.get('total_votes',0),
                'input_avg_time_per_vote': inp.get('avg_time_per_vote',0)}
    def record_oss_batch(self, counts):
        rows = []
        for oss, amount in sorted((counts or {}).items(), key=lambda item: int(str(item[0]))):
            try:
                amount = int(amount)
            except (TypeError, ValueError):
                continue
            if amount > 0:
                rows.append({'oss': str(oss), 'files': amount})
        if not rows:
            return
        batches = self.data['ocr'].setdefault('oss_batches', [])
        batches.append({
            'timestamp': datetime.now().isoformat(),
            'oss_count': len(rows),
            'total_files': sum(row['files'] for row in rows),
            'rows': rows,
        })
        self.data['ocr']['oss_batches'] = batches[-200:]
        self.save()
    def latest_oss_batch(self):
        batches = self.data.get('ocr', {}).get('oss_batches', [])
        return batches[-1] if isinstance(batches, list) and batches else None
    def export_excel(self, filepath):
        if not EXCEL_AVAILABLE: raise Exception("openpyxl не установлен")
        wb = openpyxl.Workbook()
        ws0 = wb.active; ws0.title = "Сводка"
        summary = self.get_summary()
        ws0.merge_cells('A1:B1')
        ws0['A1'] = "СТАТИСТИКА «ЕДИНЫЙ РОБОТ»"
        ws0.append([])
        ws0.append(["Показатель", "Значение"])
        summary_rows = [
            ("Дата формирования", datetime.now().strftime('%d.%m.%Y %H:%M')),
            ("OCR сегодня", daily_stats.get_ocr()),
            ("Ввод сегодня", daily_stats.get_input()),
            ("OCR — всего файлов", summary['ocr_total']),
            ("OCR — создано", summary['ocr_created']),
            ("OCR — пропущено", summary['ocr_skipped']),
            ("OCR — время, сек.", round(summary['ocr_time'], 1)),
            ("OCR — сессий", summary['ocr_sessions']),
            ("Ввод — всего", summary['input_total']),
            ("Ввод — успешно", summary['input_processed']),
            ("Ввод — ошибок", summary['input_errors']),
            ("Ввод — время, сек.", round(summary['input_time'], 1)),
            ("Ввод — сессий", summary['input_sessions']),
        ]
        for row in summary_rows:
            ws0.append(row)

        ws1 = wb.create_sheet("OCR")
        ws1.append(["Сессия","Создано","Пропущено","Голосов","Среднее время/голос","Время (сек)","Дата"])
        for i,s in enumerate(self.data['ocr']['sessions'],1):
            ws1.append([i, s['created'], s['skipped'], s.get('total_votes',0), round(s.get('avg_time_per_vote',0),1), round(s['time'],1), s['timestamp']])
        ws1.append(["Итого", self.data['ocr']['created'], self.data['ocr']['skipped'], self.data['ocr']['total_votes'],
                    round(self.data['ocr']['avg_time_per_vote'],1), round(self.data['ocr']['time'],1), ""])
        ws2 = wb.create_sheet("Ввод")
        ws2.append(["Сессия","Обработано","Ошибок","Голосов","Среднее время/голос","Время (сек)","Дата"])
        for i,s in enumerate(self.data['input']['sessions'],1):
            ws2.append([i, s['processed'], s['errors'], s.get('total_votes',0), round(s.get('avg_time_per_vote',0),1), round(s['time'],1), s['timestamp']])
        ws2.append(["Итого", self.data['input']['processed'], self.data['input']['errors'], self.data['input']['total_votes'],
                    round(self.data['input']['avg_time_per_vote'],1), round(self.data['input']['time'],1), ""])
        ws3 = wb.create_sheet("ОСС")
        ws3.append(["Партия", "Дата", "Количество ОСС", "ОСС", "Файлов"])
        for batch_index, batch in enumerate(self.data['ocr'].get('oss_batches', []), 1):
            if not isinstance(batch, dict):
                continue
            rows = batch.get('rows', [])
            for row in rows if isinstance(rows, list) else []:
                if isinstance(row, dict):
                    ws3.append([batch_index, batch.get('timestamp', ''),
                                batch.get('oss_count', 0), row.get('oss', ''), row.get('files', 0)])
        if ws3.max_row == 1:
            ws3.append(["", "Нет завершённых партий", "", "", ""])
        accent_fill = PatternFill('solid', fgColor='4F8CFF')
        title_fill = PatternFill('solid', fgColor='101A2B')
        total_fill = PatternFill('solid', fgColor='DCE9FF')
        thin = Side(style='thin', color='CBD5E1')
        border = Border(left=thin, right=thin, top=thin, bottom=thin)

        ws0['A1'].font = Font(bold=True, color='FFFFFF', size=14)
        ws0['A1'].fill = title_fill
        ws0['A1'].alignment = Alignment(horizontal='center')
        for cell in ws0[3]:
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = accent_fill
            cell.alignment = Alignment(horizontal='center')
        for row in ws0.iter_rows(min_row=3, max_row=ws0.max_row, min_col=1, max_col=2):
            for cell in row:
                cell.border = border
        ws0.column_dimensions['A'].width = 36
        ws0.column_dimensions['B'].width = 24
        ws0.freeze_panes = 'A4'

        for ws in [ws1, ws2]:
            for row in ws.iter_rows(min_row=1, max_row=1):
                for cell in row:
                    cell.font = Font(bold=True, color='FFFFFF')
                    cell.fill = accent_fill
                    cell.alignment = Alignment(horizontal='center')
            for row in ws.iter_rows(min_row=1, max_row=ws.max_row):
                for cell in row:
                    cell.border = border
            for cell in ws[ws.max_row]:
                cell.font = Font(bold=True)
                cell.fill = total_fill
            ws.freeze_panes = 'A2'
            ws.auto_filter.ref = ws.dimensions
            ws.column_dimensions['A'].width = 12; ws.column_dimensions['B'].width = 14; ws.column_dimensions['C'].width = 14
            ws.column_dimensions['D'].width = 14; ws.column_dimensions['E'].width = 20; ws.column_dimensions['F'].width = 16; ws.column_dimensions['G'].width = 22
        for row in ws3.iter_rows(min_row=1, max_row=1):
            for cell in row:
                cell.font = Font(bold=True, color='FFFFFF')
                cell.fill = accent_fill
                cell.alignment = Alignment(horizontal='center')
        for row in ws3.iter_rows(min_row=1, max_row=ws3.max_row):
            for cell in row:
                cell.border = border
        ws3.freeze_panes = 'A2'
        ws3.auto_filter.ref = ws3.dimensions
        ws3.column_dimensions['A'].width = 12
        ws3.column_dimensions['B'].width = 24
        ws3.column_dimensions['C'].width = 18
        ws3.column_dimensions['D'].width = 16
        ws3.column_dimensions['E'].width = 12
        wb.save(filepath)
stats = Statistics()

def get_oss_folders():
    if not os.path.exists(SOURCE_FOLDER_PATH): return []
    import_source_archives()
    folders = []
    for item in os.listdir(SOURCE_FOLDER_PATH):
        item_path = os.path.join(SOURCE_FOLDER_PATH, item)
        if os.path.isdir(item_path) and re.match(r'^\d+$', item):
            if any(f.lower().endswith('.pdf') for f in os.listdir(item_path)):
                folders.append(item)
    return sorted(folders, key=int)
def get_pdf_files(oss):
    oss_path = os.path.join(SOURCE_FOLDER_PATH, oss)
    if not os.path.exists(oss_path): return []
    return [f for f in os.listdir(oss_path) if f.lower().endswith('.pdf')]
def convert_pdf_to_image(pdf_path):
    temp_dir = None
    try:
        working_path = os.path.abspath(pdf_path)
        if not working_path.isascii():
            public_root = os.environ.get('PUBLIC', '')
            temp_root = os.path.join(public_root, 'RobotOCRTemp') if public_root else tempfile.gettempdir()
            if not os.path.abspath(temp_root).isascii():
                temp_root = os.path.join(os.environ.get('SystemDrive', 'C:'), 'RobotOCRTemp')
            os.makedirs(temp_root, exist_ok=True)
            temp_dir = tempfile.mkdtemp(prefix='pdf_', dir=temp_root)
            working_path = os.path.join(temp_dir, 'document.pdf')
            shutil.copy2(pdf_path, working_path)
        images = convert_from_path(working_path, dpi=FAST_RENDER_DPI, first_page=1, last_page=1,
                                   poppler_path=POPPLER_BIN_PATH, thread_count=2)
        return images[0] if images else None
    except Exception as e:
        logger.error("Ошибка: %s", e)
        logger.exception("Не удалось открыть PDF: %s", pdf_path)
        return None
    finally:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)
def play_sound():
    try:
        winsound.Beep(880, 200); time.sleep(0.1); winsound.Beep(1100, 200)
    except Exception: pass
def extract_all_fios_from_filename(filename):
    base_name = os.path.splitext(filename)[0]
    premise_number = None
    match = re.search(r'\(([^)]+)\)$', base_name)
    if match:
        premise_number = match.group(1)
        fio_part = base_name[:match.start()].strip()
    else:
        fio_part = base_name.strip()
    fio_part = re.sub(r'\s*\[\d+\]\s*$', '', fio_part).strip()
    fio_list = []
    for sep in ['_', ' - ', '  ']:
        if sep in fio_part:
            fio_list = [p.strip() for p in fio_part.split(sep) if p.strip()]
            break
    if not fio_list:
        fio_list = [fio_part.strip()]
    result = []
    for fio in fio_list:
        parts = fio.split()
        if len(parts) >= 3:
            result.append({'last_name': parts[0], 'first_name': parts[1], 'middle_name': ' '.join(parts[2:])})
        elif len(parts) >= 2:
            result.append({'last_name': parts[0], 'first_name': parts[1], 'middle_name': ''})
    return result, premise_number
def fix_filename(filename):
    base_name = os.path.splitext(filename)[0]; ext = os.path.splitext(filename)[1]
    corrections = {
        'Иринана':'Ирина','Татьянаа':'Татьяна','Юрьевнаьевнана':'Юрьевна','Юрьевнаьевна':'Юрьевна',
        'Юрьевнана':'Юрьевна','Юрьевнна':'Юрьевна','Александровнач':'Александровна','Александровн':'Александровна',
        'Владимировнаа':'Владимировна','Владимировн':'Владимировна','Николаевнаа':'Николаевна','Николаевн':'Николаевна',
        'Ивановнаа':'Ивановна','Ивановн':'Ивановна','Петровнаа':'Петровна','Петровн':'Петровна',
        'Михайловнаа':'Михайловна','Михайловнааа':'Михайловна','Михайловн':'Михайловна','Сергеевнаа':'Сергеевна',
        'Сергеевн':'Сергеевна','Алексеевнаа':'Алексеевна','Алексеевн':'Алексеевна','Дмитриевнаа':'Дмитриевна',
        'Дмитриевн':'Дмитриевна','Аннатольевна':'Анатольевна','Аннатольевн':'Анатольевна','Александровнач':'Александрович',
        'Александровичч':'Александрович','Владимировнач':'Владимирович','Владимировичч':'Владимирович',
        'Николаевнач':'Николаевич','Николаевичч':'Николаевич','Ивановнач':'Иванович','Ивановичч':'Иванович',
        'Петровнач':'Петрович','Петровичч':'Петрович','Михайловнач':'Михайлович','Михайловичч':'Михайлович',
        'Сергеевнач':'Сергеевич','Сергеевичч':'Сергеевич','Алексеевнач':'Алексеевич','Алексеевичч':'Алексеевич',
        'Дмитриевнач':'Дмитриевич','Дмитриевичч':'Дмитриевич','Аннатольевич':'Анатольевич',
        'Юрьевнач':'Юрьевич','Юрьевнаич':'Юрьевич','Юрьевнаий':'Юрьевич','Юрьевнаи':'Юрьевич',
        'Юрьевн':'Юрьевич','Юрьеви':'Юрьевич','Игоревичч':'Игоревич','Марияяия':'Мария',
        'Марияяина':'Марина','Марияягарита':'Маргарита','Марияясель':'Марсель','Марияяна':'Марианна',
        'Андреевнаа':'Андреевна','Андреевнааа':'Андреевна','Круглен':'Кругленкова','Тетерлевна':'Тетерлева',
        'Фёдорович':'Федорович','Татарстан Респ':'','Республики Казахстан Рымжанов Данияр':'Рымжанов Данияр',
        'Министерство Внутренних Дел':'','Народной Республики Бангладеш Рой':'Рой',
        'Республики Бангладеш Рой Совнали':'Рой Совнали','Вы Проект':'','Казахстан Рымжанов Данияр':'Рымжанов Данияр',
        'Элиста Республики Калмыкия':'','Старый Оскол Белгородской':'','Донецкая Народная Респ':'',
        'Белебей Республики Башкортостан':'','Махачкала Республики Дагестан':'','Нижнекамск Республика Татарстан':'',
        'Караганда Республика Казахстан':'','Октябрьский Республики Башкортостан':'','Ташкент Республика Узбекистан':'',
        'Коломна Московской':'','Чаренцаван Армянская':'','Азнакаево Азнакаевский':'','ов рз помещений':'','Кия Ошской':'',
        'Республике Марияяий Эл':'','Натальяя':'Наталья','Антонину':'Антонина','Владиславу':'Владислава',
        'Юрьевичу':'Юрьевна','Федоровну':'Федоровна','Медведеваа':'Медведева','Медведевва':'Медведева',
        'Медведеву':'Медведева','Медведевой':'Медведева','Медведевна':'Медведева','Татьянаа':'Татьяна',
        'Татьтяна':'Татьяна','Татьяну':'Татьяна','Сергеевнаа':'Сергеевна','Сергеевну':'Сергеевна',
        'Сергеевной':'Сергеевна','Сергеевнна':'Сергеевна'
    }
    fixed_name = base_name
    for wrong, correct in corrections.items():
        if wrong in fixed_name:
            fixed_name = fixed_name.replace(wrong, correct)
    fixed_name = ' '.join(fixed_name.split())
    fixed_name = re.sub(r'([а-яё]{2,})ааа+', r'\1а', fixed_name)
    fixed_name = re.sub(r'([а-яё]{2,})ччч+', r'\1ч', fixed_name)
    fixed_name = re.sub(r'([а-яё]{2,})яяя+', r'\1я', fixed_name)
    return fixed_name + ext
def fix_filenames_in_ready():
    fixed_count = 0; errors = []
    if not os.path.exists(READY_FOLDER_PATH): return 0, ["Папка ready не найдена"]
    for root, dirs, files in os.walk(READY_FOLDER_PATH):
        for file in files:
            if file.lower().endswith('.pdf'):
                old_path = os.path.join(root, file)
                new_name = fix_filename(file)
                if new_name != file:
                    new_path = os.path.join(root, new_name)
                    if os.path.exists(new_path):
                        errors.append(f"Файл уже существует: {new_name}")
                        continue
                    try:
                        shutil.move(old_path, new_path)
                        fixed_count += 1
                        logger.info("Исправлено: %s -> %s", file, new_name)
                    except Exception as e:
                        errors.append(f"Ошибка при переименовании {file}: {e}")
    return fixed_count, errors

def make_button(parent, text, command, **kwargs):
    default = {'font': ("Segoe UI", 10, "bold"), 'relief': tk.FLAT, 'padx': 12, 'pady': 6, 'bd': 0}
    default.update(kwargs)
    return tk.Button(parent, text=text, command=command, **default)
def make_label(parent, text, **kwargs):
    default = {'bg': Theme.colors['bg'], 'fg': Theme.colors['fg'], 'font': ("Segoe UI", 10)}
    default.update(kwargs)
    return tk.Label(parent, text=text, **default)
def make_entry(parent, **kwargs):
    default = {'bg': Theme.colors['entry'], 'fg': Theme.colors['fg'], 'insertbackground': Theme.colors['fg'], 'font': ("Segoe UI", 11)}
    default.update(kwargs)
    return tk.Entry(parent, **default)

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget; self.text = text; self.tip_window = None
        widget.bind('<Enter>', self.show); widget.bind('<Leave>', self.hide)
    def show(self, event):
        if self.tip_window or not self.text: return
        x = self.widget.winfo_rootx() + 8
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT, background="#ffffe0", relief=tk.SOLID, borderwidth=1, font=("Segoe UI", 9))
        label.pack()
    def hide(self, event):
        if self.tip_window: self.tip_window.destroy(); self.tip_window = None

# =============================================================================
# ОСНОВНОЙ КЛАСС OCRRobot
# =============================================================================
class OCRRobot:
    def __init__(self, parent_frame):
        self._view_preferences_file = os.path.join(SCRIPT_DIR, 'ui_preferences_v43.json')
        self._loaded_view_preferences = safe_json_load(self._view_preferences_file, {})
        if not isinstance(self._loaded_view_preferences, dict): self._loaded_view_preferences = {}
        self.parent = parent_frame
        self.theme = Theme()
        self.image = None
        self.tk_image = None
        self.zoom = 1.0
        self.original_width = self.original_height = 1
        self.mode = "auto"
        self.fast_mode = True
        self.fio_roi = self.kv_roi = None
        self.drawing = False
        self.start_x = self.start_y = 0
        self.current_rect = None
        self.select_mode = None
        self.saved_fio_roi = self.saved_kv_roi = None
        self.roi_saved = False
        self.full_text = ""
        self.recognized_fios = []
        self.recognized_kv = None
        self.last_raw_fio = self.last_raw_kv = None
        self.pdf_files = []
        self.current_index = 0
        self.current_oss = None
        self.total_created = self.total_skipped = self.total_votes = 0
        self.is_running = self.is_paused = self.stop_flag = False
        self.ocr_cache = {}
        self._anchor_cache = {}
        self._layout_match_cache = {}
        # FIX_v43.17.54: кеш numpy-дескрипторов шаблонов. Layout-шаблоны хранят
        # ORB-точки как списки, и каждая проверка шаблона конвертировала их
        # заново. Предвычисляем один раз и переиспользуем.
        self._template_np_cache = {}
        self.detected_fio_roi = None
        self.detected_kv_roi = None
        self.cache_enabled = True
        self.ocr_times = []
        self.last_ocr_time = 0
        self.corrections = {}
        self.load_corrections()
        self.load_roi()
        self.templates = self.load_templates()
        self.easyocr_reader = None
        self.easyocr_available = False
        self.fio_confidence = 0.0
        self.kv_confidence = 0.0
        self.ocr_engine_name = "—"
        self.ocr_variant_name = "—"
        self.fio_engine_name = "—"
        self.kv_engine_name = "—"
        self.last_action = None
        self.review_queue = safe_json_load(os.path.join(SCRIPT_DIR, 'ocr_review_queue.json'), [])
        if not isinstance(self.review_queue, list):
            self.review_queue = []
        self.review_queue = [r for r in self.review_queue if isinstance(r, dict) and 'oss' in r and 'filename' in r]
        self.review_mode = False
        self.batch_busy = False
        self.ocr_error = None
        self.roi_batch_mode = False
        self.learning_template_pending = False
        self.active_layout_template = None
        self.active_layout_score = 0.0
        self.ui_queue = queue.Queue()
        self._main_thread_id = threading.get_ident()
        self.fio_dictionary = set()
        self._load_fio_database()
        self.build_ui()
        self._bind_hotkeys()
        self._pump_ui_queue()
        self.parent.after(150, self._startup_diagnostics_log)
        self.parent.after(100, self._startup_session)

    def _pump_ui_queue(self):
        try:
            while True:
                func, args, kwargs, done, holder = self.ui_queue.get_nowait()
                try:
                    holder['value'] = func(*args, **kwargs)
                except Exception as exc:
                    holder['error'] = exc
                    logger.exception("Ошибка UI-команды")
                finally:
                    if done:
                        done.set()
        except queue.Empty:
            pass
        if self.parent.winfo_exists():
            self.parent.after(30, self._pump_ui_queue)

    def _ui_call(self, func, *args, wait=False, **kwargs):
        if threading.get_ident() == self._main_thread_id:
            return func(*args, **kwargs)
        done = threading.Event() if wait else None
        holder = {}
        self.ui_queue.put((func, args, kwargs, done, holder))
        if done:
            done.wait()
            if 'error' in holder:
                raise holder['error']
            return holder.get('value')
        return None

    def _startup_diagnostics_log(self):
        checks = self.run_diagnostics(show_dialog=False)
        bad = [name for name, ok, _ in checks if not ok]
        if bad:
            logger.warning("Диагностика: проблемы: %s", ', '.join(bad))
        else:
            logger.info("Диагностика: все ключевые компоненты доступны")

    def _bind_hotkeys(self):
        self.parent.bind('<Control-Return>', lambda e: self.confirm())
        self.parent.bind('<F5>', lambda e: self.re_recognize())
        self.parent.bind('<Control-plus>', lambda e: self.zoom_in())
        self.parent.bind('<Control-minus>', lambda e: self.zoom_out())
        self.parent.bind('<Escape>', lambda e: self.stop_process() if self.is_running else None)

    def _load_fio_database(self):
        if not os.path.exists(FIO_DATABASE_PATH):
            return
        try:
            with open(FIO_DATABASE_PATH, 'r', encoding='utf-8') as f:
                for line in f:
                    value = line.strip().lower()
                    if value and not value.startswith('#'):
                        self.fio_dictionary.add(value)
            logger.info("База ФИО загружена: %s записей", len(self.fio_dictionary))
        except Exception:
            logger.exception("Не удалось загрузить базу ФИО")

    def load_corrections(self):
        raw = safe_json_load(LEARNING_DATA_PATH, {})
        if isinstance(raw, dict) and ('fio' in raw or 'room' in raw):
            self.fio_corrections = dict(raw.get('fio', {}))
            self.room_corrections = {}
        else:
            self.fio_corrections = dict(raw) if isinstance(raw, dict) else {}
            self.room_corrections = {}
        self.corrections = self.fio_corrections
        defaults = {
            'Иринана':'Ирина','Татьянаа':'Татьяна','Юрьевнаьевнана':'Юрьевна','Юрьевнаьевна':'Юрьевна',
            'Юрьевнана':'Юрьевна','Юрьевнна':'Юрьевна','Александровнач':'Александровна','Александровн':'Александровна',
            'Владимировнаа':'Владимировна','Владимировн':'Владимировна','Николаевнаа':'Николаевна','Николаевн':'Николаевна',
            'Ивановнаа':'Ивановна','Ивановн':'Ивановна','Петровнаа':'Петровна','Петровн':'Петровна',
            'Михайловнаа':'Михайловна','Михайловнааа':'Михайловна','Михайловн':'Михайловна','Сергеевнаа':'Сергеевна',
            'Сергеевн':'Сергеевна','Алексеевнаа':'Алексеевна','Алексеевн':'Алексеевна','Дмитриевнаа':'Дмитриевна',
            'Дмитриевн':'Дмитриевна','Аннатольевна':'Анатольевна','Аннатольевн':'Анатольевна','Александровнач':'Александрович',
            'Александровичч':'Александрович','Владимировнач':'Владимирович','Владимировичч':'Владимирович',
            'Николаевнач':'Николаевич','Николаевичч':'Николаевич','Ивановнач':'Иванович','Ивановичч':'Иванович',
            'Петровнач':'Петрович','Петровичч':'Петрович','Михайловнач':'Михайлович','Михайловичч':'Михайлович',
            'Сергеевнач':'Сергеевич','Сергеевичч':'Сергеевич','Алексеевнач':'Алексеевич','Алексеевичч':'Алексеевич',
            'Дмитриевнач':'Дмитриевич','Дмитриевичч':'Дмитриевич','Аннатольевич':'Анатольевич',
            'Юрьевнач':'Юрьевич','Юрьевнаич':'Юрьевич','Юрьевнаий':'Юрьевич','Юрьевнаи':'Юрьевич',
            'Юрьевн':'Юрьевич','Юрьеви':'Юрьевич','Игоревичч':'Игоревич','Марияяия':'Мария',
            'Марияяина':'Марина','Марияягарита':'Маргарита','Марияясель':'Марсель','Марияяна':'Марианна',
            'Андреевнаа':'Андреевна','Андреевнааа':'Андреевна','Евгеньевнаа':'Евгеньевна','Валерьевнаа':'Валерьевна',
            'Круглен':'Кругленкова','Тетерлевна':'Тетерлева','Фёдорович':'Федорович','Фей Фей':'',
            'Тигиева Дана':'Тигиева Даная','Лабызноваа':'Лабызнова','Панкратоваа':'Панкратова','Бакановаа':'Баканова',
            'Натальяя':'Наталья','Антонину':'Антонина','Владиславу':'Владислава','Юрьевичу':'Юрьевна',
            'Федоровну':'Федоровна','Медведеваа':'Медведева','Медведевва':'Медведева','Медведеву':'Медведева',
            'Медведевой':'Медведева','Медведевна':'Медведева','Татьянаа':'Татьяна','Татьтяна':'Татьяна',
            'Татьяну':'Татьяна','Сергеевнаа':'Сергеевна','Сергеевну':'Сергеевна','Сергеевной':'Сергеевна',
            'Сергеевнна':'Сергеевна'
        }
        for k, v in defaults.items():
            self.fio_corrections.setdefault(k, v)
        logger.info("Загружено исправлений ФИО: %s, помещений: %s", len(self.fio_corrections), len(self.room_corrections))

    def save_corrections(self):
        atomic_json_save(LEARNING_DATA_PATH, {
            'version': 2,
            'fio': self.fio_corrections,
            'room': self.room_corrections,
            'updated_at': datetime.now().isoformat()
        })
    @staticmethod
    def _registration_features(image, rois=()):
        if not (OPENCV_AVAILABLE and NUMPY_AVAILABLE):
            return None
        width = 1100
        height = round(image.height * width / image.width)
        gray = np.array(image.convert('L').resize((width, height)))
        mask = np.full(gray.shape, 255, dtype=np.uint8)
        for roi in rois:
            if roi:
                x1, y1, x2, y2 = roi
                x1, x2 = int(x1 / image.width * width), int(x2 / image.width * width)
                y1, y2 = int(y1 / image.height * height), int(y2 / image.height * height)
                mask[max(0,y1-12):min(height,y2+12), max(0,x1-12):min(width,x2+12)] = 0
        points, descriptors = cv2.ORB_create(nfeatures=2500).detectAndCompute(gray, mask)
        if descriptors is None or len(points) < 20:
            return None
        return {'size': [width, height], 'points': [list(p.pt) for p in points],
                'descriptors': descriptors.tolist()}

    @classmethod
    def _layout_structure_signature(cls, image, rois=()):
        if image is None:
            return []
        masked = image.convert('L').copy()
        for roi in rois:
            if not roi or len(roi) != 4:
                continue
            x1, y1, x2, y2 = [int(v) for v in roi]
            x1, x2 = sorted((max(0, x1), min(masked.width, x2)))
            y1, y2 = sorted((max(0, y1), min(masked.height, y2)))
            if x2 > x1 and y2 > y1:
                masked.paste(255, (x1, y1, x2, y2))
        return cls._layout_signature(masked)

    def _make_adaptive_template(self, name):
        return {'kind': 'layout', 'version': 3, 'name': name,
                'signature': self._layout_signature(self.image),
                'structure_signature': self._layout_structure_signature(
                    self.image, (self.fio_roi, self.kv_roi)),
                'aspect': self.image.width / self.image.height,
                'image_size': list(self.image.size),
                'fio_roi': self._normalized_roi(self.fio_roi, *self.image.size),
                'kv_roi': self._normalized_roi(self.kv_roi, *self.image.size),
                'registration': self._registration_features(self.image, (self.fio_roi, self.kv_roi)),
                'created_at': datetime.now().isoformat()}

    def _template_numpy(self, key, template):
        """FIX_v43.17.54: возвращает (descriptors_np, points_np) с кешированием."""
        cached = self._template_np_cache.get(key)
        if cached is not None:
            return cached
        reg = template.get('registration')
        if not reg:
            self._template_np_cache[key] = (None, None)
            return (None, None)
        try:
            desc = np.asarray(reg['descriptors'], dtype=np.uint8)
            pts = np.asarray(reg['points'], dtype=np.float32)
        except Exception:
            logger.debug('Дескрипторы шаблона %s повреждены', key, exc_info=True)
            self._template_np_cache[key] = (None, None)
            return (None, None)
        self._template_np_cache[key] = (desc, pts)
        return (desc, pts)

    def _align_template(self, image, template, features=None, template_key=None):
        ref = template.get('registration')
        if not ref or not (OPENCV_AVAILABLE and NUMPY_AVAILABLE):
            return None
        try:
            current = features or self._registration_features(image)
            if not current:
                return None
            ref_desc_np = ref_pts_np = None
            if template_key is not None:
                ref_desc_np, ref_pts_np = self._template_numpy(template_key, template)
            if ref_desc_np is None:
                ref_desc_np = np.asarray(ref['descriptors'], dtype=np.uint8)
                ref_pts_np = np.asarray(ref['points'], dtype=np.float32)
            cur_desc_np = np.asarray(current['descriptors'], dtype=np.uint8)
            cur_pts_np = np.asarray(current['points'], dtype=np.float32)
            pairs = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(
                ref_desc_np, cur_desc_np, k=2)
            good = [pair[0] for pair in pairs if len(pair) == 2 and pair[0].distance < .70 * pair[1].distance]
            good = list({m.trainIdx: m for m in sorted(good, key=lambda m: -m.distance)}.values())
            if len(good) < 12:
                return None
            src = np.float32([cur_pts_np[m.trainIdx] for m in good])
            dst = np.float32([ref_pts_np[m.queryIdx] for m in good])
            matrix, inliers = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC,
                                                       ransacReprojThreshold=3, maxIters=3000)
            if matrix is None or inliers is None:
                return None
            selected = inliers.ravel().astype(bool)
            count, ratio = int(selected.sum()), float(selected.mean())
            if count < 10 or ratio < .45:
                return None
            spread = np.ptp(dst[selected], axis=0) / np.array(ref['size'])
            scale = float(np.hypot(matrix[0,0], matrix[1,0]))
            angle = float(np.degrees(np.arctan2(matrix[1,0], matrix[0,0])))
            if min(spread) < .18 or not .8 < scale < 1.25 or abs(angle) > 12:
                return None
            if abs(matrix[0,2]) > ref['size'][0]*.2 or abs(matrix[1,2]) > ref['size'][1]*.2:
                return None
            ref_w, ref_h = template['image_size']
            full = matrix.copy()
            full[:,:2] *= current['size'][0] / image.width * ref_w / ref['size'][0]
            full[:,2] *= ref_w / ref['size'][0]
            aligned = cv2.warpAffine(np.array(image.convert('RGB')), full, (ref_w, ref_h),
                                     flags=cv2.INTER_CUBIC, borderValue=(255,255,255))
            return {'image': Image.fromarray(aligned), 'inliers': count, 'ratio': ratio,
                    'score': min(.99, .82 + .12*ratio + .05*min(count/100, 1))}
        except Exception:
            logger.exception('Не удалось совместить бланк; используется обычный OCR')
            return None

    def _adaptive_manual_rois(self):
        templates = [(k, t) for k, t in self._layout_templates() if t.get('version') == 3]
        saved = getattr(self, 'saved_roi_data', {})
        if saved.get('version') == 3:
            templates.insert(0, ('__saved__', saved))
        features = self._registration_features(self.image) if templates else None
        matches = []
        for key, template in templates:
            aligned = self._align_template(self.image, template, features, template_key=key)
            if aligned:
                matches.append((aligned['score'], template, aligned))
        if not matches:
            template = saved if saved.get('fio_roi') and saved.get('kv_roi') else (templates[0][1] if templates else None)
            if not template:
                self.fio_roi = self.kv_roi = None
                return False
            self.fio_roi = self._restore_roi(template['fio_roi'], *self.image.size)
            self.kv_roi = self._restore_roi(template['kv_roi'], *self.image.size)
            self.active_layout_template = template.get('name')
            return bool(self.fio_roi and self.kv_roi)
        _, template, aligned = max(matches, key=lambda item: item[0])
        self.image = aligned['image']
        self.original_width, self.original_height = self.image.size
        self.fio_roi = self._restore_roi(template['fio_roi'], *self.image.size)
        self.kv_roi = self._restore_roi(template['kv_roi'], *self.image.size)
        self.active_layout_template = template.get('name')
        return bool(self.fio_roi and self.kv_roi)

    def _save_review_queue(self):
        if not atomic_json_save(os.path.join(SCRIPT_DIR, 'ocr_review_queue.json'), self.review_queue):
            raise IOError('Не удалось сохранить очередь проверки; пакет остановлен')

    def _enqueue_review(self, reason):
        oss, filename = self.pdf_files[self.current_index]
        route = 'roi' if (self.mode == 'manual' or getattr(self, 'roi_batch_mode', False)) else 'auto'
        fio_roi = self.fio_roi or self.detected_fio_roi
        kv_roi = self.kv_roi or self.detected_kv_roi
        fio_roi_norm = self._normalized_roi(fio_roi, *self.image.size) if self.image is not None and fio_roi else None
        kv_roi_norm = self._normalized_roi(kv_roi, *self.image.size) if self.image is not None and kv_roi else None
        item = {'oss': oss, 'filename': filename, 'reason': reason,
                'fios': list(self.recognized_fios), 'room': self.recognized_kv,
                'fio_confidence': self.fio_confidence, 'room_confidence': self.kv_confidence,
                'recognition_route': route,
                'active_template': self.active_layout_template,
                'review_fio_roi_norm': fio_roi_norm,
                'review_kv_roi_norm': kv_roi_norm,
                'timestamp': datetime.now().isoformat()}
        self.review_queue = [r for r in self.review_queue if (r['oss'], r['filename']) != (oss, filename)]
        self.review_queue.append(item)
        self._save_review_queue()

    def _resolve_review(self):
        oss, filename = self.pdf_files[self.current_index]
        self.review_queue = [r for r in self.review_queue if (r['oss'], r['filename']) != (oss, filename)]
        self._save_review_queue()

    def open_review_queue(self):
        if self.batch_busy:
            return
        pending = [r for r in self.review_queue
                   if os.path.isfile(os.path.join(SOURCE_FOLDER_PATH, r['oss'], r['filename']))]
        if not pending:
            messagebox.showinfo('Проверка', 'Нет доступных исходников в очереди проверки.')
            return
        self.pdf_files = [(r['oss'], r['filename']) for r in pending]
        self.current_index = 0
        self.review_mode = True
        self.stop_flag = False
        self.load_file()
        if self.current_index < len(self.pdf_files):
            current = self.pdf_files[self.current_index]
            item = next((r for r in self.review_queue if (r['oss'], r['filename']) == current), None)
            if item:
                self.log_label.config(text='Проверка: ' + item.get('reason', 'Проверьте поля'))

    @staticmethod
    def _fio_shape_valid(value):
        parts = str(value or '').strip().split()
        if len(parts) == 4 and parts[-1].casefold() in FIO_PARTICLES:
            parts = parts[:3]
        return len(parts) in (2, 3) and all(
            re.fullmatch(r'[А-ЯЁа-яё-]{2,40}', part) for part in parts)

    def _fio_list_valid(self, fios):
        fios=list(fios or [])
        if not (1 <= len(fios) <= 6):
            return False
        normalized=[]
        for fio in fios:
            fio=str(fio or '').strip()
            if not self._fio_shape_valid(fio):
                return False
            if len(fio.split()) == 2:
                route = str(getattr(self, 'fio_engine_name', '') or '')
                two_word_garbage = {
                    'общее', 'собрание', 'решение', 'собственник',
                    'представитель', 'номер', 'помещение', 'квартира',
                    'фамилия', 'отчество', 'голосование', 'документ'
                }
                parts = fio.casefold().replace('ё', 'е').split()
                safe_two_word = bool(
                    getattr(self, 'mode', '') == 'manual' or
                    getattr(self, '_two_word_owner_consensus', False) or
                    any(tag in route for tag in
                        ('TemplateROI', 'TurboROI', 'SmartConsensus')))
                if (not safe_two_word or min(map(len, parts)) < 3 or
                        len(parts[0]) < 4 or
                        any(part in two_word_garbage for part in parts)):
                    return False
            elif self._fio_candidate_score(fio) < 65:
                return False
            key=' '.join(fio.casefold().replace('ё','е').split())
            if key in normalized:
                return False
            normalized.append(key)
        return True

    def _multi_fio_route_is_safe(self):
        if getattr(self,'mode',None) == 'manual':
            return bool(getattr(self,'fio_roi',None) or getattr(self,'detected_fio_roi',None))
        route=str(getattr(self,'fio_engine_name','') or '')
        return any(tag in route for tag in ('TemplateROI','TurboROI','SmartConsensus'))

    def _batch_decision(self):
        if self.ocr_error:
            return False, self.ocr_error
        fios=list(self.recognized_fios or [])
        room=str(self.recognized_kv or '').strip()
        if not fios or not room or room == '0':
            return False, 'Не заполнены обязательные поля'
        if not self._fio_list_valid(fios):
            return False, 'Некорректная структура ФИО: нужна проверка'
        if len(fios) > 1 and not self._multi_fio_route_is_safe():
            return False, 'Несколько ФИО не подтверждены безопасной зоной владельцев'
        if not re.fullmatch(r'(?i)(?:ММ|М/М|КВ|НП)?[ -]?\d{1,5}(?:[/-]\d{1,4})?[А-ЯЁA-Z]?', room):
            return False, 'Нестандартный номер помещения'
        if min(self.fio_confidence, self.kv_confidence) >= OCR_REVIEW_THRESHOLD:
            return True, ('Уверенный OCR: подтверждено ФИО — %d' % len(fios))
        if self.fio_confidence < 65 or self.kv_confidence < OCR_REVIEW_THRESHOLD:
            return False, 'Низкая уверенность OCR'
        roi = (self.fio_roi or self.detected_fio_roi) if self.mode == 'manual' else self.detected_fio_roi
        if not roi:
            return False, 'Нет области ФИО для независимой перепроверки'
        old_fio, old_room = self.fio_confidence, self.kv_confidence
        try:
            data = pytesseract.image_to_data(
                self.image.crop(roi).convert('L'),
                config='--psm 6 -l rus', timeout=25,
                output_type=pytesseract.Output.DICT
            )
            repeat_text = ' '.join(data.get('text', []))
            word_conf = [
                float(conf) for word, conf in zip(data.get('text', []), data.get('conf', []))
                if len(re.findall(r'[А-ЯЁа-яё]', word)) >= 2
            ]
            needed_words = sum(len(str(fio).split()) for fio in fios)
            if (len(word_conf) < needed_words or min(word_conf) < 80 or
                    sum(word_conf)/len(word_conf) < 87):
                return False, 'Повторное OCR недостаточно уверенно подтвердило все ФИО'
            verified = self.extract_all_fios(repeat_text)
        finally:
            self.fio_confidence, self.kv_confidence = old_fio, old_room
        normalize = lambda value: ' '.join(str(value or '').casefold().replace('ё','е').split())
        expected=[normalize(v) for v in fios]
        actual=[normalize(v) for v in verified if self._fio_shape_valid(v)]
        if actual == expected:
            return True, f'Повторное OCR подтвердило {len(fios)} ФИО и помещение'
        return False, 'Повторное OCR не подтвердило весь список ФИО'

    def load_roi(self):
        data = safe_json_load(ROI_DATA_PATH, {})
        self.saved_roi_data = data if isinstance(data, dict) else {}
        data = self.saved_roi_data
        if data.get('version') == 3:
            self.saved_fio_roi = tuple(data.get('legacy_fio_roi', [])) or None
            self.saved_kv_roi = tuple(data.get('legacy_kv_roi', [])) or None
        else:
            self.saved_fio_roi = tuple(data.get('fio_roi', [])) or None
            self.saved_kv_roi = tuple(data.get('kv_roi', [])) or None
        self.roi_saved = bool(self.saved_fio_roi and self.saved_kv_roi)

    def _backup_training_data(self, reason="auto"):
        try:
            os.makedirs(TRAINING_BACKUP_DIR, exist_ok=True)
            stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            copied = 0
            for path in (ROI_DATA_PATH, TEMPLATES_PATH):
                if os.path.isfile(path):
                    stem, ext = os.path.splitext(os.path.basename(path))
                    shutil.copy2(path, os.path.join(
                        TRAINING_BACKUP_DIR, f"{stem}_{reason}_{stamp}{ext}"))
                    copied += 1
            for stem in ('roi_data_', 'templates_'):
                items = sorted(
                    (os.path.join(TRAINING_BACKUP_DIR, name)
                     for name in os.listdir(TRAINING_BACKUP_DIR)
                     if name.startswith(stem) and name.lower().endswith('.json')),
                    key=os.path.getmtime, reverse=True)
                for old in items[30:]:
                    try:
                        os.remove(old)
                    except OSError:
                        pass
            if copied:
                logger.info('Резервная копия обучения сохранена: %s файл(а)', copied)
            return True
        except Exception:
            logger.exception('Не удалось создать резервную копию обучения')
            return False

    def save_roi(self):
        if self.image is None or not self.fio_roi or not self.kv_roi:
            return False
        self._backup_training_data('before_roi_save')
        data = self._make_adaptive_template('Последние области')
        data['legacy_fio_roi'] = list(self.fio_roi)
        data['legacy_kv_roi'] = list(self.kv_roi)
        if not atomic_json_save(ROI_DATA_PATH, data):
            return False
        self.saved_roi_data = data
        self.saved_fio_roi, self.saved_kv_roi = self.fio_roi, self.kv_roi
        self.roi_saved = True
        return True
    def save_progress(self):
        try:
            progress = {'current_oss': self.current_oss, 'current_index': self.current_index, 'total_files': len(self.pdf_files),
                        'processed': self.current_index, 'total_created': self.total_created, 'total_skipped': self.total_skipped,
                        'total_votes': self.total_votes, 'timestamp': datetime.now().isoformat()}
            atomic_json_save(PROGRESS_FILE_PATH, progress)
        except Exception:
            logger.exception('Ошибка сохранения прогресса')
    def load_templates(self):
        value = safe_json_load(TEMPLATES_PATH, {})
        return value if isinstance(value, dict) else {}
    def save_templates(self):
        atomic_json_save(TEMPLATES_PATH, self.templates)
    def learn_template(self, text, fios, kv):
        if not fios and not kv:
            return
        digest = hashlib.sha1((text[:300] or '').encode('utf-8', errors='ignore')).hexdigest()[:16]
        if digest:
            self.templates[f'ocr:{digest}'] = {
                'kind': 'ocr_result', 'fios': fios, 'kv': kv,
                'timestamp': datetime.now().isoformat()
            }
            self.save_templates()

    @staticmethod
    def _normalized_roi(roi, width, height):
        if not roi or width <= 0 or height <= 0:
            return None
        x1, y1, x2, y2 = roi
        return [round(x1 / width, 6), round(y1 / height, 6),
                round(x2 / width, 6), round(y2 / height, 6)]

    @staticmethod
    def _restore_roi(normalized, width, height):
        if not normalized or len(normalized) != 4:
            return None
        x1, y1, x2, y2 = normalized
        roi = (max(0, round(x1 * width)), max(0, round(y1 * height)),
               min(width, round(x2 * width)), min(height, round(y2 * height)))
        return roi if roi[2] - roi[0] >= 10 and roi[3] - roi[1] >= 10 else None

    @staticmethod
    def _layout_signature(image):
        if image is None:
            return []
        sample = ImageOps.autocontrast(image.convert('L'), cutoff=1).resize((32, 32), Image.Resampling.BILINEAR)
        pixels = list(sample.getdata())
        darkness = [(255.0 - value) / 255.0 for value in pixels]
        signature = []
        for by in range(8):
            for bx in range(8):
                values = [darkness[y * 32 + x]
                          for y in range(by * 4, by * 4 + 4)
                          for x in range(bx * 4, bx * 4 + 4)]
                signature.append(round(min(1.0, sum(values) / len(values) * 4.0), 4))
        for band in range(16):
            rows = darkness[band * 2 * 32:(band * 2 + 2) * 32]
            signature.append(round(min(1.0, sum(rows) / len(rows) * 4.0), 4))
        for band in range(16):
            cols = [darkness[y * 32 + x] for y in range(32) for x in range(band * 2, band * 2 + 2)]
            signature.append(round(min(1.0, sum(cols) / len(cols) * 4.0), 4))
        return signature

    def _layout_templates(self):
        return [(key, value) for key, value in self.templates.items()
                if isinstance(value, dict) and value.get('kind') == 'layout'
                and value.get('signature') and value.get('fio_roi') and value.get('kv_roi')]

    @staticmethod
    def _template_roi_distance(first, second):
        distances = []
        for field in ('fio_roi', 'kv_roi'):
            left, right = first.get(field), second.get(field)
            if not left or not right or len(left) != 4 or len(right) != 4:
                return 1.0
            distances.append(max(abs(float(a) - float(b)) for a, b in zip(left, right)))
        return max(distances, default=1.0)

    def _template_signature_score(self, image, template):
        current = self._layout_signature(image)
        saved = template.get('signature', [])
        if not current or len(current) != len(saved):
            return 0.0
        difference = sum(abs(float(a) - float(b)) for a, b in zip(current, saved)) / len(current)
        return max(0.0, min(1.0, 1.0 - difference * 3.0))

    def _rank_layout_template_matches(self, image, minimum_score=0.72, limit=3):
        cache_key = (id(image), round(float(minimum_score), 3))
        cached = getattr(self, '_layout_match_cache', {}).get(cache_key)
        if cached is not None:
            return cached[:max(1, int(limit))]
        layouts = self._layout_templates()
        adaptive = [(k, t) for k, t in layouts if t.get('version') == 3]
        adaptive_remainder = []
        if getattr(self, 'fast_mode', False) and len(adaptive) > 18:
            coarse_signature = self._layout_signature(image)
            coarse = []
            complete = bool(coarse_signature)
            aspect = image.width / max(1.0, image.height)
            for key, template in adaptive:
                saved = template.get('signature', [])
                if not saved or len(saved) != len(coarse_signature):
                    complete = False
                    break
                difference = sum(abs(float(a) - float(b))
                                 for a, b in zip(coarse_signature, saved)) / len(saved)
                score = max(0.0, 1.0 - difference * 3.0)
                saved_aspect = float(template.get('aspect', aspect) or aspect)
                score -= min(0.20, abs(aspect - saved_aspect) /
                             max(aspect, saved_aspect, 0.01) * 0.6)
                coarse.append((score, key, template))
            if complete and coarse:
                coarse.sort(key=lambda item: item[0], reverse=True)
                if coarse[0][0] >= 0.46:
                    # Сначала проверяем только наиболее похожие подписи. Раньше
                    # список лишь сортировался, после чего ORB/RANSAC всё равно
                    # выполнялся для всех 80+ шаблонов.
                    ordered = [(key, template) for _, key, template in coarse]
                    shortlist_size = min(20, len(ordered))
                    adaptive = ordered[:shortlist_size]
                    adaptive_remainder = ordered[shortlist_size:]
        features = self._registration_features(image) if adaptive else None
        matches = []
        aligned_keys = set()
        for key, template in adaptive:
            aligned = self._align_template(image, template, features, template_key=key)
            if aligned:
                aligned_keys.add(key)
                signature_score = self._template_signature_score(aligned['image'], template)
                score = aligned['score'] * 0.72 + signature_score * 0.28
                matches.append({'key': key, 'template': template, 'score': score,
                                'registration_score': aligned['score'],
                                'signature_score': signature_score,
                                'aligned_image': aligned['image'],
                                'match_route': 'registration'})

        # Если короткий список не дал уверенного совпадения, качество важнее
        # скорости: однократно проверяем оставшиеся шаблоны полным способом.
        leader = max(matches, key=lambda item: item['score']) if matches else None
        template101_locked = bool(
            leader and
            str(leader.get('template', {}).get('name', '') or '') == 'Бланк 101' and
            float(leader.get('score', 0.0) or 0.0) >= 0.91 and
            float(leader.get('registration_score', 0.0) or 0.0) >= 0.93 and
            float(leader.get('signature_score', 0.0) or 0.0) >= 0.86)
        registration_locked = bool(
            template101_locked or
            (leader and leader['score'] >= 0.93 and
             float(leader.get('registration_score', 0.0) or 0.0) >= 0.93 and
             float(leader.get('signature_score', 0.0) or 0.0) >= 0.90))
        if adaptive_remainder and not registration_locked:
            for key, template in adaptive_remainder:
                aligned = self._align_template(image, template, features,
                                               template_key=key)
                if not aligned:
                    continue
                aligned_keys.add(key)
                signature_score = self._template_signature_score(
                    aligned['image'], template)
                score = aligned['score'] * 0.72 + signature_score * 0.28
                matches.append({
                    'key': key, 'template': template, 'score': score,
                    'registration_score': aligned['score'],
                    'signature_score': signature_score,
                    'aligned_image': aligned['image'],
                    'match_route': 'registration-fallback'
                })

        signature = self._layout_signature(image)
        structure_cache = {}
        aspect = image.width / max(1.0, image.height)
        for key, template in layouts:
            if template.get('version') == 3:
                if key in aligned_keys:
                    continue
                # При сильном геометрическом совпадении из shortlist не даём
                # невыравненному похожему дублю перехватить результат.
                if registration_locked:
                    continue
                saved_structure = template.get('structure_signature')
                fio_roi = self._restore_roi(template.get('fio_roi'), image.width, image.height)
                kv_roi = self._restore_roi(template.get('kv_roi'), image.width, image.height)
                if saved_structure and fio_roi and kv_roi:
                    roi_key = (tuple(fio_roi), tuple(kv_roi))
                    if roi_key not in structure_cache:
                        structure_cache[roi_key] = self._layout_structure_signature(image, (fio_roi, kv_roi))
                    current = structure_cache[roi_key]
                    saved = saved_structure
                else:
                    current = signature
                    saved = template.get('signature', [])
                if not current or len(saved) != len(current):
                    continue
                difference = sum(abs(float(a) - float(b)) for a, b in zip(current, saved)) / len(current)
                signature_score = max(0.0, 1.0 - difference * 3.0)
                saved_aspect = float(template.get('aspect', aspect) or aspect)
                aspect_penalty = min(0.20, abs(aspect - saved_aspect) /
                                     max(aspect, saved_aspect, 0.01) * 0.6)
                score = signature_score - aspect_penalty
                if score >= max(minimum_score, 0.80):
                    matches.append({'key': key, 'template': template, 'score': score,
                                    'registration_score': 0.0,
                                    'signature_score': signature_score,
                                    'match_route': 'structure-fallback'})
                continue
            saved = template.get('signature', [])
            if not signature or len(saved) != len(signature):
                continue
            difference = sum(abs(float(a) - float(b)) for a, b in zip(signature, saved)) / len(signature)
            score = max(0.0, 1.0 - difference * 3.0)
            saved_aspect = float(template.get('aspect', aspect) or aspect)
            score -= min(0.25, abs(aspect - saved_aspect) /
                         max(aspect, saved_aspect, 0.01) * 0.5)
            if score >= minimum_score:
                matches.append({'key': key, 'template': template, 'score': score,
                                'match_route': 'legacy-signature'})
        matches = [item for item in matches if item['score'] >= minimum_score]
        matches.sort(key=lambda item: item['score'], reverse=True)
        # До завершения фоновой очистки одинаковые шаблоны не должны
        # вытеснять из списка кандидатов действительно отличающиеся макеты.
        diverse_matches = []
        for item in matches:
            duplicate = any(
                self._template_roi_distance(item['template'], kept['template']) <= 0.015 and
                self._signature_distance(item['template'].get('signature'),
                                         kept['template'].get('signature')) <= 0.012
                for kept in diverse_matches)
            if not duplicate:
                diverse_matches.append(item)
        matches = diverse_matches
        self._layout_match_cache = {cache_key: matches[:8]}
        return matches[:max(1, int(limit))]

    def _match_layout_template(self, image, minimum_score=0.82):
        matches = self._rank_layout_template_matches(image, minimum_score=0.72, limit=2)
        if not matches or matches[0]['score'] < minimum_score:
            return None
        best = matches[0]
        if len(matches) > 1:
            second = matches[1]
            best['second_score'] = second['score']
            if (best['score'] - second['score'] < 0.035 and
                    self._template_roi_distance(best['template'], second['template']) > 0.035):
                return None
        return best

    def _turbo_fio_roi_result(self, image, roi):
        if image is None or not roi:
            return None
        crop = image.crop(roi)
        if crop.width < 10 or crop.height < 10:
            return None
        max_side = max(crop.size)
        if max_side < 1500:
            scale = min(2.0, 1500.0 / max_side)
            crop = crop.resize((max(1, int(crop.width * scale)),
                                max(1, int(crop.height * scale))), Image.Resampling.LANCZOS)
        quick = ImageOps.autocontrast(crop.convert('L'), cutoff=1)
        candidates = []
        best = None
        normalize = lambda value: ' '.join(
            re.sub(r'[^а-яё-]+', ' ', str(value or '').casefold().replace('ё', 'е')).split())
        for index, psm in enumerate(('7', '6', '11')):
            text, ocr_conf, _ = self._tesseract_candidate(quick, psm)
            old_conf = self.fio_confidence
            try:
                fios = self.extract_all_fios(text)
                parsed_conf = float(self.fio_confidence or 0.0)
            finally:
                self.fio_confidence = old_conf
            if hasattr(self, '_fio_list_valid'):
                valid = bool(self._fio_list_valid(fios))
            else:
                valid = (len(fios) == 1 and
                         re.fullmatch(r'[А-ЯЁа-яё-]{2,40}(?: [А-ЯЁа-яё-]{2,40}){2}', fios[0] or ''))
            if not valid:
                candidate = None
            else:
                conf = min(97.0, max(parsed_conf,
                                     parsed_conf * 0.72 + float(ocr_conf or 0.0) * 0.28 + 2.0))
                candidate = {
                    'fios': list(fios), 'conf': conf, 'text': text,
                    'variant': f'turbo-fio/psm{psm}', 'roi': roi,
                    '_raw_ocr_conf': float(ocr_conf or 0.0),
                    '_norms': tuple(normalize(value) for value in fios)
                }
                candidates.append(candidate)
                if best is None or candidate['conf'] > best['conf']:
                    best = candidate
            grouped = {}
            for item in candidates:
                grouped.setdefault(item['_norms'], []).append(item)
            winners = max(grouped.values(), key=len, default=[])
            if len(winners) >= 2:
                avg_raw = sum(item['_raw_ocr_conf'] for item in winners) / len(winners)
                if avg_raw >= 55.0:
                    chosen = max(winners, key=lambda item: (item['conf'], item['_raw_ocr_conf']))
                    chosen['conf'] = max(float(chosen['conf']), 92.0)
                    chosen['_consensus'] = True
                    chosen['variant'] += '+consensus-2of3'
                    chosen.pop('_norms', None)
                    return chosen
            if index == 1 and len(candidates) >= 2:
                continue
        if best is not None:
            best['_consensus'] = False
            best.pop('_norms', None)
        return best

    def _turbo_room_roi_result(self, image, roi):
        if image is None or not roi:
            return None
        crop = image.crop(roi)
        if crop.width < 8 or crop.height < 8:
            return None
        max_side = max(crop.size)
        scale = min(3.2, max(2.0, 1900.0 / max_side))
        crop = crop.resize((max(1, int(crop.width * scale)),
                            max(1, int(crop.height * scale))), Image.Resampling.LANCZOS)
        gray = ImageOps.autocontrast(crop.convert('L'), cutoff=1)
        variants = [('gray', gray)]
        if OPENCV_AVAILABLE and NUMPY_AVAILABLE:
            try:
                arr = np.array(gray)
                _, otsu = cv2.threshold(arr, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                variants.append(('otsu', Image.fromarray(otsu)))
            except Exception:
                pass
        configs = [
            ('room7', '--psm 7 -l rus+eng --oem 3'),
            ('room6', '--psm 6 -l rus+eng --oem 3'),
            ('room10', '--psm 10 -l rus+eng --oem 3'),
        ]
        votes = {}
        # FIX_v43.17.54: два главных прохода запускаются параллельно.
        # Раньше это был строго последовательный вызов, хотя оба независимы.
        pairs = [(variants[0], configs[0]),
                 ((variants[1] if len(variants) > 1 else variants[0]), configs[1])]

        def run_pass(vname, variant, cname, config):
            try:
                data = pytesseract.image_to_data(variant, config=config,
                                                  output_type=pytesseract.Output.DICT)
                words, confs = [], []
                for word, conf in zip(data.get('text', []), data.get('conf', [])):
                    word = (word or '').strip()
                    if not word:
                        continue
                    words.append(word)
                    try:
                        value = float(conf)
                        if value >= 0:
                            confs.append(value)
                    except Exception:
                        pass
                raw = ' '.join(words)
                compact = re.sub(r'\s+', '', raw)
                value_match = re.search(
                    r'[0-9OОIlІЗБВB]{1,5}(?:[-/.][0-9OОIlІЗБВB]{1,5})?', compact, re.I)
                room = self._normalize_room_value(value_match.group(0)) if value_match else None
                if not room or not re.fullmatch(r'\d{1,5}(?:[-/.]\d{1,5})?', room):
                    return None
                ocr_conf = sum(confs) / len(confs) if confs else 0.0
                return (room, ocr_conf, raw, f'{vname}/{cname}')
            except Exception:
                logger.debug('Turbo room OCR failed', exc_info=True)
                return None

        with ThreadPoolExecutor(max_workers=_ocr_max_workers(2)) as pool:
            futures = [pool.submit(run_pass, vname, variant, cname, config)
                       for (vname, variant), (cname, config) in pairs]
            for fut in futures:
                outcome = fut.result()
                if not outcome:
                    continue
                room, ocr_conf, raw, source = outcome
                item = votes.setdefault(room, {'count': 0, 'max_conf': 0.0, 'text': raw, 'sources': []})
                item['count'] += 1
                item['max_conf'] = max(item['max_conf'], ocr_conf)
                item['sources'].append(source)

        preliminary = max(votes.values(), key=lambda item: (item['count'], item['max_conf']), default=None)
        if not preliminary or preliminary['count'] < 2:
            cname, config = configs[2]
            with ThreadPoolExecutor(max_workers=_ocr_max_workers(min(2, len(variants[:2])))) as pool:
                futures = [pool.submit(run_pass, vname, variant, cname, config)
                           for vname, variant in variants[:2]]
                for fut in futures:
                    outcome = fut.result()
                    if not outcome:
                        continue
                    room, ocr_conf, raw, source = outcome
                    item = votes.setdefault(room, {'count': 0, 'max_conf': 0.0,
                                                   'text': raw, 'sources': []})
                    item['count'] += 1
                    item['max_conf'] = max(item['max_conf'], ocr_conf)
                    item['sources'].append(source)
        if not votes:
            return None
        room, info = max(votes.items(), key=lambda item: (item[1]['count'], item[1]['max_conf']))
        if info['count'] < 2:
            # Сохраняем единственный правдоподобный ответ как подсказку для
            # одного независимого контрольного прохода. Сам по себе он не
            # считается подтверждённым и автоматически не принимается.
            return {'kv': room, 'conf': min(79.0, max(55.0, info['max_conf'])),
                    'text': info.get('text', ''),
                    'variant': 'turbo-room-single:' + ','.join(info['sources']),
                    'roi': roi, '_consensus': False}
        conf = min(97.0, max(90.0, 72.0 + info['max_conf'] * 0.25))
        return {'kv': room, 'conf': conf, 'text': info.get('text', ''),
                'variant': 'turbo-room:' + ','.join(info['sources']), 'roi': roi}

    def _template_room_psm6_consensus(self, image, roi):
        """Три дешёвых независимых psm6-прохода для расширенной зоны номера."""
        if image is None or not roi:
            return None
        crop = image.crop(roi)
        if crop.width < 8 or crop.height < 8:
            return None
        scale = min(3.0, max(1.8, 1800.0 / max(crop.size)))
        crop = crop.resize((max(1, int(crop.width * scale)),
                            max(1, int(crop.height * scale))),
                           Image.Resampling.LANCZOS)
        gray = ImageOps.autocontrast(crop.convert('L'), cutoff=1)
        variants = [('gray', gray)]
        if OPENCV_AVAILABLE and NUMPY_AVAILABLE:
            try:
                arr = np.array(gray)
                _, otsu = cv2.threshold(
                    arr, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                adaptive = cv2.adaptiveThreshold(
                    arr, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    cv2.THRESH_BINARY, 31, 11)
                variants.extend([('otsu', Image.fromarray(otsu)),
                                 ('adaptive', Image.fromarray(adaptive))])
            except Exception:
                pass

        def recognize(item):
            name, variant = item
            try:
                data = pytesseract.image_to_data(
                    variant, config='--psm 6 -l rus+eng --oem 3',
                    output_type=pytesseract.Output.DICT)
                words, confs = [], []
                for word, raw_conf in zip(data.get('text', []),
                                          data.get('conf', [])):
                    word = (word or '').strip()
                    if not word:
                        continue
                    words.append(word)
                    try:
                        value = float(raw_conf)
                        if value >= 0:
                            confs.append(value)
                    except Exception:
                        pass
                text = ' '.join(words)
                values = []
                direct = self.extract_kv_only(text)
                if direct:
                    values.append(direct)
                for token in re.findall(
                        r'[0-9OОIlІЗБВB]{1,6}(?:[-/.][0-9OОIlІЗБВB]{1,6})?',
                        text, re.I):
                    value = self._normalize_room_value(token)
                    if value and re.fullmatch(r'\d{1,5}(?:[-/.]\d{1,5})?', value):
                        values.append(value)
                return name, list(dict.fromkeys(values)), text, (
                    sum(confs) / len(confs) if confs else 0.0)
            except Exception:
                logger.debug('Template room psm6 failed', exc_info=True)
                return name, [], '', 0.0

        votes = {}
        with ThreadPoolExecutor(
                max_workers=_ocr_max_workers(min(OCR_PARALLEL_WORKERS, len(variants))),
                thread_name_prefix='tmpl-room') as pool:
            outcomes = list(pool.map(recognize, variants))
        for name, values, text, raw_conf in outcomes:
            for value in values:
                entry = votes.setdefault(value, {'count': 0, 'max_conf': 0.0,
                                                 'text': text, 'sources': []})
                entry['count'] += 1
                entry['max_conf'] = max(entry['max_conf'], raw_conf)
                entry['sources'].append(name)
        if not votes:
            return None
        value, info = max(votes.items(),
                          key=lambda item: (item[1]['count'], item[1]['max_conf']))
        if info['count'] < 2:
            return None
        conf = min(94.0, max(84.0, 68.0 + info['max_conf'] * 0.24))
        return {'kv': value, 'conf': conf, 'text': info['text'],
                'variant': 'template-room-consensus:' + ','.join(info['sources']),
                'roi': roi, '_consensus': True}

    def _fast_template94_room_result(self, image):
        """Read the room cell from the grid without full-page Tesseract."""
        empty = {'kv': None, 'conf': 0.0, 'text': '',
                 'variant': 'template94-grid-not-found', 'roi': None,
                 'engine': 'TemplateGridOCR'}
        if image is None or not OPENCV_AVAILABLE or not NUMPY_AVAILABLE:
            return empty
        try:
            gray = np.array(ImageOps.autocontrast(image.convert('L'), cutoff=1))
            h, w = gray.shape[:2]
            _, binary = cv2.threshold(
                gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            horizontal_kernel = cv2.getStructuringElement(
                cv2.MORPH_RECT, (max(50, w // 8), 1))
            horizontal = cv2.morphologyEx(
                binary, cv2.MORPH_OPEN, horizontal_kernel)
            horizontal_projection = (horizontal > 0).sum(axis=1)
            ys = self._group_line_positions(
                np.where(horizontal_projection > max(70, w * 0.13))[0].tolist(),
                gap=max(2, h // 1200))

            row = None
            for index in range(len(ys) - 2):
                top, header_bottom, data_bottom = ys[index:index + 3]
                header_height = header_bottom - top
                data_height = data_bottom - header_bottom
                if (h * 0.22 < top < h * 0.58 and
                        h * 0.02 < header_height < h * 0.075 and
                        h * 0.02 < data_height < h * 0.075):
                    row = (top, header_bottom, data_bottom)
                    break
            if row is None:
                return empty

            top, header_bottom, data_bottom = row
            band = binary[max(0, top - 3):min(h, data_bottom + 3), :]
            vertical_kernel = cv2.getStructuringElement(
                cv2.MORPH_RECT,
                (1, max(20, int((data_bottom - top) * 0.55))))
            vertical = cv2.morphologyEx(
                band, cv2.MORPH_OPEN, vertical_kernel)
            vertical_projection = (vertical > 0).sum(axis=0)
            xs = self._group_line_positions(
                np.where(vertical_projection >
                         (data_bottom - top) * 0.55)[0].tolist(),
                gap=max(2, w // 900))
            xs = [x for x in xs if w * 0.01 < x < w * 0.99]
            if len(xs) < 5:
                return empty
            offset = 2 if len(xs) >= 6 and xs[1] - xs[0] < w * 0.09 else 1
            if offset + 1 >= len(xs):
                return empty
            left, right = xs[offset], xs[offset + 1]
            if not (w * 0.12 < right - left < w * 0.40):
                return empty
            pad_x = max(4, int((right - left) * 0.025))
            pad_y = max(3, int((data_bottom - header_bottom) * 0.08))
            roi = (left + pad_x, header_bottom + pad_y,
                   right - pad_x, data_bottom - pad_y)
            if roi[2] <= roi[0] or roi[3] <= roi[1]:
                return empty

            crop = ImageOps.autocontrast(image.crop(roi).convert('L'), cutoff=1)
            crop = crop.resize(
                (max(1, crop.width * 2), max(1, crop.height * 2)),
                Image.Resampling.LANCZOS)
            text = pytesseract.image_to_string(
                crop,
                config='--psm 6 -l rus --oem 3 -c preserve_interword_spaces=1',
                timeout=6).strip()
            explicit = re.findall(
                r'(?i)(?:пом(?:ещение)?|кв(?:артира)?)'
                r'[\s.,:;№#-]*([0-9OОIlІЗБВB]{1,5}'
                r'(?:[-/.][0-9OОIlІЗБВB]{1,5})?[А-ЯЁA-Z]?)',
                text)
            value = self._normalize_room_value(explicit[-1]) if explicit else None
            confidence = 94.0
            if not value:
                numbers = [self._normalize_room_value(token) for token in re.findall(
                    r'(?<!\d)[0-9OОIlІЗБВB]{1,5}(?!\d)', text)]
                numbers = [item for item in numbers if item and item not in ('0', '00')]
                if len(numbers) >= 2:
                    value = numbers[-1]
                    confidence = 86.0
            if not value or not re.fullmatch(
                    r'\d{1,5}(?:[-/.]\d{1,5})?[А-ЯЁA-Z]?', value, re.I):
                result = dict(empty)
                result.update({'text': text, 'roi': roi})
                return result
            logger.info('Template94Grid selected=%s conf=%.1f roi=%s',
                        value, confidence, roi)
            return {'kv': value, 'conf': confidence, 'text': text,
                    'variant': 'template94-grid-cell', 'roi': roi,
                    'engine': 'TemplateGridOCR', '_consensus': True}
        except Exception:
            logger.exception('Ошибка быстрого OCR таблицы Бланк 94')
            return empty

    def _turbo_layout_template_result(self, image):
        matches = []
        preferred_name = str(getattr(self, 'preferred_layout_template', '') or '')
        if preferred_name:
            preferred = next(
                ((key, template) for key, template in self._layout_templates()
                 if str(template.get('name', '') or '') == preferred_name), None)
            if preferred and preferred[1].get('version') == 3:
                features = self._registration_features(image)
                aligned = self._align_template(image, preferred[1], features, template_key=preferred[0])
                if aligned:
                    signature_score = self._template_signature_score(aligned['image'], preferred[1])
                    score = aligned['score'] * 0.72 + signature_score * 0.28
                    preferred_name_value = str(preferred[1].get('name', '') or '')
                    template101_fast = preferred_name_value == 'Бланк 101'
                    score_limit = 0.90 if template101_fast else 0.96
                    registration_limit = 0.88 if template101_fast else 0.95
                    signature_limit = 0.86 if template101_fast else 0.92
                    if (score >= score_limit and
                            aligned['score'] >= registration_limit and
                            signature_score >= signature_limit):
                        matches = [{
                            'key': preferred[0], 'template': preferred[1], 'score': score,
                            'registration_score': aligned['score'],
                            'signature_score': signature_score,
                            'aligned_image': aligned['image'], 'match_route': 'preferred-registration'
                        }]
        if not matches:
            matches = self._rank_layout_template_matches(image, minimum_score=0.72, limit=2)
        if not matches or matches[0]['score'] < 0.82:
            return None
        best = matches[0]
        if len(matches) > 1 and best['score'] - matches[1]['score'] < 0.035:
            if self._template_roi_distance(best['template'], matches[1]['template']) > 0.025:
                return None
        if not best.get('aligned_image') and best.get('match_route') == 'structure-fallback' and best['score'] < 0.90:
            return None
        template = best['template']
        template_name = str(template.get('name', '') or '')
        # У Бланка 101 исходная геометрия уже совпадает с сохранёнными
        # нормализованными зонами. Перспективное выравнивание слегка сдвигает
        # курсивную строку ФИО за пределы ROI, поэтому применяем его только для
        # выбора шаблона, а поля читаем с исходной страницы.
        candidate_image = (image if template_name == 'Бланк 101'
                           else (best.get('aligned_image') or image))
        fio_roi = self._restore_roi(template.get('fio_roi'), candidate_image.width, candidate_image.height)
        kv_roi = self._restore_roi(template.get('kv_roi'), candidate_image.width, candidate_image.height)
        if not fio_roi or not kv_roi:
            return None
        ocr_fio_roi = fio_roi
        ocr_kv_roi = kv_roi
        if template_name == 'Бланк 101':
            # В этом макете сохранённые прямоугольники точно указывают строку,
            # но по высоте обрезают курсив. Небольшое расширение даёт два
            # согласованных чтения примерно за секунду вместо полного каскада.
            def expand_xy(roi, pad_x, pad_y):
                x1, y1, x2, y2 = roi
                width, height = x2-x1, y2-y1
                return (
                    max(0, int(x1-width*pad_x)),
                    max(0, int(y1-height*pad_y)),
                    min(candidate_image.width, int(x2+width*pad_x)),
                    min(candidate_image.height, int(y2+height*pad_y)),
                )
            ocr_fio_roi = expand_xy(fio_roi, 0.10, 0.35)
            ocr_kv_roi = expand_xy(kv_roi, 0.45, 0.75)
        with ThreadPoolExecutor(max_workers=_ocr_max_workers(2), thread_name_prefix='ocr-roi') as pool:
            fio_future = pool.submit(self._turbo_fio_roi_result, candidate_image, ocr_fio_roi)
            if template_name == 'Бланк 94':
                room_future = pool.submit(
                    self._fast_template94_room_result, candidate_image)
            else:
                room_future = pool.submit(
                    self._turbo_room_roi_result, candidate_image, ocr_kv_roi)
            fio = fio_future.result()
            room = room_future.result()
        fio_conf = float((fio or {}).get('conf', 0) or 0)
        room_conf = float((room or {}).get('conf', 0) or 0)
        fio_verified = bool(fio) and fio_conf >= OCR_REVIEW_THRESHOLD and (
            bool(fio.get('_consensus')) or
            (best['score'] >= 0.94 and
             float(fio.get('_raw_ocr_conf', 0.0) or 0.0) >= 82.0 and
             self._fio_list_valid(fio.get('fios', []))))
        room_verified = bool(room) and room_conf >= 90.0
        verified = bool(fio_verified and room_verified)
        if not verified:
            # Не повторяем весь тяжёлый каскад и три расширения обеих ROI.
            # Дочитываем только сомнительное поле в исходной обученной зоне.
            recovered_fio = fio
            recovered_room = room
            if not (recovered_fio and
                    self._fio_list_valid(recovered_fio.get('fios', [])) and
                    float(recovered_fio.get('conf', 0.0) or 0.0) >= 82.0):
                # На части обученных бланков зона ФИО сохранена слишком узко.
                # Один проход с +80% захватывает всю строку; прежний код делал
                # три тяжёлых расширения 35/55/80 для каждого поля.
                recovery_fio_roi = self.get_roi_with_padding(
                    ocr_fio_roi, candidate_image.width, candidate_image.height,
                    pad_pct=80)
                candidate = self._turbo_fio_roi_result(
                    candidate_image, recovery_fio_roi)
                if not (candidate and
                        self._fio_list_valid(candidate.get('fios', [])) and
                        (bool(candidate.get('_consensus')) or
                         (float(candidate.get('conf', 0.0) or 0.0) >= 82.0 and
                          float(candidate.get('_raw_ocr_conf', 0.0) or 0.0) >= 82.0))):
                    candidate = self._best_tesseract_result(
                        candidate_image, recovery_fio_roi)
                if self._fio_list_valid(candidate.get('fios', [])):
                    recovered_fio = {
                        'fios': list(candidate.get('fios') or []),
                        'conf': float(candidate.get('fio_conf', 0.0) or 0.0),
                        'text': candidate.get('text', ''),
                        'variant': candidate.get('fio_variant',
                                                 candidate.get('variant', 'template-recovery'))
                    }
                    if candidate.get('conf') is not None:
                        recovered_fio['conf'] = float(candidate.get('conf', 0.0) or 0.0)
            if not (recovered_room and recovered_room.get('kv') and
                    float(recovered_room.get('conf', 0.0) or 0.0) >= 82.0):
                # Для номера достаточно меньшего расширения: оно исправляет
                # обрезанные цифры (например, 53 -> 33), не захватывая соседние
                # реквизиты документа.
                recovery_kv_roi = self.get_roi_with_padding(
                    ocr_kv_roi, candidate_image.width, candidate_image.height,
                    pad_pct=35)
                candidate = self._turbo_room_roi_result(
                    candidate_image, recovery_kv_roi)
                if not (candidate and candidate.get('kv') and
                        float(candidate.get('conf', 0.0) or 0.0) >= 82.0):
                    candidate = self._template_room_psm6_consensus(
                        candidate_image, recovery_kv_roi)
                if not (candidate and candidate.get('kv') and
                        float(candidate.get('conf', 0.0) or 0.0) >= 82.0):
                    candidate = self._best_room_ocr_result(
                        candidate_image, recovery_kv_roi)
                if candidate.get('kv'):
                    recovered_room = candidate
            fallback = {
                'name': template.get('name', 'Бланк'),
                'match_score': best['score'],
                'fio_roi': fio_roi, 'kv_roi': kv_roi,
                'fios': list((recovered_fio or {}).get('fios') or []),
                'fio_conf': float((recovered_fio or {}).get('conf', 0.0) or 0.0),
                'fio_text': (recovered_fio or {}).get('text', ''),
                'fio_variant': (recovered_fio or {}).get('variant',
                                                         'template-unreadable'),
                'kv': (recovered_room or {}).get('kv'),
                'kv_conf': float((recovered_room or {}).get('conf', 0.0) or 0.0),
                'kv_text': (recovered_room or {}).get('text', ''),
                'kv_variant': (recovered_room or {}).get('variant',
                                                         'template-unreadable'),
                'kv_engine': (recovered_room or {}).get('engine', 'TemplateROI'),
            }
            fallback['_matched_image'] = candidate_image
            fallback['_turbo'] = False
            fallback['_quick_template_candidate'] = True
            fallback['_ambiguous_match'] = False
            return fallback
        return {
            'name': template.get('name', 'Бланк'), 'match_score': best['score'],
            'fio_roi': fio_roi, 'kv_roi': kv_roi,
            'fios': list((fio or {}).get('fios') or []), 'fio_conf': fio_conf,
            'fio_text': (fio or {}).get('text', ''),
            'fio_variant': (fio or {}).get('variant', 'turbo-fio-unreadable'),
            'kv': (room or {}).get('kv'), 'kv_conf': room_conf,
            'kv_text': (room or {}).get('text', ''),
            'kv_variant': (room or {}).get('variant', 'turbo-room-unreadable'),
            'kv_engine': (room or {}).get('engine', 'TurboROI'),
            '_matched_image': candidate_image, '_turbo': verified,
            '_quick_template_candidate': True,
            '_ambiguous_match': False
        }

    def _best_layout_template_result(self, image):
        candidates = self._rank_layout_template_matches(image, minimum_score=0.72, limit=3)
        if not candidates:
            return None
        ambiguous = (len(candidates) > 1 and
                     candidates[0]['score'] - candidates[1]['score'] < 0.025 and
                     self._template_roi_distance(candidates[0]['template'],
                                                 candidates[1]['template']) > 0.035)
        candidates_to_check = candidates[:3] if ambiguous else candidates[:1]
        recognized_candidates = []
        for match in candidates_to_check:
            candidate_image = match.get('aligned_image') or image
            recognized = self._recognize_with_layout_template(candidate_image, match)
            if not recognized:
                continue
            has_fio = bool(recognized.get('fios'))
            has_kv = bool(recognized.get('kv')) and str(recognized.get('kv')).strip() not in ('', '0')
            fio_conf = float(recognized.get('fio_conf', 0.0))
            kv_conf = float(recognized.get('kv_conf', 0.0))
            validation = (35.0 if has_fio else 0.0) + (35.0 if has_kv else 0.0)
            validation += min(15.0, fio_conf * 0.15) + min(15.0, kv_conf * 0.15)
            recognized['_template_score'] = match['score'] * 45.0 + validation * 0.55
            recognized['_matched_image'] = candidate_image
            recognized['_ambiguous_match'] = ambiguous
            recognized_candidates.append(recognized)
        if not recognized_candidates:
            return None
        recognized_candidates.sort(key=lambda item: item['_template_score'], reverse=True)
        best = recognized_candidates[0]
        if (ambiguous and len(recognized_candidates) > 1 and
                best['_template_score'] - recognized_candidates[1]['_template_score'] < 3.0):
            logger.info('Похожие шаблоны не удалось различить по OCR зон')
            return None
        if (best.get('match_score', 0) < 0.82 or
                not (best.get('fios') or best.get('kv'))):
            return None
        return best

    # =========================================================================
    # FIX_v43.17.52: анализ и удаление дублей шаблонов
    # =========================================================================
    @staticmethod
    def _signature_distance(sig_a, sig_b):
        if not sig_a or not sig_b or len(sig_a) != len(sig_b):
            return 1.0
        diff = sum(abs(float(a) - float(b)) for a, b in zip(sig_a, sig_b)) / len(sig_a)
        return min(1.0, max(0.0, diff))

    def _analyze_template_duplicates(self, sig_threshold=0.04, roi_threshold=0.03):
        layouts = [(k, v) for k, v in self.templates.items()
                   if isinstance(v, dict) and v.get('kind') == 'layout'
                   and v.get('signature')]
        if len(layouts) < 2:
            return []

        parent = {k: k for k, _ in layouts}
        def find(k):
            while parent[k] != k:
                parent[k] = parent[parent[k]]
                k = parent[k]
            return k
        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra

        for i, (k1, t1) in enumerate(layouts):
            for k2, t2 in layouts[i+1:]:
                if find(k1) == find(k2):
                    continue
                a1 = float(t1.get('aspect', 1.0) or 1.0)
                a2 = float(t2.get('aspect', 1.0) or 1.0)
                if abs(a1 - a2) / max(a1, a2, 0.01) > 0.03:
                    continue
                if self._signature_distance(t1.get('signature'),
                                             t2.get('signature')) > sig_threshold:
                    continue
                ss1 = t1.get('structure_signature') or t1.get('signature')
                ss2 = t2.get('structure_signature') or t2.get('signature')
                if self._signature_distance(ss1, ss2) > sig_threshold * 1.5:
                    continue
                try:
                    d_roi = self._template_roi_distance(t1, t2)
                except Exception:
                    d_roi = 1.0
                if d_roi > roi_threshold:
                    continue
                union(k1, k2)

        groups_map = {}
        for k, t in layouts:
            groups_map.setdefault(find(k), []).append((k, t))
        result = []
        for members in groups_map.values():
            if len(members) < 2:
                continue
            members.sort(key=lambda kv: (
                str(kv[1].get('created_at', '') or ''),
                str(kv[1].get('name', '') or '')))
            result.append(members)
        return result

    def _remove_template_duplicates(self, groups, keep_index=0):
        if not groups:
            return 0, []
        self._backup_training_data('before_dedup')
        removed = 0
        removed_names = []
        removed_items = {}
        for group in groups:
            if len(group) < 2:
                continue
            keep_key = group[keep_index][0]
            for key, tpl in group:
                if key == keep_key:
                    continue
                if key in self.templates:
                    removed_items[key] = self.templates[key]
                    del self.templates[key]
                    removed += 1
                    removed_names.append(str(tpl.get('name', key)))
        if removed:
            if not atomic_json_save(TEMPLATES_PATH, self.templates):
                logger.error('Не удалось сохранить templates.json после удаления дублей')
                self.templates.update(removed_items)
                return 0, []
            self._template_np_cache.clear()
            self._layout_match_cache.clear()
        return removed, removed_names

    def _template_duplicates_dialog(self):
        if getattr(self, 'ocr_busy', False) or getattr(self, 'saving_busy', False):
            messagebox.showinfo('Анализ дублей', 'Дождитесь завершения OCR.')
            return
        try:
            groups = self._analyze_template_duplicates(
                sig_threshold=0.012, roi_threshold=0.015)
        except Exception as exc:
            logger.exception('Ошибка анализа дублей')
            messagebox.showerror('Анализ дублей', f'Не удалось проанализировать шаблоны:\n{exc}')
            return
        total_templates = len(self._layout_templates())
        if not groups:
            messagebox.showinfo(
                'Анализ дублей',
                f'Точные дубли не найдены.\n\nВсего шаблонов: {total_templates}')
            return

        total_dupes = sum(len(g) - 1 for g in groups)
        win = tk.Toplevel(self.parent)
        win.title('Анализ дублей шаблонов')
        win.geometry('950x560')
        win.configure(bg=Theme.colors['bg'])
        try:
            win.transient(self.parent.winfo_toplevel())
        except Exception:
            pass

        tk.Label(
            win,
            text=f'Точные дубли: {len(groups)} групп   •   лишних шаблонов: {total_dupes}',
            bg=Theme.colors['bg'], fg=Theme.colors['accent'],
            font=('Segoe UI', 13, 'bold')
        ).pack(pady=(14, 6))

        tk.Label(
            win,
            text=('В каждой группе первый (самый ранний) шаблон будет сохранён, '
                  'остальные — удалены.\n'
                  'Перед удалением создаётся резервная копия templates.json '
                  'в backup_training/.'),
            bg=Theme.colors['bg'], fg=Theme.colors['fg'],
            font=('Segoe UI', 9), justify=tk.LEFT
        ).pack(pady=(0, 10))

        frame = tk.Frame(win, bg=Theme.colors['bg'])
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        tree = ttk.Treeview(
            frame,
            columns=('group', 'role', 'name', 'fio', 'kv', 'created'),
            show='headings', height=18)
        for col, title, width in (
                ('group', 'Группа', 70),
                ('role', 'Роль', 100),
                ('name', 'Имя шаблона', 220),
                ('fio', 'FIO ROI', 150),
                ('kv', 'KV ROI', 150),
                ('created', 'Создан', 160)):
            tree.heading(col, text=title)
            tree.column(col, width=width, anchor='w')
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        for gi, group in enumerate(groups, 1):
            for mi, (key, tpl) in enumerate(group):
                role = 'ОСТАВИТЬ' if mi == 0 else 'удалить'
                fio_roi = tpl.get('fio_roi')
                kv_roi = tpl.get('kv_roi')
                tree.insert('', 'end', values=(
                    f'#{gi}',
                    role,
                    str(tpl.get('name', key))[:36],
                    f'{fio_roi}'[:24] if fio_roi else '—',
                    f'{kv_roi}'[:24] if kv_roi else '—',
                    str(tpl.get('created_at', ''))[:19]))

        btns = tk.Frame(win, bg=Theme.colors['bg'])
        btns.pack(fill=tk.X, pady=14)

        def do_remove():
            if not messagebox.askyesno(
                    'Удалить дубли?',
                    f'Будет удалено {total_dupes} шаблон(ов).\n'
                    'Перед удалением будет создана резервная копия.\n\n'
                    'Продолжить?'):
                return
            removed, names = self._remove_template_duplicates(groups)
            win.destroy()
            preview = ', '.join(names[:5])
            if len(names) > 5:
                preview += f' … и ещё {len(names) - 5}'
            messagebox.showinfo(
                'Готово',
                f'Удалено дублей: {removed}\n'
                f'Осталось шаблонов: {len(self._layout_templates())}\n\n'
                f'{preview}')
            logger.info('Удалены дубли шаблонов: %s', names)

        make_button(
            btns, '🗑️ Удалить дубликаты', do_remove,
            bg=Theme.colors['error'], fg='white',
            width=22, pady=8
        ).pack(side=tk.LEFT, padx=20)
        make_button(
            btns, 'Закрыть', win.destroy,
            bg=Theme.colors['btn'], fg=Theme.colors['fg'],
            width=12, pady=8
        ).pack(side=tk.RIGHT, padx=20)

        try:
            if hasattr(self, '_theme_window'):
                self._theme_window(win)
        except Exception:
            pass

    def _auto_report_template_duplicates(self):
        if getattr(self, 'ocr_busy', False) or getattr(self, 'saving_busy', False):
            try:
                self.parent.after(5000, self._auto_report_template_duplicates)
            except Exception:
                pass
            return
        try:
            groups = self._analyze_template_duplicates(
                sig_threshold=0.012, roi_threshold=0.015)
        except Exception:
            logger.exception('Автоанализ дублей шаблонов упал')
            return
        if not groups:
            logger.info('Автоанализ шаблонов: дублей не найдено (%d шаблонов)',
                        len(self._layout_templates()))
            return
        total_dupes = sum(len(g) - 1 for g in groups)
        removed, names = self._remove_template_duplicates(groups)
        if not removed:
            logger.warning('Автоочистка шаблонов: найдено %d дублей, удалить не удалось',
                           total_dupes)
            return
        logger.info('Автоочистка шаблонов: удалено %d точных дублей: %s',
                    removed, names)
        if hasattr(self, 'log_label'):
            try:
                self.log_label.config(
                    text=f'🧹 Удалено точных дублей шаблонов: {removed}')
            except Exception:
                pass

    def _save_layout_template(self, name):
        if self.image is None or not self.fio_roi or not self.kv_roi:
            return False
        self._backup_training_data('before_template_save')
        clean_name = sanitize_filename_component(name, 'Бланк')
        key = 'layout:' + hashlib.sha1(clean_name.casefold().encode('utf-8')).hexdigest()[:16]
        old = self.templates.get(key)
        candidate = self._make_adaptive_template(clean_name)
        # Автоматически не создаём второй шаблон для очевидно того же макета.
        # Порог строже ручного анализатора: похожие, но разные формы сохраняются.
        for existing_key, existing in self._layout_templates():
            if existing_key == key or not isinstance(existing, dict):
                continue
            aspect_a = float(candidate.get('aspect', 1.0) or 1.0)
            aspect_b = float(existing.get('aspect', 1.0) or 1.0)
            if abs(aspect_a - aspect_b) / max(aspect_a, aspect_b, 0.01) > 0.012:
                continue
            if self._template_roi_distance(candidate, existing) > 0.015:
                continue
            if self._signature_distance(candidate.get('signature'),
                                        existing.get('signature')) > 0.012:
                continue
            if self._signature_distance(
                    candidate.get('structure_signature') or candidate.get('signature'),
                    existing.get('structure_signature') or existing.get('signature')) > 0.018:
                continue
            existing_name = str(existing.get('name') or existing_key)
            logger.info('Шаблон «%s» не создан: точный дубль «%s»',
                        clean_name, existing_name)
            return existing_name
        self.templates[key] = candidate
        if not atomic_json_save(TEMPLATES_PATH, self.templates):
            if old is None:
                self.templates.pop(key, None)
            else:
                self.templates[key] = old
            return False
        self._template_np_cache.pop(key, None)
        return clean_name

    # =========================================================================
    # FIX_v43.17.54: _recognize_with_layout_template
    # FIO base и Room base выполняются параллельно; расширения ROI тоже
    # параллельны, если оба поля требуют расширения. Логика приёмки и пороги
    # не изменены — качество идентично v43.17.53.
    # =========================================================================
    def _recognize_with_layout_template(self, image, match):
        template = match['template']
        fio_roi = self._restore_roi(template.get('fio_roi'), image.width, image.height)
        kv_roi = self._restore_roi(template.get('kv_roi'), image.width, image.height)
        if not fio_roi or not kv_roi:
            return None

        # Параллельный базовый проход: FIO и Room независимы.
        with ThreadPoolExecutor(max_workers=_ocr_max_workers(2), thread_name_prefix='tmpl-base') as pool:
            fio_future = pool.submit(self._best_tesseract_result, image, fio_roi)
            if str(template.get('name', '') or '') == 'Бланк 94':
                kv_future = pool.submit(self._fast_template94_room_result, image)
            else:
                kv_future = pool.submit(self._best_room_ocr_result, image, kv_roi)
            fio_result = fio_future.result()
            kv_result = kv_future.result()
        fio_ocr_roi = fio_roi
        kv_ocr_roi = kv_roi

        fio_valid_now = self._fio_list_valid(fio_result.get('fios', []))
        fio_conf_now = float(fio_result.get('fio_conf', 0.0) or 0.0)
        fio_needs_expansion = (not fio_valid_now) or (fio_conf_now < 82.0)

        kv_value_now = kv_result.get('kv')
        kv_conf_now = float(kv_result.get('conf', 0.0) or 0.0)
        if (str(template.get('name', '') or '') == 'Бланк 94' and
                kv_result.get('engine') == 'TemplateGridOCR'):
            kv_needs_expansion = not kv_value_now
        else:
            kv_needs_expansion = (not kv_value_now or
                                  str(kv_value_now).strip() in ('', '0') or
                                  kv_conf_now < 82.0)

        steps = (35, 55, 80) if self.fast_mode else (35, 55, 80, 110, 150)

        def expand_fio():
            best_result, best_roi, best_conf = fio_result, fio_ocr_roi, fio_conf_now
            for pad_pct in steps:
                expanded = self.get_roi_with_padding(
                    fio_roi, image.width, image.height, pad_pct=pad_pct)
                if not expanded or expanded == fio_roi:
                    continue
                expanded_result = self._best_tesseract_result(image, expanded)
                if not self._fio_list_valid(expanded_result.get('fios', [])):
                    continue
                expanded_conf = float(expanded_result.get('fio_conf', 0.0) or 0.0)
                if expanded_conf >= best_conf:
                    best_result, best_roi, best_conf = expanded_result, expanded, expanded_conf
                if expanded_conf >= 82.0:
                    break
            return best_result, best_roi

        def expand_kv():
            best_kv_result, best_kv_roi, best_kv_conf = kv_result, kv_ocr_roi, kv_conf_now
            for pad_pct in steps:
                expanded = self.get_roi_with_padding(
                    kv_roi, image.width, image.height, pad_pct=pad_pct)
                if not expanded or expanded == kv_roi:
                    continue
                expanded_result = self._best_room_ocr_result(image, expanded)
                expanded_value = expanded_result.get('kv')
                if not expanded_value or str(expanded_value).strip() in ('', '0'):
                    continue
                expanded_conf = float(expanded_result.get('conf', 0.0) or 0.0)
                if expanded_conf >= best_kv_conf:
                    best_kv_result, best_kv_roi, best_kv_conf = expanded_result, expanded, expanded_conf
                if expanded_conf >= 82.0:
                    break
            return best_kv_result, best_kv_roi

        if fio_needs_expansion and kv_needs_expansion:
            with ThreadPoolExecutor(max_workers=_ocr_max_workers(2), thread_name_prefix='tmpl-exp') as pool:
                fio_future = pool.submit(expand_fio)
                kv_future = pool.submit(expand_kv)
                fio_result, fio_ocr_roi = fio_future.result()
                kv_result, kv_ocr_roi = kv_future.result()
        elif fio_needs_expansion:
            fio_result, fio_ocr_roi = expand_fio()
        elif kv_needs_expansion:
            kv_result, kv_ocr_roi = expand_kv()

        fios = fio_result.get('fios', [])
        fio_conf = float(fio_result.get('fio_conf', 0.0) or 0.0)
        raw_fio_conf = float(fio_result.get('fio_ocr_conf', 0.0) or 0.0)
        if (fios and self._fio_list_valid(fios) and
                float(match.get('score', 0.0) or 0.0) >= 0.90 and raw_fio_conf >= 82.0):
            fio_conf = max(fio_conf, min(94.0, raw_fio_conf))
        return {
            'name': template.get('name', 'Бланк'), 'match_score': match['score'],
            'fio_roi': fio_ocr_roi, 'kv_roi': kv_ocr_roi,
            'fios': fios, 'fio_conf': fio_conf,
            'fio_text': fio_result.get('text', ''),
            'fio_variant': fio_result.get('fio_variant', fio_result.get('variant', 'template')),
            'kv': kv_result.get('kv'), 'kv_conf': float(kv_result.get('conf', 0.0)),
            'kv_text': kv_result.get('text', ''),
            'kv_variant': kv_result.get('variant', 'template'),
            'kv_engine': kv_result.get('engine', 'TemplateROI')
        }

    def detect_text_region(self, image):
        if not NUMPY_AVAILABLE: return (0, 0, image.width, image.height)
        try:
            if image.mode != 'L': gray = image.convert('L')
            else: gray = image
            arr = np.array(gray)
            h, w = arr.shape
            th = min(220, max(150, int(np.percentile(arr, 35))))
            rows = np.sum(arr < th, axis=1)
            cols = np.sum(arr < th, axis=0)
            top = next((i for i, v in enumerate(rows) if v > 5), 0)
            bottom = next((i for i in range(h-1, -1, -1) if rows[i] > 5), h)
            left = next((j for j, v in enumerate(cols) if v > 5), 0)
            right = next((j for j in range(w-1, -1, -1) if cols[j] > 5), w)
            margin = 20
            return (max(0, left-margin), max(0, top-margin), min(w, right+margin), min(h, bottom+margin))
        except Exception:
            logger.debug("Не удалось определить текстовую область", exc_info=True)
            return (0, 0, image.width, image.height)
    def select_best_psm(self, image):
        if not NUMPY_AVAILABLE: return "6"
        try:
            if image.mode != 'L': gray = image.convert('L')
            else: gray = image
            arr = np.array(gray)
            h, w = arr.shape
            density = np.sum(arr < 50) / (h * w)
            if density < 0.01: return "6"
            elif density > 0.3: return "4"
            return "6"
        except Exception: return "6"
    def deskew_image(self, image):
        if not OPENCV_AVAILABLE: return image, 0
        try:
            if image.mode != 'L': gray = image.convert('L')
            else: gray = image
            arr = np.array(gray)
            binary = np.where(arr < 150, 0, 255).astype(np.uint8)
            edges = cv2.Canny(binary, 50, 150, apertureSize=3)
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=100, maxLineGap=10)
            angles = []
            if lines is not None:
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
                    if abs(angle) < 45:
                        angles.append(angle)
            if angles:
                median = np.median(angles)
                if abs(median) > 0.5:
                    return image.rotate(-median, expand=True, fillcolor='white'), median
            return image, 0
        except Exception: return image, 0
    def auto_rotate(self, image):
        try:
            sample = image.copy()
            max_side = max(sample.size)
            if max_side > 1800:
                scale = 1800 / max_side
                sample = sample.resize((int(sample.width * scale), int(sample.height * scale)), Image.Resampling.LANCZOS)
            try:
                osd = pytesseract.image_to_osd(sample, config='--psm 0')
                m = re.search(r'Rotate:\s*(90|180|270)', osd)
                if m:
                    angle = int(m.group(1))
                    logger.info("OSD: поворот документа на %s°", angle)
                    return image.rotate(-angle, expand=True, fillcolor='white')
            except Exception:
                logger.debug("OSD не определил ориентацию", exc_info=True)
            w, h = image.size
            crop = image.crop((w//5, h//5, w*4//5, h*4//5)).convert('L')
            text = pytesseract.image_to_string(crop, config='--psm 6 -l rus')
            rot180 = image.rotate(180, expand=True)
            crop2 = rot180.crop((w//5, h//5, w*4//5, h*4//5)).convert('L')
            text2 = pytesseract.image_to_string(crop2, config='--psm 6 -l rus')
            if len(re.findall(r'[А-Яа-яЁё]{3,}', text2)) > len(re.findall(r'[А-Яа-яЁё]{3,}', text)) * 1.35:
                return rot180
            return image
        except Exception:
            logger.debug("Ошибка автоориентации", exc_info=True)
            return image
    def get_roi_with_padding(self, roi, img_w, img_h, pad_pct=15):
        if roi is None: return None
        x1, y1, x2, y2 = roi
        w = x2 - x1; h = y2 - y1
        pad_x = int(w * pad_pct / 100)
        pad_y = int(h * pad_pct / 100)
        return (max(0, x1 - pad_x), max(0, y1 - pad_y), min(img_w, x2 + pad_x), min(img_h, y2 + pad_y))
    def get_easyocr_reader(self):
        if not self.easyocr_available:
            return None
        if self.easyocr_reader is None:
            try:
                logger.info("Инициализация EasyOCR...")
                self.easyocr_reader = easyocr.Reader(['ru', 'en'], gpu=False, verbose=False)
                logger.info("EasyOCR готов")
            except Exception:
                self.easyocr_available = False
                logger.exception("Ошибка инициализации EasyOCR")
                return None
        return self.easyocr_reader

    def ocr_easyocr(self, image, roi=None):
        reader = self.get_easyocr_reader()
        if reader is None or not NUMPY_AVAILABLE:
            return "", 0.0
        try:
            crop = image.crop(roi) if roi else image
            result = reader.readtext(np.array(crop), detail=1, paragraph=False)
            texts, confs = [], []
            for item in result:
                if not item or len(item) < 3:
                    continue
                text = str(item[1]).strip()
                if not text:
                    continue
                texts.append(text)
                try:
                    confs.append(float(item[2]) * 100.0)
                except (TypeError, ValueError):
                    pass
            confidence = sum(confs) / len(confs) if confs else 0.0
            return '\n'.join(texts), confidence
        except Exception:
            logger.exception("Ошибка EasyOCR")
            return "", 0.0

    def _normalize_ocr_text(self, text):
        text = (text or '').replace('\n', ' ')
        text = re.sub(r'\s+', ' ', text)
        text = text.replace('|', ' ').replace('—', '-')
        return text.strip()

    def _apply_text_corrections(self, value):
        result = value
        for wrong, correct in self.corrections.items():
            if wrong and wrong in result:
                result = result.replace(wrong, correct)
        return re.sub(r'\s+', ' ', result).strip()

    def _fio_candidate_score(self, fio, context=''):
        parts = fio.split()
        if len(parts) not in (3, 4):
            return 0.0
        if len(parts) == 4 and parts[-1].casefold() not in FIO_PARTICLES:
            return 0.0
        score = 45.0
        low = context.lower()
        if any(k in low for k in ('фио', 'ф.и.о', 'собственник', 'владелец', 'представитель')):
            score += 22
        patronymic = parts[2].lower()
        if patronymic.endswith(('ович','евич','ич','овна','евна','ична','инична')):
            score += 18
        if len(parts) == 4:
            score += 20
        if all(len(p) >= 2 for p in parts):
            score += 5
        garbage = {'собрания','собственников','помещений','повестка','решение','голосование','протокол',
                   'председатель','секретарь','инициатор','москва','улица','квартира','помещение','общего'}
        if any(p.lower() in garbage for p in parts):
            score -= 60
        if self.fio_dictionary:
            hits = sum(1 for p in parts if p.lower() in self.fio_dictionary)
            score += hits * 5
        return max(0.0, min(100.0, score))

    def extract_all_fios(self, text):
        text = self._normalize_ocr_text(text)
        if not text:
            self.fio_confidence = 0.0
            return []
        candidates = []
        seen = set()

        # На части печатных форм Tesseract возвращает произвольный регистр:
        # "шереев Вячеслав Олегович" или "руткова Валентина павловна".
        # Отдельно проверяем тройки слов внутри одной строки и принимаем их
        # только при характерном окончании отчества и достаточном общем балле.
        any_case_token_re = re.compile(r'[А-ЯЁа-яё][А-ЯЁа-яё-]{1,35}')
        patronymic_endings = (
            'ович', 'евич', 'ич', 'овна', 'евна', 'ична', 'инична')
        line_offset = 0
        for line in text.splitlines(keepends=True):
            line_tokens = list(any_case_token_re.finditer(line))
            for i in range(len(line_tokens) - 2):
                selected = line_tokens[i:i+3]
                gaps = [line[selected[j].end():selected[j+1].start()]
                        for j in range(2)]
                if not all(re.fullmatch(r'[\s,.-]{1,8}', gap) for gap in gaps):
                    continue
                if not selected[2].group().casefold().endswith(patronymic_endings):
                    continue
                fio = self._apply_text_corrections(
                    ' '.join(item.group() for item in selected).title())
                if fio in seen:
                    continue
                start = line_offset + selected[0].start()
                end = line_offset + selected[-1].end()
                context = text[max(0, start-80):min(len(text), end+80)]
                score = self._fio_candidate_score(fio, context)
                if score >= 60:
                    seen.add(fio)
                    candidates.append((fio, score))
            line_offset += len(line)

        token_re = re.compile(
            r'[А-ЯЁ][а-яёА-ЯЁ-]{1,35}|(?i:оглы|оглу|кызы|улы|уулу)')
        tokens = list(token_re.finditer(text))
        four_word_spans = []
        for length in (4, 3):
            for i in range(len(tokens) - length + 1):
                selected = tokens[i:i+length]
                if length == 4 and selected[-1].group().casefold() not in FIO_PARTICLES:
                    continue
                if length == 3 and any(i >= start and i+length <= end
                                       for start, end in four_word_spans):
                    continue
                gaps = [text[selected[j].end():selected[j+1].start()]
                        for j in range(length-1)]
                if not all(re.fullmatch(r'[\s,.-]{1,8}', gap) for gap in gaps):
                    continue
                fio = self._apply_text_corrections(
                    ' '.join(item.group() for item in selected).title())
                if fio in seen:
                    continue
                seen.add(fio)
                context = text[max(0,selected[0].start()-80):
                               min(len(text),selected[-1].end()+80)]
                score = self._fio_candidate_score(fio, context)
                third = fio.split()[2].lower()
                patronymic_like = third.endswith(('ович','евич','ич','овна','евна','ична','инична'))
                if (len(fio.split()) == 4 and
                        fio.split()[-1].casefold() in FIO_PARTICLES):
                    patronymic_like = True
                    four_word_spans.append((i, i+length))
                if not patronymic_like and not self.fio_dictionary:
                    score -= 25
                if score >= 50:
                    candidates.append((fio, score))
        candidates.sort(key=lambda x: x[1], reverse=True)
        self.fio_confidence = candidates[0][1] if candidates else 0.0
        return [fio for fio, _ in candidates[:2]]

    def _normalize_room_value(self, value):
        value = str(value or '').strip().upper()
        value = value.replace('№', '').replace('#', '').replace(' ', '')
        value = value.replace('—', '-').replace('–', '-').replace('_', '-')
        suffix = ''
        if re.search(r'\d[А-ЯЁ]$', value):
            suffix, value = value[-1], value[:-1]
        trans = str.maketrans({
            'O':'0','О':'0','Q':'0','D':'0',
            'I':'1','L':'1','|':'1','І':'1','Ӏ':'1',
            'З':'3','Z':'2','S':'5','Б':'6','G':'6','Ч':'4',
            'В':'8','B':'8'
        })
        value = value.translate(trans) + suffix
        value = re.sub(r'[^0-9A-ZА-ЯЁ./-]', '', value)
        value = re.sub(r'-{2,}', '-', value).strip('.-/')
        if len(value) > 18:
            return ''
        return value

    def _room_candidate_score(self, value, context, priority):
        value = self._normalize_room_value(value)
        if not value:
            return 0.0
        score = float(priority)
        low = context.lower()
        strong = ('номер помещения', 'номер помешения', 'номер помещен', '№ помещения', 'помещение №', 'квартира №')
        room_words = ('помещ', 'квартир', 'машино', 'кладов', 'офис', 'гараж', 'паркинг', 'комнат', 'нжп', 'нхп')
        if any(k in low for k in strong):
            score += 30
        elif any(k in low for k in room_words):
            score += 18
        if re.fullmatch(r'\d{1,5}(?:[-/.]\d{1,5})?[A-ZА-ЯЁ]?', value):
            score += 10
        if any(k in low for k in ('площадь', 'кв.м', 'м2', 'м²', 'дата', 'год', 'телефон', 'снилс', 'инн')) and not any(k in low for k in room_words):
            score -= 42
        if value in {'0', '00'}:
            score -= 55
        elif value == '6':
            score -= 12
        if len(re.sub(r'\D','',value)) > 7:
            score -= 25
        return max(0.0, min(100.0, score))

    def extract_kv_only(self, text):
        text = self._normalize_ocr_text(text)
        if not text:
            self.kv_confidence = 0.0
            return None
        value_pat = r'([0-9OОIlІЗБВB]{1,6}(?:\s*[-/.]\s*[0-9OОIlІЗБВB]{1,6})?[А-ЯA-Z]?)'
        patterns = [
            (92, rf'(?:номер|ном[её]р|n[oо]mer)\s+(?:помещен(?:ия|ие|ии)|помешен(?:ия|ие)|помещ\.?|квартир[ыа]?)\s*[:№#.= -]*{value_pat}'),
            (90, rf'(?:помещен(?:ие|ия)|помешение|квартир[аы]|машино-?место|кладов(?:ая|ка)|офис|гараж|паркинг|комната)\s*[№#:=.-]*\s*{value_pat}'),
            (84, rf'(?:№|номер)\s*[:.= -]*{value_pat}'),
            (78, rf'(?:нжп|нхп|м/м|машино-?место)\s*[№#:=.-]*\s*{value_pat}'),
        ]
        found = []
        for priority, pat in patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                value = self._normalize_room_value(m.group(1))
                if not value:
                    continue
                context = text[max(0,m.start()-100):min(len(text),m.end()+100)]
                score = self._room_candidate_score(value, context, priority)
                found.append((value, score, context))
        if not found:
            self.kv_confidence = 0.0
            return None
        counts = {}
        for value, _, _ in found:
            counts[value] = counts.get(value, 0) + 1
        ranked = []
        for value, score, context in found:
            score = min(100.0, score + min(8, (counts[value]-1)*3))
            ranked.append((value, score))
        best = max(ranked, key=lambda x: x[1])
        self.kv_confidence = best[1]
        return best[0]

    @staticmethod
    def _group_line_positions(indices, gap=4):
        if not indices:
            return []
        groups = [[int(indices[0])]]
        for value in indices[1:]:
            value = int(value)
            if value - groups[-1][-1] <= gap:
                groups[-1].append(value)
            else:
                groups.append([value])
        return [int(round(sum(g) / len(g))) for g in groups]

    @staticmethod
    def _header_token(text):
        value = re.sub(r'[^а-яa-z0-9]', '', str(text or '').lower().replace('ё', 'е'))
        value = value.replace('0', 'о').replace('1', 'i')
        return value

    def _anchor_cache_key(self, image):
        try:
            thumb = ImageOps.autocontrast(image.convert('L')).resize((96, 128), Image.Resampling.BILINEAR)
            mode = 'fast' if getattr(self, 'fast_mode', False) else 'deep'
            return hashlib.sha1(thumb.tobytes() + f'{image.width}x{image.height}:{mode}'.encode()).hexdigest()
        except Exception:
            return f'{id(image)}:{getattr(image, "size", None)}'

    def _get_anchor_words(self, image):
        if image is None:
            return []
        key = self._anchor_cache_key(image)
        if key in self._anchor_cache:
            return self._anchor_cache[key]
        try:
            sample = ImageOps.autocontrast(image.convert('L'), cutoff=1)
            max_side = max(sample.size)
            anchor_limit = 1200.0 if getattr(self, 'fast_mode', False) else 2200.0
            scale = min(1.0, anchor_limit / max_side) if max_side else 1.0
            if scale < 0.999:
                sample = sample.resize((max(1, int(sample.width * scale)), max(1, int(sample.height * scale))), Image.Resampling.LANCZOS)
            sx = image.width / sample.width
            sy = image.height / sample.height
            data = pytesseract.image_to_data(
                sample,
                config=('--psm 11 -l rus --oem 3' if getattr(self, 'fast_mode', False)
                        else '--psm 11 -l rus+eng --oem 3'),
                output_type=pytesseract.Output.DICT,
            )
            words = []
            for i, raw in enumerate(data.get('text', [])):
                txt = (raw or '').strip()
                if not txt:
                    continue
                try:
                    conf = float(data.get('conf', ['-1'])[i])
                except Exception:
                    conf = -1.0
                words.append({
                    'text': txt,
                    'token': self._header_token(txt),
                    'conf': conf,
                    'x': int(round(int(data['left'][i]) * sx)),
                    'y': int(round(int(data['top'][i]) * sy)),
                    'w': max(1, int(round(int(data['width'][i]) * sx))),
                    'h': max(1, int(round(int(data['height'][i]) * sy))),
                    'block': int(data.get('block_num', [0])[i] or 0),
                    'par': int(data.get('par_num', [0])[i] or 0),
                    'line': int(data.get('line_num', [0])[i] or 0),
                })
            if len(self._anchor_cache) >= 16:
                self._anchor_cache.pop(next(iter(self._anchor_cache)))
            self._anchor_cache[key] = words
            return words
        except Exception:
            logger.exception('Ошибка динамического поиска подписей')
            if len(self._anchor_cache) >= 16:
                self._anchor_cache.pop(next(iter(self._anchor_cache)))
            self._anchor_cache[key] = []
            return []

    @staticmethod
    def _cluster_words_into_lines(words):
        if not words:
            return []
        ordered = sorted(words, key=lambda d: (d['y'] + d['h'] / 2.0, d['x']))
        heights = sorted(max(1, d['h']) for d in ordered)
        median_h = heights[len(heights)//2] if heights else 20
        tolerance = max(10, median_h * 0.70)
        lines = []
        for word in ordered:
            cy = word['y'] + word['h'] / 2.0
            target = None
            best_delta = None
            for line in lines[-8:]:
                delta = abs(cy - line['cy'])
                if delta <= tolerance and (best_delta is None or delta < best_delta):
                    target = line
                    best_delta = delta
            if target is None:
                lines.append({'cy': cy, 'words': [word]})
            else:
                target['words'].append(word)
                target['cy'] = sum(w['y'] + w['h']/2.0 for w in target['words']) / len(target['words'])
        result = []
        for line in lines:
            ws = sorted(line['words'], key=lambda d: d['x'])
            x1 = min(w['x'] for w in ws); y1 = min(w['y'] for w in ws)
            x2 = max(w['x'] + w['w'] for w in ws); y2 = max(w['y'] + w['h'] for w in ws)
            result.append({'words': ws, 'bbox': (x1, y1, x2, y2), 'text': ' '.join(w['text'] for w in ws)})
        return sorted(result, key=lambda d: d['bbox'][1])

    def _owner_field_fio(self, image):
        lines = self._cluster_words_into_lines(self._get_anchor_words(image))
        for index, line in enumerate(lines):
            words = line['words']
            if line['bbox'][1] > image.height * .70:
                break
            if not words:
                continue
            tokens = [word['token'] for word in words]
            owner_label = words[0]['token'] in ('собственник', 'собственники', 'владелец')
            participant_label = (
                words[0]['token'].startswith('сведен') and
                any(token.startswith('лиц') for token in tokens[:10]) and
                any(token.startswith('голосован') for token in tokens[:14])
            )
            if not (owner_label or participant_label):
                continue
            colon = next((i for i, word in enumerate(words) if ':' in word['text']), 0)
            field_words = list(words[colon+1:])
            bottom = line['bbox'][3]
            line_height = max(18, bottom-line['bbox'][1])
            for other in lines[index+1:index+4]:
                if other['bbox'][1]-bottom > line_height*1.8:
                    break
                tokens = [word['token'] for word in other['words']]
                if (any(':' in word['text'] for word in other['words'])
                        or any(t.startswith(('номер','доля','общая','снилс','представител',
                                             'документ','вопрос','повестк','кадастр')) for t in tokens)):
                    break
                field_words.extend(other['words'])
                bottom = other['bbox'][3]
            text = ' '.join(word['text'] for word in field_words)
            old = self.fio_confidence
            try:
                fios = self.extract_all_fios(text)
                parsed = self.fio_confidence
            finally:
                self.fio_confidence = old
            name_parts = {self._header_token(part) for fio in fios for part in fio.split()}
            name_words = [word for word in field_words if word['token'] in name_parts]
            region_words = name_words or field_words
            roi = None
            if region_words:
                roi = (max(0,min(word['x'] for word in region_words)-6),
                       max(0,min(word['y'] for word in region_words)-5),
                       min(image.width,max(word['x']+word['w'] for word in region_words)+6),
                       min(image.height,max(word['y']+word['h'] for word in region_words)+5))
            confidence = min([max(0.,word['conf']) for word in name_words], default=0.)
            return {'fios': fios, 'conf': min(96., max(parsed, confidence)),
                    'text': text, 'roi': roi, 'variant': 'owner-field'}
        return None

    def _best_dynamic_fio_result(self, image):
        owner = self._owner_field_fio(image)
        if owner is not None:
            return owner
        empty = {'fios': [], 'conf': 0.0, 'text': '', 'variant': 'anchor-not-found', 'roi': None}
        words = self._get_anchor_words(image)
        if not words:
            return empty
        h, w = image.height, image.width
        lines = self._cluster_words_into_lines(words)
        label_tokens = ('фио', 'фамил', 'отчеств', 'собствен', 'владел', 'представител')
        candidates = []

        for li, line in enumerate(lines):
            tokens = [x['token'] for x in line['words']]
            joined = ''.join(tokens)
            explicit_fio = any(t.startswith('фио') for t in tokens) or 'фио' in joined
            long_label = any(t.startswith('фамил') for t in tokens) and any(t.startswith('имя') for t in tokens)
            owner_only = (any(t.startswith(('собствен', 'владел')) for t in tokens) and len(tokens) <= 4 and not any('помещ' in t or 'квартир' in t for t in tokens))
            if not (explicit_fio or long_label or owner_only):
                continue

            label_words = [x for x in line['words'] if any(x['token'].startswith(k) for k in label_tokens)]
            if not label_words:
                label_words = line['words'][:2]
            label_right = max(x['x'] + x['w'] for x in label_words)
            lx1, ly1, lx2, ly2 = line['bbox']
            line_h = max(18, ly2 - ly1)

            nearby = [x for x in line['words'] if x['x'] >= label_right - max(3, int(w*0.002))]
            for nxt in lines[li+1:li+4]:
                nx1, ny1, nx2, ny2 = nxt['bbox']
                if ny1 - ly2 > max(line_h * 3.2, h * 0.045):
                    break
                if nx2 < lx1 - w*0.04:
                    continue
                nearby.extend([x for x in nxt['words'] if x['x'] >= max(0, lx1 - int(w*0.04))])

            near_text = ' '.join(x['text'] for x in sorted(nearby, key=lambda d: (d['y'], d['x'])))
            saved_conf = self.fio_confidence
            fios = self.extract_all_fios(near_text)
            parsed_conf = self.fio_confidence
            self.fio_confidence = saved_conf
            if fios:
                name_words = [x for x in nearby if any(part.lower().strip('.,:;()') == x['text'].lower().strip('.,:;()') for part in fios[0].split())]
                box_words = name_words or nearby
                if box_words:
                    rx1 = max(0, min(x['x'] for x in box_words) - 10)
                    ry1 = max(0, min(x['y'] for x in box_words) - 8)
                    rx2 = min(w, max(x['x']+x['w'] for x in box_words) + 15)
                    ry2 = min(h, max(x['y']+x['h'] for x in box_words) + 10)
                else:
                    rx1, ry1, rx2, ry2 = max(0,label_right), max(0,ly1-line_h), min(w,lx2+int(w*.5)), min(h,ly2+line_h*3)
                anchor_quality = 7.0 if explicit_fio else 4.0
                avg_word_conf = sum(max(0.0, x['conf']) for x in nearby) / max(1, len(nearby))
                conf = min(96.0, max(parsed_conf, 72.0 + avg_word_conf*0.18) + anchor_quality)
                candidates.append({'fios': fios, 'conf': conf, 'text': near_text,
                                   'variant': 'anchor-data', 'roi': (rx1, ry1, rx2, ry2)})
                continue

            rx1 = max(0, min(label_right + 3, int(w*0.88)))
            ry1 = max(0, ly1 - int(line_h*0.55))
            rx2 = min(w, max(rx1 + int(w*0.30), int(w*0.96)))
            ry2 = min(h, ly2 + int(line_h*3.0))
            if rx2 - rx1 < 40 or ry2 - ry1 < 20:
                continue
            crop = image.crop((rx1, ry1, rx2, ry2))
            scale = min(2.2, max(1.25, 1500.0 / max(crop.size)))
            crop = ImageOps.autocontrast(crop.convert('L')).resize(
                (max(1, int(crop.width*scale)), max(1, int(crop.height*scale))), Image.Resampling.LANCZOS)
            for psm in ('7', '6'):
                try:
                    txt = pytesseract.image_to_string(crop, config=f'--psm {psm} -l rus --oem 3')
                    saved_conf = self.fio_confidence
                    fios = self.extract_all_fios(txt)
                    parsed_conf = self.fio_confidence
                    self.fio_confidence = saved_conf
                    if fios:
                        candidates.append({'fios': fios, 'conf': min(94.0, max(82.0, parsed_conf + 6.0)),
                                           'text': txt, 'variant': f'anchor-roi/psm{psm}',
                                           'roi': (rx1, ry1, rx2, ry2)})
                        break
                except Exception:
                    logger.debug('FIO anchor ROI OCR failed', exc_info=True)

        if not candidates:
            return empty
        candidates.sort(key=lambda d: (d['conf'], bool(d['fios'])), reverse=True)
        best = candidates[0]
        logger.info('DynamicFIO selected=%s conf=%.1f variant=%s roi=%s', best['fios'][0], best['conf'], best['variant'], best['roi'])
        return best

    def _detect_room_table_roi(self, image):
        if image is None or not OPENCV_AVAILABLE or not NUMPY_AVAILABLE:
            return None, 0.0, 'table-unavailable'
        try:
            gray = np.array(ImageOps.autocontrast(image.convert('L'), cutoff=1))
            h, w = gray.shape[:2]
            words = self._get_anchor_words(image)
            header = None
            for a in words:
                tok = a['token']
                is_num = tok.startswith(('номер', 'номep', 'nomer')) or ('номер' in tok) or a['text'].strip() in ('№', '#')
                if not is_num:
                    continue
                for b in words:
                    bt = b['token']
                    if not (bt.startswith(('помещ', 'помеш', 'помещен', 'квартир')) or 'помещ' in bt or 'помеш' in bt or 'квартир' in bt):
                        continue
                    if abs((a['y'] + a['h']//2) - (b['y'] + b['h']//2)) > max(55, int(h*0.025)):
                        continue
                    if b['x'] < a['x'] - int(w*0.03) or b['x'] > a['x'] + int(w*0.28):
                        continue
                    x1 = min(a['x'], b['x']); x2 = max(a['x']+a['w'], b['x']+b['w'])
                    y1 = min(a['y'], b['y']); y2 = max(a['y']+a['h'], b['y']+b['h'])
                    header = (x1, y1, x2, y2)
                    break
                if header:
                    break
            if not header:
                return None, 0.0, 'header-not-found'

            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            vert_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(18, h // 70)))
            hori_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(25, w // 35), 1))
            vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vert_kernel)
            horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, hori_kernel)

            vproj = (vertical > 0).sum(axis=0)
            hproj = (horizontal > 0).sum(axis=1)
            xs = self._group_line_positions(np.where(vproj > max(20, h * 0.035))[0].tolist(), gap=max(2, w//900))
            ys = self._group_line_positions(np.where(hproj > max(30, w * 0.12))[0].tolist(), gap=max(2, h//1200))

            hx1, hy1, hx2, hy2 = header
            center_x = (hx1 + hx2) / 2.0
            lefts = [x for x in xs if x < center_x - max(5, (hx2-hx1)*0.05)]
            rights = [x for x in xs if x > center_x + max(5, (hx2-hx1)*0.05)]
            if not lefts or not rights:
                return None, 0.0, 'column-lines-not-found'
            left = max(lefts); right = min(rights)
            if right - left < max(40, w * 0.035) or right - left > w * 0.45:
                return None, 0.0, 'column-width-invalid'

            below = [y for y in ys if y > hy2 + max(4, h * 0.002)]
            if not below:
                return None, 0.0, 'row-line-not-found'
            top = below[0]
            row_candidates = [y for y in ys if y > top + max(12, h * 0.008)]
            if row_candidates:
                bottom = row_candidates[0]
            else:
                bottom = min(h, top + max(45, int(h * 0.045)))
            if bottom - top < 18:
                return None, 0.0, 'row-height-invalid'

            pad_x = max(5, int((right-left) * 0.025))
            pad_y = max(4, int((bottom-top) * 0.10))
            roi = (
                max(0, left + pad_x), max(0, top + pad_y),
                min(w, right - pad_x), min(h, bottom - pad_y),
            )
            if roi[2] <= roi[0] or roi[3] <= roi[1]:
                return None, 0.0, 'roi-invalid'
            logger.info('RoomTable ROI=%s header=%s lines_x=%s lines_y=%s', roi, header, xs[:20], ys[:30])
            return roi, 98.0, 'header+grid'
        except Exception:
            logger.exception('Ошибка поиска ячейки номера помещения')
            return None, 0.0, 'table-error'

    def _detect_room_anchor_roi(self, image):
        words = self._get_anchor_words(image)
        if not words:
            return None, 0.0, 'room-anchor-not-found'
        h, w = image.height, image.width
        pairs = []
        for a in words:
            at = a['token']
            is_num = at.startswith(('номер', 'nomer')) or 'номер' in at or a['text'].strip() in ('№', '#')
            if not is_num:
                continue
            for b in words:
                bt = b['token']
                if not (bt.startswith(('помещ', 'помеш', 'квартир')) or 'помещ' in bt or 'квартир' in bt):
                    continue
                acy = a['y'] + a['h']/2.0; bcy = b['y'] + b['h']/2.0
                if abs(acy-bcy) > max(60, h*0.03):
                    continue
                if b['x'] < a['x'] - w*0.05 or b['x'] > a['x'] + w*0.35:
                    continue
                x1=min(a['x'],b['x']); y1=min(a['y'],b['y'])
                x2=max(a['x']+a['w'],b['x']+b['w']); y2=max(a['y']+a['h'],b['y']+b['h'])
                pairs.append((x1,y1,x2,y2,a,b))
        if not pairs:
            return None, 0.0, 'room-anchor-not-found'
        pairs.sort(key=lambda q: (max(0,q[4].get('conf',0))+max(0,q[5].get('conf',0)), -(q[2]-q[0])), reverse=True)
        x1,y1,x2,y2,_,_=pairs[0]
        center=(x1+x2)/2.0
        width=max(int((x2-x1)*1.65), int(w*0.14))
        rx1=max(0,int(center-width/2)); rx2=min(w,int(center+width/2))
        ry1=max(0,y2 + max(4,int(h*0.003)))
        ry2=min(h,ry1 + max(int((y2-y1)*3.4), int(h*0.07)))
        if rx2-rx1 < 40 or ry2-ry1 < 20:
            return None, 0.0, 'room-anchor-invalid'
        return (rx1,ry1,rx2,ry2), 78.0, 'header-neighborhood'

    def _best_room_anchor_data_result(self, image):
        words = self._get_anchor_words(image)
        if not words:
            return {'kv': None, 'conf': 0.0, 'text': '', 'variant': 'anchor-data-none', 'roi': None, 'engine': 'RoomAnchorOCR'}
        h, w = image.height, image.width
        inline_best = None
        for marker in words:
            raw_marker = str(marker.get('text', '')).strip()
            match = re.fullmatch(
                r'(?:№|#|N[oо]?)\s*([0-9OОIlІЗБВB]{1,6}(?:[-/.][0-9OОIlІЗБВB]{1,6})?[A-ZА-ЯЁ]?)',
                raw_marker, re.I)
            if not match:
                continue
            value = self._normalize_room_value(match.group(1))
            if not value or value in ('0', '00') or not re.fullmatch(
                    r'\d{1,5}(?:[-/.]\d{1,5})?[A-ZА-ЯЁ]?', value):
                continue
            cy = marker['y'] + marker['h'] / 2.0
            nearby_labels = [word for word in words if
                abs((word['y'] + word['h'] / 2.0) - cy) <= max(45, h * .018) and
                abs(word['x'] - marker['x']) <= w * .34 and
                (word['token'].startswith(('помещ', 'помеш', 'квартир')) or
                 'помещ' in word['token'] or 'квартир' in word['token'])]
            if not nearby_labels:
                continue
            ocr_conf = max(0.0, float(marker.get('conf', 0) or 0))
            score = ocr_conf + 25.0
            roi = (max(0, marker['x'] - 12), max(0, marker['y'] - 10),
                   min(w, marker['x'] + marker['w'] + 12),
                   min(h, marker['y'] + marker['h'] + 10))
            candidate = (score, value, ocr_conf, raw_marker, roi)
            if inline_best is None or candidate[0] > inline_best[0]:
                inline_best = candidate
        headers = []
        for a in words:
            at = a['token']
            if not (at.startswith(('номер','nomer')) or 'номер' in at or a['text'].strip() in ('№','#')):
                continue
            for b in words:
                bt = b['token']
                if not (bt.startswith(('помещ','помеш','квартир')) or 'помещ' in bt or 'квартир' in bt):
                    continue
                if abs((a['y']+a['h']/2)-(b['y']+b['h']/2)) > max(60,h*.03):
                    continue
                if b['x'] < a['x']-w*.20 or b['x'] > a['x']+w*.35:
                    continue
                x1=min(a['x'],b['x']); y1=min(a['y'],b['y']); x2=max(a['x']+a['w'],b['x']+b['w']); y2=max(a['y']+a['h'],b['y']+b['h'])
                headers.append((x1,y1,x2,y2,a,b))
        if not headers and inline_best is None:
            return {'kv': None, 'conf': 0.0, 'text': '', 'variant': 'anchor-data-no-header', 'roi': None, 'engine': 'RoomAnchorOCR'}
        best=inline_best
        for x1,y1,x2,y2,a,b in headers:
            cx=(x1+x2)/2.0; maxdy=max(90,h*.10); maxdx=max((x2-x1)*1.3,w*.14)
            for word in words:
                if word is a or word is b:
                    continue
                wy=word['y']+word['h']/2.0; wx=word['x']+word['w']/2.0
                dy=wy-y2
                header_cy=(y1+y2)/2.0
                same_row=(abs(wy-header_cy) <= max(45,h*.018) and
                          word['x'] >= min(a['x'],b['x'])-4 and
                          word['x'] <= x2+w*.22)
                if not same_row and (dy < -4 or dy > maxdy):
                    continue
                dx=abs(wx-cx)
                if dx>maxdx:
                    continue
                raw=word['text'].strip()
                if not re.fullmatch(r'[0-9OОIlІЗБВB]{1,6}(?:[-/.][0-9OОIlІЗБВB]{1,6})?[A-ZА-ЯЁ]?', raw, re.I):
                    continue
                value=self._normalize_room_value(raw)
                if not value or not re.fullmatch(r'\d{1,5}(?:[-/.]\d{1,5})?[A-ZА-ЯЁ]?', value):
                    continue
                ocr_conf=max(0.0,float(word.get('conf',0)))
                proximity=max(0.0,1.0-dx/maxdx)*18.0 + max(0.0,1.0-max(0,dy)/maxdy)*12.0
                score=ocr_conf+proximity+(18.0 if same_row else 0.0)
                roi=(max(0,word['x']-12),max(0,word['y']-10),min(w,word['x']+word['w']+12),min(h,word['y']+word['h']+10))
                cand=(score,value,ocr_conf,raw,roi)
                if best is None or cand[0]>best[0]: best=cand
        if best is None:
            return {'kv': None, 'conf': 0.0, 'text': '', 'variant': 'anchor-data-no-value', 'roi': None, 'engine': 'RoomAnchorOCR'}
        _,value,ocr_conf,raw,roi=best
        conf=min(92.0,max(80.0,68.0+ocr_conf*.22))
        return {'kv':value,'conf':conf,'text':raw,'variant':'ANCHOR-DATA','roi':roi,'engine':'RoomAnchorOCR'}

    def _best_side_cell_room_result(self, image):
        words = self._get_anchor_words(image)
        if not words:
            return None
        h, w = image.height, image.width
        best = None
        for marker in words:
            marker_token = marker.get('token', '')
            is_number_marker = (
                marker_token.startswith(('номер', 'nomer')) or
                'номер' in marker_token or marker.get('text', '').strip() in ('№', '#')
            )
            if not is_number_marker:
                continue
            for label in words:
                label_token = label.get('token', '')
                if not (label_token.startswith(('квартир', 'помещ', 'помеш')) or
                        'квартир' in label_token or 'помещ' in label_token or
                        'помеш' in label_token):
                    continue
                marker_cy = marker['y'] + marker['h']/2.0
                label_cy = label['y'] + label['h']/2.0
                if abs(marker_cy-label_cy) > max(65, h*.035):
                    continue
                if label['x'] < marker['x']-w*.03 or label['x'] > marker['x']+w*.22:
                    continue
                label_right = max(marker['x']+marker['w'], label['x']+label['w'])
                row_center = (marker_cy+label_cy)/2.0
                for value_word in words:
                    value_cy = value_word['y'] + value_word['h']/2.0
                    if abs(value_cy-row_center) > max(45, h*.022):
                        continue
                    if value_word['x'] <= label_right + max(4, w*.002):
                        continue
                    if value_word['x'] > label_right + w*.24:
                        continue
                    raw = value_word.get('text', '').strip('.,:;()[]{}')
                    if not re.fullmatch(
                            r'[0-9OОIlІЗБВB]{1,6}(?:[-/.][0-9OОIlІЗБВB]{1,6})?[A-ZА-ЯЁ]?',
                            raw, re.I):
                        continue
                    value = self._normalize_room_value(raw)
                    if (not value or value in {'0', '00'} or
                            not re.fullmatch(r'\d{1,5}(?:[-/.]\d{1,5})?[A-ZА-ЯЁ]?', value)):
                        continue
                    ocr_conf = max(0.0, float(value_word.get('conf', 0) or 0))
                    horizontal_gap = value_word['x']-label_right
                    score = ocr_conf + max(0.0, 20.0-horizontal_gap/max(1, w*.012))
                    roi = (max(0, value_word['x']-16), max(0, value_word['y']-12),
                           min(w, value_word['x']+value_word['w']+16),
                           min(h, value_word['y']+value_word['h']+12))
                    candidate = (score, value, ocr_conf, raw, roi)
                    if best is None or candidate[0] > best[0]:
                        best = candidate
        if best is None:
            return None
        _, value, ocr_conf, raw, roi = best
        conf = min(97.0, max(90.0, 82.0+ocr_conf*.15))
        logger.info('RoomSideCell selected=%s conf=%.1f roi=%s', value, conf, roi)
        return {'kv': value, 'conf': conf, 'text': raw,
                'variant': 'SIDE-CELL', 'roi': roi, 'engine': 'RoomAnchorOCR'}

    def _best_table_room_result(self, image):
        side_cell = self._best_side_cell_room_result(image)
        if side_cell and side_cell.get('kv'):
            return side_cell
        roi, geo_conf, reason = self._detect_room_table_roi(image)
        engine = 'TableOCR'
        if not roi:
            direct = self._best_room_anchor_data_result(image)
            if direct.get('kv'):
                return direct
            roi, geo_conf, reason = self._detect_room_anchor_roi(image)
            engine = 'RoomAnchorOCR'
        if not roi:
            return {'kv': None, 'conf': 0.0, 'text': '', 'variant': reason, 'roi': None, 'engine': engine}
        result = self._best_room_ocr_result(image, roi)
        result['roi'] = roi
        result['engine'] = engine
        if result.get('kv'):
            if engine == 'TableOCR':
                result['conf'] = min(96.0, max(result.get('conf', 0.0), 84.0 + geo_conf * 0.06))
                result['variant'] = 'TABLE/' + result.get('variant', 'ocr')
            else:
                result['conf'] = min(89.0, max(result.get('conf', 0.0), 76.0 + geo_conf * 0.08))
                result['variant'] = 'ANCHOR/' + result.get('variant', 'ocr')
        return result

    def _best_room_ocr_result(self, image, roi=None):
        crop = image.crop(roi) if roi else image
        cache_key = None
        if getattr(self, 'cache_enabled', False):
            try:
                thumb = ImageOps.autocontrast(crop.convert('L')).resize((64, 64), Image.Resampling.BILINEAR)
                digest = hashlib.sha1(thumb.tobytes()).hexdigest()
                cache_key = f"room:{digest}:{crop.size}:{roi}:{bool(getattr(self, 'fast_mode', False))}"
                cached = self.ocr_cache.get(cache_key)
                if cached is not None:
                    return dict(cached)
            except Exception:
                cache_key = None
        if crop.width < 8 or crop.height < 8:
            return {'kv': None, 'conf': 0.0, 'text': '', 'variant': 'none'}
        max_side = max(crop.size)
        scale = min(3.5, max(2.0, 2200.0 / max_side))
        crop = crop.resize((max(1, int(crop.width*scale)), max(1, int(crop.height*scale))), Image.Resampling.LANCZOS)
        gray = ImageOps.autocontrast(crop.convert('L'), cutoff=1)

        variants = [('gray', gray)]
        if OPENCV_AVAILABLE and NUMPY_AVAILABLE:
            try:
                arr = np.array(gray)
                _, otsu = cv2.threshold(arr, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                variants.append(('otsu', Image.fromarray(otsu)))
            except Exception:
                pass

        quick_configs = [
            ('digits7', '--psm 7 -l eng --oem 3 -c tessedit_char_whitelist=0123456789-/.'),
            ('digits13', '--psm 13 -l eng --oem 3 -c tessedit_char_whitelist=0123456789-/.'),
        ]
        deep_configs = [
            ('psm7', '--psm 7 -l rus+eng --oem 3'),
            ('psm6', '--psm 6 -l rus+eng --oem 3'),
            ('alnum7', '--psm 7 -l rus+eng --oem 3 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZАБВГДЕЖЗИКЛМНОПРСТУФХЦЧШЩЭЮЯ-/.'),
        ]

        votes = {}
        def run_pass(pass_variants, configs):
            for vname, variant in pass_variants:
                for cname, config in configs:
                    try:
                        data = pytesseract.image_to_data(variant, config=config, output_type=pytesseract.Output.DICT)
                        words, confs = [], []
                        for word, conf in zip(data.get('text', []), data.get('conf', [])):
                            word = (word or '').strip()
                            if not word:
                                continue
                            words.append(word)
                            try:
                                c = float(conf)
                                if c >= 0: confs.append(c)
                            except Exception:
                                pass
                        txt = ' '.join(words)
                        ocr_conf = sum(confs)/len(confs) if confs else 0.0
                        candidates = []
                        direct = self.extract_kv_only(txt)
                        if direct:
                            candidates.append(direct)
                        for token in re.findall(r'[0-9OОIlІЗБВB]{1,6}(?:[-/.][0-9OОIlІЗБВB]{1,6})?[A-ZА-ЯЁ]?', txt, re.I):
                            cand = self._normalize_room_value(token)
                            if cand and re.fullmatch(r'\d{1,5}(?:[-/.]\d{1,5})?[A-ZА-ЯЁ]?', cand):
                                candidates.append(cand)
                        for cand in dict.fromkeys(candidates):
                            weight = 1.45 if cname.startswith('digits') else 1.0
                            if re.fullmatch(r'\d{1,5}(?:[-/.]\d{1,5})?', cand):
                                weight += 0.25
                            entry = votes.setdefault(cand, {'score':0.0,'count':0,'max_conf':0.0,'sources':[],'text':txt})
                            entry['score'] += weight * (max(25.0, ocr_conf)/100.0)
                            entry['count'] += 1
                            entry['max_conf'] = max(entry['max_conf'], ocr_conf)
                            entry['sources'].append(f'{vname}/{cname}')
                    except Exception:
                        logger.debug('Room OCR candidate failed', exc_info=True)

        def select_result():
            if not votes:
                return None
            ranked = sorted(votes.items(), key=lambda kv: (kv[1]['score'] + min(2.5, kv[1]['count']*0.32), kv[1]['max_conf']), reverse=True)
            value, info = ranked[0]
            runner = ranked[1][1]['score'] if len(ranked) > 1 else 0.0
            margin = max(0.0, info['score'] - runner)
            conf = min(97.0, 52.0 + info['count']*5.0 + info['max_conf']*0.28 + margin*5.0)
            if re.search(r'[A-ZА-ЯЁ]$', value) and info['count'] < 2:
                conf = min(conf, 72.0)
            return value, info, conf, ranked

        run_pass(variants, quick_configs)
        selected = select_result()
        if selected:
            value, info, conf, ranked = selected
            pure_numeric = bool(re.fullmatch(r'\d{1,5}(?:[-/.]\d{1,5})?', value))
            runner_score = ranked[1][1]['score'] if len(ranked) > 1 else 0.0
            if pure_numeric and info['count'] >= 2 and conf >= 82 and (info['score'] - runner_score >= 0.30 or len(ranked) == 1):
                logger.info('RoomOCR FAST selected=%s conf=%.1f votes=%s', value, conf, info['count'])
                result = {'kv': value, 'conf': conf, 'text': info.get('text',''), 'variant': 'fast-vote:' + ','.join(info['sources'][:3])}
                if cache_key:
                    self.ocr_cache[cache_key] = dict(result)
                return result

        deep_variants = list(variants)
        if OPENCV_AVAILABLE and NUMPY_AVAILABLE:
            try:
                arr = np.array(gray)
                den = cv2.fastNlMeansDenoising(arr, None, 5, 7, 21)
                adaptive = cv2.adaptiveThreshold(den, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 11)
                deep_variants.append(('adaptive', Image.fromarray(adaptive)))
            except Exception:
                pass
        run_pass(deep_variants, deep_configs)
        selected = select_result()
        if not selected:
            result = {'kv': None, 'conf': 0.0, 'text': '', 'variant': 'none'}
            if cache_key:
                self.ocr_cache[cache_key] = dict(result)
            return result
        value, info, conf, _ = selected
        logger.info('RoomOCR DEEP selected=%s conf=%.1f votes=%s', value, conf, info['count'])
        result = {'kv': value, 'conf': conf, 'text': info.get('text',''), 'variant': 'deep-vote:' + ','.join(info['sources'][:3])}
        if cache_key:
            if len(self.ocr_cache) >= 96:
                for old_key in list(self.ocr_cache)[:16]:
                    self.ocr_cache.pop(old_key, None)
            self.ocr_cache[cache_key] = dict(result)
        return result

    def _confidence_color(self, value):
        c = Theme.colors
        if value >= 90:
            return c['success']
        if value >= OCR_REVIEW_THRESHOLD:
            return c['warning']
        return c['error']

    def _update_confidence_ui(self):
        c = Theme.colors
        if hasattr(self, 'fio_conf_label'):
            self.fio_conf_label.config(text=f"{self.fio_confidence:.0f}%", fg=self._confidence_color(self.fio_confidence))
        if hasattr(self, 'kv_conf_label'):
            self.kv_conf_label.config(text=f"{self.kv_confidence:.0f}%", fg=self._confidence_color(self.kv_confidence))
        if hasattr(self, 'engine_label'):
            self.engine_label.config(text=f"ФИО: {self.fio_engine_name} | №: {self.kv_engine_name}")
        if hasattr(self, 'quality_badge'):
            score = min(self.fio_confidence, self.kv_confidence)
            if score >= 90:
                self.quality_badge.config(text="НАДЁЖНО", bg=c['success'])
            elif score >= OCR_REVIEW_THRESHOLD:
                self.quality_badge.config(text="ПРОВЕРИТЬ", bg=c['warning'])
            else:
                self.quality_badge.config(text="РУЧНАЯ ПРОВЕРКА", bg=c['error'])

    def _apply_recognized(self, fios, kv):
        for i, entry in enumerate(self.fio_entries):
            entry.delete(0, 'end')
            if i < len(fios):
                entry.insert(0, fios[i])
        self.kv_entry.delete(0, 'end')
        self.kv_entry.insert(0, kv if kv else "0")
        self.count_label.config(text=f"ФИО: {len(fios)}")
        if hasattr(self, 'toggle_extra_fios'):
            self.toggle_extra_fios(force=len(fios) > 2)
        self.recognized_fios = fios
        self.recognized_kv = kv
        self._update_confidence_ui()
        self.update_image()

    def _preprocess_variants(self, image):
        gray = image.convert('L') if image.mode != 'L' else image.copy()
        auto = ImageOps.autocontrast(gray, cutoff=1)
        variants = [('autocontrast', auto), ('gray', gray)]
        if self.fast_mode:
            if OPENCV_AVAILABLE and NUMPY_AVAILABLE:
                try:
                    arr = np.array(auto)
                    _, otsu = cv2.threshold(arr, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    variants.append(('otsu', Image.fromarray(otsu)))
                except Exception:
                    logger.debug("OpenCV fast preprocessing failed", exc_info=True)
            return variants
        strong = ImageEnhance.Contrast(auto).enhance(1.55)
        sharp = strong.filter(ImageFilter.UnsharpMask(radius=1.2, percent=135, threshold=3))
        variants.extend([('contrast', strong), ('sharp', sharp)])
        if OPENCV_AVAILABLE and NUMPY_AVAILABLE:
            try:
                arr = np.array(auto)
                denoise = cv2.fastNlMeansDenoising(arr, None, 7, 7, 21)
                _, otsu = cv2.threshold(denoise, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                adaptive = cv2.adaptiveThreshold(denoise, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                                 cv2.THRESH_BINARY, 35, 13)
                variants.extend([('denoise', Image.fromarray(denoise)), ('otsu', Image.fromarray(otsu)),
                                 ('adaptive', Image.fromarray(adaptive))])
            except Exception:
                logger.debug("OpenCV preprocessing failed", exc_info=True)
        return variants

    def _tesseract_candidate(self, image, psm='6'):
        config = f'--psm {psm} -l rus --oem 3 -c preserve_interword_spaces=1'
        try:
            data = pytesseract.image_to_data(image, config=config, output_type=pytesseract.Output.DICT)
            lines, confs = {}, []
            count = len(data.get('text', []))
            for i in range(count):
                word = (data['text'][i] or '').strip()
                try:
                    conf = float(data['conf'][i])
                except (TypeError, ValueError):
                    conf = -1
                if not word:
                    continue
                key = (data.get('block_num', [0]*count)[i], data.get('par_num', [0]*count)[i], data.get('line_num', [0]*count)[i])
                lines.setdefault(key, []).append(word)
                if conf >= 0:
                    confs.append(conf)
            text = '\n'.join(' '.join(words) for words in lines.values())
            avg = float(np.median(confs)) if confs and NUMPY_AVAILABLE else (sum(confs) / len(confs) if confs else 0.0)
            return text, avg, data
        except Exception:
            logger.exception("Ошибка Tesseract")
            return '', 0.0, {}

    def _score_ocr_candidate(self, text, ocr_conf):
        if not text.strip():
            return -1, [], None, 0.0, 0.0
        old_fio, old_kv = self.fio_confidence, self.kv_confidence
        fios = self.extract_all_fios(text)
        fio_conf = self.fio_confidence
        kv = self.extract_kv_only(text)
        kv_conf = self.kv_confidence
        score = ocr_conf * 0.40 + fio_conf * 0.36 + kv_conf * 0.24
        if fios:
            score += 7
        if kv:
            score += 5
        self.fio_confidence, self.kv_confidence = old_fio, old_kv
        return score, fios, kv, fio_conf, kv_conf

    def _best_tesseract_result(self, image, roi=None):
        crop = image.crop(roi) if roi else image
        cache_key = None
        if getattr(self, 'cache_enabled', False):
            try:
                thumb = ImageOps.autocontrast(crop.convert('L')).resize((64, 64), Image.Resampling.BILINEAR)
                digest = hashlib.sha1(thumb.tobytes()).hexdigest()
                cache_key = f"best:{digest}:{crop.size}:{roi}:{bool(getattr(self, 'fast_mode', False))}"
                cached = self.ocr_cache.get(cache_key)
                if cached is not None:
                    return dict(cached)
            except Exception:
                cache_key = None
        empty = {'text':'','fios':[],'kv':None,'fio_conf':0,'kv_conf':0,'score':-1,'variant':'none','engine':'Tesseract',
                 'fio_variant':'none','kv_variant':'none','fio_engine':'Tesseract','kv_engine':'Tesseract'}
        if crop.width < 10 or crop.height < 10:
            return empty
        max_side = max(crop.size)
        if max_side < 1700:
            scale = min(2.2, 1700 / max_side)
            crop = crop.resize((max(1,int(crop.width*scale)), max(1,int(crop.height*scale))), Image.Resampling.LANCZOS)

        gray = crop.convert('L') if crop.mode != 'L' else crop.copy()
        quick = ImageOps.autocontrast(gray, cutoff=1)
        txt, conf, _ = self._tesseract_candidate(quick, '6')
        score, fios, kv, fio_conf, kv_conf = self._score_ocr_candidate(txt, conf)
        quick_result = {'text':txt,'fios':fios,'kv':kv,'fio_conf':fio_conf,'kv_conf':kv_conf,
                        'score':score,'variant':'autocontrast/psm6','engine':'Tesseract',
                        'fio_ocr_conf':float(conf or 0.0),
                        'fio_variant':'autocontrast/psm6','kv_variant':'autocontrast/psm6',
                        'fio_engine':'Tesseract','kv_engine':'Tesseract'}
        if self.fast_mode and fios and fio_conf >= 85:
            if cache_key:
                self.ocr_cache[cache_key] = dict(quick_result)
            return quick_result

        best_overall = quick_result
        best_fio = {'fios':fios,'conf':fio_conf,'raw_conf':float(conf or 0.0),
                    'metric':fio_conf*0.72+conf*0.28+(8 if fios else 0),
                    'variant':'autocontrast/psm6','text':txt} if fios else None
        best_kv = {'kv':kv,'conf':kv_conf,'metric':kv_conf*0.78+conf*0.22+(8 if kv else 0),'variant':'autocontrast/psm6','text':txt} if kv else None
        psm_modes = ('11',) if self.fast_mode else ('6','4','11')
        for name, variant in self._preprocess_variants(crop):
            for psm in psm_modes:
                if name == 'autocontrast' and psm == '6':
                    continue
                txt, conf, _ = self._tesseract_candidate(variant, psm)
                score, fios, kv, fio_conf, kv_conf = self._score_ocr_candidate(txt, conf)
                label = f'{name}/psm{psm}'
                cand = {'text':txt,'fios':fios,'kv':kv,'fio_conf':fio_conf,'kv_conf':kv_conf,'score':score,'variant':label,'engine':'Tesseract'}
                if score > best_overall['score']:
                    best_overall = cand
                fio_metric = fio_conf*0.72 + conf*0.28 + (8 if fios else 0)
                kv_metric = kv_conf*0.78 + conf*0.22 + (8 if kv else 0)
                if fios and (best_fio is None or fio_metric > best_fio['metric']):
                    best_fio = {'fios':fios,'conf':fio_conf,'raw_conf':float(conf or 0.0),
                                'metric':fio_metric,'variant':label,'text':txt}
                if kv and (best_kv is None or kv_metric > best_kv['metric']):
                    best_kv = {'kv':kv,'conf':kv_conf,'metric':kv_metric,'variant':label,'text':txt}
                if self.fast_mode and best_fio and best_fio['conf'] >= 88:
                    break
            if self.fast_mode and best_fio and best_fio['conf'] >= 88:
                break
        if best_fio:
            best_overall['fios']=best_fio['fios']; best_overall['fio_conf']=best_fio['conf']; best_overall['fio_variant']=best_fio['variant']
            best_overall['fio_ocr_conf']=float(best_fio.get('raw_conf', 0.0) or 0.0)
        else:
            best_overall['fio_variant']=best_overall.get('variant','none')
        if best_kv:
            best_overall['kv']=best_kv['kv']; best_overall['kv_conf']=best_kv['conf']; best_overall['kv_variant']=best_kv['variant']
        else:
            best_overall['kv_variant']=best_overall.get('variant','none')
        best_overall['fio_engine']='Tesseract'; best_overall['kv_engine']='Tesseract'
        if cache_key:
            if len(self.ocr_cache) >= 96:
                for old_key in list(self.ocr_cache)[:16]:
                    self.ocr_cache.pop(old_key, None)
            self.ocr_cache[cache_key] = dict(best_overall)
        return best_overall

    def auto_recognize(self):
        if self.image is None:
            self.log_label.config(text="Изображение не загружено")
            return
        self.log_label.config(text="Ищу ФИО и помещение по структуре бланка…")
        self.parent.update_idletasks()
        start = time.time()
        try:
            self._layout_match_cache = {}
            if self.fast_mode:
                img = self.image
            else:
                img, _ = self.deskew_image(self.image)
                img = self.auto_rotate(img)
            self.image = img
            self._source_page_image = img
            self.original_width, self.original_height = img.size
            self.detected_fio_roi = None
            self.detected_kv_roi = None

            turbo_enabled = bool(getattr(self, 'turbo_batch_mode', False) and self.fast_mode)
            layout_result = self._turbo_layout_template_result(img) if turbo_enabled else None
            turbo_template_ready = bool(layout_result and layout_result.get('_turbo'))
            if layout_result is None:
                layout_result = self._best_layout_template_result(img)
            if layout_result and layout_result.get('_matched_image') is not None:
                img = layout_result['_matched_image']
                self.image = img
                self.original_width, self.original_height = img.size
            self.active_layout_template = layout_result.get('name') if layout_result else None
            self.active_layout_score = float(layout_result.get('match_score', 0.0) or 0.0) if layout_result else 0.0
            template_complete = bool(layout_result and layout_result.get('fios') and layout_result.get('kv'))
            template_ready = bool(
                template_complete and
                min(layout_result.get('fio_conf', 0), layout_result.get('kv_conf', 0)) >= OCR_REVIEW_THRESHOLD
            )

            if template_ready:
                spatial_fio = {
                    'fios': layout_result['fios'], 'conf': layout_result['fio_conf'],
                    'text': layout_result.get('fio_text', ''),
                    'variant': f"template:{layout_result['name']}",
                    'roi': layout_result['fio_roi']
                }
                table_room = {
                    'kv': layout_result['kv'], 'conf': layout_result['kv_conf'],
                    'text': layout_result.get('kv_text', ''),
                    'variant': f"template:{layout_result['name']}",
                    'engine': 'TemplateROI', 'roi': layout_result['kv_roi']
                }
            else:
                if layout_result:
                    spatial_fio = {
                        'fios': list(layout_result.get('fios') or []),
                        'conf': float(layout_result.get('fio_conf', 0.0) or 0.0),
                        'text': layout_result.get('fio_text', ''),
                        'variant': f"template:{layout_result['name']}",
                        'roi': layout_result.get('fio_roi')
                    }
                    if (layout_result.get('kv') and
                            (float(layout_result.get('kv_conf', 0) or 0) >= OCR_REVIEW_THRESHOLD or
                             layout_result.get('_quick_template_candidate'))):
                        table_room = {
                            'kv': layout_result['kv'], 'conf': layout_result['kv_conf'],
                            'text': layout_result.get('kv_text', ''),
                            'variant': f"template:{layout_result['name']}",
                            'engine': 'TemplateROI', 'roi': layout_result['kv_roi']
                        }
                    elif layout_result.get('_quick_template_candidate'):
                        table_room = {
                            'kv': None, 'conf': 0.0,
                            'text': layout_result.get('kv_text', ''),
                            'variant': 'template-room-unreadable',
                            'engine': 'TemplateROI', 'roi': layout_result.get('kv_roi')
                        }
                    else:
                        table_room = self._best_table_room_result(img)
                        if (layout_result.get('kv') and
                                (not table_room.get('kv') or
                                 layout_result.get('kv_conf', 0) >= table_room.get('conf', 0))):
                            table_room = {
                                'kv': layout_result['kv'], 'conf': layout_result['kv_conf'],
                                'text': layout_result.get('kv_text', ''),
                                'variant': f"template:{layout_result['name']}",
                                'engine': 'TemplateROI', 'roi': layout_result['kv_roi']
                            }
                else:
                    spatial_fio = self._best_dynamic_fio_result(img)
                    table_room = self._best_table_room_result(img)
            region = None
            universal_ready = (
                bool(spatial_fio.get('fios')) and spatial_fio.get('conf', 0) >= OCR_REVIEW_THRESHOLD and
                bool(table_room.get('kv')) and table_room.get('conf', 0) >= OCR_REVIEW_THRESHOLD
            )

            if template_ready:
                result = {
                    'text': (layout_result.get('fio_text','') + '\n' + layout_result.get('kv_text','')).strip(),
                    'fios': layout_result['fios'],
                    'kv': layout_result['kv'],
                    'fio_conf': layout_result['fio_conf'],
                    'kv_conf': layout_result['kv_conf'],
                    'score': layout_result['fio_conf'] + layout_result['kv_conf'],
                    'variant': f"template:{layout_result['name']}",
                    'engine': 'TurboTemplateOCR' if turbo_template_ready else 'TemplateOCR',
                    'fio_engine': 'TurboROI' if turbo_template_ready else 'TemplateROI',
                    'fio_variant': layout_result.get('fio_variant','template'),
                    'kv_engine': layout_result.get(
                        'kv_engine', 'TurboROI' if turbo_template_ready else 'TemplateROI'),
                    'kv_variant': layout_result.get('kv_variant','template'),
                }
            elif layout_result:
                result = {
                    'text': (spatial_fio.get('text','') + '\n' + table_room.get('text','')).strip(),
                    'fios': list(spatial_fio.get('fios') or []),
                    'kv': table_room.get('kv'),
                    'fio_conf': float(spatial_fio.get('conf', 0.0) or 0.0),
                    'kv_conf': float(table_room.get('conf', 0.0) or 0.0),
                    'score': float(spatial_fio.get('conf', 0.0) or 0.0) + float(table_room.get('conf', 0.0) or 0.0),
                    'variant': 'template-review-fast',
                    'engine': 'TemplateOCR',
                    'fio_engine': 'TemplateROI',
                    'fio_variant': spatial_fio.get('variant','template'),
                    'kv_engine': table_room.get('engine','TableOCR'),
                    'kv_variant': table_room.get('variant','table'),
                }
            elif self.fast_mode and universal_ready:
                result = {
                    'text': (spatial_fio.get('text','') + '\n' + table_room.get('text','')).strip(),
                    'fios': spatial_fio['fios'],
                    'kv': table_room['kv'],
                    'fio_conf': spatial_fio['conf'],
                    'kv_conf': table_room['conf'],
                    'score': spatial_fio['conf'] + table_room['conf'],
                    'variant': 'universal-fast',
                    'engine': 'UniversalOCR',
                    'fio_engine': 'AnchorOCR',
                    'fio_variant': spatial_fio.get('variant','anchor'),
                    'kv_engine': table_room.get('engine','TableOCR'),
                    'kv_variant': table_room.get('variant','table'),
                }
            else:
                region = self.detect_text_region(img)
                result = self._best_tesseract_result(img, region)
                fio_from_template = str(spatial_fio.get('variant', '')).startswith('template:')
                if spatial_fio.get('fios') and (fio_from_template or not result.get('fios') or spatial_fio.get('conf',0) >= result.get('fio_conf',0)):
                    result['fios'] = spatial_fio['fios']
                    result['fio_conf'] = spatial_fio['conf']
                    result['fio_engine'] = 'TemplateROI' if fio_from_template else 'AnchorOCR'
                    result['fio_variant'] = spatial_fio.get('variant','anchor')
                if table_room.get('kv'):
                    result['kv'] = table_room['kv']
                    result['kv_conf'] = table_room['conf']
                    result['kv_engine'] = table_room.get('engine','TableOCR')
                    result['kv_variant'] = table_room.get('variant','table')
                else:
                    room_roi = layout_result.get('kv_roi') if layout_result else None
                    if room_roi:
                        room_result = self._best_room_ocr_result(img, room_roi)
                        if room_result.get('kv') and (not result.get('kv') or room_result.get('conf',0) >= result.get('kv_conf',0)):
                            result['kv'] = room_result['kv']
                            result['kv_conf'] = room_result['conf']
                            result['kv_engine'] = 'RoomOCR'
                            result['kv_variant'] = room_result['variant']

            if spatial_fio.get('roi'):
                self.detected_fio_roi = spatial_fio['roi']
            if table_room.get('roi'):
                self.detected_kv_roi = table_room['roi']

            if self.easyocr_available and (min(result.get('fio_conf',0), result.get('kv_conf',0)) < OCR_REVIEW_THRESHOLD or not result.get('fios') or not result.get('kv')):
                if region is None:
                    region = self.detect_text_region(img)
                easy_text, easy_conf = self.ocr_easyocr(img, region)
                if easy_text:
                    easy_score, e_fios, e_kv, e_fio_conf, e_kv_conf = self._score_ocr_candidate(easy_text, easy_conf)
                    if (not layout_result and e_fios and
                            (not result.get('fios') or e_fio_conf > result.get('fio_conf',0) + 2)):
                        result['fios'] = e_fios
                        result['fio_conf'] = e_fio_conf
                        result['fio_engine'] = 'EasyOCR'
                        result['fio_variant'] = 'fallback'
                    if e_kv and result.get('kv_engine') not in ('TableOCR','RoomAnchorOCR','TemplateROI','TemplateGridOCR') and (not result.get('kv') or e_kv_conf > result.get('kv_conf',0) + 2):
                        result['kv'] = e_kv
                        result['kv_conf'] = e_kv_conf
                        result['kv_engine'] = 'EasyOCR'
                        result['kv_variant'] = 'fallback'
                        result['score'] = easy_score

            if result.get('kv') and result.get('kv_engine') not in (
                    'TableOCR', 'RoomAnchorOCR', 'RoomOCR', 'TemplateROI',
                    'TemplateGridOCR', 'TurboROI'):
                result['kv_conf'] = min(float(result.get('kv_conf', 0.0)), 79.0)

            if layout_result:
                result['fios'] = list(spatial_fio.get('fios') or [])
                result['fio_conf'] = float(spatial_fio.get('conf', 0.0) or 0.0)
                result['fio_engine'] = 'TurboROI' if turbo_template_ready else 'TemplateROI'
                result['fio_variant'] = (spatial_fio.get('variant') or
                                         ('template-unreadable' if not result['fios'] else 'template'))
            else:
                if len(result.get('fios', [])) != 1 or not spatial_fio.get('roi'):
                    owner = self._owner_field_fio(img)
                    if owner is not None:
                        result['fios'] = owner['fios']
                        result['fio_conf'] = owner['conf']
                        result['fio_engine'] = 'OwnerFieldOCR'
                        result['fio_variant'] = 'owner-field'
                        spatial_fio = owner
                        self.detected_fio_roi = owner['roi']

            self.full_text = result.get('text','')
            self.last_raw_fio = spatial_fio.get('text') or result.get('text','')
            self.last_raw_kv = table_room.get('text') or result.get('text','')
            self.fio_confidence = float(result.get('fio_conf', 0.0))
            self.kv_confidence = float(result.get('kv_conf', 0.0))
            self.ocr_engine_name = result.get('engine', 'UniversalOCR')
            self.fio_engine_name = f"{result.get('fio_engine','Tesseract')} {result.get('fio_variant', result.get('variant',''))}".strip()
            self.kv_engine_name = f"{result.get('kv_engine','Tesseract')} {result.get('kv_variant', result.get('variant',''))}".strip()
            self.ocr_variant_name = result.get('variant', '—')
            self._apply_recognized(result.get('fios', []), result.get('kv'))
            self.update_image()

            elapsed = time.time() - start
            self.last_ocr_time = elapsed
            self.ocr_times.append(elapsed)
            state = "готово" if min(self.fio_confidence, self.kv_confidence) >= OCR_REVIEW_THRESHOLD else "нужна проверка"
            if layout_result:
                prefix = '🚀 Турбо-шаблон' if turbo_template_ready else 'Шаблон'
                route = f"{prefix} «{layout_result['name']}» {layout_result['match_score'] * 100:.0f}%"
                if not template_ready:
                    route += ' + проверка'
            else:
                route = 'Universal fast' if self.fast_mode and universal_ready else 'Universal + fallback'
            self.log_label.config(text=f"{state}: {elapsed:.1f}с | {route} | ФИО {self.fio_confidence:.0f}% | помещение {self.kv_confidence:.0f}%")
            if result.get('fios') or result.get('kv'):
                self.learn_template(result.get('text',''), result.get('fios',[]), result.get('kv'))
        except Exception as e:
            logger.exception("Ошибка авто-OCR")
            self.ocr_error = f'Ошибка OCR: {e}'
            self.log_label.config(text=self.ocr_error)

    def manual_recognize(self):
        if self.image is None:
            self.log_label.config(text="Изображение не загружено")
            return
        self.log_label.config(text="Распознаю выбранные области…")
        self.parent.update_idletasks()
        start = time.time()
        try:
            fio_result = self._best_tesseract_result(self.image, self.fio_roi) if self.fio_roi else None
            kv_result = self._best_tesseract_result(self.image, self.kv_roi) if self.kv_roi else None
            room_result = self._best_room_ocr_result(self.image, self.kv_roi) if self.kv_roi else None
            fios = fio_result['fios'] if fio_result else []
            kv = kv_result['kv'] if kv_result else None
            base_kv_conf = kv_result['kv_conf'] if kv_result else 0.0
            if room_result and room_result.get('kv') and (not kv or room_result.get('conf', 0) >= base_kv_conf):
                kv = room_result['kv']
                base_kv_conf = room_result['conf']
            dynamic_room = None
            self.fio_confidence = fio_result['fio_conf'] if fio_result else 0.0
            self.kv_confidence = base_kv_conf
            self.last_raw_fio = fio_result['text'] if fio_result else ''
            self.last_raw_kv = (
                dynamic_room.get('text','') if dynamic_room and dynamic_room.get('kv') == kv else
                (room_result.get('text','') if room_result and room_result.get('kv') == kv else
                 (kv_result['text'] if kv_result else ''))
            )
            self.ocr_engine_name = 'Tesseract'
            self.fio_engine_name = f"Tesseract {fio_result.get('fio_variant', fio_result.get('variant','-'))}" if fio_result else '—'
            self.kv_engine_name = (
                f"{dynamic_room.get('engine','RoomOCR')} {dynamic_room.get('variant','-')}"
                if dynamic_room and dynamic_room.get('kv') == kv else
                (f"RoomOCR {room_result.get('variant','-')}" if room_result and room_result.get('kv') == kv else
                 (f"Tesseract {kv_result.get('kv_variant', kv_result.get('variant','-'))}" if kv_result else '—'))
            )
            self.ocr_variant_name = f"ROI: {fio_result['variant'] if fio_result else '-'} / {kv_result['variant'] if kv_result else '-'}"
            self._apply_recognized(fios, kv)
            self.last_ocr_time = time.time() - start
            self.log_label.config(text=f"ROI OCR: {self.last_ocr_time:.1f}с | ФИО {self.fio_confidence:.0f}% | помещение {self.kv_confidence:.0f}%")
        except Exception as e:
            logger.exception("Ошибка ручного OCR")
            self.ocr_error = f'Ошибка OCR: {e}'
            self.log_label.config(text=self.ocr_error)

    def ocr_image(self, image, roi):
        if image is None or not roi:
            return ""
        try:
            crop_for_hash = image.crop(roi) if roi else image
            thumb = crop_for_hash.convert('L').resize((64, 64), Image.Resampling.BILINEAR)
            digest = hashlib.sha1(thumb.tobytes()).hexdigest()
        except Exception:
            digest = f"{image.size}"
        key = f"{digest}_{roi}_{self.fast_mode}"
        if self.cache_enabled and key in self.ocr_cache:
            return self.ocr_cache[key]
        result = self._best_tesseract_result(image, roi)
        value = self._normalize_ocr_text(result['text'])
        self.ocr_cache[key] = value
        return value

    def build_ui(self):
        c = Theme.colors
        root = tk.Frame(self.parent, bg=c['bg'])
        root.pack(fill=tk.BOTH, expand=True)

        top = tk.Frame(root, bg=c['bg_secondary'], height=42,
                       highlightthickness=1, highlightbackground=c['border'])
        top.pack(fill=tk.X, padx=8, pady=(8, 4))
        top.pack_propagate(False)

        primary = tk.Frame(top, bg=c['bg_secondary'])
        primary.pack(side=tk.LEFT, padx=(8,0), pady=4)
        self.btn_start = make_button(primary, "Запустить пакет", self.confirm_all,
                                     bg=c['accent'], fg='white', width=13, pady=5)
        self.btn_start.pack(side=tk.LEFT, padx=2)
        self.btn_pause = make_button(primary, "Пауза", self.toggle_pause,
                                     bg=c['btn'], fg=c['fg'], width=8, state=tk.DISABLED, pady=5)
        self.btn_pause.pack(side=tk.LEFT, padx=2)
        self.btn_resume = make_button(primary, "Продолжить", self.resume_process,
                                      bg=c['success'], fg='white', width=10, state=tk.DISABLED, pady=5)
        self.btn_resume.pack(side=tk.LEFT, padx=2)
        self.btn_stop = make_button(primary, "Стоп", self.stop_process,
                                    bg=c['error'], fg='white', width=7, state=tk.DISABLED, pady=5)
        self.btn_stop.pack(side=tk.LEFT, padx=2)

        self.status_indicator = tk.Label(top, text="●", fg=c['success'], bg=c['bg_secondary'])
        self.status_panel = tk.Label(top, text="Готов", fg=c['success'], bg=c['bg_secondary'])
        self.daily_ocr_label = tk.Label(top, text=f"OCR {daily_stats.get_ocr()}",
                                        bg=c['bg_secondary'], fg=c['accent'])
        self.daily_input_label = tk.Label(top, text=f"Ввод {daily_stats.get_input()}",
                                          bg=c['bg_secondary'], fg=c['fg'])

        controls = tk.Frame(root, bg=c['card_bg'], height=42,
                            highlightthickness=1, highlightbackground=c['border'])
        controls.pack(fill=tk.X, padx=8, pady=4)
        controls.pack_propagate(False)
        self.controls_frame = controls

        mode_row = tk.Frame(controls, bg=c['card_bg'])
        mode_row.pack(fill=tk.X, padx=8, pady=(3, 2))
        tk.Label(mode_row, text="Режим", bg=c['card_bg'], fg=c['accent'],
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(2, 8))
        self.btn_auto = make_button(mode_row, "Авто", partial(self.set_mode, "auto"),
                                    bg=c['success'], fg='white', width=11, pady=5)
        self.btn_auto.pack(side=tk.LEFT, padx=2)
        self.btn_manual = make_button(mode_row, "Ручной ROI", partial(self.set_mode, "manual"),
                                      bg=c['btn'], fg=c['fg'], width=15, pady=5)
        self.btn_manual.pack(side=tk.LEFT, padx=2)
        self.btn_fast = make_button(mode_row, "Быстро", self.toggle_fast_mode,
                                    bg=c['accent'], fg='white', width=11, pady=5)
        self.btn_fast.pack(side=tk.LEFT, padx=2)

        zoom_box = tk.Frame(mode_row, bg=c['card_bg'])
        zoom_box.pack(side=tk.RIGHT, padx=2)
        make_button(zoom_box, "−", self.zoom_out, width=3, pady=5).pack(side=tk.LEFT, padx=1)
        self.zoom_label = tk.Label(zoom_box, text="100%", bg=c['card_bg'], fg=c['accent'],
                                   width=6, font=("Segoe UI", 9, "bold"))
        self.zoom_label.pack(side=tk.LEFT)
        make_button(zoom_box, "+", self.zoom_in, width=3, pady=5).pack(side=tk.LEFT, padx=1)
        make_button(zoom_box, "100%", self.reset_zoom, width=5, pady=5).pack(side=tk.LEFT, padx=2)

        roi_row = tk.Frame(controls, bg=c['card_bg'])
        self.roi_tools_row = roi_row
        tk.Label(roi_row, text="ROI:", bg=c['card_bg'], fg=c['fg'],
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(2, 6))
        self.select_frame = tk.Frame(roi_row, bg=c['card_bg'])
        self.select_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.btn_fio = make_button(self.select_frame, "ФИО", partial(self.set_select_mode, 'fio'),
                                   bg=c['btn'], fg=c['fg'], width=8, pady=4)
        self.btn_fio.pack(side=tk.LEFT, padx=2)
        self.btn_kv = make_button(self.select_frame, "№ помещения", partial(self.set_select_mode, 'kv'),
                                  bg=c['btn'], fg=c['fg'], width=13, pady=4)
        self.btn_kv.pack(side=tk.LEFT, padx=2)
        self.btn_save_roi = make_button(self.select_frame, "Сохранить ROI", self.save_current_roi,
                                        bg=c['warning'], fg='#101010', width=14, pady=4)
        self.btn_save_roi.pack(side=tk.LEFT, padx=2)
        self.btn_roi_batch = make_button(
            self.select_frame, "Пакет по ROI", self.confirm_roi_batch,
            bg=c['success'], fg='white', width=14, pady=4,
            state=tk.NORMAL if self.roi_saved else tk.DISABLED
        )
        self.btn_roi_batch.pack(side=tk.LEFT, padx=2)
        self.btn_reset_roi = make_button(self.select_frame, "Сброс ROI", self.reset_rois,
                                         bg=c['btn'], fg=c['fg'], width=11, pady=4)
        self.btn_reset_roi.pack(side=tk.LEFT, padx=2)
        self.btn_teach = make_button(self.select_frame, "Обучить бланк", self.teach_mode,
                                     bg=c['btn'], fg=c['fg'], width=15, pady=4)
        self.btn_teach.pack(side=tk.LEFT, padx=2)

        footer = tk.Frame(root, bg=c['bg_secondary'], height=32,
                          highlightthickness=1, highlightbackground=c['border'])
        footer.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=(2, 5))
        footer.pack_propagate(False)
        self.status_label = tk.Label(footer, text="Готов", bg=c['bg_secondary'], fg=c['accent'],
                                     font=("Segoe UI", 9, "bold"), anchor="w")
        self.status_label.pack(side=tk.LEFT, padx=10)
        self.log_label = tk.Label(footer, text="Выберите документ", bg=c['bg_secondary'], fg=c['fg'],
                                  font=("Segoe UI", 9), anchor="w")
        self.log_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
        make_button(footer, "Справка", self.show_controls_help, bg=c['btn'], fg=c['fg'],
                    width=8, pady=3).pack(side=tk.RIGHT, padx=4, pady=2)

        body = tk.Frame(root, bg=c['bg'])
        body.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1, minsize=520)
        body.grid_columnconfigure(1, weight=0, minsize=525)

        viewer = tk.Frame(body, bg=c['card_bg'], highlightthickness=1, highlightbackground=c['border'])
        viewer.grid(row=0, column=0, sticky='nsew', padx=(0, 4))
        docbar = tk.Frame(viewer, bg=c['card_bg'], height=36)
        docbar.pack(fill=tk.X)
        docbar.pack_propagate(False)
        self.info = tk.Label(docbar, text="Документ не выбран", bg=c['card_bg'], fg=c['fg'],
                             font=("Segoe UI", 9, "bold"), anchor='w')
        self.info.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        self.quality_badge = tk.Label(docbar, text="ПРОВЕРКА", bg=c['warning'], fg='#101010',
                                      font=("Segoe UI", 8, "bold"), padx=7, pady=2)
        self.quality_badge.pack(side=tk.RIGHT, padx=5)
        self.engine_label = tk.Label(docbar, text="", bg=c['card_bg'], fg=c['accent'], font=("Segoe UI", 8))
        self.engine_label.pack(side=tk.RIGHT, padx=5)

        canvas_wrap = tk.Frame(viewer, bg='#0a0f18')
        canvas_wrap.pack(fill=tk.BOTH, expand=True, padx=1, pady=(0, 1))
        self.x_scroll = tk.Scrollbar(canvas_wrap, orient=tk.HORIZONTAL)
        self.y_scroll = tk.Scrollbar(canvas_wrap, orient=tk.VERTICAL)
        self.canvas = tk.Canvas(canvas_wrap, xscrollcommand=self.x_scroll.set, yscrollcommand=self.y_scroll.set,
                                bg='#0a0f18', highlightthickness=0)
        self.x_scroll.config(command=self.canvas.xview)
        self.y_scroll.config(command=self.canvas.yview)
        self.x_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.y_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas_image = self.canvas.create_image(0, 0, anchor=tk.NW, image=None)
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)

        inspector = tk.Frame(body, bg=c['bg_secondary'], highlightthickness=1, highlightbackground=c['border'])
        inspector.grid(row=0, column=1, sticky='nsew')
        inspector.grid_propagate(False)

        head = tk.Frame(inspector, bg=c['bg_secondary'], height=38)
        head.pack(fill=tk.X, padx=8, pady=(6, 2))
        head.pack_propagate(False)

        title_box = tk.Frame(head, bg=c['bg_secondary'])
        title_box.pack(side=tk.LEFT, fill=tk.Y)
        tk.Label(title_box, text="Результат распознавания", bg=c['bg_secondary'], fg=c['fg'],
                 font=("Segoe UI", 11, "bold")).pack(anchor='w')
        self.review_hint = tk.Label(
            title_box, text="Проверьте данные и подтвердите результат",
            bg=c['bg_secondary'], fg=c['accent'], font=("Segoe UI", 8)
        )
        self.review_hint.pack(anchor='w')

        self.roi_label = tk.Label(
            head, text="ROI ✓" if self.roi_saved else "ROI —",
            bg=c['bg_secondary'],
            fg=c['success'] if self.roi_saved else c['warning'],
            font=("Segoe UI", 8, "bold"), padx=6, pady=2
        )
        self.roi_label.pack(side=tk.RIGHT, pady=3)

        confidence = tk.Frame(inspector, bg=c['bg_secondary'], height=54)
        confidence.pack(fill=tk.X, padx=8, pady=(0, 3))
        confidence.pack_propagate(False)
        confidence.grid_columnconfigure(0, weight=1, uniform='confidence')
        confidence.grid_columnconfigure(1, weight=1, uniform='confidence')

        fio_conf_card = tk.Frame(
            confidence, bg=c['card_bg'], highlightthickness=1,
            highlightbackground=c['border']
        )
        fio_conf_card.grid(row=0, column=0, sticky='nsew', padx=(0, 3))
        tk.Label(
            fio_conf_card, text="ФИО", bg=c['card_bg'], fg=c['fg'],
            font=("Segoe UI", 8, "bold")
        ).pack(side=tk.LEFT, padx=(9,4), pady=8)
        self.fio_conf_label = tk.Label(
            fio_conf_card, text="0%", bg=c['card_bg'], fg=c['error'],
            font=("Segoe UI", 15, "bold")
        )
        self.fio_conf_label.pack(side=tk.RIGHT, padx=(4,9), pady=5)
        self.fio_conf_bar = ttk.Progressbar(
            fio_conf_card, orient=tk.HORIZONTAL, maximum=100,
            style='Dashboard.Horizontal.TProgressbar'
        )

        room_conf_card = tk.Frame(
            confidence, bg=c['card_bg'], highlightthickness=1,
            highlightbackground=c['border']
        )
        room_conf_card.grid(row=0, column=1, sticky='nsew', padx=(3, 0))
        tk.Label(
            room_conf_card, text="№ ПОМЕЩЕНИЯ", bg=c['card_bg'], fg=c['fg'],
            font=("Segoe UI", 8, "bold")
        ).pack(side=tk.LEFT, padx=(9,4), pady=8)
        self.kv_conf_label = tk.Label(
            room_conf_card, text="0%", bg=c['card_bg'], fg=c['error'],
            font=("Segoe UI", 15, "bold")
        )
        self.kv_conf_label.pack(side=tk.RIGHT, padx=(4,9), pady=5)
        self.kv_conf_bar = ttk.Progressbar(
            room_conf_card, orient=tk.HORIZONTAL, maximum=100,
            style='Dashboard.Horizontal.TProgressbar'
        )

        fields_host = tk.Frame(inspector, bg=c['card_bg'])
        fields_host.pack(fill=tk.BOTH, expand=True, padx=8, pady=3)
        fields_scroll = tk.Scrollbar(fields_host, orient=tk.VERTICAL)
        fields_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        fields_canvas = tk.Canvas(fields_host, bg=c['card_bg'], highlightthickness=0,
                                  height=210, yscrollcommand=fields_scroll.set)
        fields_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        fields_scroll.config(command=fields_canvas.yview)
        fields = tk.Frame(
            fields_canvas, bg=c['card_bg'], highlightthickness=1,
            highlightbackground=c['border']
        )
        fields_window = fields_canvas.create_window((0,0), window=fields, anchor='nw')
        fields.bind('<Configure>', lambda event: fields_canvas.configure(scrollregion=fields_canvas.bbox('all')))
        fields_canvas.bind('<Configure>', lambda event: fields_canvas.itemconfigure(fields_window, width=event.width))

        fio_row = tk.Frame(fields, bg=c['card_bg'])
        fio_row.pack(fill=tk.X, padx=8, pady=(6, 2))
        tk.Label(
            fio_row, text="ФИО СОБСТВЕННИКА",
            bg=c['card_bg'], fg=c['fg'], font=("Segoe UI", 8, "bold")
        ).pack(anchor='w')

        self._extra_fios_visible = False
        self.fio_entries = []

        always_fio_frame = tk.Frame(fields, bg=c['card_bg'])
        always_fio_frame.pack(fill=tk.X, padx=8, pady=(0,4))

        for i in range(2):
            row = tk.Frame(always_fio_frame, bg=c['card_bg'])
            row.pack(fill=tk.X, pady=1)

            tk.Label(
                row, text=f"ФИО {i+1}",
                bg=c['card_bg'], fg=c['accent'],
                font=("Segoe UI", 8, "bold"),
                width=6, anchor='w'
            ).pack(side=tk.LEFT, padx=(0,6))

            entry = make_entry(
                row, relief=tk.FLAT, bd=0,
                font=("Segoe UI", 10)
            )
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=2)
            entry.bind("<FocusOut>", lambda e, idx=i: self.on_fio_edit(idx))
            self.fio_entries.append(entry)

        self.extra_fio_frame = tk.Frame(fields, bg=c['card_bg'])
        self.extra_fio_frame.pack(fill=tk.X, padx=8, pady=(0,4))
        for i in range(2, 3):
            row = tk.Frame(self.extra_fio_frame, bg=c['card_bg'])
            row.pack(fill=tk.X, pady=1)

            tk.Label(
                row, text=f"ФИО {i+1}",
                bg=c['card_bg'], fg=c['accent'],
                font=("Segoe UI", 8, "bold"),
                width=6, anchor='w'
            ).pack(side=tk.LEFT, padx=(0,6))

            entry = make_entry(
                row, relief=tk.FLAT, bd=0,
                font=("Segoe UI", 9)
            )
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=2)
            entry.bind("<FocusOut>", lambda e, idx=i: self.on_fio_edit(idx))
            self.fio_entries.append(entry)

        self.btn_extra_fios = tk.Button(
            fields, text="ФИО 3–6  ▾",
            command=self.toggle_extra_fios,
            bg=c['card_bg'], fg=c['accent'],
            activebackground=c['card_bg'], activeforeground=c['fg'],
            relief=tk.FLAT, bd=0, cursor='hand2',
            font=("Segoe UI", 8, "bold"), anchor='w'
        )

        room_row = tk.Frame(fields, bg=c['bg_secondary'])
        room_row.pack(fill=tk.X, padx=8, pady=(1,3))
        room_head = tk.Frame(room_row, bg=c['bg_secondary'])
        room_head.pack(fill=tk.X, padx=8, pady=(3,1))
        tk.Label(
            room_head, text="НОМЕР ПОМЕЩЕНИЯ / КВАРТИРЫ",
            bg=c['bg_secondary'], fg=c['fg'], font=("Segoe UI", 8, "bold")
        ).pack(side=tk.LEFT)
        self.room_value_hint = tk.Label(
            room_head, text="", bg=c['bg_secondary'], fg=c['accent'],
            font=("Segoe UI", 8, "bold")
        )
        self.room_value_hint.pack(side=tk.RIGHT)

        self.kv_entry = make_entry(
            room_row, width=18, relief=tk.FLAT, bd=0,
            font=("Segoe UI", 15, "bold")
        )
        self.kv_entry.pack(fill=tk.X, padx=8, pady=(0,3), ipady=2)
        self.kv_entry.bind("<FocusOut>", self.on_kv_edit)

        action_dock = tk.Frame(
            inspector, bg=c['bg_secondary'],
            highlightthickness=1, highlightbackground=c['border']
        )
        action_dock.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=(3,8), before=fields_host)

        primary_actions = tk.Frame(action_dock, bg=c['bg_secondary'])
        primary_actions.pack(fill=tk.X, padx=7, pady=(4,2))

        self.btn_confirm_result = make_button(
            primary_actions, "ПОДТВЕРДИТЬ", self.confirm,
            bg=c['success'], fg='white', width=14, pady=4
        )
        self.btn_confirm_result.pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0,2)
        )

        self.btn_review_result = make_button(
            primary_actions, "НА ПРОВЕРКУ", self.skip_file,
            bg=c['warning'], fg='#101010', width=12, pady=4
        )
        self.btn_review_result.pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=2
        )

        self.btn_edit_result = make_button(
            primary_actions, "ИСПРАВИТЬ",
            lambda: self.fio_entries[0].focus_set() if self.fio_entries else None,
            bg=c['accent'], fg='white', width=10, pady=4
        )
        self.btn_edit_result.pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(2,0)
        )

        secondary = tk.Frame(action_dock, bg=c['bg_secondary'])
        secondary.pack(fill=tk.X, padx=7, pady=(0,6))
        if hasattr(self, '_exclude_current_review'):
            make_button(secondary, 'Удалить из проверки', self._exclude_current_review,
                        bg=c['btn'], fg=c['error'], pady=3).pack(side=tk.LEFT)

        self.more_result_menu = tk.Menu(
            secondary, tearoff=0,
            bg=c['bg_secondary'], fg=c['fg'],
            activebackground=c['accent'], activeforeground='white'
        )
        self.more_result_menu.add_command(
            label='Повторить OCR', command=self.re_recognize
        )
        self.more_result_menu.add_command(
            label='Отменить последнее действие', command=self.undo_last_action
        )
        self.more_result_menu.add_separator()
        self.more_result_menu.add_command(
            label='Диагностика', command=self.run_diagnostics
        )

        self.btn_more_result = tk.Menubutton(
            secondary, text='Ещё  ⋯', menu=self.more_result_menu,
            bg=c['btn'], fg=c['fg'],
            activebackground=c['accent'], activeforeground='white',
            relief=tk.FLAT, bd=0, font=('Segoe UI',8,'bold'),
            cursor='hand2', padx=10, pady=3
        )
        self.btn_more_result.pack(side=tk.RIGHT)

        self.learn_label = tk.Label(
            secondary,
            text=f"Обучение: {len(self.fio_corrections) + len(self.room_corrections)}",
            bg=c['bg_secondary'], fg=c['accent'], font=("Segoe UI", 8)
        )
        self.learn_label.pack(side=tk.LEFT)

        self.count_label = tk.Label(
            secondary, text="ФИО: 0",
            bg=c['bg_secondary'], fg=c['fg'], font=("Segoe UI", 8)
        )
        self.count_label.pack(side=tk.LEFT, padx=(10,0))

        ToolTip(
            self.btn_confirm_result,
            'Сохранить проверенные данные в ready.'
        )
        ToolTip(
            self.btn_review_result,
            'Оставить документ в очереди ручной проверки.'
        )
        ToolTip(
            self.btn_edit_result,
            'Перейти к редактированию распознанных данных.'
        )

        self.set_mode("auto")
        self.apply_styles()

    def show_controls_help(self):
        messagebox.showinfo(
            "Управление OCR",
            "Обработать всё — запускает очередь OCR.\n"
            "Пауза / Продолжить / Стоп — управляют пакетной обработкой.\n"
            "Подтвердить и сохранить — сохраняет проверенный результат в ready.\n"
            "Повторить OCR — дополнительная команда для текущего документа.\n"
            "Пропустить — переходит к следующему PDF без сохранения результата.\n"
            "Отменить — возвращает последнее подтверждённое действие, если это возможно.\n"
            "Диагностика — показывает состояние OCR и окружения.\n"
            "Авто — динамически ищет ФИО по подписи и номер по таблице.\n"
            "Ручной ROI — позволяет выделить ФИО и номер вручную.\n"
            "Быстро — переключает скорость/качество распознавания.\n"
            "Запомнить ROI — сохраняет области для похожих бланков.\n"
            "Сбросить ROI — удаляет сохранённые области.\n"
            "Масштаб — изменяет просмотр, но не качество OCR."
        )

    def apply_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        c = Theme.colors
        style.configure('Custom.TLabelframe', background=c['bg_secondary'], foreground=c['fg'], relief='solid', borderwidth=1)
        style.configure('Custom.TLabelframe.Label', background=c['bg_secondary'], foreground=c['accent'], font=('Segoe UI', 10, 'bold'))
        style.configure('Custom.Horizontal.TProgressbar', background=c['progress_bg'], troughcolor=c['bg_secondary'],
                        bordercolor=c['progress_bg'], lightcolor=c['progress_bg'], darkcolor=c['progress_bg'], thickness=20)

    def toggle_fast_mode(self):
        if getattr(self, 'batch_busy', False) and not getattr(self, '_mandatory_training', False):
            return
        self.fast_mode = not self.fast_mode
        self.btn_fast.config(text="⚡ БЫСТРОЕ OCR" if self.fast_mode else "🔎 ГЛУБОКОЕ OCR", bg="#0066cc" if self.fast_mode else "#aa6600")
        self.log_label.config(text="⚡ Быстрое адаптивное OCR" if self.fast_mode else "🔎 Глубокая проверка OCR")

    def select_oss(self):
        if getattr(self, 'batch_busy', False) and not getattr(self, '_mandatory_training', False):
            return
        oss_list = get_oss_folders()
        if not oss_list:
            if messagebox.askyesno("Нет ОСС", "📂 Нет папок с ОСС. Создать пример?"):
                os.makedirs(os.path.join(SOURCE_FOLDER_PATH, "123"), exist_ok=True)
                messagebox.showinfo("Готово", "✅ Создана папка source/123/")
            return False
        dialog = tk.Toplevel(self.parent)
        dialog.title("Выбор ОСС")
        dialog.geometry("400x400")
        dialog.config(bg=Theme.colors['bg'])
        dialog.transient(self.parent)
        dialog.grab_set()
        tk.Label(dialog, text="Выберите один ОСС или обработайте все сразу:", bg=Theme.colors['bg'], fg=Theme.colors['fg'],
                 font=("Segoe UI", 12, "bold")).pack(pady=15)
        listbox = tk.Listbox(dialog, bg=Theme.colors['entry'], fg=Theme.colors['fg'],
                             font=("Segoe UI", 12), selectmode=tk.SINGLE)
        listbox.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        total_files = sum(len(get_pdf_files(oss)) for oss in oss_list)
        listbox.insert(tk.END, f"▶ ВСЕ ОСС ({total_files} файлов)")
        for oss in oss_list:
            listbox.insert(tk.END, f"ОСС {oss} ({len(get_pdf_files(oss))} файлов)")
        listbox.select_set(0)
        listbox.focus_set()
        result = [None]
        def on_select():
            sel = listbox.curselection()
            if sel:
                result[0] = "__ALL__" if sel[0] == 0 else oss_list[sel[0] - 1]
                dialog.destroy()
        listbox.bind("<Double-Button-1>", lambda e: on_select())
        listbox.bind("<Return>", lambda e: on_select())
        tk.Button(dialog, text="✅ Выбрать", command=on_select,
                  bg=Theme.colors['accent'], fg=Theme.colors['bg'],
                  font=("Segoe UI", 10, "bold")).pack(pady=15)
        dialog.wait_window()
        if not result[0]:
            return False
        self.current_index = 0
        self.review_mode = False
        self.stop_flag = False
        if result[0] == "__ALL__":
            self.current_oss = "Все ОСС"
            self.pdf_files = [
                (oss, filename)
                for oss in oss_list
                for filename in get_pdf_files(oss)
            ]
            logger.info("Выбраны все ОСС: %s папок, %s PDF", len(oss_list), len(self.pdf_files))
        else:
            self.current_oss = result[0]
            self.find_files()
        self.load_file()
        return True

    def find_files(self):
        files = get_pdf_files(self.current_oss)
        if files:
            self.current_index = 0
            self.pdf_files = [(self.current_oss, f) for f in files]
            self.review_mode = False
            logger.info("Найдено файлов: %s", len(files))
            return True
        messagebox.showwarning("Нет файлов", f"В source/{self.current_oss} нет PDF")
        return False

    def open_robot_helper_tab(self):
        try:
            self.parent.master.select(1)
        except Exception as exc:
            logger.exception("Не удалось открыть вкладку Робота-помощника")
            messagebox.showerror("Робот-помощник", f"Не удалось открыть вкладку:\n{exc}")

    def toggle_extra_fios(self, force=None):
        return

    def set_mode(self, mode):
        if getattr(self, 'batch_busy', False) and not getattr(self, '_mandatory_training', False):
            return
        self.mode = mode
        if mode == "auto":
            self.btn_auto.config(relief=tk.SUNKEN, bg=Theme.colors['success'])
            self.btn_manual.config(relief=tk.RAISED, bg=Theme.colors['btn'])
            self.btn_fio.config(state=tk.DISABLED)
            self.btn_kv.config(state=tk.DISABLED)
            self.btn_reset_roi.config(state=tk.DISABLED)
            self.btn_teach.config(state=tk.DISABLED)
            self.btn_save_roi.config(state=tk.DISABLED)
            self.btn_roi_batch.config(state=tk.DISABLED)
            if hasattr(self,'roi_tools_row'):
                self.roi_tools_row.pack_forget()
            if hasattr(self,'controls_frame'):
                self.controls_frame.config(height=42)
            self.canvas.config(cursor="")
            self.status_label.config(text="🤖 Авто: динамический поиск полей")
            if self.image is not None:
                self.auto_recognize()
        else:
            self.btn_auto.config(relief=tk.RAISED, bg=Theme.colors['btn'])
            self.btn_manual.config(relief=tk.SUNKEN, bg=Theme.colors['success'])
            self.btn_fio.config(state=tk.NORMAL)
            self.btn_kv.config(state=tk.NORMAL)
            self.btn_reset_roi.config(state=tk.NORMAL)
            self.btn_teach.config(state=tk.NORMAL)
            self.btn_save_roi.config(state=tk.NORMAL)
            self.btn_roi_batch.config(state=tk.NORMAL if self.roi_saved else tk.DISABLED)
            if hasattr(self,'controls_frame'):
                self.controls_frame.config(height=76)
            if hasattr(self,'roi_tools_row'):
                self.roi_tools_row.pack(fill=tk.X, padx=8, pady=(1,5))
            self.canvas.config(cursor="cross")
            self.status_label.config(text="✋ Режим: Ручное выделение")
            if getattr(self, '_mandatory_training', False):
                self.fio_roi = self.detected_fio_roi
                self.kv_roi = self.detected_kv_roi
                self.log_label.config(text="🧠 Неизвестный бланк: проверьте/выделите ФИО и помещение, затем сохраните шаблон")
                self.update_image()
            elif self.roi_saved and self.saved_fio_roi and self.saved_kv_roi and self.image is not None:
                if self._adaptive_manual_rois():
                    self.log_label.config(text="✅ Области совмещены с бланком")
                    self.update_image()
                    self.manual_recognize()
                else:
                    self.log_label.config(text="Выделите области для обучения этого бланка")
            else:
                self.log_label.config(text="✋ Выделите области и нажмите 'Запомнить области'")

    def teach_mode(self):
        if self.image is None:
            messagebox.showinfo("Внимание", "Сначала загрузите изображение")
            return
        self.learning_template_pending = True
        messagebox.showinfo("🎯 Режим обучения",
            "1. Нажмите '🔵 ФИО' и выделите область с ФИО\n"
            "2. Нажмите '🟢 Помещение' и выделите область с номером\n"
            "3. Нажмите '💾 Сохранить ROI' и задайте имя бланка\n\n"
            "В режиме АВТО робот сам узнает этот тип бланка.")
        self.set_mode("manual")
        self.set_select_mode('fio')
        self.status_label.config(text="🎯 Режим обучения: выделите ФИО")

    def set_select_mode(self, mode):
        if self.mode != "manual": return
        self.select_mode = mode
        if mode == 'fio':
            self.btn_fio.config(relief=tk.SUNKEN, bg="#0066CC")
            self.btn_kv.config(relief=tk.RAISED, bg=Theme.colors['btn'])
            self.status_label.config(text="🔵 Выделите область с ФИО")
        else:
            self.btn_fio.config(relief=tk.RAISED, bg=Theme.colors['btn'])
            self.btn_kv.config(relief=tk.SUNKEN, bg="#00AA00")
            self.status_label.config(text="🟢 Выделите область с номером помещения")
        self.canvas.config(cursor="cross")

    def reset_rois(self, clear_only=False):
        if getattr(self, 'batch_busy', False) and not getattr(self, '_mandatory_training', False):
            return
        self.fio_roi = self.kv_roi = None
        self.select_mode = None
        self.btn_fio.config(relief=tk.RAISED, bg=Theme.colors['btn'])
        self.btn_kv.config(relief=tk.RAISED, bg=Theme.colors['btn'])
        self.canvas.config(cursor="cross" if self.mode == "manual" else "")
        if not clear_only:
            self.saved_fio_roi = self.saved_kv_roi = None
            self.roi_saved = False
            self.btn_roi_batch.config(state=tk.DISABLED)
            self.roi_label.config(text="📍 Области: не сохранены", fg=Theme.colors['error'])
            if os.path.exists(ROI_DATA_PATH):
                try:
                    os.remove(ROI_DATA_PATH)
                except Exception:
                    logger.debug("Не критичная ошибка очистки", exc_info=True)
            self.log_label.config(text="🔄 Области сброшены")
        self.update_image()

    def save_current_roi(self):
        if getattr(self, 'batch_busy', False) and not getattr(self, '_mandatory_training', False):
            return
        if not self.fio_roi or not self.kv_roi:
            messagebox.showwarning("Внимание", "Сначала выделите обе области (ФИО и помещение)!")
            return
        if self.save_roi():
            self.roi_label.config(text="📍 Области: сохранены ✅", fg=Theme.colors['success'])
            self.roi_saved = True
            self.btn_roi_batch.config(state=tk.NORMAL)
            learned_message = ""
            if True:
                default_name = f"Бланк {len(self._layout_templates()) + 1}"
                name = simpledialog.askstring(
                    "🧠 Имя шаблона",
                    "Как назвать этот тип бланка?",
                    initialvalue=default_name, parent=self.parent
                ) or default_name
                existing = next((value for _, value in self._layout_templates()
                                 if str(value.get('name', '')).casefold() == name.casefold()), None)
                if existing and not messagebox.askyesno(
                    "Заменить шаблон?",
                    f"Шаблон «{name}» уже есть. Обновить его этими областями?"
                ):
                    name = f"{name} {datetime.now().strftime('%H%M%S')}"
                saved_name = self._save_layout_template(name)
                if saved_name:
                    duplicate_note = (f' (использован существующий «{saved_name}»)' 
                                      if str(saved_name) != str(name) else '')
                    learned_message = (
                        f"\n\n🧠 Шаблон «{saved_name}» готов{duplicate_note}.\n"
                        f"Всего типов бланков: {len(self._layout_templates())}."
                    )
                    try:
                        groups = self._analyze_template_duplicates(
                            sig_threshold=0.012, roi_threshold=0.015)
                        dupes = sum(len(g) - 1 for g in groups)
                        if dupes > 0 and hasattr(self, 'log_label'):
                            self.log_label.config(
                                text=f'🧹 Похоже, есть дубли шаблонов: {dupes}. '
                                     f'Инструменты → Анализ дублей шаблонов.')
                    except Exception:
                        logger.debug('Автопроверка дублей после обучения упала', exc_info=True)
                self.learning_template_pending = False
            messagebox.showinfo(
                "Готово",
                "✅ ROI сохранён для пакета."
                + learned_message
                + "\n\nВ режиме АВТО сначала будет выбираться подходящий обученный шаблон."
            )
            if self.image is not None:
                self.manual_recognize()

    def on_mouse_down(self, event):
        if getattr(self, 'batch_busy', False) and not getattr(self, '_mandatory_training', False):
            return
        if self.mode != "manual" or not self.select_mode: return
        self.drawing = True
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        if self.current_rect:
            self.canvas.delete(self.current_rect)
        color = "#00A0FF" if self.select_mode == 'fio' else "#00C040"
        self.current_rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline=color, width=2)

    def on_mouse_move(self, event):
        if getattr(self, 'batch_busy', False) and not getattr(self, '_mandatory_training', False):
            return
        if not self.drawing or not self.current_rect: return
        end_x = self.canvas.canvasx(event.x)
        end_y = self.canvas.canvasy(event.y)
        self.canvas.coords(self.current_rect, self.start_x, self.start_y, end_x, end_y)

    def on_mouse_up(self, event):
        if getattr(self, 'batch_busy', False) and not getattr(self, '_mandatory_training', False):
            return
        if not self.drawing or self.mode != "manual": return
        self.drawing = False
        if not self.current_rect: return
        end_x = self.canvas.canvasx(event.x)
        end_y = self.canvas.canvasy(event.y)
        self.canvas.delete(self.current_rect)
        self.current_rect = None
        x1 = min(self.start_x, end_x)
        y1 = min(self.start_y, end_y)
        x2 = max(self.start_x, end_x)
        y2 = max(self.start_y, end_y)
        if abs(x2 - x1) < 10 or abs(y2 - y1) < 10: return
        roi = (int(x1/self.zoom), int(y1/self.zoom), int(x2/self.zoom), int(y2/self.zoom))
        if self.select_mode == 'fio':
            self.fio_roi = roi
            self.status_label.config(text="✅ ФИО выбрано! Теперь выберите помещение")
            self.btn_fio.config(relief=tk.RAISED, bg=Theme.colors['btn'])
        else:
            self.kv_roi = roi
            self.status_label.config(text="✅ Помещение выбрано! Нажмите 'Запомнить области'")
            self.btn_kv.config(relief=tk.RAISED, bg=Theme.colors['btn'])
        self.select_mode = None
        self.canvas.config(cursor="cross")
        self.update_image()
        if self.fio_roi and self.kv_roi:
            self.log_label.config(text="💡 Нажмите 'Запомнить области'")
            self.btn_save_roi.config(bg=Theme.colors['success'])
            if self.image is not None and not getattr(self, '_mandatory_training', False):
                self.manual_recognize()
            elif getattr(self, '_mandatory_training', False):
                self.log_label.config(text="🧠 Области выбраны. Нажмите «Сохранить ROI», чтобы обучить этот бланк.")

    def update_image(self):
        if not self.image: return
        w = int(self.original_width * self.zoom)
        h = int(self.original_height * self.zoom)
        resized = self.image.resize((w, h), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(resized)
        self.canvas.itemconfig(self.canvas_image, image=self.tk_image)
        self.canvas.config(scrollregion=(0, 0, w, h))
        self.zoom_label.config(text=f"{int(self.zoom * 100)}%")
        self.draw_annotations()

    def draw_annotations(self):
        self.canvas.delete("annotation")
        fio_box = self.fio_roi if self.mode == 'manual' and self.fio_roi else self.detected_fio_roi
        kv_box = self.kv_roi if self.mode == 'manual' and self.kv_roi else self.detected_kv_roi
        if fio_box:
            x1,y1,x2,y2 = [int(v*self.zoom) for v in fio_box]
            self.canvas.create_rectangle(x1,y1,x2,y2, outline="#00A0FF", width=3, tags="annotation")
            self.canvas.create_text(x1+5, y1+5, text="ФИО AUTO" if self.mode == 'auto' else "ФИО", anchor=tk.NW, fill="#00A0FF", tags="annotation")
        if kv_box:
            x1,y1,x2,y2 = [int(v*self.zoom) for v in kv_box]
            self.canvas.create_rectangle(x1,y1,x2,y2, outline="#00C040", width=3, tags="annotation")
            self.canvas.create_text(x1+5, y1+5, text="№ AUTO" if self.mode == 'auto' else "№", anchor=tk.NW, fill="#00C040", tags="annotation")
        y = 30
        for i, fio in enumerate(self.recognized_fios[:3]):
            self.canvas.create_text(20, y, text=f"🔵 ФИО {i+1}: {fio}", anchor=tk.NW,
                                    fill="#00FFFF" if i==0 else "#88DDDD", tags="annotation")
            y += 25
        if self.recognized_kv:
            self.canvas.create_text(20, y, text=f"🟢 №: {self.recognized_kv}", anchor=tk.NW,
                                    fill="#00FF00", tags="annotation")

    def zoom_in(self):
        if self.zoom < 3.0:
            self.zoom = min(self.zoom + 0.1, 3.0)
            self.update_image()
    def zoom_out(self):
        if self.zoom > 0.2:
            self.zoom = max(self.zoom - 0.1, 0.2)
            self.update_image()
    def reset_zoom(self):
        self.zoom = 1.0
        self.update_image()
    def on_mousewheel(self, event):
        self.zoom_in() if event.delta > 0 else self.zoom_out()

    def load_file(self):
        if self.stop_flag:
            if not self.is_running:
                self.show_summary()
            return False
        if self.current_index >= len(self.pdf_files):
            if not self.is_running:
                self.show_summary()
            return False
        oss, filename = self.pdf_files[self.current_index]
        logger.info("Обработка [%s] %s", oss, filename)
        self.info.config(text=f"ОСС {oss} | {self.current_index + 1}/{len(self.pdf_files)}")
        file_path = os.path.join(SOURCE_FOLDER_PATH, oss, filename)
        self.recognized_fios, self.recognized_kv = [], None
        self.fio_confidence = self.kv_confidence = 0.0
        self.ocr_error = None
        self.fio_roi = self.kv_roi = None
        self.image = convert_pdf_to_image(file_path)
        if not self.image:
            self.ocr_error = 'Не удалось открыть PDF'
            self._enqueue_review(self.ocr_error)
            if self.is_running:
                return True
            logger.error("Ошибка загрузки PDF: %s", filename)
            self.total_skipped += 1
            self.current_index += 1
            return self.load_file()
        self.original_width, self.original_height = self.image.size
        self.detected_fio_roi = None
        self.detected_kv_roi = None
        self.reset_zoom()
        for entry in self.fio_entries:
            entry.delete(0, 'end')
        self.kv_entry.delete(0, 'end')
        self.recognized_fios = []
        self.recognized_kv = None
        self.count_label.config(text="👤 ФИО: 0")

        if self.roi_saved and self.saved_fio_roi and self.saved_kv_roi:
            if self.mode == 'manual' and self._adaptive_manual_rois():
                self.update_image()
                self.manual_recognize()
            else:
                self.auto_recognize()
        elif self.mode == "auto":
            self.auto_recognize()
        else:
            self.log_label.config(text="✋ Выделите ФИО и помещение")
            self.fio_roi = self.kv_roi = None
            self.update_image()
        self.parent.update_idletasks()
        return True

    def _archive_original(self, original, oss, filename):
        archive_dir = os.path.join(PROCESSED_FOLDER_PATH, str(oss))
        os.makedirs(archive_dir, exist_ok=True)
        target = os.path.join(archive_dir, filename)
        if os.path.exists(target):
            stem, ext = os.path.splitext(filename)
            target = os.path.join(archive_dir, f"{stem}_{datetime.now().strftime('%H%M%S_%f')}{ext}")
        shutil.move(original, target)
        return target

    def _remove_empty_source_oss(self, oss):
        source_dir = os.path.join(SOURCE_FOLDER_PATH, str(oss))
        try:
            if os.path.isdir(source_dir) and not os.listdir(source_dir):
                os.rmdir(source_dir)
                logger.info('Пустая папка source/%s удалена после обработки', oss)
                return True
        except OSError:
            logger.debug('Не удалось удалить пустую папку source/%s', oss, exc_info=True)
        return False

    def _finalize_current_file(self, fio, kv, require_confidence=False):
        self.last_created_count = 0
        self.last_duplicate_count = 0
        if require_confidence and min(self.fio_confidence, self.kv_confidence) < OCR_REVIEW_THRESHOLD:
            return False, "Низкая уверенность OCR"
        oss, filename = self.pdf_files[self.current_index]
        original = os.path.join(SOURCE_FOLDER_PATH, oss, filename)
        if not os.path.exists(original):
            return False, "Исходный файл уже отсутствует"
        raw_fios = fio if isinstance(fio, (list, tuple, set)) else [fio]
        fios, seen = [], set()
        for raw_fio in raw_fios:
            clean_fio = sanitize_filename_component(raw_fio)
            key = clean_fio.casefold()
            if clean_fio and key not in seen:
                seen.add(key)
                fios.append(clean_fio)
        if not fios:
            return False, "Не найдено ни одного ФИО"
        kv = sanitize_filename_component(kv or '0', '0')
        ready = os.path.join(READY_FOLDER_PATH, oss)
        os.makedirs(ready, exist_ok=True)
        def file_hash(path):
            digest = hashlib.sha256()
            with open(path, 'rb') as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(chunk)
            return digest.hexdigest()

        source_hash = file_hash(original)
        missing, existing = [], []
        for person in fios:
            number = 1
            while True:
                suffix = '' if number == 1 else f' [{number}]'
                new_filename = f"{person}{suffix} ({kv}).pdf"
                new_path = os.path.join(ready, new_filename)
                if not os.path.exists(new_path):
                    missing.append((new_filename, new_path))
                    break
                if file_hash(new_path) == source_hash:
                    existing.append(new_filename)
                    break
                number += 1
        self.last_duplicate_count = len(existing)

        created_paths = []
        try:
            for new_filename, new_path in missing:
                temp_path = new_path + f'.tmp_{threading.get_ident()}'
                shutil.copy2(original, temp_path)
                if os.path.getsize(temp_path) != os.path.getsize(original):
                    try: os.remove(temp_path)
                    except OSError: pass
                    raise IOError(f"Размер копии не совпадает с оригиналом: {new_filename}")
                os.replace(temp_path, new_path)
                created_paths.append(new_path)
        except Exception:
            for path in created_paths:
                try: os.remove(path)
                except OSError: pass
            raise

        if not created_paths:
            duplicate_dir = os.path.join(DUPLICATES_FOLDER_PATH, oss)
            os.makedirs(duplicate_dir, exist_ok=True)
            dup_target = os.path.join(duplicate_dir, filename)
            if os.path.exists(dup_target):
                stem, ext = os.path.splitext(filename)
                dup_target = os.path.join(duplicate_dir, f"{stem}_{datetime.now().strftime('%H%M%S_%f')}{ext}")
            shutil.move(original, dup_target)
            self._remove_empty_source_oss(oss)
            logger.warning("Все результаты уже существуют: %s -> %s", filename, dup_target)
            return False, f"Все {len(existing)} результата уже существуют"

        archived_path = self._archive_original(original, oss, filename)
        self._remove_empty_source_oss(oss)
        self.last_created_count = len(created_paths)
        self.last_action = {
            'original_path': original, 'archived_path': archived_path,
            'ready_path': created_paths[0], 'ready_paths': created_paths,
            'created_count': len(created_paths), 'oss': oss, 'filename': filename,
            'created_at': datetime.now().isoformat()
        }
        message = f"Создано файлов: {len(created_paths)}"
        if existing:
            message += f", уже существовало: {len(existing)}"
        return True, message

    def undo_last_action(self):
        if getattr(self, 'batch_busy', False) and not getattr(self, '_mandatory_training', False):
            return
        action = self.last_action
        if not action:
            messagebox.showinfo("Отмена", "Нет последнего действия для отмены")
            return
        archived = action.get('archived_path')
        original = action.get('original_path')
        ready_paths = action.get('ready_paths') or ([action.get('ready_path')] if action.get('ready_path') else [])
        if not archived or not os.path.exists(archived):
            messagebox.showwarning("Отмена", "Архивный оригинал не найден")
            return
        if not messagebox.askyesno("Отменить последнее действие", f"Вернуть файл {action.get('filename','')} обратно в source?"):
            return
        try:
            os.makedirs(os.path.dirname(original), exist_ok=True)
            if os.path.exists(original):
                raise FileExistsError("В source уже существует файл с таким именем")
            shutil.move(archived, original)
            for ready in ready_paths:
                if ready and os.path.exists(ready):
                    os.remove(ready)
            self.last_action = None
            created_count = int(action.get('created_count', len(ready_paths) or 1))
            self.total_created = max(0, self.total_created - created_count)
            self.total_votes = max(0, self.total_votes - created_count)
            logger.info("Отменено последнее действие: %s", original)
            messagebox.showinfo("Готово", "Последний файл возвращён. Созданная копия удалена.")
        except Exception as exc:
            logger.exception("Ошибка отмены последнего действия")
            messagebox.showerror("Ошибка отмены", str(exc))

    def run_diagnostics(self, show_dialog=True):
        checks = []
        def add(name, ok, detail=''):
            checks.append((name, bool(ok), detail))
        add('Tesseract', os.path.isfile(TESSERACT_PATH), TESSERACT_PATH)
        add('Poppler', os.path.isdir(POPPLER_BIN_PATH), POPPLER_BIN_PATH)
        add('NumPy', NUMPY_AVAILABLE)
        add('OpenCV', OPENCV_AVAILABLE)
        add('EasyOCR (отключён для стабильности)', True, 'используется Tesseract')
        add('Selenium', SELENIUM_AVAILABLE)
        for label, path in [('source', SOURCE_FOLDER_PATH), ('ready', READY_FOLDER_PATH), ('processed', PROCESSED_FOLDER_PATH)]:
            try:
                os.makedirs(path, exist_ok=True)
                probe = os.path.join(path, '.write_test')
                with open(probe, 'w', encoding='utf-8') as f:
                    f.write('ok')
                os.remove(probe)
                add(f'Папка {label}', True, path)
            except Exception as exc:
                add(f'Папка {label}', False, str(exc))
        if show_dialog:
            lines = [f"{'✓' if ok else '✗'} {name}" + (f" — {detail}" if detail and not ok else '') for name, ok, detail in checks]
            title = "Диагностика — всё готово" if all(ok for _,ok,_ in checks) else "Диагностика — есть замечания"
            messagebox.showinfo(title, '\n'.join(lines))
        return checks

    def confirm(self):
        if getattr(self, 'batch_busy', False) and not getattr(self, '_mandatory_training', False):
            return
        fios = [e.get().strip() for e in self.fio_entries if e.get().strip()]
        if not fios:
            if messagebox.askyesno("Нет ФИО", "Ввести вручную?"):
                manual = simpledialog.askstring("Ввод ФИО", "Введите ФИО полностью:", parent=self.parent)
                if manual and manual.strip():
                    fios = [manual.strip()]
                    self.fio_entries[0].delete(0, 'end')
                    self.fio_entries[0].insert(0, manual.strip())
                    self.recognized_fios = [manual.strip()]
                else:
                    return
            else:
                return
        kv = self.kv_entry.get().strip() or "0"
        try:
            ok, message = self._finalize_current_file(fios, kv, require_confidence=False)
            if ok:
                created_count = self.last_created_count
                self.total_created += created_count
                self.total_votes += created_count
                daily_stats.add_ocr(created_count)
                self.daily_ocr_label.config(text=f"OCR: {daily_stats.get_ocr()}")
                logger.info("Подтверждено: %s", message)
            else:
                self.total_skipped += 1
                logger.warning(message)
            if ok or not os.path.exists(os.path.join(SOURCE_FOLDER_PATH, *self.pdf_files[self.current_index])):
                self._resolve_review()
            else:
                self._enqueue_review(message)
                return
            self.current_index += 1
            self.save_progress()
            if not self.is_running:
                self.load_file()
        except Exception as e:
            logger.exception("Ошибка сохранения результата")
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл:\n{e}")

    def confirm_roi_batch(self):
        if not (self.roi_saved and self.saved_fio_roi and self.saved_kv_roi):
            messagebox.showwarning(
                "Пакет по ROI",
                "Сначала выделите области ФИО и помещения, затем нажмите «Сохранить ROI»."
            )
            return
        if self.mode != "manual":
            self.set_mode("manual")
        self.confirm_all(roi_batch=True)

    def confirm_all(self, roi_batch=False):
        if self.batch_busy:
            return
        if self.review_mode:
            messagebox.showinfo('Проверка', 'Подтвердите исключения вручную или выберите ОСС для нового пакета.')
            return
        if not self.pdf_files:
            messagebox.showinfo("Информация", "Нет файлов для обработки")
            return
        title = "ПАКЕТ ПО ROI" if roi_batch else "ВСЁ СРАЗУ"
        prompt = (
            f"Обработать по сохранённым ROI все оставшиеся файлы?\n\n"
            f"Уверенные — автоматически; сомнительные — в очередь проверки.\n"
            f"Осталось: {len(self.pdf_files)-self.current_index}"
            if roi_batch else
            f"Запустить обработку всех файлов? (осталось {len(self.pdf_files)-self.current_index})"
        )
        if not messagebox.askyesno(title, prompt):
            return
        if not roi_batch and self.mode != 'auto':
            self.set_mode('auto')
        self.roi_batch_mode = bool(roi_batch)
        self.batch_busy = True
        self.is_running = True
        self.stop_flag = False
        self.is_paused = False
        self.start_time = time.time()
        self.total_votes = 0
        self.btn_start.config(state=tk.DISABLED)
        self.btn_roi_batch.config(state=tk.DISABLED)
        self.btn_pause.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.NORMAL)
        status_text = "▶ Пакет по ROI" if self.roi_batch_mode else "▶ Выполняется"
        self.status_panel.config(text=status_text, fg=Theme.colors['success'])
        self.status_indicator.config(fg=Theme.colors['success'])
        threading.Thread(target=self._process_all_files, daemon=True).start()

    def _process_all_files(self):
        try:
            while self.current_index < len(self.pdf_files) and not self.stop_flag:
                while self.is_paused and not self.stop_flag:
                    time.sleep(.1)
                if self.stop_flag:
                    break
                loaded = self._ui_call(self.load_file, wait=True)
                if self.stop_flag or not loaded:
                    break
                while self.is_paused and not self.stop_flag:
                    time.sleep(.1)
                if self.stop_flag:
                    break
                try:
                    accepted, reason = self._ui_call(self._batch_decision, wait=True)
                except Exception as exc:
                    accepted, reason = False, f'Ошибка проверки: {exc}'
                if self.stop_flag:
                    break
                if not accepted:
                    self._enqueue_review(reason)
                    self._ui_call(self.log_label.config, text=f'В очередь проверки: {reason}')
                else:
                    try:
                        ok, message = self._finalize_current_file(
                            self.recognized_fios, self.recognized_kv, require_confidence=False)
                        if ok:
                            count = self.last_created_count
                            self.total_created += count
                            self.total_votes += count
                            daily_stats.add_ocr(count)
                            self._resolve_review()
                            self._ui_call(self.daily_ocr_label.config, text=f'OCR: {daily_stats.get_ocr()}')
                        elif not os.path.exists(os.path.join(SOURCE_FOLDER_PATH, *self.pdf_files[self.current_index])):
                            self._resolve_review()
                            self.total_skipped += 1
                        else:
                            self._enqueue_review(message)
                    except Exception as exc:
                        self._enqueue_review(f'Ошибка сохранения: {exc}')
                self.current_index += 1
                self.save_progress()
            elapsed = time.time() - (self.start_time or time.time())
            stats.update_ocr(self.total_created, self.total_skipped, elapsed, self.total_votes)
            self._ui_call(self._finish_batch_ui)
        except Exception as exc:
            logger.exception('Ошибка пакетной обработки')
            self._ui_call(self._batch_error_ui, str(exc))
        finally:
            self.is_running = False
            self.roi_batch_mode = False

    def _finish_batch_ui(self):
        self.batch_busy = False
        self.is_running = False
        self.btn_start.config(state=tk.NORMAL)
        self.btn_roi_batch.config(state=tk.NORMAL if self.roi_saved and self.mode == "manual" else tk.DISABLED)
        self.btn_pause.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.DISABLED)
        self.btn_resume.config(state=tk.DISABLED)
        if not self.stop_flag and self.current_index >= len(self.pdf_files):
            self.status_panel.config(text="Завершено", fg=Theme.colors['success'])
            self.status_indicator.config(fg=Theme.colors['success'])
            if self.review_queue:
                self.status_panel.config(text=f'Проверить: {len(self.review_queue)}', fg=Theme.colors['warning'])
                self.open_review_queue()
            else:
                self.show_summary()
        elif self.stop_flag:
            self.status_panel.config(text="Остановлен", fg=Theme.colors['error'])
            self.status_indicator.config(fg=Theme.colors['error'])

    def _batch_error_ui(self, message):
        self.batch_busy = False
        self.is_running = False
        self.status_panel.config(text="Ошибка", fg=Theme.colors['error'])
        self.status_indicator.config(fg=Theme.colors['error'])
        self.btn_start.config(state=tk.NORMAL)
        self.btn_roi_batch.config(state=tk.NORMAL if self.roi_saved and self.mode == "manual" else tk.DISABLED)
        self.btn_pause.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.DISABLED)
        self.btn_resume.config(state=tk.DISABLED)
        messagebox.showerror("Ошибка", f"Произошла ошибка:\n{message}")

    def skip_file(self):
        if getattr(self, 'batch_busy', False) and not getattr(self, '_mandatory_training', False):
            return
        logger.info("Текущий файл пропущен")
        self.total_skipped += 1
        self.current_index += 1
        self.save_progress()
        if self.is_running and self.is_paused:
            self.is_paused = False
            self.btn_pause.config(state=tk.NORMAL)
            self.btn_resume.config(state=tk.DISABLED)
            self.status_panel.config(text="▶ Выполняется", fg=Theme.colors['success'])
            self.status_indicator.config(fg=Theme.colors['success'])
        if not self.is_running:
            self.load_file()

    def show_summary(self):
        self.save_corrections()
        if os.path.exists(PROGRESS_FILE_PATH):
            try:
                os.remove(PROGRESS_FILE_PATH)
            except Exception:
                logger.debug("Не критичная ошибка очистки", exc_info=True)
        avg_time = sum(self.ocr_times)/len(self.ocr_times) if self.ocr_times else 0
        avg_vote = (time.time() - self.start_time) / self.total_votes if self.start_time and self.total_votes > 0 else 0
        self.btn_start.config(state=tk.NORMAL)
        self.btn_pause.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.DISABLED)
        self.btn_resume.config(state=tk.DISABLED)
        self.status_panel.config(text="✅ Готов", fg=Theme.colors['success'])
        self.status_indicator.config(fg=Theme.colors['success'])
        messagebox.showinfo("Готово",
            f"✅ Создано: {self.total_created}\n"
            f"⏭ Пропущено: {self.total_skipped}\n"
            f"🗳️ Голосов: {self.total_votes}\n"
            f"⏱️ Среднее время на голос: {avg_vote:.1f}с\n"
            f"🧠 Исправлений: {len(self.fio_corrections) + len(self.room_corrections)}\n"
            f"⚡ Среднее время OCR: {avg_time:.2f}с\n"
            f"⚠ На ручной проверке: {len(self.review_queue)}")
        if self.review_queue:
            return
        try:
            self.parent.after(150, self.open_robot_helper_tab)
        except Exception:
            pass

    def on_fio_edit(self, idx):
        if getattr(self, 'batch_busy', False) and not getattr(self, '_mandatory_training', False):
            return
        if idx >= len(self.recognized_fios) or not self.last_raw_fio: return
        current = self.fio_entries[idx].get().strip()
        if not current: return
        old = self.recognized_fios[idx]
        if old != current:
            logger.info("Обучение ФИО: %s -> %s", old, current)
            self.fio_corrections[old] = current
            self.save_corrections()
            self.learn_label.config(text=f"🧠 {len(self.fio_corrections) + len(self.room_corrections)}")
            self.recognized_fios[idx] = current
            self.update_image()

    def on_kv_edit(self, event):
        if getattr(self, 'batch_busy', False) and not getattr(self, '_mandatory_training', False):
            return
        if not self.last_raw_kv: return
        current = self.kv_entry.get().strip()
        if not current: return
        if self.recognized_kv and self.recognized_kv != current:
            logger.info("Ручная корректировка помещения: %s -> %s", self.recognized_kv, current)
            self.recognized_kv = current
            self.update_image()

    def re_recognize(self):
        if getattr(self, 'batch_busy', False) and not getattr(self, '_mandatory_training', False):
            return
        if not self.image: return
        if self.mode == "auto":
            self.auto_recognize()
        else:
            if self.fio_roi and self.kv_roi:
                self.manual_recognize()
            else:
                messagebox.showinfo("Внимание", "Выделите обе области")

    def toggle_pause(self):
        if self.is_running:
            self.is_paused = not self.is_paused
            if self.is_paused:
                self.btn_pause.config(state=tk.DISABLED)
                self.btn_resume.config(state=tk.NORMAL)
                self.status_panel.config(text="⏸ На паузе", fg=Theme.colors['warning'])
                self.status_indicator.config(fg=Theme.colors['warning'])
            else:
                self.btn_pause.config(state=tk.NORMAL)
                self.btn_resume.config(state=tk.DISABLED)
                self.status_panel.config(text="▶ Выполняется", fg=Theme.colors['success'])
                self.status_indicator.config(fg=Theme.colors['success'])

    def resume_process(self):
        if self.is_running and self.is_paused:
            self.is_paused = False
            self.btn_pause.config(state=tk.NORMAL)
            self.btn_resume.config(state=tk.DISABLED)
            self.status_panel.config(text="▶ Выполняется", fg=Theme.colors['success'])
            self.status_indicator.config(fg=Theme.colors['success'])

    def stop_process(self):
        self.stop_flag = True
        self.is_running = False
        self.is_paused = False
        self.roi_batch_mode = False
        self.btn_start.config(state=tk.NORMAL)
        self.btn_roi_batch.config(state=tk.NORMAL if self.roi_saved and self.mode == "manual" else tk.DISABLED)
        self.btn_pause.config(state=tk.DISABLED)
        self.btn_resume.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.DISABLED)
        self.status_panel.config(text="⏹ Остановлен", fg=Theme.colors['error'])
        self.status_indicator.config(fg=Theme.colors['error'])
        self.log_label.config(text="⏹ Процесс остановлен")
        play_sound()

# =============================================================================
# РОБОТ-ПОМОЩНИК (ВНЕСЕНИЕ) — ПОРЯДОК ШАГОВ СОХРАНЁН
# =============================================================================
class RobotHelper:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.theme = Theme()
        self.stop_flag = False
        self.driver = None
        self.total_processed = 0
        self.total_errors = 0
        self.total_votes = 0
        self.total_files = 0
        self.start_time = None
        self.last_bulletin_url = None
        self.operator_help_required = []
        self.input_retry_reasons = {}
        self.build_ui()

    def build_ui(self):
        c = Theme.colors
        main = tk.Frame(self.parent, bg=c['bg'])
        main.pack(fill=tk.BOTH, expand=True)
        top_bar = tk.Frame(main, bg=c['card_bg'], height=62,
                           highlightthickness=1, highlightbackground=c['border'])
        top_bar.pack(fill=tk.X, padx=8, pady=(8,5))
        top_bar.pack_propagate(False)
        tk.Label(top_bar, text="Внесение", bg=c['card_bg'], fg=c['fg'],
                 font=("Segoe UI Semibold", 17)).pack(side=tk.LEFT, padx=(18,8))
        tk.Label(top_bar, text="ready  →  ОСС  →  внесено", bg=c['card_bg'],
                 fg=c['accent'], font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=8)
        self.status_label = tk.Label(top_bar, text="●  Готов", bg=c['card_bg'],
                                     fg=c['success'], font=("Segoe UI Semibold", 9))
        self.status_label.pack(side=tk.RIGHT, padx=15)
        content = tk.Frame(main, bg=c['bg'])
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=14)
        if not SELENIUM_AVAILABLE:
            tk.Label(content, text="⚠️ Selenium не установлен!", bg=c['bg'], fg=c['error'], font=("Segoe UI", 16, "bold")).pack(pady=30)
            tk.Label(content, text="Установите:\npip install selenium webdriver-manager", bg=c['bg'], fg=c['fg'], font=("Segoe UI", 12)).pack()
            return
        btn_frame = tk.Frame(content, bg=c['card_bg'],
                             highlightthickness=1, highlightbackground=c['border'])
        btn_frame.pack(fill=tk.X, pady=(0,12), ipady=8)
        btn_style = {"bg": c['btn'], "fg": c['fg'], "activebackground": c['hover'],
                     "activeforeground": c['fg'], "font": ("Segoe UI Semibold", 10),
                     "relief": tk.FLAT, "bd": 0, "padx": 16, "pady": 10,
                     "width": 20, "cursor": "hand2"}
        self.btn_run = tk.Button(btn_frame, text="🚀 Запуск Ввода (выбор ОСС)", command=self.start_automation, **btn_style)
        self.btn_run.pack(side=tk.LEFT, padx=5, pady=5)
        self.btn_problems = tk.Button(
            btn_frame, text="🧑 Внесение проблем",
            command=self.start_problem_automation, **btn_style)
        self.btn_problems.pack(side=tk.LEFT, padx=5, pady=5)
        self.btn_clean = tk.Button(btn_frame, text="🧹 Очистить source / ready", command=self.clean_folders, **btn_style)
        self.btn_clean.pack(side=tk.LEFT, padx=5, pady=5)
        btn_stop_style = {"bg": c['error'], "fg": "white", "font": ("Segoe UI Semibold", 10),
                          "relief": tk.FLAT, "bd": 0, "padx": 20, "pady": 10,
                          "width": 22, "state": tk.NORMAL, "cursor": "hand2"}
        self.btn_stop = tk.Button(btn_frame, text="⛔ Остановить процесс", command=self.stop_process, **btn_stop_style)
        self.btn_stop.pack(side=tk.LEFT, padx=5, pady=5)
        progress_frame = tk.Frame(content, bg=c['bg'])
        progress_frame.pack(fill=tk.X, pady=10, padx=20)
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("green.Horizontal.TProgressbar", background=c['success'],
                        troughcolor=c['btn'], bordercolor=c['btn'],
                        lightcolor=c['success'], darkcolor=c['success'], thickness=12)
        self.progress_bar = ttk.Progressbar(progress_frame, length=400, mode='determinate', style="green.Horizontal.TProgressbar")
        self.progress_bar.pack(fill=tk.X, pady=5)
        progress_info_frame = tk.Frame(progress_frame, bg=c['bg'])
        progress_info_frame.pack(fill=tk.X, pady=2)
        self.progress_text = tk.Label(progress_info_frame, text="0 / 0 | Внесено: 0 | Ошибок: 0 | Голосов: 0",
                                      bg=c['bg'], fg=c['success'], font=("Segoe UI Semibold", 11))
        self.progress_text.pack(side=tk.LEFT, padx=5)
        self.progress_percent = tk.Label(progress_info_frame, text="0%", bg=c['bg'],
                                         fg=c['success'], font=("Segoe UI Semibold", 11))
        self.progress_percent.pack(side=tk.RIGHT, padx=5)
        self.detail_text = tk.Label(progress_frame, text="📊 Ожидание запуска...", bg=c['bg'], fg=c['fg'], font=("Segoe UI", 10))
        self.detail_text.pack(pady=2)
        log_frame = tk.Frame(content, bg=c['card_bg'], highlightthickness=1,
                             highlightbackground=c['border'])
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.log_text = tk.Text(log_frame, bg=c['entry'], fg=c['fg'], font=("Consolas", 8), wrap=tk.WORD, height=10, relief=tk.FLAT)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar = tk.Scrollbar(log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.log_text.yview)
        self.log_text.insert(tk.END, "💡 Готов к работе (АВТОМАТИЗАЦИЯ - МАКСИМАЛЬНО УСКОРЕННАЯ ВЕРСИЯ)\n")
        self.log_text.insert(tk.END, "📌 Робот берет файлы из папки ready\n📌 После ввода файлы перемещаются в ready/ОСС/внесено/\n")
        self.log_text.insert(tk.END, "🔁 Сбойные PDF автоматически проходят второй круг; при повторном сбое нужна помощь оператора\n")
        self.log_text.insert(tk.END, "🧑 'Внесение проблем' повторяет PDF из problems и при сбое ждёт оператора на открытой странице\n")
        self.log_text.insert(tk.END, "⚡ МАКСИМАЛЬНО УСКОРЕННЫЙ режим (оптимизированные задержки 0.01с)\n")
        self.log_text.insert(tk.END, "⛔ Кнопка 'Остановить процесс' - останавливает текущую обработку\n")

    def log(self, message):
        if threading.current_thread() is not threading.main_thread():
            try:
                self.parent.after(0, self.log, message)
            except Exception:
                logger.exception("Не удалось показать сообщение внесения: %s", message)
                pass
            return
        logger.info("Внесение: %s", message)
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.update()

    def fix_ready_filenames(self):
        self.log("🔧 Запуск исправления имен файлов в ready...")
        fixed_count, errors = fix_filenames_in_ready()
        if fixed_count == 0 and not errors:
            self.log("✅ Нет файлов для исправления")
            messagebox.showinfo("Готово", "Нет файлов для исправления\nВсе имена корректны.")
            return
        msg = f"✅ Исправлено файлов: {fixed_count}\n"
        if errors:
            msg += f"⚠️ Ошибок: {len(errors)}\n"
            for err in errors[:5]:
                msg += f"  • {err}\n"
            if len(errors) > 5:
                msg += f"  • ... и еще {len(errors)-5} ошибок\n"
        self.log(msg)
        messagebox.showinfo("Результат исправления", msg)

    @staticmethod
    def _pdfs_below(root, skip_done=False):
        found=[]
        if not os.path.isdir(root): return found
        for folder,_,files in os.walk(root):
            relative=os.path.relpath(folder,root)
            parts={part.casefold() for part in relative.split(os.sep)}
            if skip_done and 'внесено' in parts: continue
            found.extend(os.path.join(folder,name) for name in files if name.lower().endswith('.pdf'))
        return found

    @staticmethod
    def _sha256_file(path):
        digest = hashlib.sha256()
        with open(path, 'rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _unique_pdf_path(folder, filename):
        target = os.path.join(folder, filename)
        if not os.path.exists(target):
            return target
        stem, ext = os.path.splitext(filename)
        number = 2
        while True:
            target = os.path.join(folder, f'{stem} [{number}]{ext}')
            if not os.path.exists(target):
                return target
            number += 1

    def _input_entries(self, oss):
        entries = []
        ready_folder = os.path.join(READY_FOLDER_PATH, oss)
        if not os.path.isdir(ready_folder):
            return entries
        for name in os.listdir(ready_folder):
            path = os.path.join(ready_folder, name)
            if os.path.isfile(path) and name.lower().endswith('.pdf'):
                entries.append((name, path, False))
        return entries

    def _problem_entries(self, oss):
        entries = []
        problem_folder = os.path.join(PROBLEMS_FOLDER_PATH, oss)
        if not os.path.isdir(problem_folder):
            return entries
        for name in os.listdir(problem_folder):
            path = os.path.join(problem_folder, name)
            if os.path.isfile(path) and name.lower().endswith('.pdf'):
                entries.append((name, path, False))
        return entries

    def _operator_finish_problem(self, source_path, oss, filename, reason, done_folder):
        self.log(f"🧑 ТРЕБУЕТСЯ ПОМОЩЬ ОПЕРАТОРА: {filename} — {reason}")
        self.detail_text.config(text=f"🧑 Требуется помощь оператора: {filename}")
        answer = messagebox.askyesnocancel(
            "Требуется помощь оператора",
            f"Автоматически внести файл не удалось:\n{filename}\n\n"
            f"Причина: {reason}\n\n"
            "Браузер оставлен на текущей странице. Завершите внесение вручную.\n\n"
            "ДА — внесение завершено, убрать PDF из problems.\n"
            "НЕТ — оставить PDF в problems и перейти к следующему.\n"
            "ОТМЕНА — остановить очередь проблем.")
        if answer is None:
            self.stop_flag = True
            self.log(f"⏹ Очередь проблем остановлена оператором; {filename} оставлен в problems")
            return 'stop'
        if answer is False:
            self.log(f"⏭️ Оператор пропустил файл; {filename} оставлен в problems")
            return 'skip'
        if not os.path.exists(source_path):
            self.log(f"⚠️ После ручного внесения исходный PDF уже отсутствует: {filename}")
            return 'done'
        os.makedirs(done_folder, exist_ok=True)
        target = self._unique_pdf_path(done_folder, filename)
        shutil.move(source_path, target)
        self.log(f"✅ Оператор подтвердил внесение: {filename}; PDF перенесён в внесено")
        return 'done'

    @staticmethod
    def _input_retry_key(oss, filename):
        return str(oss), str(filename).casefold()

    def _record_input_failure(self, source_path, oss, filename, reason, is_retry=False):
        reason = str(reason or 'Неизвестная ошибка внесения')
        key = self._input_retry_key(oss, filename)
        if not is_retry:
            self.input_retry_reasons[key] = reason
            self.log(f"⚠️ ПЕРВЫЙ КРУГ: {filename} — {reason}")
            self.log("🔁 Файл поставлен во второй круг внесения")
            return 'retry'

        problem_folder = os.path.join(PROBLEMS_FOLDER_PATH, oss)
        os.makedirs(problem_folder, exist_ok=True)
        target = self._unique_pdf_path(problem_folder, filename)
        shutil.move(source_path, target)
        record = {
            'file': os.path.basename(target),
            'oss': str(oss),
            'attempts': 2,
            'first_reason': self.input_retry_reasons.get(key, 'Причина первого сбоя не записана'),
            'last_reason': reason,
            'last_failed_at': datetime.now().isoformat(timespec='seconds'),
            'operator_help_required': True,
        }
        self.operator_help_required.append(record)
        self.log(f"❌ ВТОРОЙ КРУГ: {filename} — {reason}")
        self.log(f"🧑 ТРЕБУЕТСЯ ПОМОЩЬ ОПЕРАТОРА: {filename}")
        self.log(f"📁 PDF перемещён в problems/{oss}; внесите его вручную")
        return 'operator'

    def _clear_input_failure(self, pdf_path):
        return None

    def _wait_input_confirmation(self, timeout=12.0):
        deadline = time.monotonic() + max(1.0, float(timeout))
        while time.monotonic() < deadline and not self.stop_flag:
            try:
                ok_buttons = self.driver.find_elements(By.XPATH, "//button[contains(., 'ОК')]")
                if any(button.is_displayed() and button.is_enabled() for button in ok_buttons):
                    return True
                body = self.driver.find_element(By.TAG_NAME, 'body').text.casefold()
                if any(text in body for text in (
                        'данные внесены', 'успешно внесен', 'успешно внесён',
                        'внесение завершено')):
                    return True
            except Exception:
                pass
            time.sleep(0.2)
        return False

    def clean_folders(self):
        if self.driver or str(self.btn_run.cget('state'))==str(tk.DISABLED):
            messagebox.showwarning('Очистка','Сначала дождитесь завершения Робота-помощника.')
            return
        pending_source=self._pdfs_below(SOURCE_FOLDER_PATH)
        pending_ready=self._pdfs_below(READY_FOLDER_PATH,skip_done=True)
        if pending_source or pending_ready:
            messagebox.showwarning('Работа не завершена',
                f'Очистка отменена, чтобы не потерять документы.\n\n'
                f'Не завершено OCR в source: {len(pending_source)}\n'
                f'Не внесено в ready: {len(pending_ready)}')
            return
        roots=[('source',SOURCE_FOLDER_PATH),('ready',READY_FOLDER_PATH),('pdf',PDF_FOLDER_PATH)]
        total=sum(len(os.listdir(path)) for _,path in roots if os.path.isdir(path))
        if not total:
            messagebox.showinfo('Очистка','Папки source, ready и pdf уже пусты.')
            return
        if not messagebox.askyesno('Очистить рабочие папки?',
                'Обработка завершена. Source, ready и pdf будут очищены.\n\n'
                'Для безопасности всё будет перенесено в архив восстановления.\nПродолжить?'):
            return
        archive_root=os.path.join(SCRIPT_DIR,'cleanup_archive',datetime.now().strftime('%Y%m%d_%H%M%S'))
        moved=0
        try:
            for label,root in roots:
                if not os.path.isdir(root): continue
                destination=os.path.join(archive_root,label)
                for name in os.listdir(root):
                    os.makedirs(destination,exist_ok=True)
                    shutil.move(os.path.join(root,name),os.path.join(destination,name)); moved+=1
            self.log(f'🧹 Папки очищены. В архив перенесено: {moved}')
            messagebox.showinfo('Готово',f'Source, ready и pdf очищены.\n\nАрхив восстановления:\n{archive_root}')
        except Exception as exc:
            logger.exception('Ошибка безопасной очистки')
            messagebox.showerror('Ошибка очистки',f'Очистка остановлена:\n{exc}\n\nУже перенесённые файлы лежат в:\n{archive_root}')

    def update_progress(self, current, total, processed=0, errors=0, votes=0):
        if total > 0:
            percent = int((current / total) * 100)
            self.progress_bar['value'] = percent
            self.progress_percent.config(text=f"{percent}%")
        else:
            self.progress_bar['value'] = 0
            self.progress_percent.config(text="0%")
        elapsed = max(0.0, time.time() - self.start_time) if self.start_time else 0.0
        avg = elapsed / votes if votes else 0.0
        speed = (votes * 60.0 / elapsed) if elapsed > 0 and votes else 0.0
        speed_text = f" | {avg:.1f} с/голос | {speed:.1f} голос/мин" if votes else ""
        self.progress_text.config(
            text=f"{current} / {total} | Внесено: {processed} | Ошибок: {errors} | Голосов: {votes}{speed_text}")
        self.parent.update()

    def start_automation(self):
        if not SELENIUM_AVAILABLE:
            messagebox.showerror("Ошибка", "Selenium не установлен!")
            return
        self.log("🚀 Запуск (АВТОМАТИЗАЦИЯ - МАКСИМАЛЬНО УСКОРЕННЫЙ РЕЖИМ)...")
        oss_folders = []
        candidates = (os.listdir(READY_FOLDER_PATH)
                      if os.path.isdir(READY_FOLDER_PATH) else [])
        for item in candidates:
            if self._input_entries(item):
                oss_folders.append(item)
        if not oss_folders:
            messagebox.showwarning("Нет данных", "В папке 'ready' нет ОСС с PDF файлами")
            return
        oss_folders = sorted(oss_folders, key=int) if all(f.isdigit() for f in oss_folders) else oss_folders
        choice = simpledialog.askstring("Выбор ОСС", f"Найдены в ready: {', '.join(oss_folders)}\nВведите номер ОСС или 'all':")
        if choice is None: return
        choice = choice.strip()
        if choice.lower() == 'all':
            oss_list = oss_folders
        elif choice in oss_folders:
            oss_list = [choice]
        else:
            messagebox.showerror("Ошибка", f"ОСС '{choice}' не найден в папке ready")
            return
        self.stop_flag = False
        self.btn_run.config(state=tk.DISABLED)
        self.btn_problems.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.total_processed = 0; self.total_errors = 0; self.total_votes = 0; self.total_files = 0
        self.operator_help_required = []
        self.input_retry_reasons = {}
        self.start_time = time.time()
        self.progress_bar['value'] = 0
        self.progress_percent.config(text="0%")
        self.detail_text.config(text="🔄 Подсчет файлов...")
        for oss in oss_list:
            self.total_files += len(self._input_entries(oss))
        self.progress_text.config(text=f"0 / {self.total_files} | Внесено: 0 | Ошибок: 0 | Голосов: 0")
        threading.Thread(target=self.process_oss, args=(oss_list,), daemon=True).start()

    def start_problem_automation(self):
        if not SELENIUM_AVAILABLE:
            messagebox.showerror("Ошибка", "Selenium не установлен!")
            return
        oss_folders = []
        candidates = (os.listdir(PROBLEMS_FOLDER_PATH)
                      if os.path.isdir(PROBLEMS_FOLDER_PATH) else [])
        for item in candidates:
            if self._problem_entries(item):
                oss_folders.append(item)
        if not oss_folders:
            messagebox.showinfo("Внесение проблем", "В папке problems нет PDF файлов")
            return
        oss_folders = (sorted(oss_folders, key=int)
                       if all(f.isdigit() for f in oss_folders) else oss_folders)
        choice = simpledialog.askstring(
            "Внесение проблем",
            f"Найдены ОСС в problems: {', '.join(oss_folders)}\n"
            "Введите номер ОСС или 'all':")
        if choice is None:
            return
        choice = choice.strip()
        if choice.lower() == 'all':
            oss_list = oss_folders
        elif choice in oss_folders:
            oss_list = [choice]
        else:
            messagebox.showerror("Ошибка", f"ОСС '{choice}' не найден в папке problems")
            return
        self.stop_flag = False
        self.btn_run.config(state=tk.DISABLED)
        self.btn_problems.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.total_processed = 0
        self.total_errors = 0
        self.total_votes = 0
        self.total_files = sum(len(self._problem_entries(oss)) for oss in oss_list)
        self.operator_help_required = []
        self.input_retry_reasons = {}
        self.start_time = time.time()
        self.progress_bar['value'] = 0
        self.progress_percent.config(text="0%")
        self.progress_text.config(
            text=f"0 / {self.total_files} | Внесено: 0 | Ошибок: 0 | Голосов: 0")
        self.detail_text.config(text="🧑 Подготовка очереди problems...")
        self.log(f"🧑 Запуск внесения проблем: {self.total_files} PDF")
        threading.Thread(
            target=self.process_oss, args=(oss_list, True), daemon=True).start()

    def _offer_cleanup(self):
        if messagebox.askyesno('Работа полностью завершена',
                'OCR и внесение в систему завершены без ошибок.\n\n'
                'Очистить source, ready и pdf сейчас?\n'
                'Файлы будут перенесены в архив восстановления.'):
            self.clean_folders()

    def fast_click(self, driver, text, timeout=0.3):
        try:
            button = WebDriverWait(
                driver, timeout, poll_frequency=0.05
            ).until(EC.element_to_be_clickable(
                (By.XPATH, f"//button[contains(text(), '{text}')]")))
            driver.execute_script("arguments[0].click();", button)
            return True
        except:
            try:
                clicked = driver.execute_script(f"""
                    var buttons = document.querySelectorAll('button');
                    for (var i=0; i<buttons.length; i++) {{
                        if (buttons[i].textContent.includes('{text}')) {{
                            buttons[i].click();
                            return true;
                        }}
                    }}
                    return false;
                """)
                return bool(clicked)
            except: return False

    def open_owner_form(self, bulletin_url):
        for attempt in range(3):
            if self.stop_flag:
                return False
            try:
                self.driver.get(bulletin_url)
                if not self.fast_click(self.driver, "Продолжить", 2.0):
                    raise RuntimeError('Кнопка «Продолжить» ещё недоступна')
                WebDriverWait(self.driver, 5, poll_frequency=0.05).until(
                    EC.presence_of_element_located((By.ID, "lastName")))
                return True
            except Exception as exc:
                if self.stop_flag:
                    return False
                if attempt < 2:
                    self.log(f"  ⏳ Жду форму собственника, попытка {attempt + 2}/3")
                    time.sleep(0.7)
                else:
                    raise RuntimeError(f'Не удалось открыть форму собственника: {exc}')
        return False

    def fast_fill(self, driver, field_id, value):
        try:
            field = driver.find_element(By.ID, field_id)
            value = str(value or '')
            try:
                driver.execute_script("""
                    const el = arguments[0], value = arguments[1];
                    const setter = Object.getOwnPropertyDescriptor(
                        HTMLInputElement.prototype, 'value').set;
                    setter.call(el, value);
                    el.dispatchEvent(new Event('input', {bubbles:true}));
                    el.dispatchEvent(new Event('change', {bubbles:true}));
                    el.dispatchEvent(new Event('blur', {bubbles:true}));
                """, field, value)
                if str(field.get_attribute('value') or '') == value:
                    return True
            except Exception:
                pass
            field.clear()
            field.send_keys(value)
            return str(field.get_attribute('value') or '') == value
        except Exception:
            return False

    def fast_checkbox(self, driver):
        try:
            driver.execute_script("""
                var checkboxes = document.querySelectorAll('input[type="checkbox"]');
                for (var i=0; i<checkboxes.length; i++) {
                    if (checkboxes[i].offsetParent !== null && !checkboxes[i].checked) {
                        checkboxes[i].click();
                        return true;
                    }
                }
            """)
            return True
        except: return False

    def stop_process(self):
        self.stop_flag = True
        self.log("⏹ Остановка процесса...")
        self.btn_stop.config(state=tk.DISABLED)
        self.btn_run.config(state=tk.DISABLED)
        self.btn_problems.config(state=tk.DISABLED)
        self.detail_text.config(text="⏳ Завершаю текущий шаг; дождитесь остановки")

    def _input_browser_unavailable(self, error):
        reason = str(error).lower()
        fatal = ('invalid session id', 'no such window', 'chrome not reachable',
                 'not connected to devtools', 'disconnected', 'winerror 10061',
                 'connection refused')
        if any(token in reason for token in fatal):
            return True
        driver = self.driver
        if driver is None:
            return True
        process = getattr(getattr(driver, 'service', None), 'process', None)
        return process is not None and process.poll() is not None

    def process_oss(self, oss_list, problems_mode=False):
        offer_cleanup = False
        try:
            self.log("🔄 Запуск Chrome (ускоренный)...")
            options = webdriver.ChromeOptions()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-setuid-sandbox')
            options.add_argument('--remote-debugging-port=0')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-application-cache')
            options.add_argument('--disable-web-security')
            options.add_argument('--disable-features=VizDisplayCompositor')
            options.add_argument('--disable-background-timer-throttling')
            options.add_argument('--disable-backgrounding-occluded-windows')
            options.add_argument('--disable-renderer-backgrounding')
            options.add_argument('--disable-component-update')
            options.add_argument('--disable-domain-reliability')
            options.add_argument('--disable-client-side-phishing-detection')
            options.add_argument('--disable-windows10-custom-titlebar')
            options.add_argument('--disable-notifications')
            options.add_argument('--mute-audio')
            options.add_argument('--no-default-browser-check')
            options.add_argument('--no-first-run')
            options.add_argument('--disable-default-apps')
            options.add_argument('--disable-popup-blocking')
            options.add_argument('--disable-prompt-on-repost')
            options.add_argument('--disable-hang-monitor')
            options.add_argument('--disable-sync')
            options.add_argument('--disable-browser-side-navigation')
            options.add_argument('--disable-crash-reporter')
            options.add_argument('--disable-in-process-stack-traces')
            options.add_argument('--disable-logging')
            options.add_argument('--disable-breakpad')
            options.add_argument('--disable-back-forward-cache')
            options.add_argument('--disable-ipc-flooding-protection')
            prefs = {"credentials_enable_service": False, "profile.password_manager_enabled": False,
                     "profile.default_content_setting_values.notifications": 2, "profile.block_third_party_cookies": True}
            options.add_experimental_option("prefs", prefs)
            service = ChromeService()
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.set_page_load_timeout(10)
            self.driver.implicitly_wait(1)
            self.log("✅ Chrome запущен")
            for attempt in range(2):
                try:
                    self.driver.get("https://int.ed.mos.ru/")
                    break
                except:
                    if attempt < 1:
                        self.driver.quit()
                        time.sleep(1)
                        self.driver = webdriver.Chrome(service=service, options=options)
                        self.driver.set_page_load_timeout(10)
                        self.driver.implicitly_wait(1)
            self.log("🌐 Открыта страница входа")
            messagebox.showinfo("Вход", "Войдите в систему и нажмите OK")
            current = 0
            for oss in oss_list:
                if self.stop_flag: break
                oss_folder = os.path.join(
                    PROBLEMS_FOLDER_PATH if problems_mode else READY_FOLDER_PATH, oss)
                entries = (self._problem_entries(oss) if problems_mode
                           else self._input_entries(oss))
                if not entries: continue
                queue_name = 'problems' if problems_mode else 'ready'
                self.log(f"📂 Обработка ОСС {oss} из {queue_name} ({len(entries)} файлов)")
                self.detail_text.config(
                    text=f"📂 ОСС {oss}, {queue_name} ({len(entries)} файлов)")
                bulletin_url = f"https://int.ed.mos.ru/operator-oss/{oss}/bulletin"
                done_folder = os.path.join(READY_FOLDER_PATH, oss, "внесено")
                os.makedirs(done_folder, exist_ok=True)
                done_hashes = {}
                for archived_name in os.listdir(done_folder):
                    archived_path = os.path.join(done_folder, archived_name)
                    if not (os.path.isfile(archived_path) and archived_name.lower().endswith('.pdf')):
                        continue
                    try:
                        key = (os.path.getsize(archived_path), self._sha256_file(archived_path))
                        done_hashes.setdefault(key, archived_path)
                    except OSError:
                        logger.debug('Не удалось проиндексировать PDF: %s', archived_path, exc_info=True)
                for filename, ready_path, is_retry in entries:
                    if self.stop_flag: break
                    current += 1
                    self.update_progress(current, self.total_files, self.total_processed, self.total_errors, self.total_votes)
                    self.detail_text.config(text=f"📄 {filename}")
                    if is_retry:
                        first_reason = self.input_retry_reasons.get(
                            self._input_retry_key(oss, filename), 'причина не записана')
                        self.log(f"🔁 ВТОРОЙ КРУГ: {filename}; первый сбой: {first_reason}")
                    done_path = os.path.join(done_folder, filename)
                    try:
                        ready_size = os.path.getsize(ready_path)
                        ready_hash = self._sha256_file(ready_path)
                        exact_done = done_hashes.get((ready_size, ready_hash))
                    except OSError as hash_exc:
                        ready_size = ready_hash = exact_done = None
                        self.log(f'⚠️ Не удалось проверить дубль {filename}: {hash_exc}')
                    if exact_done:
                        duplicate_dir = os.path.join(DUPLICATES_FOLDER_PATH, oss)
                        os.makedirs(duplicate_dir, exist_ok=True)
                        duplicate_target = self._unique_pdf_path(duplicate_dir, filename)
                        try:
                            shutil.move(ready_path, duplicate_target)
                            self._clear_input_failure(ready_path)
                            self.log(f'⏭️ Точный дубль: {filename} уже внесён как '
                                     f'{os.path.basename(exact_done)}; повторная отправка пропущена')
                        except OSError as move_exc:
                            self.log(f'⚠️ Точный дубль не отправлен повторно, но остался в ready: {move_exc}')
                        continue
                    if os.path.exists(done_path):
                        self.log(f'🔁 Имя {filename} совпадает, но содержимое другое — обрабатываю как новый PDF')
                    self.log(f"📄 Обработка: {filename}")
                    try:
                        fios_list, premise_number = extract_all_fios_from_filename(filename)
                        if not fios_list or not premise_number:
                            raise RuntimeError(
                                'Не удалось извлечь ФИО или номер помещения из имени файла')
                        for i, fio_data in enumerate(fios_list):
                            if self.stop_flag: break
                            fio_num = i+1
                            fio_name = f"{fio_data['last_name']} {fio_data['first_name']}"
                            if fio_data.get('middle_name'): fio_name += f" {fio_data['middle_name']}"
                            self.log(f"  👤 Внесение ФИО {fio_num}: {fio_name}")
                            if not self.open_owner_form(bulletin_url):
                                if self.stop_flag:
                                    break
                                raise RuntimeError('Не удалось открыть форму собственника')
                            if not self.fast_fill(self.driver, "lastName", fio_data.get('last_name','')):
                                raise RuntimeError('Не удалось заполнить фамилию собственника')
                            if not self.fast_fill(self.driver, "firstName", fio_data.get('first_name','')):
                                raise RuntimeError('Не удалось заполнить имя собственника')
                            if fio_data.get('middle_name') and not self.fast_fill(
                                    self.driver, "middleName", fio_data.get('middle_name','')):
                                raise RuntimeError('Не удалось заполнить отчество собственника')
                            if not self.fast_click(self.driver, "Проверить наличие данных", 0.3):
                                self.fast_click(self.driver, "Проверить", 0.3)
                            time.sleep(0.05)
                            found_window = False
                            try:
                                elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Данные о собственности физического лица найдены')]")
                                if elements:
                                    found_window = True
                                    self.log(f"  ✅ Данные найдены!")
                                    self.fast_click(self.driver, "Подтвердить данные", 0.3)
                            except: pass
                            if not found_window:
                                try:
                                    elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'не найдены') or contains(text(), 'Не найдены')]")
                                    if elements:
                                        found_window = True
                                        self.log(f"  ⚠️ Данные не найдены, заполняем вручную")
                                        self.fast_click(self.driver, "Закрыть", 0.3)
                                        time.sleep(0.05)
                                        self.fast_click(self.driver, "Заполнить вручную", 0.3)
                                        time.sleep(0.05)
                                except: pass
                            try:
                                email_field = WebDriverWait(self.driver, 0.5).until(EC.presence_of_element_located((By.ID, "ownerEmail")))
                                cur = email_field.get_attribute("value")
                                if "," in cur:
                                    email_field.clear()
                                    time.sleep(0.05)
                                    email_field.send_keys(cur.split(',')[0].strip())
                            except: pass
                            if not self.fast_click(self.driver, "Продолжить", 0.3):
                                raise RuntimeError('Не удалось перейти к вводу помещения')
                            time.sleep(0.05)
                            try:
                                WebDriverWait(self.driver, 0.5).until(
                                    EC.presence_of_element_located((By.ID, "number-0"))
                                ).send_keys(premise_number)
                            except Exception:
                                pass
                            if not self.fast_click(self.driver, "Далее", 0.3):
                                raise RuntimeError('Не удалось перейти после ввода помещения')
                            time.sleep(0.05)
                            if not self.fast_click(self.driver, "Далее", 0.3):
                                raise RuntimeError('Не удалось перейти к загрузке PDF')
                            time.sleep(0.05)
                            upload_dir = None
                            try:
                                upload_dir = tempfile.mkdtemp(prefix='portal_upload_', dir=SCRIPT_DIR)
                                upload_copy = os.path.join(upload_dir, os.path.basename(ready_path))
                                shutil.copy2(ready_path, upload_copy)
                                WebDriverWait(self.driver, 1).until(
                                    EC.presence_of_element_located((By.ID, "files"))
                                ).send_keys(os.path.abspath(upload_copy))
                            except Exception as upload_exc:
                                if upload_dir:
                                    shutil.rmtree(upload_dir, ignore_errors=True)
                                raise RuntimeError(f'Не удалось прикрепить PDF: {upload_exc}')
                            time.sleep(0.05)
                            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                            time.sleep(0.05)
                            for _ in range(2):
                                if self.fast_checkbox(self.driver): break
                                time.sleep(0.05)
                            try:
                                WebDriverWait(self.driver, 1).until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit' and contains(text(), 'Далее')]")))
                            except: pass
                            if not self.fast_click(self.driver, "Далее", 0.3):
                                if upload_dir:
                                    shutil.rmtree(upload_dir, ignore_errors=True)
                                raise RuntimeError('Не удалось перейти к подтверждению отправки PDF')
                            time.sleep(0.05)
                            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                            time.sleep(0.05)
                            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight - 300);")
                            time.sleep(0.05)
                            submitted = self.fast_click(self.driver, "Внести данные в систему", 0.3)
                            if not submitted:
                                submitted = bool(self.driver.execute_script("""
                                    var btns = document.querySelectorAll('button');
                                    for(var i=0;i<btns.length;i++){
                                        if(btns[i].textContent.includes('Внести данные в систему')){
                                            btns[i].click();
                                            return true;
                                        }
                                    }
                                    return false;
                                """))
                            if not submitted:
                                if upload_dir:
                                    shutil.rmtree(upload_dir, ignore_errors=True)
                                raise RuntimeError('Не найдена кнопка «Внести данные в систему»')
                            self.fast_click(self.driver, "ОК", 0.3)
                            try:
                                self.driver.execute_script(
                                    "var f=document.getElementById('files'); if(f){f.value='';}")
                            except Exception:
                                pass
                            if upload_dir:
                                for cleanup_try in range(4):
                                    try:
                                        shutil.rmtree(upload_dir)
                                        break
                                    except PermissionError:
                                        time.sleep(0.2 * (cleanup_try + 1))
                                    except OSError:
                                        break
                            temp_filename = f"{fio_name} ({premise_number}).pdf"
                            temp_filename = re.sub(r'[\\/*?:"<>|]', '', temp_filename)
                            done_file_path = self._unique_pdf_path(done_folder, temp_filename)
                            if os.path.exists(ready_path):
                                moved = False
                                last_move_error = None
                                for move_try in range(8):
                                    try:
                                        shutil.move(ready_path, done_file_path)
                                        self._clear_input_failure(ready_path)
                                        moved = True
                                        if ready_hash is not None and ready_size is not None:
                                            done_hashes[(ready_size, ready_hash)] = done_file_path
                                        break
                                    except PermissionError as move_exc:
                                        last_move_error = move_exc
                                        time.sleep(0.35 * (move_try + 1))
                                    except OSError as move_exc:
                                        last_move_error = move_exc
                                        if getattr(move_exc, 'winerror', None) in (32, 33):
                                            time.sleep(0.35 * (move_try + 1))
                                            continue
                                        raise
                                if not moved:
                                    raise OSError(f'Не удалось переместить PDF: {last_move_error}')
                            self.total_processed += 1
                            self.total_votes += 1
                            daily_stats.add_input(1)
                            self.log(f"  ✅ ФИО {fio_num} внесен! ⚡")
                            self.update_progress(current, self.total_files, self.total_processed, self.total_errors, self.total_votes)
                        if os.path.exists(ready_path):
                            raise RuntimeError('Портал не подтвердил внесение всех ФИО из PDF')
                    except Exception as e:
                        logger.exception("Ошибка внесения ОСС %s, PDF %s", oss, filename)
                        if self.stop_flag:
                            location = 'problems' if problems_mode else 'ready'
                            self.log(f"⏸️ Остановлено пользователем: {filename}; PDF оставлен в {location}")
                            break
                        if self._input_browser_unavailable(e):
                            self.stop_flag = True
                            self.total_errors += 1
                            self.log("⛔ Потеряна связь с браузером. Очередь остановлена без повторной отправки текущего PDF. "
                                     "Перед новым запуском проверьте на портале, сохранился ли текущий голос.")
                            self.detail_text.config(text="⛔ Браузер недоступен — проверьте последний голос на портале")
                            self.update_progress(current, self.total_files, self.total_processed, self.total_errors, self.total_votes)
                            break
                        if problems_mode:
                            action = self._operator_finish_problem(
                                ready_path, oss, filename, str(e), done_folder)
                            if action == 'done':
                                self.total_processed += 1
                                self.total_votes += 1
                                daily_stats.add_input(1)
                            elif action == 'skip':
                                self.total_errors += 1
                            self.update_progress(
                                current, self.total_files, self.total_processed,
                                self.total_errors, self.total_votes)
                            if action == 'stop':
                                break
                            continue
                        if os.path.exists(ready_path):
                            action = self._record_input_failure(
                                ready_path, oss, filename, str(e), is_retry=is_retry)
                            if action == 'retry':
                                entries.append((filename, ready_path, True))
                                self.total_files += 1
                            else:
                                self.total_errors += 1
                        else:
                            self.total_errors += 1
                            self.log(f"❌ Ошибка при вводе {filename}: {e}; исходный PDF уже перемещён")
                        self.update_progress(current, self.total_files, self.total_processed, self.total_errors, self.total_votes)
            if not self.stop_flag:
                elapsed = time.time() - (self.start_time or time.time())
                stats.update_input(self.total_processed, self.total_errors, elapsed, self.total_votes)
                avg_vote_time = elapsed / self.total_votes if self.total_votes > 0 else 0
                mode_text = 'Очередь problems обработана' if problems_mode else 'Все ОСС обработаны'
                self.log(f"✅ {mode_text}! Внесено: {self.total_processed}, Ошибок: {self.total_errors}, Голосов: {self.total_votes}, Время: {timedelta(seconds=int(elapsed))}")
                self.log(f"⏱️ Среднее время на голос: {avg_vote_time:.1f}с")
                self.detail_text.config(text=f"✅ Готово! Внесено: {self.total_processed}, Ошибок: {self.total_errors}, Голосов: {self.total_votes}")
                self.status_label.config(text="✅ Завершено", fg=Theme.colors['success'])
                final_location = ('Успешные PDF перенесены из problems в ready/ОСС/внесено/'
                                  if problems_mode else
                                  'Файлы перемещены в ready/ОСС/внесено/')
                error_label = ('Осталось в problems' if problems_mode else 'Ошибок')
                messagebox.showinfo("Готово", f"✅ Внесено: {self.total_processed}\n❌ {error_label}: {self.total_errors}\n🗳️ Голосов: {self.total_votes}\n⏱️ Среднее время на голос: {avg_vote_time:.1f}с\n⏱️ Общее время: {timedelta(seconds=int(elapsed))}\n📁 {final_location}")
                if self.operator_help_required and not problems_mode:
                    unique = {}
                    for record in self.operator_help_required:
                        unique[(str(record.get('oss', '')), str(record.get('file', '')))] = record
                    records = list(unique.values())
                    lines = [f"ОСС {r.get('oss', '?')}: {r.get('file', '?')} — "
                             f"{r.get('last_reason', 'Причина не записана')}"
                             for r in records[:12]]
                    extra = f"\n...и ещё {len(records) - 12}" if len(records) > 12 else ''
                    messagebox.showwarning(
                        "Требуется помощь оператора",
                        "Повторное автоматическое внесение не удалось.\n"
                        "Файлы оставлены в problems и больше автоматически не отправляются.\n"
                        "Внесите их вручную:\n\n" + "\n".join(lines) + extra)
                offer_cleanup = (not problems_mode and self.total_errors == 0)
        except Exception as e:
            logger.exception("Аварийное завершение внесения")
            self.log(f"❌ Ошибка: {e}")
            self.detail_text.config(text=f"❌ Ошибка: {e}")
            messagebox.showerror("Ошибка", f"Произошла ошибка:\n{e}")
        finally:
            if self.driver:
                try: self.driver.quit()
                except: pass
            self.driver = None
            self.btn_run.config(state=tk.NORMAL)
            self.btn_problems.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)
            if offer_cleanup:
                self.parent.after(0,self._offer_cleanup)

class AppSettings:
    def __init__(self):
        self.file = os.path.join(SCRIPT_DIR, "settings.json")
        self.defaults = {"theme": "dark", "last_oss": "", "sound_enabled": True, "auto_clean": False, "language": "ru"}
        self.settings = self.load()
    def load(self):
        if os.path.exists(self.file):
            try:
                with open(self.file, 'r', encoding='utf-8') as f:
                    s = json.load(f)
                    for k,v in self.defaults.items():
                        if k not in s: s[k] = v
                    return s
            except Exception:
                logger.debug("Не критичная ошибка очистки", exc_info=True)
        return self.defaults.copy()
    def save(self):
        try:
            with open(self.file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception: pass
    def get(self, key, default=None):
        return self.settings.get(key, default)
    def set(self, key, value):
        self.settings[key] = value
        self.save()

class StudioEngine(OCRRobot):
    def learn_template(self, text, fios, kv):
        pass

    def _apply_text_corrections(self, value):
        return re.sub(r'\s+', ' ', value).strip()

    def _locate_name_region(self, image, fios):
        if not fios:
            return None
        norm = lambda s: re.sub(r'[^а-яa-z-]', '', s.casefold().replace('ё', 'е'))
        wanted = [norm(p) for p in str(fios[0]).split()]
        if len(wanted) not in (2, 3):
            return None
        lines = self._cluster_words_into_lines(self._get_anchor_words(image))
        for line in lines:
            low = line['text'].lower()
            if line['bbox'][1] > image.height * .60 or 'повестк' in low or 'вопросы, поставлен' in low:
                break
            words = line['words']
            for i in range(len(words)-len(wanted)+1):
                group = words[i:i+len(wanted)]
                if [norm(w['text']) for w in group] == wanted:
                    if any(t in low for t in ('предлага', 'избрать', 'секретар', 'председател',
                                                   'счетн', 'счётн', 'комисси', 'кандидат')):
                        continue
                    return (max(0, min(w['x'] for w in group)-4),
                            max(0, min(w['y'] for w in group)-4),
                            min(image.width, max(w['x']+w['w'] for w in group)+4),
                            min(image.height, max(w['y']+w['h'] for w in group)+4))
        return None

    @staticmethod
    def _smart_norm_fio(value):
        return ' '.join(
            re.sub(r'[^а-яё-]+', ' ', str(value or '').casefold().replace('ё', 'е')).split())

    @staticmethod
    def _smart_two_word_owner_candidate(text):
        garbage = {
            'сведения','лице','лицо','участвующем','голосовании','собственник',
            'собственники','собственника','жилого','нежилого','помещения',
            'помещений','квартиры','квартира','фамилия','имя','отчество',
            'гражданина','наименование','огрн','юридического','представитель',
            'решение','решения','вопросам','повестки','общего','собрания',
            'дата','время','место','приема','приёма','номер','объекты',
            'собственности','документе','подтверждающем','право'
        }
        for raw_line in str(text or '').splitlines():
            line = re.sub(r'\b([А-ЯЁ])\s+([а-яё]{2,})\b', r'\1\2', raw_line)
            tokens = re.findall(r'\b[А-ЯЁа-яё][А-ЯЁа-яё-]{1,39}\b', line)
            useful = [t for t in tokens if t.casefold().replace('ё','е') not in garbage]
            if len(useful) != 2:
                continue
            first, second = useful
            if min(len(first), len(second)) < 3 or len(first) < 4:
                continue
            return f'{first.title()} {second.title()}'
        return None

    # =========================================================================
    # FIX_v43.17.54: _smart_verify_taught_fio — варианты выполняются параллельно.
    # Согласованность (>=2 из N) проверяется после сбора результатов;
    # логика и пороги не изменены.
    # =========================================================================
    def _smart_verify_taught_fio(self, allow_two_word=False):
        if self.image is None:
            return None
        roi=self.detected_fio_roi or self.fio_roi
        if not roi:
            return None
        x1, y1, x2, y2 = (int(v) for v in roi)
        width, height = max(1, x2-x1), max(1, y2-y1)
        pad_x = max(20, int(width * 0.04))
        pad_y = max(8, int(height * 0.18))
        expanded = (max(0, x1-pad_x), max(0, y1-pad_y),
                    min(self.image.width, x2+pad_x),
                    min(self.image.height, y2+pad_y))
        crop=self.image.crop(expanded)
        if crop.width < 10 or crop.height < 10:
            return None

        max_side=max(crop.size)
        if max_side < 1600:
            scale=min(2.2,1600.0/max_side)
            crop=crop.resize((max(1,int(crop.width*scale)),
                              max(1,int(crop.height*scale))), Image.Resampling.LANCZOS)

        gray=crop.convert('L')
        auto=ImageOps.autocontrast(gray,cutoff=1)
        variants=[('auto-psm6',auto,'6'),('auto-psm11',auto,'11')]
        if OPENCV_AVAILABLE and NUMPY_AVAILABLE:
            try:
                arr=np.array(auto)
                _,otsu=cv2.threshold(arr,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
                variants.append(('otsu-psm6',Image.fromarray(otsu),'6'))
            except Exception:
                variants.append(('sharp-psm6',auto.filter(ImageFilter.SHARPEN),'6'))
        else:
            variants.append(('sharp-psm6',auto.filter(ImageFilter.SHARPEN),'6'))

        if allow_two_word and auto.width >= auto.height * 3:
            fy1 = max(0, int(auto.height * 0.34))
            fx1 = max(0, int(auto.width * 0.12))
            focused = auto.crop((fx1, fy1, auto.width, auto.height))
            if focused.width >= 40 and focused.height >= 20:
                variants.extend([
                    ('owner-line-psm7', focused, '7'),
                    ('owner-line-psm11', focused, '11'),
                    ('owner-line-sharp-psm7', focused.filter(ImageFilter.SHARPEN), '7'),
                ])

        def run_variant(label, variant, psm):
            try:
                text_value,raw_conf,_=self._tesseract_candidate(variant,psm)
                before=self.fio_confidence
                try:
                    fios=self.extract_all_fios(text_value)
                    parsed_conf=float(self.fio_confidence or 0.0)
                finally:
                    self.fio_confidence=before
                fios=[str(v).strip() for v in fios if str(v).strip()]
                two_word = False
                if not self._fio_list_valid(fios):
                    candidate = (self._smart_two_word_owner_candidate(text_value)
                                 if allow_two_word else None)
                    if not candidate:
                        return None
                    fios = [candidate]
                    parsed_conf = max(parsed_conf, 82.0)
                    two_word = True
                raw_conf=float(raw_conf or 0.0)
                if raw_conf < 45.0:
                    return None
                norms=tuple(self._smart_norm_fio(v) for v in fios)
                if not all(norms):
                    return None
                return {'fios':fios,'norms':norms,'raw_conf':raw_conf,
                        'parsed_conf':parsed_conf,'two_word':two_word,
                        'label':label,'text':text_value}
            except Exception:
                logger.debug('SmartVariant %s failed', label, exc_info=True)
                return None

        old_conf=self.fio_confidence
        votes=[]
        try:
            with ThreadPoolExecutor(max_workers=_ocr_max_workers(min(OCR_PARALLEL_WORKERS, len(variants))),
                                    thread_name_prefix='smart-fio') as pool:
                futures = [pool.submit(run_variant, label, variant, psm)
                           for label, variant, psm in variants]
                for fut in futures:
                    outcome = fut.result()
                    if outcome:
                        votes.append(outcome)
        finally:
            self.fio_confidence=old_conf

        if len(votes) < 2:
            return None

        grouped={}
        for vote in votes:
            grouped.setdefault(vote['norms'],[]).append(vote)
        norms,winners=max(
            grouped.items(),
            key=lambda item:(len(item[1]),
                             sum(v['raw_conf'] for v in item[1])/max(1,len(item[1])))
        )
        if len(winners) < 2:
            return None

        avg_raw=sum(v['raw_conf'] for v in winners)/len(winners)
        if avg_raw < 55.0:
            return None

        chosen=max(winners,key=lambda v:(v['parsed_conf'],v['raw_conf']))
        if len({bool(v.get('two_word')) for v in winners}) != 1:
            return None
        boosted=min(
            92.0,
            max(SMART_VERIFIED_CONFIDENCE,float(old_conf or 0.0),
                84.0+max(0.0,avg_raw-55.0)*0.12)
        )
        return {
            'fios':list(chosen['fios']),
            'conf':boosted,
            'variant':'SmartConsensusList 2of3:' + '+'.join(v['label'] for v in winners),
            'avg_raw_conf':avg_raw,
            'votes':len(winners),
            'all_votes':len(votes),
            'two_word':bool(chosen.get('two_word'))
        }

    # =========================================================================
    # FIX_v43.17.54: варианты _verify_owner_line выполняются параллельно.
    # =========================================================================
    def _verify_owner_line(self):
        page = ((getattr(self, '_source_page_image', None) or self.image)
                if getattr(self, 'deep_recheck', False) else self.image)
        if page is None:
            return None
        owner = self._owner_field_fio(page)
        lines = self._cluster_words_into_lines(self._get_anchor_words(page))
        if owner is None:
            for line in lines:
                if line['bbox'][1] > page.height*.55:
                    break
                label = re.sub(r'[^а-яё]', '', line['text'].casefold())
                if (label.startswith('фиособствен') and
                        'представител' not in label):
                    x1,y1,x2,y2 = line['bbox']
                    owner = {'roi':(max(0,x1-6),max(0,y1-6),
                                    min(page.width,x2+12),min(page.height,y2+6))}
                    break
        if not owner or not owner.get('roi'):
            return None
        roi = owner['roi']
        dedicated = False
        for index, line in enumerate(lines):
            low = line['text'].casefold()
            if line['bbox'][1] > page.height*.55:
                break
            if (not low.startswith('собственник') or 'квартир' not in low
                    or any(t in low for t in ('инициатор', 'председател', 'вопрос'))):
                continue
            for caption in lines[index+1:index+5]:
                if 'отчеств' not in caption['text'].casefold():
                    continue
                top, bottom = line['bbox'][3]+2, caption['bbox'][1]-2
                if bottom <= top or bottom-top > page.height*.1:
                    break
                roi = (line['bbox'][0], top, page.width-60, bottom)
                dedicated = True
                break
            if dedicated:
                break
        crop = page.crop(roi).convert('L')
        if dedicated and NUMPY_AVAILABLE:
            ys, xs = np.where(np.array(crop) < 120)
            if not len(xs):
                return None
            box = (max(0,int(xs.min())-3), max(0,int(ys.min())-3),
                   min(crop.width,int(xs.max())+4), min(crop.height,int(ys.max())+4))
            crop = crop.crop(box)
            roi = (roi[0]+box[0],roi[1]+box[1],roi[0]+box[2],roi[1]+box[3])
        if crop.width < 20 or crop.height < 10:
            return None
        variants = [('line7',crop,'7'), ('line13',crop,'13'),
                    ('line13-scale2',crop.resize((crop.width*2,crop.height*2),
                                                 Image.Resampling.LANCZOS),'13')]
        if dedicated:
            variants.extend([
                ('line13-thin',crop.filter(ImageFilter.MaxFilter(3)),'13'),
                ('line13-thin150',crop.resize((int(crop.width*1.5),int(crop.height*1.5)),
                      Image.Resampling.LANCZOS).filter(ImageFilter.MaxFilter(3)),'13')])

        def run_line_variant(label, image, psm):
            try:
                text, confidence, _ = self._tesseract_candidate(image, psm)
                fios = self.extract_all_fios(text)
                two_word = False
                if not self._fio_list_valid(fios):
                    candidate = self._smart_two_word_owner_candidate(text)
                    if not candidate:
                        return None
                    fios, two_word = [candidate], True
                if confidence < 55:
                    return None
                key = tuple(self._smart_norm_fio(fio) for fio in fios)
                return (key, fios, confidence, two_word, label)
            except Exception:
                logger.debug('OwnerLine variant %s failed', label, exc_info=True)
                return None

        votes = {}
        saved_conf = self.fio_confidence
        try:
            with ThreadPoolExecutor(max_workers=_ocr_max_workers(min(OCR_PARALLEL_WORKERS, len(variants))),
                                    thread_name_prefix='owner-line') as pool:
                futures = [pool.submit(run_line_variant, label, image, psm)
                           for label, image, psm in variants]
                for fut in futures:
                    outcome = fut.result()
                    if not outcome:
                        continue
                    key, fios, confidence, two_word, label = outcome
                    votes.setdefault(key, []).append((fios,confidence,two_word,label))
        finally:
            self.fio_confidence = saved_conf
        if len(votes) != 1:
            return None
        winners = next(iter(votes.values()))
        if len(winners) < 2:
            return None
        chosen = max(winners,key=lambda item:item[1])
        self.detected_fio_roi = roi
        return {'fios':chosen[0], 'conf':max(SMART_VERIFIED_CONFIDENCE,85.0),
                'two_word':chosen[2], 'route':'OwnerField',
                'variant':'OwnerLine consensus '+ '+'.join(v[3] for v in winners)}

    def _smart_recheck_owner_fio(self):
        if self.image is None:
            return None
        original_roi = self.detected_fio_roi or self.fio_roi
        attempts = []
        owner = self._owner_field_fio(self.image)
        if owner is not None and owner.get('roi'):
            attempts.append(('OwnerField', owner['roi'], True))
        if original_roi and all(tuple(original_roi) != tuple(item[1]) for item in attempts):
            # Сохранённая зона шаблона является безопасным контекстом ФИО,
            # поэтому в ней допустимы фамилия + имя без отчества.
            attempts.append(('TemplateROI', original_roi, True))

        saved_detected = self.detected_fio_roi
        for route, roi, allow_two_word in attempts:
            self.detected_fio_roi = tuple(int(v) for v in roi)
            verified = self._smart_verify_taught_fio(allow_two_word=allow_two_word)
            if verified:
                verified['route'] = route
                return verified
        self.detected_fio_roi = saved_detected
        return None

    @staticmethod
    def _room_route_is_taught_consensus(route):
        route = str(route or '')
        return (('TemplateROI' in route or 'TurboROI' in route) and
                ('fast-vote:' in route or 'turbo-room:' in route))

    def _batch_decision(self):
        self._two_word_owner_consensus = False

        template_fio_route = str(getattr(self, 'fio_engine_name', '') or '')
        template_room_route = str(getattr(self, 'kv_engine_name', '') or '')
        template_room = str(getattr(self, 'recognized_kv', '') or '').strip()
        template_room_valid = bool(re.fullmatch(
            r'(?i)(?:ММ|М/М|КВ|НП)?[ -]?\d{1,5}(?:[/-]\d{1,4})?[А-ЯЁA-Z]?',
            template_room))
        template_present = bool(
            getattr(self, 'mode', '') == 'auto' and
            getattr(self, 'active_layout_template', None) and
            ('TemplateROI' in template_fio_route or 'TurboROI' in template_fio_route))
        if template_present and (
                not self._fio_list_valid(getattr(self, 'recognized_fios', []) or []) or
                float(getattr(self, 'fio_confidence', 0.0) or 0.0) < 82.0):
            verified = self._smart_verify_taught_fio(allow_two_word=True)
            if verified:
                self.recognized_fios = list(verified['fios'])
                self.fio_confidence = float(verified['conf'])
                self.fio_engine_name = 'SmartConsensus TemplateROI'
                self.ocr_variant_name = verified.get('variant', 'SmartConsensus 2of3')
                self._two_word_owner_consensus = bool(verified.get('two_word'))
                template_fio_route = self.fio_engine_name
            else:
                # Шаблон уже геометрически найден, поэтому не отправляем PDF
                # в ручную проверку только из-за шума внутри сохранённой ROI.
                # Один резервный проход ищет строку владельца по подписи поля и
                # требует согласия независимых вариантов OCR.
                recovered = self._smart_recheck_owner_fio()
                if recovered:
                    self.recognized_fios = list(recovered['fios'])
                    self.fio_confidence = float(recovered['conf'])
                    route = recovered.get('route', 'OwnerField')
                    self.fio_engine_name = 'SmartConsensus ' + route
                    self.ocr_variant_name = recovered.get(
                        'variant', 'OwnerLine consensus')
                    self._two_word_owner_consensus = bool(
                        recovered.get('two_word'))
                    template_fio_route = self.fio_engine_name

        # У табличных бланков номер находится в ячейке «Номер помещения»,
        # а сохранённый ROI старого шаблона иногда захватывает соседнюю колонку.
        # Проверяем только этот известный тип, чтобы не замедлять остальные PDF.
        # Для Бланка 94 номер уже прочитан быстрым grid-OCR в auto_recognize.
        # Не запускаем здесь повторный полностраничный OCR.
        layout_name = str(getattr(self, 'active_layout_template', '') or '')
        if layout_name == 'Бланк 94':
            room_check = {}
        elif (self.image is not None and
              (not template_room_valid or
               float(getattr(self, 'kv_confidence', 0.0) or 0.0) < 82.0)):
            # У этих бланков вся строка собственности смещается по горизонтали,
            # поэтому сохранённый ROI номера может оказаться пустым. Динамический
            # поиск запускается только при неудаче ROI и не замедляет обычные формы.
            room_check = self._labeled_room(self.image)
        else:
            room_check = None

        template_verified = bool(
            template_present and
            float(getattr(self, 'active_layout_score', 0.0) or 0.0) >= 0.90 and
            (self._fio_list_valid(getattr(self, 'recognized_fios', []) or []) or
             getattr(self, '_two_word_owner_consensus', False)) and
            template_room_valid and
            (('TemplateROI' in template_fio_route or 'TurboROI' in template_fio_route) or
             template_fio_route == 'SmartConsensus OwnerField') and
            ('TemplateROI' in template_room_route or 'TurboROI' in template_room_route or
             'TemplateGridOCR' in template_room_route or
             'LabeledRoom table-number-cell' in template_room_route) and
            float(getattr(self, 'fio_confidence', 0.0) or 0.0) >= 65.0 and
            float(getattr(self, 'kv_confidence', 0.0) or 0.0) >= 82.0)
        if template_verified:
            return True, '⚡ Обученный шаблон принят по согласованным ROI'
        if template_present and not self._fio_list_valid(
                getattr(self, 'recognized_fios', []) or []):
            return False, 'Шаблон найден, но ФИО в обученной зоне не прочитано'

        if (getattr(self, 'turbo_batch_mode', False) and
                self.ocr_engine_name == 'TurboTemplateOCR' and
                self.active_layout_template and
                min(float(self.fio_confidence or 0),
                    float(self.kv_confidence or 0)) >= 90.0):
            accepted, reason = OCRRobot._batch_decision(self)
            if accepted:
                return True, '🚀 Турбо: обученный шаблон подтверждён по ROI'
            return accepted, reason

        if room_check is None:
            room_check = self._labeled_room(self.image) if self.image is not None else None
        if room_check:
            prior_value = str(self.recognized_kv or '')
            prior_normalized = self._normalize_room_value(prior_value)
            taught_room = (
                self.active_layout_template and
                self._room_route_is_taught_consensus(self.kv_engine_name)
            )
            if (prior_normalized not in ('', '0', '00')
                    and prior_normalized != room_check['value'] and taught_room):
                room_check = None
                self.kv_engine_name = str(self.kv_engine_name) + ' / taught-priority'
            elif (prior_normalized not in ('', '0', '00')
                    and prior_normalized != room_check['value']):
                return False, ('Конфликт номера помещения: область OCR дала '
                               f'{prior_value}, дополнительный поиск — {room_check["value"]}. Проверьте номер собственника.')
        if room_check:
            prior_value = str(self.recognized_kv or '')
            self.recognized_kv = room_check['value']
            self.detected_kv_roi = room_check['roi']
            confidence = float(room_check['conf'])
            if confidence < OCR_REVIEW_THRESHOLD:
                crop = self.image.crop(room_check['roi'])
                matching = []
                for scale in (2,3):
                    enlarged = crop.resize((crop.width*scale,crop.height*scale),Image.Resampling.LANCZOS)
                    text, raw_conf, _ = self._tesseract_candidate(enlarged, '7')
                    match = re.search(r'(?:№|#|N[oо]?)?\s*(\d{1,5}[А-Яа-яA-Za-z]?)\s*[.)]?\s*$', text)
                    if match and self._normalize_room_value(match.group(1)) == room_check['value']:
                        matching.append(float(raw_conf))
                if len(matching) == 2 and min(matching) >= 55:
                    confidence = max(confidence, SMART_VERIFIED_CONFIDENCE)
            self.kv_confidence = (max(float(self.kv_confidence or 0),confidence)
                                  if prior_value == room_check['value'] else confidence)
            self.kv_engine_name = 'LabeledRoom explicit-field'
        template_roi_route = bool(
            self.active_layout_template and
            ('TemplateROI' in str(self.fio_engine_name or '') or
             'TurboROI' in str(self.fio_engine_name or '')))
        if (self.mode == 'auto' and not template_roi_route and
                (not self._fio_list_valid(self.recognized_fios) or
                 float(self.fio_confidence or 0) < OCR_REVIEW_THRESHOLD)):
            verified = self._verify_owner_line()
            if verified:
                self.recognized_fios = list(verified['fios'])
                self.fio_confidence = verified['conf']
                self.fio_engine_name = 'SmartConsensus OwnerField'
                self.ocr_variant_name = verified['variant']
                self._two_word_owner_consensus = verified['two_word']
        if (self.mode == 'auto' and getattr(self, 'deep_recheck', False) and
                not self._two_word_owner_consensus and
                (not self._fio_list_valid(self.recognized_fios) or
                 float(self.fio_confidence or 0.0) < OCR_REVIEW_THRESHOLD)):
            verified = self._smart_recheck_owner_fio()
            if verified:
                self.recognized_fios = list(verified['fios'])
                self.fio_confidence = float(verified['conf'])
                route = verified.get('route', 'OwnerField')
                self.fio_engine_name = 'SmartConsensus ' + route
                self.ocr_variant_name = verified.get('variant', 'SmartConsensus 2of3')
                self._two_word_owner_consensus = bool(verified.get('two_word'))

        if self.mode == 'auto' and self.active_layout_template:
            fio_route = str(self.fio_engine_name or '')
            from_taught_fio = (('TemplateROI' in fio_route or 'TurboROI' in fio_route) or
                               fio_route == 'SmartConsensus OwnerField')
            if not from_taught_fio:
                return False, 'Шаблон найден, но ФИО не подтверждено обученной зоной'
            fio_is_verified = (self._fio_list_valid(self.recognized_fios) or
                               self._two_word_owner_consensus)
            if (not fio_is_verified or
                    float(self.fio_confidence or 0.0) < OCR_REVIEW_THRESHOLD):
                verified = self._smart_verify_taught_fio(allow_two_word=True)
                if verified:
                    self.recognized_fios = list(verified['fios'])
                    self.fio_confidence = float(verified['conf'])
                    self.fio_engine_name = 'SmartConsensus TemplateROI'
                    self.ocr_variant_name = verified.get('variant', 'SmartConsensus 2of3')
                else:
                    return False, 'Шаблон найден, но ФИО в обученной зоне прочитано неуверенно — AUTO RECHECK'

        room = str(self.recognized_kv or '').strip()
        fio_route = str(self.fio_engine_name or '')
        room_route = str(self.kv_engine_name or '')
        verified_template_result = bool(
            self.active_layout_template and
            float(self.active_layout_score or 0.0) >= 0.88 and
            self._fio_list_valid(self.recognized_fios) and
            'SmartConsensus' in fio_route and 'TemplateROI' in fio_route and
            'TemplateROI' in room_route and
            min(float(self.fio_confidence or 0.0),
                float(self.kv_confidence or 0.0)) >= OCR_REVIEW_THRESHOLD and
            re.fullmatch(r'(?i)(?:ММ|М/М|КВ|НП)?[ -]?\d{1,5}(?:[/-]\d{1,4})?[А-ЯЁA-Z]?', room)
        )
        if verified_template_result:
            return True, '⚡ Обученный шаблон подтверждён по согласованным ROI'

        if self.image is None or not self._get_anchor_words(self.image):
            return False, 'Не удалось выполнить независимую проверку страницы'
        if not self.detected_fio_roi and self.image is not None:
            self.detected_fio_roi = self._locate_name_region(self.image, self.recognized_fios)
        if self._two_word_owner_consensus:
            room = str(self.recognized_kv or '').strip()
            if not room or room == '0':
                return False, 'Не заполнены обязательные поля'
            if not re.fullmatch(r'(?i)(?:ММ|М/М|КВ|НП)?[ -]?\d{1,5}(?:[/-]\d{1,4})?[А-ЯЁA-Z]?', room):
                return False, 'Нестандартный номер помещения'
            if min(float(self.fio_confidence or 0), float(self.kv_confidence or 0)) >= OCR_REVIEW_THRESHOLD:
                return True, 'Уверенный OCR: двухсловное ФИО владельца подтверждено 2 из 3'
            return False, 'Низкая уверенность OCR'
        return super()._batch_decision()

    def _labeled_room(self, image):
        explicit = re.compile(
            r'(?:помещ\w*|помеш\w*|квартир\w*|пом\.?|кв\.?)'
            r'(?:\s*\([^)]{0,40}\))?'
            r'[\s,;.)]*(?:(?:№|#|N[oо]?|номер)\s*)?[:.=\-]*\s*'
            r'([0-9OОIlІЗБВB]{1,6}(?:\s*[-/.]\s*[0-9OОIlІЗБВB]{1,6})?[А-Яа-яA-Za-z]?)',
            re.IGNORECASE,
        )
        found = []
        lines = self._cluster_words_into_lines(self._get_anchor_words(image))
        for index, line in enumerate(lines):
            low = line['text'].casefold()
            property_list_hint = (
                any(token in low for token in ('машино', 'машина')) and
                'комнат' in low and 'собствен' in low
            )
            if (not any(x in low for x in ('помещ', 'помеш', 'квартир')) and
                    not re.search(r'(?i)(?:^|\s)(?:кв|пом)\.', line['text']) and
                    not property_list_hint):
                continue
            match = explicit.search(line['text'])
            if not match and property_list_hint:
                # Первая буква слова «квартира» часто повреждена краем
                # подчёркивания (например, OCR даёт «‹вартира»). В строке
                # перечня первый номер всё равно относится к квартире.
                match = re.search(
                    r'(?:№|#|N[oо]?|номер)\s*[:.=\-]*\s*'
                    r'([0-9OОIlІЗБВB]{1,6}(?:\s*[-/.]\s*'
                    r'[0-9OОIlІЗБВB]{1,6})?[А-Яа-яA-Za-z]?)',
                    line['text'], re.IGNORECASE)
            if not match:
                continue
            previous = lines[index-1]['text'].casefold() if index else ''
            nearby = previous + ' ' + low
            property_list_field = (
                property_list_hint and
                ('квартир' in low or match is not None)
            )
            header_context = ' '.join(
                item['text'].casefold()
                for item in lines[max(0, index-2):index+1]
            )
            table_number_field = (
                'номер' in header_context and
                ('помещ' in header_context or 'помеш' in header_context or
                 'квартир' in header_context) and
                bool(re.search(r'(?i)(?:кв|пом)\.?\s*(?:№\s*)?\d', line['text']))
            )
            context = ' '.join(item['text'].casefold().replace('ё', 'е')
                               for item in lines[max(0, index-4):index+1])
            if ('прием' in context and 'решени' in context
                    and 'мест' in context):
                continue
            property_field = ('объект' in nearby and 'собствен' in nearby)
            dangerous = any(token in nearby for token in (
                'вопрос', 'повест', 'голосован', 'избрат', 'избран',
                'собрани', 'протокол', 'председател', 'секретар'
            ))
            address_line = any(token in low for token in (
                'адрес', 'улиц', 'проспект', 'дом ', 'корпус', 'корп.'
            ))
            owner_property_field = (
                'собственник' in low and
                ('квартир' in low or 'помещен' in low or 'помешен' in low) and
                low.lstrip().startswith('собственник') and
                (not dangerous or
                 ('сведен' in previous and 'лиц' in previous and 'голосован' in previous)) and
                not any(token in low for token in (
                    'инициатор', 'председател', 'секретар', 'избрат', 'вопрос')) and
                not address_line
            )
            standalone_field = (
                match.start() <= 3 and len(line['text'].strip()) <= 80 and
                not dangerous and not address_line
            )
            if (not property_field and not owner_property_field and
                    not standalone_field and not table_number_field and
                    not property_list_field):
                continue
            value = self._normalize_room_value(match.group(1))
            if not value or value in {'0', '00'}:
                continue

            target = None
            for word in line['words']:
                raw = word['text'].strip('.,:;()[]{}')
                raw = re.sub(r'^[№#NnНн]+\s*', '', raw)
                if self._normalize_room_value(raw) == value:
                    target = word
                    break
            if target:
                conf = float(target.get('conf', 0) or 0)
                roi = (max(0, target['x']-10), max(0, target['y']-8),
                       min(image.width, target['x']+target['w']+10),
                       min(image.height, target['y']+target['h']+8))
            else:
                x1, y1, x2, y2 = line['bbox']
                conf = max((float(w.get('conf', 0) or 0) for w in line['words']), default=0.0)
                roi = (max(0, x1-8), max(0, y1-6),
                       min(image.width, x2+8), min(image.height, y2+6))

            priority = (7 if property_list_field else
                        4 if table_number_field else
                        3 if (property_field or owner_property_field) else 2)
            source = ('property-list-apartment' if property_list_field else
                      'table-number-cell' if table_number_field else
                      'explicit-field')
            found.append((priority, conf, value, roi, source))

        if found:
            _, conf, value, roi, source = max(found, key=lambda item: (item[0], item[1]))
            return {'value': value, 'conf': conf, 'roi': roi, 'source': source}
        return None

_WORKER_TEMPLATE_CACHE = {'signature': None, 'templates': None, 'np_cache': {}}

def _worker_templates(templates_path):
    """Load the large template database once per persistent worker."""
    if not templates_path:
        return {}, {}
    try:
        real_path = os.path.realpath(templates_path)
        stat = os.stat(real_path)
        signature = (real_path, stat.st_mtime_ns, stat.st_size)
    except OSError:
        return {}, {}
    if _WORKER_TEMPLATE_CACHE.get('signature') != signature:
        loaded = safe_json_load(real_path, {})
        _WORKER_TEMPLATE_CACHE['signature'] = signature
        _WORKER_TEMPLATE_CACHE['templates'] = loaded if isinstance(loaded, dict) else {}
        _WORKER_TEMPLATE_CACHE['np_cache'] = {}
    return (_WORKER_TEMPLATE_CACHE.get('templates') or {},
            _WORKER_TEMPLATE_CACHE.get('np_cache'))

def _set_worker_priority():
    if os.name != 'nt':
        return True
    try:
        import ctypes
        from ctypes import wintypes
        priority = 0x00000040 if _input_priority_active() else 0x00000020
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        kernel32.SetPriorityClass.argtypes = (wintypes.HANDLE, wintypes.DWORD)
        kernel32.SetPriorityClass.restype = wintypes.BOOL
        process = kernel32.GetCurrentProcess()
        if not kernel32.SetPriorityClass(process, priority):
            raise ctypes.WinError(ctypes.get_last_error())
        return True
    except Exception:
        logger.debug('Не удалось изменить приоритет OCR worker', exc_info=True)
        return False

def _studio_worker(job_dir):
    _set_worker_priority()
    request = safe_json_load(os.path.join(job_dir, 'request.json'), {})
    class Quiet:
        def config(self, **kwargs): pass
        def update_idletasks(self): pass
    engine = StudioEngine.__new__(StudioEngine)
    engine.parent = Quiet()
    engine.log_label = Quiet()
    engine.ocr_error = None
    engine.mode = request.get('mode', 'auto')
    engine.fast_mode = request.get('fast_mode', True)
    engine.turbo_batch_mode = bool(request.get('turbo_batch', False))
    engine.deep_recheck = bool(request.get('deep_recheck', False))
    engine.fio_dictionary = set(request.get('fio_dictionary', []))
    engine.corrections = {}
    templates_path = request.get('templates_path')
    loaded_templates, template_np_cache = _worker_templates(templates_path)
    engine._template_np_cache = template_np_cache
    engine.templates = loaded_templates if isinstance(loaded_templates, dict) and loaded_templates else request.get('templates', {})
    engine.preferred_layout_template = request.get('preferred_layout_template')
    engine.saved_roi_data = request.get('saved_roi_data', {})
    engine.saved_fio_roi = request.get('saved_fio_roi')
    engine.saved_kv_roi = request.get('saved_kv_roi')
    engine.roi_saved = bool(engine.saved_fio_roi and engine.saved_kv_roi)
    engine.fio_roi = request.get('fio_roi')
    engine.kv_roi = request.get('kv_roi')
    engine.detected_fio_roi = engine.detected_kv_roi = None
    engine._anchor_cache = {}
    engine._layout_match_cache = {}
    engine.ocr_cache = {}
    engine.ocr_times = []
    engine.easyocr_available = False
    engine.fio_confidence = engine.kv_confidence = 0.
    engine.recognized_fios = []
    engine.recognized_kv = None
    engine.ocr_engine_name = engine.fio_engine_name = engine.kv_engine_name = ''
    engine.ocr_variant_name = ''
    engine.last_raw_fio = engine.last_raw_kv = ''
    engine.full_text = ''
    engine.last_ocr_time = 0.
    engine.active_layout_template = None
    engine.active_layout_score = 0.0
    engine.update_image = lambda: None
    def apply(fios, room):
        engine.recognized_fios = list(fios)
        engine.recognized_kv = room
    engine._apply_recognized = apply
    performance_profile = {'tesseract_calls': 0, 'tesseract_seconds': 0.0}
    render_started = time.perf_counter()
    _timeout_state = {'count': 0}
    _MAX_SOFT_TIMEOUTS = 6
    tesseract_originals = {}
    for name in ('image_to_data', 'image_to_string', 'image_to_osd'):
        original = getattr(pytesseract, name)
        tesseract_originals[name] = original
        def bounded(*args, _original=original, _name=name, **kwargs):
            if _timeout_state['count'] >= _MAX_SOFT_TIMEOUTS:
                raise RuntimeError('Tesseract уже превысил время ожидания на этой странице')
            kwargs.setdefault('timeout', 9 if _timeout_state['count'] else 15)
            started = time.perf_counter()
            try:
                return _original(*args, **kwargs)
            except RuntimeError as exc:
                if 'timeout' in str(exc).lower():
                    performance_profile['tesseract_timeout'] = True
                    _timeout_state['count'] += 1
                raise
            finally:
                performance_profile['tesseract_calls'] += 1
                elapsed = time.perf_counter() - started
                performance_profile['tesseract_seconds'] += elapsed
                performance_profile[_name + '_calls'] = performance_profile.get(_name + '_calls', 0) + 1
        setattr(pytesseract, name, bounded)
    result = {}
    try:
        if request.get('image_path'):
            with Image.open(request['image_path']) as im:
                engine.image = im.convert('RGB')
        else:
            local_pdf = os.path.join(job_dir, 'input.pdf')
            shutil.copy2(request['pdf_path'], local_pdf)
            render_dpi = (DEEP_RENDER_DPI if request.get('deep_recheck')
                          else FAST_RENDER_DPI)
            pages = convert_from_path(local_pdf, dpi=render_dpi, first_page=1, last_page=1,
                                      poppler_path=request['poppler'], thread_count=1, timeout=45)
            engine.image = pages[0]
        performance_profile['pdf_to_image_seconds'] = time.perf_counter() - render_started
        engine.original_width, engine.original_height = engine.image.size
        image_path = os.path.join(job_dir, 'page.png')
        image_temp = os.path.join(job_dir, 'page.rendering')
        engine.image.save(image_temp, format='PNG')
        os.replace(image_temp, image_path)
        if request.get('recognize', True):
            recognition_started = time.perf_counter()
            if engine.mode == 'manual' and request.get('image_path') and engine.fio_roi and engine.kv_roi:
                engine.manual_recognize()
            elif engine.mode == 'manual' and engine._adaptive_manual_rois():
                engine.manual_recognize()
            else:
                engine.auto_recognize()
            performance_profile['recognition_seconds'] = time.perf_counter() - recognition_started
            if engine.ocr_error:
                accepted, reason = False, str(engine.ocr_error)
            else:
                accepted, reason = engine._batch_decision()
                if performance_profile.get('tesseract_timeout') and not accepted:
                    reason = f'{reason}. Tesseract долго отвечал на вспомогательном проходе, но шаблонный ROI был обработан.'
            for record in request.get('scoped_learning', []):
                if (record.get('enabled', True) and engine.active_layout_template
                        and record.get('template') == engine.active_layout_template):
                    mapped = [record['new'] if name == record['old'] else name for name in engine.recognized_fios]
                    if mapped != engine.recognized_fios:
                        engine.recognized_fios = mapped
                        accepted, reason = False, 'Применено обученное исправление: подтвердите ФИО'
        else:
            accepted = False
            reason = ('Введите ФИО и помещение вручную' if engine.mode == 'entry'
                      else 'Выделите области ФИО и помещения')
        result = {key: getattr(engine, key, None) for key in (
            'recognized_fios','recognized_kv','fio_confidence','kv_confidence',
            'detected_fio_roi','detected_kv_roi','fio_roi','kv_roi','ocr_error',
            'fio_engine_name','kv_engine_name','ocr_engine_name','ocr_variant_name',
            'last_raw_fio','last_raw_kv','full_text','last_ocr_time','active_layout_template','active_layout_score')}
        performance_profile['tesseract_seconds'] = round(performance_profile['tesseract_seconds'], 4)
        performance_profile['pdf_to_image_seconds'] = round(performance_profile.get('pdf_to_image_seconds', 0.0), 4)
        performance_profile['recognition_seconds'] = round(performance_profile.get('recognition_seconds', 0.0), 4)
        result.update(image_path=image_path, accepted=accepted, reason=reason,
                      owner_two_word_verified=bool(getattr(engine, '_two_word_owner_consensus', False)),
                      performance_profile=performance_profile)
    except Exception as exc:
        logger.exception('Ошибка отдельного OCR-процесса')
        result = {'ocr_error': str(exc), 'accepted': False, 'reason': 'Ошибка OCR: '+str(exc),
                  'recognized_fios': [], 'recognized_kv': None}
    for name, original in tesseract_originals.items():
        setattr(pytesseract, name, original)
    if not atomic_json_save_compact(os.path.join(job_dir, 'result.json'), result):
        return 2
    return 0

def _persistent_ocr_worker():
    """Process job directories from stdin without re-importing Python each time."""
    try:
        _worker_templates(TEMPLATES_PATH)
        logger.info('Постоянный OCR worker готов; шаблонов: %s',
                    len(_WORKER_TEMPLATE_CACHE.get('templates') or {}))
    except Exception:
        logger.exception('Предварительная загрузка шаблонов OCR не удалась')
    for raw_line in sys.stdin:
        job_dir = raw_line.strip()
        if not job_dir:
            continue
        try:
            _studio_worker(os.path.abspath(job_dir))
        except Exception as exc:
            logger.exception('Необработанная ошибка постоянного OCR worker')
            atomic_json_save_compact(os.path.join(job_dir, 'result.json'), {
                'ocr_error': str(exc), 'accepted': False,
                'reason': 'Ошибка OCR worker: ' + str(exc),
                'recognized_fios': [], 'recognized_kv': None})
    return 0

class OCRStudio(StudioEngine):
    def __init__(self, parent_frame):
        self.ocr_busy = self.saving_busy = self._closing = False
        self._ocr_worker_process = None
        self._ocr_worker_stdin = None
        self._ocr_worker_log = None
        self._ocr_worker_lock = threading.RLock()
        self._ocr_worker_log_path = os.path.join(LOG_DIR, 'ocr_worker_persistent.log')
        self._job_number = 0
        self._cancel_job = threading.Event()
        self._pending_result = None
        self._switch_to_entry_pending = False
        self._displayed_document = None
        self._displayed_fingerprint = None
        self._batch_document_action = None
        self._draft_after = None
        self._drafts = {}
        self._statuses = {}
        self._queue_window = self._preview_window = self._tools_window = None
        self._last_batch_report = None
        self._batch_results_window = None
        self._batch_review_reason_by_doc = {}
        self._batch_training_docs = {}
        self._view_fit_mode = 'page'
        self.manual_input_seconds = 0.0
        self.manual_input_documents = 0
        self._manual_current_seconds = 0.0
        self._manual_timer_started = None
        self._manual_timer_document = None
        self.scoped_learning = safe_json_load(os.path.join(SCRIPT_DIR, 'learning_scoped.json'), [])
        if not isinstance(self.scoped_learning, list): self.scoped_learning = []
        self._session_file = os.path.join(SCRIPT_DIR, 'ocr_session_v43.json')
        self._session_ready = False
        self._recheck_only = False
        self._manual_review_open = False
        self._mandatory_training = False
        self._training_document = None
        self._training_reason = ''
        self._dashboard_after = None
        self._dashboard_ready_cache = (0.0, 0)
        self._dashboard_cards = {}
        self._dashboard_progress = None
        self._dashboard_progress_text = None
        self._dashboard_state = None
        self._dashboard_route = None
        self.auto_recheck_enabled = True
        self._auto_recheck_phase = False
        self._auto_recheck_started = False
        self._first_pass_done_count = 0
        self._recheck_saved_count = 0
        self._manual_remaining_count = 0
        self._ocr_perf_docs = 0
        self._ocr_perf_seconds = 0.0
        self._ocr_perf_tesseract_calls = 0
        self._ocr_perf_auto_accepted = 0
        self._template_performance = {}
        self._recheck_source_queue = []
        self._batch_original_files = []
        self._batch_original_keys = set()
        self._batch_review_keys = set()
        self.turbo_batch_mode = True
        super().__init__(parent_frame)
        threading.Thread(target=self._ensure_persistent_ocr_worker,
                         name='ocr-worker-warmup', daemon=True).start()
        view_preferences = self._loaded_view_preferences
        self._view_fit_mode = view_preferences.get('mode','page') if view_preferences.get('mode') in ('page','width','custom') else 'page'
        try: self._saved_custom_zoom = max(.2, min(3., float(view_preferences.get('zoom',1.0))))
        except (TypeError, ValueError): self._saved_custom_zoom = 1.0
        if self._view_fit_mode == 'custom': self.zoom = self._saved_custom_zoom
        self._session_ready = True
        top = self.btn_start.master.master
        root = top.master
        c = Theme.colors

        self.btn_start.config(text='▶ Запустить пакет')
        self.btn_pause.config(text='Ⅱ Пауза')
        self.btn_resume.config(text='▶ Продолжить')
        self.btn_stop.config(text='■ Стоп')

        primary = self.btn_start.master
        self.btn_skip_current = make_button(
            primary, 'Пропустить', self._request_batch_skip_current,
            bg=c['warning'], fg='#101010', width=10, state=tk.DISABLED, pady=5)
        self.btn_skip_current.pack(side=tk.LEFT, padx=2)
        self.btn_exclude_current = make_button(
            primary, 'Убрать', self._request_batch_exclude_current,
            bg=c['btn'], fg=c['error'], width=9, state=tk.DISABLED, pady=5)
        self.btn_exclude_current.pack(side=tk.LEFT, padx=2)

        toolbar = tk.Frame(root, bg=c['card_bg'], height=50,
                           highlightthickness=1, highlightbackground=c['border'])
        toolbar.pack(fill=tk.X, after=top, padx=8, pady=(4,6))
        toolbar.pack_propagate(False)

        make_button(toolbar,'Новый пакет',self.select_oss,bg=c['btn'],fg=c['fg'],
                    width=10,pady=4).pack(side=tk.LEFT,padx=(8,2))

        self.btn_turbo=make_button(toolbar,'Турбо: ВКЛ',self.toggle_turbo_batch,
                                   bg=c['success'],fg='white',width=10,pady=4)
        self.btn_turbo.pack(side=tk.LEFT,padx=2)

        self.btn_auto_recheck=make_button(toolbar,'Максимум авто: ВКЛ',self.toggle_auto_recheck,
                                          bg=c['success'],fg='white',width=16,pady=4)
        self.btn_auto_recheck.pack(side=tk.LEFT,padx=2)

        self.btn_batch_results=make_button(toolbar,'Результаты',self._show_batch_report,
                                            bg=c['accent'],fg='white',width=10,pady=4)
        self.btn_batch_results.pack(side=tk.LEFT,padx=2)

        self.btn_entry=make_button(toolbar,'Рукописные',self._start_handwritten,
                                   bg=c['btn'],fg=c['fg'],width=10,pady=4)
        self.btn_entry.pack(side=tk.LEFT,padx=2)
        make_button(toolbar, 'Проверка', self._start_manual_review_queue,
                    bg=c['btn'], fg=c['fg'], width=10, pady=4).pack(side=tk.LEFT,padx=2)

        tools_menu = tk.Menu(toolbar, tearoff=0, bg=c['bg_secondary'], fg=c['fg'],
                             activebackground=c['accent'], activeforeground='white')
        tools_menu.add_command(label='Внесение', command=self.open_robot_helper_tab)
        tools_menu.add_command(label='Фрагменты', command=self._show_preview)
        tools_menu.add_separator()
        tools_menu.add_command(label='Вся страница', command=self.fit_page)
        tools_menu.add_command(label='По ширине', command=self.fit_width)
        tools_menu.add_separator()
        tools_menu.add_command(label='OCR-исправления', command=self._learning_window)
        tools_menu.add_command(label='Интернет-образцы (не обучены)', command=self._open_reference_library)
        tools_menu.add_command(label='Аудит копий', command=self._audit_copies)
        tools_menu.add_separator()
        tools_menu.add_command(
            label='Удалить точные дубли шаблонов',
            command=self._template_duplicates_dialog)

        self.btn_more_tools = tk.Button(
            toolbar, text='Инструменты  ⋯', command=self._open_tools_panel,
            bg=c['btn'], fg=c['fg'], activebackground=c['accent'],
            activeforeground='white', relief=tk.FLAT, bd=0,
            font=('Segoe UI',9,'bold'), cursor='hand2', padx=12, pady=6)
        self.btn_more_tools.pack(side=tk.RIGHT,padx=(4,10),pady=4)
        self.tools_menu = tools_menu

        self.view_mode_label = tk.Label(
            toolbar, text='Вид: Вся страница',
            bg=c['bg_secondary'], fg=c['accent'],
            font=('Segoe UI',8,'bold')
        )
        self.view_mode_label.pack(side=tk.RIGHT,padx=(10,6))

        self.btn_fit_page = make_button(
            toolbar, 'Вся страница', self.fit_page,
            bg=c['btn'], fg=c['fg'], width=12, pady=4)
        self.btn_fit_page.pack(side=tk.RIGHT, padx=2)

        self.btn_fit_width = make_button(
            toolbar, 'По ширине', self.fit_width,
            bg=c['btn'], fg=c['fg'], width=10, pady=4)
        self.btn_fit_width.pack(side=tk.RIGHT, padx=2)

        dashboard = tk.Frame(root, bg=c['bg'], height=132)
        dashboard.pack(fill=tk.X, after=toolbar, padx=8, pady=(0,4))
        dashboard.pack_propagate(False)
        self._build_modern_dashboard(dashboard)

        self.studio_counts=tk.Label(self.log_label.master,text='',bg=c['bg_secondary'],
                                    fg=c['accent'],font=('Segoe UI',8,'bold'))

        for entry in self.fio_entries + [self.kv_entry]:
            entry.bind('<KeyRelease>', self._draft_changed, add='+')
        for entry in self.fio_entries:
            entry.bind('<Return>', self._manual_focus_room, add='+')
        self.kv_entry.bind('<Return>', self._manual_confirm_key, add='+')

        ToolTip(self.btn_batch_results,'Живые показатели партии и причины перепроверки.')

        self.parent.winfo_toplevel().bind(
            '<Control-Return>',
            lambda e:self.confirm() if self.parent.winfo_toplevel().focus_get() else None,
            add='+'
        )
        self._refresh_view_controls()
        self._controls()
        self._schedule_dashboard_refresh()
        try:
            self.parent.after(3000, self._auto_report_template_duplicates)
        except Exception:
            pass

    def _dashboard_card(self, parent, key, title, hint='', accent=None):
        c = Theme.colors
        card = tk.Frame(parent, bg=c['card_bg'], highlightthickness=1,
                        highlightbackground=c['border'])
        value = tk.Label(card, text='0', bg=c['card_bg'],
                         fg=accent or c['fg'], font=('Segoe UI Semibold',17),
                         anchor='w')
        value.pack(anchor='w', padx=14, pady=(9,1))
        tk.Label(card, text=title, bg=c['card_bg'], fg=c['fg'],
                 font=('Segoe UI Semibold',8), anchor='w').pack(
                     anchor='w', padx=14, pady=(0,1))
        sub = tk.Label(card, text=hint, bg=c['card_bg'], fg=c['accent'],
                       font=('Segoe UI',7), anchor='w')
        sub.pack(anchor='w', padx=14, pady=(0,8))
        self._dashboard_cards[key] = (value, sub)
        return card

    def _build_modern_dashboard(self, parent):
        c = Theme.colors

        top = tk.Frame(parent, bg=c['bg'], height=66)
        top.pack(fill=tk.X)
        top.pack_propagate(False)

        specs = (
            ('progress','ПРОЙДЕНО','текущая партия',c['accent']),
            ('ready','В READY','готово к внесению',c['success']),
            ('firstpass','СРАЗУ ПРИНЯТО','первый проход',c['success']),
            ('recheck','СПАСЕНО RECHECK','второй проход',c['accent']),
            ('manual','ВРУЧНУЮ','осталось оператору',c['warning']),
            ('eta','ОСТАЛОСЬ','примерная оценка',c['fg']),
        )
        for col,(key,title,hint,accent) in enumerate(specs):
            top.grid_columnconfigure(col, weight=1, uniform='dashboard')
            card = self._dashboard_card(top,key,title,hint,accent)
            card.grid(
                row=0, column=col, sticky='nsew',
                padx=(0 if col==0 else 2, 0 if col==len(specs)-1 else 2)
            )

        status_card = tk.Frame(
            parent, bg=c['bg_secondary'], height=46,
            highlightthickness=1, highlightbackground=c['border']
        )
        status_card.pack(fill=tk.X, pady=(6,0))
        status_card.pack_propagate(False)

        status_top = tk.Frame(status_card, bg=c['bg_secondary'], height=29)
        status_top.pack(fill=tk.X)
        status_top.pack_propagate(False)

        self._dashboard_state = tk.Label(
            status_top, text='ГОТОВ',
            bg=c['success'], fg='white',
            font=('Segoe UI',9,'bold'),
            padx=12, pady=3
        )
        self._dashboard_state.pack(side=tk.LEFT, padx=(8,8), pady=4)

        self._dashboard_route = tk.Label(
            status_top,
            text='Готово к запуску нового пакета',
            bg=c['bg_secondary'], fg=c['fg'],
            font=('Segoe UI',9,'bold'),
            anchor='w'
        )
        self._dashboard_route.pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0,8)
        )

        self._dashboard_progress_text = tk.Label(
            status_top, text='0%',
            bg=c['bg_secondary'], fg=c['accent'],
            font=('Segoe UI',9,'bold'),
            width=5, anchor='e'
        )
        self._dashboard_progress_text.pack(side=tk.RIGHT, padx=(6,10))

        progress_row = tk.Frame(status_card, bg=c['bg_secondary'], height=12)
        progress_row.pack(fill=tk.X, padx=8, pady=(0,5))
        progress_row.pack_propagate(False)

        style = ttk.Style()
        style.configure(
            'Dashboard.Horizontal.TProgressbar',
            troughcolor=c['card_bg'], background=c['accent'],
            bordercolor=c['border'], lightcolor=c['accent'],
            darkcolor=c['accent'], thickness=8
        )

        self._dashboard_progress = ttk.Progressbar(
            progress_row,
            style='Dashboard.Horizontal.TProgressbar',
            orient=tk.HORIZONTAL,
            mode='determinate',
            maximum=100
        )
        self._dashboard_progress.pack(fill=tk.X, expand=True)

    def _count_ready_pending(self):
        now=time.monotonic()
        cached_at,cached_value=getattr(self,'_dashboard_ready_cache',(0.0,0))
        if now-cached_at < 4.0:
            return cached_value
        count=0
        try:
            for folder,dirs,files in os.walk(READY_FOLDER_PATH):
                dirs[:] = [d for d in dirs if d.casefold() not in ('внесено','vneseno','processed')]
                parts={part.casefold() for part in os.path.normpath(folder).split(os.sep)}
                if 'внесено' in parts or 'vneseno' in parts:
                    continue
                count += sum(1 for name in files if name.lower().endswith('.pdf'))
        except Exception:
            logger.debug('Не удалось обновить счётчик ready',exc_info=True)
            count=cached_value
        self._dashboard_ready_cache=(now,count)
        return count

    @staticmethod
    def _dashboard_time(seconds):
        seconds=max(0,int(seconds or 0))
        if seconds >= 3600:
            return f'{seconds//3600:02d}:{seconds%3600//60:02d}:{seconds%60:02d}'
        return f'{seconds//60:02d}:{seconds%60:02d}'

    def _refresh_modern_dashboard(self):
        if self._closing or not self._dashboard_cards:
            return
        try:
            if self.ocr_busy:
                if hasattr(self,'fio_conf_label'): self.fio_conf_label.config(text='…', fg=Theme.colors['accent'])
                if hasattr(self,'kv_conf_label'): self.kv_conf_label.config(text='…', fg=Theme.colors['accent'])
            display_files=list(self._batch_original_files or self.pdf_files)
            total=len(display_files)
            if self._auto_recheck_phase:
                processed=total
            else:
                processed=min(max(0,int(self.current_index or 0)),total)
            statuses=dict(self._statuses)
            keys={self._key(doc) for doc in display_files if self._valid_document(doc)}
            done=sum(1 for key,value in statuses.items() if key in keys and value=='done')
            review=sum(1 for key,value in statuses.items() if key in keys and value=='review')
            duplicate=sum(1 for key,value in statuses.items() if key in keys and value=='duplicate')
            decided=done+review+duplicate
            autorate=(done/decided*100.0) if decided else 0.0
            percent=(processed/total*100.0) if total else 0.0

            timings=[float(x) for x in self.ocr_times[-8:]
                     if isinstance(x,(int,float)) and x>0]
            if len(timings) >= 4:
                ordered = sorted(timings)
                trimmed = ordered[1:-1]
                timings = trimmed or ordered
            avg=(sum(timings)/len(timings)) if timings else float(getattr(self,'last_ocr_time',0) or 0)
            perf_docs=int(getattr(self,'_ocr_perf_docs',0) or 0)
            perf_seconds=float(getattr(self,'_ocr_perf_seconds',0.0) or 0.0)
            batch_avg=(perf_seconds/perf_docs) if perf_docs else avg
            docs_per_min=(60.0/batch_avg) if batch_avg>0 else 0.0
            remaining=max(0,total-processed)
            eta=avg*remaining if avg>0 else 0
            ready=self._count_ready_pending()
            firstpass=int(getattr(self,'_first_pass_done_count',done) or done)
            recheck_saved=int(getattr(self,'_recheck_saved_count',0) or 0)
            manual_count=(len(self._batch_review_keys) if self._batch_original_files
                          else int(getattr(self,'_manual_remaining_count',
                                           len(self.review_queue)) or 0))
            denominator=max(1,done+review+duplicate)

            values={
                'progress':(f'{processed} / {total}',f'{percent:.0f}% партии'),
                'ready':(str(ready),'реально лежит в ready'),
                'firstpass':(str(firstpass),
                             f'{firstpass/denominator*100:.0f}% решений без recheck'),
                'recheck':(str(recheck_saved),
                           f'{recheck_saved / denominator * 100:.0f}% спасено перепроверкой'),
                'manual':(str(manual_count),
                          f'{manual_count/denominator*100:.0f}% осталось оператору'),
                'eta':(self._dashboard_time(eta) if eta else '—',
                       ((f'{batch_avg:.1f} с/док • {docs_per_min:.1f} док/мин')
                        if batch_avg>0 else f'осталось документов: {remaining}'))
            }
            for key,(value,hint) in values.items():
                label,sub=self._dashboard_cards[key]
                label.config(text=value)
                sub.config(text=hint)

            if self._dashboard_progress is not None:
                self._dashboard_progress['value']=percent
            if self._dashboard_progress_text is not None:
                self._dashboard_progress_text.config(text=f'{percent:.0f}%')

            c=Theme.colors
            if self._mandatory_training:
                state='НУЖНО ОБУЧЕНИЕ'; bg=c['warning']; fg='#101010'
            elif self.is_paused:
                state='ПАУЗА'; bg=c['warning']; fg='#101010'
            elif self._auto_recheck_phase and self.is_running:
                state='AUTO RECHECK'; bg='#8b5cf6'; fg='white'
            elif self.ocr_busy:
                state='OCR РАБОТАЕТ'; bg=c['accent']; fg='white'
            elif self.is_running:
                state='ПАКЕТ ИДЁТ'; bg=c['success']; fg='white'
            elif self.mode=='entry':
                state='РУЧНОЙ ВВОД'; bg='#8b5cf6'; fg='white'
            elif getattr(self,'ocr_error',None):
                state='ОШИБКА OCR'; bg=c['error']; fg='white'
            elif self.review_mode or (
                    self._displayed_document is not None and
                    min(float(getattr(self,'fio_confidence',0) or 0),
                        float(getattr(self,'kv_confidence',0) or 0)) < OCR_REVIEW_THRESHOLD):
                state='НУЖНА ПРОВЕРКА'; bg=c['warning']; fg='#101010'
            else:
                state='ГОТОВ'; bg=c['success']; fg='white'
            self._dashboard_state.config(text=state,bg=bg,fg=fg)

            template=getattr(self,'active_layout_template',None) or '—'
            engine=getattr(self,'ocr_engine_name',None) or '—'
            fio=int(float(getattr(self,'fio_confidence',0) or 0))
            room=int(float(getattr(self,'kv_confidence',0) or 0))
            if self._mandatory_training:
                route_text=('Обучение на паузе — выделите ФИО и № помещения'
                            if self._training_reason == 'Обучение пользователем на паузе'
                            else 'Новый бланк — требуется обучение')
            elif self.is_paused:
                route_text='Пауза — прогресс сохранён'
            elif self._auto_recheck_phase and self.is_running:
                route_text=f'Перепроверка {self.current_index}/{len(self.pdf_files)} сомнительных документов'
            elif self.ocr_busy:
                route_text='OCR текущего документа'
            elif self.is_running:
                route_text='Автоматическая обработка партии'
            elif self.mode=='entry':
                route_text='Ручной ввод'
            elif getattr(self,'ocr_error',None):
                route_text=str(self.ocr_error)[:120]
            elif self.review_mode:
                route_text='Документ требует решения'
            else:
                route_text='Готово к запуску нового пакета'
            self._dashboard_route.config(text=route_text)
        except Exception:
            logger.exception('Ошибка обновления dashboard')

    def _schedule_dashboard_refresh(self):
        try:
            if self._dashboard_after:
                self.parent.after_cancel(self._dashboard_after)
        except Exception:
            pass
        def tick():
            if self._closing:
                return
            self._refresh_modern_dashboard()
            self._dashboard_after=self.parent.after(1000,tick)
        self._dashboard_after=self.parent.after(150,tick)

    def toggle_auto_recheck(self):
        if self.ocr_busy or self.saving_busy or self.is_running:
            return
        self.auto_recheck_enabled = not bool(getattr(self,'auto_recheck_enabled',True))
        if hasattr(self,'btn_auto_recheck'):
            self.btn_auto_recheck.config(
                text='Максимум авто: ВКЛ' if self.auto_recheck_enabled else 'Максимум авто: ВЫКЛ',
                bg=Theme.colors['success'] if self.auto_recheck_enabled else Theme.colors['btn'],
                fg='white' if self.auto_recheck_enabled else Theme.colors['fg']
            )
        self.log_label.config(text=(
            'Автоматическая пакетная перепроверка включена.' if self.auto_recheck_enabled
            else 'Автоматическая перепроверка отключена: после первого прохода останется обычная очередь проверки.'
        ))
        self.save_progress()

    def _prepare_auto_recheck(self):
        docs=[]; seen=set()
        allowed=set(getattr(self,'_batch_review_keys',set()) or set())
        for item in list(self.review_queue):
            try:
                doc=(item.get('oss'),item.get('filename'))
                if not self._valid_document(doc):
                    continue
                key=self._key(doc)
                if allowed and key not in allowed:
                    continue
                if not os.path.isfile(os.path.join(SOURCE_FOLDER_PATH,*doc)):
                    continue
                if key in seen:
                    continue
                seen.add(key); docs.append(doc)
            except Exception:
                continue
        self._recheck_source_queue=list(docs)
        return docs

    def _start_auto_recheck(self):
        docs=self._prepare_auto_recheck()
        if not docs:
            self._manual_remaining_count=0
            return False
        self._auto_recheck_phase=True
        self._auto_recheck_started=True
        self.review_mode=True
        self.mode='auto'
        self.pdf_files=list(docs)
        self.current_index=0
        self.is_running=self.batch_busy=True
        self.is_paused=self.stop_flag=False
        self.start_time=time.time()
        self._batch_review_reason_by_doc={}
        self.status_panel.config(text='AUTO RECHECK • углублённая перепроверка сомнительных',fg='#8b5cf6')
        self.log_label.config(text=f'Второй проход: пакетно перепроверяю {len(docs)} документов. Надёжные автоматически уйдут в ready.')
        self._controls(); self.save_progress(); self.load_file()
        return True

    def _recheck_result_verified(self, result):
        if not result or result.get('ocr_error'):
            return False
        fios=list(result.get('recognized_fios') or result.get('fios') or self.recognized_fios or [])
        room=str(result.get('recognized_kv') or result.get('room') or self.recognized_kv or '').strip()
        two_word_verified = bool(
            result.get('owner_two_word_verified') and result.get('accepted') and
            'SmartConsensus' in str(result.get('fio_engine_name') or '') and
            'OwnerField' in str(result.get('fio_engine_name') or '') and
            len(fios) == 1 and len(str(fios[0]).split()) == 2 and
            self._smart_two_word_owner_candidate(fios[0]) == fios[0])
        if (not self._fio_list_valid(fios) and not two_word_verified) or not room or room=='0':
            return False
        fio_conf=float(result.get('fio_confidence',self.fio_confidence) or 0)
        room_conf=float(result.get('kv_confidence',self.kv_confidence) or 0)
        fio_route=str(result.get('fio_engine_name') or self.fio_engine_name or '')
        room_route=str(result.get('kv_engine_name') or self.kv_engine_name or '')

        if result.get('accepted'):
            if len(fios) > 1 and not any(tag in fio_route for tag in ('TemplateROI','TurboROI','SmartConsensus')):
                return False
            if fio_conf < OCR_REVIEW_THRESHOLD or room_conf < OCR_REVIEW_THRESHOLD:
                return False
            if result.get('active_layout_template'):
                if not any(tag in fio_route for tag in ('TemplateROI','TurboROI','SmartConsensus')):
                    return False
            return True

        document = tuple(self.pdf_files[self.current_index]) if self.current_index < len(self.pdf_files) else None
        previous = self._review_item_for(document) if document else None
        if not previous:
            return False
        normalize = lambda value: ' '.join(str(value or '').casefold().replace('ё','е').split())
        previous_fios = [normalize(value) for value in list(previous.get('fios') or [])]
        current_fios = [normalize(value) for value in fios]
        previous_template = str(previous.get('active_template') or '')
        current_template = str(result.get('active_layout_template') or self.active_layout_template or '')
        return bool(
            previous_fios == current_fios and current_fios and
            previous_template and previous_template == current_template and
            any(tag in fio_route for tag in ('TemplateROI','TurboROI','SmartConsensus')) and
            'LabeledRoom' in room_route and
            fio_conf >= 65 and room_conf >= OCR_REVIEW_THRESHOLD
        )

    def toggle_turbo_batch(self):
        if self.ocr_busy or self.saving_busy or self.is_running:
            return
        self.turbo_batch_mode = not self.turbo_batch_mode
        self.btn_turbo.config(text='Турбо: ВКЛ' if self.turbo_batch_mode else 'Турбо: ВЫКЛ',
                              bg=Theme.colors['success'] if self.turbo_batch_mode else Theme.colors['btn'],
                              fg='white' if self.turbo_batch_mode else Theme.colors['fg'])
        self.log_label.config(text=(
            '🚀 Турбо-пакет включён: знакомые шаблоны читаются только по сохранённым ROI; '
            'сомнительные автоматически идут в обычный OCR.' if self.turbo_batch_mode else
            'Турбо-пакет выключен: используется обычный адаптивный OCR.'))
        self.save_progress()

    @staticmethod
    def _key(document):
        return str(document[0])+'\n'+str(document[1])

    @staticmethod
    def _valid_document(document):
        return (isinstance(document, (list,tuple)) and len(document)==2
                and str(document[0]).isdigit() and isinstance(document[1],str)
                and document[1].lower().endswith('.pdf')
                and not any(c in document[1] for c in ('/','\\','\x00')))

    @staticmethod
    def _fingerprint(path):
        try:
            st = os.stat(path)
            return [st.st_size, st.st_mtime_ns]
        except OSError: return None

    def _manual_focus_room(self, event=None):
        if self.mode != 'entry': return None
        self.kv_entry.focus_set()
        self.kv_entry.selection_range(0, tk.END)
        return 'break'

    def _manual_confirm_key(self, event=None):
        if self.mode != 'entry': return None
        self.confirm()
        return 'break'

    def _pump_ui_queue(self):
        if self._closing: return
        self.parent.after(30, self._pump_ui_queue)
        for _ in range(25):
            try: func,args,kwargs,done,holder = self.ui_queue.get_nowait()
            except queue.Empty: break
            try: holder['value'] = func(*args, **kwargs)
            except Exception as exc:
                holder['error'] = exc
                logger.exception('Ошибка обновления интерфейса')
            finally:
                if done: done.set()

    def _draft_changed(self, event=None):
        if self.ocr_busy or self.saving_busy: return
        if self._draft_after:
            try: self.parent.after_cancel(self._draft_after)
            except tk.TclError: pass
        self._draft_after = self.parent.after(500, self._save_draft)

    def _save_draft(self):
        self._draft_after = None
        self._capture_draft()
        self.save_progress()

    def _capture_draft(self):
        if self._displayed_document is None or self.ocr_busy or self.saving_busy: return
        values = [e.get().strip() for e in self.fio_entries]
        room = self.kv_entry.get().strip()
        if (values == (list(getattr(self, '_raw_ocr_fields', []))+['']*len(values))[:len(values)]
                and room == str(getattr(self, '_raw_ocr_room', '') or '0')):
            self._drafts.pop(self._key(self._displayed_document), None)
            return
        self._drafts[self._key(self._displayed_document)] = {
            'fios': values, 'room': room,
            'fingerprint': self._displayed_fingerprint}

    def _manual_timer_value(self):
        current = self._manual_current_seconds
        if self._manual_timer_started is not None:
            current += max(0.0, time.monotonic() - self._manual_timer_started)
        return max(0.0, self.manual_input_seconds + current)

    def _start_manual_timer(self, document=None):
        if self.mode != 'entry' or document is None:
            return
        key = self._key(document)
        if self._manual_timer_document != key:
            self._manual_current_seconds = 0.0
            self._manual_timer_document = key
        if self._manual_timer_started is None:
            self._manual_timer_started = time.monotonic()

    def _pause_manual_timer(self):
        if self._manual_timer_started is not None:
            self._manual_current_seconds += max(0.0, time.monotonic() - self._manual_timer_started)
            self._manual_timer_started = None

    def _commit_manual_timer(self):
        self._pause_manual_timer()
        if self._manual_timer_document is not None:
            self.manual_input_seconds += max(0.0, self._manual_current_seconds)
            self.manual_input_documents += 1
        self._manual_current_seconds = 0.0
        self._manual_timer_document = None

    def select_oss(self):
        if self.ocr_busy or self.saving_busy or self.is_running: return False
        old_statuses, old_drafts = self._statuses, self._drafts
        self._statuses, self._drafts = {}, {}
        selected = super().select_oss()
        if not selected:
            self._statuses, self._drafts = old_statuses, old_drafts
        else:
            self.manual_input_seconds = 0.0
            self.manual_input_documents = 0
            self._manual_current_seconds = 0.0
            self._manual_timer_started = None
            self._manual_timer_document = None
            self.start_time = time.time()
        return selected

    def set_mode(self, mode):
        if self.saving_busy or (self.ocr_busy and mode!='entry'):
            self.log_label.config(text='Дождитесь завершения OCR текущего бланка, затем нажмите «Ручной ROI».')
            return
        if (mode == 'manual' and self.is_running and self.is_paused
                and not self._mandatory_training):
            if self.image is None or self.current_index >= len(self.pdf_files):
                self.log_label.config(text='Для обучения сначала откройте текущий документ.')
                return
            self._mandatory_training = True
            self._training_document = tuple(self.pdf_files[self.current_index])
            self._training_reason = 'Обучение пользователем на паузе'
            self.learning_template_pending = True
        if mode == 'entry':
            self.mode='entry'
            self.btn_auto.config(relief=tk.RAISED,bg=Theme.colors['btn'])
            self.btn_manual.config(relief=tk.RAISED,bg=Theme.colors['btn'])
            self.status_label.config(text='✍ Рукописные: ввод без распознавания')
            self.log_label.config(text='OCR отключён. Введите ФИО и помещение, затем нажмите «Подтвердить».')
            if hasattr(self,'btn_entry'):self.btn_entry.config(bg=Theme.colors['accent'])
            return
        if hasattr(self,'btn_entry'):self.btn_entry.config(bg=Theme.colors['btn'],fg=Theme.colors['fg'])
        super().set_mode(mode)
        if mode == 'manual' and self._mandatory_training:
            self._controls()
            self.log_label.config(text='Выделите ФИО и № помещения, затем «Сохранить ROI». После сохранения шаблона текущий бланк будет перепроверен, пакет продолжится.')

    def _start_handwritten(self):
        if self.saving_busy or self.is_running:
            self.log_label.config(text='Сначала остановите пакетную обработку, затем включите рукописный режим.')
            return
        self.set_mode('entry')
        self.stop_flag=False
        if not getattr(self, 'start_time', None): self.start_time=time.time()
        if self.ocr_busy:
            self._switch_to_entry_pending=True
            self._cancel_job.set()
            self.status_panel.config(text='Отключаю OCR • открываю тот же бланк…',fg='#8b5cf6')
            return
        if self.pdf_files and self.current_index<len(self.pdf_files):
            self._displayed_document=None
            self.load_file()
        else:self.select_oss()

    def re_recognize(self):
        if self.mode=='entry':
            self.log_label.config(text='Для рукописных бланков OCR отключён — вводите данные вручную.')
            return
        super().re_recognize()

    def undo_last_action(self):
        if self.ocr_busy or self.saving_busy or self.is_running: return
        super().undo_last_action()
        self.save_progress()

    def save_progress(self):
        if not self._session_ready: return
        data = {'version':43, 'files':self.pdf_files, 'index':self.current_index,
                'oss':self.current_oss, 'mode':self.mode, 'review_mode':self.review_mode,
                'statuses':self._statuses, 'drafts':self._drafts,
                 'created':self.total_created, 'skipped':self.total_skipped, 'votes':self.total_votes,
                 'manual_input_seconds':self._manual_timer_value(),
                 'manual_input_documents':self.manual_input_documents,
                 'review_reasons_by_doc':self._batch_review_reason_by_doc,
                 'training_docs':list(self._batch_training_docs.keys()),
                'turbo_batch':bool(self.turbo_batch_mode),
                'auto_recheck_enabled':bool(self.auto_recheck_enabled),
                'first_pass_done_count':int(self._first_pass_done_count),
                'recheck_saved_count':int(self._recheck_saved_count),
                'ocr_perf_docs':int(self._ocr_perf_docs),
                'ocr_perf_seconds':round(float(self._ocr_perf_seconds),4),
                'ocr_perf_tesseract_calls':int(self._ocr_perf_tesseract_calls),
                'ocr_perf_auto_accepted':int(self._ocr_perf_auto_accepted),
                'template_performance':self._template_performance,
                'batch_original_files':list(self._batch_original_files),
                'batch_review_keys':list(self._batch_review_keys),
                'auto_recheck_phase':bool(self._auto_recheck_phase),
                'mandatory_training':bool(self._mandatory_training),
                'state':'paused' if self.is_paused else ('running' if self.is_running else 'stopped'),
                'timestamp':datetime.now().isoformat()}
        if not atomic_json_save(self._session_file, data):
            self.is_paused = True
            self.log_label.config(text='Не удалось сохранить сеанс. Освободите место на диске.')

    def _startup_session(self):
        saved = safe_json_load(self._session_file, {})
        valid = (isinstance(saved,dict) and saved.get('version')==43
                 and isinstance(saved.get('files'),list)
                 and all(self._valid_document(d) for d in saved['files']))
        if not valid and not self.review_queue:
            self.select_oss()
            return
        window = tk.Toplevel(self.parent)
        window.title('OCR Studio — продолжение работы')
        window.geometry('600x230')
        window.configure(bg=Theme.colors['bg'])
        tk.Label(window,text='Продолжим с сохранённого места?',bg=Theme.colors['bg'],
                 fg=Theme.colors['fg'],font=('Segoe UI',17,'bold')).pack(pady=20)
        tk.Label(window,text=f'Документов в очереди проверки: {len(self.review_queue)}',
                 bg=Theme.colors['bg'],fg=Theme.colors['fg']).pack(pady=8)
        bar = tk.Frame(window,bg=Theme.colors['bg']); bar.pack(pady=12)
        def choose(fn):
            window.destroy(); fn()
        if valid:
            make_button(bar,'Продолжить',lambda:choose(lambda:self._restore_session(saved)),
                        bg=Theme.colors['success'],fg='white').pack(side=tk.LEFT,padx=4)
        make_button(bar,'Проверка',lambda:choose(self.open_review_queue)).pack(side=tk.LEFT,padx=4)
        make_button(bar,'Новый пакет',lambda:choose(self.select_oss)).pack(side=tk.LEFT,padx=4)

    def _restore_session(self, saved):
        self.pdf_files = [tuple(d) for d in saved['files']]
        self.current_index = max(0,min(int(saved.get('index',0)),len(self.pdf_files)))
        self.current_oss = saved.get('oss')
        saved_mode = saved.get('mode')
        self.mode = saved_mode if saved_mode in ('auto','entry') else 'auto'
        self.review_mode = bool(saved.get('review_mode'))
        self._statuses = saved.get('statuses',{}) if isinstance(saved.get('statuses'),dict) else {}
        self._drafts = saved.get('drafts',{}) if isinstance(saved.get('drafts'),dict) else {}
        self.total_created = int(saved.get('created',0))
        self.total_skipped = int(saved.get('skipped',0))
        self.total_votes = int(saved.get('votes',0))
        self.manual_input_seconds = max(0.0, float(saved.get('manual_input_seconds',0) or 0))
        self.manual_input_documents = max(0, int(saved.get('manual_input_documents',0) or 0))
        reasons = saved.get('review_reasons_by_doc', {})
        self._batch_review_reason_by_doc = reasons if isinstance(reasons, dict) else {}
        training_docs = saved.get('training_docs', [])
        self._batch_training_docs = {str(key): True for key in training_docs} if isinstance(training_docs, list) else {}
        self.turbo_batch_mode = bool(saved.get('turbo_batch', True))
        self.auto_recheck_enabled = bool(saved.get('auto_recheck_enabled', True))
        self._first_pass_done_count = int(saved.get('first_pass_done_count',0) or 0)
        self._recheck_saved_count = int(saved.get('recheck_saved_count',0) or 0)
        self._ocr_perf_docs = int(saved.get('ocr_perf_docs',0) or 0)
        self._ocr_perf_seconds = float(saved.get('ocr_perf_seconds',0.0) or 0.0)
        self._ocr_perf_tesseract_calls = int(
            saved.get('ocr_perf_tesseract_calls',0) or 0)
        self._ocr_perf_auto_accepted = int(
            saved.get('ocr_perf_auto_accepted',0) or 0)
        template_performance = saved.get('template_performance', {})
        self._template_performance = (template_performance
                                      if isinstance(template_performance, dict) else {})
        self._manual_remaining_count = len(self.review_queue)
        original = saved.get('batch_original_files', [])
        self._batch_original_files = [tuple(d) for d in original
                                      if self._valid_document(d)] if isinstance(original,list) else []
        self._batch_original_keys = {self._key(d) for d in self._batch_original_files}
        review_keys = saved.get('batch_review_keys', [])
        self._batch_review_keys = {str(k) for k in review_keys} if isinstance(review_keys,list) else set()
        self._auto_recheck_phase = bool(saved.get('auto_recheck_phase', False))
        if hasattr(self, 'btn_turbo'):
            self.btn_turbo.config(text='Турбо: ВКЛ' if self.turbo_batch_mode else 'Турбо: ВЫКЛ',
                                  bg=Theme.colors['success'] if self.turbo_batch_mode else Theme.colors['btn'],
                                  fg='white' if self.turbo_batch_mode else Theme.colors['fg'])
        self._manual_current_seconds = 0.0
        self._manual_timer_started = None
        self._manual_timer_document = None
        self.stop_flag = False
        restart_training = bool(saved.get('mandatory_training'))
        if restart_training:
            self.mode = 'auto'
            self._mandatory_training = False
            self._training_document = None
        while self.current_index < len(self.pdf_files):
            doc = self.pdf_files[self.current_index]
            if os.path.isfile(os.path.join(SOURCE_FOLDER_PATH,*doc)): break
            self.current_index += 1
        if self.current_index >= len(self.pdf_files):
            self.open_review_queue()
        elif self.review_mode and self.mode == 'auto':
            self._manual_review_open = False
            self._resume_saved_review_batch()
        elif self.review_mode or self.mode=='entry':
            self.load_file()
        else:
            self._begin_batch()

    @staticmethod
    def _confidence_color(value):
        value=float(value or 0)
        c=Theme.colors
        if value >= 90: return c['success']
        if value >= OCR_REVIEW_THRESHOLD: return c['accent']
        if value >= 65: return c['warning']
        return c['error']

    def _refresh_result_confidence_ui(self):
        fio=float(getattr(self,'fio_confidence',0) or 0)
        room=float(getattr(self,'kv_confidence',0) or 0)
        if hasattr(self,'fio_conf_label'):
            self.fio_conf_label.config(text=f'{fio:.0f}%', fg=self._confidence_color(fio))
        if hasattr(self,'kv_conf_label'):
            self.kv_conf_label.config(text=f'{room:.0f}%', fg=self._confidence_color(room))
        if hasattr(self,'room_value_hint'):
            value=str(getattr(self,'recognized_kv','') or '').strip()
            self.room_value_hint.config(text=f'Распознано: {value}' if value else '')
        if hasattr(self,'fio_conf_bar'): self.fio_conf_bar['value']=max(0,min(100,fio))
        if hasattr(self,'kv_conf_bar'): self.kv_conf_bar['value']=max(0,min(100,room))
        if hasattr(self,'review_hint'):
            if self.mode=='entry':
                msg='Ручной ввод'
            elif fio >= OCR_REVIEW_THRESHOLD and room >= OCR_REVIEW_THRESHOLD:
                msg='Данные выглядят надёжно'
            elif fio < OCR_REVIEW_THRESHOLD and room < OCR_REVIEW_THRESHOLD:
                msg='Проверьте ФИО и номер помещения'
            elif fio < OCR_REVIEW_THRESHOLD:
                msg='Проверьте ФИО собственника'
            else:
                msg='Проверьте номер помещения'
            self.review_hint.config(text=msg)

    def _controls(self):
        busy = self.ocr_busy or self.saving_busy
        resumable_review = (
            self.review_mode and self.mode == 'auto' and
            not getattr(self, '_manual_review_open', False) and
            bool(self.pdf_files) and self.current_index < len(self.pdf_files)
        )
        self.btn_start.config(state=tk.DISABLED if busy or self.is_running else tk.NORMAL)
        self.btn_pause.config(state=tk.NORMAL if self.is_running and not self.is_paused else tk.DISABLED)
        self.btn_resume.config(state=tk.NORMAL if (
            (self.is_paused or resumable_review) and not self._mandatory_training and not busy
        ) else tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL if busy or self.is_running else tk.DISABLED)
        action_pending = bool(self._batch_document_action)
        has_current = (
            self.current_index < len(self.pdf_files) and
            self._valid_document(self.pdf_files[self.current_index])
        )
        batch_action_state = (tk.NORMAL if has_current and not self.saving_busy
                              and not action_pending else tk.DISABLED)
        if hasattr(self, 'btn_skip_current'):
            self.btn_skip_current.config(state=batch_action_state)
        if hasattr(self, 'btn_exclude_current'):
            self.btn_exclude_current.config(state=batch_action_state)
        self.btn_roi_batch.config(state=tk.NORMAL if self.roi_saved and not busy and not self.is_running else tk.DISABLED)
        if hasattr(self, 'btn_turbo'):
            self.btn_turbo.config(state=tk.DISABLED if busy or self.is_running else tk.NORMAL)
        if hasattr(self,'btn_auto_recheck'):
            self.btn_auto_recheck.config(state=tk.DISABLED if busy or self.is_running else tk.NORMAL)
        for entry in self.fio_entries+[self.kv_entry]:
            entry.config(state=tk.DISABLED if busy or (self.is_running and not self.is_paused and not self._mandatory_training) else tk.NORMAL)
        action_busy = busy or (
            self.is_running and not self.is_paused and not self._mandatory_training and
            not getattr(self, '_manual_review_open', False)
        )
        for name in ('btn_confirm_result','btn_review_result','btn_edit_result'):
            if hasattr(self,name): getattr(self,name).config(state=tk.DISABLED if action_busy else tk.NORMAL)
        if hasattr(self, 'btn_review_result'):
            self.btn_review_result.config(
                text=('ПРОПУСТИТЬ БЕЗ ОБУЧЕНИЯ'
                      if self._mandatory_training else 'НА ПРОВЕРКУ'))
        if hasattr(self,'more_result_menu'):
            try:
                self.more_result_menu.entryconfig('Повторить OCR',
                    state=tk.DISABLED if action_busy else tk.NORMAL)
                self.more_result_menu.entryconfig('Отменить последнее действие',
                    state=tk.DISABLED if busy or self.is_running else tk.NORMAL)
            except tk.TclError:
                pass
        if self._mandatory_training and not busy:
            self.btn_fio.config(state=tk.NORMAL)
            self.btn_kv.config(state=tk.NORMAL)
            self.btn_save_roi.config(state=tk.NORMAL)
            self.btn_teach.config(state=tk.NORMAL)
        if hasattr(self,'studio_counts'):
            eta=''
            timings=[x for x in self.ocr_times[-8:] if isinstance(x,(int,float)) and x>0]
            if self.is_running and timings:
                stable = sorted(timings)[1:-1] if len(timings) >= 4 else timings
                seconds=int(sum(stable)/len(stable)*max(0,len(self.pdf_files)-self.current_index))
                eta=f'    Осталось ≈ {seconds//3600:02d}:{seconds%3600//60:02d}:{seconds%60:02d}'
            self.studio_counts.config(text=f'Готово: {self.total_created}    Проверить: {len(self.review_queue)}    '
                                           f'Пройдено: {self.current_index}/{len(self.pdf_files)}{eta}' +
                                           (f'    Ручной ввод: {int(self._manual_timer_value())//60:02d}:'
                                            f'{int(self._manual_timer_value())%60:02d}' if self.mode=='entry' else ''))

    def _refresh_view_controls(self):
        if not hasattr(self, 'view_mode_label'):
            return
        labels = {'page':'Вид: Вся страница',
                  'width':'Вид: По ширине',
                  'custom':'Вид: Пользовательский'}
        self.view_mode_label.config(text=labels.get(self._view_fit_mode, 'Вид: Вся страница'))

    def _save_view_preferences(self):
        saved=atomic_json_save(self._view_preferences_file, {
            'mode': self._view_fit_mode,
            'zoom': round(float(getattr(self, '_saved_custom_zoom', self.zoom)), 3),
            'updated_at': datetime.now().isoformat()})
        self._refresh_view_controls()
        if not saved and hasattr(self,'log_label'):
            self.log_label.config(text='Не удалось запомнить вид. Проверьте доступ к папке программы.')
        return saved

    def _apply_saved_view(self):
        if self.image is None: return
        if self._view_fit_mode == 'width': self.fit_width(False)
        elif self._view_fit_mode == 'custom':
            self.zoom = max(.2, min(3., self._saved_custom_zoom))
            self.update_image(); self.canvas.xview_moveto(0); self.canvas.yview_moveto(0)
        else: self.fit_page(False)
        self._refresh_view_controls()

    def fit_page(self, remember=True):
        if self.image is None:return
        self.canvas.update_idletasks()
        width=max(200,self.canvas.winfo_width()-20);height=max(200,self.canvas.winfo_height()-20)
        self.zoom=max(.1,min(3.,width/max(1,self.original_width),height/max(1,self.original_height)))
        self.update_image();self.canvas.xview_moveto(0);self.canvas.yview_moveto(0)
        if remember:
            self._view_fit_mode='page'
            self._save_view_preferences()

    def fit_width(self, remember=True):
        if self.image is None:return
        self.canvas.update_idletasks()
        self.zoom=max(.1,min(3.,max(200,self.canvas.winfo_width()-20)/max(1,self.original_width)))
        self.update_image();self.canvas.xview_moveto(0);self.canvas.yview_moveto(0)
        if remember:
            self._view_fit_mode='width'
            self._save_view_preferences()

    def zoom_in(self):
        super().zoom_in()
        self._view_fit_mode='custom'; self._saved_custom_zoom=self.zoom
        self._save_view_preferences()

    def zoom_out(self):
        super().zoom_out()
        self._view_fit_mode='custom'; self._saved_custom_zoom=self.zoom
        self._save_view_preferences()

    def reset_zoom(self):
        super().reset_zoom()
        self._view_fit_mode='custom'; self._saved_custom_zoom=1.0
        self._save_view_preferences()

    def _review_item_for(self, document):
        if not self.review_mode:
            return None
        return next((item for item in self.review_queue
                     if (item.get('oss'), item.get('filename')) == tuple(document)), None)

    def _review_ocr_context(self, document):
        if self.mode == 'entry':
            return 'entry', {}
        item = self._review_item_for(document)
        if not item:
            return self.mode, {}
        route = item.get('recognition_route')
        if route == 'roi':
            mode = 'manual'
        elif route == 'auto':
            mode = 'auto'
        else:
            mode = 'manual' if self.mode == 'manual' and self.roi_saved else 'auto'
        fio_norm = item.get('review_fio_roi_norm')
        kv_norm = item.get('review_kv_roi_norm')
        overrides = {}
        if mode == 'manual' and fio_norm and kv_norm:
            overrides = {
                'saved_roi_data': {'version': 3, 'fio_roi': fio_norm, 'kv_roi': kv_norm},
                'saved_fio_roi': [1, 1, 2, 2],
                'saved_kv_roi': [1, 1, 2, 2],
                'fio_roi': None,
                'kv_roi': None,
            }
        return mode, overrides

    def load_file(self):
        if self._closing or self.ocr_busy or self.saving_busy or self.stop_flag: return False
        if self.current_index >= len(self.pdf_files):
            self._finish_batch_ui() if self.is_running else self.open_review_queue()
            return False
        self._capture_draft()
        document = self.pdf_files[self.current_index]
        if not self._valid_document(document):
            self.stop_process(); self.log_label.config(text='Недопустимый путь PDF в сеансе'); return False
        self._displayed_document = None
        self.image = None
        self.canvas.itemconfig(self.canvas_image, image='')
        self.canvas.delete('annotation')
        self.detected_fio_roi = self.detected_kv_roi = None
        self.fio_roi = self.kv_roi = None
        self.recognized_fios, self.recognized_kv = [], None
        self.fio_confidence = self.kv_confidence = 0.
        self.ocr_error = None
        self.info.config(text=f'ОСС {document[0]}  •  {self.current_index+1}/{len(self.pdf_files)}  •  {document[1]}')
        self._apply_recognized([],None)
        request_mode, review_overrides = self._review_ocr_context(document)
        has_review_roi = bool(review_overrides.get('saved_roi_data'))
        self._start_ocr_request(
            pdf_path=os.path.join(SOURCE_FOLDER_PATH,*document),
            mode=request_mode,
            recognize=(request_mode != 'entry' and
                       (request_mode == 'auto' or self.roi_saved or has_review_roi)),
            request_overrides=review_overrides)
        return True

    def auto_recognize(self):
        if self.image is not None: self._start_ocr_request(image=self.image,mode='auto')

    def manual_recognize(self):
        if self.image is not None: self._start_ocr_request(image=self.image,mode='manual')

    def _start_ocr_request(self, pdf_path=None, image=None, mode=None, recognize=True,
                           request_overrides=None):
        if self.ocr_busy or self.saving_busy or self._closing: return
        self._job_number += 1
        number = self._job_number
        self._cancel_job = threading.Event()
        cancellation = self._cancel_job
        self.ocr_busy = True
        self._pending_result = None
        request = {'pdf_path':pdf_path,'mode':mode or self.mode,'fast_mode':self.fast_mode,
                   'templates_path':TEMPLATES_PATH,
                   'preferred_layout_template':self.active_layout_template,
                   'saved_roi_data':self.saved_roi_data,'saved_fio_roi':self.saved_fio_roi,
                   'saved_kv_roi':self.saved_kv_roi,'fio_roi':self.fio_roi,'kv_roi':self.kv_roi,
                   'fio_dictionary':list(self.fio_dictionary),'poppler':POPPLER_BIN_PATH,
                   'scoped_learning':self.scoped_learning,'recognize':recognize,
                   'deep_recheck':bool(self.review_mode or self._auto_recheck_phase or
                                       self._recheck_only),
                   'turbo_batch':bool(self.turbo_batch_mode and self.is_running and
                                      (mode or self.mode) == 'auto' and recognize)}
        if request_overrides:
            request.update(request_overrides)
        snapshot = image.copy() if image is not None else None
        doc = tuple(self.pdf_files[self.current_index]) if self.current_index < len(self.pdf_files) else None
        fingerprint = self._fingerprint(os.path.join(SOURCE_FOLDER_PATH,*doc)) if doc else None
        self.status_panel.config(text='Загружаю страницу без OCR…' if not recognize else 'Распознавание…',
                                 fg='#8b5cf6' if not recognize else Theme.colors['accent'])
        self.log_label.config(text=('OCR отключён. Подготавливаю бланк для ручного ввода.' if not recognize
                                    else 'Окно доступно. Можно свернуть, поставить паузу или остановить OCR.'))
        self._controls()
        self.save_progress()
        threading.Thread(target=self._run_job,args=(number,request,snapshot,doc,fingerprint,cancellation),daemon=False).start()

    def _stop_persistent_ocr_worker(self):
        with self._ocr_worker_lock:
            process = self._ocr_worker_process
            self._ocr_worker_process = None
            stream = self._ocr_worker_stdin
            self._ocr_worker_stdin = None
            if stream is not None:
                try: stream.close()
                except Exception: pass
            if process is not None and process.poll() is None:
                try:
                    subprocess.run(
                        ['taskkill', '/PID', str(process.pid), '/T', '/F'],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        timeout=8,
                        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                except Exception:
                    try: process.kill()
                    except Exception: pass
                try: process.wait(timeout=8)
                except Exception: pass
            if self._ocr_worker_log is not None:
                try: self._ocr_worker_log.close()
                except Exception: pass
                self._ocr_worker_log = None

    def _ensure_persistent_ocr_worker(self):
        with self._ocr_worker_lock:
            process = self._ocr_worker_process
            if process is not None and process.poll() is None and self._ocr_worker_stdin is not None:
                return process
            self._stop_persistent_ocr_worker()
            os.makedirs(LOG_DIR, exist_ok=True)
            self._ocr_worker_log = open(self._ocr_worker_log_path, 'a', encoding='utf-8')
            creation_flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            if _input_priority_active():
                creation_flags |= getattr(subprocess, 'IDLE_PRIORITY_CLASS', 0)
            process = subprocess.Popen(
                [sys.executable, '-u', os.path.abspath(__file__), '--ocr-worker'],
                stdin=subprocess.PIPE, stdout=self._ocr_worker_log,
                stderr=subprocess.STDOUT, text=True, encoding='utf-8',
                bufsize=1, creationflags=creation_flags)
            self._ocr_worker_process = process
            self._ocr_worker_stdin = process.stdin
            return process

    def _submit_persistent_ocr_job(self, job_dir):
        with self._ocr_worker_lock:
            process = self._ensure_persistent_ocr_worker()
            if process.poll() is not None or self._ocr_worker_stdin is None:
                raise RuntimeError('Постоянный OCR worker не запустился')
            self._ocr_worker_stdin.write(os.path.abspath(job_dir) + '\n')
            self._ocr_worker_stdin.flush()
            return process

    def _run_job(self, number, request, snapshot, document, fingerprint, cancellation):
        process = None
        result = None
        page_announced = False
        job_dir = None
        started_at = time.monotonic()
        worker_log_path = self._ocr_worker_log_path
        try:
            folder = os.path.join(SCRIPT_DIR, 'ocr_jobs')
            os.makedirs(folder, exist_ok=True)
            job_dir = tempfile.mkdtemp(prefix='job_', dir=folder)
            if snapshot is not None:
                request['image_path'] = os.path.join(job_dir, 'input.png')
                snapshot.save(request['image_path'])
            if not atomic_json_save_compact(os.path.join(job_dir, 'request.json'), request):
                raise IOError('Не удалось записать задание OCR')
            process = self._submit_persistent_ocr_job(job_dir)
            job_limit = 300 if request.get('deep_recheck') else 200
            deadline = time.monotonic() + job_limit
            result_path = os.path.join(job_dir, 'result.json')
            while True:
                page_path = os.path.join(job_dir, 'page.png')
                if not page_announced and os.path.isfile(page_path) and os.path.getsize(page_path) > 0:
                    page_announced = True
                    self._ui_call(self._show_job_page, number, page_path, document, fingerprint)
                candidate = safe_json_load(result_path, None) if os.path.isfile(result_path) else None
                if isinstance(candidate, dict):
                    result = candidate
                    break
                if process.poll() is not None:
                    break
                if cancellation.wait(.15):
                    result = {'cancelled': True}
                    self._stop_persistent_ocr_worker()
                    break
                if time.monotonic() > deadline:
                    result = {'ocr_error': f'Время обработки PDF превысило {job_limit} секунд',
                              'reason': 'Превышено время OCR', 'accepted': False}
                    self._stop_persistent_ocr_worker()
                    break
            if result is None:
                exit_code = process.returncode if process is not None else None
                runtime = max(0.0, time.monotonic() - started_at)
                log_tail = ''
                try:
                    with open(worker_log_path, 'r', encoding='utf-8', errors='replace') as fh:
                        log_tail = fh.read().strip()[-2500:]
                except Exception:
                    pass
                hint = (f'OCR worker завершился без result.json '
                        f'(exit={exit_code}, t={runtime:.1f}s).')
                if not page_announced:
                    hint += ' Страница не успела отрендериться.'
                if log_tail:
                    hint += '\n\n--- persistent worker log (хвост) ---\n' + log_tail
                raise RuntimeError(hint)
        except Exception as exc:
            logger.exception('Ошибка запуска OCR')
            result = {'ocr_error': str(exc),
                      'reason': 'Ошибка обработки: ' + str(exc),
                      'accepted': False}
        finally:
            if job_dir:
                for name in ('input.pdf', 'input.png'):
                    try: os.remove(os.path.join(job_dir, name))
                    except OSError: pass
            self._ui_call(self._ocr_finished, number, result, document, fingerprint)

    def _show_job_page(self,number,page_path,document,fingerprint):
        if self._closing or number!=self._job_number or document is None:return
        try:
            if self.mode != 'entry':
                for entry in self.fio_entries + [self.kv_entry]:
                    entry.config(state=tk.NORMAL)
                    entry.delete(0, 'end')
                self.room_value_hint.config(text='Распознаётся…')
                self.quality_badge.config(text='OCR В ПРОЦЕССЕ', bg=Theme.colors['accent'])
            with Image.open(page_path) as im:self.image=im.copy()
            self.original_width,self.original_height=self.image.size
            self._displayed_document=document
            self._displayed_fingerprint=fingerprint
            self._start_manual_timer(document)
            self.parent.after_idle(self._apply_saved_view)
            if self.mode=='entry':
                self.status_panel.config(text='Страница загружена • OCR отключён',fg='#8b5cf6')
                self.log_label.config(text='Введите ФИО и помещение вручную, затем нажмите «Подтвердить».')
            else:
                self.status_panel.config(text='Страница загружена • OCR работает…',fg=Theme.colors['accent'])
                self.log_label.config(text='Бланк уже доступен для просмотра. Распознавание продолжается в фоне.')
        except Exception:
            logger.exception('Не удалось показать страницу до завершения OCR')

    def _requires_template_training(self, result):
        return bool(
            self.is_running and not self.review_mode and self.mode == 'auto'
            and not result.get('ocr_error')
            and not result.get('active_layout_template')
        )

    def _pause_for_template_training(self, result, document):
        if self.is_running and document:
            try:
                self._batch_training_docs[self._key(tuple(document))] = True
            except Exception:
                pass
        self._mandatory_training = True
        self._training_document = tuple(document) if document else None
        self._training_reason = 'Неизвестный тип бланка'
        self.is_paused = True
        self.learning_template_pending = True
        self.set_mode('manual')
        if not self.fio_roi:
            self.set_select_mode('fio')
        elif not self.kv_roi:
            self.set_select_mode('kv')
        else:
            self.select_mode = None
            self.status_label.config(text='🧠 Проверьте выделенные зоны и сохраните шаблон')
        self.quality_badge.config(text='НУЖНО ОБУЧИТЬ БЛАНК', bg=Theme.colors['warning'])
        self.status_panel.config(text='⏸ Пакет ждёт обучения текущего бланка', fg=Theme.colors['warning'])
        self.log_label.config(text=(
            'Неизвестный бланк. Пакет НЕ перешёл дальше. Выделите/проверьте ФИО и помещение, '
            'нажмите «Сохранить ROI». После сохранения этот же PDF будет распознан заново, '
            'а пакет продолжится автоматически. Если документ рукописный, нажмите '
            '«ПРОПУСТИТЬ БЕЗ ОБУЧЕНИЯ».'))
        self._pending_result = result
        self.save_progress()
        self._controls()
        messagebox.showwarning(
            'Новый тип бланка — нужно обучение',
            'Пакет остановлен на текущем PDF.\n\n'
            'Проверьте или выделите область ФИО и область номера помещения, затем нажмите «Сохранить ROI».\n\n'
            'После сохранения шаблона этот же документ будет распознан повторно, и пакет продолжится автоматически.\n\n'
            'Если это рукописный документ, нажмите «ПРОПУСТИТЬ БЕЗ ОБУЧЕНИЯ»: '
            'он останется в ручной проверке, а шаблон создаваться не будет.')

    def _skip_training_without_template(self):
        if not self._mandatory_training or self.ocr_busy or self.saving_busy:
            return
        if self.current_index >= len(self.pdf_files):
            return
        if not messagebox.askyesno(
                'Пропустить без обучения?',
                'Документ будет оставлен в очереди ручной проверки.\n'
                'Шаблон для него НЕ будет создан, пакет перейдёт к следующему PDF.\n\n'
                'Продолжить?'):
            return
        document = tuple(self.pdf_files[self.current_index])
        reason = 'Рукописный документ — пропущен без обучения'
        self._enqueue_review(reason)
        try:
            self._batch_training_docs.pop(self._key(document), None)
        except Exception:
            pass
        self._mandatory_training = False
        self._training_document = None
        self._training_reason = ''
        self.learning_template_pending = False
        self._pending_result = None
        self.is_paused = False
        self.set_mode('auto')
        self.log_label.config(text=reason)
        self.status_panel.config(text='▶ Пропущен без обучения • продолжаю пакет',
                                 fg=Theme.colors['warning'])
        self.save_progress()
        self._advance('review')

    def save_current_roi(self):
        if not self._mandatory_training:
            return super().save_current_roi()
        if self.ocr_busy or self.saving_busy:
            return
        if not self.fio_roi or not self.kv_roi:
            messagebox.showwarning('Обучение бланка', 'Выделите обе области: ФИО и помещение.')
            return
        if not self.save_roi():
            messagebox.showerror('Обучение бланка', 'Не удалось сохранить области. Пакет остаётся на паузе.')
            return
        self.roi_label.config(text='📍 Области: сохранены ✅', fg=Theme.colors['success'])
        self.roi_saved = True
        default_name = f'Бланк {len(self._layout_templates()) + 1}'
        name = simpledialog.askstring(
            '🧠 Имя шаблона', 'Как назвать этот тип бланка?',
            initialvalue=default_name, parent=self.parent) or default_name
        existing = next((value for _, value in self._layout_templates()
                         if str(value.get('name', '')).casefold() == name.casefold()), None)
        if existing and not messagebox.askyesno(
                'Заменить шаблон?', f'Шаблон «{name}» уже есть. Обновить его этими областями?'):
            name = f"{name} {datetime.now().strftime('%H%M%S')}"
        saved_name = self._save_layout_template(name)
        if not saved_name:
            messagebox.showerror('Обучение бланка', 'Не удалось сохранить шаблон. Пакет остаётся на паузе.')
            return
        name = str(saved_name)

        document = self._training_document
        self.learning_template_pending = False
        self.active_layout_template = name
        self._pending_result = None
        self.is_paused = False
        self.status_panel.config(text=f'▶ Шаблон «{name}» сохранён • перепроверяю тот же бланк…',
                                 fg=Theme.colors['success'])
        self.log_label.config(text='Обучение сохранено. Повторный OCR текущего PDF по новому шаблону…')
        self.set_mode('auto')
        self._mandatory_training = False
        self._training_document = None
        self._training_reason = ''
        self.save_progress()
        self._controls()
        if document and not self.ocr_busy and self.image is not None:
            self._start_ocr_request(image=self.image, mode='auto')

    def _ocr_finished(self, number, result, document, fingerprint):
        if self._closing or number != self._job_number: return
        self.ocr_busy = False
        if result.get('cancelled') and self._batch_document_action and not self.stop_flag:
            self._complete_batch_document_action()
            return
        if result.get('cancelled') or self.stop_flag:
            self.batch_busy=False; self._controls(); self.save_progress()
            if self._switch_to_entry_pending and not self.stop_flag:
                self._switch_to_entry_pending=False
                self._displayed_document=None
                self.parent.after(50,self.load_file)
            return
        self._controls()
        self._displayed_document=document
        self._displayed_fingerprint=fingerprint
        self._start_manual_timer(document)
        for key in ('recognized_fios','recognized_kv','fio_confidence','kv_confidence','detected_fio_roi',
                    'detected_kv_roi','fio_roi','kv_roi','ocr_error','fio_engine_name','kv_engine_name',
                    'ocr_engine_name','ocr_variant_name','last_raw_fio','last_raw_kv','full_text',
                    'last_ocr_time','active_layout_template','active_layout_score'):
            if key in result: setattr(self,key,result[key])
        self.recognized_fios = result.get('recognized_fios',[]) or []
        self.recognized_kv = result.get('recognized_kv')
        self.ocr_error = result.get('ocr_error')
        self.fio_confidence = result.get('fio_confidence',0.) or 0.
        self.kv_confidence = result.get('kv_confidence',0.) or 0.
        profile = result.get('performance_profile') or {}
        try:
            recognition_seconds = float(
                profile.get('recognition_seconds', result.get('last_ocr_time', 0)) or 0)
            if recognition_seconds > 0:
                self._ocr_perf_docs += 1
                self._ocr_perf_seconds += recognition_seconds
                self._ocr_perf_tesseract_calls += int(
                    profile.get('tesseract_calls', 0) or 0)
                if result.get('accepted'):
                    self._ocr_perf_auto_accepted += 1
            template_name = str(result.get('active_layout_template') or '').strip()
            if template_name:
                stats = self._template_performance.setdefault(template_name, {
                    'attempts':0, 'accepted':0, 'review':0, 'seconds':0.0})
                stats['attempts'] = int(stats.get('attempts',0) or 0) + 1
                stats['accepted'] = int(stats.get('accepted',0) or 0) + int(bool(result.get('accepted')))
                stats['review'] = int(stats.get('review',0) or 0) + int(not bool(result.get('accepted')))
                stats['seconds'] = round(float(stats.get('seconds',0.0) or 0.0)
                                         + max(0.0, recognition_seconds), 3)
        except (TypeError, ValueError):
            logger.debug('Не удалось учесть показатели OCR', exc_info=True)
        if hasattr(self,'fio_conf_bar'): self.fio_conf_bar['value']=max(0,min(100,float(self.fio_confidence or 0)))
        if hasattr(self,'kv_conf_bar'): self.kv_conf_bar['value']=max(0,min(100,float(self.kv_confidence or 0)))
        elapsed=result.get('last_ocr_time',0.) or 0.
        if elapsed>0:self.ocr_times.append(float(elapsed))
        if result.get('image_path'):
            with Image.open(result['image_path']) as im: self.image=im.copy()
            candidate=os.path.realpath(result['image_path'])
            jobs=os.path.realpath(os.path.join(SCRIPT_DIR,'ocr_jobs'))
            if os.path.commonpath([candidate,jobs])==jobs and os.path.basename(candidate)=='page.png':
                try: os.remove(candidate)
                except OSError: pass
            self.original_width,self.original_height=self.image.size
            self._apply_saved_view()
        self._raw_ocr_fields=list(self.recognized_fios)
        self._raw_ocr_room=self.recognized_kv
        for entry in self.fio_entries+[self.kv_entry]: entry.config(state=tk.NORMAL)
        self._apply_recognized(self.recognized_fios,self.recognized_kv)
        draft=self._drafts.get(self._key(document),{}) if document else {}
        if draft and draft.get('fingerprint')==fingerprint:
            for i,e in enumerate(self.fio_entries):
                e.delete(0,'end'); e.insert(0,(draft.get('fios',[])+['']*6)[i])
            self.kv_entry.delete(0,'end'); self.kv_entry.insert(0,draft.get('room',''))
            result['accepted']=False; result['reason']='Восстановлены ручные правки: подтвердите документ'
        if self.mode=='entry':
            self.parent.after_idle(lambda:self.fio_entries[0].focus_set())
        self.log_label.config(text=result.get('reason','Распознано'))
        if self.mode=='entry':
            self.quality_badge.config(text='РУЧНОЙ ВВОД',bg='#8b5cf6')
            self.status_panel.config(text='Введите данные и подтвердите',fg=Theme.colors['accent'])
        else:
            self.quality_badge.config(text='АВТОПРОВЕРКА ПРОЙДЕНА' if result.get('accepted') else 'НУЖНА ПРОВЕРКА',
                                      bg=Theme.colors['success'] if result.get('accepted') else Theme.colors['warning'])
        self._refresh_result_confidence_ui()
        self._refresh_preview()
        self._pending_result=result
        self.save_progress()
        if self.is_running and not self.is_paused: self._consume_result()
        else:
            self.status_panel.config(text='На паузе' if self.is_paused else 'Проверьте результат',fg=Theme.colors['warning'])
            self._controls()

    def confirm_all(self, roi_batch=False):
        if self.ocr_busy or self.saving_busy or self.is_running: return
        if not self.pdf_files: self.select_oss(); return
        if self.review_mode:
            if (self.mode == 'auto' and not getattr(self, '_manual_review_open', False)
                    and self.current_index < len(self.pdf_files)):
                self._resume_saved_review_batch()
                return
            messagebox.showinfo('Проверка','Выберите новый пакет или используйте «Перепроверить и сохранить надёжные» в очереди.'); return
        if not messagebox.askyesno('Начать пакет',
                'Уверенные документы будут сохранены автоматически. Сомнительные останутся в очереди проверки. Продолжить?'): return
        self.mode='manual' if roi_batch else 'auto'
        self._begin_batch()

    @staticmethod
    def _review_reason_category(reason):
        low = str(reason or '').casefold()
        if 'обученное исправление' in low:
            return 'Обученное исправление ФИО — подтвердить'
        if 'фио' in low:
            if '2 из 3' in low or 'двумя из трёх' in low or 'consensus' in low or '72–81' in low or '72-81' in low or 'неувер' in low or 'не подтверж' in low:
                return 'ФИО — низкая/неподтверждённая уверенность'
            if 'несколько' in low or 'нестандарт' in low or 'структур' in low:
                return 'ФИО — нестандартная структура'
            return 'ФИО — требуется проверка'
        if 'номер' in low or 'помещ' in low:
            if 'отличается' in low or 'не совп' in low:
                return 'Номер помещения — расхождение'
            if 'нестандарт' in low:
                return 'Номер помещения — нестандартный формат'
            if 'не заполн' in low or 'низк' in low:
                return 'Номер помещения — низкая уверенность'
            return 'Номер помещения — требуется проверка'
        if 'шаблон' in low:
            return 'Шаблон — требуется проверка'
        if 'ручн' in low or 'правк' in low:
            return 'Ручная правка — подтвердить'
        if 'ошиб' in low:
            return 'Ошибка OCR/сохранения'
        return 'Прочее'

    def _enqueue_review(self, reason):
        super()._enqueue_review(reason)
        if getattr(self,'current_index',0) < len(getattr(self,'pdf_files',[])):
            try:
                document=tuple(self.pdf_files[self.current_index])
                key=self._key(document)
                if not self._batch_original_keys or key in self._batch_original_keys:
                    self._batch_review_keys.add(key)
                if getattr(self,'is_running',False):
                    self._batch_review_reason_by_doc[key]=self._review_reason_category(reason)
            except Exception:
                logger.debug('Не удалось записать причину review партии', exc_info=True)

    def _begin_batch(self):
        self._capture_draft()
        if not self._auto_recheck_phase:
            self._auto_recheck_started=False
            self._first_pass_done_count=0
            self._recheck_saved_count=0
            self._manual_remaining_count=0
            self._batch_original_files=list(self.pdf_files)
            self._batch_original_keys={
                self._key(doc) for doc in self._batch_original_files
                if self._valid_document(doc)
            }
            self._batch_review_keys=set()
            self._ocr_perf_docs=0
            self._ocr_perf_seconds=0.0
            self._ocr_perf_tesseract_calls=0
            self._ocr_perf_auto_accepted=0
            self._template_performance={}
            self._oss_stats_recorded=False
            self._record_batch_oss_statistics()
        self._batch_review_reason_by_doc = {}
        self._batch_training_docs = {}
        self._mandatory_training=False; self._training_document=None; self._training_reason=''
        self.is_running=self.batch_busy=True
        self.is_paused=self.stop_flag=False
        self.start_time=time.time()
        self._controls(); self.save_progress(); self.load_file()

    def _batch_oss_counts(self):
        counts = {}
        for document in list(self._batch_original_files or self.pdf_files):
            if not self._valid_document(document):
                continue
            oss = str(document[0])
            counts[oss] = counts.get(oss, 0) + 1
        return counts

    def _record_batch_oss_statistics(self):
        if getattr(self, '_oss_stats_recorded', False):
            return
        counts = self._batch_oss_counts()
        if counts:
            stats.record_oss_batch(counts)
            self._oss_stats_recorded = True
            self._last_batch_oss_counts = dict(counts)
            try:
                top = self.parent.winfo_toplevel()
                if hasattr(top, 'update_stats_display'):
                    top.after_idle(top.update_stats_display)
            except Exception:
                logger.debug('Не удалось обновить статистику ОСС', exc_info=True)

    def _open_reference_library(self):
        directory = os.path.join(SCRIPT_DIR, 'ocr_reference_library')
        if not os.path.isfile(os.path.join(directory, 'sources.json')):
            messagebox.showinfo('Библиотека образцов', 'Папка ocr_reference_library с каталогом sources.json не найдена рядом с программой.')
            return
        messagebox.showinfo(
            'Библиотека интернет-образцов',
            'Это пустые публичные формы, а не проверенные OCR-шаблоны.\n'
            'sources.json содержит ссылки, контрольные суммы и предварительные зоны полей.\n'
            'Автоприменение выключено: сначала нужна проверка на заполненных сканах.\n'
            'Ваши обученные шаблоны не изменены.')
        try:
            os.startfile(directory)
        except OSError as exc:
            messagebox.showerror('Библиотека образцов', str(exc))

    def _consume_result(self):
        result=self._pending_result
        if not result or self.is_paused or self.stop_flag: return
        self._pending_result=None

        if result.get('ocr_error'):
            self.is_paused = True
            self.batch_busy = False
            self._enqueue_review(result.get('reason') or str(result['ocr_error']))
            self.status_panel.config(text='Ошибка OCR — пакет на паузе', fg=Theme.colors['error'])
            self.log_label.config(text=str(result['ocr_error']))
            self._controls()
            self.save_progress()
            return

        if self._auto_recheck_phase:
            if self._recheck_result_verified(result):
                self._save_result(self.recognized_fios,self.recognized_kv)
            else:
                reason=result.get('reason','Нужна ручная проверка после AUTO RECHECK')
                self._enqueue_review(reason)
                self._advance('review')
            return

        document = (tuple(self.pdf_files[self.current_index])
                    if self.current_index < len(self.pdf_files) else None)
        if document is not None and self._requires_template_training(result):
            self._pause_for_template_training(result, document)
            return

        if self._recheck_only or not result.get('accepted'):
            reason = ('Готово к подтверждению' if result.get('accepted')
                      else result.get('reason', 'Нужна проверка'))
            self._enqueue_review(reason)
            self._advance('review')
        else:
            self._save_result(self.recognized_fios,self.recognized_kv)

    def _save_result(self,fios,room):
        if self.saving_busy:return
        document=tuple(self.pdf_files[self.current_index])
        if (document != self._displayed_document or self._displayed_fingerprint !=
                self._fingerprint(os.path.join(SOURCE_FOLDER_PATH,*document))):
            self.stop_process()
            self.log_label.config(text='PDF изменился после распознавания. Откройте его заново перед сохранением.')
            messagebox.showwarning(
                'Документ изменился',
                'PDF изменился после распознавания. Откройте документ из списка проверки заново.')
            return
        self.saving_busy=True; self._controls()
        self.log_label.config(text='Сохраняю проверенную копию PDF…')
        def save():
            try: value=self._finalize_current_file(fios,room,require_confidence=False)
            except Exception as exc: value=(False,'Ошибка сохранения: '+str(exc))
            self._ui_call(self._saved_result,*value)
        threading.Thread(target=save,daemon=False).start()

    def _saved_result(self,ok,message):
        self.saving_busy=False
        original=os.path.join(SOURCE_FOLDER_PATH,*self.pdf_files[self.current_index])
        if ok:
            if self._auto_recheck_phase:
                self._recheck_saved_count += 1
                try:
                    self._batch_review_keys.discard(self._key(self.pdf_files[self.current_index]))
                except Exception:
                    pass
            if self.mode == 'entry': self._commit_manual_timer()
            count=self.last_created_count
            self.total_created+=count; self.total_votes+=count
            daily_stats.add_ocr(count)
            self.daily_ocr_label.config(text=f'OCR: {daily_stats.get_ocr()}')
            try:
                top=self.parent.winfo_toplevel()
                if hasattr(top,'update_daily_display'):
                    top.update_daily_display()
            except Exception:
                logger.debug('Не удалось обновить счётчики шапки', exc_info=True)
        if ok or not os.path.exists(original):
            self._resolve_review()
            if self.review_mode and self.mode == 'entry':
                self._batch_review_keys.discard(self._key(self.pdf_files[self.current_index]))
            self._drafts.pop(self._key(self.pdf_files[self.current_index]),None)
            self._advance('done' if ok else 'duplicate')
        else:
            self._enqueue_review(message)
            self.log_label.config(text=message)
            if self.mode == 'entry': self._start_manual_timer(tuple(self.pdf_files[self.current_index]))
            if self.is_running and not self.is_paused: self._advance('review')
            else: self._controls(); self.save_progress()

    def _advance(self,status):
        if self.mode == 'entry' and self._manual_timer_document is not None:
            self._commit_manual_timer()
        self._statuses[self._key(self.pdf_files[self.current_index])]=status
        self._displayed_document=None
        self.current_index+=1
        self.save_progress(); self._refresh_review(); self._controls()
        if self.is_running:
            if self.current_index>=len(self.pdf_files): self._finish_batch_ui()
            elif not self.is_paused and not self.stop_flag: self.parent.after(50,self.load_file)
        elif not self.stop_flag:
            if self.current_index<len(self.pdf_files): self.parent.after(50,self.load_file)
            elif self.mode=='entry':
                self._finish_batch_ui()
            else: self.open_review_queue()

    def _finish_batch_ui(self):
        if not self._auto_recheck_phase:
            original_keys=set(self._batch_original_keys or {
                self._key(doc) for doc in self.pdf_files if self._valid_document(doc)
            })
            self._first_pass_done_count=sum(
                1 for key in original_keys if self._statuses.get(key)=='done'
            )
            self._manual_remaining_count=len(self._batch_review_keys)

            if (self.mode != 'entry' and self.auto_recheck_enabled and self._batch_review_keys and
                    not self.stop_flag and not self._auto_recheck_started):
                self.is_running=self.batch_busy=False
                self.is_paused=False
                self._controls()
                if self._start_auto_recheck():
                    return

        if self._auto_recheck_phase:
            self._auto_recheck_phase=False
            self._manual_remaining_count=len(self._batch_review_keys)
            if self._batch_original_files:
                self.pdf_files=list(self._batch_original_files)
                self.current_index=len(self.pdf_files)
            self.review_mode=False

        self.is_running=self.batch_busy=self.is_paused=False
        self._mandatory_training=False; self._training_document=None; self._training_reason=''
        self._recheck_only=False
        self._record_batch_oss_statistics()
        self._controls(); self.save_progress(); self._write_batch_report()
        report=self._last_batch_report[0] if self._last_batch_report else {}
        duplicates=report.get('duplicates',0)
        self._displayed_document=None; self._pending_result=None
        self.active_layout_template=None
        self.detected_fio_roi=self.detected_kv_roi=None
        self.fio_roi=self.kv_roi=None
        self.image=self.tk_image=None
        self.canvas.itemconfig(self.canvas_image,image=''); self.canvas.delete('annotation')
        for entry in self.fio_entries+[self.kv_entry]:
            entry.config(state=tk.NORMAL); entry.delete(0,tk.END)
        if hasattr(self,'toggle_extra_fios'):
            self.toggle_extra_fios(force=False)
        self.info.config(text='Партия завершена • нажмите «Результаты» для подробностей')
        self.quality_badge.config(text='ПАРТИЯ ГОТОВА',bg=Theme.colors['success'])
        self.engine_label.config(text='')
        summary=(f'Сразу принято: {self._first_pass_done_count}  •  '
                 f'Recheck спас: {self._recheck_saved_count}  •  '
                 f'Вручную: {self._manual_remaining_count}  •  Дубли: {duplicates}')
        self.status_panel.config(text='Готов',fg=Theme.colors['success'])
        self.log_label.config(text=summary)
        self._auto_recheck_started=False
        self._recheck_source_queue=[]
        self._refresh_modern_dashboard()

    def _write_batch_report(self):
        batch_files=list(self._batch_original_files or self.pdf_files)
        keys={self._key(doc) for doc in batch_files if self._valid_document(doc)}
        counts={name:sum(1 for key in keys if self._statuses.get(key)==name)
                for name in ('done','review','duplicate')}
        elapsed=max(0,int(time.time()-getattr(self,'start_time',time.time())))
        reason_counts={}
        for key,category in self._batch_review_reason_by_doc.items():
            if not keys or key in keys:
                reason_counts[category]=reason_counts.get(category,0)+1

        perf_docs=int(getattr(self,'_ocr_perf_docs',0) or 0)
        perf_seconds=float(getattr(self,'_ocr_perf_seconds',0.0) or 0.0)
        perf_avg=(perf_seconds/perf_docs) if perf_docs else 0.0

        report={
            'created_at':datetime.now().isoformat(),
            'documents':len(batch_files),
            'processed':len(batch_files),
            'oss_counts':dict(sorted(self._batch_oss_counts().items(), key=lambda item: int(str(item[0])))),
            'saved_documents':counts['done'],
            'ready_files_created':int(getattr(self,'total_created',0) or 0),
            'review':len(self._batch_review_keys),
            'duplicates':counts['duplicate'],
            'elapsed_seconds':elapsed,
            'review_reasons':dict(sorted(reason_counts.items(), key=lambda item:(-item[1],item[0]))),
            'template_performance': dict(getattr(self, '_template_performance', {}) or {}),
            'training_required':len(self._batch_training_docs),
            'first_pass_saved':int(self._first_pass_done_count or 0),
            'recheck_saved':int(self._recheck_saved_count or 0),
            'manual_remaining':int(len(self._batch_review_keys)),
            'manual_input_seconds':round(self._manual_timer_value(),1),
            'manual_input_documents':self.manual_input_documents,
            'manual_avg_seconds':round(self._manual_timer_value()/self.manual_input_documents,1)
                                if self.manual_input_documents else 0,
            'ocr_measured_documents':perf_docs,
            'ocr_average_seconds':round(perf_avg,2),
            'ocr_documents_per_minute':round(60.0/perf_avg,2) if perf_avg else 0,
            'ocr_average_tesseract_calls':round(
                float(getattr(self,'_ocr_perf_tesseract_calls',0) or 0)/perf_docs,2)
                if perf_docs else 0,
            'stopped':bool(self.stop_flag),
            'mode':self.mode
        }

        directory=os.path.join(SCRIPT_DIR,'reports'); os.makedirs(directory,exist_ok=True)
        stem='batch_'+datetime.now().strftime('%Y%m%d_%H%M%S')
        path=os.path.join(directory,stem+'.json')
        if atomic_json_save(path,report):
            text_path=os.path.join(directory,stem+'.txt')
            with open(text_path,'w',encoding='utf-8') as stream:
                stream.write(
                    'РЕЗУЛЬТАТЫ ПАРТИИ\n\n'
                    f"Документов: {report['documents']}\n"
                    f"Пройдено: {report['processed']}\n"
                    f"Сразу принято: {report['first_pass_saved']}\n"
                    f"Спасено AUTO RECHECK: {report['recheck_saved']}\n"
                    f"Осталось вручную: {report['manual_remaining']}\n"
                    f"Надёжно сохранено всего: {report['saved_documents']}\n"
                    f"Создано файлов ready: {report['ready_files_created']}\n"
                    + ("ОСС и файлов в партии:\n" + ''.join(
                        f"  - {oss}: {amount}\n"
                        for oss, amount in report.get('oss_counts', {}).items())
                       if report.get('oss_counts') else '')
                    + f"Дубли: {report['duplicates']}\n"
                    f"Новых типов бланков: {report['training_required']}\n"
                    f"Среднее OCR на документ: {report['ocr_average_seconds']:.1f} с\n"
                    f"Скорость OCR: {report['ocr_documents_per_minute']:.2f} док/мин\n"
                    f"Среднее число OCR-вызовов: {report['ocr_average_tesseract_calls']:.1f}\n"
                    + (("Причины проверки:\n" + ''.join(
                        f"  - {name}: {count}\n"
                        for name,count in report.get('review_reasons',{}).items()))
                       if report.get('review_reasons') else '')
                    + f"Время: {elapsed//3600:02d}:{elapsed%3600//60:02d}:{elapsed%60:02d}\n"
                )
            self._last_batch_report=(report,text_path)

    def _current_batch_report(self):
        try:
            current_files=list(self.pdf_files)
        except Exception:
            current_files=[]
        batch_files=list(self._batch_original_files or current_files)
        batch_keys={self._key(doc) for doc in batch_files if self._valid_document(doc)}
        try:
            statuses_snapshot=dict(self._statuses)
        except Exception:
            statuses_snapshot={}
        try:
            reasons_snapshot=dict(self._batch_review_reason_by_doc)
        except Exception:
            reasons_snapshot={}
        try:
            training_snapshot=dict(self._batch_training_docs)
        except Exception:
            training_snapshot={}

        counts={name:sum(1 for key in batch_keys if statuses_snapshot.get(key)==name)
                for name in ('done','review','duplicate')}
        reason_counts={}
        for key,category in reasons_snapshot.items():
            if not batch_keys or key in batch_keys:
                reason_counts[category]=reason_counts.get(category,0)+1

        started=getattr(self,'start_time',None)
        elapsed=max(0,int(time.time()-started)) if isinstance(started,(int,float)) and started else 0
        if self._auto_recheck_phase:
            processed=len(batch_files)
            recheck_processed=min(int(self.current_index or 0),len(current_files))
        else:
            processed=min(int(self.current_index or 0),len(batch_files))
            recheck_processed=0

        manual_docs=int(getattr(self,'manual_input_documents',0) or 0)
        manual_seconds=round(self._manual_timer_value(),1)
        perf_docs=int(getattr(self,'_ocr_perf_docs',0) or 0)
        perf_seconds=float(getattr(self,'_ocr_perf_seconds',0.0) or 0.0)
        perf_avg=(perf_seconds/perf_docs) if perf_docs else 0.0
        return {
            'created_at':datetime.now().isoformat(),
            'documents':len(batch_files),
            'processed':processed,
            'saved_documents':counts['done'],
            'ready_files_created':int(getattr(self,'total_created',0) or 0),
            'review':len(self._batch_review_keys) if self._batch_original_files else counts['review'],
            'duplicates':counts['duplicate'],
            'elapsed_seconds':elapsed,
            'review_reasons':dict(sorted(reason_counts.items(), key=lambda item:(-item[1],item[0]))),
            'training_required':len(training_snapshot),
            'first_pass_saved':int(getattr(self,'_first_pass_done_count',0) or 0),
            'recheck_saved':int(getattr(self,'_recheck_saved_count',0) or 0),
            'manual_remaining':int(len(self._batch_review_keys) if self._batch_original_files
                                   else counts['review']),
            'recheck_processed':recheck_processed,
            'recheck_total':len(current_files) if self._auto_recheck_phase else 0,
            'template_performance': dict(getattr(self, '_template_performance', {}) or {}),
            'manual_input_seconds':manual_seconds,
            'manual_input_documents':manual_docs,
            'manual_avg_seconds':round(manual_seconds/manual_docs,1) if manual_docs else 0,
            'ocr_measured_documents':perf_docs,
            'ocr_average_seconds':round(perf_avg,2),
            'ocr_documents_per_minute':round(60.0/perf_avg,2) if perf_avg else 0,
            'ocr_average_tesseract_calls':round(
                float(getattr(self,'_ocr_perf_tesseract_calls',0) or 0)/perf_docs,2)
                if perf_docs else 0,
            'stopped':bool(getattr(self,'stop_flag',False)),
            'mode':getattr(self,'mode','auto')
        }

    def _show_batch_report(self):
        try:
            existing=getattr(self,'_batch_results_window',None)
            if existing is not None:
                try:
                    if existing.winfo_exists():
                        existing.deiconify(); existing.lift(); existing.focus_force()
                        return
                except Exception:
                    self._batch_results_window=None

            if self.is_running or self.batch_busy:
                report=self._current_batch_report()
                report_path='Текущая партия — итоговый файл отчёта будет создан после завершения.'
                live=True
            elif self._last_batch_report:
                report,report_path=self._last_batch_report
                live=False
            elif self.pdf_files:
                report=self._current_batch_report()
                report_path='Текущий сеанс.'
                live=False
            else:
                messagebox.showinfo('Результаты партии','Нет текущей или завершённой партии.')
                return

            window=tk.Toplevel(self.parent)
            self._batch_results_window=window
            window.title('Текущие результаты партии' if live else 'Результаты партии')
            window.geometry('690x590')
            try:
                window.transient(self.parent.winfo_toplevel())
            except Exception:
                pass

            def close_window():
                self._batch_results_window=None
                window.destroy()
            window.protocol('WM_DELETE_WINDOW', close_window)

            title_var=tk.StringVar()
            summary_vars={}
            tk.Label(window,textvariable=title_var,font=('Segoe UI',17,'bold')).pack(pady=(18,10))
            rows_frame=tk.Frame(window); rows_frame.pack(fill=tk.X)
            labels=('Документов','Пройдено','Сразу принято','Спасено AUTO RECHECK',
                    'Осталось вручную','Файлов создано в ready','Дубли',
                    'Новых типов бланков','Среднее OCR','Скорость OCR','Время')
            for label in labels:
                var=tk.StringVar(value=''); summary_vars[label]=var
                tk.Label(rows_frame,textvariable=var,font=('Segoe UI',11)).pack(anchor='w',padx=55,pady=3)

            reasons_frame=tk.Frame(window)
            reasons_frame.pack(fill=tk.BOTH,expand=True,padx=10,pady=(8,0))
            path_var=tk.StringVar(value='')
            tk.Label(window,textvariable=path_var,wraplength=600,justify='left').pack(padx=30,pady=14)

            def refresh():
                try:
                    if not window.winfo_exists(): return
                    if self.is_running or self.batch_busy:
                        current=self._current_batch_report()
                        current_path='Текущая партия — итоговый файл отчёта будет создан после завершения.'
                        is_live=True
                    elif self._last_batch_report:
                        current,current_path=self._last_batch_report
                        is_live=False
                    else:
                        current,current_path,is_live=report,report_path,False

                    elapsed=int(current.get('elapsed_seconds',0) or 0)
                    title_var.set('ТЕКУЩИЕ РЕЗУЛЬТАТЫ ПАРТИИ' if is_live else 'РЕЗУЛЬТАТЫ ПАРТИИ')
                    summary_vars['Документов'].set(f"Документов:  {current.get('documents',0)}")
                    summary_vars['Пройдено'].set(f"Пройдено:  {current.get('processed',0)}")
                    summary_vars['Сразу принято'].set(f"Сразу принято:  {current.get('first_pass_saved',0)}")
                    summary_vars['Спасено AUTO RECHECK'].set(f"Спасено AUTO RECHECK:  {current.get('recheck_saved',0)}")
                    summary_vars['Осталось вручную'].set(f"Осталось вручную:  {current.get('manual_remaining',0)}")
                    summary_vars['Файлов создано в ready'].set(f"Файлов создано в ready:  {current.get('ready_files_created',0)}")
                    summary_vars['Дубли'].set(f"Дубли:  {current.get('duplicates',0)}")
                    summary_vars['Новых типов бланков'].set(f"Новых типов бланков:  {current.get('training_required',0)}")
                    summary_vars['Среднее OCR'].set(
                        f"Среднее OCR:  {float(current.get('ocr_average_seconds',0) or 0):.1f} с/документ")
                    summary_vars['Скорость OCR'].set(
                        f"Скорость OCR:  {float(current.get('ocr_documents_per_minute',0) or 0):.2f} документов/мин")
                    summary_vars['Время'].set(f"Время:  {elapsed//3600:02d}:{elapsed%3600//60:02d}:{elapsed%60:02d}")

                    for child in list(reasons_frame.winfo_children()): child.destroy()
                    tk.Label(reasons_frame,text='Почему документы попали в проверку:',
                             font=('Segoe UI',11,'bold')).pack(anchor='w',padx=45,pady=(4,3))
                    reasons=current.get('review_reasons') or {}
                    if reasons:
                        for name,count in reasons.items():
                            tk.Label(reasons_frame,text=f'• {name}: {count}',font=('Segoe UI',10),
                                     wraplength=560,justify='left').pack(anchor='w',padx=60,pady=1)
                    else:
                        tk.Label(reasons_frame,text='• Пока нет документов в перепроверке',
                                 font=('Segoe UI',10)).pack(anchor='w',padx=60,pady=1)
                    templates=current.get('template_performance') or {}
                    if templates:
                        tk.Label(reasons_frame,text='Результативность шаблонов:',
                                 font=('Segoe UI',11,'bold')).pack(anchor='w',padx=45,pady=(10,3))
                        for name,stats in sorted(templates.items()):
                            attempts=int(stats.get('attempts',0) or 0)
                            accepted=int(stats.get('accepted',0) or 0)
                            review=int(stats.get('review',0) or 0)
                            seconds=float(stats.get('seconds',0.0) or 0.0)
                            rate=(accepted*100.0/attempts) if attempts else 0.0
                            average=(seconds/attempts) if attempts else 0.0
                            tk.Label(reasons_frame,
                                     text=(f'• {name}: {accepted}/{attempts} авто ({rate:.0f}%), '
                                           f'проверка {review}, {average:.1f} с/попытку'),
                                     font=('Segoe UI',10),wraplength=570,justify='left').pack(
                                         anchor='w',padx=60,pady=1)
                    path_var.set('Отчёт: '+current_path)
                    self._theme_window(window)
                    window.lift()
                    if is_live: window.after(2000,refresh)
                except Exception as exc:
                    logger.exception('Ошибка обновления окна результатов партии')
                    try: self.log_label.config(text='Ошибка окна результатов: '+str(exc))
                    except Exception: pass

            refresh()
            window.after(100,lambda:(window.lift(),window.focus_force()))
        except Exception as exc:
            logger.exception('Не удалось открыть результаты партии')
            messagebox.showerror('Результаты партии','Не удалось открыть окно результатов.\n\n'+str(exc))

    def confirm(self):
        if self.ocr_busy:
            messagebox.showinfo('Подтверждение', 'Дождитесь завершения OCR.'); return
        if self.saving_busy:
            messagebox.showinfo('Подтверждение', 'Документ уже сохраняется.'); return
        if self.is_running and not self.is_paused and not getattr(self, '_manual_review_open', False):
            messagebox.showinfo(
                'Подтверждение',
                'Сейчас идёт автоматическая обработка. Поставьте пакет на паузу '
                'или дождитесь перехода к следующему документу.')
            return
        if self.current_index>=len(self.pdf_files):
            messagebox.showwarning('Подтверждение', 'Текущий документ не выбран.'); return
        try:
            fios=[e.get().strip() for e in self.fio_entries if e.get().strip()]
            room=self.kv_entry.get().strip()
            if not fios or not room or room=='0':
                messagebox.showwarning('Проверьте поля','Заполните ФИО и номер помещения перед сохранением.');return
            if getattr(self, '_manual_review_open', False):
                self.is_running=False
                self.batch_busy=False
                self.is_paused=False
            self.log_label.config(text='Подтверждаю и сохраняю документ…')
            self.parent.update_idletasks()
            self._pause_manual_timer(); self._capture_draft(); self.save_progress()
            self._pending_result = None
            self._save_result(fios,room)
        except Exception as exc:
            logger.exception('Ошибка кнопки подтверждения')
            messagebox.showerror('Не удалось подтвердить', str(exc))

    def skip_file(self):
        if self._mandatory_training:
            self._skip_training_without_template()
            return
        if self.ocr_busy or self.saving_busy or self.is_running:return
        if self.current_index>=len(self.pdf_files):return
        self._capture_draft()
        if self.mode == 'entry': self._commit_manual_timer()
        self._enqueue_review('Отложено пользователем')
        self._advance('review')

    def _request_batch_skip_current(self):
        self._request_batch_document_action('skip')

    def _request_batch_exclude_current(self):
        self._request_batch_document_action('exclude')

    def _request_batch_document_action(self, action):
        if self.saving_busy or self._batch_document_action:
            return
        if self.current_index >= len(self.pdf_files):
            messagebox.showinfo('Документ', 'Текущий PDF не выбран.')
            return
        document = tuple(self.pdf_files[self.current_index])
        if not self._valid_document(document):
            messagebox.showerror('Документ', 'Недопустимый путь PDF.')
            return
        if action == 'exclude' and not messagebox.askyesno(
                'Убрать из очереди?',
                f'{document[1]}\n\nPDF будет перемещён в ocr_excluded. '
                'Его можно будет восстановить вручную. Пакет продолжится.'):
            return
        self._batch_document_action = {'action': action, 'document': document}
        self._pending_result = None
        self.is_paused = True
        label = ('Пропускаю текущий PDF…' if action == 'skip'
                 else 'Убираю текущий PDF из очереди…')
        self.status_panel.config(text=label, fg=Theme.colors['warning'])
        self.log_label.config(text=label)
        self._controls()
        if self.ocr_busy:
            self._cancel_job.set()
        else:
            self.parent.after_idle(self._complete_batch_document_action)

    def _complete_batch_document_action(self):
        pending = self._batch_document_action
        if not pending:
            return
        document = tuple(pending['document'])
        if (self.current_index >= len(self.pdf_files) or
                tuple(self.pdf_files[self.current_index]) != document):
            self._batch_document_action = None
            self.is_paused = False
            self._controls()
            return
        action = pending['action']
        source = os.path.realpath(os.path.join(SOURCE_FOLDER_PATH, *document))
        root = os.path.realpath(SOURCE_FOLDER_PATH)
        try:
            if action == 'exclude':
                if os.path.commonpath([root, source]) != root or not os.path.isfile(source):
                    raise FileNotFoundError('Исходный PDF не найден или путь недопустим.')
                archive = os.path.join(SCRIPT_DIR, 'ocr_excluded')
                os.makedirs(archive, exist_ok=True)
                folder = tempfile.mkdtemp(prefix='excluded_batch_', dir=archive)
                destination = os.path.join(folder, document[1])
                records = [r for r in self.review_queue
                           if (r.get('oss'), r.get('filename')) == document]
                if not atomic_json_save(os.path.join(folder, 'restore.json'), {
                        'original_path': source, 'document': list(document),
                        'review_records': records,
                        'excluded_at': datetime.now().isoformat()}):
                    raise IOError('Не удалось сохранить сведения для восстановления.')
                shutil.move(source, destination)
                self.review_queue = [r for r in self.review_queue
                                     if (r.get('oss'), r.get('filename')) != document]
                self._save_review_queue()
            self._drafts.pop(self._key(document), None)
            self._batch_review_keys.discard(self._key(document))
            self._batch_training_docs.pop(self._key(document), None)
            self._mandatory_training = False
            self._training_document = None
            self._training_reason = ''
            self.learning_template_pending = False
            self.total_skipped += 1
            self._batch_document_action = None
            self.is_paused = False
            message = ('PDF убран в ocr_excluded' if action == 'exclude'
                       else 'PDF пропущен в этом пакете')
            self.log_label.config(text=message)
            self.status_panel.config(text='▶ Пакет продолжается', fg=Theme.colors['success'])
            self._advance('excluded' if action == 'exclude' else 'skipped')
        except Exception as exc:
            logger.exception('Не удалось обработать команду для текущего PDF')
            self._batch_document_action = None
            self.is_paused = False
            self._controls()
            messagebox.showerror('Документ не обработан', str(exc))
            if self.is_running and not self.stop_flag:
                self.parent.after(50, self.load_file)

    def toggle_pause(self):
        if not self.is_running:return
        self.is_paused=True
        self._capture_draft(); self.save_progress(); self._controls()
        self.status_panel.config(text='На паузе — сеанс сохранён',fg=Theme.colors['warning'])

    def resume_process(self):
        if not self.is_paused:
            if (self.review_mode and self.mode == 'auto'
                    and not getattr(self, '_manual_review_open', False)
                    and self.current_index < len(self.pdf_files)):
                self._resume_saved_review_batch()
            return
        if self._mandatory_training:
            self.log_label.config(text='Сначала сохраните шаблон текущего неизвестного бланка — пакет не пропустит этот шаг.')
            return
        self.is_paused=False; self._controls(); self.save_progress()
        if self._pending_result:self._consume_result()
        elif not self.ocr_busy and not self.saving_busy:self.load_file()

    def _resume_saved_review_batch(self):
        if (self.ocr_busy or self.saving_busy or self.is_running or
                not self.pdf_files or self.current_index >= len(self.pdf_files)):
            return
        self.review_mode = True
        self.mode = 'auto'
        self._manual_review_open = False
        self._auto_recheck_phase = True
        self._auto_recheck_started = True
        self._recheck_only = False
        self.log_label.config(
            text=f'Продолжаю сохранённую перепроверку с документа '
                 f'{self.current_index + 1} из {len(self.pdf_files)}')
        self._begin_batch()

    def stop_process(self):
        self._capture_draft()
        self.stop_flag=True;self.is_running=False;self.is_paused=False
        self._mandatory_training=False; self._training_document=None; self._training_reason=''
        self._pending_result=None; self._cancel_job.set()
        if not self.ocr_busy and not self.saving_busy:self.batch_busy=False
        self.status_panel.config(text='Останавливаю…' if self.ocr_busy else 'Остановлен — сеанс сохранён',fg=Theme.colors['warning'])
        self.save_progress();self._controls()

    def shutdown(self):
        self._pause_manual_timer();self._capture_draft();self.save_progress()
        self._closing=True;self._cancel_job.set()
        self._stop_persistent_ocr_worker()

    def on_fio_edit(self,idx):
        self._draft_changed()

    def on_kv_edit(self,event):
        self._draft_changed()

    def save_corrections(self):
        atomic_json_save(os.path.join(SCRIPT_DIR,'learning_scoped.json'),self.scoped_learning)

    def _teach_correction(self):
        if self.ocr_busy or self.saving_busy:return
        current=[e.get().strip() for e in self.fio_entries if e.get().strip()]
        raw=getattr(self,'_raw_ocr_fields',[])
        if not self.active_layout_template:
            messagebox.showinfo('Обучение','Сначала сохраните именованный шаблон этого бланка. Исправление будет действовать только для него.');return
        if len(current)!=1 or len(raw)!=1 or current==raw:
            messagebox.showinfo('Обучение','Исправьте одно распознанное ФИО, затем нажмите «Запомнить исправление».');return
        self.scoped_learning.append({'template':self.active_layout_template,'old':raw[0],'new':current[0],
                                     'enabled':True,'timestamp':datetime.now().isoformat()})
        self.save_corrections()
        self.log_label.config(text='Исправление сохранено только для шаблона «'+self.active_layout_template+'».')

    def _learning_window(self):
        window=tk.Toplevel(self.parent);window.title('Обучение — только явные исправления');window.geometry('1000x390')
        tk.Label(window,text='Старые глобальные подстановки не применяются. Новые исправления привязаны к шаблону.').pack(pady=12)
        tree=ttk.Treeview(window,columns=('scope','old','new','state'),show='headings')
        for col,title in [('scope','Шаблон'),('old','Распознано'),('new','Исправлено'),('state','Состояние')]:tree.heading(col,text=title)
        tree.pack(fill=tk.BOTH,expand=True,padx=10)
        def refresh():
            tree.delete(*tree.get_children())
            for i,r in enumerate(self.scoped_learning):tree.insert('',tk.END,iid=str(i),values=(r['template'],r['old'],r['new'],'Включено' if r.get('enabled',True) else 'Отключено'))
        def toggle():
            for item in tree.selection():
                r=self.scoped_learning[int(item)];r['enabled']=not r.get('enabled',True)
            self.save_corrections();refresh()
        make_button(window,'Включить / отключить выбранное',toggle).pack(pady=10)
        make_button(window,'Запомнить текущее исправление ФИО',lambda:(self._teach_correction(),refresh())).pack(pady=(0,10))
        refresh()
        self._theme_window(window)

    def _theme_window(self, window):
        c=Theme.colors
        style=ttk.Style(window)
        style.configure('Studio.Treeview',background=c['entry'],fieldbackground=c['entry'],
                        foreground=c['fg'],rowheight=30,font=('Segoe UI',10),borderwidth=0)
        style.configure('Studio.Treeview.Heading',background=c['btn'],foreground=c['fg'],font=('Segoe UI',10,'bold'))
        style.map('Studio.Treeview',background=[('selected',c['accent'])],foreground=[('selected','white')])
        def apply(widget):
            if isinstance(widget,(tk.Frame,tk.Toplevel)):widget.configure(bg=c['bg'])
            elif isinstance(widget,tk.Label):widget.configure(bg=c['bg'],fg=c['fg'])
            elif isinstance(widget,ttk.Treeview):widget.configure(style='Studio.Treeview')
            for child in widget.winfo_children():apply(child)
        apply(window)

    def _start_manual_review_queue(self):
        if self.ocr_busy or self.saving_busy or self.is_running:
            messagebox.showinfo('Проверка', 'Сначала остановите OCR и дождитесь завершения текущей операции.')
            return
        documents = list(dict.fromkeys(
            (r.get('oss'), r.get('filename')) for r in self.review_queue
            if self._valid_document((r.get('oss'), r.get('filename')))
            and os.path.isfile(os.path.join(SOURCE_FOLDER_PATH, r['oss'], r['filename']))))
        if not documents:
            messagebox.showinfo('Проверка', 'Нет доступных PDF в очереди проверки. Записи с отсутствующими источниками сохранены.')
            return
        self._capture_draft()
        self.pdf_files = documents
        self.current_index = 0
        self.review_mode = True
        self._manual_review_open = True
        self._auto_recheck_phase = False
        self._recheck_only = False
        self._pending_result = None
        self._mandatory_training = False
        self.is_running = self.batch_busy = self.is_paused = self.stop_flag = False
        self._displayed_document = None
        self.set_mode('entry')
        if self._queue_window is not None and self._queue_window.winfo_exists():
            self._queue_window.withdraw()
        self.save_progress()
        self.load_file()

    def _exclude_current_review(self):
        if (self.ocr_busy or self.saving_busy or self.is_running or not self.review_mode
                or self.mode != 'entry' or self.current_index >= len(self.pdf_files)):
            messagebox.showinfo('Удаление', 'Откройте документ кнопкой «Проверка» и дождитесь загрузки.')
            return
        document = tuple(self.pdf_files[self.current_index])
        if not self._valid_document(document) or document != self._displayed_document:
            return
        source = os.path.realpath(os.path.join(SOURCE_FOLDER_PATH, *document))
        root = os.path.realpath(SOURCE_FOLDER_PATH)
        if os.path.commonpath([root, source]) != root or not os.path.isfile(source):
            messagebox.showerror('Удаление', 'Исходный PDF не найден или путь недопустим.')
            return
        if not messagebox.askyesno('Удалить из проверки?',
                f'{document[1]}\n\nPDF будет перенесён в ocr_excluded рядом с программой. '
                'Его можно восстановить вручную. Файлы ready и внесённые документы не затрагиваются. Продолжить?'):
            return
        old_queue = list(self.review_queue)
        destination = None
        try:
            archive = os.path.join(SCRIPT_DIR, 'ocr_excluded')
            os.makedirs(archive, exist_ok=True)
            folder = tempfile.mkdtemp(prefix='excluded_', dir=archive)
            destination = os.path.join(folder, document[1])
            if not atomic_json_save(os.path.join(folder, 'restore.json'), {
                    'original_path': source, 'document': list(document),
                    'review_records': [r for r in old_queue if (r.get('oss'), r.get('filename')) == document],
                    'excluded_at': datetime.now().isoformat()}):
                raise IOError('Не удалось сохранить сведения для восстановления')
            shutil.move(source, destination)
            self._resolve_review()
        except Exception as exc:
            self.review_queue = old_queue
            if destination and os.path.isfile(destination) and not os.path.exists(source):
                try:
                    shutil.move(destination, source)
                except OSError:
                    logger.exception('PDF остался в архиве исключённых: %s', destination)
            messagebox.showerror('Удаление не завершено', str(exc))
            return
        self._pending_result = None
        self._drafts.pop(self._key(document), None)
        self._batch_review_keys.discard(self._key(document))
        self._advance('excluded')

    def open_review_queue(self):
        if self.ocr_busy or self.saving_busy or self.is_running:
            self.log_label.config(text='Сначала остановите пакет; затем откройте очередь проверки.');return
        self._capture_draft()
        if self._queue_window is not None and self._queue_window.winfo_exists():
            self._refresh_review();self._queue_window.deiconify();self._queue_window.lift();return
        window=self._queue_window=tk.Toplevel(self.parent)
        window.title('OCR Studio — очередь проверки');window.geometry('1180x510')
        top=tk.Frame(window);top.pack(fill=tk.X,padx=12,pady=10)
        tk.Label(top,text='Найти документ:').pack(side=tk.LEFT)
        self._review_search=tk.StringVar()
        ttk.Entry(top,textvariable=self._review_search,width=35).pack(side=tk.LEFT,padx=8)
        self._review_reason=tk.StringVar(value='Все причины')
        self._reason_box=ttk.Combobox(top,textvariable=self._review_reason,state='readonly',width=48)
        self._reason_box.pack(side=tk.LEFT,padx=8)
        tree=self._review_tree=ttk.Treeview(window,columns=('oss','file','fio','room','reason'),show='headings',selectmode='browse')
        for col,title,width in [('oss','ОСС',80),('file','Документ',300),('fio','ФИО',230),('room','Помещение',80),('reason','Причина',360)]:
            tree.heading(col,text=title);tree.column(col,width=width,minwidth=60)
        scroll=ttk.Scrollbar(window,orient=tk.VERTICAL,command=tree.yview);tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT,fill=tk.Y);tree.pack(fill=tk.BOTH,expand=True,padx=12)
        bar=tk.Frame(window);bar.pack(fill=tk.X,padx=12,pady=10)
        make_button(bar,'Открыть выбранный',self._open_review_selected).pack(side=tk.LEFT,padx=4)
        make_button(bar,'Вручную без OCR',self._start_manual_review_queue).pack(side=tk.LEFT,padx=4)
        make_button(bar,'Перепроверить и сохранить надёжные',self._recheck_queue,
                    bg=Theme.colors['success'],fg='white').pack(side=tk.LEFT,padx=4)
        make_button(bar,'Закрыть список',window.destroy).pack(side=tk.RIGHT,padx=4)
        self._review_summary=tk.Label(bar,text='');self._review_summary.pack(side=tk.LEFT,padx=12)
        tree.bind('<Double-1>',lambda e:self._open_review_selected())
        self._review_search.trace_add('write',lambda *a:self._refresh_review())
        self._reason_box.bind('<<ComboboxSelected>>',lambda e:self._refresh_review())
        self._refresh_review()
        self._theme_window(window)

    def _refresh_review(self):
        if self._queue_window is None or not self._queue_window.winfo_exists():return
        tree=self._review_tree;tree.delete(*tree.get_children())
        query=self._review_search.get().casefold();reason=self._review_reason.get()
        self._reason_box['values']=['Все причины']+sorted({str(r.get('reason','')) for r in self.review_queue})
        count=0
        for i,r in enumerate(self.review_queue):
            if query and query not in (str(r.get('filename',''))+' '+' '.join(r.get('fios',[]))).casefold():continue
            if reason!='Все причины' and reason!=r.get('reason'):continue
            document=(r.get('oss'),r.get('filename'))
            available=self._valid_document(document) and os.path.isfile(os.path.join(SOURCE_FOLDER_PATH,*document))
            tree.insert('',tk.END,iid=str(i),values=(r.get('oss'),r.get('filename'),' / '.join(r.get('fios',[])),r.get('room') or '',r.get('reason') if available else 'Источник отсутствует — запись сохранена'))
            count+=1
        self._review_summary.config(text=f'Показано {count} из {len(self.review_queue)}')

    def _open_review_selected(self):
        if self.ocr_busy or self.saving_busy or self.is_running:return
        selected=self._review_tree.selection()
        if not selected:return
        r=self.review_queue[int(selected[0])];document=(r['oss'],r['filename'])
        if not self._valid_document(document) or not os.path.isfile(os.path.join(SOURCE_FOLDER_PATH,*document)):
            messagebox.showwarning('Источник отсутствует','Исходный PDF не найден. Запись очереди не удалена.');return
        self._capture_draft();self.review_mode=True;self.stop_flag=False
        self._manual_review_open=True
        self.is_running=False;self.batch_busy=False;self.is_paused=False
        self.pdf_files=[document]+[(x['oss'],x['filename']) for x in self.review_queue if (x['oss'],x['filename'])!=document and self._valid_document((x['oss'],x['filename'])) and os.path.isfile(os.path.join(SOURCE_FOLDER_PATH,x['oss'],x['filename']))]
        self.current_index=0
        self._queue_window.withdraw()
        self.load_file();self._show_preview()

    def _recheck_queue(self):
        if self.ocr_busy or self.saving_busy or self.is_running:return
        if not messagebox.askyesno('Повторная проверка очереди',
                'Программа заново распознает документы. Надёжные результаты будут сохранены автоматически, остальные останутся в очереди. Продолжить?'):return
        self.pdf_files=[(r['oss'],r['filename']) for r in self.review_queue if self._valid_document((r['oss'],r['filename'])) and os.path.isfile(os.path.join(SOURCE_FOLDER_PATH,r['oss'],r['filename']))]
        if not self.pdf_files:return
        self._capture_draft();self.current_index=0;self.review_mode=True;self.mode='auto';self._recheck_only=False
        self._manual_review_open=False
        self._queue_window.withdraw();self._begin_batch()

    def _open_tools_menu(self):
        self._open_tools_panel()

    def _open_tools_panel(self):
        """Open a regular tool window; unlike tk_popup it is reliable on Windows."""
        if self._tools_window is not None and self._tools_window.winfo_exists():
            self._tools_window.deiconify()
            self._tools_window.lift()
            self._tools_window.focus_force()
            return
        c = Theme.colors
        owner = self.parent.winfo_toplevel()
        win = self._tools_window = tk.Toplevel(owner)
        win.title('Инструменты OCR Studio')
        win.geometry('560x420')
        win.minsize(500, 360)
        win.configure(bg=c['bg'])
        win.transient(owner)

        def close_panel():
            try: win.destroy()
            finally: self._tools_window = None

        win.protocol('WM_DELETE_WINDOW', close_panel)
        header = tk.Frame(win, bg=c['card_bg'], height=64,
                          highlightthickness=1, highlightbackground=c['border'])
        header.pack(fill=tk.X, padx=12, pady=(12, 8))
        header.pack_propagate(False)
        tk.Label(header, text='Инструменты', bg=c['card_bg'], fg=c['fg'],
                 font=('Segoe UI Semibold', 17)).pack(side=tk.LEFT, padx=18)

        body = tk.Frame(win, bg=c['bg'])
        body.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)
        for column in range(2):
            body.grid_columnconfigure(column, weight=1, uniform='tools')
        actions = (
            ('Внесение', self.open_robot_helper_tab),
            ('Фрагменты документа', self._show_preview),
            ('Вся страница', self.fit_page),
            ('По ширине', self.fit_width),
            ('OCR-исправления', self._learning_window),
            ('Интернет-образцы', self._open_reference_library),
            ('Аудит копий', self._audit_copies),
            ('Удалить дубли шаблонов', self._template_duplicates_dialog),
        )
        for index, (label, callback) in enumerate(actions):
            button = make_button(body, label, callback, bg=c['btn'], fg=c['fg'],
                                 anchor='w', padx=16, pady=12)
            button.grid(row=index // 2, column=index % 2,
                        sticky='nsew', padx=5, pady=5)
        make_button(win, 'Закрыть', close_panel, bg=c['accent'], fg='white',
                    width=14, pady=7).pack(side=tk.BOTTOM, pady=(4, 14))
        win.update_idletasks()
        x = owner.winfo_rootx() + max(20, (owner.winfo_width() - win.winfo_width()) // 2)
        y = owner.winfo_rooty() + max(40, (owner.winfo_height() - win.winfo_height()) // 3)
        win.geometry(f'+{x}+{y}')
        win.lift()
        win.focus_force()

    def _show_preview(self):
        if self._preview_window is None or not self._preview_window.winfo_exists():
            win=self._preview_window=tk.Toplevel(self.parent);win.title('Фрагменты исходного бланка');win.geometry('930x440')
            tk.Label(win,text='Сверяйте поля с оригиналом — увеличенные фрагменты',font=('Segoe UI',14,'bold')).pack(pady=10)
            self._fio_preview=tk.Label(win,text='ФИО: область ещё не определена');self._fio_preview.pack(fill=tk.BOTH,expand=True,padx=12,pady=8)
            self._room_preview=tk.Label(win,text='Помещение: область ещё не определена');self._room_preview.pack(fill=tk.BOTH,expand=True,padx=12,pady=8)
            self._theme_window(win)
        self._preview_window.deiconify();self._preview_window.lift();self._refresh_preview()

    def _refresh_preview(self):
        if self._preview_window is None or not self._preview_window.winfo_exists():return
        self._preview_images=[]
        for widget,roi,title in [(self._fio_preview,self.detected_fio_roi or self.fio_roi,'ФИО'),(self._room_preview,self.detected_kv_roi or self.kv_roi,'Помещение')]:
            if self.image is None or not roi:
                widget.config(image='',text=title+': область не определена — проверьте страницу');continue
            padded=self.get_roi_with_padding(roi,*self.image.size,pad_pct=8)
            crop=self.image.crop(padded)
            scale=min(880/max(1,crop.width),155/max(1,crop.height),3.)
            crop=crop.resize((max(1,int(crop.width*scale)),max(1,int(crop.height*scale))),Image.Resampling.LANCZOS)
            photo=ImageTk.PhotoImage(crop,master=self.parent)
            self._preview_images.append(photo);widget.config(image=photo,text=title,compound=tk.TOP)

    def _audit_copies(self):
        self.log_label.config(text='Проверяю совпадающие PDF в ready. Файлы не будут изменены.')
        def audit():
            import csv
            groups={}
            try:
                for folder,_,files in os.walk(READY_FOLDER_PATH):
                    for name in files:
                        if not name.lower().endswith('.pdf'):continue
                        path=os.path.join(folder,name);digest=hashlib.sha256()
                        with open(path,'rb') as f:
                            for chunk in iter(lambda:f.read(1024*1024),b''):digest.update(chunk)
                        groups.setdefault((folder,digest.hexdigest()),[]).append(name)
                directory=os.path.join(SCRIPT_DIR,'reports');os.makedirs(directory,exist_ok=True)
                report=os.path.join(directory,'copies_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.csv')
                matches=[(k,v) for k,v in groups.items() if len(v)>1]
                with open(report,'w',encoding='utf-8-sig',newline='') as f:
                    writer=csv.writer(f,delimiter=';');writer.writerow(['Папка','Совпадающие файлы','Примечание'])
                    for (folder,_),names in matches:writer.writerow([folder,' | '.join(names),'Проверить: возможны законные совладельцы. Ничего не удалено.'])
                self._ui_call(self.log_label.config,text=f'Аудит: {len(matches)} групп. Отчёт: {report}')
            except Exception as exc:self._ui_call(self.log_label.config,text='Ошибка аудита: '+str(exc))
        threading.Thread(target=audit,daemon=True).start()

    def show_controls_help(self):
        messagebox.showinfo('OCR Studio',
            'АВТО + Обработать всё: знакомые шаблоны идут без остановки; слабое ФИО дополнительно проверяется 3 короткими OCR только внутри обученной ROI и принимается при согласии минимум 2 из 3.\n'
            'Неизвестный бланк ставит пакет на паузу до обучения ROI. Для рукописи нажмите '
            '«ПРОПУСТИТЬ БЕЗ ОБУЧЕНИЯ» — документ останется в ручной проверке.\n'
            'После сохранения шаблона тот же PDF распознаётся заново, затем пакет продолжается автоматически.\n\n'
            'Рукописные — без OCR: выберите пакет, введите ФИО и помещение, нажмите Подтвердить.\n'
            'После сохранения автоматически откроется следующий бланк. Ctrl+Enter — подтвердить.\n\n'
            'Пауза: текущий OCR может завершиться, но сохранение ждёт Продолжить.\n'
            'Стоп: отменяет текущий OCR, исходный PDF остаётся на месте.\n'
            'Сеанс и ручные правки сохраняются; при запуске доступно продолжение.\n\n'
            'После первого прохода при включённом «Максимум авто» программа сама запускает пакетный AUTO RECHECK.\n'
            'Проверка: список с фильтрами. «Перепроверить и сохранить надёжные» автоматически\n'
            'сохранит только результаты, прошедшие все проверки; остальные останутся в очереди.\n'
            'Фрагменты: увеличенные ФИО и номер.\n'
            'Обучение: только явные исправления внутри именованного шаблона.\n'
            'Аудит копий: отчёт без удаления файлов.\n'
            'Анализ дублей шаблонов: удаляются только точные совпадения, с резервной копией и вашим подтверждением.')

class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.settings = AppSettings()
        self.theme = Theme()
        Theme.set(self.settings.get("theme", "dark"))
        self.title("OCR Studio v43.17.73 LOWERCASE FIO FIX — пакетная обработка")
        self.geometry("1380x820")
        self.config(bg=Theme.colors['bg'])
        self.minsize(1120, 700)

        main = tk.Frame(self, bg=Theme.colors['bg'])
        main.pack(fill=tk.BOTH, expand=True)

        header = tk.Frame(main, bg=Theme.colors['card_bg'], height=72,
                          highlightthickness=1, highlightbackground=Theme.colors['border'])
        header.pack(fill=tk.X, padx=12, pady=(12, 0))
        header.pack_propagate(False)

        brand = tk.Frame(header, bg=Theme.colors['card_bg'])
        brand.pack(side=tk.LEFT, padx=(18,22), pady=10)
        tk.Label(brand, text='OCR  STUDIO', bg=Theme.colors['card_bg'],
                 fg=Theme.colors['fg'], font=('Segoe UI Semibold',16)).pack(anchor='w')
        tk.Label(brand, text='v43.17.73 LOWERCASE FIO FIX  •  VERIFIED OCR  •  SAFE AUTOMATION',
                 bg=Theme.colors['card_bg'], fg=Theme.colors['accent'],
                 font=('Segoe UI',8,'bold')).pack(anchor='w', pady=(2,0))

        tk.Label(header,text='BETA',bg=Theme.colors['accent'],fg='white',
                 font=('Segoe UI',8,'bold'),padx=8,pady=3).pack(
                     side=tk.LEFT,padx=(0,18))

        daily_frame = tk.Frame(header, bg=Theme.colors['btn'],
                               highlightthickness=1, highlightbackground=Theme.colors['border'])
        daily_frame.pack(side=tk.LEFT, padx=6, pady=14)
        self.daily_ocr = tk.Label(
            daily_frame, text=f'OCR сегодня  {daily_stats.get_ocr()}',
            bg=Theme.colors['btn'], fg=Theme.colors['accent'],
            font=('Segoe UI',9,'bold'))
        self.daily_ocr.pack(side=tk.LEFT, padx=10)
        self.daily_input = tk.Label(
            daily_frame, text=f'Ввод сегодня  {daily_stats.get_input()}',
            bg=Theme.colors['btn'], fg=Theme.colors['success'],
            font=('Segoe UI',9,'bold'))
        self.daily_input.pack(side=tk.LEFT, padx=10)

        self.theme_button = tk.Button(
            header,
            text='☀ Светлая' if Theme.current_theme == 'dark' else '🌙 Тёмная',
            command=self.toggle_theme,
            bg=Theme.colors['btn'], fg=Theme.colors['fg'],
            activebackground=Theme.colors['hover'],
            activeforeground=Theme.colors['fg'],
            font=('Segoe UI',9,'bold'), relief=tk.FLAT,
            padx=12, pady=7, cursor='hand2')
        self.theme_button.pack(side=tk.RIGHT,padx=(4,12),pady=10)
        tk.Button(header, text='Excel', command=self.export_excel,
                  bg=Theme.colors['success'], fg='#ffffff',
                  activebackground=Theme.colors['accent'], activeforeground='#ffffff',
                  font=('Segoe UI',9,'bold'), relief=tk.FLAT,
                  padx=14, pady=7, cursor='hand2').pack(side=tk.RIGHT,padx=4,pady=10)

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TNotebook", background=Theme.colors['bg'], borderwidth=0)
        style.configure("TNotebook.Tab", background=Theme.colors['btn'], foreground=Theme.colors['fg'],
                        padding=(16, 9), font=("Segoe UI", 9, "bold"), borderwidth=0)
        style.map("TNotebook.Tab", background=[("selected", Theme.colors['card_bg'])],
                  foreground=[("selected", Theme.colors['accent'])])

        style.configure('App.TNotebook', background=Theme.colors['bg'], borderwidth=0)
        style.layout('App.TNotebook.Tab', [])
        nav_shell=tk.Frame(main, bg=Theme.colors['card_bg'],
                           highlightthickness=1,
                           highlightbackground=Theme.colors['border'])
        nav_shell.pack(fill=tk.X, padx=12, pady=(10,0))
        nav_left=tk.Frame(nav_shell, bg=Theme.colors['card_bg'])
        nav_left.pack(side=tk.LEFT, padx=8, pady=7)
        self.nav_buttons=[]
        for index, (icon, label) in enumerate((
                ('◉','Распознавание'), ('⇧','Внесение'),
                ('▥','Аналитика'))):
            button=tk.Button(
                nav_left, text=f'{icon}  {label}',
                command=lambda page=index:self._select_app_page(page),
                bg=Theme.colors['card_bg'], fg=Theme.colors['fg'],
                activebackground=Theme.colors['hover'],
                activeforeground=Theme.colors['fg'],
                font=('Segoe UI Semibold',10), relief=tk.FLAT, bd=0,
                padx=18, pady=9, cursor='hand2')
            button.pack(side=tk.LEFT, padx=2)
            self.nav_buttons.append(button)
        self.nav_session=tk.Label(
            nav_shell, text='●  Автосохранение включено',
            bg=Theme.colors['card_bg'], fg=Theme.colors['success'],
            font=('Segoe UI',9))
        self.nav_session.pack(side=tk.RIGHT, padx=18)

        self.notebook = ttk.Notebook(main, style='App.TNotebook')
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=(8,8))

        self.tab_ocr = tk.Frame(self.notebook, bg=Theme.colors['bg'])
        self.notebook.add(self.tab_ocr, text="  OCR  ")
        self.ocr_robot = OCRStudio(self.tab_ocr)

        self.tab_robot = tk.Frame(self.notebook, bg=Theme.colors['bg'])
        self.notebook.add(self.tab_robot, text="  Внесение  ")
        self.robot_helper = RobotHelper(self.tab_robot)

        self.tab_stats = tk.Frame(self.notebook, bg=Theme.colors['bg'])
        self.notebook.add(self.tab_stats, text="  Аналитика  ")
        self.create_stats_tab()

        self.tab_dev = tk.Frame(self.notebook, bg=Theme.colors['bg'])
        self.notebook.add(self.tab_dev, text="  Разработчик  ")
        self.dev_tab_access = False
        self._dev_auth_busy = False
        self._dev_ui_built = False
        self._dev_return_tab = str(self.tab_ocr)
        self.notebook.bind('<<NotebookTabChanged>>', self._on_notebook_tab_changed, add='+')
        self.after_idle(self._refresh_nav_state)

        self.create_status_bar()
        self._configure_modern_styles()
        self.after(60, self._apply_modern_widget_finish)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(120, self._ensure_window_visible)
        logger.info("✅ Приложение запущено")

    def _ensure_window_visible(self):
        try:
            self.update_idletasks()
            sw=max(1080,int(self.winfo_screenwidth()))
            sh=max(720,int(self.winfo_screenheight()))
            width=min(1500,max(1080,sw-40))
            height=min(920,max(680,sh-90))
            x=max(0,(sw-width)//2)
            y=max(0,(sh-height)//2-10)
            try:
                if str(self.state()) in ('iconic','withdrawn'):
                    self.state('normal')
            except Exception:
                pass
            self.geometry(f'{width}x{height}+{x}+{y}')
            self.deiconify()
            self.lift()
        except Exception:
            logger.exception('Не удалось восстановить геометрию главного окна')

    def _configure_modern_styles(self):
        c = Theme.colors
        style = ttk.Style(self)
        try:
            style.theme_use('clam')
        except tk.TclError:
            pass
        style.configure('TNotebook', background=c['bg'], borderwidth=0,
                        tabmargins=(4, 4, 4, 0))
        style.configure('TNotebook.Tab', background=c['bg'], foreground=c['fg'],
                        padding=(22, 11), font=('Segoe UI Semibold', 10),
                        borderwidth=0, focuscolor=c['bg'])
        style.map('TNotebook.Tab',
                  background=[('selected', c['card_bg']), ('active', c['hover'])],
                  foreground=[('selected', c['accent']), ('active', c['fg'])])
        style.configure('Dashboard.Horizontal.TProgressbar',
                        troughcolor=c['btn'], background=c['accent'],
                        bordercolor=c['btn'], lightcolor=c['accent'],
                        darkcolor=c['accent'], thickness=7)
        style.configure('green.Horizontal.TProgressbar',
                        troughcolor=c['btn'], background=c['success'],
                        bordercolor=c['btn'], lightcolor=c['success'],
                        darkcolor=c['success'], thickness=10)
        style.configure('Studio.Treeview', background=c['entry'],
                        fieldbackground=c['entry'], foreground=c['fg'],
                        borderwidth=0, rowheight=30,
                        font=('Segoe UI', 9))
        style.configure('Studio.Treeview.Heading', background=c['btn'],
                        foreground=c['fg'], borderwidth=0,
                        padding=(8, 8), font=('Segoe UI Semibold', 9))

    def _apply_modern_widget_finish(self):
        c = Theme.colors
        protected = {c['success'].casefold(), c['warning'].casefold(),
                     c['error'].casefold(), c['accent'].casefold()}

        def finish(widget):
            if isinstance(widget, (tk.Button, tk.Menubutton)):
                try:
                    widget.configure(relief=tk.FLAT, bd=0, cursor='hand2',
                                     highlightthickness=0,
                                     font=('Segoe UI Semibold', 9))
                    current = str(widget.cget('background')).casefold()
                    if current not in protected:
                        widget.configure(activebackground=c['hover'],
                                         activeforeground=c['fg'])
                except tk.TclError:
                    pass
            elif isinstance(widget, tk.Entry):
                try:
                    widget.configure(relief=tk.FLAT, bd=0,
                                     highlightthickness=1,
                                     highlightbackground=c['border'],
                                     highlightcolor=c['accent'],
                                     font=('Segoe UI', 10))
                except tk.TclError:
                    pass
            elif isinstance(widget, (tk.Text, tk.Listbox)):
                try:
                    widget.configure(relief=tk.FLAT, bd=0,
                                     highlightthickness=1,
                                     highlightbackground=c['border'])
                except tk.TclError:
                    pass
            for child in widget.winfo_children():
                finish(child)

        finish(self)
        self._configure_modern_styles()

    def create_stats_tab(self):
        c = Theme.colors
        main = tk.Frame(self.tab_stats, bg=c['bg'])
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        title_row = tk.Frame(main, bg=c['bg'])
        title_row.pack(fill=tk.X, padx=20, pady=(4, 10))
        title_box = tk.Frame(title_row, bg=c['bg'])
        title_box.pack(side=tk.LEFT)
        tk.Label(title_box, text="Аналитика", bg=c['bg'], fg=c['fg'],
                 font=("Segoe UI Semibold", 22)).pack(anchor='w')
        tk.Label(title_box, text="Сводка OCR и внесения · скорость, качество и объём",
                 bg=c['bg'], fg=c['accent'], font=("Segoe UI", 9)).pack(anchor='w', pady=(2,0))
        stats_actions = tk.Frame(main, bg=c['bg'])
        stats_actions.pack(fill=tk.X, padx=20, pady=(2, 6))
        tk.Button(stats_actions, text="📥 Скачать статистику в Excel", command=self.export_excel,
                  bg=c['success'], fg='#ffffff', activebackground=c['accent'], activeforeground='#ffffff',
                  font=("Segoe UI", 11, "bold"), relief=tk.FLAT, padx=28, pady=9,
                  cursor='hand2').pack(side=tk.RIGHT)
        tk.Button(stats_actions, text="🔄 Обновить", command=self.update_stats_display,
                  bg=c['btn'], fg=c['fg'], font=("Segoe UI", 10, "bold"), relief=tk.FLAT,
                  padx=22, pady=9, cursor='hand2').pack(side=tk.RIGHT, padx=(0, 10))
        daily_frame = tk.Frame(main, bg=c['card_bg'], relief=tk.FLAT, bd=0,
                               highlightthickness=1, highlightbackground=c['border'])
        daily_frame.pack(fill=tk.X, pady=10, padx=20)
        tk.Label(daily_frame, text="Сегодня", bg=c['card_bg'], fg=c['fg'],
                 font=("Segoe UI Semibold", 13)).pack(anchor='w', padx=18, pady=(14,5))
        d_inner = tk.Frame(daily_frame, bg=c['card_bg'])
        d_inner.pack(pady=10)
        self.stats_daily_ocr = tk.Label(d_inner, text=f"📄 OCR распознано: {daily_stats.get_ocr()}", bg=c['card_bg'], fg=c['accent'], font=("Segoe UI", 12))
        self.stats_daily_ocr.pack(side=tk.LEFT, padx=20)
        self.stats_daily_input = tk.Label(d_inner, text=f"📥 Внесено в систему: {daily_stats.get_input()}", bg=c['card_bg'], fg=c['success'], font=("Segoe UI", 12))
        self.stats_daily_input.pack(side=tk.LEFT, padx=20)
        self.stats_daily_history = tk.Label(daily_frame, text=f"По календарным дням: {daily_stats.history_text()}", bg=c['card_bg'], fg=c['fg'], font=("Segoe UI", 9), anchor='w', justify=tk.LEFT)
        self.stats_daily_history.pack(fill=tk.X, padx=20, pady=(0, 4))
        tk.Button(daily_frame, text="🔄 Сбросить статистику", command=self.reset_daily_stats, bg=c['error'], fg=c['bg'], font=("Segoe UI", 9, "bold")).pack(pady=5)
        sf = tk.Frame(main, bg=c['bg'])
        sf.pack(fill=tk.X, pady=10)
        for column in range(3):
            sf.grid_columnconfigure(column, weight=1, uniform='stats')
        summ = stats.get_summary()
        perf_docs=int(getattr(self.ocr_robot,'_ocr_perf_docs',0) or 0)
        perf_seconds=float(getattr(self.ocr_robot,'_ocr_perf_seconds',0.0) or 0.0)
        perf_avg=(perf_seconds/perf_docs) if perf_docs else 0.0
        data = [
            ("📁 OCR всего", str(summ['ocr_total']), c['accent']),
            ("✅ OCR создано", str(summ['ocr_created']), c['success']),
            ("⏭ OCR пропущено", str(summ['ocr_skipped']), c['warning']),
            ("⏱️ OCR время", f"{int(summ['ocr_time'])}с", c['warning']),
            ("🗳️ OCR голосов", str(summ['ocr_total_votes']), c['accent']),
            ("📂 Ввод всего", str(summ['input_total']), c['accent']),
            ("✅ Ввод успешно", str(summ['input_processed']), c['success']),
            ("❌ Ввод ошибок", str(summ['input_errors']), c['error']),
            ("⏱️ Ввод время", f"{int(summ['input_time'])}с", c['warning']),
            ("🗳️ Ввод голосов", str(summ['input_total_votes']), c['accent']),
            ("🧠 Исправлений", str(len(self.ocr_robot.corrections)), c['accent']),
            ("⚡ OCR среднее", f"{perf_avg:.1f} с", c['warning']),
            ("🚀 OCR скорость", f"{(60.0/perf_avg if perf_avg else 0):.2f} док/мин", c['success']),
            ("🎯 Автопринято", f"{(getattr(self.ocr_robot,'_ocr_perf_auto_accepted',0)/perf_docs*100 if perf_docs else 0):.0f}%", c['accent'])
        ]
        self.stats_cards = {}
        for i, (label, val, col) in enumerate(data):
            card = tk.Frame(sf, bg=c['card_bg'], relief=tk.FLAT, bd=0,
                            highlightthickness=1, highlightbackground=c['border'])
            card.grid(row=i//3, column=i%3, padx=10, pady=10, sticky="nsew")
            tk.Label(card, text=label, bg=c['card_bg'], fg=c['fg'],
                     font=("Segoe UI", 9), anchor='w').pack(fill=tk.X, padx=16, pady=(14,3))
            lb = tk.Label(card, text=val, bg=c['card_bg'], fg=col,
                          font=("Segoe UI Semibold", 18), anchor='w')
            lb.pack(fill=tk.X, padx=16, pady=(2,14))
            self.stats_cards[label] = lb

        oss_frame = tk.Frame(main, bg=c['card_bg'], relief=tk.FLAT, bd=0,
                             highlightthickness=1, highlightbackground=c['border'])
        oss_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(4, 10))
        tk.Label(oss_frame, text='ОСС в последней партии', bg=c['card_bg'], fg=c['fg'],
                 font=('Segoe UI Semibold', 13)).pack(anchor='w', padx=18, pady=(12, 2))
        self.stats_oss_summary = tk.Label(
            oss_frame, text='Нет данных о завершённых партиях', bg=c['card_bg'],
            fg=c['accent'], font=('Segoe UI', 9), anchor='w')
        self.stats_oss_summary.pack(fill=tk.X, padx=18, pady=(0, 7))
        oss_table = tk.Frame(oss_frame, bg=c['card_bg'])
        oss_table.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 12))
        self.stats_oss_tree = ttk.Treeview(
            oss_table, columns=('oss', 'files'), show='headings', height=7,
            style='Studio.Treeview')
        self.stats_oss_tree.heading('oss', text='Номер ОСС')
        self.stats_oss_tree.heading('files', text='Файлов было')
        self.stats_oss_tree.column('oss', width=180, anchor='center')
        self.stats_oss_tree.column('files', width=150, anchor='center')
        oss_scroll = ttk.Scrollbar(oss_table, orient='vertical',
                                   command=self.stats_oss_tree.yview)
        self.stats_oss_tree.configure(yscrollcommand=oss_scroll.set)
        self.stats_oss_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        oss_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._refresh_oss_stats_display()

    def _select_app_page(self, index):
        try:
            tabs=(self.tab_ocr, self.tab_robot, self.tab_stats, self.tab_dev)
            if 0 <= int(index) < len(tabs):
                self.notebook.select(tabs[int(index)])
                self.after_idle(self._refresh_nav_state)
        except Exception:
            logger.exception('Не удалось переключить раздел приложения')

    def _refresh_nav_state(self):
        try:
            current=self.notebook.index(self.notebook.select())
            for index, button in enumerate(self.nav_buttons):
                active=index == current
                button.configure(
                    bg=Theme.colors['accent'] if active else Theme.colors['card_bg'],
                    fg='white' if active else Theme.colors['fg'],
                    activebackground=Theme.colors['accent'] if active else Theme.colors['hover'],
                    activeforeground='white' if active else Theme.colors['fg'])
        except (tk.TclError, AttributeError):
            pass

    def _on_notebook_tab_changed(self, event=None):
        self.after_idle(self._refresh_nav_state)
        if self._dev_auth_busy:
            return
        selected = self.notebook.select()
        if selected != str(self.tab_dev):
            self._dev_return_tab = selected
            self.dev_tab_access = False
            return
        if self.dev_tab_access:
            return
        self._dev_auth_busy = True
        try:
            self.notebook.select(self._dev_return_tab)
            self.update_idletasks()
            if not self._authorize_dev_tab():
                return
            self.dev_tab_access = True
            if not self._dev_ui_built:
                self.create_dev_tab()
                self._dev_ui_built = True
            self.notebook.select(self.tab_dev)
        except Exception:
            self.dev_tab_access = False
            self.notebook.select(self._dev_return_tab)
            logger.exception('Ошибка открытия вкладки разработчика')
            messagebox.showerror('Разработчик', 'Не удалось открыть вкладку разработчика.')
        finally:
            self._dev_auth_busy = False

    def _authorize_dev_tab(self):
        env_password = os.environ.get("ROBOT_DEV_PASSWORD", "")
        stored = None
        if not env_password and os.path.exists(DEV_AUTH_PATH):
            try:
                with open(DEV_AUTH_PATH, 'r', encoding='utf-8') as f:
                    stored = json.load(f)
            except Exception:
                logger.exception("Не удалось прочитать настройки доступа разработчика")

        if not env_password and not stored:
            first = simpledialog.askstring("🛠 Первый запуск", "Создайте пароль разработчика:", parent=self, show='*')
            if not first:
                return False
            second = simpledialog.askstring("🛠 Первый запуск", "Повторите пароль разработчика:", parent=self, show='*')
            if first != second:
                messagebox.showerror("Разработчик", "Пароли не совпадают.")
                return False
            salt = os.urandom(16)
            digest = hashlib.pbkdf2_hmac('sha256', first.encode('utf-8'), salt, 200_000)
            stored = {'salt': salt.hex(), 'hash': digest.hex(), 'iterations': 200000}
            try:
                with open(DEV_AUTH_PATH, 'w', encoding='utf-8') as f:
                    json.dump(stored, f, ensure_ascii=False, indent=2)
            except Exception:
                logger.exception("Не удалось сохранить пароль разработчика")
                messagebox.showerror("Разработчик", "Не удалось сохранить пароль. Доступ не открыт.")
                return False
            password = first
        else:
            password = simpledialog.askstring("🛠 Доступ к разработчику", "Введите пароль для доступа к редактору кода:", parent=self, show='*')

        access_ok = False
        if env_password:
            import hmac
            access_ok = bool(password) and hmac.compare_digest(password.encode('utf-8'), env_password.encode('utf-8'))
        elif stored and password:
            try:
                import hmac
                salt = bytes.fromhex(stored['salt'])
                iterations = int(stored.get('iterations', 200000))
                digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations).hex()
                access_ok = hmac.compare_digest(digest, stored['hash'])
            except Exception:
                logger.exception("Ошибка проверки пароля разработчика")
        if not access_ok:
            if password:
                messagebox.showerror("Доступ запрещён", "Неверный пароль!")
            return False
        return True

    def create_dev_tab(self):
        if not self.dev_tab_access:
            return
        c = Theme.colors
        if not self.tab_dev.winfo_exists():
            return
        for widget in self.tab_dev.winfo_children():
            widget.destroy()

        main = tk.Frame(self.tab_dev, bg=c['bg'])
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        header = tk.Frame(main, bg=c['bg_secondary'])
        header.pack(fill=tk.X, pady=(0, 10))
        tk.Label(header, text="🛠 РЕДАКТОР КОДА - АВТОМАТИЗАЦИЯ v30.0",
                 bg=c['bg_secondary'], fg=c['accent'],
                 font=("Segoe UI", 14, "bold")).pack(pady=10)

        info_frame = tk.Frame(main, bg=c['bg'])
        info_frame.pack(fill=tk.X, pady=5)

        self.dev_status = tk.Label(info_frame,
            text="✅ Готов к редактированию | Внимание: изменения применяются после перезапуска!",
            bg=c['bg'], fg=c['success'], font=("Segoe UI", 10))
        self.dev_status.pack(side=tk.LEFT, padx=10)

        btn_frame = tk.Frame(info_frame, bg=c['bg'])
        btn_frame.pack(side=tk.RIGHT, padx=10)

        self.btn_reload = tk.Button(btn_frame, text="🔄 Перечитать код",
                                    command=self.reload_code,
                                    bg=c['btn'], fg=c['fg'],
                                    font=("Segoe UI", 9, "bold"))
        self.btn_reload.pack(side=tk.LEFT, padx=5)

        self.btn_save = tk.Button(btn_frame, text="💾 Сохранить и перезапустить",
                                  command=self.save_and_restart,
                                  bg="#FF6B00", fg='white',
                                  font=("Segoe UI", 9, "bold"))
        self.btn_save.pack(side=tk.LEFT, padx=5)

        self.btn_backup = tk.Button(btn_frame, text="📦 Создать бэкап",
                                    command=self.create_backup,
                                    bg="#0066CC", fg='white',
                                    font=("Segoe UI", 9, "bold"))
        self.btn_backup.pack(side=tk.LEFT, padx=5)

        self.btn_paste = tk.Button(btn_frame, text="📋 Вставить",
                                   command=self.paste_code,
                                   bg="#2E8B57", fg='white',
                                   font=("Segoe UI", 9, "bold"))
        self.btn_paste.pack(side=tk.LEFT, padx=5)

        editor_frame = tk.Frame(main, bg=c['bg_secondary'])
        editor_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        status_bar = tk.Frame(editor_frame, bg=c['bg_secondary'], height=25)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        status_bar.pack_propagate(False)

        self.editor_status = tk.Label(status_bar,
            text="Строка: 1 | Колонка: 1 | Символов: 0 | Изменено: Нет",
            bg=c['bg_secondary'], fg=c['fg'], font=("Segoe UI", 8))
        self.editor_status.pack(side=tk.LEFT, padx=10)

        self.code_editor = tk.Text(editor_frame,
                                   bg=c['entry'],
                                   fg=c['fg'],
                                   insertbackground=c['fg'],
                                   font=("Consolas", 10),
                                   wrap=tk.NONE,
                                   undo=True,
                                   maxundo=100)
        self.code_editor.bind('<Control-v>', self.paste_code_event)

        v_scroll = tk.Scrollbar(editor_frame, orient=tk.VERTICAL, command=self.code_editor.yview)
        h_scroll = tk.Scrollbar(editor_frame, orient=tk.HORIZONTAL, command=self.code_editor.xview)
        self.code_editor.config(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.code_editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.code_editor.bind('<KeyRelease>', self.on_code_change)
        self.code_editor.bind('<ButtonRelease-1>', self.update_cursor_position)
        self.code_editor.bind('<KeyRelease>', self.update_cursor_position)

        log_frame = tk.LabelFrame(main, text="📋 Лог изменений", bg=c['bg'], fg=c['fg'],
                                  font=("Segoe UI", 9, "bold"))
        log_frame.pack(fill=tk.X, pady=5)

        self.dev_log = tk.Text(log_frame, bg=c['entry'], fg=c['fg'],
                              font=("Consolas", 8), height=5, wrap=tk.WORD)
        self.dev_log.pack(fill=tk.X, padx=5, pady=5)
        self.dev_log.config(state=tk.DISABLED)

        self.load_current_code()
        self.code_modified = False

        self.log_dev_message("✅ Вкладка разработчика загружена")
        self.log_dev_message(f"📁 Файл: {self.get_script_path()}")
        self.log_dev_message("🔐 Пароль разработчика не выводится в интерфейсе")
        self.log_dev_message("💡 Используйте Ctrl+V для вставки кода")

    def get_script_path(self):
        return os.path.abspath(sys.argv[0])

    def load_current_code(self):
        try:
            path = self.get_script_path()
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    code = f.read()
                self.code_editor.delete(1.0, tk.END)
                self.code_editor.insert(1.0, code)
                self.editor_status.config(text=f"Строк: {code.count(chr(10))+1} | Символов: {len(code)} | Изменено: Нет")
                self.log_dev_message(f"✅ Код загружен: {os.path.basename(path)}")
                self.code_modified = False
            else:
                self.log_dev_message(f"❌ Файл не найден: {path}")
        except Exception as e:
            self.log_dev_message(f"❌ Ошибка загрузки: {e}")

    def on_code_change(self, event):
        if not hasattr(self, 'code_modified'): self.code_modified = True
        elif not self.code_modified:
            self.code_modified = True
            if 'Изменено: Нет' in self.editor_status.cget('text'):
                self.editor_status.config(text=self.editor_status.cget('text').replace('Изменено: Нет', 'Изменено: ДА'))
                self.dev_status.config(text="⚠️ Код изменён! Сохраните изменения и перезапустите программу.", fg=Theme.colors['warning'])

    def update_cursor_position(self, event=None):
        try:
            row, col = self.code_editor.index(tk.INSERT).split('.')
            current = self.editor_status.cget('text')
            parts = current.split('|')
            if len(parts) >= 2:
                status = parts[2].strip() if len(parts)>2 else "Изменено: Нет"
                self.editor_status.config(text=f"Строка: {row} | Колонка: {int(col)+1} | {status}")
        except Exception: pass

    def log_dev_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        if hasattr(self, 'dev_log') and self.dev_log:
            self.dev_log.config(state=tk.NORMAL)
            self.dev_log.insert(tk.END, f"[{timestamp}] {message}\n")
            self.dev_log.see(tk.END)
            self.dev_log.config(state=tk.DISABLED)
        else:
            logger.info("[%s] %s", timestamp, message)

    def paste_code(self):
        try:
            clipboard_text = self.clipboard_get()
            if clipboard_text:
                self.code_editor.insert(tk.INSERT, clipboard_text)
                self.on_code_change(None)
                self.log_dev_message("📋 Вставлено из буфера обмена")
        except tk.TclError:
            self.log_dev_message("⚠️ Буфер обмена пуст или недоступен")
        except Exception as e:
            self.log_dev_message(f"❌ Ошибка вставки: {e}")

    def paste_code_event(self, event):
        self.paste_code()
        return "break"

    def create_backup(self):
        try:
            path = self.get_script_path()
            backup_dir = os.path.join(SCRIPT_DIR, "backups")
            os.makedirs(backup_dir, exist_ok=True)
            backup_name = f"АВТОМАТИЗАЦИЯ_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
            backup_path = os.path.join(backup_dir, backup_name)
            shutil.copy2(path, backup_path)
            self.log_dev_message(f"✅ Бэкап создан: {backup_name}")
            messagebox.showinfo("Бэкап создан", f"Сохранено в:\n{backup_path}")
        except Exception as e:
            self.log_dev_message(f"❌ Ошибка создания бэкапа: {e}")
            messagebox.showerror("Ошибка", str(e))

    def reload_code(self):
        if self.code_modified and not messagebox.askyesno("Есть изменения", "В редакторе есть несохранённые изменения. Перезагрузить (потеряете изменения)?"):
            return
        self.load_current_code()
        self.code_modified = False
        self.log_dev_message("🔄 Код перечитан из файла")
        self.dev_status.config(text="✅ Код перечитан", fg=Theme.colors['success'])

    def save_and_restart(self):
        try:
            path = self.get_script_path()
            new_code = self.code_editor.get(1.0, tk.END)
            backup_dir = os.path.join(SCRIPT_DIR, "backups")
            os.makedirs(backup_dir, exist_ok=True)
            backup_name = f"auto_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
            backup_path = os.path.join(backup_dir, backup_name)
            shutil.copy2(path, backup_path)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_code)
            self.log_dev_message(f"✅ Код сохранён (бэкап: {backup_name})")
            if messagebox.askyesno("Перезапуск", "Код сохранён!\n\nДля применения изменений нужно перезапустить программу.\nПерезапустить сейчас?"):
                self.log_dev_message("🔄 Перезапуск программы...")
                self.dev_status.config(text="🔄 Перезапуск...", fg=Theme.colors['warning'])
                robot = getattr(self, 'ocr_robot', None)
                if robot is not None:
                    try:
                        robot._pause_manual_timer()
                        robot._capture_draft()
                        robot.save_progress()
                    except Exception:
                        logger.exception('Не удалось сохранить сеанс перед перезапуском')
                python = sys.executable
                os.execl(python, python, *sys.argv)
        except Exception as e:
            self.log_dev_message(f"❌ Ошибка сохранения: {e}")
            messagebox.showerror("Ошибка", str(e))

    def reset_daily_stats(self):
        if messagebox.askyesno("Сброс", "Сбросить дневную статистику?"):
            daily_stats.reset()
            self.update_daily_display()
            messagebox.showinfo("Готово", "Статистика сброшена")

    def update_daily_display(self):
        self.daily_ocr.config(text=f"📄 OCR сегодня: {daily_stats.get_ocr()}")
        self.daily_input.config(text=f"📥 Ввод сегодня: {daily_stats.get_input()}")
        if hasattr(self, 'stats_daily_ocr'):
            self.stats_daily_ocr.config(text=f"📄 OCR распознано: {daily_stats.get_ocr()}")
            self.stats_daily_input.config(text=f"📥 Внесено в систему: {daily_stats.get_input()}")
        if hasattr(self, 'stats_daily_history'):
            self.stats_daily_history.config(text=f"По календарным дням: {daily_stats.history_text()}")
        if hasattr(self.ocr_robot, 'daily_ocr_label'):
            self.ocr_robot.daily_ocr_label.config(text=f"📄 OCR: {daily_stats.get_ocr()}")
            self.ocr_robot.daily_input_label.config(text=f"📥 Ввод: {daily_stats.get_input()}")

    def create_status_bar(self):
        c = Theme.colors
        self.status_bar = tk.Label(self, text="Ctrl+Enter — подтвердить   •   Esc — стоп   •   Сеанс сохраняется автоматически", bg=c['bg_secondary'], fg=c['fg'], font=("Segoe UI", 9), anchor=tk.W, padx=15)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _apply_live_theme(self, old_colors, new_colors):
        self.configure(bg=new_colors['bg'])
        color_map = {
            str(old_colors[key]).casefold(): new_colors[key]
            for key in old_colors if key in new_colors
        }

        def recolor(widget):
            options = (
                'background', 'foreground', 'activebackground',
                'activeforeground', 'insertbackground', 'selectbackground',
                'selectforeground', 'highlightbackground', 'highlightcolor',
                'troughcolor'
            )
            for option in options:
                try:
                    current = str(widget.cget(option)).casefold()
                    if current in color_map:
                        widget.configure(**{option: color_map[current]})
                except (tk.TclError, AttributeError):
                    pass
            if isinstance(widget, tk.Canvas):
                for item in widget.find_all():
                    for option in ('fill', 'outline'):
                        try:
                            current = str(widget.itemcget(item, option)).casefold()
                            if current in color_map:
                                widget.itemconfigure(item, **{option: color_map[current]})
                        except tk.TclError:
                            pass
            for child in widget.winfo_children():
                recolor(child)

        recolor(self)
        style = ttk.Style(self)
        style.configure('TNotebook', background=new_colors['bg'], borderwidth=0)
        style.configure('TNotebook.Tab', background=new_colors['btn'],
                        foreground=new_colors['fg'], padding=(16, 9),
                        font=('Segoe UI', 9, 'bold'), borderwidth=0)
        style.map('TNotebook.Tab',
                  background=[('selected', new_colors['card_bg'])],
                  foreground=[('selected', new_colors['accent'])])
        style.configure('Custom.TLabelframe', background=new_colors['bg_secondary'],
                        foreground=new_colors['fg'])
        style.configure('Custom.TLabelframe.Label',
                        background=new_colors['bg_secondary'],
                        foreground=new_colors['accent'])
        style.configure('Dashboard.Horizontal.TProgressbar',
                        troughcolor=new_colors['card_bg'],
                        background=new_colors['accent'],
                        bordercolor=new_colors['border'],
                        lightcolor=new_colors['accent'],
                        darkcolor=new_colors['accent'])
        style.configure('Studio.Treeview', background=new_colors['entry'],
                        fieldbackground=new_colors['entry'],
                        foreground=new_colors['fg'])
        style.configure('Studio.Treeview.Heading', background=new_colors['btn'],
                        foreground=new_colors['fg'])
        style.map('Studio.Treeview',
                  background=[('selected', new_colors['accent'])],
                  foreground=[('selected', 'white')])
        style.configure('green.Horizontal.TProgressbar',
                        background=new_colors['success'],
                        troughcolor=new_colors['bg_secondary'],
                        bordercolor=new_colors['success'],
                        lightcolor=new_colors['success'],
                        darkcolor=new_colors['success'])

    def toggle_theme(self):
        old_colors = dict(Theme.colors)
        theme_name = Theme.toggle()
        self._apply_live_theme(old_colors, dict(Theme.colors))
        self._configure_modern_styles()
        self.settings.set("theme", theme_name)
        self.settings.save()
        if hasattr(self, 'theme_button'):
            self.theme_button.config(
                text='☀ Светлая' if theme_name == 'dark' else '🌙 Тёмная')
        self._refresh_nav_state()
        self.status_bar.config(
            text=f"Тема переключена: {'светлая' if theme_name=='light' else 'тёмная'}. "
                 "OCR и внесение продолжают работу."
        )
        logger.info("Тема переключена без остановки процессов: %s", theme_name)

    def _refresh_oss_stats_display(self):
        if not hasattr(self, 'stats_oss_tree'):
            return
        batch = stats.latest_oss_batch()
        rows = []
        if isinstance(batch, dict):
            rows = [row for row in (batch.get('rows') or []) if isinstance(row, dict)]
            timestamp = str(batch.get('timestamp', '') or '').replace('T', ' ')[:16]
            self.stats_oss_summary.config(
                text=(f"ОСС: {int(batch.get('oss_count', len(rows)) or len(rows))}  •  "
                      f"файлов: {int(batch.get('total_files', sum(int(row.get('files', 0) or 0) for row in rows)) or 0)}  •  "
                      f"партия: {timestamp}"))
        else:
            counts = {}
            for oss in get_oss_folders():
                amount = len(get_pdf_files(oss))
                if amount:
                    counts[str(oss)] = amount
            rows = [{'oss': oss, 'files': amount} for oss, amount in counts.items()]
            self.stats_oss_summary.config(
                text=(f"Текущий source: ОСС {len(rows)}  •  файлов: "
                      f"{sum(int(row.get('files', 0) or 0) for row in rows)}"))
        for item in self.stats_oss_tree.get_children():
            self.stats_oss_tree.delete(item)
        for row in sorted(rows, key=lambda item: int(str(item.get('oss', 0) or 0))):
            self.stats_oss_tree.insert('', 'end', values=(
                str(row.get('oss', '')), int(row.get('files', 0) or 0)))

    def update_stats_display(self):
        summ = stats.get_summary()
        perf_docs=int(getattr(self.ocr_robot,'_ocr_perf_docs',0) or 0)
        perf_seconds=float(getattr(self.ocr_robot,'_ocr_perf_seconds',0.0) or 0.0)
        perf_avg=(perf_seconds/perf_docs) if perf_docs else 0.0
        mapping = {
            "📁 OCR всего": str(summ['ocr_total']),
            "✅ OCR создано": str(summ['ocr_created']),
            "⏭ OCR пропущено": str(summ['ocr_skipped']),
            "⏱️ OCR время": f"{int(summ['ocr_time'])}с",
            "🗳️ OCR голосов": str(summ['ocr_total_votes']),
            "📂 Ввод всего": str(summ['input_total']),
            "✅ Ввод успешно": str(summ['input_processed']),
            "❌ Ввод ошибок": str(summ['input_errors']),
            "⏱️ Ввод время": f"{int(summ['input_time'])}с",
            "🗳️ Ввод голосов": str(summ['input_total_votes']),
            "🧠 Исправлений": str(len(self.ocr_robot.corrections)),
            "⚡ OCR среднее": f"{perf_avg:.1f} с",
            "\U0001f680 OCR скорость": f"{(60.0/perf_avg if perf_avg else 0):.2f} док/мин",
            "\U0001f3af Автопринято": (
                f"{(getattr(self.ocr_robot,'_ocr_perf_auto_accepted',0)/perf_docs*100 if perf_docs else 0):.0f}%")
        }
        for label, value in mapping.items():
            if label in self.stats_cards:
                self.stats_cards[label].config(text=value)
        self._refresh_oss_stats_display()
        self.update_daily_display()

    def export_excel(self):
        if not EXCEL_AVAILABLE:
            messagebox.showwarning("Внимание", "Установите: pip install openpyxl")
            return
        default_name = f"Статистика_Единый_Робот_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")],
            title="Скачать статистику в Excel", initialfile=default_name
        )
        if not path: return
        try:
            stats.export_excel(path)
            messagebox.showinfo("Готово", f"✅ Excel-отчёт сохранён:\n{path}")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def on_close(self):
        if getattr(self.ocr_robot, 'saving_busy', False):
            self.ocr_robot.log_label.config(text='Дождитесь завершения сохранения PDF перед закрытием.')
            return
        if messagebox.askokcancel("Выход", "Закрыть программу?"):
            self.settings.save()
            if hasattr(self.ocr_robot, 'shutdown'):
                self.ocr_robot.shutdown()
            if hasattr(self.ocr_robot, 'save_corrections'):
                self.ocr_robot.save_corrections()
            if hasattr(self, 'robot_helper'):
                self.robot_helper.stop_flag = True
                if hasattr(self.robot_helper, 'login_event'):
                    self.robot_helper.login_event.set()
                if hasattr(self.robot_helper, '_close_driver'):
                    self.robot_helper._close_driver()
                elif self.robot_helper.driver:
                    try:
                        self.robot_helper.driver.quit()
                    except Exception:
                        pass
            self.destroy()
            sys.exit(0)

if __name__ == "__main__" and '--ocr-job' in sys.argv:
    position = sys.argv.index('--ocr-job')
    raise SystemExit(_studio_worker(os.path.abspath(sys.argv[position + 1])))

if __name__ == "__main__" and '--ocr-worker' in sys.argv:
    raise SystemExit(_persistent_ocr_worker())

if __name__ == "__main__":
    _single_instance_mutex = None
    if os.name == 'nt':
        try:
            import ctypes
            _single_instance_mutex = ctypes.windll.kernel32.CreateMutexW(
                None, False, 'Local\\OCRStudio_v43_single_instance')
            if ctypes.windll.kernel32.GetLastError() == 183:
                messagebox.showwarning(
                    'OCR Studio уже запущен',
                    'Уже работает другое окно OCR Studio.\n\n'
                    'Закройте его или продолжайте работу в нём — второй экземпляр '
                    'не запущен, чтобы не повредить сохранённую сессию.')
                raise SystemExit(0)
        except SystemExit:
            raise
        except Exception:
            logger.exception('Не удалось проверить второй экземпляр приложения')
    logger.info("OCR Studio v43.17.73 LOWERCASE FIO FIX; folder=%s; selenium=%s; workers=%s",
                SCRIPT_DIR, SELENIUM_AVAILABLE, OCR_PARALLEL_WORKERS)
    try:
        app = MainApp()
        app.mainloop()
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
        try: messagebox.showerror("Ошибка запуска OCR Studio", str(e))
        except Exception: pass
