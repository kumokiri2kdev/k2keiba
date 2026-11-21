# k2kparser 出力仕様

k2kparser の各パーサーが返すデータの形をまとめた資料です。
キー名の決め方は [naming.md](naming.md) を参照してください。

- 対象バージョン: 0.1.0
- 出力例は 2026年11月21日に JRA サイトから取得したデータを、要素を絞って載せています。

## 目次

- [使い方](#使い方)
- [共通の約束](#共通の約束)
- [トップページ `ParserTop`](#トップページ-parsertop)
- [開催一覧 `ParserDenTop` / `ParserOddsTop` / `ParserResultTop` / `ParserResultKaisaiList`](#開催一覧)
- [出馬表 `ParserDenKaisai` / `ParserDenRace`](#出馬表)
- [オッズ `ParserOddsKaisai` / `OddsParser*`](#オッズ)
- [レース結果 `ParserResultKaisai` / `ParserResultRace`](#レース結果)
- [WIN5 `ParserWin5Kaisai`](#win5-parserwin5kaisai)
- [競走馬 `ParserUma`](#競走馬-parseruma)
- [競走馬検索 `ParserSearch`](#競走馬検索-parsersearch)
- [開催情報 `ParserKaisai`](#開催情報-parserkaisai)
- [特別レース登録馬 `ParserTokubetuTop` / `ParserTokubetuRace`](#特別レース登録馬)
- [開催日程 `ParserCalendar` / `ParserCalendarMonth`](#開催日程)

## 使い方

パーサーを作って `parse()` を呼ぶと、JRA サイトからページを取得して dict や list を返します。
多くのページは、前のページの出力にある `link`（`url` と `param`）を渡して開きます。

```python
from k2kparser import den

days = den.ParserDenTop().parse()                       # 今週の開催一覧
kaisai = days[0]['kaisai'][0]                           # 1日目の最初の開催
races = den.ParserDenKaisai(kaisai['link']['url'], kaisai['link']['param']).parse()
race = races['races'][10]                               # 11R
card = den.ParserDenRace(race['link']['url'], race['link']['param']).parse()
print(card['name'], [h['name'] for h in card['horses']])
```

ページのつながりは次のとおりです。

```
ParserTop ─┬─ ParserDenTop ──── ParserDenKaisai ──── ParserDenRace ─── ParserUma
           │        └─ win5_link ── ParserWin5Kaisai
           ├─ ParserOddsTop ─── ParserOddsKaisai ─── OddsParserWin など
           ├─ ParserResultTop ─ ParserResultKaisai ─ ParserResultRace
           ├─ ParserTokubetuTop ─ ParserTokubetuRace
           └─ ParserSearch ─── ParserUma
ParserResultKaisaiList（過去の月）─ ParserResultKaisai ─ ParserResultRace
ParserCalendar（月）─ ParserCalendarMonth（日）
```

失敗したときは `k2kparser.parser.ParseError` を送出します（HTTP エラーは、そのサブクラスの `ParseErrorHTTP`。`code` に HTTP ステータスが入ります）。

### 並行して取得する（非同期版）

すべてのパーサーに、`parse()` の非同期版 `aparse()` があります（asyncio + aiohttp）。出力は `parse()` と同じです。
`aio.AsyncClient` を共有すると、接続を使い回せます。

```python
import asyncio
from k2kparser import aio, den

async def main():
    async with aio.AsyncClient() as client:
        days = await den.ParserDenTop().aparse(client)
        kaisai = days[0]['kaisai'][0]
        races = await den.ParserDenKaisai(kaisai['link']['url'], kaisai['link']['param']).aparse(client)
        # 12レース分の出馬表を並行して取得
        return await asyncio.gather(*(
            den.ParserDenRace(r['link']['url'], r['link']['param']).aparse(client) for r in races['races']))

cards = asyncio.run(main())
```

JRA に負荷をかけすぎないよう、リクエストはサーバー（ホスト）ごとに常に制限されます。`AsyncClient` を共有していなくても、同じ制限がかかります。

| 制限 | 既定値 | 変更方法 |
|---|---|---|
| 同時に送るリクエスト数 | 4 | `aio.set_limits(max_concurrency=...)` |
| リクエストの開始間隔 | 0.25 秒 | `aio.set_limits(min_interval=...)` |

`set_limits()` は、リクエストを始める前に呼んでください。

そのほかの違い:

- 内部でさらにページを取得するパーサーは、その部分も並行して取得します（`ParserCalendar` の開催日のページ、`ParserResultRace(fetch_video=True)` の映像の情報）。
- 失敗したときのリトライは同期版と同じく3回までですが、404 などのクライアントエラー（408・429 以外の 4xx）はリトライせず、すぐに `ParseErrorHTTP` を送出します。
- 映像の HLS は `video.aget_hls(video_id, contract_company_no, client)` でも取得できます。

## 共通の約束

### 値の形

| 種類 | 形 | 例 |
|---|---|---|
| 日付 | `'YYYY-MM-DD'` の文字列 | `'2026-11-21'` |
| 曜日 | 漢字1文字 | `'土'` |
| 時刻 | `'HH:MM'` の文字列 | `'15:40'` |
| タイム | 0.1 秒単位の int | `693`（1:09.3）、`338`（33.8） |
| 距離 | メートルの int | `1900` |
| 金額 | 円の int | `6340` |
| 斤量・オッズ | float | `57.0`、`15.5` |

ページに年が書かれていない日付（`'11月21日'`）は、リンクのパラメータに年月日が入っていればそこから年を取り、なければ実行した日の年で補います。

### リンク

ページへのリンクは、すべて次の形です。対応するパーサーに `url` と `param` をそのまま渡せます。

```python
{'url': '/JRADB/accessD.html', 'param': 'pw01dde0108202605051120261121/25'}
```

| キー | 意味 |
|---|---|
| `link` | その要素自身のページ |
| `<種類>_link` | 別のページ（`den_link`, `odds_link`, `result_link`, `win5_link`, `prev_link`, `next_link` など） |
| `odds_links` | 券種ごとのオッズページ `{券種: link}` |

### 人（騎手・調教師）

```python
{'name': '武 英智', 'affiliation': '栗東', 'link': {...}}
```

`affiliation`（所属）と `link` は、ページに載っている場合だけ入ります。

### 券種

`win`（単勝）, `place`（複勝）, `wakuren`（枠連）, `umaren`（馬連）, `wide`（ワイド）, `umatan`（馬単）, `trio`（3連複）, `tierce`（3連単）

### 値がないとき

ページに値が載っていないキーは、省略します。各表の「必須」が ○ のキーは、常に入ります。
ただし、次の場合は値として `None` を入れます。

- 結果の着順 `finish_position`：取消・除外・中止などのとき（理由は `finish_status`）
- オッズ：取消・票数なしのとき

## トップページ `ParserTop`

```python
from k2kparser import top
top.ParserTop().parse()
```

JRA トップページのクイックメニューです。list of dict を返します。

| キー | 型 | 必須 | 説明 |
|---|---|---|---|
| `tag` | str | ○ | `'kaisai'`, `'den'`, `'odds'`, `'payout'`, `'result'`, `'tokubetsu'`, `'search'` |
| `link` | link | ○ | メニューのリンク先 |

```python
[{'tag': 'den', 'link': {'url': '/JRADB/accessD.html', 'param': 'pw01dli00/F3'}},
 {'tag': 'odds', 'link': {'url': '/JRADB/accessO.html', 'param': 'pw15oli00/6D'}},
 ...]
```

## 開催一覧

| クラス | 内容 | 呼び出し方 |
|---|---|---|
| `den.ParserDenTop` | 出馬表（今週） | `den.ParserDenTop().parse()` |
| `odds.ParserOddsTop` | オッズ（今週） | `odds.ParserOddsTop().parse()` |
| `result.ParserResultTop` | レース結果（今週） | `result.ParserResultTop().parse()` |
| `result.ParserResultKaisaiList` | レース結果（過去の1か月） | `result.ParserResultKaisaiList('/JRADB/accessS.html', result_params.ParserRaceParams.get_cname(202510)).parse()` |

いずれも、開催日ごとの list of dict を返します。

| キー | 型 | 必須 | 説明 |
|---|---|---|---|
| `date` | str | ○ | 開催日 |
| `weekday` | str | ○ | 曜日 |
| `kaisai` | list | ○ | その日の開催 |
| `kaisai[].kai` | int | ○ | 開催回（5回京都5日 の 5） |
| `kaisai[].racecourse` | str | ○ | 競馬場 |
| `kaisai[].nichi` | int | ○ | 開催日次（5回京都5日 の 5） |
| `kaisai[].link` | link | ○ | 開催ごとのレース一覧（出馬表なら `ParserDenKaisai` に渡す） |
| `win5_link` | link | | WIN5 のページ（出馬表・結果のトップで、WIN5 がある日のみ） |

```python
[{'date': '2026-11-21', 'weekday': '土',
  'kaisai': [{'kai': 5, 'racecourse': '京都', 'nichi': 5,
              'link': {'url': '/JRADB/accessD.html', 'param': 'pw01drl00082026050520261121/3A'}},
             {'kai': 3, 'racecourse': '福島', 'nichi': 5, 'link': {...}}],
  'win5_link': {'url': '/JRADB/access5.html', 'param': 'pw17hde01202611211/EF'}},
 ...]
```

## 出馬表

### 開催ごとのレース一覧 `ParserDenKaisai`

```python
den.ParserDenKaisai(kaisai['link']['url'], kaisai['link']['param']).parse()
```

| キー | 型 | 必須 | 説明 |
|---|---|---|---|
| `date`, `weekday`, `kai`, `racecourse`, `nichi` | | ○ | 開催（[開催一覧](#開催一覧) と同じ） |
| `weather` | str | | 天候 |
| `track_condition` | dict | | 馬場状態 `{'turf': '良', 'dirt': '稍重'}` |
| `races` | list | ○ | レース |
| `races[].race_num` | int | ○ | レース番号 |
| `races[].departure` | str | ○ | 発走時刻 |
| `races[].name` | str | ○ | レース名 |
| `races[].condition` | str | ○ | 条件（一覧の表示どおり。特別レース以外はレース名と同じ） |
| `races[].surface` | str | ○ | `'芝'`, `'ダート'`, `'障害'` |
| `races[].distance` | int | ○ | 距離 |
| `races[].horse_count` | int | | 出走頭数 |
| `races[].link` | link | | 出馬表（`ParserDenRace` に渡す） |
| `races[].odds_link` | link | | オッズ（単勝・複勝） |
| `races[].result_link` | link | | 結果（確定後のみ） |

```python
{'date': '2026-11-21', 'weekday': '土', 'kai': 5, 'racecourse': '京都', 'nichi': 5,
 'weather': '晴', 'track_condition': {'turf': '良', 'dirt': '良'},
 'races': [{'race_num': 1, 'departure': '10:01', 'name': '2歳未勝利牝［指定］',
            'condition': '2歳未勝利牝［指定］', 'surface': 'ダート', 'distance': 1400,
            'horse_count': 15, 'link': {...}, 'odds_link': {...}, 'result_link': {...}},
           ...]}
```

### 出馬表（1レース） `ParserDenRace`

```python
den.ParserDenRace(race['link']['url'], race['link']['param']).parse()
```

レースの情報（出馬表と結果で共通）:

| キー | 型 | 必須 | 説明 |
|---|---|---|---|
| `date`, `weekday`, `kai`, `racecourse`, `nichi` | | ○ | 開催 |
| `race_num` | int | ○ | レース番号 |
| `departure` | str | ○ | 発走時刻 |
| `name` | str | ○ | レース名 |
| `grade` | str | | グレード（`'GⅠ'` など） |
| `category` | str | | 年齢条件（`'3歳以上'`） |
| `class` | str | | クラス（`'オープン'`） |
| `rule` | str | | 競走記号（`'（国際）（特指）'`） |
| `weight_rule` | str | | 重量種別（`'別定'`, `'定量'`, `'馬齢'`, `'ハンデ'`） |
| `distance` | int | ○ | 距離 |
| `surface` | str | ○ | `'芝'`, `'ダート'`, `'障害'` |
| `course` | str | ○ | コース（`'ダート・右'`。ページの表示どおり） |
| `odds_link` | link | | オッズ |
| `result_link` | link | | 結果（確定後のみ） |

出走馬 `horses[]`:

| キー | 型 | 必須 | 説明 |
|---|---|---|---|
| `waku` | int | | 枠番（確定後） |
| `horse_num` | int | | 馬番（確定後） |
| `name` | str | ○ | 馬名 |
| `link` | link | | 馬ページ（`ParserUma` に渡す） |
| `win_odds` | float | | 単勝オッズ |
| `popularity` | int | | 単勝人気 |
| `body_weight`, `body_weight_diff` | int | | 馬体重と増減（発表後） |
| `owner` | str | | 馬主 |
| `trainer` | 人 | ○ | 調教師 |
| `sire`, `dam`, `broodmare_sire` | str | | 父・母・母の父 |
| `hande` | float | | 斤量 |
| `jockey` | 人 | ○ | 騎手 |
| `age` | int | ○ | 馬齢 |
| `sex` | str | ○ | 性別 |
| `coat` | str | | 毛色（`'黒鹿'`） |

```python
{'date': '2026-11-21', 'weekday': '土', 'kai': 5, 'racecourse': '京都', 'nichi': 5,
 'race_num': 11, 'departure': '15:40', 'name': 'シトリンステークス',
 'category': '3歳以上', 'class': 'オープン', 'rule': '（国際）（特指）', 'weight_rule': '別定',
 'distance': 1900, 'surface': 'ダート', 'course': 'ダート・右', 'odds_link': {...},
 'horses': [{'waku': 1, 'horse_num': 1, 'name': 'ヒルノハンブルク', 'link': {...},
             'win_odds': 15.5, 'popularity': 8, 'owner': '(株)ヒルノ',
             'trainer': {'name': '武 英智', 'affiliation': '栗東', 'link': {...}},
             'sire': 'ナダル', 'dam': 'グリントオブライト', 'broodmare_sire': 'ステイゴールド',
             'hande': 57.0, 'jockey': {'name': '北村 友一', 'link': {...}},
             'age': 4, 'sex': '牡', 'coat': '黒鹿'},
            ...]}
```

## オッズ

### 開催ごとのレース一覧 `ParserOddsKaisai`

```python
odds.ParserOddsKaisai(kaisai['link']['url'], kaisai['link']['param']).parse()
```

| キー | 型 | 必須 | 説明 |
|---|---|---|---|
| `date`, `weekday`, `kai`, `racecourse`, `nichi` | | ○ | 開催 |
| `races[].race_num` | int | ○ | レース番号 |
| `races[].name` | str | ○ | レース名 |
| `races[].condition` | str | ○ | 条件 |
| `races[].odds_links` | dict | ○ | 券種ごとのオッズページ `{券種: link}` |

### 1レースのオッズ

`odds_links` の券種に応じて、次のクラスにリンクを渡します。

| 券種 | クラス | `odds` の形 |
|---|---|---|
| `win`（単勝・複勝） | `OddsParserWin` | list of `{'waku', 'horse_num', 'win', 'place': {'min', 'max'}}` |
| `wakuren` | `OddsParserBracketQuinella` | `{'1-2': 12.3}`（枠番の組み合わせ） |
| `umaren` | `OddsParserBracket` | `{'1-2': 55.9}` |
| `wide` | `OddsParserWide` | `{'1-2': {'min': 13.9, 'max': 14.6}}` |
| `umatan` | `OddsParserExacta` | `{'1-2': 129.4}`（1着-2着） |
| `trio` | `OddsParserTrio` | `{'1-2-3': 136.6}` |
| `tierce` | `OddsParserTierce` | `{'1-2-3': 609.5}`（1着-2着-3着） |

```python
odds.OddsParserWin(link['url'], link['param']).parse()
```

| キー | 型 | 必須 | 説明 |
|---|---|---|---|
| `odds_links` | dict | ○ | ほかの券種のオッズページ `{券種: link}` |
| `odds` | list / dict | ○ | オッズ（上の表の形。取消・票数なしは `None`） |
| `votes` | dict | | 投票数 `{券種: 票数, 'total': 合計}`（ページに載っている場合） |
| `updated_at` | str | | オッズの更新時刻 |

```python
{'odds_links': {'win': {...}, 'wakuren': {...}, 'umaren': {...}, 'wide': {...},
                'umatan': {...}, 'trio': {...}, 'tierce': {...}},
 'odds': [{'waku': 1, 'horse_num': 1, 'win': 15.5, 'place': {'min': 3.1, 'max': 4.1}},
          ...],
 'updated_at': '11:19'}
```

## レース結果

### 開催ごとのレース一覧 `ParserResultKaisai`

```python
result.ParserResultKaisai(kaisai['link']['url'], kaisai['link']['param']).parse()
```

[出馬表の開催ごとのレース一覧](#開催ごとのレース一覧-parserdenkaisai) と同じ形です。ただし、次の点が違います。

- `departure`、`weather`、`track_condition`、`result_link` はありません。
- `races[].link` は結果のページ（`ParserResultRace` に渡す）です。

### レース結果（1レース） `ParserResultRace`

```python
result.ParserResultRace(race['link']['url'], race['link']['param']).parse()
result.ParserResultRace(race['link']['url'], race['link']['param'], fetch_video=True).parse()  # 映像の HLS も取得
```

`fetch_video=True` を指定すると、レース映像と全周パトロールの HLS の URL も取得します（映像1本につき、配信 CDN へ2回アクセスします）。
指定しない場合は、ページにある動画 ID だけを返します。

[出馬表（1レース）のレースの情報](#出馬表1レース-parserdenrace) に加えて、次のキーがあります。

| キー | 型 | 必須 | 説明 |
|---|---|---|---|
| `weather` | str | | 天候 |
| `track_condition` | str | | 馬場状態（`'良'`） |
| `den_link` | link | | 出馬表 |
| `horses` | list | ○ | 着順の順 |
| `laps` | list of int | | ラップタイム（0.1 秒） |
| `last_furlongs` | dict | | 上がり `{'4F': 462, '3F': 347}` |
| `corner_orders` | dict | | コーナー通過順 `{'3': '18,8(4,12)…'}` |
| `payouts` | dict | | 払戻 `{券種: list}` |
| `payouts.<券種>[].combination` | str | ○ | 馬番の組み合わせ（`'13-15'`） |
| `payouts.<券種>[].payout` | int | ○ | 払戻金（100円あたり） |
| `payouts.<券種>[].popularity` | int | | 人気 |
| `videos` | dict | | 映像 `{'race': レース映像, 'patrol': 全周パトロール}`（ボタンがある映像のみ） |
| `videos.<種類>.video_id` | str | ○ | 動画 ID（パトロールは末尾に `a`） |
| `videos.<種類>.contract_company_no` | int | ○ | 配信元の番号（1: 過去のレース、2: 最近のレース。ページのボタンから読み取る） |
| `videos.<種類>.master_url` | str | | HLS マスタープレイリストの URL（`fetch_video=True` のとき） |
| `videos.<種類>.resolutions` | list of str | | 解像度（`['480x270', '640x360', '854x480']`。`fetch_video=True` のとき） |
| `videos.<種類>.duration` | int | | 長さ（秒。`fetch_video=True` のとき） |

開催当日は、映像のボタンがレース確定より遅れて追加されることがあります。ボタンがまだないときは、`videos`（または `race` / `patrol`）が入りません。時間をおいて取り直してください。
`fetch_video=True` でも、配信側の準備ができていない映像は `video_id` だけになります（ログに警告を出します）。

動画 ID が分かっていれば、`k2kparser.video.get_hls(video_id, contract_company_no)` で HLS の情報だけを取得することもできます。
配信元はレースの時期で分かれていて、番号を間違えると見つかりません（`VideoError`）。`contract_company_no` は、結果ページから読み取った値を渡してください。

出走馬 `horses[]`:

| キー | 型 | 必須 | 説明 |
|---|---|---|---|
| `finish_position` | int / None | ○ | 着順（取消・中止などは `None`） |
| `finish_status` | str | | `finish_position` が `None` のときの理由（`'取消'` など） |
| `waku`, `horse_num`, `name`, `link`, `age`, `sex`, `hande`, `jockey`, `trainer` | | | 出馬表と同じ |
| `finish_time` | int | | 走破タイム（0.1 秒） |
| `margin` | str | | 着差（`'アタマ'`） |
| `corner_positions` | dict | | コーナーごとの通過順位 `{'3': 9, '4': 8}` |
| `last_3f` | int | | 上がり3F（0.1 秒） |
| `body_weight`, `body_weight_diff` | int | | 馬体重と増減 |
| `popularity` | int | | 単勝人気 |

```python
{'date': '2026-11-21', 'weekday': '土', 'kai': 5, 'racecourse': '京都', 'nichi': 5,
 'race_num': 3, 'departure': '11:00', 'name': '2歳未勝利', 'category': '2歳', 'class': '未勝利',
 'rule': '（混合）［指定］', 'weight_rule': '馬齢', 'distance': 1200, 'surface': '芝', 'course': '芝・右',
 'weather': '晴', 'track_condition': '良', 'den_link': {...}, 'odds_link': {...},
 'horses': [{'finish_position': 1, 'waku': 7, 'horse_num': 13, 'name': 'ジャヤ', 'link': {...},
             'age': 2, 'sex': '牝', 'hande': 55.0, 'jockey': {'name': '田口 貫太', 'link': {...}},
             'finish_time': 693, 'corner_positions': {'3': 9, '4': 8}, 'last_3f': 338,
             'body_weight': 402, 'body_weight_diff': 12,
             'trainer': {'name': '河嶋 宏樹', 'link': {...}}, 'popularity': 13},
            ...],
 'laps': [123, 108, 115, 115, 115, 117],
 'last_furlongs': {'4F': 462, '3F': 347},
 'corner_orders': {'3': '18,8(4,12)9(3,15)6(13,17)5(1,7,11)(14,16)-2', '4': '...'},
 'payouts': {'win': [{'combination': '13', 'payout': 6340, 'popularity': 13}],
             'place': [{'combination': '13', 'payout': 1350, 'popularity': 13}, ...],
             'tierce': [{'combination': '13-15-4', 'payout': 701850, 'popularity': 1269}],
             ...},
 'videos': {'race': {'video_id': '202605080504', 'contract_company_no': 2,
                     'master_url': 'https://eqc834rezx.eq.webcdn.stream.ne.jp/www50/eqc834rezx/jmc_pub/jmc_pd/00372/9b121242bc3c4460b743d9cb48ece2f5.m3u8',
                     'resolutions': ['480x270', '640x360', '854x480'], 'duration': 126},
            'patrol': {'video_id': '202605080504a', 'contract_company_no': 2, 'master_url': '...', 'resolutions': [...], 'duration': 129}}}
```

## WIN5 `ParserWin5Kaisai`

```python
from k2kparser import win5
win5.ParserWin5Kaisai(day['win5_link']['url'], day['win5_link']['param']).parse()
```

| キー | 型 | 必須 | 説明 |
|---|---|---|---|
| `date`, `weekday` | | ○ | 開催日 |
| `prev_link`, `next_link` | link | | 前回・次回の WIN5 |
| `closing_time_pat`, `closing_time_direct` | str | | 締切時刻（ページに載っている場合） |
| `races` | list | ○ | 対象の5レース |
| `races[].leg` | int | ○ | WIN5 の何レース目か（1〜5） |
| `races[].departure` | str | | 発走時刻 |
| `races[].racecourse`, `race_num`, `name` | | | 対象レース |
| `races[].link` | link | | 出馬表（確定後は結果） |
| `races[].winner` | dict | | 勝ち馬 `{'horse_num', 'name', 'link'}`（確定後） |
| `races[].popularity` | int | | 勝ち馬の単勝人気（確定後） |
| `races[].remaining_votes` | int | | そのレース後の残り票数（確定後） |
| `votes` | int | | 発売票数 |
| `sales` | int | | 発売金額 |
| `carryover_in` | int | | 前回からのキャリーオーバー |
| `carryover_out` | int | | 次回へのキャリーオーバー（確定後） |
| `winning_combination` | str | | 的中馬番（`'10-9-7-15-15'`、確定後） |
| `payout` | int | | 払戻金（確定後） |
| `winning_votes` | int | | 的中票数（確定後） |

```python
{'date': '2026-11-15', 'weekday': '日', 'prev_link': {...}, 'next_link': {...},
 'races': [{'leg': 1, 'departure': '14:45', 'racecourse': '東京', 'race_num': 10, 'name': 'ユートピアS',
            'link': {...}, 'winner': {'horse_num': 10, 'name': 'ハニーコム', 'link': {...}},
            'popularity': 10, 'remaining_votes': 83305},
           ...],
 'carryover_in': 0, 'votes': 6655003, 'sales': 665500300,
 'winning_combination': '10-9-7-15-15', 'payout': 11091670, 'winning_votes': 42, 'carryover_out': 0}
```

## 競走馬 `ParserUma`

```python
from k2kparser import uma
uma.ParserUma(horse['link']['url'], horse['link']['param']).parse()
```

| キー | 型 | 必須 | 説明 |
|---|---|---|---|
| `name` | str | | 馬名 |
| `profile` | dict | | プロフィール |
| `profile.sire`, `dam`, `broodmare_sire`, `dam_dam` | str | | 父・母・母の父・母の母 |
| `profile.<上の4つ>_link` | link | | それぞれの馬ページ |
| `profile.sex`, `age`, `coat` | | | 性別・馬齢（int）・毛色 |
| `profile.birthday` | str | | 生年月日 |
| `profile.owner` | str | | 馬主 |
| `profile.trainer` | 人 | | 調教師 |
| `profile.breeding_farm`, `birthplace` | str | | 生産牧場・産地 |
| `profile.name_meaning` | str | | 馬名の意味 |
| `profile.market` | str | | 取引市場 |
| `races` | list | | 出走レース（新しい順） |

`races[]` は `type` で2種類あります。

`type` が `'race'`（出走）:

| キー | 型 | 説明 |
|---|---|---|
| `date`, `racecourse`, `name`, `grade`, `link` | | レース（`link` は結果のページ） |
| `surface`, `distance`, `track_condition` | | コースと馬場状態 |
| `horse_count`, `popularity`, `finish_position`, `finish_status` | | 頭数・人気・着順 |
| `jockey`, `hande`, `body_weight`, `body_weight_diff` | | 騎手・斤量・馬体重 |
| `finish_time` | int | 走破タイム（0.1 秒） |
| `rating` | int | レーティング |
| `winner` | str | 1着馬（この馬が負けたとき） |
| `runner_up` | str | 2着馬（この馬が勝ったとき） |

`type` が `'info'`（登録抹消など、出走以外の行）: `date`, `info`（内容）

```python
{'name': 'ヒルノハンブルク',
 'profile': {'sire': 'ナダル', 'dam': 'グリントオブライト', 'dam_link': {...},
             'broodmare_sire': 'ステイゴールド', 'dam_dam': 'アドマイヤライト', 'sex': '牡', 'age': 4,
             'coat': '黒鹿', 'birthday': '2022-02-07', 'owner': '(株)ヒルノ',
             'trainer': {'name': '武 英智', 'affiliation': '栗東', 'link': {...}},
             'breeding_farm': '目名共同トレーニングセンター', 'birthplace': '新ひだか町',
             'name_meaning': '冠名+ドイツの都市名'},
 'races': [{'type': 'race', 'date': '2026-08-08', 'racecourse': '札幌', 'grade': 'GⅢ', 'name': 'エルムS',
            'link': {...}, 'surface': 'ダート', 'distance': 1700, 'track_condition': '稍重',
            'horse_count': 11, 'popularity': 10, 'finish_position': 7,
            'jockey': {'name': '池添 謙一', 'link': {...}}, 'hande': 57.0, 'body_weight': 472,
            'finish_time': 1053, 'rating': 99, 'winner': 'ルクソールカフェ'},
           ...]}
```

## 競走馬検索 `ParserSearch`

```python
from k2kparser import search
search.ParserSearch('/JRADB/accessR.html', 'pw02uliD1', 'アイアン', category='all').parse()
```

`category` は `'all'`（すべて）、`'active'`（現役）、`'inactive'`（抹消）のいずれかです。list of dict を返します。

| キー | 型 | 必須 | 説明 |
|---|---|---|---|
| `active` | bool | ○ | 現役なら True、抹消なら False |
| `name` | str | ○ | 馬名 |
| `link` | link | | 馬ページ |
| `sex` | str | ○ | 性別 |
| `age` | int | | 馬齢（抹消馬は抹消時） |
| `trainer` | 人 | | 調教師 |

```python
[{'active': False, 'name': 'アイアン', 'link': {...}, 'age': 3, 'sex': '牡',
  'trainer': {'name': '辻野 泰之', 'link': {...}, 'affiliation': '栗東'}},
 ...]
```

## 開催情報 `ParserKaisai`

```python
from k2kparser import kaisai
kaisai.ParserKaisai().parse()
```

| キー | 型 | 必須 | 説明 |
|---|---|---|---|
| `date`, `weekday` | | ○ | 日付 |
| `racecourses` | list | ○ | 開催中の競馬場 |
| `racecourses[].racecourse` | str | ○ | 競馬場 |
| `racecourses[].weather` | str | | 天候 |
| `racecourses[].track_condition` | dict | | 馬場状態 `{'turf': '良', 'dirt': '良'}` |

```python
{'date': '2026-11-21', 'weekday': '土',
 'racecourses': [{'racecourse': '京都', 'weather': '晴', 'track_condition': {'turf': '良', 'dirt': '良'}},
                 {'racecourse': '福島', 'weather': '晴', 'track_condition': {'turf': '重', 'dirt': '不良'}}]}
```

## 特別レース登録馬

### レース一覧 `ParserTokubetuTop`

```python
from k2kparser import tokubetsu
link = next(t['link'] for t in top.ParserTop().parse() if t['tag'] == 'tokubetsu')
tokubetsu.ParserTokubetuTop(link['url'], link['param']).parse()
```

| キー | 型 | 必須 | 説明 |
|---|---|---|---|
| `date`, `weekday` | | ○ | 開催日 |
| `kaisai[].kai`, `racecourse`, `nichi` | | ○ | 開催 |
| `kaisai[].races[].name` | str | ○ | レース名 |
| `kaisai[].races[].grade`, `class` | str | | グレード・クラス |
| `kaisai[].races[].distance`, `surface` | | | 距離・芝/ダート |
| `kaisai[].races[].rule`, `weight_rule` | str | | 競走記号・重量種別 |
| `kaisai[].races[].link` | link | | 登録馬（`ParserTokubetuRace` に渡す） |

### 登録馬 `ParserTokubetuRace`

list of `{'name': 馬名, 'link': 馬ページ, 'hande': 斤量}` を返します。

```python
[{'name': 'アーバンシック', 'link': {...}, 'hande': 58.0}, ...]
```

## 開催日程

### 1か月 `ParserCalendar`

```python
from k2kparser import calendar
calendar.ParserCalendar(year=2026, month=11).parse()     # 省略時は今月
```

開催日ごとに `ParserCalendarMonth` でページを取得します（1か月で10回前後のアクセスになります）。

| キー | 型 | 必須 | 説明 |
|---|---|---|---|
| `date`, `weekday` | | ○ | 開催日 |
| `kaisai` | list | ○ | その日の開催（`ParserCalendarMonth` の出力） |

### 1日 `ParserCalendarMonth`

```python
calendar.ParserCalendarMonth(2026, 11, 1).parse()
```

| キー | 型 | 必須 | 説明 |
|---|---|---|---|
| `kai`, `racecourse`, `nichi` | | ○ | 開催 |
| `races[].race_num` | int | ○ | レース番号 |
| `races[].name` | str | ○ | レース名（特別レース以外はクラス名） |
| `races[].class` | str | ○ | クラス |
| `races[].distance`, `surface` | | ○ | 距離・芝/ダート |
| `races[].rule`, `weight_rule` | str | | 競走記号・重量種別 |
| `races[].departure` | str | | 発走時刻 |

```python
[{'kai': 4, 'racecourse': '東京', 'nichi': 11,
  'races': [{'race_num': 1, 'name': '2歳未勝利', 'class': '2歳未勝利', 'distance': 1400,
             'surface': '芝', 'rule': '（牝）', 'departure': '10:00'},
            ...]},
 ...]
```
