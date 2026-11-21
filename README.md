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

非同期版の `aparse()` を使うと、複数のページを並行して取得できます（[docs/output.md](docs/output.md#並行して取得する非同期版)）。

各パーサーの出力は [docs/output.md](docs/output.md)、キー名の規則は [docs/naming.md](docs/naming.md) を参照してください。

## 毎年の更新（過去のレース結果のパラメータ）

過去のレース結果を月ごとに開くためのパラメータ（`result_params.ParserRaceParams.get_cname()`）は、
JRA の「過去のレース結果検索」のページにある表を `k2kparser/result_params_data.py` に保存して使っています。
表に翌年の月が加わる12月ごろに、一度実行してください（JRA へのアクセスは1回です）。

```
$ python tools/update_result_params.py --dry-run   # 変更点の確認だけ
$ python tools/update_result_params.py             # result_params_data.py を作り直す
```

## テスト

テストは、JRA のページを保存した HTML（`test/fixtures/`）に対して実行します。JRA サイトにはアクセスしません。
`test/fixtures/` はリポジトリに含めていないので、最初に一度だけ取得してください（約30ページを2秒間隔で取得します）。

```
$ python tools/capture_fixtures.py
$ pytest
```

HTML を取得していない場合、パーサーのテストはスキップされます。
`test/*_test.py` は、JRA サイトに実際にアクセスして動作を確認するための手動スクリプトです（pytest の対象外）。
