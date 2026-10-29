"""Preflight, official Dart validation and reproducible .chatgal packaging."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile
import zipfile

from common import inside, load_jsonc, write_json
from upstream import SKILL, compare, snapshot


def collect(source, lock):
    files, documents = {}, {}
    media = set(lock['reviewedCapabilities']['packageMediaExtensions'])
    for path in sorted(source.rglob('*')):
        if path.is_symlink(): raise ValueError('Symlinks are not packaged')
        if not path.is_file(): continue
        rel = path.relative_to(source).as_posix()
        if any(part.startswith('.') for part in Path(rel).parts): continue
        if rel not in {'manifest.json','home.png'} and Path(rel).parts[0] not in {'characters','stories','events'}:
            raise ValueError(f'Authoring attachments/settings do not belong inside pack/: {rel}')
        if path.suffix.lower() not in {'.json',*media}: raise ValueError(f'Unreviewed media type: {rel}')
        if path.suffix.lower() == '.json':
            if rel.startswith('stories/') and len(Path(rel).parts) != 2:
                raise ValueError('Story JSON must be flat under stories/')
            value = load_jsonc(path)
            if not isinstance(value,dict): raise ValueError('Expected JSON object: '+rel)
            role = ('manifest' if rel == 'manifest.json' else 'character' if rel.startswith('characters/') and rel.endswith('/character.json') else
                    'scene' if rel.startswith('stories/') else 'event' if rel.startswith('events/') and rel.endswith('/event.json') else None)
            if role is None: raise ValueError('Unknown runtime JSON location: '+rel)
            unknown = set(value) - set(lock['topLevelFields'][role])
            if unknown: raise ValueError(f'Fields outside reviewed {role} contract: {sorted(unknown)}')
            documents[rel] = value
        files[rel] = path.read_bytes()
    if 'manifest.json' not in documents or 'stories/start.json' not in documents:
        raise ValueError('manifest.json and stories/start.json are required')
    return files, documents


def media_requirements(documents):
    # home.png is optional in the engine (theme fallback). A generated asset
    # plan may still require it for a particular authored work.
    required = set()
    for rel, value in documents.items():
        parent = Path(rel).parent.as_posix()
        if rel.startswith('characters/'):
            required.update(parent + f'/{state}_{emotion}.png' for state in value.get('states',[]) for emotion in value.get('emotions',[]))
        elif rel.startswith('stories/') and value.get('background'):
            required.add('stories/' + value['background'])
        elif rel.startswith('events/'):
            required.update(parent + '/' + slide['image'] for slide in value.get('slides',[]) if slide.get('image'))
    return required


def verify_pngs(files):
    try:
        from PIL import Image
    except ImportError:
        Image = None
    import io
    checked = 0
    for name, data in files.items():
        if not name.lower().endswith('.png'): continue
        checked += 1
        if len(data) < 33 or data[:8] != b'\x89PNG\r\n\x1a\n' or data[12:16] != b'IHDR':
            raise ValueError('Not an actual PNG: '+name)
        width,height = struct.unpack('>II',data[16:24])
        if width <= 0 or height <= 0 or b'IEND' not in data[-16:]: raise ValueError('Invalid PNG dimensions/trailer: '+name)
        if Image:
            with Image.open(io.BytesIO(data)) as image: image.verify()
    return {'status':'passed' if checked else 'not-checked', 'checkedImages':checked,
            'method':('pillow-decode' if Image else 'png-signature-and-header-only') if checked else None}


def build(source, output, project=None, lock_path=None, draft=False, previous=None, dart=None):
    source, output = Path(source).resolve(), Path(output).resolve()
    lock = json.loads(Path(lock_path or SKILL/'compatibility.lock.json').read_text(encoding='utf-8'))
    if not source.is_dir(): raise ValueError('Source pack directory does not exist')
    if output.is_relative_to(source): raise ValueError('Output must be outside source pack')
    if output.exists(): raise ValueError('Use a new output filename; existing releases are not overwritten')
    if draft and not output.name.endswith('.draft.zip'): raise ValueError('Draft output must end with .draft.zip')
    if not draft and output.suffix != '.chatgal': raise ValueError('Validated output must end with .chatgal')
    files, docs = collect(source,lock)
    manifest = docs['manifest.json']
    if not isinstance(manifest.get('version'),str) or not re.fullmatch('[0-9]+',manifest['version']): raise ValueError('Version must be a numeric string')
    required = media_requirements(docs)
    plan_path = source.parent/'asset-plan.json'
    if plan_path.is_file():
        required.update(item['path'] for item in load_jsonc(plan_path)['assets'])
    missing = sorted(required - files.keys())
    if missing and not draft: raise ValueError('Missing images: '+', '.join(missing))
    for reference in required: inside(source,reference)
    media_check = verify_pngs(files)
    limits = lock['installLimits']
    if len(files) > limits['maxEntries'] or sum(map(len,files.values())) > limits['maxExtractedBytes']:
        raise ValueError('Package exceeds reviewed install limits')
    if any(len(data)>limits['maxJsonBytes'] for name,data in files.items() if name.endswith('.json')):
        raise ValueError('JSON exceeds reviewed install limit')
    if previous:
        with zipfile.ZipFile(previous) as old:
            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp)/'manifest.json'
                path.write_bytes(old.read('manifest.json'))
                prior = load_jsonc(path)
            if prior['packageId'] != manifest['packageId']: raise ValueError('Previous package identity differs')
            if int(manifest['version']) < int(prior['version']): raise ValueError('Package version cannot decrease')
            if int(manifest['version']) == int(prior['version']) and {name:old.read(name) for name in old.namelist()} != files:
                raise ValueError('Changed content requires a higher package version')
    validation = {'validated':False,'reason':'explicit draft','missingImages':missing}
    if not draft:
        if not project: raise ValueError('A target ChatGal checkout is required for authoritative validation')
        actual = snapshot(project)
        result = compare(lock,actual)
        if not result['compatibleWithReviewedBaseline']:
            raise ValueError('Target contract drift requires review; run upstream.py check. No final package written.')
        project = Path(project).resolve()
        for folder,key in [('default_v2','defaultPackageVersion'),('daily_v2','dailyPackageVersion')]:
            builtin = project/'content'/folder
            if not (builtin/'manifest.json').exists(): continue
            builtin_manifest = load_jsonc(builtin/'manifest.json')
            if source != builtin.resolve() and manifest['packageId'] == builtin_manifest['packageId']:
                raise ValueError('Do not reuse a built-in packageId for an independent pack')
            if source == builtin.resolve():
                if manifest['version'] != actual['builtinPackageVersions'][key]: raise ValueError('Built-in version must match AppServices constant')
                if folder == 'default_v2':
                    rebuild = (project/'tools/rebuild_default_v2_demo.py').read_text(encoding='utf-8')
                    if re.search(r'^VERSION\s*=\s*"([^"]+)"',rebuild,re.M).group(1) != manifest['version']:
                        raise ValueError('Built-in default rebuild VERSION must also match')
        executable = dart or shutil.which('dart')
        if not executable: raise ValueError('Dart is unavailable; source remains a draft. Do not claim runtime validation.')
        run = subprocess.run([executable,'run','tool/validate_pack.dart',str(source)],cwd=project/'packages/gal_protocol',capture_output=True,text=True,encoding='utf-8',timeout=120)
        if run.returncode: raise ValueError('Official PackageValidator failed:\n'+run.stdout+run.stderr)
        validation = {'validated':True,'tool':'ChatGal PackageLoader + PackageValidator','output':run.stdout.strip(),
                      'appVersion':actual['appVersion'],'upstreamCommit':actual['upstreamCommit'],'contractFingerprint':actual['contractFingerprint']}
    output.parent.mkdir(parents=True,exist_ok=True)
    # Build in a temporary sibling; failed checks never leave a misleading release.
    with tempfile.TemporaryDirectory(dir=output.parent) as temp:
        archive_path=Path(temp)/'package.zip'
        with zipfile.ZipFile(archive_path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
            for name,data in sorted(files.items()):
                info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.create_system=3;info.external_attr=0o644<<16
                archive.writestr(info,data)
        if archive_path.stat().st_size > limits['maxZipBytes']: raise ValueError('Compressed package exceeds install limit')
        with zipfile.ZipFile(archive_path) as archive:
            if archive.testzip() or {name:archive.read(name) for name in archive.namelist()} != files:
                raise ValueError('Archive round-trip mismatch')
        archive_path.replace(output)
    report={'packageId':manifest['packageId'],'version':manifest['version'],'status':'draft' if draft else 'runtime-validated',
            'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'bytes':output.stat().st_size,'entries':len(files),
            'mediaVerification':media_check,'runtimeValidation':validation,'liveModelAndVisualQA':'not performed by this script'}
    write_json(output.with_name(output.name+'.report.json'),report)
    return report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',required=True);parser.add_argument('--output',required=True)
    parser.add_argument('--project');parser.add_argument('--lock');parser.add_argument('--previous');parser.add_argument('--dart')
    parser.add_argument('--draft',action='store_true')
    args=parser.parse_args()
    report=build(args.source,args.output,args.project,args.lock,args.draft,args.previous,args.dart)
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
