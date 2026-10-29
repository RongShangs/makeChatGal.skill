"""Create an installable, reproducible skill ZIP; no credentials or QA outputs."""
import hashlib
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'skills/make-chatgal'


def main():
    out=ROOT/'dist/make-chatgal-0.1.0.zip';out.parent.mkdir(exist_ok=True)
    paths=[p for p in SOURCE.rglob('*') if p.is_file() and not any(part.startswith('.') or part=='__pycache__' for part in p.relative_to(SOURCE).parts)]
    for path in paths:
        if path.suffix in {'.py','.md','.json','.yaml'}:path.read_text(encoding='utf-8')
    assert (SOURCE/'SKILL.md') in paths and (SOURCE/'LICENSE') in paths
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for path in sorted(paths):
            name='make-chatgal/'+path.relative_to(SOURCE).as_posix()
            info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16
            data=path.read_bytes()
            if path.suffix in {'.py','.md','.json','.yaml','.yml','.txt','.svg'} or path.name=='LICENSE':
                data=data.replace(b'\r\n',b'\n')
            archive.writestr(info,data)
    with zipfile.ZipFile(out) as archive:assert archive.testzip() is None
    print(out)
    print('SHA256',hashlib.sha256(out.read_bytes()).hexdigest())


if __name__=='__main__':main()
