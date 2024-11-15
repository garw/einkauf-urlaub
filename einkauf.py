#!/sbin/env python
import csv
import sys
from collections import defaultdict
import locale
import itertools

from rapidfuzz import fuzz
import inquirer
import json

locale.setlocale(locale.LC_ALL, 'de_DE.utf-8')

VALID_UNITS = {"g", "kg", "ml", "L", "Stück", "VE", "Pott"}

shopping_items = defaultdict(lambda: {unit: 0 for unit in VALID_UNITS})
try:
    with open("einkauf.db", "r") as f:
        data = json.load(f)
except FileNotFoundError:
    data = {}

items_per_section = defaultdict(list)
if "items_per_section" in data:
    for sec in data["items_per_section"]:
        items_per_section[sec] = data["items_per_section"][sec]
item_equivalence = {}
if "equivalence" in data:
    item_equivalence = data["equivalence"]


def write_einkaufdb(items_per_section, equivalence):
    db_data = {
        "items_per_section": items_per_section,
        "equivalence": equivalence
    }
    with open("einkauf.db", "w") as f:
        json.dump(db_data, f)

def pretty_print_amounts(amounts):
    to_be_printed = list(VALID_UNITS)
    output = ""
    for unit in to_be_printed:
        if amounts[unit] > 0:
            if output:
                output += " + "
            output += f"{amounts[unit]}{unit}"
    return output

def load_sections(sec_path):
    sections = {}
    with open(sec_path, "r") as f:
        reader = csv.reader(f)
        for line in reader:
            if line[1] in sections:
                print(f"ERROR: Key {line[1]} used for {line[0]} was already assigned to {sections[line[1]]}")
                sys.exit(-1)
            sections[line[1]] = line[0]

    return sections

def check_match(products, new_product):
    potential_matches = []
    for product in products:
        if fuzz.ratio(product, new_product) > 85:
            potential_matches.append(product)

    return potential_matches

def check_equivalence(new_product, products, equivalences):
    if new_product in equivalences:
        return equivalences[new_product]
    potential_matches = check_match(products, new_product)
    if potential_matches:
        potential_matches.append("Do not merge.")
        questions = [
            inquirer.List(
                "match",
                message=f"Do you want to merge *{new_product}* with one of the following?",
                choices=potential_matches
            )
        ]
        answers = inquirer.prompt(questions)
        if answers["match"] != "Do not merge.":
            equivalences[new_product] = answers["match"]
            return answers["match"]
        else:
            return new_product
    else:
        return new_product

def select_section(product, sections):
    while True:
        res = input(f"In which category is {product}? [? for list]").strip()
        if res == "?":
            section_info = [f"{name} [{short}]" for short, name in sections.items()]
            print("\n".join(section_info))
        if res in sections:
            return sections[res]

with open(sys.argv[1], "r") as f:
    reader = csv.reader(f)
    for line in reader:
        ignore = line[0]
        item = line[1].strip()
        unit = line[3]
        if ignore == "1" or not item or unit not in VALID_UNITS:
            continue
        normalized_amount = line[2].replace(",", ".")
        try:
            amount = float(normalized_amount)
        except ValueError:
            print(f"WARN: {item} with amount {line[2]} is invalid and ignored")
            continue
        if unit == "kg":
            amount *= 1000
            unit = "g"
        if unit == "L":
            amount *= 1000
            unit = "ml"

        if item not in shopping_items:
            item = check_equivalence(item, shopping_items.keys(), item_equivalence)

        shopping_items[item][unit] += amount

sections = load_sections("sections.csv")
for item in shopping_items.keys():
    if item not in itertools.chain.from_iterable(items_per_section.values()):
        sec = select_section(item, sections)
        items_per_section[sec].append(item)

write_einkaufdb(items_per_section, item_equivalence)

for section, section_items in items_per_section.items():
    section_items = {k: v for k,v in shopping_items.items() if k in section_items}
    print(f"\n* {section}:")
    for item, amounts in sorted(section_items.items(), key=lambda x: locale.strxfrm(x[0])):
        print(f"{item}: {pretty_print_amounts(amounts)}")
