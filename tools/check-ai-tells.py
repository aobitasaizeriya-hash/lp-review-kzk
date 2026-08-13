#!/usr/bin/env python3
"""AIデザイン10のクセ ヒューリスティックチェッカー。

docs/design-habits-audit.md の10項目をパターン検索で機械判定し、
改修の前後でスコアが下がったかを数字で確認するためのツール。
あくまでヒューリスティック(機械判定)なので、⚠️判定の妥当性は目視確認と併用する。

使い方: python3 tools/check-ai-tells.py [ページ...]   # 省略時は4案すべて
出力: ページ×10項目の判定表(markdown)と合計スコア(低いほど良い)
"""
import re
import sys

DEFAULT_PAGES = ["index.html", "hitotonari.html", "editorial.html", "gravure.html"]

EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿]")  # 矢印・✿などの記号は含めない
PURPLE = re.compile(r"667eea|764ba2|8b5cf6|a78bfa|c084fc|9333ea|7c3aed|6d28d9", re.I)


def css_blocks(text):
    """雑なCSSブロック分解: (セレクタ, 宣言) のリスト。1行CSSにも対応。"""
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", text):
        yield m.group(1).strip(), m.group(2)


def check(path):
    raw = open(path, encoding="utf-8").read()
    text = re.sub(r"url\(data:[^)]*\)", "url(DATA)", raw)  # 埋め込みフォント除去
    blocks = list(css_blocks(text))
    r = {}

    # 01 紫→ピンクグラデ
    r[1] = ("OK", "") if not PURPLE.search(text) else ("NG", "紫系hex検出")

    # 02 絵文字アイコン(本文マークアップ中の絵文字)
    body = re.sub(r"<(style|script)[^>]*>.*?</\1>", "", text, flags=re.S)
    emojis = EMOJI.findall(body)
    r[2] = ("OK", "") if not emojis else ("NG", f"絵文字{len(emojis)}個: {''.join(sorted(set(emojis)))[:10]}")

    # 03 均等3カラム+ふわ影: repeat(3,1fr) と、カード系セレクタのぼかし影の併存
    three = re.findall(r"repeat\(3, ?1fr\)", text)
    soft = [s for s, d in blocks
            if re.search(r"card|grid-item|item\b", s, re.I)
            and re.search(r"box-shadow:[^;]*\d{1,2}px \d{1,2}px[^;]*rgba", d)]
    if three and soft:
        r[3] = ("NG", f"repeat(3,1fr)×{len(three)} + カード影×{len(soft)}")
    elif three:
        r[3] = ("WARN", f"repeat(3,1fr)×{len(three)}(影なし)")
    else:
        r[3] = ("OK", "")

    # 04 blob/浮遊装飾: filter:blur(装飾) or 無限アニメの装飾要素
    blur_deco = re.findall(r"(?<!backdrop-)filter: ?blur", text)
    inf = [s for s, d in blocks if re.search(r"animation:[^;]*infinite", d)
           and not re.search(r"marquee|progress|spin(ner)?\b", s, re.I)]
    if blur_deco:
        r[4] = ("NG", f"filter:blur×{len(blur_deco)}")
    elif inf:
        r[4] = ("WARN", f"無限アニメ装飾: {', '.join(s[:28] for s in inf[:3])}")
    else:
        r[4] = ("OK", "")

    # 05 glassヘッダー: header/sticky系セレクタ内のbackdrop-filter
    glass = [s for s, d in blocks if "backdrop-filter" in d]
    glass_hd = [s for s in glass if re.search(r"header|sticky|nav", s, re.I)]
    if glass_hd:
        r[5] = ("NG", f"backdrop-filter: {', '.join(s[:30] for s in glass_hd[:2])}")
    elif glass:
        r[5] = ("WARN", f"backdrop-filter×{len(glass)}(ヘッダー外)")
    else:
        r[5] = ("OK", "")

    # 06 999pxピル: 使用箇所数で段階判定(CTA限定なら許容)
    pills = re.findall(r"border-radius: ?9{2,4}px|var\(--r-pill\)", text)
    r[6] = ("OK", "") if not pills else (("WARN", f"ピル×{len(pills)}") if len(pills) <= 8 else ("NG", f"ピル×{len(pills)}(タグ類まで統一)"))

    # 07 hover浮き上がり: :hoverブロック内のtranslateY(-Npx)
    lifts = []
    for s, d in blocks:
        if ":hover" in s:
            lifts += re.findall(r"translateY\((-\d+(?:\.\d+)?)px\)", d)
    if any(abs(float(v)) >= 6 for v in lifts):
        r[7] = ("NG", f"hover浮き {sorted(set(lifts))}px")
    elif lifts:
        r[7] = ("WARN", f"hover浮き {sorted(set(lifts))}px(軽度)")
    else:
        r[7] = ("OK", "")

    # 08 Inter一択
    r[8] = ("NG", "Inter使用") if re.search(r"font-family[^;]*\bInter\b", text) else ("OK", "")

    # 09 中央揃え見出し: 見出し系セレクタの text-align:center + HTML側の使用比率
    title_center = [s for s, d in blocks
                    if re.search(r"sec-?title|sec-?head|section-title", s, re.I)
                    and re.search(r"text-align: ?center", d)]
    center_use = len(re.findall(r'class="sec-(?:title|head)(?! [^"]*left)[^"]*center[^"]*"', text))
    # 中央がCSS既定の場合: 素のクラス使用回数をそのまま中央運用として数える
    if any(re.fullmatch(r"\.sec-(?:title|head)", s) for s in title_center):
        center_use += len(re.findall(r'class="sec-(?:title|head)"', text))
    if title_center and center_use >= 4:
        r[9] = ("NG", f"見出しcenter既定/多用({', '.join(s[:20] for s in title_center[:2])})")
    elif title_center or center_use:
        r[9] = ("WARN", f"一部center(クラス使用{center_use})")
    else:
        r[9] = ("OK", "")

    # 10 絵文字CTA: ボタン/CTA近傍の絵文字
    cta_emoji = [l for l in body.split("\n") if EMOJI.search(l) and re.search(r"btn|cta|button", l, re.I)]
    r[10] = ("NG", f"{len(cta_emoji)}行") if cta_emoji else ("OK", "")

    return r


MARK = {"OK": "🟢", "WARN": "🟡", "NG": "🔴"}
NAMES = ["紫グラデ", "絵文字アイコン", "3カラム+ふわ影", "blob/浮遊装飾", "glassヘッダー",
         "999pxピル", "hover浮き", "Inter", "中央見出し", "絵文字CTA"]


def main():
    pages = sys.argv[1:] or DEFAULT_PAGES
    results = {p: check(p) for p in pages}
    print("| # | クセ | " + " | ".join(pages) + " |")
    print("|---|------|" + "---|" * len(pages))
    for i in range(1, 11):
        cells = [MARK[results[p][i][0]] for p in pages]
        print(f"| {i:02d} | {NAMES[i-1]} | " + " | ".join(cells) + " |")
    scores = [sum({"OK": 0, "WARN": 0.5, "NG": 1}[results[p][i][0]] for i in range(1, 11)) for p in pages]
    print("| — | **スコア(低いほど良い)** | " + " | ".join(f"**{s:g}**" for s in scores) + " |")
    print()
    for p in pages:
        notes = [f"  {i:02d} {MARK[results[p][i][0]]} {results[p][i][1]}" for i in range(1, 11) if results[p][i][1]]
        if notes:
            print(f"[{p}]")
            print("\n".join(notes))


if __name__ == "__main__":
    main()
