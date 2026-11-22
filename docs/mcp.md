# k2keiba MCP サーバー

k2keiba の機能を MCP（Model Context Protocol）のツールとして公開するサーバーです。
Claude Code、Claude Desktop、Codex、ChatGPT などから、「今週の京都11Rの出馬表を見せて」「2025年10月4日の東京1Rの結果は？」のように頼むと、モデルがツールを使って JRA のサイトから取得します。

## インストール

```
$ pip install -e '.[mcp]'
```

`k2keiba-mcp` コマンドが入ります（`python -m k2kmcp` でも起動できます）。通信は stdio です。
`--http` を付けると HTTP（Streamable HTTP）で起動します（[HTTP で使う](#http-で使う)）。

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

### Codex

`~/.codex/config.toml` に追加します（CLI と IDE 拡張で共通です）。

```toml
[mcp_servers.k2keiba]
command = "/path/to/venv/bin/k2keiba-mcp"
```

`codex mcp add k2keiba -- /path/to/venv/bin/k2keiba-mcp` でも同じです。

Windows 上の Codex から WSL 上の環境を使う場合は、`C:\Users\<ユーザー>\.codex\config.toml` に `wsl.exe` 経由で書きます。

```toml
[mcp_servers.k2keiba]
command = "wsl.exe"
args = ["-e", "/path/to/venv/bin/k2keiba-mcp"]
```

既定でないディストリビューションに入れた場合は、`args = ["-d", "Ubuntu", "-e", ...]` のように `-d` で指定します。

## HTTP で使う

ChatGPT のように、サーバーをクラウド側から呼び出すクライアントは、stdio の MCP サーバーを起動できません。
その場合は HTTP で起動し、HTTPS の URL で公開します。

```
$ k2keiba-mcp --http                          # http://127.0.0.1:8000/mcp
$ k2keiba-mcp --http --host 0.0.0.0 --port 8080
```

| オプション | 内容 |
|---|---|
| `--http` | stdio の代わりに HTTP で起動します。エンドポイントは `/mcp` です |
| `--host` | 待ち受けるアドレス（既定 `127.0.0.1`） |
| `--port` | ポート（既定 `8000`） |
| `--allow-host NAME` | 受け付ける Host ヘッダーを追加します（複数指定できます） |

`127.0.0.1` で待ち受けるとき、MCP の SDK は DNS リバインディング対策として、Host ヘッダーが `localhost` などのリクエストしか受け付けません（それ以外は 421 を返します）。
トンネルやリバースプロキシを経由すると Host ヘッダーは公開側の名前になるので、その名前を `--allow-host` で指定します。

### トンネルで公開する例

cloudflared のクイックトンネルを使う場合です。

```
$ cloudflared tunnel --url http://localhost:8000
  ...  https://xxxx-yyyy.trycloudflare.com  ...
$ k2keiba-mcp --http --allow-host xxxx-yyyy.trycloudflare.com
```

クライアントには `https://xxxx-yyyy.trycloudflare.com/mcp` を登録します。クイックトンネルの名前は起動するたびに変わります。

ChatGPT では、設定の「アプリとコネクタ」→「詳細設定」で開発者モードをオンにし、上の URL でアプリ（コネクタ）を作成します（画面の名前は時期によって変わります）。

公開した URL は、知っている人なら誰でも呼び出せ、そのたびに手元から JRA へアクセスします。使わないときはトンネルを止めてください。

## ツール

すべて読み取り専用です。日付は `YYYY-MM-DD`、競馬場は日本語名（`東京`、`京都` など）か、ローマ字名（`Tokyo`、`Kyoto` など）で指定します。

| ツール | 内容 | 対象期間 |
|---|---|---|
| `list_meetings` | 今週の開催（日付、競馬場、開催回・日次、WIN5 の有無） | 今週 |
| `get_track_conditions` | 天候と馬場状態 | 今週 |
| `list_races` | 開催のレース一覧（距離、芝/ダート、頭数、発走時刻） | 今週・過去 |
| `get_race_card` | 出馬表（枠番、馬番、`horse_id`、騎手、斤量、血統、馬体重、単勝オッズ・人気） | 今週 |
| `get_odds` | オッズ（`bet_type`: `win`, `wakuren`, `umaren`, `wide`, `umatan`, `trio`, `tierce`）。過去のレースは確定オッズ | 今週・過去 |
| `get_race_result` | レース結果（着順、タイム、上がり、通過順、払戻）。`include_video` で映像の HLS も取得 | 今週・過去（1986年〜） |
| `compare_bets` | 買い方の比較（当たる確率、当たったときのリターン、決着ごとの払戻）。[k2kodds.md](k2kodds.md) | 今週・過去 |
| `search_horses` | 馬名での検索（カタカナ、前方一致） | — |
| `get_horse` | 馬のプロフィールと過去の成績（`horse_id` で指定） | — |

出力の各項目は [output.md](output.md) と同じ名前です。ただし、ページのリンク（`url` / `param`）は取り除き、馬には `horse_id`（10桁の数字）を付けています。

### オッズの絞り込み

3連単は3000通りを超えるので、`get_odds` は組み合わせをオッズの低い順に並べ、`limit` 件（既定30件）まで返します。
`horse_nums` を指定すると、その馬番をすべて含む組み合わせだけに絞れます（枠連は枠番）。

```
get_odds(date="2026-11-21", racecourse="京都", race_num=11, bet_type="tierce", horse_nums=[1], limit=5)
```

## 使い方

登録すると、会話の中でモデルが必要なツールを選んで呼び出します。ツール名を覚える必要はありません。

### 頼み方の例

| 頼み方 | 使われるツール |
|---|---|
| 今週の開催は？ | `list_meetings` |
| 今週の京都11Rの出馬表を見せて | `get_race_card` |
| 京都11Rの3連単、5番を含む人気上位を10件 | `get_odds` |
| 2025年10月4日の東京11Rの結果と払戻は？ | `get_race_result` |
| 勝ち馬のこれまでの成績は？ | `get_horse` |
| 「イクイノックス」を検索して | `search_horses` |

### 買い方の比較（compare_bets）

印（本命・対抗・連下）と予算、比べたい案を伝えます。
今週のレースは今のオッズ、過去のレースは確定オッズで比べます（終わったレースの振り返りにも使えます）。

```
2026-11-21 京都11R、予算 3000 円。
本命 12、対抗 10・14、連下 9・1・15・5。
基本案：3連複 12-10,14-10,14,9,1,15,5
比べたい案：連下を1頭ずつ外した案、馬連 12-10,14、3連単 12→10,14→相手全部
compare_bets で比べて、トリガミになる買い目があれば教えて。
```

案ごとに、点数、当たる確率、当たったときのリターン（最小 / 中央 / 最大）、トリガミの確率と、決着ごとの払戻の表が返ります。
確率はオッズから読んだ市場の見立てで、予想ではありません（[k2kodds.md](k2kodds.md)）。

サーバーは接続のときに、「印と予算を言われたら compare_bets を使う」などの使い方をモデルに伝えています。
クライアントによってはこれが弱いことがあるので、ツール名を頼み方に入れると確実です。

### いつも守る指示を書いておく（Codex）

Codex では `~/.codex/AGENTS.md`（Windows は `C:\Users\<ユーザー>\.codex\AGENTS.md`）に書いておくと、毎回の指示を短くできます。
Claude Code では `~/.claude/CLAUDE.md` に同じことを書けます。

```markdown
## 馬券の分析（k2keiba MCP）
- 印（本命・対抗・連下）と予算を伝えられたら、k2keiba の compare_bets で比較する。オッズや確率を自分で暗算しない。
- 基本案に加えて、変形案（連下を1頭ずつ外す、券種を変える、allocation='payout'）を作り、10案以内でまとめて1回で呼ぶ。
- 結果は表にする：点数、的中率、当たったときのリターン（最小 / 中央 / 最大）、トリガミの確率。
- finishes を使って、「外した馬が来たときに何を失うか」を具体的に説明する。
- 確率はオッズから読んだ市場の見立てで、予想ではないことを添える。
- 馬番がわからないときは、get_race_card（過去のレースは get_race_result）で確認する。
```

## 動作について

- 出馬表は、JRA が今週の開催分しか公開していません。過去のレースは `get_race_result` を使います。
- オッズは、今週の一覧にないレースでは、結果ページのリンクから確定オッズのページを開きます。
- 指定した日付・競馬場・レース番号から、開催一覧などのページをたどって目的のページを開きます。たどる途中の一覧ページは、短い時間（今週の分は5分、確定済みの過去の分は1日）キャッシュします。今週のオッズは1分、確定オッズは1日です。
- JRA への取得には、非同期版（`aparse()`）の負荷の制限（同時4本、0.25 秒間隔）がそのままかかります。
- 開催やレースが見つからないときは、その日の開催やレース番号の一覧を添えたエラーを返します。

## 更新したとき・困ったとき

### コードを更新したとき

`pip install -e` で入れていれば、再インストールは要りません。サーバーが起動するときに、その時点のコードを読み込みます。
ただし、動いているサーバーは古いコードのままなので、クライアントを起動し直します。

- Claude Code：新しいセッションを開きます。
- Codex / Claude Desktop：アプリを完全に終了してから起動します（Windows ではタスクトレイに残っていないか確認します）。

`setup.py` にパッケージを追加したときは、`pip install -e '.[mcp]'` をやり直します。
動くのは、作業フォルダでチェックアウトしているブランチのコードです。

### 新しいツールが出てこないとき

1. クライアントで `/mcp`（Claude Code / Codex）を実行し、k2keiba のツールの一覧を確認します。
2. 古いサーバーが残っていないか確認します。起動時刻がコードを更新した時刻より前なら、古いサーバーです。

   ```
   $ ps -eo pid,lstart,args | grep "[k]2keiba-mcp"
   ```

   Windows の Codex などから `wsl.exe` 経由で起動したサーバーは、親プロセスが `/init` になります
   （`ps -o ppid= -p <PID>` で親を確認できます）。クライアントを終了しても残っていれば、`kill <PID>` で止めてから起動し直します。
3. サーバー単体で起動できるか確認します。何も表示されずに入力待ちになれば正常です（Ctrl+C で止めます）。

   ```
   $ /path/to/venv/bin/k2keiba-mcp
   ```
