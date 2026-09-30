# -*- coding: utf-8 -*-
"""构建火星文映射表：人工表 > OpenCC简繁 > Unihan异体，全部经字体cmap验证"""
import json
import re
import sys
from fontTools.ttLib import TTFont
from opencc import OpenCC
from mars_manual import MANUAL

FONT = 'NotoSansSC-VF.ttf'


def gb2312_hanzi():
    """生成 GB2312 全部汉字（6763个）"""
    chars = []
    for hi in range(0xB0, 0xF8):
        for lo in range(0xA1, 0xFF):
            try:
                chars.append(bytes([hi, lo]).decode('gb2312'))
            except UnicodeDecodeError:
                pass
    return chars


def main():
    font = TTFont(FONT, lazy=True)
    cmap = font.getBestCmap()

    def pick(cands):
        for c in cands:
            if len(c) == 1 and ord(c) in cmap:
                return c
        return None

    gb = gb2312_hanzi()
    gb_set = set(gb)
    mapping = {}
    skipped = []

    # ===== 层1：人工经典映射 =====
    l1 = 0
    for src, cands in MANUAL.items():
        if len(src) != 1 or ord(src) not in cmap:
            continue
        dst = pick(cands)
        if dst:
            mapping[src] = dst
            l1 += 1
        else:
            skipped.append(src)

    # ===== 层2：OpenCC 简→繁 =====
    cc = OpenCC('s2t')
    l2 = 0
    for ch in gb:
        if ch in mapping:
            continue
        t = cc.convert(ch)
        if len(t) == 1 and t != ch and ord(t) in cmap:
            mapping[ch] = t
            l2 += 1

    # ===== 层3：Unihan 异体字 =====
    unihan = {}
    with open('Unihan_Variants.txt', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) < 3:
                continue
            cp_field, field, value = parts[0], parts[1], parts[2]
            if field in ('kSemanticVariant', 'kSpecializedSemanticVariant', 'kZVariant'):
                try:
                    src_cp = int(cp_field[2:], 16)
                except ValueError:
                    continue
                cands = re.findall(r'U\+([0-9A-Fa-f]{4,6})', value)
                lst = unihan.setdefault(src_cp, [])
                for c in cands:
                    cp = int(c, 16)
                    if cp not in lst:
                        lst.append(cp)

    l3 = 0
    for ch in gb:
        if ch in mapping:
            continue
        for cp in unihan.get(ord(ch), []):
            if cp != ord(ch) and cp in cmap:
                mapping[ch] = chr(cp)
                l3 += 1
                break

    # ===== 统计 =====
    covered = sum(1 for c in gb if c in mapping)
    print(f'人工经典映射: {l1} 条（跳过 {len(skipped)}: {"".join(skipped)}）')
    print(f'OpenCC 简繁: {l2} 条')
    print(f'Unihan 异体: {l3} 条')
    print(f'总映射: {len(mapping)} 条')
    print(f'GB2312 覆盖: {covered}/{len(gb)} = {covered/len(gb)*100:.1f}%')

    # 抽查高频句子效果
    demo = '我爱你你知道吗今天真的很开心因为见到了你不要忘记我们的约定一直在一起'
    print('示例:', ''.join(mapping.get(c, c) for c in demo))

    json.dump(mapping, open('mapping.json', 'w', encoding='utf-8'),
              ensure_ascii=False)
    print('已保存 mapping.json')


if __name__ == '__main__':
    main()
