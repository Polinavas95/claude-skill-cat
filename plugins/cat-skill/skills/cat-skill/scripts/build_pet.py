#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Собирает цифрового кота: проверяет cat.json и подставляет его в шаблон.

    python3 scripts/build_pet.py cat.json -o murzik.html
    python3 scripts/build_pet.py cat.json --check      # только проверка

На выходе один самодостаточный HTML-файл: ни сети, ни зависимостей.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parent / "assets" / "pet.template.html"

PATTERNS = {"solid", "tabby", "mackerel", "spotted", "tuxedo", "bicolor",
            "tortie", "calico", "point"}
FURS = {"short", "medium", "long", "hairless"}
FACES = {"round", "flat", "wedge"}
LEGS = {"short", "normal", "long"}
EARS = {"normal", "large", "folded", "tufted"}
TAILS = {"long", "fluffy", "short", "bobtail"}
BUILDS = {"slim", "normal", "chonky"}
EXTRAS = {"white_socks", "chest_spot", "white_muzzle", "white_tail_tip",
          "collar", "heterochromia", "notched_ear", "scar", "tan_points", "pirate_hat"}
# Готовые окрасы-«приметы», которые раскладываются на pattern + extras
PATTERN_PRESETS = {
    "whiskas": {"pattern": "mackerel", "extras": ["white_socks", "chest_spot", "white_muzzle"],
                "pattern_color": "#4a3324", "belly_color": "#f5f0e8"},
    "black_and_tan": {"pattern": "solid", "extras": ["tan_points"]},
}
PATTERN_ALIASES = {"вискас": "whiskas", "whiskas_tabby": "whiskas", "вискас-табби": "whiskas",
                   "подпалый": "black_and_tan", "с подпалинами": "black_and_tan",
                   "tan": "black_and_tan"}
TRAITS = ("energy", "curiosity", "boldness", "clinginess", "talkativeness", "loaf_bias")
PHRASE_KEYS = ("meow", "purr", "scared", "sleep", "eat", "annoyed")
HEX_RE = re.compile(r"^#?(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
TOP_LEVEL = {"name", "sex", "breed", "language", "scale", "speed_scale", "appearance",
             "personality", "phrases", "notes", "source"}

# Порода — это не отдельная картинка, а набор параметров. Пресет задаёт значения
# по умолчанию; всё, что указано в appearance явно, важнее пресета.
BREEDS = {
    "sphynx": {"fur": "hairless", "ear_style": "large", "build": "slim",
               "face": "wedge", "leg_length": "long", "tail": "long"},
    "british": {"fur": "short", "build": "chonky", "face": "flat", "tail": "long"},
    "persian": {"fur": "long", "build": "chonky", "face": "flat", "tail": "fluffy"},
    "siamese": {"fur": "short", "build": "slim", "face": "wedge",
                "ear_style": "large", "pattern": "point", "tail": "long"},
    "maine_coon": {"fur": "long", "build": "chonky", "tail": "fluffy",
                   "ear_style": "tufted", "face": "wedge"},
    "norwegian": {"fur": "long", "build": "chonky", "tail": "fluffy", "ear_style": "tufted"},
    "ragdoll": {"fur": "long", "build": "chonky", "tail": "fluffy", "pattern": "point"},
    "munchkin": {"leg_length": "short", "fur": "short", "build": "normal"},
    "scottish_fold": {"ear_style": "folded", "fur": "short", "build": "chonky", "face": "flat"},
    "bengal": {"pattern": "spotted", "fur": "short", "build": "normal", "leg_length": "long"},
    "abyssinian": {"fur": "short", "build": "slim", "ear_style": "large",
                   "face": "wedge", "leg_length": "long"},
    "oriental": {"fur": "short", "build": "slim", "ear_style": "large",
                 "face": "wedge", "leg_length": "long"},
    "russian_blue": {"fur": "short", "build": "slim", "face": "wedge"},
    "manx": {"tail": "bobtail", "fur": "medium", "build": "chonky"},
    "bobtail": {"tail": "short", "fur": "medium", "build": "normal"},
    "devon_rex": {"fur": "short", "build": "slim", "face": "wedge", "ear_style": "large",
                  "leg_length": "long"},
    "cornish_rex": {"fur": "short", "build": "slim", "face": "wedge", "ear_style": "large",
                    "leg_length": "long"},
    "burmese": {"fur": "short", "build": "normal", "face": "round"},
    "siberian": {"fur": "long", "build": "chonky", "tail": "fluffy", "ear_style": "tufted"},
    "turkish_angora": {"fur": "long", "build": "slim", "tail": "fluffy", "face": "wedge",
                       "ear_style": "large"},
    "chartreux": {"fur": "short", "build": "chonky", "face": "round"},
    "exotic": {"fur": "short", "build": "chonky", "face": "flat"},
    "himalayan": {"fur": "long", "build": "chonky", "face": "flat", "tail": "fluffy",
                  "pattern": "point"},
    "birman": {"fur": "long", "build": "normal", "tail": "fluffy", "pattern": "point"},
    "snowshoe": {"fur": "short", "build": "normal", "pattern": "point"},
    "egyptian_mau": {"fur": "short", "build": "slim", "pattern": "spotted", "leg_length": "long"},
    "savannah": {"fur": "short", "build": "slim", "pattern": "spotted", "leg_length": "long",
                 "ear_style": "large", "face": "wedge"},
    "bombay": {"fur": "short", "build": "normal", "pattern": "solid", "face": "round"},
    "toyger": {"fur": "short", "build": "normal", "pattern": "mackerel"},
    "american_shorthair": {"fur": "short", "build": "normal", "face": "round"},
    "nebelung": {"fur": "long", "build": "slim", "tail": "fluffy", "face": "wedge"},
    "somali": {"fur": "long", "build": "slim", "tail": "fluffy", "ear_style": "large",
               "face": "wedge"},
    "balinese": {"fur": "long", "build": "slim", "face": "wedge", "ear_style": "large",
                 "pattern": "point", "tail": "fluffy"},
    "tonkinese": {"fur": "short", "build": "slim", "pattern": "point"},
    "turkish_van": {"fur": "medium", "build": "normal", "tail": "fluffy", "pattern": "bicolor"},
    "mixed": {},
}
BREED_ALIASES = {
    "сфинкс": "sphynx", "канадский сфинкс": "sphynx", "донской сфинкс": "sphynx",
    "лысый": "sphynx", "бесшёрстный": "sphynx", "бесшерстный": "sphynx",
    "британец": "british", "британская": "british", "британская короткошёрстная": "british",
    "перс": "persian", "персидская": "persian", "персидский": "persian",
    "сиамец": "siamese", "сиамская": "siamese", "сиамский": "siamese", "тайская": "siamese",
    "мейн-кун": "maine_coon", "мейнкун": "maine_coon", "кун": "maine_coon",
    "норвежская лесная": "norwegian", "норвежская": "norwegian",
    "рэгдолл": "ragdoll", "регдолл": "ragdoll",
    "манчкин": "munchkin", "коротконогий": "munchkin",
    "скоттиш-фолд": "scottish_fold", "вислоухая": "scottish_fold",
    "вислоухий": "scottish_fold", "шотландская вислоухая": "scottish_fold",
    "бенгальская": "bengal", "бенгал": "bengal",
    "абиссинская": "abyssinian", "абиссинец": "abyssinian",
    "ориентальная": "oriental", "ориентал": "oriental",
    "русская голубая": "russian_blue",
    "мэнкс": "manx", "манкс": "manx", "бесхвостая": "manx",
    "курильский бобтейл": "bobtail", "бобтейл": "bobtail",
    "девон-рекс": "devon_rex", "девон рекс": "devon_rex", "девон": "devon_rex",
    "корниш-рекс": "cornish_rex", "корниш рекс": "cornish_rex", "корниш": "cornish_rex",
    "бурма": "burmese", "бурманская": "burmese", "бурманский": "burmese",
    "сибирская": "siberian", "сибирский": "siberian", "сибиряк": "siberian",
    "турецкая ангора": "turkish_angora", "ангора": "turkish_angora", "ангорская": "turkish_angora",
    "шартрез": "chartreux", "картезианская": "chartreux",
    "экзот": "exotic", "экзотическая": "exotic", "экзотическая короткошёрстная": "exotic",
    "гималайская": "himalayan", "гималаец": "himalayan",
    "бирма": "birman", "бирманская": "birman", "священная бирма": "birman",
    "сноу-шу": "snowshoe", "сноушу": "snowshoe",
    "египетская мау": "egyptian_mau", "мау": "egyptian_mau",
    "саванна": "savannah",
    "бомбей": "bombay", "бомбейская": "bombay",
    "тойгер": "toyger",
    "американская короткошёрстная": "american_shorthair", "американка": "american_shorthair",
    "нибелунг": "nebelung",
    "сомали": "somali", "сомалийская": "somali",
    "балинез": "balinese", "балинезийская": "balinese",
    "тонкинез": "tonkinese", "тонкинская": "tonkinese",
    "турецкий ван": "turkish_van", "ван": "turkish_van",
    "дворовый": "mixed", "дворовая": "mixed", "метис": "mixed",
    "домашняя": "mixed", "без породы": "mixed", "беспородный": "mixed",
}


def resolve_breed(value):
    """Возвращает (ключ породы, пресет) или (None, {}) если порода не распознана."""
    key = str(value).strip().lower().replace("_", " ")
    key = BREED_ALIASES.get(key, key.replace(" ", "_"))
    if key in BREEDS:
        return key, dict(BREEDS[key])
    return None, {}


def norm_hex(value: str) -> str:
    value = str(value).strip()
    if not value.startswith("#"):
        value = "#" + value
    if len(value) == 4:
        value = "#" + "".join(ch * 2 for ch in value[1:])
    return value.lower()


def validate(raw):
    """Возвращает (спецификация, ошибки, замечания). Дефолты подставляет сама."""
    errors, warns = [], []
    if not isinstance(raw, dict):
        return {}, ["cat.json должен быть объектом {...}"], []

    spec = {k: v for k, v in raw.items() if v is not None}

    name = str(spec.get("name") or "").strip()
    if not name:
        errors.append("нет поля 'name' — питомцу нужно имя")
    spec["name"] = name or "Кот"

    sex = str(spec.get("sex", "male")).lower()
    if sex not in {"male", "female"}:
        errors.append(f"'sex'={sex!r} — допустимо male или female")
    spec["sex"] = sex

    lang = str(spec.get("language", "ru")).lower()
    spec["language"] = "en" if lang.startswith("en") else "ru"

    for key, lo, hi, default in (("scale", 0.5, 2.0, 1.0), ("speed_scale", 0.3, 2.0, 1.0)):
        try:
            value = float(spec.get(key, default))
        except (TypeError, ValueError):
            errors.append(f"'{key}' должно быть числом")
            continue
        if not lo <= value <= hi:
            warns.append(f"'{key}'={value} вне {lo}-{hi}, подрезано")
            value = min(hi, max(lo, value))
        spec[key] = round(value, 3)

    app = dict(spec.get("appearance") or {})
    if not isinstance(spec.get("appearance", {}), dict):
        errors.append("'appearance' должно быть объектом {...}")
        app = {}
    app = {k: v for k, v in app.items() if v is not None}

    if spec.get("breed"):
        key, preset = resolve_breed(spec["breed"])
        if key is None:
            warns.append(f"порода '{spec['breed']}' не в таблице — параметры берутся "
                         "только из appearance; см. references/pet-spec.md")
        else:
            spec["breed"] = key
            applied = {k: v for k, v in preset.items() if k not in app}
            app.update(applied)
            if applied:
                warns.append("порода " + key + " задала: "
                             + ", ".join(f"{k}={v}" for k, v in sorted(applied.items())))
    pat_raw = str(app.get("pattern", "")).strip().lower()
    pat_key = PATTERN_ALIASES.get(pat_raw, pat_raw)
    if pat_key in PATTERN_PRESETS:
        preset = PATTERN_PRESETS[pat_key]
        app["pattern"] = preset["pattern"]
        extras_list = list(app.get("extras") or [])
        for item in preset.get("extras", []):
            if item not in [str(x).lower() for x in extras_list]:
                extras_list.append(item)
        app["extras"] = extras_list
        for key in ("pattern_color", "belly_color"):
            if key in preset and not app.get(key):
                app[key] = preset[key]
        warns.append(f"окрас '{pat_raw}' разложен на pattern={preset['pattern']}, "
                     f"extras={', '.join(preset.get('extras', []))}")
    if not app.get("base_color"):
        errors.append("нет 'appearance.base_color' — основной цвет шерсти обязателен")
    for key in ("base_color", "pattern_color", "belly_color", "eye_color", "eye_color2",
                "nose_color", "inner_ear_color", "collar_color", "tan_color"):
        if key in app:
            if not HEX_RE.match(str(app[key])):
                errors.append(f"'appearance.{key}'={app[key]!r} не похоже на цвет #rrggbb")
            else:
                app[key] = norm_hex(app[key])

    def enum(field, allowed, default):
        value = str(app.get(field, default)).lower()
        if value not in allowed:
            errors.append(f"'appearance.{field}'={value!r} — допустимо: {', '.join(sorted(allowed))}")
        app[field] = value

    enum("pattern", PATTERNS, "tabby")
    enum("fur", FURS, "short")
    enum("ear_style", EARS, "normal")
    enum("tail", TAILS, "long")
    enum("build", BUILDS, "normal")
    enum("face", FACES, "round")
    enum("leg_length", LEGS, "normal")

    extras = app.get("extras", [])
    if not isinstance(extras, list):
        errors.append("'appearance.extras' должно быть списком")
        extras = []
    clean = []
    for item in extras:
        low = str(item).lower()
        if low in EXTRAS:
            clean.append(low)
        else:
            warns.append(f"деталь '{item}' неизвестна — пропущена "
                         f"(есть: {', '.join(sorted(EXTRAS))})")
    app["extras"] = clean
    if "collar" in clean and not app.get("collar_color"):
        app["collar_color"] = "#c0392b"
        warns.append("есть ошейник без 'collar_color' — взят красный")
    if "heterochromia" in clean and not app.get("eye_color2"):
        app["eye_color2"] = "#8fc7e8"
        warns.append("разноглазие без 'eye_color2' — второй глаз голубой")
    if "tan_points" in clean and not app.get("tan_color"):
        warns.append("подпалины без 'tan_color' — цвет выведен из основного (рыжеватый)")
    if app.get("pattern") in {"tabby", "mackerel", "spotted", "tortie", "calico", "point"} \
            and not app.get("pattern_color"):
        warns.append(f"окрас {app['pattern']} без 'pattern_color' — "
                     "полосы/пятна будут просто темнее основного цвета")
    for unknown in set(app) - {
        "base_color", "pattern", "pattern_color", "belly_color", "eye_color", "nose_color",
        "inner_ear_color", "fur", "ear_style", "tail", "build", "extras", "collar_color",
        "face", "leg_length", "eye_color2", "tan_color",
    }:
        warns.append(f"поле 'appearance.{unknown}' движок не читает")
    spec["appearance"] = app

    pers = spec.get("personality") or {}
    if not isinstance(pers, dict):
        errors.append("'personality' должно быть объектом {...}")
        pers = {}
    out = {}
    for trait in TRAITS:
        value = pers.get(trait, 0.4 if trait == "boldness" else 0.5)
        try:
            value = float(value)
        except (TypeError, ValueError):
            errors.append(f"'personality.{trait}' должно быть числом 0..1")
            continue
        if not 0.0 <= value <= 1.0:
            warns.append(f"'personality.{trait}'={value} вне 0..1, подрезано")
            value = min(1.0, max(0.0, value))
        out[trait] = round(value, 3)
    for extra in set(pers) - set(TRAITS):
        warns.append(f"черта характера '{extra}' неизвестна — пропущена "
                     f"(есть: {', '.join(TRAITS)})")
    spec["personality"] = out

    phrases = spec.get("phrases") or {}
    if not isinstance(phrases, dict):
        errors.append("'phrases' должно быть объектом {...}")
        phrases = {}
    clean_phrases = {}
    for key, value in phrases.items():
        if key not in PHRASE_KEYS:
            warns.append(f"'phrases.{key}' движок не использует "
                         f"(есть: {', '.join(PHRASE_KEYS)})")
            continue
        if not isinstance(value, list) or not value:
            warns.append(f"'phrases.{key}' должно быть непустым списком строк — пропущено")
            continue
        strings = [str(x) for x in value]
        long_ones = [x for x in strings if len(x) > 10]
        if long_ones:
            warns.append(f"длинные фразы не влезут в пузырь: {', '.join(long_ones)}")
        clean_phrases[key] = strings
    if clean_phrases:
        spec["phrases"] = clean_phrases
    else:
        spec.pop("phrases", None)

    for unknown in set(spec) - TOP_LEVEL:
        warns.append(f"поле '{unknown}' движок не читает")

    return spec, errors, warns


def build(spec, out_path: Path) -> Path:
    if not TEMPLATE.exists():
        raise FileNotFoundError(f"не найден шаблон {TEMPLATE}")
    template = TEMPLATE.read_text(encoding="utf-8")
    payload = json.dumps(spec, ensure_ascii=False, indent=2).replace("</", "<\\/")
    html = template.replace("__CAT_SPEC__", payload).replace("__CAT_NAME__", spec["name"])
    if "__CAT_SPEC__" in html or "__CAT_NAME__" in html:
        raise RuntimeError("подстановка в шаблон не сработала")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return out_path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Сборка цифрового кота из описания")
    ap.add_argument("spec", help="путь к cat.json")
    ap.add_argument("-o", "--out", default=None, help="куда сохранить HTML")
    ap.add_argument("--check", action="store_true", help="только проверить описание")
    args = ap.parse_args(argv)

    path = Path(args.spec)
    if not path.exists():
        print(f"не найден файл: {path}", file=sys.stderr)
        return 2
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"{path}: некорректный JSON, строка {exc.lineno}: {exc.msg}", file=sys.stderr)
        return 2

    spec, errors, warns = validate(raw)
    for warn in warns:
        print(f"  замечание: {warn}")
    if errors:
        print("\nошибки в описании кота:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    app = spec["appearance"]
    print(f"описание корректно: {spec['name']}"
          + (f", порода {spec['breed']}" if spec.get("breed") else "")
          + f", {app['pattern']}, шерсть {app['fur']}, телосложение {app['build']}, "
          f"морда {app['face']}, лапы {app['leg_length']}, "
          f"{'кот' if spec['sex'] == 'male' else 'кошка'}")
    if args.check:
        return 0

    out = Path(args.out) if args.out else path.with_suffix(".html")
    build(spec, out)
    print(f"готово: {out.resolve()}")
    print("открыть в браузере — двойной клик по файлу")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
