# Design Sync ノート

## セットアップ情報

- **パッケージ**: `design-system/` (モノレポ内のローカルパッケージ)
- **エントリ**: `./design-system/dist/index.es.js`
- **node_modules**: `design-system/node_modules`
- **ビルドコマンド**: `cd design-system && npm run build`（JS + tsc 型定義）
- **CSS**: `design-system/src/styles.css` を `cfg.cssEntry` で指定（PKG_DIR からの相対パス）
- **Playwright**: `~/.cache/ms-playwright/` に playwright-core、`~/Library/Caches/ms-playwright/` に playwright 本体

## Known render warns

なし（初回全クリーン）

## 注意点

- `cssEntry` は `PKG_DIR` (`design-system/`) からの相対パス。リポジトリルートからではない
- esbuild の WARNING: `package.json` の `exports["."].types` が `import`/`require` の後にあるため unused になるが無害
- tsconfig は `moduleResolution: bundler` を使用（Node16 ではない）
- `design-system/node_modules/` に react がインストール済み（コンバーターが要求）
- `HeatCell` は `<td>` 要素なので必ず `<table>` の中でしか使えない。プレビューは table でラップして書く

## 再同期手順

```bash
# 1. スクリプトを再ステージ
mkdir -p .ds-sync && cp -r /path/to/design-sync/skill/{package-build,package-validate,package-capture,resync}.mjs /path/to/design-sync/skill/{lib,storybook} .ds-sync/
cd .ds-sync && npm i esbuild ts-morph @types/react playwright && cd ..

# 2. DSをリビルド
cd design-system && npm run build && cd ..

# 3. ドライバー実行
node .ds-sync/resync.mjs \
  --config .design-sync/config.json \
  --node-modules design-system/node_modules \
  --entry ./design-system/dist/index.es.js \
  --out ./ds-bundle \
  --remote .design-sync/.cache/remote-sync.json
```

## Re-sync risks

- **CSS トークン**: `design-system/src/styles.css` に直書きされているため、既存レポートの CSS と乖離が生じた場合は手動で同期が必要
- **プレビューの日本語テキスト**: 特定のデータ値（192件, 52件など）がハードコードされている。実際のデータが変わっても自動更新されない
- **フロアカード**: BarRow, Chip, NavLinks, StatGrid はプレビューなし（フロアカード）。必要ならいつでも `.design-sync/previews/` に追加可能
- **esbuild 型定義 WARNING**: package.json の `exports.types` 位置による無害な警告は毎回出る
