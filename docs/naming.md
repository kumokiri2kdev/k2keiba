# k2kparser 出力キーの命名規則

k2kparser の各パーサーが返す dict のキー名・値の型をそろえるための規則です。
新しいパーサーやキーを足すときも、この規則に従ってください。
各パーサーが実際に返す形は [output.md](output.md) にまとめています。

## 基本方針

1. **英語を基本にする。** 一般的な概念は英語の snake_case で書く（`popularity`, `distance`, `horse_count`）。
2. **英語にしにくい競馬用語はローマ字にする。** 枠番 `waku`、開催回 `kai`、開催日次 `nichi`、斤量 `hande`、券種（`wakuren`, `umaren` など）。ただし、すでに定着している `trio`, `tierce` はそのまま使う。
3. **1つの意味には1つのキーだけを使う。** パーサーが違っても、同じ意味なら同じキーにする。
4. **1つのキーは1つの意味でだけ使う。** たとえば `place` は券種の「複勝」にだけ使い、競馬場は `racecourse`、着順は `finish_position` にする。
5. **値は使える型に変換して返す。** 数値は `int` / `float`、日付は `'YYYY-MM-DD'`、時刻は `'HH:MM'` にする。表示用の文字列が必要なら、別のキーで返す。ページに年が書かれていない日付（`'11月21日'` など）は、リンクのパラメータに年月日が入っていればそこから年を取り、なければ実行した日の年で補う。
6. **値がないときはキーを省略する。** `None` や空文字は入れない。ただし、取消などで「値がないこと自体」に意味がある場合は `None` を入れる（その旨を出力仕様に書く）。

## 共通の部品

### リンク

ページへのリンクは、どこでも `{'url': str, 'param': str}` の形にする。

| キー | 意味 |
|---|---|
| `link` | その要素自身のページ（馬なら馬ページ、レースならレースページ） |
| `<種類>_link` | 別のページへのリンク（`den_link`, `odds_link`, `result_link`, `win5_link`, `prev_link`, `next_link`、血統の `sire_link` など） |
| `odds_links` | 券種ごとのオッズページ `{<券種>: link}` |

### 人（騎手・調教師）

`{'name': str, 'affiliation': str, 'link': link}`。
`affiliation`（所属: `'栗東'`, `'美浦'` など）と `link` は、取れる場合だけ入れる。名前に `'(栗東)'` が付いていたら、`affiliation` に分ける。

## 用語集

| 意味 | キー | 型 | 例 | 置き換えた旧キー |
|---|---|---|---|---|
| 日付 | `date` | str | `'2026-11-21'` | `date`（`'2026年11月21日'`, `'11月21日'`, `20241116` などばらばら） |
| 曜日 | `weekday` | str | `'土'` | `weekday`（`'土曜'`）, `week_day` |
| 開催回 | `kai` | int | `5`（5回京都） | 開催の `index` |
| 開催日次 | `nichi` | int | `5`（5日目） | `nichisuu`, `day` |
| 競馬場 | `racecourse` | str | `'京都'` | `place`, WIN5 の `course` |
| レース番号 | `race_num` | int | `11` | レースの `index`, WIN5 の `id` |
| WIN5 の何レース目か | `leg` | int | `1`〜`5` | WIN5 の `index` |
| 発走時刻 | `departure` | str | `'15:40'` | `departure`（`'15時40分'`） |
| レース名 | `name` | str | `'シトリンステークス'` | |
| グレード | `grade` | str | `'GⅠ'` | |
| 条件（一覧表示用） | `condition` | str | `'2歳1勝クラス（混合）（特指）'` | `cond` |
| 競走の年齢条件 | `category` | str | `'3歳以上'` | |
| クラス | `class` | str | `'オープン'` | |
| 競走記号 | `rule` | str | `'（国際）（特指）'` | |
| 重量種別 | `weight_rule` | str | `'別定'`, `'ハンデ'` | レースの `weight`, カレンダーの `cond` |
| 距離（m） | `distance` | int | `1900` | `dist`, `distance`（文字列のものも） |
| 芝・ダート | `surface` | str | `'芝'`, `'ダート'`, `'障害'` | `course` の一部 |
| コース（表示どおり） | `course` | str | `'ダート・右'` | |
| 天候 | `weather` | str | `'晴'` | |
| 馬場状態 | `track_condition` | str / dict | `'良'` または `{'turf': '良', 'dirt': '稍重'}` | `course_cond`, `condition`, `turf`/`dirt` |
| 出走頭数 | `horse_count` | int | `16` | `uma_num`, `number` |
| 枠番 | `waku` | int | `1` | |
| 馬番 | `horse_num` | int | `1` | `num`, `number` |
| 馬名 | `name` | str | | |
| 馬齢 | `age` | int | `4` | 文字列のものも |
| 性別 | `sex` | str | `'牡'` | |
| 毛色 | `coat` | str | `'黒鹿'`（末尾の「毛」は付けない） | `hair` |
| 生年月日 | `birthday` | str | `'2022-02-07'` | |
| 父 | `sire` | str | | `father` |
| 母 | `dam` | str | | `mare`, `mother` |
| 母の父 | `broodmare_sire` | str | | `bms`, `bmr` |
| 母の母 | `dam_dam` | str | | `mother_of_mother` |
| 馬主 | `owner` | str | | |
| 生産牧場 | `breeding_farm` | str | | |
| 産地 | `birthplace` | str | `'新ひだか町'` | `breeding_center` |
| 馬名の意味 | `name_meaning` | str | | `origin_of_name` |
| 取引市場 | `market` | str | | （新規） |
| 騎手 | `jockey` | 人 | | `jockey`, `jokey` |
| 調教師 | `trainer` | 人 | | 文字列のものも |
| 所属 | `affiliation` | str | `'栗東'` | 調教師名の `'(栗東)'` |
| 斤量（kg） | `hande` | float | `57.0` | 文字列のものも |
| 馬体重（kg） | `body_weight` | int | `460` | 馬の `weight` |
| 馬体重増減（kg） | `body_weight_diff` | int | `-4` | `weight_diff` |
| 単勝オッズ | `win_odds` | float | `15.5` | 出馬表の `odds` |
| 人気 | `popularity` | int | `1` | `odds_rank`, `win_fav`, `fav`, `ninki` |
| 着順 | `finish_position` | int / None | `1`（取消・中止などは `None`） | 結果の `place`, 馬ページの `rank` |
| 着順の注記 | `finish_status` | str | `'取消'`, `'中止'` | （新規） |
| 走破タイム（0.1秒単位） | `finish_time` | int | `693`（1:09.3） | `finish`, 馬ページの `time` |
| 上がり3F（0.1秒単位） | `last_3f` | int | `336` | `flap` |
| 着差 | `margin` | str | `'クビ'` | |
| レーティング | `rating` | int | `99` | （新規） |
| 1着馬・2着馬（馬ページ） | `winner`, `runner_up` | str | | `winner` |
| 金額（円） | `payout`, `sales` など | int | | `price`, `pay_back`, `bet_price` |

## 券種

券種は、どのパーサーでも次のキーにそろえる（払戻 `payouts`、オッズのリンク `odds_links`、投票数 `votes` など）。

| 券種 | キー | 置き換えた旧キー |
|---|---|---|
| 単勝 | `win` | `win`, `tanpuku`（単複ページへのリンク） |
| 複勝 | `place` | |
| 枠連 | `wakuren` | |
| 馬連 | `umaren` | |
| ワイド | `wide` | |
| 馬単 | `umatan` | |
| 3連複 | `trio` | |
| 3連単 | `tierce` | |

## 0.0.57 からの構造の変更

用語集の置き換えに加えて、0.1.0 で次の構造を変えた。

- **レース単体のページ（出馬表・結果）**：開催回 `kai` とレース番号 `race_num` を別のキーで持つ。以前は `index` が開催回からレース番号に上書きされ、開催回が失われていた。
- **結果のレース**：`surface`（芝/ダート）、`course`（`'芝・右'`）、`track_condition`（`'良'`）を別々に持つ。以前は `course` が上書きされていた。
- **払戻**：`pay_off` → `payouts`。各要素を `{'combination': '13-15', 'payout': 11710, 'popularity': 32}` にした（旧 `tag`, `price`, `fav`）。
- **ラップ**：`laps` は 0.1 秒単位の int のリストのまま。`ftime` → `last_furlongs`（`{'3F': 384, '4F': 495}`）。
- **通過順**：馬ごとの `corner` → `corner_positions`、レース全体の `corner` → `corner_orders`。
- **オッズ**：`links` → `odds_links`、`vote` → `votes`、`refresh`/`time` → `updated_at`（`'HH:MM'`）。取消や票数なしのオッズは `None`（以前は文字列のまま、または捨てていた）。
- **WIN5**：`list` → `races`、`race.url` → `link`、`winner` は `{'horse_num', 'name', 'link'}` に平らにした。総計の `indexes` → `winning_combination`、`pay_back` → `payout`、`remaining`（的中票数）→ `winning_votes`、各レースの `remaining`（残り票数）→ `remaining_votes`、`bets` → `votes`、`bet_price` → `sales`、`carried_over` → `carryover_in`、`carry_over` → `carryover_out`、`prev_url`/`next_url` → `prev_link`/`next_link`。
- **馬ページ**：`basic.name` → 上の階層の `name`。`profile` のキーは用語集に合わせた。成績 `races` の値は型を変換した（以前はすべて文字列）。
- **開催情報**：`places` → `racecourses`、`place` → `racecourse`、`condition` → `track_condition`。
- **開催一覧のトップ（出馬表・オッズ・結果）**：`kaisai` の要素を `{'kai', 'nichi', 'racecourse', 'link'}` にした。
- **トップページ**：`tag` の値を `kaisai`, `den`, `odds`, `payout`, `result`, `tokubetsu`, `search` にそろえた（旧 `shutuba`, `haraimodoshi`, `tokubetu`）。
- **開催一覧**：`'5回東京8日'` のような文字列は、`kai`, `racecourse`, `nichi` に分解して返す（カレンダー、特別レース登録馬）。
- **カレンダー**：`{'year', 'month', 'day', 'races'}` → `{'date', 'weekday', 'kaisai'}`。
