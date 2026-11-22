# k2keiba

JRA のホームページから、出馬表・オッズ・レース結果・WIN5・競走馬などの情報を取得するライブラリです。

## インストール

```
$ pip install -e .            # 開発用（コードの変更がすぐ反映される）
$ pip install -e .[test]      # テストも実行する場合（pytest）
$ pip install -e .[mcp]       # MCP サーバーも使う場合
```

配布用のパッケージを作る場合:

```
$ python setup.py sdist
```

## 使い方

```python
from k2kparser import den

days = den.ParserDenTop().parse()
kaisai = days[0]['kaisai'][0]
races = den.ParserDenKaisai(kaisai['link']['url'], kaisai['link']['param']).parse()
```

非同期版の `aparse()` を使うと、複数のページを並行して取得できます（[docs/output.md](docs/output.md#並行して取得する非同期版)）。

Claude Code・Claude Desktop・Codex・ChatGPT などから使う MCP サーバーもあります（[docs/mcp.md](docs/mcp.md)）。

各パーサーの出力は [docs/output.md](docs/output.md)、キー名の規則は [docs/naming.md](docs/naming.md) を参照してください。

## テスト

テストは、JRA のページを保存した HTML（`test/fixtures/`）に対して実行します。JRA サイトにはアクセスしません。
`test/fixtures/` はリポジトリに含めていないので、最初に一度だけ取得してください（約30ページを2秒間隔で取得します）。

```
$ python tools/capture_fixtures.py
$ pytest
```

HTML を取得していない場合、パーサーのテストはスキップされます。
`test/*_test.py` は、JRA サイトに実際にアクセスして動作を確認するための手動スクリプトです（pytest の対象外）。

## 注意

- このライブラリは JRA（日本中央競馬会）の公式なものではなく、JRA とは関係ありません。
- 取得するデータ（出馬表、オッズ、レース結果、映像など）の権利は JRA などの権利者にあります。利用するときは、JRA のサイトの利用条件に従ってください。
- JRA のサイトに負荷をかけないでください。非同期版の取得には、同時接続数と間隔の制限がかかっています（`aio.set_limits()`）。制限を緩めるときは注意してください。
- k2kodds（買い方の比較）の確率は、オッズから読み取った市場の見立てです。予想や投票の推奨ではありません。馬券の購入は自己責任で行ってください。
- ページの構造が変わると、パーサーが正しく動かなくなることがあります。取得結果の正確さは保証しません。

## ライセンス

[MIT License](LICENSE)

ライセンスの対象は、このリポジトリのコードです。JRA のデータは含みません。
