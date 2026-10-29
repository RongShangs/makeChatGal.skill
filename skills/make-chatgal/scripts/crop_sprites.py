"""Mechanically crop inspected bounding boxes, preserving original alpha."""
import argparse
import json
from pathlib import Path

from common import inside


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--atlas', required=True)
    parser.add_argument('--boxes', required=True, help='JSON list: [{"file":"characters/角色/状态_情绪.png","box":[l,t,r,b]}]')
    parser.add_argument('--output', required=True)
    parser.add_argument('--canvas', nargs=2, type=int, default=[768,1024])
    parser.add_argument('--height', type=int, default=900)
    parser.add_argument('--baseline', type=int, default=980)
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args()
    from PIL import Image
    if not 0 < args.height <= args.baseline < args.canvas[1]: parser.error('height <= baseline < canvas height is required')
    atlas = Image.open(args.atlas).convert('RGBA')
    if atlas.getchannel('A').getextrema()[0] == 255: parser.error('Atlas has no transparent pixels; obtain a real alpha cutout first')
    items = json.loads(Path(args.boxes).read_text(encoding='utf-8-sig'))
    prepared = []
    seen = set()
    for item in items:
        target = inside(args.output, item['file'])
        if target in seen or (target.exists() and not args.overwrite): parser.error(f'Would overwrite output: {target}')
        seen.add(target)
        left,top,right,bottom = item['box']
        if not (0 <= left < right <= atlas.width and 0 <= top < bottom <= atlas.height): parser.error('Bounding box outside atlas')
        crop = atlas.crop((left,top,right,bottom))
        box = crop.getbbox()
        if not box: parser.error('Empty sprite')
        crop = crop.crop(box)
        width = round(crop.width * args.height / crop.height)
        if width > args.canvas[0]-8: parser.error('Sprite too wide; reduce height or increase canvas')
        canvas = Image.new('RGBA', tuple(args.canvas), (0,0,0,0))
        canvas.alpha_composite(crop.resize((width,args.height), Image.Resampling.LANCZOS), ((args.canvas[0]-width)//2,args.baseline-args.height))
        prepared.append((target,canvas))
    for target, canvas in prepared:
        target.parent.mkdir(parents=True,exist_ok=True)
        canvas.save(target, optimize=True)
    print(f'Cropped {len(prepared)} sprites with preserved alpha and common baseline')


if __name__ == '__main__': main()
