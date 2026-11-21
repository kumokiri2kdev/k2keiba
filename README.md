# k2keiba

JRA のホームページから、出馬表・オッズ・レース結果・WIN5・競走馬などの情報を取得するライブラリです。

## インストール

```
$ pip install -e .            # 開発用（コードの変更がすぐ反映される）
$ pip install -e .[video]     # k2kvideo も使う場合（selenium）
$ pip install -e .[test]      # テストも実行する場合（pytest）
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
