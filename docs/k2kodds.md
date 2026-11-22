# k2kodds：買い方の比較

レースの買い方（券種、フォーメーション、ボックス、予算の配分）を、**当たる確率**と**当たったときのリターン**で比べるライブラリです。
「D を外すと当たる確率はどれだけ下がり、リターンはどれだけ上がるか」「3連複より馬連の方がよいか」のような比較に使います。

k2kparser にもネットワークにも依存しません。入力は、k2kparser のオッズの出力（[output.md](output.md)）と同じ形の dict です。
MCP サーバーからは `compare_bets` ツールとして使えます（[mcp.md](mcp.md)）。

```python
from k2kparser import odds as po
from k2kodds import compare

odds = {'tierce': po.OddsParserTierce(url, param).parse()['odds'],
        'trio': po.OddsParserTrio(url, param).parse()['odds'],
        'umaren': po.OddsParserBracket(url, param).parse()['odds']}

A, B, C, D, E, F = 14, 2, 8, 1, 5, 11
result = compare([
    {'name': '3連複 A-BC-BCDEF', 'bets': [{'bet_type': 'trio', 'formation': [[A], [B, C], [B, C, D, E, F]]}]},
    {'name': 'D を外す',         'bets': [{'bet_type': 'trio', 'formation': [[A], [B, C], [B, C, E, F]]}]},
    {'name': '馬連 A-BCDEF',     'bets': [{'bet_type': 'umaren', 'formation': [[A], [B, C, D, E, F]]}]},
], odds, budget=3000)
```

## 当たる確率の求め方

3連単のオッズから、1〜3着のすべての並びについて、市場が見ている確率を求めます。
オッズは「(1 − 控除率) ÷ 確率」なので、`1 / オッズ` を合計が 1 になるように割り戻します（控除率は消えます）。
どの券種も 1〜3着の並びで当たり外れが決まるので、券種が違う買い方も同じ物差しで比べられます。

3連単のオッズを渡さないときは、単勝のオッズから Harville モデルで求めます。`outcomes` 引数で自分の確率を渡すこともできます。

これは市場の見立てで、予想ではありません。

## 入力

### `compare(strategies, odds, budget=3000, allocation='equal', wide='min', outcomes=None, table_size=20)`

| 引数 | 内容 |
|---|---|
| `strategies` | 比べる買い方のリスト。`{'name': 名前（重複不可）, 'bets': [bet, ...], 'allocation': 任意}` |
| `odds` | `{券種: オッズ}`。使う券種すべてと、確率用の `tierce`（または `win`）が必要です。枠連には枠番を知るために `win` も必要です |
| `budget` | 買い方ごとの予算（円） |
| `allocation` | `equal`（各点同額。余りは使わない）/ `payout`（どれが当たっても払戻がほぼ同じになるよう、オッズの低い点に厚く。予算を使い切る） |
| `wide` | ワイドのオッズの幅のどちらを使うか：`min` / `max` / `mid` |
| `table_size` | 決着の表の最大行数 |

bet は、`bet_type` と次のどれか1つです。`amount`（1点あたりの金額、100円単位）を付けると、その金額で固定し、残りの予算をほかの点に配分します。

| 指定 | 例 | 内容 |
|---|---|---|
| `formation` | `[[A], [B, C], [B, C, D]]` | 着順ごとのリスト。馬連・ワイド・3連複では「軸」と「相手」のグループとして扱います |
| `box` | `[A, B, C]` | ボックス |
| `horses` | `[A, B]` | `box` と同じ（単勝向け） |
| `combinations` | `['1-2-3', '1-2-5']` | 買い目を直接指定 |

`bet_type` は `win`（単勝）、`wakuren`（枠連、枠番で指定）、`umaren`、`wide`、`umatan`、`trio`、`tierce` です。
オッズのない買い目（取消など）と出走しない馬の買い目は、`excluded` に理由とともに入れて、計算から外します。

## 出力

```python
{'probability_source': 'tierce odds',
 'budget': 3000,
 'strategies': [
     {'name': 'D を外す', 'points': 5, 'spent': 3000,
      'hit_probability': 0.1216,          # 当たる確率
      'profit_probability': 0.1216,       # 払戻 > 投資
      'torigami_probability': 0,          # 当たったが払戻 < 投資
      'market_return_rate': 0.827,        # 市場の確率で見た 払戻の平均 ÷ 投資（控除率のため 0.7〜0.8 程度）
      'payout_when_hit': {'min': 12780, 'median': 22680, 'max': 31260},    # 当たったときの払戻（円）
      'return_when_hit': {'min': 4.26, 'median': 7.56, 'max': 10.42},      # 払戻 ÷ 投資
      'tickets': [{'bet_type': 'trio', 'combination': '2-8-14', 'odds': 42.6, 'amount': 600, 'payout': 25560}, ...],
      'unused_budget': 200,               # equal で余った予算（あれば）
      'excluded': [...]},                 # 計算から外した買い目（あれば）
     ...],
 'finishes': [                            # どれかの買い方が当たる決着（確率の高い順）
     {'finish': '2-8-14 / 8-2-14', 'probability': 0.0153,
      'payouts': {'3連複 A-BC-BCDEF': 8520, 'D を外す': 12780, '馬連 A-BCDEF': 0}},
     {'finish': '1-2-14 (any order)', ...},   # 6通りの並びすべてで払戻が同じとき
     ...],
 'finishes_omitted': 140,                 # table_size を超えて省いた行数
 'omitted_probability': 0.21,
 'no_hit_probability': 0.66,              # どの買い方も外れる確率
 'horses': {14: {'win': 0.17, 'top2': 0.31, 'top3': 0.44}, ...}}   # 使った馬の 1着 / 2着以内 / 3着以内の確率
```

払戻は、今のオッズで計算した見込みです。オッズは締め切りまで変わります。
