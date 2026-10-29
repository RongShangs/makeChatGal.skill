"""Create editable source and per-image prompts. This script never generates art."""
import argparse
import json
from pathlib import Path
import re

from common import inside, safe_name, write_json


def initialize(output, brief, template, image_mode):
    output = Path(output).resolve()
    if output.exists(): raise ValueError('Use a new output directory; existing work is not overwritten')
    package_id = brief['packageId']
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', package_id) or '..' in package_id:
        raise ValueError('Invalid packageId')
    if not re.fullmatch(r'[0-9]+', str(brief.get('version', '1'))): raise ValueError('Version must contain digits only')
    char = safe_name(brief['character'])
    companion = safe_name(brief['companion']) if brief.get('companion') else None
    if companion == char: raise ValueError('Companion must have a distinct character id')
    states = [safe_name(value) for value in brief['states']]
    emotions = [safe_name(value) for value in brief['emotions']]
    if not states or not emotions or len(set(states)) != len(states) or len(set(emotions)) != len(emotions):
        raise ValueError('States/emotions must be nonempty and unique')
    if len({f'{state}_{emotion}' for state in states for emotion in emotions}) != len(states)*len(emotions):
        raise ValueError('State/emotion combinations produce ambiguous duplicate filenames')
    output.mkdir(parents=True)
    pack = output / 'pack'
    manifest = {'packageId': package_id, 'version': str(brief.get('version','1')), 'name': brief['name'],
                'author': brief.get('author','内容作者'), 'description': brief.get('description',''),
                'variables':[{'id':'day','type':'int','default':0},
                {'id':char+'好感','type':'int','default':50,'min':0,'max':100,'label':'好感'},
                {'id':char+'信任','type':'int','default':40,'min':0,'max':100,'label':'信任'}]}
    write_json(pack / 'manifest.json', manifest)
    assets = []
    def asset(path, role, details, transparent=False, **extra):
        identifier = f'image-{len(assets)+1:03}'
        prompt = f"用途：{role}。风格：{brief.get('visualStyle','清晰一致的插画')}。形象设定：{brief.get('appearance','遵循用户已确认的角色设计')}。{details}。无文字、水印或界面元素。"
        assets.append({'id':identifier,'role':role,'path':path,'transparent':transparent,
                       'referenceRole':'用户图像仅作形象/风格参考；编辑目标另行标记',
                       'prompt':prompt,'negativePrompt':'裁切主体、身份漂移、多余人物、乱码、水印',**extra})
    asset('home.png','主页封面','主体位于中央可见区，为标题和底部抽屉留空间；以目标客户端手机 cover 裁切为准')
    for name in [char] + ([companion] if companion else []):
        prompt = brief.get('characterPrompt') if name == char else f'你是{name}，海边店员，观察细致、说话直接。只知道参与过的对话，不替玩家行动。'
        write_json(pack / f'characters/{name}/character.json', {'id':name,'prompt':prompt or f'你是{name}，自然回应玩家，只描写自己的行动。',
                   'states':states,'emotions':emotions,'defaultState':states[0],'defaultEmotion':emotions[0]})
        for state in states:
            for emotion in emotions:
                asset(f'characters/{name}/{state}_{emotion}.png','角色立绘',
                      f'只画{name}一人，{state}服装，{emotion}表情；真透明 PNG，完整头发/耳尾/手脚，留透明边，统一比例和脚底基线',
                      True, character=name, state=state, emotion=emotion)
    backgrounds = [('morning.png','清晨海边早餐店，柔和晨光'),('afternoon.png','午后海边步道，温暖阳光'),('night.png','夜晚小屋客厅，暖色灯光')]
    for filename, description in backgrounds:
        asset('stories/'+filename,'场景背景',description+'；不画角色，主体叠加区域留清楚')
    def destination(kind, to): return {'kind':kind,'to':to}
    def scene(title, bg, when, next_id, index, first=False):
        actors = [{'charId':char,'state':states[index % len(states)],'emotion':emotions[0],
                   'scenePrompt':f'现在是{when}，地点是{title}。承接记忆中的真实约定，先回应玩家；只在本幕活动，不自行跨时段或换衣。'}]
        if companion and index == 1:
            actors.append({'charId':companion,'state':states[0],'emotion':emotions[0],
                           'scenePrompt':f'现在是{when}，和{char}、玩家在场；不知道此前未参与的私聊。'})
        return {'displayName':title,'background':bg,'narration':f'{title}。海风轻轻吹过，新的一段相处从这里继续。',
                'atmosphere':f'{when}的光落在熟悉的地方。','characters':actors,
                'fixedEffects':[{'id':'day','value':1}] if first else [],
                'settlement':[{'var':char+'好感','prompt':'主动分享或愿意陪伴且有具体证据时增加；明确疏远时减少；无证据保持不变。','maxAbsDelta':2,'onNoEvidence':'zero'}],
                'target':[{'kind':[destination('story',next_id)]}]}
    scenes = {'start':scene('清晨·早餐店','morning.png','清晨','afternoon',0,True),
              'afternoon':scene('午后·海边','afternoon.png','下午','night',1),
              'night':scene('夜晚·小屋','night.png','夜晚','start',2)}
    if template == 'branching':
        scenes['start']['target'][0]['kind'].append(destination('story','detour'))
        scenes['detour'] = scene('午后·旧书摊','afternoon.png','下午','night',1)
        for key in ('afternoon','detour'):
            scenes[key]['target'] = [
                {'require':f'"day" >= 1 & "{char}好感" >= 60','kind':[destination('event','小小约定')]},
                {'kind':[destination('event','海边纸条')]}]
        for event in ('小小约定','海边纸条'):
            asset(f'events/{event}/cover.png','事件CG',f'{event}：海边朋友递来折好的纸条；保持角色身份，不把对白画进图片')
        write_json(pack/'events/小小约定/event.json', {'slides':[{'image':'cover.png','text':['她认真地把纸船递给你。','一个小小的约定留在海风里。']},{'image':None,'text':['这张图继续承接下一屏。']}],
                   'target':[{'kind':[destination('story','night')]}]})
        write_json(pack/'events/海边纸条/event.json', {'slides':[{'image':'cover.png','text':['你们在海边捡到一张写着问候的纸条。']}],
                   'choice':{'title':'接下来想去哪里？','options':[{'text':'回小屋聊聊',**destination('story','night')},{'text':'开始新一天',**destination('story','start')},{'text':'回到主页',**destination('appShell','home')}]}})
    for identifier, value in scenes.items(): write_json(pack / f'stories/{identifier}.json', value)
    write_json(output/'asset-plan.json', {'imageMode':image_mode,'status':'needs-assets','assets':assets})
    prompt_dir = output/'image-prompts'
    prompt_dir.mkdir()
    lines = ['# 素材提示词与待补路径', '', f'当前模式：{image_mode}。此脚本未生成任何图片。', '']
    for item in assets:
        text = f"目标路径：pack/{item['path']}\n{item['prompt']}\n避免：{item['negativePrompt']}\n"
        (prompt_dir/(item['id']+'.txt')).write_text(text, encoding='utf-8')
        lines.extend([f"## {item['id']} · {item['path']}", '', item['prompt'], ''])
    (output/'IMAGE_PROMPTS.md').write_text('\n'.join(lines), encoding='utf-8')
    write_json(output/'AUTHORING_STATUS.json', {'status':'draft-needs-assets','imageMode':image_mode,'expectedImages':len(assets),'runtimeValidated':False})
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--brief', required=True)
    parser.add_argument('--template', choices=['daily','branching'], default='daily')
    parser.add_argument('--image-mode', choices=['generate','prompts'], required=True)
    args = parser.parse_args()
    result = initialize(args.output, json.loads(Path(args.brief).read_text(encoding='utf-8-sig')), args.template, args.image_mode)
    print('Created editable source and per-image prompts:', result)
    print('Draft only: generated image count=0; supply assets before final validation.')


if __name__ == '__main__': main()
