# -*- coding: utf-8 -*-
import os
import re
import sys
import json
import time
import random
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

try:
    from pynspd import Nspd
    from openpyxl import Workbook
    from openpyxl.styles import Font
except Exception:
    traceback.print_exc()
    input("\nНажмите Enter для закрытия...")
    sys.exit(1)


MAX_WORKERS = min(8, (os.cpu_count() or 4) * 2)
REQUEST_TIMEOUT = 45
MAX_RETRIES = 3
ADDRESS_PAUSE_MIN = 3
ADDRESS_PAUSE_MAX = 5
ROOM_PAUSE_MIN = 0.1
ROOM_PAUSE_MAX = 0.4
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP_DIR = os.path.join(os.path.expanduser("~"), "Desktop")
OUTPUT_DIR = os.path.join(DESKTOP_DIR, "адреса")

def pause_exit(message="Нажмите Enter для закрытия..."):
    input(f"\n{message}")


def get_option(options, *names):
    for name in names:
        value = options.get(name) if isinstance(options, dict) else getattr(options, name, None)
        if value not in (None, "", "None", "null"):
            return str(value).strip()
    return ""


def call_with_timeout(function, *args, timeout=REQUEST_TIMEOUT):
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(function, *args)
    try:
        return future.result(timeout=timeout)
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def call_with_retries(function, *args, label="запрос"):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return call_with_timeout(function, *args)
        except Exception as error:
            print(f"[повтор {attempt}/{MAX_RETRIES}] {label}: {error}")
            if attempt < MAX_RETRIES:
                if "403" in str(error) or "доступ заблокирован" in str(error).lower():
                    time.sleep(15 * attempt)
                else:
                    time.sleep(2 * attempt)
    raise RuntimeError(f"Не удалось выполнить {label}")


def get_cadastral_number(feature):
    options = getattr(getattr(feature, "properties", None), "options", None)

    value = get_option(
        options,
        "cadastral_number",
        "cad_num",
        "kn",
        "object_cad_num",
        "cadastral_num",
    )

    if value:
        return value

    text = str(feature)
    match = re.search(r"\b\d{2}:\d{2}:\d{6,7}:\d+\b", text)
    return match.group(0) if match else ""


def normalized_address(value):
    value = value.lower().replace("ё", "е")
    for pattern, replacement in (
        (r"\bд\.", "дом "), (r"\bкорп\.", "корпус "),
        (r"\bк\.", "корпус "), (r"\bстр\.", "строение "),
        (r"\bул\.", "улица "), (r"\bпр-т\b", "проспект"),
    ):
        value = re.sub(pattern, replacement, value)
    return re.sub(r"\s+", " ", value).strip()


def address_matches(requested, actual):
    requested, actual = map(normalized_address, (requested, actual))
    number_pattern = r"\b(?:дом|корпус|строение)\s*(\d+[а-яa-z]?(?:/\d+[а-яa-z]?)?)\b"
    for label in ("дом", "корпус", "строение"):
        pattern = number_pattern.replace("(?:дом|корпус|строение)", label)
        expected = re.findall(pattern, requested)
        received = re.findall(pattern, actual)
        if expected != received:
            return False
    street = re.split(r"\bдом\b", requested)[0]
    tokens = re.findall(r"[а-я]+|\d+", street)
    actual_tokens = set(re.findall(r"[а-я]+|\d+", actual))
    return bool(tokens) and all(token in actual_tokens for token in tokens)


def find_building(nspd, user_input):
    if re.fullmatch(r"\d{2}:\d{2}:\d+:\d+", user_input):
        print(f"🔎 Поиск по кадастровому номеру: {user_input}", flush=True)
        building = call_with_retries(
            nspd.find, user_input, label="поиск по кадастровому номеру"
        )
        if not building:
            return None
        options = getattr(getattr(building, "properties", None), "options", None)
        actual = get_option(options, "readable_address", "address")
        normalized = normalized_address(actual)
        if not re.search(r"\bмосква\b", normalized) or "московская область" in normalized:
            print(f"❌ Объект не относится к Москве: {actual or 'адрес не указан'}")
            return None
        return building

    query = f"город Москва, {user_input}"
    print(f"🔎 Поиск: {query}", flush=True)
    found = call_with_retries(nspd.search, query, label="поиск московского МКД")
    candidates = {}
    for feature in found or []:
        kad = get_cadastral_number(feature)
        if not kad:
            print("Пропуск: у результата отсутствует кадастровый номер.")
            continue
        # Read the full card: search results may omit address/type fields.
        full = call_with_retries(nspd.find, kad, label=f"карточка {kad}")
        if not full:
            continue
        properties = getattr(full, "properties", None)
        options = getattr(properties, "options", None)
        actual = get_option(options, "readable_address", "address")
        norm = normalized_address(actual)
        kind = " ".join(get_option(options, key) for key in (
            "type", "object_type", "object_kind", "kind", "purpose",
            "name", "building_name", "building_purpose"))
        kind += " " + get_option(properties, "categoryName", "category_name")
        kind = kind.lower()
        reason = ""
        if not re.search(r"\bмосква\b", norm) or "московская область" in norm:
            reason = "в карточке не подтверждён город Москва"
        elif not address_matches(user_input, actual):
            reason = "не совпадают улица, дом, корпус или строение"
        elif not re.search(r"многоквартир|\bмкд\b", kind):
            reason = "тип МКД не подтверждён полями карточки"
        elif re.search(r"\b(?:помещение|квартира|земельный участок)\b", kind):
            reason = "карточка отдельного помещения или участка"
        if reason:
            print(f"Пропуск {kad}: {actual or '(адрес отсутствует)'} — {reason}", flush=True)
        else:
            candidates[kad] = full
    if len(candidates) != 1:
        print(f"Подтверждённых МКД: {len(candidates)}. Нужен точный кадастровый номер или уточнение карточки.")
        return None
    return next(iter(candidates.values()))


def fetch_room_data(room_kad):
    try:
        time.sleep(random.uniform(ROOM_PAUSE_MIN, ROOM_PAUSE_MAX))

        with Nspd() as nspd:
            room = call_with_retries(
                nspd.find,
                room_kad,
                label=f"поиск помещения {room_kad}",
            )

        if not room:
            return room_kad, [""] * 14

        options = getattr(getattr(room, "properties", None), "options", None)

        purpose = get_option(options, "purpose")
        area = get_option(
            options,
            "area",
            "build_record_area",
            "total_area",
        )
        floor = get_option(
            options,
            "floor",
            "floors",
            "floor_number",
        )
        floor = re.sub(r"[\[\]'\" ]", "", floor)

        ownership = get_option(
            options,
            "ownership_type",
            "right_type",
            "ownership",
        )

        room_number = get_option(
            options,
            "room_number",
            "flat_number",
            "number",
            "apartment",
            "room",
            "flat",
        )

        odi = "да" if "долев" in ownership.lower() else "нет"

        reg_date = get_option(
            options,
            "registration_date",
            "reg_date",
        )

        right_number = get_option(
            options,
            "right_number",
            "registration_number",
        )

        if reg_date and right_number:
            status = "Актуально с собственностью"
        else:
            status = "Актуально без собственности"

        build_year = get_option(
            options,
            "year_built",
            "build_year",
        )

        return room_kad, [
            purpose,
            floor,
            area,
            ownership,
            odi,
            room_number,
            ownership,
            reg_date,
            right_number,
            status,
            build_year,
            area,
            area,
            area,
        ]

    except Exception:
        return room_kad, [""] * 14


def load_cache(cache_file):
    try:
        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as file:
                return json.load(file)
    except Exception:
        pass

    return None


def save_cache(data, cache_file):
    temp_file = cache_file + ".tmp"

    try:
        with open(temp_file, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.flush()
            os.fsync(file.fileno())

        os.replace(temp_file, cache_file)
        return cache_file

    except PermissionError:
        backup_file = os.path.join(
            SCRIPT_DIR,
            f"cache_backup_{int(time.time())}.json",
        )

        with open(backup_file, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

        print(f"⚠️ Основной кэш занят.")
        print(f"💾 Резервный кэш сохранён: {backup_file}")
        return backup_file

    finally:
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except Exception:
            pass


def process_address(user_input):
    print("=" * 70)
    print("ПОИСК ПО КАДАСТРОВОМУ НОМЕРУ ИЛИ АДРЕСУ")
    print("=" * 70)

    if not user_input:
        return False

    safe_name = re.sub(r"[^0-9A-Za-zА-Яа-я_-]+", "_", user_input)
    cache_file = os.path.join(
        SCRIPT_DIR,
        f"cache_{safe_name}.json",
    )

    with Nspd() as nspd:
        building = find_building(nspd, user_input)

        if not building:
            print("❌ Здание по указанному запросу не найдено.")
            return False

        options = getattr(
            getattr(building, "properties", None),
            "options",
            None,
        )

        address = get_option(
            options,
            "readable_address",
            "address",
        ) or user_input

        building_kad = get_cadastral_number(building)
        # Old address-only caches may belong to a different city/building.
        cache_file = os.path.join(SCRIPT_DIR, f"cache_moscow_{building_kad.replace(':', '_')}.json")

        print(f"\n✅ Найдено здание: {address}")
        print(f"📌 Кадастровый номер: {building_kad or 'не определён'}")

        area = get_option(
            options,
            "build_record_area",
            "area",
            "total_area",
        )

        print(f"📐 Общая площадь здания: {area or 'не указана'} кв.м")

        if not building_kad:
            print("❌ Не удалось определить кадастровый номер здания.")
            print("Попробуйте уточнить адрес.")
            return False

        objects = call_with_retries(
            nspd.tab_objects_list,
            building,
            label="получение квартир дома",
        )

    rooms = objects.get("Помещения (список)", [])
    if not rooms:
        for key, value in objects.items():
            key_text = str(key).lower()
            if ("помещ" in key_text or "кварт" in key_text) and isinstance(value, list):
                rooms = value
                print(f"ℹ️ Использован раздел объектов: {key}")
                break

    if not rooms:
        print(f"ℹ️ Доступные разделы ответа: {', '.join(map(str, objects.keys()))}")
        print("❌ Помещения не найдены.")
        return False

    print(f"\n🏠 Всего помещений: {len(rooms)}")
    print(f"⚡ Загружаем данные в {MAX_WORKERS} потоков...\n")

    cached_data = load_cache(cache_file)

    if cached_data:
        print(f"✅ Используется кэш: {len(cached_data)} помещений")
        result_dict = cached_data
    else:
        result_dict = {}

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [
                executor.submit(fetch_room_data, room)
                for room in rooms
            ]

            completed = 0

            for future in as_completed(futures):
                room_kad, data = future.result()
                result_dict[room_kad] = data

                completed += 1

                if completed % 50 == 0 or completed == len(rooms):
                    print(
                        f"⏳ Обработано {completed} "
                        f"из {len(rooms)}..."
                    )

        saved_cache = save_cache(result_dict, cache_file)
        print(f"💾 Кэш сохранён: {saved_cache}")

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Помещения"

    headers = [
        "N п/п",
        "Кадастровый номер помещения",
        "Назначение помещения",
        "Номер этажа",
        "Площадь, м2",
        "Форма собственности",
        "ОДИ",
        "Номер помещения",
        "Тип собственности",
        "Дата права",
        "Номер права",
        "Статус",
        "Год постройки",
        "Кадастр МКД",
        "Площадь ПКК",
        "Площадь РР",
        "Площадь ГИС",
    ]

    sheet.append(headers)

    for cell in sheet[1]:
        cell.font = Font(bold=True)

    for number, room_kad in enumerate(rooms, 1):
        data = result_dict.get(room_kad, [""] * 14)

        sheet.append([
            number,
            room_kad,
            data[0],
            data[1],
            data[2],
            data[3],
            data[4],
            data[5],
            data[6],
            data[7],
            data[8],
            data[9],
            data[10],
            building_kad,
            data[11],
            data[12],
            data[13],
        ])

    for column in sheet.columns:
        max_length = 0
        column_letter = column[0].column_letter

        for cell in column:
            value = str(cell.value or "")
            max_length = max(max_length, len(value))

        sheet.column_dimensions[column_letter].width = min(
            max(max_length + 2, 10),
            35,
        )

    output_file = os.path.join(
        OUTPUT_DIR,
        f"rooms_{safe_name}.xlsx",
    )

    workbook.save(output_file)

    found_count = sum(
        1 for data in result_dict.values()
        if len(data) > 5 and data[5]
    )

    print("\n" + "=" * 70)
    print(f"✅ ГОТОВО! Обработано помещений: {len(rooms)}")
    print(f"📌 Найдено номеров помещений: {found_count}")
    print(f"📄 Excel сохранён: {output_file}")
    print("=" * 70)
    return True


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("Поиск объектов только в Москве")
    print("Введите адрес или кадастровый номер здания.")
    user_input = input("Запрос: ").strip()
    if not user_input:
        print("❌ Запрос не введён.")
        return
    process_address(user_input)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("\n❌ КРИТИЧЕСКАЯ ОШИБКА:")
        traceback.print_exc()

    pause_exit()
