# 検証ツール — デザイン改修の前後比較用

[docs/design-habits-audit.md](../docs/design-habits-audit.md) の監査結果に対して、改修で品質が変わったことを「数字」と「見た目」の両方で確認するためのツール。

## check-ai-tells.py — AIクセ自動スコアラー

```bash
python3 tools/check-ai-tells.py                 # 4案すべて
python3 tools/check-ai-tells.py index.html      # 特定ページのみ
```

10のクセをパターン検索で 🟢/🟡/🔴 判定し、ページごとのスコア（🔴=1・🟡=0.5、低いほど良い）を出す。
**改修前に1回、改修後に1回**実行して差を見る。機械判定なので最終判断は目視と併用すること。

## capture.mjs — フルページスクリーンショット

```bash
npm i playwright-core        # 初回のみ（ブラウザ本体は不要。/opt/pw-browsers/chromium を使用）
node tools/capture.mjs before                     # 改修前: 4案×375/1280px → docs/shots/before/
# …改修する…
node tools/capture.mjs after index.html --width 375   # 改修後
```

`docs/shots/<ラベル>/` に保存される（gitignore済み）。前後のPNGを並べて見比べる。
アニメーションは `reducedMotion: reduce` で止めて撮るので、比較がブレない。

## 運用ルール

1. **一度に1つだけ変えて撮り直す**（出典検証サイトと同じ方法論。まとめて変えると効果の切り分けができない）
2. スコアが下がっても見た目が壊れていないか必ずスクリーンショットで確認する
3. hover・:active・イージング・スクロール挙動は静止画に写らない → 実機スマホで触って確認する
