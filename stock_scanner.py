"""
stock_scanner.py
────────────────────────────────────────────────
ボリンジャーバンド・出来高急増・MAクロスで
シグナルあり銘柄をスコアリングしてCSV出力するスクリプト。

【スコアリング設計】
  BB上抜け / BB下抜け  : 40点  ← メインシグナル
  出来高急増           : 30点  ← 確度補強（出来高比率で加点あり）
  バンド収縮           : 20点  ← ブレイクアウト前兆
  MAクロス             : 10点  ← 方向感確認
  出来高ボーナス       : 最大+10点（3倍→+5pt、5倍→+10pt）
  合計最大             : 110点

使い方:
  pip install yfinance pandas numpy
  python stock_scanner.py                        # デフォルト: 日経225代表 + S&P500代表
  python stock_scanner.py --universe nikkei      # 日経225代表のみ
  python stock_scanner.py --universe sp500       # S&P500代表のみ
  python stock_scanner.py --universe both        # 両方
  python stock_scanner.py --tickers 7203.T AAPL  # 個別指定
  python stock_scanner.py --min-score 50         # スコア50点以上のみ出力
  python stock_scanner.py --all-results          # スコア0銘柄も含めて全件出力
  python stock_scanner.py --out result.csv       # 出力ファイル名変更
"""

import argparse
import sys
from datetime import datetime

import numpy as np
import pandas as pd
import yfinance as yf

# ── 銘柄リスト ────────────────────────────────────────────────────────────────

NIKKEI225 = [
    "1332.T","1605.T","1721.T","1801.T","1802.T","1803.T","1808.T","1812.T","1925.T","1928.T",
    "2002.T","2269.T","2282.T","2413.T","2432.T","2501.T","2502.T","2503.T","2531.T","2768.T",
    "2801.T","2802.T","2871.T","2914.T","3086.T","3099.T","3289.T","3382.T","3401.T","3402.T",
    "3405.T","3407.T","3436.T","4004.T","4005.T","4021.T","4042.T","4043.T","4061.T",
    "4063.T","4183.T","4188.T","4208.T","4272.T","4452.T","4502.T","4503.T","4506.T","4507.T",
    "4519.T","4523.T","4543.T","4568.T","4578.T","4661.T","4689.T","4704.T","4751.T","4755.T",
    "4901.T","4902.T","5019.T","5020.T","5101.T","5108.T","5201.T","5202.T","5214.T","5301.T",
    "5332.T","5333.T","5401.T","5406.T","5411.T","5541.T","5631.T","5713.T","5714.T","5715.T",
    "5802.T","5803.T","5901.T","6098.T","6103.T","6113.T","6178.T","6301.T","6302.T","6305.T",
    "6326.T","6361.T","6366.T","6367.T","6412.T","6471.T","6472.T","6473.T","6479.T","6501.T",
    "6503.T","6504.T","6506.T","6594.T","6645.T","6674.T","6702.T","6703.T","6724.T","6752.T",
    "6753.T","6758.T","6762.T","6770.T","6841.T","6857.T","6861.T","6902.T","6952.T","6954.T",
    "6971.T","6976.T","6981.T","7003.T","7004.T","7011.T","7012.T","7013.T","7201.T","7202.T",
    "7203.T","7205.T","7211.T","7261.T","7267.T","7269.T","7270.T","7272.T","7731.T","7733.T",
    "7735.T","7741.T","7751.T","7752.T","7762.T","7832.T","7911.T","7912.T","7951.T","8001.T",
    "8002.T","8003.T","8015.T","8031.T","8035.T","8053.T","8058.T","8233.T","8252.T","8267.T",
    "8306.T","8308.T","8309.T","8316.T","8331.T","8354.T","8411.T","8601.T","8604.T","8628.T",
    "8697.T","8725.T","8750.T","8766.T","8801.T","8802.T","8804.T","8830.T","9001.T","9005.T",
    "9007.T","9008.T","9009.T","9020.T","9021.T","9022.T","9064.T","9101.T","9104.T","9107.T",
    "9202.T","9301.T","9432.T","9433.T","9434.T","9501.T","9502.T","9503.T","9531.T","9532.T",
    "9602.T","9613.T","9681.T","9735.T","9766.T","9983.T","9984.T",
]

SP500_SAMPLE = [
    "AAPL","MSFT","NVDA","GOOGL","GOOG","AMZN","META","TSLA","BRK-B","UNH",
    "JPM","LLY","V","XOM","AVGO","JNJ","PG","MA","HD","MRK",
    "COST","ABBV","CVX","CRM","BAC","NFLX","AMD","PEP","KO","TMO",
    "ACN","MCD","ADBE","CSCO","WMT","LIN","DHR","ABT","TXN","PM",
    "NKE","NEE","ORCL","UPS","RTX","QCOM","MS","HON","INTU","AMGN",
    "IBM","GS","CAT","SPGI","BLK","AXP","ISRG","SYK","ELV","GILD",
    "ADI","VRTX","REGN","PLD","AMT","CI","DE","MDLZ","MMC","ZTS",
    "ETN","SLB","EOG","MO","DUK","SO","D","PGR","AON","BSX",
    "GE","HUM","ITW","CSX","EMR","FDX","FCX","KLAC","LRCX","ANET",
    "PANW","CRWD","SNOW","DDOG","MDB","ZS","NET","FTNT","OKTA","TEAM",
]

# ── スコアリング ──────────────────────────────────────────────────────────────

SCORE_WEIGHTS = {
    "bb_breakout":  40,
    "volume_surge": 30,
    "band_squeeze": 20,
    "ma_cross":     10,
}

def volume_bonus(vol_ratio: float) -> int:
    """出来高比率に応じたボーナス点（最大+10点）"""
    if vol_ratio >= 5.0: return 10
    if vol_ratio >= 3.0: return 5
    return 0

def calc_score(signals: list, vol_ratio: float, chg: float, ma75_adj: int) -> tuple:
    """シグナルと出来高比率・当日変化率・MA75調整値からスコアと内訳を返す。
    - BB下抜けは売りシグナルのためスコア加点の対象外
    - 出来高急増は当日価格が上昇している時のみ加点（下落時は表示のみ）
    - BB上抜け(25日)かつMA75未満 → +10pt、MA75超 → -5pt
    """
    bd = {k: 0 for k in SCORE_WEIGHTS}
    bd["volume_bonus"] = 0
    bd["ma75_adj"]     = 0

    for sig in signals:
        if sig == "BB上抜け":                  # BB下抜けは加点しない
            bd["bb_breakout"]  = SCORE_WEIGHTS["bb_breakout"]
            bd["ma75_adj"]     = ma75_adj      # BB上抜け時のみMA75調整を適用
        elif sig == "バンド収縮":
            bd["band_squeeze"] = SCORE_WEIGHTS["band_squeeze"]
        elif sig == "出来高急増":
            if chg > 0:                        # 上昇時のみ加点
                bd["volume_surge"] = SCORE_WEIGHTS["volume_surge"]
                bd["volume_bonus"] = volume_bonus(vol_ratio)
        elif sig in ("ゴールデンC", "デッドC"):
            bd["ma_cross"]     = SCORE_WEIGHTS["ma_cross"]

    return sum(bd.values()), bd

def score_rank(score: int) -> str:
    if score >= 80: return "★★★"
    if score >= 50: return "★★☆"
    if score >= 20: return "★☆☆"
    return "—"

# ── テクニカル計算 ────────────────────────────────────────────────────────────

def compute(ticker: str) -> "dict | None":
    try:
        t_obj = yf.Ticker(ticker)
        df = t_obj.history(period="6mo", interval="1d", auto_adjust=True)
        if df is None or len(df) < 30:
            return None

        # 銘柄名取得（取得失敗時はtickerをそのまま使用）
        try:
            info = t_obj.info
            name = info.get("longName") or info.get("shortName") or ticker
        except Exception:
            name = ticker

        close  = df["Close"].squeeze().dropna()
        volume = df["Volume"].squeeze().dropna()

        # Bollinger Bands（25日・2σ）
        ma25b = close.rolling(25).mean()
        std25 = close.rolling(25).std()
        bb_u  = ma25b + 2 * std25
        bb_l  = ma25b - 2 * std25
        bw    = (bb_u - bb_l) / ma25b * 100

        # 移動平均
        ma5  = close.rolling(5).mean()
        ma25 = close.rolling(25).mean()
        ma75 = close.rolling(75).mean()

        # 出来高
        vol_ma20 = volume.rolling(20).mean()

        p         = float(close.iloc[-1])
        bbu       = float(bb_u.iloc[-1])
        bbl       = float(bb_l.iloc[-1])
        bbm       = float(ma25b.iloc[-1])
        bw_val    = float(bw.iloc[-1])
        ma5_v     = float(ma5.iloc[-1])
        ma25_v    = float(ma25.iloc[-1])
        ma75_v    = float(ma75.iloc[-1]) if len(close) >= 75 else None
        vol_ratio = float(volume.iloc[-1]) / float(vol_ma20.iloc[-1]) if float(vol_ma20.iloc[-1]) > 0 else 0
        chg       = float((close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100)

        # MA75調整値（BB上抜け時のみ適用）
        if ma75_v is not None:
            ma75_adj = +10 if p < ma75_v else -5
        else:
            ma75_adj = 0

        # シグナル判定
        signals = []
        if p > bbu:          signals.append("BB上抜け")
        if p < bbl:          signals.append("BB下抜け")
        if bw_val < 8:       signals.append("バンド収縮")
        if vol_ratio >= 2.0: signals.append("出来高急増")

        for i in range(-3, 0):
            try:
                p5,  p25 = float(ma5.iloc[i-1]), float(ma25.iloc[i-1])
                c5,  c25 = float(ma5.iloc[i]),   float(ma25.iloc[i])
                if p5 < p25 and c5 >= c25:
                    signals.append("ゴールデンC"); break
                if p5 > p25 and c5 <= c25:
                    signals.append("デッドC");     break
            except Exception:
                pass

        score, bd = calc_score(signals, vol_ratio, chg, ma75_adj)

        return {
            "score":      score,
            "rank":       score_rank(score),
            "ticker":     ticker,
            "name":       name,
            "price":      round(p, 2),
            "change%":    round(chg, 2),
            "signals":    ", ".join(signals) if signals else "",
            # スコア内訳
            "pt_BB":      bd["bb_breakout"],
            "pt_出来高":  bd["volume_surge"] + bd["volume_bonus"],
            "pt_収縮":    bd["band_squeeze"],
            "pt_MA":      bd["ma_cross"],
            "pt_MA75補正": bd["ma75_adj"],
            # テクニカル値
            "BB上限":     round(bbu, 2),
            "BB中央":     round(bbm, 2),
            "BB下限":     round(bbl, 2),
            "BW%":        round(bw_val, 2),
            "MA5":        round(ma5_v, 2),
            "MA25":       round(ma25_v, 2),
            "MA75":       round(ma75_v, 2) if ma75_v is not None else None,
            "出来高比":   round(vol_ratio, 2),
        }
    except Exception:
        return None

# ── メイン ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="テクニカルシグナルスキャナー（スコアリング版）")
    parser.add_argument("--universe",    choices=["nikkei", "sp500", "both"], default="both")
    parser.add_argument("--tickers",     nargs="+", help="個別ティッカー指定（スペース区切り）")
    parser.add_argument("--min-score",   type=int, default=1, help="出力するスコアの下限（デフォルト: 1）")
    parser.add_argument("--all-results", action="store_true", help="スコア0銘柄も含めて全件出力")
    parser.add_argument("--out",         default="scan_result.csv", help="出力CSVファイル名")
    args = parser.parse_args()

    if args.tickers:
        tickers, label = args.tickers, "カスタム"
    elif args.universe == "nikkei":
        tickers, label = NIKKEI225, "日経225"
    elif args.universe == "sp500":
        tickers, label = SP500_SAMPLE, "S&P500"
    else:
        tickers, label = NIKKEI225 + SP500_SAMPLE, "日経225 + S&P500"

    print(f"\n{'='*62}")
    print(f"  SIGNAL SCANNER  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  対象: {label}  ({len(tickers)}銘柄)")
    print(f"  スコア: BB=40pt / 出来高=30pt+ボーナス最大10pt / 収縮=20pt / MA=10pt")
    print(f"{'='*62}\n")

    rows = []
    for i, t in enumerate(tickers, 1):
        print(f"  [{i:>3}/{len(tickers)}] {t:<12}", end="", flush=True)
        r = compute(t)
        if r:
            rows.append(r)
            print(
                f"  {r['price']:>10,.2f}  {r['change%']:>+6.2f}%"
                f"  score={r['score']:>3}  {r['rank']}  {r['signals'] or '—'}"
                f"  ({r['name']})"
            )
        else:
            print("  (取得失敗)")

    if not rows:
        print("\nデータを取得できませんでした。ネットワーク接続を確認してください。")
        sys.exit(1)

    df = pd.DataFrame(rows)

    out_df = df if args.all_results else df[df["score"] >= args.min_score]
    out_df = out_df.sort_values("score", ascending=False)
    out_df.to_csv(args.out, index=False, encoding="utf-8-sig")

    # サマリー
    sig_df = df[df["score"] > 0]
    print(f"\n{'='*62}")
    print(f"  スキャン完了")
    print(f"  総銘柄数           : {len(df)}")
    print(f"  シグナルあり       : {len(sig_df)} 件")
    print(f"  ★★★  80点以上  : {len(df[df['score'] >= 80])} 件")
    print(f"  ★★☆  50〜79点  : {len(df[(df['score'] >= 50) & (df['score'] < 80)])} 件")
    print(f"  ★☆☆  20〜49点  : {len(df[(df['score'] >= 20) & (df['score'] < 50)])} 件")
    print(f"  出力ファイル       : {args.out}")
    print(f"{'='*62}\n")

    if not sig_df.empty:
        top = sig_df.sort_values("score", ascending=False).head(20)
        print("【スコアランキング TOP20】\n")
        print(f"  {'#':<4} {'ticker':<12} {'name':<30} {'score':>5}  {'rank'}  {'price':>10}  {'chg%':>7}  signals")
        print(f"  {'-'*90}")
        for n, (_, r) in enumerate(top.iterrows(), 1):
            print(
                f"  {n:<4} {r['ticker']:<12} {r['name'][:28]:<30} {r['score']:>5}  {r['rank']}  "
                f"{r['price']:>10,.2f}  {r['change%']:>+7.2f}%  {r['signals']}"
            )
        print()


if __name__ == "__main__":
    main()
