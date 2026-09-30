# -*- coding: utf-8 -*-
"""生成火星文 TTF：实例化 Regular → 重写 cmap → 修改字体元数据"""
import json
import datetime
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

SRC = 'NotoSansSC-VF.ttf'
OUT = 'HuoXingWenHei-Regular.ttf'

mapping = json.load(open('mapping.json', encoding='utf-8'))
print(f'载入映射 {len(mapping)} 条')

# ===== 1. 实例化可变字体为 Regular (wght=400) =====
print('实例化可变字体 wght=400 ...')
font = TTFont(SRC)
instantiateVariableFont(font, {'wght': 400}, inplace=True)
# 静态化后清掉可变字体遗留表
for tbl in ('fvar', 'gvar', 'avar', 'STAT', 'MVAR', 'VVAR', 'HVAR'):
    if tbl in font:
        del font[tbl]
print(f'  字形数 {font["maxp"].numGlyphs}')

# ===== 2. 去掉「视觉上无变化」的映射（源/目标字形轮廓相同） =====
from fontTools.pens.recordingPen import RecordingPen

def glyph_sig(name):
    try:
        g = font['glyf'][name]
    except KeyError:
        return None
    pen = RecordingPen()
    g.draw(pen, font['glyf'])
    return str(pen.value)

best_cmap = font.getBestCmap()
removed = []
for src, dst in list(mapping.items()):
    sg = best_cmap.get(ord(src))
    dg = best_cmap.get(ord(dst))
    if sg and dg and glyph_sig(sg) == glyph_sig(dg):
        removed.append(src)
        del mapping[src]
print(f'去除字形轮廓重复的无效映射 {len(removed)} 条: {"".join(removed[:30])}')

# ===== 3. 重写 cmap：源字码点 → 火星文字形 =====
applied = {4: 0, 12: 0}
for table in font['cmap'].tables:
    if not table.isUnicode():
        continue
    fmt = table.format
    if fmt not in (4, 12):
        continue
    new_cmap = dict(table.cmap)
    for src, dst in mapping.items():
        s, d = ord(src), ord(dst)
        if fmt == 4 and (s > 0xFFFF or d > 0xFFFF):
            continue  # format 4 仅支持 BMP
        if d in table.cmap and s in table.cmap:
            new_cmap[s] = table.cmap[d]
            applied[fmt] += 1
    table.cmap = new_cmap
print(f'cmap 重映射: format4 {applied[4]} 条, format12 {applied[12]} 条')

# ===== 4. 修改字体元数据（双语：中文优先显示） =====
name = font['name']
for nid in (0, 1, 2, 3, 4, 5, 6, 16, 17):
    name.removeNames(nameID=nid)

stamp = datetime.date.today().isoformat()
# 英文记录 (Windows Unicode, en-US)
name.setName('HuoXingWen Hei', 1, 3, 1, 0x409)
name.setName('Regular', 2, 3, 1, 0x409)
name.setName(f'HuoXingWen:MarsWen:{stamp}', 3, 3, 1, 0x409)
name.setName('HuoXingWen Hei Regular', 4, 3, 1, 0x409)
name.setName(f'Version 1.0 - {stamp}', 5, 3, 1, 0x409)
name.setName('HuoXingWenHei-Regular', 6, 3, 1, 0x409)
name.setName('HuoXingWen Hei', 16, 3, 1, 0x409)
name.setName('Regular', 17, 3, 1, 0x409)
# 简体中文记录 (zh-CN) —— Windows 字体列表显示「火星文黑体」
name.setName('火星文黑体', 1, 3, 1, 0x804)
name.setName('Regular', 2, 3, 1, 0x804)
name.setName(f'HuoXingWen:MarsWen:{stamp}', 3, 3, 1, 0x804)
name.setName('火星文黑体 Regular', 4, 3, 1, 0x804)
name.setName(f'Version 1.0 - {stamp}', 5, 3, 1, 0x804)
name.setName('HuoXingWenHei-Regular', 6, 3, 1, 0x804)
name.setName('火星文黑体', 16, 3, 1, 0x804)
name.setName('Regular', 17, 3, 1, 0x804)
# Mac 平台记录（兼容旧软件）
name.setName('HuoXingWen Hei', 1, 1, 0, 0)
name.setName('Regular', 2, 1, 0, 0)
name.setName('HuoXingWenHei-Regular', 6, 1, 0, 0)

# 描述信息
name.setName('HuoXingWen (Martian Text) display font: type hanzi, '
             'glyphs come out in classic 2000s-style Martian Chinese. '
             'Derived from Noto Sans SC (SIL OFL 1.1).', 10, 3, 1, 0x409)
name.setName('火星文显示字体：输入正常汉字，显示为经典火星文。基于 Noto Sans SC（SIL OFL 1.1 开源协议）改造。',
             10, 3, 1, 0x804)

# ===== 5. 保存 =====
font.save(OUT)
sz = len(open(OUT, 'rb').read()) / 1024 / 1024
print(f'已保存 {OUT} ({sz:.1f} MB)')

# ===== 6. 回读验证 =====
f2 = TTFont(OUT, lazy=True)
cmap = f2.getBestCmap()
checks = {
    '我': '莪', '你': '沵', '的': '旳', '是': '湜', '不': '卟',
    '一': '①', '天': '兲', '爱': '嬡', '笑': '咲', '知道': '倁檤',
}
ok = 0
for src, dst in checks.items():
    if len(src) == 1:
        good = cmap.get(ord(src)) == cmap.get(ord(dst))
        print(f'  {src}({ord(src):04X}) -> {dst} : {"OK" if good else "FAIL"}')
        ok += good
print(f'验证通过 {ok}/{len(checks)}')
