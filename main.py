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
    # 1. 抓取完整數列
    res_series = fred.get_series('WRESBAL')
    asset_series = fred.get_series('TLAACBW027SBOG')
    gdp_series = fred.get_series('GDP')

    # 2. 取得「本週」與「上週」數據 (Reserves 單位轉成 B)
    res_now = res_series.iloc[-1] / 1000
    res_last = res_series.iloc[-2] / 1000
    res_date = res_series.index[-1]

    asset_now = asset_series.iloc[-1]
    asset_last = asset_series.iloc[-2]
    asset_date = asset_series.index[-1]

    gdp_now = gdp_series.iloc[-1]
    gdp_last = gdp_series.iloc[-2] # 這是前一季，因為 GDP 每週不更新
    gdp_date = gdp_series.index[-1]

    # 3. 計算比例與變動
    res_to_asset_now = (res_now / asset_now) * 100
    res_to_asset_last = (res_last / asset_last) * 100
    
    res_to_gdp_now = (res_now / gdp_now) * 100
    res_to_gdp_last = (res_last / gdp_last) * 100

    # 4. 格式化訊息
    msg = (
        f"🚨 **美國流動性週報**\n\n"
        f"🏦 銀行準備金：{res_now:,.1f} B ({res_date.strftime('%Y-%m-%d')})\n"
        f"   (週增減：{calc_wow(res_now, res_last)})\n"
        f"📈 GDP：{gdp_now:,.1f} B ({get_quarter_str(gdp_date)})\n"
        f"🏢 商業銀行總資產：{asset_now:,.1f} B ({asset_date.strftime('%Y-%m-%d')})\n"
        f"   (週增減：{calc_wow(asset_now, asset_last)})\n\n"
        f"📊 **指標分析：**\n"
        f"1️⃣ 準備金/總資產 = {res_to_asset_now:.2f}%\n"
        f"   (上週：{res_to_asset_last:.2f}%) | 目標 12%~13%\n"
        f"2️⃣ 準備金/GDP = {res_to_gdp_now:.2f}%\n"
        f"   (上週：{res_to_gdp_last:.2f}%) | 目標 9%~10%\n"
    )

    # 5. 更新 GitHub 上的 CSV 資料庫
    db_file = 'database.csv'
    new_data = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'reserves_b': res_now,
        'assets_b': asset_now,
        'gdp_b': gdp_now,
        'res_to_asset': res_to_asset_now,
        'res_to_gdp': res_to_gdp_now
    }
    df_new = pd.DataFrame([new_data])
    
    if os.path.exists(db_file):
        df_old = pd.read_csv(db_file)
        df_final = pd.concat([df_old, df_new]).drop_duplicates(subset=['date'], keep='last')
    else:
        df_final = df_new
    
    df_final.to_csv(db_file, index=False)

    # 6. 發送 Telegram 訊息
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    requests.post(url, data=payload)

if __name__ == "__main__":
    run_analysis()
