# k2keiba MCP サーバー

k2keiba の機能を MCP（Model Context Protocol）のツールとして公開するサーバーです。
Claude Code や Claude Desktop から、「今週の京都11Rの出馬表を見せて」「2025年10月4日の東京1Rの結果は？」のように頼むと、Claude がツールを使って JRA のサイトから取得します。

## インストール

```
$ pip install -e '.[mcp]'
```

`k2keiba-mcp` コマンドが入ります（`python -m k2kmcp` でも起動できます）。通信は stdio です。

## 登録

以下の `/path/to/venv` は、k2keiba を入れた Python 環境に置き換えてください。

### Claude Code

```
$ claude mcp add k2keiba -- /path/to/venv/bin/k2keiba-mcp
```

どのプロジェクトからでも使う場合は、`--scope user` を付けます。

### Claude Desktop

`claude_desktop_config.json` に追加します。

```json
{
  "mcpServers": {
    "k2keiba": {
      "command": "/path/to/venv/bin/k2keiba-mcp"
    }
  }
}
```

Windows の Claude Desktop から WSL 上の環境を使う場合は、`wsl` 経由で起動します。

```json
{
  "mcpServers": {
    "k2keiba": {
      "command": "wsl",
      "args": ["-e", "/path/to/venv/bin/k2keiba-mcp"]
    }
  }
}
```

## ツール

すべて読み取り専用です。日付は `YYYY-MM-DD`、競馬場は日本語名（`東京`、`京都` など）か、ローマ字名（`Tokyo`、`Kyoto` など）で指定します。

| ツール | 内容 | 対象期間 |
|---|---|---|
| `list_meetings` | 今週の開催（日付、競馬場、開催回・日次、WIN5 の有無） | 今週 |
| `get_track_conditions` | 天候と馬場状態 | 今週 |
| `list_races` | 開催のレース一覧（距離、芝/ダート、頭数、発走時刻） | 今週・過去 |
| `get_race_card` | 出馬表（枠番、馬番、`horse_id`、騎手、斤量、血統、馬体重、単勝オッズ・人気） | 今週 |
| `get_odds` | オッズ（`bet_type`: `win`, `wakuren`, `umaren`, `wide`, `umatan`, `trio`, `tierce`） | 今週 |
| `get_race_result` | レース結果（着順、タイム、上がり、通過順、払戻）。`include_video` で映像の HLS も取得 | 今週・過去（1986年〜） |
| `search_horses` | 馬名での検索（カタカナ、前方一致） | — |
| `get_horse` | 馬のプロフィールと過去の成績（`horse_id` で指定） | — |

出力の各項目は [output.md](output.md) と同じ名前です。ただし、ページのリンク（`url` / `param`）は取り除き、馬には `horse_id`（10桁の数字）を付けています。

### オッズの絞り込み

3連単は3000通りを超えるので、`get_odds` は組み合わせをオッズの低い順に並べ、`limit` 件（既定30件）まで返します。
`horse_nums` を指定すると、その馬番をすべて含む組み合わせだけに絞れます（枠連は枠番）。

```
get_odds(date="2026-11-21", racecourse="京都", race_num=11, bet_type="tierce", horse_nums=[1], limit=5)
```

## 動作について

- 出馬表とオッズは、JRA が今週の開催分しか公開していません。過去のレースは `get_race_result` を使います。
- 指定した日付・競馬場・レース番号から、開催一覧などのページをたどって目的のページを開きます。たどる途中の一覧ページは、短い時間（今週の分は5分、確定済みの過去の分は1日）キャッシュします。オッズは1分です。
- JRA への取得には、非同期版（`aparse()`）の負荷の制限（同時4本、0.25 秒間隔）がそのままかかります。
- 開催やレースが見つからないときは、その日の開催やレース番号の一覧を添えたエラーを返します。
