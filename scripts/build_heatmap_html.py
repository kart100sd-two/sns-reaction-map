#!/usr/bin/env python3
"""Build a static heatmap page from classified social reaction JSON."""

from __future__ import annotations

import argparse
import html
import json
from collections import Counter, defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


CATEGORY_ORDER = [
    "高市氏批判・責任追及",
    "高市氏擁護・報道批判",
    "サナエトークン関連",
    "松井健氏を軸にした拡張",
    "玉木氏比較・説明責任",
    "ネット選挙・透明性問題",
    "未確認・陰謀寄り",
    "その他・分類保留",
]

STANCE_ORDER = ["批判", "擁護", "比較", "未確認", "保留", "その他"]


def resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else PROJECT_ROOT / p


def pct(value: int, max_value: int) -> float:
    if max_value <= 0:
        return 0.0
    return value / max_value


def heat_color(value: int, max_value: int) -> str:
    ratio = pct(value, max_value)
    if value == 0:
        return "#f5f6f8"
    if ratio < 0.2:
        return "#dceeff"
    if ratio < 0.4:
        return "#9fd0ff"
    if ratio < 0.6:
        return "#4da3ff"
    if ratio < 0.8:
        return "#1769d1"
    return "#0a3d91"


def text_color(value: int, max_value: int) -> str:
    return "#ffffff" if pct(value, max_value) >= 0.55 else "#172033"


def table_html(title: str, rows: list[str], cols: list[str], counts: dict[tuple[str, str], int]) -> str:
    max_value = max(counts.values(), default=0)
    out = [f"<section class=\"panel\"><h2>{html.escape(title)}</h2>", "<div class=\"table-wrap\"><table>"]
    out.append("<thead><tr><th>分類</th>" + "".join(f"<th>{html.escape(col)}</th>" for col in cols) + "<th>合計</th></tr></thead>")
    out.append("<tbody>")
    for row in rows:
        total = sum(counts.get((row, col), 0) for col in cols)
        out.append(f"<tr><th>{html.escape(row)}</th>")
        for col in cols:
            value = counts.get((row, col), 0)
            out.append(
                "<td "
                f"style=\"background:{heat_color(value, max_value)};color:{text_color(value, max_value)}\" "
                f"title=\"{html.escape(row)} / {html.escape(col)}: {value}件\">{value}</td>"
            )
        out.append(f"<td class=\"total\">{total}</td></tr>")
    out.append("</tbody></table></div></section>")
    return "\n".join(out)


def representative_html(rows: list[dict]) -> str:
    buckets: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        category = row["classification"]["category"]
        if len(buckets[category]) < 3:
            buckets[category].append(row)

    out = ["<section class=\"panel\"><h2>代表サンプル</h2>", "<div class=\"sample-grid\">"]
    for category in CATEGORY_ORDER:
        items = buckets.get(category, [])
        if not items:
            continue
        out.append(f"<article class=\"sample-card\"><h3>{html.escape(category)}</h3>")
        for row in items:
            c = row["classification"]
            text = row.get("text", "").replace("\n", " ")
            if len(text) > 180:
                text = text[:177] + "..."
            out.append(
                "<div class=\"sample\">"
                f"<div class=\"meta\">{html.escape(c.get('stance', ''))} / 信頼度 {float(c.get('confidence', 0.0)):.2f}</div>"
                f"<p>{html.escape(c.get('summary') or '')}</p>"
                f"<blockquote>{html.escape(text)}</blockquote>"
                f"<a href=\"{html.escape(row.get('url', ''))}\">投稿URL</a>"
                "</div>"
            )
        out.append("</article>")
    out.append("</div></section>")
    return "\n".join(out)


def build(rows: list[dict]) -> str:
    categories = [c for c in CATEGORY_ORDER if any(r["classification"]["category"] == c for r in rows)]
    queries = sorted({r.get("query", "") for r in rows})
    stances = [s for s in STANCE_ORDER if any(r["classification"].get("stance") == s for r in rows)]

    by_query = Counter((r["classification"]["category"], r.get("query", "")) for r in rows)
    by_stance = Counter((r["classification"]["category"], r["classification"].get("stance", "")) for r in rows)
    by_category = Counter(r["classification"]["category"] for r in rows)
    by_stance_total = Counter(r["classification"].get("stance", "") for r in rows)

    total = len(rows)
    top_category = by_category.most_common(1)[0] if by_category else ("", 0)
    top_stance = by_stance_total.most_common(1)[0] if by_stance_total else ("", 0)

    return f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SNS反応ヒートマップ</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f8fa;
      --ink: #172033;
      --muted: #667085;
      --line: #d9dee7;
      --panel: #ffffff;
      --accent: #1769d1;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", "Yu Gothic", "Noto Sans JP", sans-serif;
      line-height: 1.65;
    }}
    header {{
      padding: 32px min(5vw, 56px) 20px;
      border-bottom: 1px solid var(--line);
      background: #fff;
    }}
    h1 {{ margin: 0 0 8px; font-size: clamp(26px, 4vw, 42px); letter-spacing: 0; }}
    h2 {{ margin: 0 0 16px; font-size: 20px; }}
    h3 {{ margin: 0 0 12px; font-size: 16px; }}
    .lead {{ margin: 0; color: var(--muted); max-width: 920px; }}
    main {{ padding: 22px min(5vw, 56px) 48px; }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }}
    .stat {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px 16px;
    }}
    .stat span {{ display: block; color: var(--muted); font-size: 13px; }}
    .stat strong {{ display: block; font-size: 24px; margin-top: 4px; }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
      margin-top: 18px;
    }}
    .table-wrap {{ overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; min-width: 900px; }}
    th, td {{
      border: 1px solid var(--line);
      padding: 10px 12px;
      text-align: center;
      vertical-align: middle;
      white-space: nowrap;
    }}
    th:first-child {{ text-align: left; position: sticky; left: 0; background: #fff; z-index: 1; }}
    thead th {{ background: #eef2f7; font-size: 13px; }}
    td {{ font-weight: 700; }}
    .total {{ background: #f2f4f7; color: var(--ink); }}
    .legend {{
      display: flex;
      gap: 8px;
      align-items: center;
      color: var(--muted);
      font-size: 13px;
      margin-top: 12px;
    }}
    .chip {{ width: 30px; height: 14px; border-radius: 3px; border: 1px solid rgba(0,0,0,.08); }}
    .sample-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 12px;
    }}
    .sample-card {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      background: #fbfcfe;
    }}
    .sample {{ border-top: 1px solid var(--line); padding-top: 10px; margin-top: 10px; }}
    .meta {{ color: var(--accent); font-size: 12px; font-weight: 700; }}
    blockquote {{
      margin: 8px 0;
      padding-left: 10px;
      border-left: 3px solid var(--line);
      color: #344054;
      font-size: 13px;
    }}
    a {{ color: var(--accent); font-size: 13px; }}
    .note {{ color: var(--muted); font-size: 13px; margin-top: 14px; }}
  </style>
</head>
<body>
  <header>
    <h1>SNS反応ヒートマップ</h1>
    <p class="lead">Yahooリアルタイム検索で取得した投稿サンプルを、論点カテゴリ・検索クエリ・立場で可視化したものです。世論調査ではなく、反応の偏りと論点の広がりを見るための編集用ビューです。</p>
  </header>
  <main>
    <section class="stats">
      <div class="stat"><span>総サンプル</span><strong>{total}</strong></div>
      <div class="stat"><span>最多カテゴリ</span><strong>{html.escape(top_category[0])} {top_category[1]}</strong></div>
      <div class="stat"><span>最多スタンス</span><strong>{html.escape(top_stance[0])} {top_stance[1]}</strong></div>
    </section>
    {table_html("カテゴリ × 検索クエリ", categories, queries, by_query)}
    <div class="legend">
      <span>少</span>
      <span class="chip" style="background:#f5f6f8"></span>
      <span class="chip" style="background:#dceeff"></span>
      <span class="chip" style="background:#9fd0ff"></span>
      <span class="chip" style="background:#4da3ff"></span>
      <span class="chip" style="background:#1769d1"></span>
      <span class="chip" style="background:#0a3d91"></span>
      <span>多</span>
    </div>
    {table_html("カテゴリ × スタンス", categories, stances, by_stance)}
    {representative_html(rows)}
    <p class="note">注意: 投稿本文の転載は最小限にし、公開記事では要約中心にしてください。代表投稿は公開前に人間が確認する前提です。</p>
  </main>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Build static SNS reaction heatmap HTML")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    rows = json.loads(resolve(args.input).read_text(encoding="utf-8"))
    output = resolve(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build(rows), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
