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

    # 取得最新數據
    res_now = res_series.iloc[-1] / 1000
    res_last = res_series.iloc[-2] / 1000
    res_date = res_series.index[-1].strftime('%Y-%m-%d')

    asset_now = asset_series.iloc[-1]
    asset_last = asset_series.iloc[-2]
    asset_date = asset_series.index[-1].strftime('%Y-%m-%d')

    gdp_now = gdp_series.iloc[-1]
    gdp_date = get_quarter_str(gdp_series.index[-1])

    # 2. 計算比例與平均值
    df_history = pd.DataFrame({
        'res': res_series / 1000,
        'asset': asset_series
    }).dropna()

    df_history['ratio_asset'] = (df_history['res'] / df_history['asset']) * 100
    df_history['ratio_gdp'] = (df_history['res'] / gdp_now) * 100
    
    current_asset_ratio = df_history['ratio_asset'].iloc[-1]
    avg_4w_asset = df_history['ratio_asset'].tail(4).mean()
    avg_12w_asset = df_history['ratio_asset'].tail(12).mean()

    current_gdp_ratio = df_history['ratio_gdp'].iloc[-1]
    avg_4w_gdp = df_history['ratio_gdp'].tail(4).mean()
    avg_12w_gdp = df_history['ratio_gdp'].tail(12).mean()

    # 3. 格式化訊息 (使用三引號確保不會斷開)
    msg = f"""🇺🇸 **美國流動性監測週報**
📅 報告日期：{datetime.now().strftime('%Y-%m-%d')}
━━━━━━━━━━━━━━━━━━

💰 **核心數據 (Current Levels)**
• 銀行準備金：`{res_now:,.1f} B`
  (資料日：{res_date} | {calc_wow(res_now, res_last)})
• 銀行總資產：`{asset_now:,.1f} B`
  (資料日：{asset_date} | {calc_wow(asset_now, asset_last)})
• 名目 GDP：`{gdp_now:,.1f} B`
  (資料期：{gdp_date})
━━━━━━━━━━━━━━━━━━

📊 **指標分析 (Ratios)**

1️⃣ **準備金 / 總資產**
   現值：`{current_asset_ratio:.2f}%` (目標 12-13%)
   - 近 04 週平均：`{avg_4w_asset:.2f}%`
   - 近 12 週平均：`{avg_12w_asset:.2f}%`

2️⃣ **準備金 / GDP**
   現值：`{current_gdp_ratio:.2f}%` (目標 9-10%)
   - 近 04 週平均：`{avg_4w_gdp:.2f}%`
   - 近 12 週平均：`{avg_12w_gdp:.2f}%`

💡 *註：僅供參考*"""

    # 4. 更新 database.csv
    db_file = 'database.csv'
    new_entry = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'res_date': res_date,
        'reserves_b': res_now,
        'asset_date': asset_date,
        'assets_b': asset_now,
        'gdp_period': gdp_date,
        'gdp_b': gdp_now,
        'res_to_asset': current_asset_ratio,
        'res_to_gdp': current_gdp_ratio
    }
    df_new = pd.DataFrame([new_entry])
    if os.path.exists(db_file):
        df_old = pd.read_csv(db_file)
        df_total = pd.concat([df_old, df_new]).drop_duplicates(subset=['date'], keep='last')
    else:
        df_total = df_new
    df_total.to_csv(db_file, index=False)

    # 5. 發送訊息
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    requests.post(url, data=payload)

if __name__ == "__main__":
    run_analysis()
