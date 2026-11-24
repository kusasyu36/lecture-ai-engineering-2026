# 第6回 解答

## 演習

- （演習は今回は省略）

## 宿題

- 取り組んだレベル：発展
- やったこと：Claude Code の公式ドキュメント（https://code.claude.com/docs/en/mcp 、2026-11-24 に参照）で MCP サーバーの設定方法を調べ、演習の `app/mcp_servers.json` と比べた。
- 結果：

| 項目 | 演習の `app/mcp_servers.json` | Claude Code |
|---|---|---|
| 設定を書く場所 | リポジトリ内の `app/mcp_servers.json`（エージェントが読み込む） | プロジェクト共有なら `.mcp.json`（プロジェクトのルート）、自分だけなら `~/.claude.json`。`claude mcp add` コマンドでも追加でき、`/mcp` で状態を確認できる |
| 一番上のキー | `mcpServers` | `mcpServers`（同じ） |
| コマンドで起動する書き方 | `"command": "uv"`, `"args": [...]` | `"type": "stdio"`, `"command"`, `"args"`, `"env"`。`type` を省くと stdio 扱い。CLI では `claude mcp add <名前> -- <コマンド> [引数...]` |
| URL で接続する書き方 | `"url": "https://..."` だけ | `"type": "http"` と `"url"` が必要（`url` だけで `type` がないとエラー）。`"headers"` で認証ヘッダを付けられる。OAuth が要るサーバーは `/mcp` から認証する。CLI では `claude mcp add --transport http <名前> <URL>` |
| 有効になる範囲 | このリポジトリのエージェントだけ | local（既定、そのプロジェクトで自分だけ）・project（`.mcp.json`、リポジトリを使う全員）・user（自分の全プロジェクト）の3つ。`.mcp.json` のサーバーは対話モードでは使う前に承認を求められる |

- 気づき・疑問：
  - 書き方はほぼ同じで、演習の設定を `.mcp.json` に写せばそのまま Claude Code でも使えそうだった。違いは URL 接続で `type` を明示する点と、範囲を3段階で選べる点。
  - リポジトリに置いた `.mcp.json` は他人が書いたコマンドを自分の手元で動かすことになるので、承認を挟む作りになっている。演習の注意（出所の分からないサーバーを書かない）と同じ考え方だと思った。
  - 疑問：`claude -p` のような非対話の実行では承認なしで project のサーバーが読み込まれるとあり、CI で使うときは何を許すかを別に決める必要がありそう。
