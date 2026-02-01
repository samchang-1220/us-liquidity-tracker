import os
import requests
import pandas as pd
from fredapi import Fred
from datetime import datetime

# 設定金鑰
FRED_API_KEY = os.getenv('FRED_API_KEY')
TG_BOT_TOKEN = os.getenv('TG_BOT_TOKEN')
TG_CHAT_ID = os.getenv('TG_CHAT_ID')

fred = Fred(api_key=FRED_API_KEY)

def get_quarter_str(date):
    year = date.year
    quarter = (date.month - 1) // 3 + 1
    return f"{str(year)[2:]}Q{quarter}"

def calc_wow(now, last):
    change = ((now - last) / last) * 100
    sign = "+" if change >= 0 else ""
    return f"{sign}{change:.2f}%"

def run_analysis():
    # 1. 抓取完整歷史數列
    res_series = fred.get_series('WRESBAL')
    asset_series = fred.get_series('TLAACBW027SBOG')
    gdp_series = fred.get_series('GDP')

    # 取得最新一筆資料及其日期
    res_now = res_series.iloc[-1] / 1000
    res_last = res_series.iloc[-2] / 1000
    res_date = res_series.index[-1].strftime('%Y-%m-%d')

    asset_now = asset_series.iloc[-1]
    asset_last = asset_series.iloc[-2]
    asset_date = asset_series.index[-1].strftime('%Y-%m-%d')

    gdp_now = gdp_series.iloc[-1]
    gdp_date = get_quarter_str(gdp_series.index[-1])

    # 2. 計算比例數列 (Series)，直接從歷史資料算平均
    df_history = pd.DataFrame({
        'res': res_series / 1000,
        'asset': asset_series
    }).dropna()

    df_history['ratio'] = (df_history['res'] / df_history['asset']) * 100
    
    # 計算平均值
    avg_4w_asset = df_history['ratio'].tail(4).mean()
    avg_12w_asset = df_history['ratio'].tail(12).mean()

    res_to_gdp_series = (df_history['res'] / gdp_now) * 100
    avg_4w_gdp = res_to_gdp_series.tail(4).mean()
    avg_12w_gdp = res_to_gdp_series.tail(12).mean()

    current_res_to_asset = df_history['ratio'].iloc[-1]
    current_res_to_gdp = res_to_gdp_series.iloc[-1]

    # 3. 格式化 Telegram 訊息
    # 注意：這裡使用多行字串避免引號斷裂問題
    msg = (
        f"🇺🇸 **美國流動性監測週報**\n"
        f"📅 報告日期：{datetime.now().strftime('%Y-%m-%d')}\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 **核心數據 (Current Levels)**\n"
        f"• 銀行準備金：`{res_now:,.1f} B`\n"
        f"  (資料日：{res_date} | {calc_wow(res_now, res_last)})\n"
        f"• 銀行總資產：`{asset_now:,.1f} B`\n"
        f"  (資料日：{asset_date} | {calc_wow(asset_now, asset_last)})\n"
        f"• 名目 GDP：`{gdp_now:,.1f} B`\n"
        f"  (資料期：{gdp_date})\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 **指標分析 (Ratios)**\n\n"
        f"1️⃣ **準備金 / 總資產**\n"
        f"   現值：`{current_res_to_asset:.2f}%` (目標
