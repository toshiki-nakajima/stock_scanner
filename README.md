# 📈 Stock Signal Scanner

ボリンジャーバンド・出来高急増・MAクロスで日本株・米国株のシグナルを自動スキャンし、**スコアリングしてCSVに出力**するPythonスクリプトです。

---

## 🔑 APIキー・認証について

**APIキーもアカウント登録も不要です。**

`yfinance` ライブラリがYahoo! Financeの公開データに直接アクセスします。認証設定は一切不要で、インストールしてすぐ動きます。

> ⚠️ **注意事項**
> - yfinanceはYahoo, Inc.の公式ライブラリではありません（非公式ラッパー）
> - **個人利用・研究・教育目的**での使用を想定しています
> - 商用利用はYahoo!の利用規約に抵触する可能性があります
> - Yahoo! Finance側の仕様変更により一時的にデータ取得が失敗する場合があります

---

## 🚀 セットアップ

### 1. リポジトリをクローン

```bash
git clone https://github.com/YOUR_USERNAME/stock-signal-scanner.git
cd stock-signal-scanner
```

### 2. Python バージョン確認（3.8以上が必要）

```bash
python --version
```

### 3. 依存ライブラリのインストール

```bash
pip install -r requirements.txt
```

---

## 📦 ファイル構成

```
stock-signal-scanner/
├── stock_scanner.py   # メインスクリプト
├── requirements.txt   # 依存ライブラリ
└── README.md          # このファイル
```

---

## ▶️ 使い方

### 基本実行

```bash
python stock_scanner.py
```

### ユニバース指定

```bash
python stock_scanner.py --universe nikkei   # 日経225代表銘柄
python stock_scanner.py --universe sp500    # S&P500代表銘柄
python stock_scanner.py --universe both     # 両方（デフォルト）
```

### 個別ティッカー指定

```bash
# 日本株は末尾に .T が必要
python stock_scanner.py --tickers 7203.T 9984.T AAPL NVDA
```

### スコアで絞り込み

```bash
# 50点以上のみ表示
python stock_scanner.py --min-score 50

# 80点以上（★★★）のみ表示
python stock_scanner.py --min-score 80
```

### 全件出力（シグナルなし銘柄も含む）

```bash
python stock_scanner.py --all-results
```

### 出力ファイル名変更

```bash
python stock_scanner.py --out my_result.csv
```

### 組み合わせ例

```bash
# 日経225を高スコア順にCSV出力
python stock_scanner.py --universe nikkei --min-score 50 --out nikkei_top.csv

# 個別ウォッチリストをスキャン
python stock_scanner.py --tickers 7203.T 6758.T 9984.T AAPL NVDA --out watchlist.csv
```

---

## 🏆 スコアリング設計

シグナルの重要度に応じて点数を付けてランキングします。

| シグナル | 点数 | 考え方 |
|---|---|---|
| **BB上抜け / BB下抜け** | 40点 | メインシグナル（価格の方向性） |
| **出来高急増**（基本） | 30点 | 価格変動の信頼性を補強 |
| **出来高ボーナス** | +5〜10点 | 3倍→+5pt、5倍以上→+10pt |
| **バンド収縮** | 20点 | ブレイクアウト前兆 |
| **MAクロス** | 10点 | トレンド方向の確認 |
| **合計最大** | **110点** | |

### ランク基準

| ランク | スコア | 意味 |
|---|---|---|
| ★★★ | 80点以上 | 複数シグナルが重なる強い注目銘柄 |
| ★★☆ | 50〜79点 | BBと出来高など2つのシグナルが一致 |
| ★☆☆ | 20〜49点 | 単一シグナルあり、様子見 |

---

## 📊 検出シグナル一覧

| シグナル | 条件 |
|---|---|
| **BB上抜け** | 終値がボリンジャーバンド上限（20日・2σ）を上回っている |
| **BB下抜け** | 終値がボリンジャーバンド下限を下回っている |
| **バンド収縮** | バンド幅が中央値の8%未満（低ボラティリティ・ブレイクアウト前兆） |
| **出来高急増** | 当日出来高が20日平均出来高の2倍以上 |
| **ゴールデンC** | 直近3日以内にMA5がMA25を上抜けた |
| **デッドC** | 直近3日以内にMA5がMA25を下抜けた |

---

## 📁 出力CSVの列

| 列名 | 説明 |
|---|---|
| score | 合計スコア（高いほど注目度が高い） |
| rank | ★の段階評価 |
| ticker | ティッカーシンボル |
| price | 最新終値 |
| change% | 前日比変化率（%） |
| signals | 検出シグナル（カンマ区切り） |
| pt_BB | BBシグナルの得点 |
| pt_出来高 | 出来高シグナルの得点（ボーナス込み） |
| pt_収縮 | バンド収縮の得点 |
| pt_MA | MAクロスの得点 |
| BB上限 / BB中央 / BB下限 | ボリンジャーバンド値 |
| BW% | バンド幅（%） |
| MA5 / MA25 | 移動平均線 |
| 出来高比 | 当日出来高 ÷ 20日平均出来高 |

---

## ⚙️ 動作要件

- Python 3.8以上
- インターネット接続

---

## 🚨 トラブルシューティング・設計メモ

会話・開発経緯から得られた補足情報をランク付きで記録しています。

### ★★★ 必須級（トラブル時に最初に確認）

**ローカル実行が前提 — サーバー・CI環境では動かない**

yfinanceは `finance.yahoo.com` へHTTPリクエストを送りますが、制限されたネットワーク環境（Dockerコンテナ、GitHub Actions、AWS Lambdaなど）では `HTTP 403: Host not in allowlist` エラーで弾かれる場合があります。動作確認済みの環境はローカルPCのみです。CI/CDで自動実行したい場合はプロキシまたは別のデータソースへの切り替えが必要です。

```
# エラー例
HTTP Error 403: Host not in allowlist
Failed to get ticker 'AAPL': AttributeError("'Response' object has no attribute 'get'")
```

**Yahoo!側の仕様変更で突然動かなくなるリスク**

yfinanceはYahoo! Financeの非公式ラッパーです。Yahoo!がサイト構造やAPIエンドポイントを変更すると予告なくデータ取得が失敗します。「昨日まで動いていたのに今日動かない」場合はまずyfinanceのバージョンアップを試してください。

```bash
pip install --upgrade yfinance
```

---

### ★★☆ 設計判断の根拠

**出来高ボーナスを比率連動にした理由**

出来高シグナルを単純な「2倍フラグ（ON/OFF）」ではなく、比率に応じた加点方式（3倍→+5pt、5倍以上→+10pt）にしています。これは「出来高が大きいほど価格変動の信頼性が上がる」という考え方に基づいています。閾値を変更したい場合は `volume_bonus()` 関数を直接編集してください。

**robots.txt確認済み（株価取得パスは制限対象外）**

Yahoo! Finance の robots.txt を確認した結果、Disallow対象は `/r/`, `/_finance_doubledown/`, `/caas/` などの内部管理パスのみです。yfinanceが使う株価・履歴データ取得のエンドポイントはDisallow対象に含まれていません（2025年5月時点）。

---

### ★☆☆ 精度改善の出発点

**MAクロス判定は粗い実装**

現在のゴールデンクロス/デッドクロス判定は「直近3日以内に交差があったか」を確認するだけで、厳密なクロス発生日は特定していません。より正確に判定したい場合は、日ごとの前後比較に変更することで対応できます。

**日足単一時間軸のみ**

現在は日足（1d）データのみで判定しています。週足・月足のトレンドは考慮していないため、短期的なノイズを拾う場合があります。週足対応に拡張する場合は `interval="1wk"` に変更して別途スキャンする方法が手軽です。

**本スクリプトの位置づけ**

シグナルが出た＝買い/売りサインではありません。あくまで一次スクリーニング用です。最終的な売買判断にはチャート確認や他指標との組み合わせが必要です。

---

## 📄 ライセンス

MIT License

---

## 🔗 参考

- [yfinance GitHub](https://github.com/ranaroussi/yfinance) — Ran Aroussi（イスラエル人個人開発者）作。Apache License。GitHubスター数1.5万以上の事実上の標準ライブラリ
- [Yahoo! Finance 利用規約](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html)
