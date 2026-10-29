"""Maintain one upstream-drift issue using the workflow's scoped GH_TOKEN."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

TITLE='[compatibility] ChatGal upstream changed — review skill capabilities'


def gh(*args):
    return subprocess.run(['gh',*args],check=True,capture_output=True,text=True,encoding='utf-8').stdout


def main():
    report=json.loads(Path('compatibility-report.json').read_text(encoding='utf-8'))
    repo=os.environ['GITHUB_REPOSITORY']
    issues=json.loads(gh('issue','list','--repo',repo,'--state','open','--limit','100','--json','number,title'))
    existing=next((issue for issue in issues if issue['title']==TITLE),None)
    if report['compatibleWithReviewedBaseline']:
        if existing:gh('issue','close',str(existing['number']),'--repo',repo)
        return
    body=('The upstream contract differs from the reviewed baseline. This is a maintenance task, not an automatic claim of support.\n\n'
          'Review parser/schema, validator, resource loading, renderer and lifecycle. Update capability references, templates, media rules, tests, version notes and compatibility.lock.json together. In particular, TTS/UI transitions do not establish package BGM/animation support.\n\n'
          '```json\n'+json.dumps(report,ensure_ascii=False,indent=2)+'\n```\n')
    with tempfile.TemporaryDirectory() as temp:
        path=Path(temp)/'body.md';path.write_text(body,encoding='utf-8')
        if existing:gh('issue','edit',str(existing['number']),'--repo',repo,'--body-file',str(path))
        else:gh('issue','create','--repo',repo,'--title',TITLE,'--body-file',str(path))


if __name__=='__main__':main()
