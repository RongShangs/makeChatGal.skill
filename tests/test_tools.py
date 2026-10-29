import base64
import copy
import json
import os
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT/'skills/make-chatgal'
sys.path.insert(0,str(SKILL/'scripts'))
from common import inside, load_jsonc, write_json
from init_pack import initialize
from build_pack import build, media_requirements, collect
from upstream import compare, snapshot


def png_fixture():
    """Test-only 16px tile, never supplied as user artwork."""
    def chunk(kind,data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    data=b''.join(b'\0'+bytes([80,100,180,255])*16 for _ in range(16))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',16,16,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(data))+chunk(b'IEND',b'')


def populate_test_art(folder):
    plan=json.loads((folder/'asset-plan.json').read_text(encoding='utf-8'))
    for item in plan['assets']:
        target=inside(folder/'pack',item['path']);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(png_fixture())


class ToolTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.brief=json.loads((SKILL/'assets/example-brief.json').read_text(encoding='utf-8'))
        self.lock=json.loads((SKILL/'compatibility.lock.json').read_text(encoding='utf-8'))
    def tearDown(self): self.temp.cleanup()
    def create(self,mode='prompts',template='daily'):
        return initialize(self.root/'work',self.brief,template,mode)
    def test_prompts_mode_complete_plan_no_fake_art(self):
        work=self.create();plan=json.loads((work/'asset-plan.json').read_text(encoding='utf-8'))
        self.assertFalse(list((work/'pack').rglob('*.png')))
        files,docs=collect(work/'pack',self.lock)
        self.assertEqual({item['path'] for item in plan['assets']},media_requirements(docs)|{'home.png'})
        self.assertEqual(len(plan['assets']),len(list((work/'image-prompts').glob('*.txt'))))
        with self.assertRaisesRegex(ValueError,'Missing images'):
            build(work/'pack',self.root/'bad.chatgal')
        self.assertFalse((self.root/'bad.chatgal').exists())
    def test_generate_mode_does_not_falsely_claim_execution(self):
        work=self.create('generate');status=json.loads((work/'AUTHORING_STATUS.json').read_text(encoding='utf-8'))
        self.assertEqual(status['status'],'draft-needs-assets');self.assertFalse(status['runtimeValidated'])
        self.assertFalse(list((work/'pack').rglob('*.png')))
    def test_draft_label_and_reproducible_archive(self):
        work=self.create()
        first=build(work/'pack',self.root/'a.draft.zip',draft=True)
        second=build(work/'pack',self.root/'b.draft.zip',draft=True)
        self.assertEqual(first['sha256'],second['sha256']);self.assertFalse(first['runtimeValidation']['validated'])
        self.assertEqual(first['mediaVerification'],{'status':'not-checked','checkedImages':0,'method':None})
        with self.assertRaisesRegex(ValueError,'draft.zip'):
            build(work/'pack',self.root/'misleading.chatgal',draft=True)
    def test_unknown_future_feature_is_not_silently_accepted(self):
        work=self.create();p=work/'pack/stories/start.json';scene=load_jsonc(p);scene['bgm']='song.mp3';write_json(p,scene)
        with self.assertRaisesRegex(ValueError,'outside reviewed scene contract'):
            build(work/'pack',self.root/'music.draft.zip',draft=True)
    def test_same_version_changed_content_rejected(self):
        work=self.create();populate_test_art(work);old=self.root/'old.draft.zip';build(work/'pack',old,draft=True)
        p=work/'pack/stories/start.json';scene=load_jsonc(p);scene['narration']='新的开场';write_json(p,scene)
        with self.assertRaisesRegex(ValueError,'higher package version'):
            build(work/'pack',self.root/'new.draft.zip',draft=True,previous=old)
    def test_numeric_alias_does_not_bypass_version_increase(self):
        work=self.create();populate_test_art(work);old=self.root/'old.draft.zip';build(work/'pack',old,draft=True)
        p=work/'pack/manifest.json';value=load_jsonc(p);value['version']='01';write_json(p,value)
        with self.assertRaisesRegex(ValueError,'higher package version'):
            build(work/'pack',self.root/'alias.draft.zip',draft=True,previous=old)
    def test_home_can_be_intentionally_omitted_with_theme_fallback(self):
        work=self.create();populate_test_art(work);(work/'pack/home.png').unlink()
        path=work/'asset-plan.json';plan=load_jsonc(path);plan['assets']=[item for item in plan['assets'] if item['path']!='home.png'];write_json(path,plan)
        report=build(work/'pack',self.root/'fallback.draft.zip',draft=True)
        self.assertEqual(report['runtimeValidation']['missingImages'],[])
        self.assertGreater(report['mediaVerification']['checkedImages'],0)
    def test_jsonc_keeps_strings_urls_and_trailing_commas(self):
        path=self.root/'x.json';path.write_text('{/* c */"url":"https://host/a//b", "text":"literal , } /* keep */", "list":[1,2,],}',encoding='utf-8')
        obj=load_jsonc(path);self.assertEqual(obj['url'],'https://host/a//b');self.assertEqual(obj['text'],'literal , } /* keep */');self.assertEqual(obj['list'],[1,2])
    def test_path_and_filename_matrix_collisions(self):
        with self.assertRaises(ValueError): inside(self.root,'../../escape.png')
        brief=copy.deepcopy(self.brief);brief['states']=['a_b','a'];brief['emotions']=['c','b_c']
        with self.assertRaisesRegex(ValueError,'ambiguous'):
            initialize(self.root/'collision',brief,'daily','prompts')
        self.assertFalse((self.root/'collision').exists())
    def test_contract_drift_detects_media_candidate_without_enabling(self):
        actual=copy.deepcopy(self.lock);actual['sourceHashes']['schemas/v2/scene.json']='different'
        actual['topLevelFields']['scene'].append('bgm')
        report=compare(self.lock,actual)
        self.assertFalse(report['compatibleWithReviewedBaseline']);self.assertIn('bgm',report['mediaCandidatesRequireRuntimeReview'])
        self.assertEqual(actual['reviewedCapabilities']['features']['package_bgm_sfx']['status'],'not-supported-at-baseline')
    def test_invalid_png_fails_before_archive_written(self):
        work=self.create();populate_test_art(work);(work/'pack/home.png').write_bytes(b'not a png')
        with self.assertRaisesRegex(ValueError,'actual PNG'):
            build(work/'pack',self.root/'invalid.draft.zip',draft=True)
    @unittest.skipUnless(os.environ.get('CHATGAL_PROJECT'),'Set CHATGAL_PROJECT for the real upstream checkout')
    def test_real_upstream_fingerprint(self):
        self.assertTrue(compare(self.lock,snapshot(os.environ['CHATGAL_PROJECT']))['compatibleWithReviewedBaseline'])
    @unittest.skipUnless(os.environ.get('CHATGAL_PROJECT'),'Set CHATGAL_PROJECT for line-ending portability test')
    def test_windows_line_endings_do_not_create_false_contract_drift(self):
        project=Path(os.environ['CHATGAL_PROJECT']);target=self.root/'crlf-project'
        for rel in self.lock['sourceHashes']:
            dest=target/rel;dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes((project/rel).read_bytes().replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'))
        self.assertTrue(compare(self.lock,snapshot(target))['compatibleWithReviewedBaseline'])


if __name__=='__main__': unittest.main()
