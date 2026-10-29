"""Read-only contract audit and explicit reviewed-baseline capture (stdlib)."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

SKILL = Path(__file__).resolve().parents[1]
WATCH = [
    'apps/chatgal/pubspec.yaml', 'docs/AUTHOR_GUIDE.md', 'docs/BOUNDARY.md',
    'tools/rebuild_default_v2_demo.py', 'tools/pack_default_v2.py',
    'schemas/v2/*.json', 'packages/gal_protocol/lib/**/*.dart',
    'packages/gal_protocol/tool/validate_pack.dart',
    'packages/gal_ai/lib/**/*.dart', 'packages/gal_storage/lib/src/install*.dart',
    'packages/gal_storage/lib/src/package_installer.dart',
    'apps/chatgal/lib/app/app_services.dart',
    'apps/chatgal/lib/features/settings/*.dart',
    'apps/chatgal/lib/features/tts/*.dart',
    'apps/chatgal/lib/features/session/*.dart',
    'apps/chatgal/lib/features/studio/*.dart',
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return Path(path).read_text(encoding='utf-8-sig')


def schema_shapes(node, prefix=''):
    result = {}
    if isinstance(node, dict):
        if isinstance(node.get('properties'), dict):
            result[prefix or '/'] = sorted(node['properties'])
        for key, value in node.items():
            if isinstance(value, (dict, list)):
                result.update(schema_shapes(value, prefix + '/' + key))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            result.update(schema_shapes(value, prefix + '/' + str(index)))
    return result


def snapshot(project):
    project = Path(project).resolve()
    version_file = project / 'apps/chatgal/pubspec.yaml'
    if not version_file.is_file():
        raise ValueError('Not a ChatGal project root')
    paths = sorted({p for pattern in WATCH for p in project.glob(pattern) if p.is_file()})
    # All watched inputs are text. Git checkouts on Windows may use CRLF;
    # line-ending conversion must not look like a protocol change.
    hashes = {p.relative_to(project).as_posix(): sha(p.read_bytes().replace(b'\r\n', b'\n')) for p in paths}
    contracts = {}
    for path in sorted((project / 'schemas/v2').glob('*.json')):
        contracts[path.name] = schema_shapes(json.loads(read(path)))
    character = read(project / 'packages/gal_protocol/lib/src/models/character.dart')
    character_keys = sorted(set(re.findall(r"'([A-Za-z][A-Za-z0-9_]*)'\s*:", character.split('toJson()', 1)[-1])))
    fields = {name: contracts[file]['/'] for name, file in
              [('manifest', 'manifest.json'), ('scene', 'scene.json'), ('event', 'event.json')]}
    fields['character'] = character_keys
    app_version = re.search(r'^version:\s*([^\s#]+)', read(version_file), re.M).group(1)
    services = read(project / 'apps/chatgal/lib/app/app_services.dart')
    builtin = dict(re.findall(r"(defaultPackageVersion|dailyPackageVersion)\s*=\s*'([^']+)'", services))
    limits = {}
    limit_source = read(project / 'packages/gal_storage/lib/src/install_limits.dart')
    for key in ('maxZipBytes','maxExtractedBytes','maxEntries','maxJsonBytes'):
        match = re.search(r'this\.' + key + r'\s*=\s*([0-9][0-9 *]*)\s*[,)]', limit_source)
        if not match: raise ValueError('Review changed install-limit expression: ' + key)
        value = 1
        for factor in match.group(1).split('*'): value *= int(factor.strip())
        limits[key] = value
    git = subprocess.run(['git', '-C', str(project), 'rev-parse', 'HEAD'], capture_output=True, text=True)
    tracked = subprocess.run(['git', '-C', str(project), 'status', '--porcelain', '--untracked-files=no'], capture_output=True, text=True)
    catalog = SKILL / 'references/capabilities.json'
    return {'lockVersion': 1, 'skillVersion': '0.1.0',
            'upstreamRepository': 'https://github.com/RongShangs/ChatGal',
            'upstreamCommit': git.stdout.strip() if git.returncode == 0 else None,
            'trackedWorktreeDirty': bool(tracked.stdout.strip()) if tracked.returncode == 0 else None,
            'appVersion': app_version, 'contentFormat': 'flat-v2', 'builtinPackageVersions': builtin, 'installLimits': limits,
            'watchPatterns': WATCH, 'sourceHashes': hashes,
            'contractFingerprint': sha(json.dumps(hashes, sort_keys=True).encode()),
            'schemaShapes': contracts, 'topLevelFields': fields,
            'capabilityCatalogSha256': sha(catalog.read_bytes()),
            'reviewedCapabilities': json.loads(read(catalog))}


def compare(expected, actual):
    old, new = expected['sourceHashes'], actual['sourceHashes']
    changed = sorted(key for key in old.keys() | new.keys() if old.get(key) != new.get(key))
    additions = {}
    for role, fields in actual['topLevelFields'].items():
        extra = sorted(set(fields) - set(expected['topLevelFields'].get(role, [])))
        if extra:
            additions[role] = extra
    matches = not changed and expected['appVersion'] == actual['appVersion'] and expected['capabilityCatalogSha256'] == actual['capabilityCatalogSha256']
    media_hints = sorted({field for fields in additions.values() for field in fields
                          if re.search(r'audio|music|sound|bgm|sfx|anim|video|voice', field, re.I)})
    return {'compatibleWithReviewedBaseline': matches, 'baselineAppVersion': expected['appVersion'],
            'observedAppVersion': actual['appVersion'], 'observedCommit': actual['upstreamCommit'],
            'changedPaths': changed, 'newTopLevelFields': additions,
            'mediaCandidatesRequireRuntimeReview': media_hints,
            'note': 'Detected names are review candidates, not proof of playback support.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['check', 'capture'])
    parser.add_argument('--project', required=True)
    parser.add_argument('--lock', default=str(SKILL / 'compatibility.lock.json'))
    parser.add_argument('--output')
    parser.add_argument('--reviewed', action='store_true')
    args = parser.parse_args()
    actual = snapshot(args.project)
    if args.command == 'capture':
        if not args.reviewed:
            parser.error('Capture requires --reviewed after code/docs/examples/runtime review; not an automatic compatibility upgrade')
        target = Path(args.output or args.lock)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(actual, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print('Captured reviewed baseline:', actual['appVersion'], actual['upstreamCommit'])
        return
    report = compare(json.loads(read(args.lock)), actual)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if args.output:
        Path(args.output).write_text(text + '\n', encoding='utf-8')
    raise SystemExit(0 if report['compatibleWithReviewedBaseline'] else 3)


if __name__ == '__main__':
    main()
