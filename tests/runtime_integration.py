"""Official Dart validation + real runtime with explicitly test-only PNG tiles."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skills/make-chatgal/scripts'))
from init_pack import initialize
from build_pack import build
from test_tools import populate_test_art


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--project',required=True);args=parser.parse_args()
    project=Path(args.project).resolve()
    brief=json.loads((ROOT/'skills/make-chatgal/assets/example-brief.json').read_text(encoding='utf-8'))
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp)
        for template in ('daily','branching'):
            work=initialize(root/template,brief,template,'prompts');populate_test_art(work)
            report=build(work/'pack',root/(template+'.chatgal'),project)
            if not report['runtimeValidation']['validated']:raise RuntimeError('Official validation did not run')
            print(report['runtimeValidation']['output'])
        result=subprocess.run([shutil.which('dart'),'--packages='+str(project/'packages/gal_ai/.dart_tool/package_config.json'),
                  'run',str(ROOT/'tests/runtime_smoke.dart'),str(root/'daily/pack'),str(root/'branching/pack')],cwd=ROOT,check=False)
        if result.returncode:raise SystemExit(result.returncode)


if __name__=='__main__':main()
