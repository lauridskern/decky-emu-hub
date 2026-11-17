"""Small editors for emulator config files.

Each `*_set(text, updates)` returns the file with the named keys set and
every other line kept as it was (order, comments, unknown keys). Each
`*_get(text, ...)` reads one value back, for "is the Deck preset in place?".

Formats:
  ini   [Section] / key = value   PCSX2, DuckStation, Dolphin, PPSSPP, Azahar, Flycast
  toml  ini with typed values     xemu
  cfg   key = "value"             RetroArch
  json  top-level keys            Ryubing
  xml   children of the root      Cemu
  yaml  Section: / two-space keys RPCS3 (two levels only)
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

_SECTION = re.compile(r"^\s*\[([^\]]+)\]\s*$")


def _key_line(key: str) -> "re.Pattern[str]":
    return re.compile(r"^\s*" + re.escape(key) + r"\s*=")


def _sections(lines: List[str]) -> List[Tuple[str, int, int]]:
    """(name, first body line, end) for the top block ("") and each section."""
    heads = [(0, "", -1)]
    for i, line in enumerate(lines):
        m = _SECTION.match(line)
        if m:
            heads.append((i, m.group(1).strip(), i))
    out = []
    for n, (start, name, head) in enumerate(heads):
        end = heads[n + 1][0] if n + 1 < len(heads) else len(lines)
        out.append((name, head + 1 if head >= 0 else 0, end))
    return out


def _separator(lines: List[str]) -> str:
    for line in lines:
        if _SECTION.match(line) or line.strip().startswith(("#", ";")) or "=" not in line:
            continue
        return " = " if re.search(r"\s=\s", line) else "="
    return " = "


def ini_set(text: str, updates: Dict[str, Dict[str, str]], sep: Optional[str] = None) -> str:
    lines = text.splitlines()
    sep = sep or _separator(lines)
    for section, values in updates.items():
        block = next((b for b in _sections(lines) if b[0] == section), None)
        if block is None:
            while lines and not lines[-1].strip():
                lines.pop()
            if lines:
                lines.append("")
            lines.append(f"[{section}]")
            lines.extend(f"{k}{sep}{v}" for k, v in values.items())
            continue
        _, start, end = block
        missing = []
        for key, value in values.items():
            pattern = _key_line(key)
            hit = next((i for i in range(start, end) if pattern.match(lines[i])), None)
            if hit is None:
                missing.append(f"{key}{sep}{value}")
            else:
                lines[hit] = f"{key}{sep}{value}"
        if missing:
            insert = end
            while insert > start and not lines[insert - 1].strip():
                insert -= 1
            lines[insert:insert] = missing
    return "\n".join(lines) + "\n"


def ini_get(text: str, section: str, key: str) -> Optional[str]:
    lines = text.splitlines()
    pattern = _key_line(key)
    for name, start, end in _sections(lines):
        if name != section:
            continue
        for i in range(start, end):
            if pattern.match(lines[i]):
                return lines[i].split("=", 1)[1].strip()
    return None


def toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value))


def toml_set(text: str, updates: Dict[str, Dict[str, Any]]) -> str:
    return ini_set(text, {s: {k: toml_value(v) for k, v in vals.items()} for s, vals in updates.items()}, sep=" = ")


def toml_get(text: str, section: str, key: str) -> Optional[str]:
    return ini_get(text, section, key)


def cfg_set(text: str, updates: Dict[str, str]) -> str:
    """RetroArch's retroarch.cfg: one `key = "value"` per line, no sections."""
    lines = text.splitlines()
    for key, value in updates.items():
        line = f'{key} = "{value}"'
        pattern = _key_line(key)
        hit = next((i for i, l in enumerate(lines) if pattern.match(l)), None)
        if hit is None:
            lines.append(line)
        else:
            lines[hit] = line
    return "\n".join(lines) + "\n"


def cfg_get(text: str, key: str) -> Optional[str]:
    pattern = _key_line(key)
    for line in text.splitlines():
        if pattern.match(line):
            return line.split("=", 1)[1].strip().strip('"')
    return None


def json_set(text: str, updates: Dict[str, Any]) -> str:
    data = json.loads(text) if text.strip() else {}
    if not isinstance(data, dict):
        raise ValueError("not a JSON object")
    for key, value in updates.items():
        if isinstance(value, list) and isinstance(data.get(key), list):
            # Lists (game folders) gain entries; the user's own stay.
            data[key] = data[key] + [item for item in value if item not in data[key]]
        else:
            data[key] = value
    return json.dumps(data, indent=2) + "\n"


def json_get(text: str, key: str) -> Any:
    try:
        data = json.loads(text)
    except ValueError:
        return None
    return data.get(key) if isinstance(data, dict) else None


# XML is edited with a small tokenizer instead of xml.etree: Decky Loader's
# bundled Python has no xml package (checked in PluginLoader v3.3.1), and an
# import of it stops the whole backend from loading. tests/test_imports.py
# keeps the backend on modules Decky ships. Only direct children of the root
# element are read or changed; every other byte of the file stays as it was.
_XML_TOKEN = re.compile(
    r"<!--.*?-->|<!\[CDATA\[.*?\]\]>|<\?.*?\?>|<![^>]*>"
    r"|<(/?)([A-Za-z_][\w.:-]*)(?:\s[^>]*?)?(/?)>",
    re.S,
)
_XML_ESCAPES = (("&", "&amp;"), ("<", "&lt;"), (">", "&gt;"))


def _xml_escape(value: str) -> str:
    for raw, escaped in _XML_ESCAPES:
        value = value.replace(raw, escaped)
    return value


def _xml_unescape(value: str) -> str:
    value = value.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&apos;", "'")
    return value.replace("&amp;", "&")


def _xml_children(text: str) -> Tuple[Tuple[str, int, int], Dict[str, List[Tuple[int, int, Optional[int], Optional[int]]]]]:
    """The root element (name, inner start, inner end) and its direct children:
    tag -> [(start, end, inner start, inner end)], inner None when self-closing."""
    stack: List[Tuple[str, "re.Match[str]"]] = []
    children: Dict[str, List[Tuple[int, int, Optional[int], Optional[int]]]] = {}
    for match in _XML_TOKEN.finditer(text):
        name = match.group(2)
        if name is None:
            continue
        if match.group(1) == "/":
            if not stack or stack[-1][0] != name:
                raise ValueError(f"unbalanced </{name}>")
            _, opened = stack.pop()
            if len(stack) == 1:
                children.setdefault(name, []).append((opened.start(), match.end(), opened.end(), match.start()))
            elif not stack:
                return (name, opened.end(), match.start()), children
        elif match.group(3) == "/":
            if len(stack) == 1:
                children.setdefault(name, []).append((match.start(), match.end(), None, None))
            elif not stack:
                raise ValueError("empty root element")
        else:
            stack.append((name, match))
    raise ValueError("no root element")


def _xml_entries(inner: str) -> List[str]:
    return [_xml_unescape(v) for v in re.findall(r"<Entry>(.*?)</Entry>", inner, re.S)]


def xml_set(text: str, updates: Dict[str, Any], root_tag: str = "content") -> str:
    """Set children of the root element. A list value means one <Entry> per item
    (Cemu's <GamePaths>); entries already there are kept."""
    if not text.strip():
        text = f'<?xml version="1.0" encoding="UTF-8"?>\n<{root_tag}>\n</{root_tag}>\n'
    for tag, value in updates.items():
        (_, _, root_end), children = _xml_children(text)
        found = children.get(tag, [None])[0]
        if isinstance(value, list):
            have = _xml_entries(text[found[2]:found[3]]) if found and found[2] is not None else []
            missing = "".join(f"\t\t<Entry>{_xml_escape(str(v))}</Entry>\n" for v in value if str(v) not in have)
            if found and found[2] is not None:
                if missing:
                    # New entries go before the closing tag's indentation.
                    inner = text[found[2]:found[3]]
                    at = found[3] - (len(inner) - len(inner.rstrip(" \t")))
                    if not text[:at].endswith("\n"):
                        missing = "\n" + missing
                    text = text[:at] + missing + text[at:]
                continue
            block = f"<{tag}>\n{missing}\t</{tag}>"
        else:
            block = f"<{tag}>{_xml_escape(str(value))}</{tag}>"
            if found and found[2] is not None:
                text = text[:found[2]] + _xml_escape(str(value)) + text[found[3]:]
                continue
        if found:  # self-closing: replace it
            text = text[:found[0]] + block + text[found[1]:]
        else:
            before = text[:root_end]
            sep = "" if before.endswith("\n") else "\n"
            text = before + sep + "\t" + block + "\n" + text[root_end:]
    return text


def xml_get(text: str, tag: str) -> Any:
    try:
        _, children = _xml_children(text)
    except ValueError:
        return None
    found = children.get(tag)
    if not found:
        return None
    _, _, start, end = found[0]
    if start is None:
        return ""
    inner = text[start:end]
    if "<Entry>" in inner:
        return _xml_entries(inner)
    return "" if "<" in inner else _xml_unescape(inner)


def yaml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _yaml_block(lines: List[str], section: str) -> Optional[Tuple[int, int]]:
    head = next((i for i, l in enumerate(lines) if l.rstrip() == f"{section}:"), None)
    if head is None:
        return None
    end = head + 1
    while end < len(lines) and (not lines[end].strip() or lines[end][:1] in (" ", "\t")):
        end += 1
    return head + 1, end


def yaml_set(text: str, updates: Dict[str, Dict[str, Any]]) -> str:
    lines = text.splitlines()
    for section, values in updates.items():
        block = _yaml_block(lines, section)
        if block is None:
            lines.append(f"{section}:")
            lines.extend(f"  {k}: {yaml_scalar(v)}" for k, v in values.items())
            continue
        start, end = block
        indent = next((re.match(r"^(\s+)", lines[i]).group(1) for i in range(start, end)
                       if lines[i].strip() and re.match(r"^(\s+)", lines[i])), "  ")
        missing = []
        for key, value in values.items():
            pattern = re.compile("^" + re.escape(indent) + re.escape(key) + r":(\s|$)")
            hit = next((i for i in range(start, end) if pattern.match(lines[i])), None)
            line = f"{indent}{key}: {yaml_scalar(value)}"
            if hit is None:
                missing.append(line)
            else:
                lines[hit] = line
        insert = end
        while insert > start and not lines[insert - 1].strip():
            insert -= 1
        lines[insert:insert] = missing
    return "\n".join(lines) + "\n"


def yaml_get(text: str, section: str, key: str) -> Optional[str]:
    lines = text.splitlines()
    block = _yaml_block(lines, section)
    if block is None:
        return None
    for i in range(*block):
        m = re.match(r"^\s+" + re.escape(key) + r":\s*(.*)$", lines[i])
        if m:
            return m.group(1).strip()
    return None


def same(found: Any, wanted: Any) -> bool:
    """Loose equality for read-back values ("True" == true, quotes ignored)."""
    if isinstance(wanted, list):
        return isinstance(found, list) and all(item in found for item in wanted)
    norm = lambda v: str(v).strip().strip('"').lower() if v is not None else None  # noqa: E731
    return found is not None and norm(found) == norm(toml_value(wanted) if isinstance(wanted, bool) else wanted)
