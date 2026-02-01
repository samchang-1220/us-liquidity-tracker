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

def run_analysis():
    # 1. 抓取數據 (若失敗會抓最後一筆可用資料)
    res_raw = fred.get_series('WRESBAL').iloc[-1]
    res_date = fred.get_series('WRESBAL').index[-1]
    
    asset_raw = fred.get_series('TLAACBW027SBOG').iloc[-1]
    asset_date = fred.get_series('TLAACBW027SBOG').index[-1]
    
    gdp_raw = fred.get_series('GDP').iloc[-1]
    gdp_date = fred.get_series('GDP').index[-1]

    # 2. 單位換算與計算 (Reserves 原始單位是百萬MM，需轉為十億B)
    res_b = res_raw / 1000
    asset_b = asset_raw
    gdp_b = gdp_raw
    
    res_to_asset = (res_b / asset_b) * 100
    res_to_gdp = (res_b / gdp_b) * 100

    # 3. 格式化訊息
    msg = (
        f"🚨 **美國流動性週報**\n\n"
        f"🏦 銀行準備金：{res_b:,.1f} B ({res_date.strftime('%Y-%m-%d')})\n"
        f"📈 GDP：{gdp_b:,.1f} B ({get_quarter_str(gdp_date)})\n"
        f"🏢 商業銀行總資產：{asset_b:,.1f} B ({asset_date.strftime('%Y-%m-%d')})\n\n"
        f"📊 **指標分析：**\n"
        f"1️⃣ 準備金/總資產 = {res_to_asset:.2f}%\n"
        f"   (目標區間 12%~13%)\n"
        f"2️⃣ 準備金/GDP = {res_to_gdp:.2f}%\n"
        f"   (目標區間 9%~10%)\n"
    )

    # 4. 更新 GitHub 上的 CSV 資料庫
    db_file = 'database.csv'
    new_data = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'reserves_b': res_b,
        'assets_b': asset_b,
        'gdp_b': gdp_b,
        'res_to_asset': res_to_asset,
        'res_to_gdp': res_to_gdp
    }
    df_new = pd.DataFrame([new_data])
    
    if os.path.exists(db_file):
        df_old = pd.read_csv(db_file)
        df_final = pd.concat([df_old, df_new]).drop_duplicates(subset=['date'], keep='last')
    else:
        df_final = df_new
    
    df_final.to_csv(db_file, index=False)

    # 5. 發送 Telegram 訊息
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

if __name__ == "__main__":
    run_analysis()
