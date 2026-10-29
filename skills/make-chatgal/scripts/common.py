"""Small JSONC/path/media helpers, not a second ChatGal validator."""
import json
from pathlib import Path
import re


def load_jsonc(path):
    text = Path(path).read_text(encoding='utf-8-sig')
    out, i, quoted, escaped = [], 0, False, False
    while i < len(text):
        ch = text[i]
        if quoted:
            out.append(ch)
            if escaped: escaped = False
            elif ch == '\\': escaped = True
            elif ch == '"': quoted = False
            i += 1
        elif ch == '"':
            quoted = True; out.append(ch); i += 1
        elif text[i:i+2] == '//':
            i = text.find('\n', i)
            if i < 0: break
        elif text[i:i+2] == '/*':
            end = text.find('*/', i + 2)
            if end < 0: raise ValueError('Unclosed JSONC comment')
            out.append(' '); i = end + 2
        else:
            out.append(ch); i += 1
    text = ''.join(out)
    out, i, quoted, escaped = [], 0, False, False
    while i < len(text):
        ch = text[i]
        if not quoted and ch == ',':
            j = i + 1
            while j < len(text) and text[j].isspace(): j += 1
            if j < len(text) and text[j] in '}]': i += 1; continue
        out.append(ch)
        if quoted:
            if escaped: escaped = False
            elif ch == '\\': escaped = True
            elif ch == '"': quoted = False
        elif ch == '"': quoted = True
        i += 1
    return json.loads(''.join(out))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def inside(root, relative):
    root = Path(root).resolve()
    relative = str(relative)
    if '\\' in relative or relative.startswith('/') or '..' in Path(relative).parts:
        raise ValueError(f'Unsafe relative path: {relative}')
    target = (root / relative).resolve()
    if not target.is_relative_to(root): raise ValueError(f'Path escapes output: {relative}')
    return target


def safe_name(value):
    value = str(value).strip()
    if not value or value in {'.', '..'} or re.search(r'[<>:"/\\|?*\x00-\x1f]', value) or value.endswith(('.', ' ')):
        raise ValueError(f'Unsafe filename component: {value!r}')
    if value.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}:
        raise ValueError(f'Reserved filename component: {value}')
    return value
