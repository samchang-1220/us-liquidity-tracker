import os
import requests
import pandas as pd
from fredapi import Fred
from datetime import datetime

# 設定金鑰 (從 GitHub Secrets 讀取)
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
    # 1. 抓取最新數據
    res_series = fred.get_series('WRESBAL')
    asset_series = fred.get_series('TLAACBW027SBOG')
    gdp_series = fred.get_series('GDP')

    # 本週數值
    res_now = res_series.iloc[-1] / 1000
    res_last = res_series.iloc[-2] / 1000
    asset_now = asset_series.iloc[-1]
    asset_last = asset_series.iloc[-2]
    gdp_now = gdp_series.iloc[-1]
    
    # 2. 更新並讀取資料庫以計算平均值
    db_file = 'database.csv'
    new_data = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'reserves_b': res_now,
        'assets_b': asset_now,
        'gdp_b': gdp_now,
        'res_to_asset': (res_now / asset_now) * 100,
        'res_to_gdp': (res_now / gdp_now) * 100
    }
    df_new = pd.DataFrame([new_data])
    
    if os.path.exists(db_file):
        df_history = pd.read_csv(db_file)
        df_total = pd.concat([df_history, df_new]).drop_duplicates(subset=['date'], keep='last')
    else:
        df_total = df_new

    # 計算近 4 週與 12 週平均
    avg_4w_asset = df_total['res_to_asset'].tail(4).mean()
    avg_12w_asset = df_total['res_to_asset'].tail(12).mean()
    avg_4w_gdp = df_total['res_to_gdp'].tail(4).mean()
    avg_12w_gdp = df_total['res_to_gdp'].tail(12).mean()

    # 3. 格式化 Telegram 訊息
    msg = (
        f"🇺🇸 **美國流動性監測週報**\n"
        f"📅 報告日期：{datetime.now().strftime('%Y-%m-%d')}\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 **核心數據 (Current Levels)**\n"
        f"• 銀行準備金：`{res_now:,.1f} B` ({calc_wow(res_now, res_last)})\n"
        f"• 銀行總資產：`{asset_now:,.1f} B` ({calc_wow(asset_now, asset_last)})\n"
        f"• 實質名目GDP：`{gdp_now:,.1f} B` ({get_quarter_str(gdp_series.index[-1])})\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 **指標分析 (Ratios)**\n\n"
        f"1️⃣ **準備金 / 總資產**\n"
        f"   現值：`{new_data['res_to_asset']:.2f}%` (目標 12-13%)\n"
        f"   - 近 04 週平均：`{avg_4w_asset:.2f}%`\n"
        f"   - 近 12 週平均：`{avg_12w_asset:.2f}%`\n\n"
        f"2️⃣ **準備金 / GDP**\n"
        f"   現值：`{new_data['res_to_gdp']:.2f}%` (目標 9-10%)\n"
        f"   - 近 04 週平均：`{avg_4w_gdp:.2f}%`\n"
        f"   - 近 12 週平均：`{avg_12w_gdp:.2f}%`\n\n"
        f"💡 *註：若現值低於長期平均，需警惕流動性轉緊風險。*"
    )

    # 4. 儲存資料庫
    df_total.to_csv(db_file, index=False)

    # 5. 發送訊息
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    requests.post(url, data=payload)

if __name__ == "__main__":
    run_analysis()
