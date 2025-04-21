#Version 2: Add Flush Mechinsm
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

total = 0
rounds = 100
for j in range(rounds):
    # 模擬參數
    n = 96 * 60 # 96K per day
    S0 = 10000 # Begining Prices
    mu = 0.00001 # every 15 mins 0.005% → a day 0.5%
    sigma = 0.00306 # every 15 mins volatility ≈ a day 0.306%
    dt = 1 # 15 mins

    np.random.seed(j)
    W = np.random.normal(loc=0, scale=np.sqrt(dt), size=n)
    price_series = S0 * np.exp((mu - 0.5 * sigma**2) * dt + sigma * W).cumprod()

    df = pd.DataFrame({"price": price_series})

    # 計算布林通道
    window = 20
    df["MA20"] = df["price"].rolling(window=window).mean()
    df["Upper"] = df["MA20"] + 2 * df["price"].rolling(window=window).std()
    df["Lower"] = df["MA20"] - 2 * df["price"].rolling(window=window).std()

    balance = 10000 #初始資金
    position = 0 #倉位
    total_buy_cost = 0       # 累積買進所花的總金額（用來計算多單持倉的平均成本）
    total_short_income = 0   # 累積放空時賣出的總收入（用來計算空單持倉的平均賣出價格）
    avg_position_price = 0 #均價
    fee_rate = 1 / 1000 #手續費

    transactions = []

    for i in range(len(df)):
        price = df["price"].iloc[i]
        unit = 0.01  # 💡 每次交易金額為該價格的 1%
        range_multi = 0.8
        # 多單進場 買入0.01顆
        if df["Lower"].iloc[i] <= price <= (df["MA20"].iloc[i]*(1-range_multi) + df["Lower"].iloc[i]*range_multi)  and position >= 0:
            cost = unit * price * fee_rate #手續費
            balance -= unit * price + cost #帳戶餘額
            total_buy_cost += unit * price #倉位價值
            position += unit #持倉顆數變化
            position = round(position, 2)
            avg_position_price = total_buy_cost / position if position != 0 else 0 # 計算持倉均價
            #balance += (price - avg_position_price) * position

            transactions.append({
                "Index": i, "Action": "Buy", "Price": price, "Amount": unit * price, "Fee": cost,
                "Balance": balance, "Position": position,
                "Account Value": balance + position * avg_position_price,
                "Avg Position Price": avg_position_price, "Unrealized P&L": (price - avg_position_price) * position
            })

        # 多單出場 賣出0.01顆
        elif (df["MA20"].iloc[i]*(1-range_multi) + df["Upper"].iloc[i]*range_multi) <= price <= df["Upper"].iloc[i] and position > 0:

            #如果累積超過20張多單(position >= 0.20) => 出一半(0.1)
            if position >= 0.2 :
                Sell_position = 0.1
                cost = Sell_position * price * fee_rate #手續費
                balance += Sell_position * price - cost #結算盈虧
                total_buy_cost -= avg_position_price * Sell_position #賣出倉位價值
                position -= Sell_position #清空持倉
                position = round(position, 2)
                avg_position_price = total_buy_cost / position if position != 0 else 0 #更新持倉均價

                transactions.append({
                    "Index": i, "Action": "Sell", "Price": price, "Amount": Sell_position * price, "Fee": cost,
                    "Balance": balance, "Position": position,
                    "Account Value": balance + position * avg_position_price,
                    "Avg Position Price": avg_position_price if position > 0 else 0,
                    "Unrealized P&L": (price - avg_position_price) * position if position > 0 else 0
                })
            else:
                cost = unit * price * fee_rate #手續費
                balance += unit * price - cost #結算盈虧
                total_buy_cost -= avg_position_price * unit #賣出倉位價值
                position -= unit #持倉 -0.01顆
                position = round(position, 2)
                avg_position_price = total_buy_cost / position if position > 0 else 0 #更新持倉均價
                #balance += (price - avg_position_price) * position

                transactions.append({
                    "Index": i, "Action": "Sell", "Price": price, "Amount": unit * price, "Fee": cost,
                    "Balance": balance, "Position": position,
                    "Account Value": balance + position * avg_position_price,
                    "Avg Position Price": avg_position_price if position > 0 else 0,
                    "Unrealized P&L": (price - avg_position_price) * position if position > 0 else 0
                })

        # 空單進場 #賣出0.01顆
        elif df["Upper"].iloc[i] >= price >= (df["MA20"].iloc[i]*(1-range_multi) + df["Upper"].iloc[i]*range_multi) and position <= 0:
            cost = unit * price * fee_rate #手續費
            balance += unit * price - cost #帳戶餘額
            total_short_income += unit * price
            position -= unit
            position = round(position, 2)
            avg_position_price = total_short_income / abs(position) if position != 0 else 0
            #balance += (price - avg_position_price) * position
            
            transactions.append({
                "Index": i, "Action": "Short", "Price": price, "Amount": unit * price, "Fee": cost,
                "Balance": balance, "Position": position,
                "Account Value": balance + position * avg_position_price,
                "Avg Position Price": avg_position_price, "Unrealized P&L": (avg_position_price - price) * abs(position)
            })

        # 空單出場
        elif (df["MA20"].iloc[i]*(1-range_multi) + df["Lower"].iloc[i]*range_multi) >= price >= df["Lower"].iloc[i] and position < 0:
            #如果累積超過20張空單(position <= -0.20) => 出一半(0.1)
            if position <= -0.2 :
                Sell_position = -0.1
                cost = abs(Sell_position) * price * fee_rate #手續費
                balance -= abs(Sell_position) * price + cost
                total_short_income -= avg_position_price * abs(Sell_position)
                position -= Sell_position
                position = round(position, 2)
                avg_position_price = total_short_income / abs(position) if position != 0 else 0
                #balance += (price - avg_position_price) * position
                
                transactions.append({
                    "Index": i, "Action": "Cover", "Price": price, "Amount": abs(Sell_position) * price, "Fee": cost,
                    "Balance": balance, "Position": position,
                    "Account Value": balance + position * avg_position_price,
                    "Avg Position Price": avg_position_price if position < 0 else 0,
                    "Unrealized P&L": (avg_position_price - price) * abs(position) if position < 0 else 0
                })
            else:
                cost = unit * price * fee_rate #手續費
                balance -= unit * price + cost
                total_short_income -= avg_position_price * unit
                position += unit
                position = round(position, 2)
                avg_position_price = total_short_income / abs(position) if position < 0 else 0
                #balance += (price - avg_position_price) * position
                
                transactions.append({
                    "Index": i, "Action": "Cover", "Price": price, "Amount": unit * price, "Fee": cost,
                    "Balance": balance, "Position": position,
                    "Account Value": balance + position * avg_position_price,
                    "Avg Position Price": avg_position_price if position < 0 else 0,
                    "Unrealized P&L": (avg_position_price - price) * abs(position) if position < 0 else 0
                })

    # 最後清算
    if position != 0:
        final_price = df["price"].iloc[-1]
        cost = abs(position) * final_price * fee_rate 
        balance += position * final_price - cost

        transactions.append({
            "Index": len(df) - 1, "Action": "Close Position", "Price": final_price,
            "Amount": abs(position) * final_price, "Fee": cost,
            "Balance": balance, "Position": 0,
            "Account Value": balance, "Avg Position Price": 0, "Unrealized P&L": 0
        })

    # 匯出交易紀錄
    transaction_df = pd.DataFrame(transactions)
    #print(transaction_df.tail())
    print(f"Round: {j}, {transaction_df.iloc[-1]["Balance"]}")
    total += transaction_df.iloc[-1]["Balance"]
    
print(total / rounds)
if(rounds != 1):
    exit()

##################################################################################################################################
transaction_df.columns = ["索引", "操作", "價格", "交易金額", "手續費", "現金餘額", "持倉數量", "帳戶浮動價值", "持倉均價", "浮動盈虧"]
transaction_df.to_excel("交易記錄.xlsx", index=False)
print("已儲存交易紀錄")

# 繪圖
plt.figure(figsize=(14, 8))
plt.plot(df["price"], label="Price", color="blue")
plt.plot(df["Upper"], label="BOLL Upper", linestyle="--", color="green")
plt.plot(df["Lower"], label="BOLL Lower", linestyle="--", color="red")
plt.plot(df["MA20"], label="BOLL Middle", linestyle=":", color="orange")

# 畫交易點
for t in transactions:
    if t["Action"] == "Buy":
        plt.scatter(t["Index"], t["Price"], color="lime", label="Buy" if "Buy" not in plt.gca().get_legend_handles_labels()[1] else "", marker="^", s=100)
    elif t["Action"] == "Sell":
        plt.scatter(t["Index"], t["Price"], color="darkgreen", label="Sell" if "Sell" not in plt.gca().get_legend_handles_labels()[1] else "", marker="v", s=100)
    elif t["Action"] == "Short":
        plt.scatter(t["Index"], t["Price"], color="orange", label="Short" if "Short" not in plt.gca().get_legend_handles_labels()[1] else "", marker="x", s=100)
    elif t["Action"] == "Cover":
        plt.scatter(t["Index"], t["Price"], color="purple", label="Cover" if "Cover" not in plt.gca().get_legend_handles_labels()[1] else "", marker="o", s=100)

plt.title("Price")
plt.xlabel("15K")
plt.ylabel("Price($)")
plt.legend()
plt.grid()
plt.tight_layout()
plt.show()
