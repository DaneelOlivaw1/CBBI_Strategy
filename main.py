import json
from datetime import datetime
import os
import time
import requests
from binance import Client

# 子账户 API
api_key = "bn_api_key" # bianace子账户的API
api_secret = "bn_api_secret" 
pushplus_token = "pushplus_token" # https://www.pushplus.plus/ 登录后获取
cbbi_json = "last_cbbi.json" # CBBI指数文件
piece = 10  # 定义每份 USDT 的数量，例如 10 USDT


client = Client(api_key, api_secret)
print("===========================================")
print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


def stragegy1(piece, mark, **kwargs):
    total_money = kwargs.get('total_money', 0)
    if mark <= 20:
        buy_amount = 0.05 * total_money  # 抄底，按照百分比去抄底
        buy_amount = max(buy_amount, 8 * piece)
        return "buy", buy_amount
    elif mark <= 40:
        return "buy", 4 * piece
    elif mark <= 60:
        return "buy", 2 * piece 
    elif mark <= 80:
        return "buy", 1 * piece  
    else:
        return "sell", 0.1 # 信心极高时，卖出10%的比特币

def check_order_status(order_id, symbol="BTCUSDT"):
    """查询订单状态"""
    time.sleep(2)  # 等待一段时间，确保订单状态更新

    order_status = client.get_order(symbol=symbol, orderId=order_id)
    print(f"Order status: {order_status}")

    if order_status['status'] == 'FILLED':
        print("订单已成交")
        return True
    else:
        print("订单未完全成交")
        return False

def execute_trade(action, usdt_amount, symbol="BTCUSDT"):
    """执行交易"""
    if action == "buy":
        # 直接使用USDT数量下单
        order = client.order_market_buy(symbol=symbol, quoteOrderQty=usdt_amount)
        print(f"Buy order placed: {order}")
    elif action == "sell":
        # 获取BTC余额
        btc_balance = float(client.get_asset_balance(asset='BTC')['free'])
        # 计算卖出BTC的数量
        sell_amount = btc_balance * usdt_amount
        order = client.order_market_sell(symbol=symbol, quantity=sell_amount)
        print(f"Sell order placed: {order}")

    return order["orderId"]

def check_balance(min_balance):
    """检查钱包余额是否足够

    Args:
        min_balance: 最低余额要求 (USDT)

    Returns:
        如果余额足够，返回 True，否则返回 False
    """
    try:
        usdt_balance = float(client.get_asset_balance(asset='USDT')['free'])
    except TypeError:  # 如果获取余额失败，抛出异常
        print("获取USDT余额失败，请检查API密钥和网络连接")
        return False, None

    if usdt_balance >= min_balance:
        return True, usdt_balance
    else:
        print(f"USDT余额不足，当前余额: {usdt_balance}，最低要求: {min_balance}")
        return False, usdt_balance

def send_pushplus_notification(content, topic=None):
    """发送 PushPlus 推送消息

    Args:
        token (str): 你的 PushPlus 推送 token
        title (str): 消息标题
        content (str): 消息内容
        topic (str, optional): 推送主题，默认为 None
    """
    url = 'http://www.pushplus.plus/send/'
    headers = {'Content-Type': 'application/json'}
    data = {
        "token": pushplus_token,
        "title": "CBBI 自动定投",
        "content": content,
        "template":"json"
    }
    if topic:
        data["topic"] = topic

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        print("消息推送成功")
    else:
        print(f"消息推送失败，错误码: {response.status_code}")
        print(response.text)

with open(cbbi_json) as f:
    data = json.load(f)

mark = data["Confidence"]

# Get the latest date (key) from the dictionary
latest_date = max(mark.keys())

latest_value = mark[latest_date]

# Convert the timestamp to a datetime object
datetime_object = datetime.fromtimestamp(int(latest_date))

# Format the date as YYYY-MM-DD
formatted_date = datetime_object.strftime("%Y-%m-%d")

# 计算历史低于今天分数的比例
lower_count = 0
total_count = 0
for date, value in mark.items():
    total_count += 1
    if value < latest_value:
        lower_count += 1

lower_percentage = (lower_count / total_count) * 100

print(f"Date: {formatted_date}, Value: {latest_value}")

is_blance_enough, usdt_balance = check_balance(10 * piece)
# Now you can use latest_value in your strategy
action, amount = stragegy1(piece, latest_value * 100, total_money=usdt_balance)
print(f"Action: {action}, Amount: {amount}")

if action:
    order_id = execute_trade(action, amount)
    order_status = check_order_status(order_id)

    content = {
        "日期": formatted_date,
        "CBBI指数": latest_value * 100,
        "定投单位": f"{piece}u",
        "今日操作": f"{action}, {amount}u",
        "交易是否成功": order_status,
        "是否需要补充余额": is_blance_enough,
        "当前钱包余额": f"{usdt_balance:.2f}"
    }
    send_pushplus_notification(content)

print("============================")

