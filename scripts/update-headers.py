#!/usr/bin/env python3

import argparse
from pathlib import Path
import re
import sys
from typing import Any

import jinja2

KEYSYM_PATTERN = re.compile(
    r"^#define\s+XKB_KEY_(?P<name>\w+)\s+(?P<value>0x[0-9a-fA-F]+)\s"
)


def load_keysyms(path: Path) -> dict[str, int]:
    # Load the keysyms header
    keysym_min = sys.maxsize
    keysym_max = 0
    min_unicode_keysym = 0x01000100
    max_unicode_keysym = 0x0110FFFF
    canonical_names: dict[int, str] = {}
    max_unicode_name = "U10FFFF"
    max_keysym_name = "0x1fffffff"  # XKB_KEYSYM_MAX
    with path.open("rt", encoding="utf-8") as fd:
        for line in fd:
            if m := KEYSYM_PATTERN.match(line):
                value = int(m.group("value"), 16)
                keysym_min = min(keysym_min, value)
                keysym_max = max(keysym_max, value)
                if value not in canonical_names:
                    canonical_names[value] = m.group("name")
    return {
        "XKB_KEYSYM_MIN_ASSIGNED": min(keysym_min, min_unicode_keysym),
        "XKB_KEYSYM_MAX_ASSIGNED": max(keysym_max, max_unicode_keysym),
        "XKB_KEYSYM_MIN_EXPLICIT": keysym_min,
        "XKB_KEYSYM_MAX_EXPLICIT": keysym_max,
        "XKB_KEYSYM_COUNT_EXPLICIT": len(canonical_names),
        "XKB_KEYSYM_NAME_MAX_SIZE": max(
            max(len(name) for name in canonical_names.values()),
            len(max_unicode_name),
            len(max_keysym_name),
        ),
    }


def generate(
    env: jinja2.Environment,
    data: dict[str, Any],
    root: Path,
    file: Path,
):
    """Generate a file from its Jinja2 template"""
    template_path = file.with_suffix(f"{file.suffix}.jinja")
    template = env.get_template(str(template_path))
    path = root / file
    with path.open("wt", encoding="utf-8") as fd:
        fd.writelines(template.generate(**data))


# Root of the project
ROOT = Path(__file__).parent.parent

# Parse commands
parser = argparse.ArgumentParser(
    description="Generate C header files related to keysyms bounds"
)
parser.add_argument(
    "--root",
    type=Path,
    default=ROOT,
    help="Path to the root of the project (default: %(default)s)",
)

args = parser.parse_args()

# Configure Jinja
template_loader = jinja2.FileSystemLoader(args.root, encoding="utf-8")
jinja_env = jinja2.Environment(
    loader=template_loader,
    keep_trailing_newline=True,
    trim_blocks=True,
    lstrip_blocks=True,
)

jinja_env.filters["keysym"] = lambda ks: f"0x{ks:0>8x}"

# Load keysyms
keysyms_data = load_keysyms(args.root / "include/xkbcommon/xkbcommon-keysyms.h")

# Generate the files
generate(
    jinja_env,
    keysyms_data,
    args.root,
    Path("src/keysym.h"),
)
