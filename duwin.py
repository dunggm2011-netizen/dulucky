import os
import json
import requests
import logging
import random
import threading
import time
from flask import Flask
import telebot
from telebot import types

# === FLASK GIỮ CỔNG ===
app_flask = Flask(__name__)

@app_flask.route('/')
def index():
    return "Bot is running!"

def keep_alive():
    port = int(os.environ.get('PORT', 5000))
    app_flask.run(host='0.0.0.0', port=port)

# === CẤU HÌNH BOT ===
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8385677064:AAHS5ZqmV9QPka3I1t84lyysLzLsLTp3N6g")
WINHASH_API = "https://api.winhash.net/lucky_hash/home"

logging.basicConfig(level=logging.INFO)
bot = telebot.TeleBot(BOT_TOKEN)

# === LƯU TRỮ ===
user_data_store = {}

# === GỌI API ===
def fetch_winhash_data(user_id, secret_key):
    headers = {
        'user-id': str(user_id),
        'user-secret-key': secret_key,
        'Content-Type': 'application/json'
    }
    try:
        response = requests.get(WINHASH_API, headers=headers, params={'game_id': 2, 'asset': 'BUILD'}, timeout=10)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

# === 5 THUẬT TOÁN ===
def algo_random(history):
    return random.uniform(0, 99.99)

def algo_hot(history):
    counts = {}
    for item in history:
        num = item.get('result') or item.get('number') or item.get('lucky_number')
        if num:
            try:
                num = float(num)
                counts[num] = counts.get(num, 0) + 1
            except:
                pass
    if not counts:
        return random.uniform(0, 99.99)
    hot = max(counts, key=counts.get)
    return max(0, min(99.99, hot + random.uniform(-3, 3)))

def algo_cold(history):
    counts = {}
    for item in history:
        num = item.get('result') or item.get('number') or item.get('lucky_number')
        if num:
            try:
                num = float(num)
                counts[num] = counts.get(num, 0) + 1
            except:
                pass
    if not counts:
        return random.uniform(0, 99.99)
    cold = min(counts, key=counts.get)
    return max(0, min(99.99, cold + random.uniform(-2, 2)))

def algo_trend(history):
    numbers = []
    for item in history:
        num = item.get('result') or item.get('number') or item.get('lucky_number')
        if num:
            try:
                numbers.append(float(num))
            except:
                pass
    if len(numbers) < 3:
        return random.uniform(0, 99.99)
    diff_sum = 0
    for i in range(1, len(numbers)):
        diff_sum += numbers[i] - numbers[i-1]
    avg_diff = diff_sum / (len(numbers) - 1)
    last = numbers[-1]
    prediction = last + avg_diff * 1.5 + random.uniform(-2, 2)
    return max(0, min(99.99, prediction))

def algo_ensemble(history):
    results = [algo_random(history), algo_hot(history), algo_cold(history), algo_trend(history)]
    weights = [0.1, 0.35, 0.2, 0.35]
    weighted_sum = sum(r * w for r, w in zip(results, weights))
    return max(0, min(99.99, weighted_sum))

ALGO_MAP = {
    "RANDOM": algo_random,
    "HOT": algo_hot,
    "COLD": algo_cold,
    "TREND": algo_trend,
    "ENSEMBLE": algo_ensemble,
}

def analyze_and_predict(history, algo_name="ENSEMBLE"):
    if not history:
        return {"prediction": f"{random.uniform(0, 99.99):.2f}", "confidence": "30.0%", "algo": algo_name}
    
    func = ALGO_MAP.get(algo_name, algo_ensemble)
    prediction = func(history)
    
    numbers = []
    for item in history:
        num = item.get('result') or item.get('number') or item.get('lucky_number')
        if num:
            try:
                numbers.append(float(num))
            except:
                pass
    
    if len(numbers) > 1:
        mean = sum(numbers) / len(numbers)
        variance = sum((x - mean) ** 2 for x in numbers) / len(numbers)
        std_dev = variance ** 0.5
        confidence = max(30, min(90, 90 - std_dev * 1.5))
    else:
        confidence = 50
    
    return {
        "prediction": f"{prediction:.2f}",
        "confidence": f"{confidence:.1f}%",
        "algo": algo_name
    }

# === LỆNH ===
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message,
        "🤖 **Lucky Hash Predictor Bot**\n\n"
        "/setid <ID> - Lưu User ID\n"
        "/setkey <KEY> - Lưu Secret Key\n"
        "/predict [algo] - Dự đoán\n"
        "/status - Trạng thái\n"
        "/algos - Danh sách thuật toán",
        parse_mode='Markdown')

@bot.message_handler(commands=['setid'])
def set_id(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "⚠️ /setid <User ID>")
        return
    uid = message.from_user.id
    user_data_store[uid] = user_data_store.get(uid, {})
    user_data_store[uid]['user_id'] = args[1]
    bot.reply_to(message, f"✅ Đã lưu User ID: {args[1]}")

@bot.message_handler(commands=['setkey'])
def set_key(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "⚠️ /setkey <Secret Key>")
        return
    uid = message.from_user.id
    user_data_store[uid] = user_data_store.get(uid, {})
    user_data_store[uid]['secret_key'] = args[1]
    bot.reply_to(message, "✅ Đã lưu Secret Key")

@bot.message_handler(commands=['predict'])
def predict(message):
    uid = message.from_user.id
    data = user_data_store.get(uid, {})
    
    if 'user_id' not in data or 'secret_key' not in data:
        bot.reply_to(message, "⚠️ Chưa set ID/Key. Dùng /setid và /setkey")
        return
    
    args = message.text.split()
    algo = args[1].upper() if len(args) > 1 else "ENSEMBLE"
    if algo not in ALGO_MAP:
        algo = "ENSEMBLE"
    
    bot.reply_to(message, f"⏳ Đang phân tích với *{algo}*...", parse_mode='Markdown')
    
    resp = fetch_winhash_data(data['user_id'], data['secret_key'])
    
    if "error" in resp:
        bot.reply_to(message, f"❌ Lỗi: {resp['error']}")
        return
    if resp.get('code') == 1004:
        bot.reply_to(message, "❌ Sai User ID hoặc Secret Key")
        return
    
    history = resp.get('data', {}).get('history', [])
    if not history:
        bot.reply_to(message, "⚠️ Chưa có dữ liệu lịch sử")
        return
    
    result = analyze_and_predict(history, algo)
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🎲 RANDOM", callback_data="RANDOM"),
        types.InlineKeyboardButton("🔥 HOT", callback_data="HOT"),
        types.InlineKeyboardButton("❄️ COLD", callback_data="COLD"),
        types.InlineKeyboardButton("📈 TREND", callback_data="TREND"),
        types.InlineKeyboardButton("🧠 ENSEMBLE", callback_data="ENSEMBLE"),
    )
    
    bot.send_message(message.chat.id,
        f"🔮 **DỰ ĐOÁN LUCKY HASH**\n\n"
        f"🎯 Số: `{result['prediction']}`\n"
        f"📊 Độ tin cậy: {result['confidence']}\n"
        f"⚙️ Thuật toán: *{result['algo']}*\n\n"
        f"🔄 Chọn thuật toán khác:",
        parse_mode='Markdown',
        reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    uid = call.from_user.id
    data = user_data_store.get(uid, {})
    
    if 'user_id' not in data or 'secret_key' not in data:
        bot.answer_callback_query(call.id, "⚠️ Chưa set ID/Key")
        return
    
    algo = call.data
    bot.answer_callback_query(call.id, f"Đang phân tích {algo}...")
    bot.edit_message_text(f"⏳ Đang phân tích với *{algo}*...", call.message.chat.id, call.message.message_id, parse_mode='Markdown')
    
    resp = fetch_winhash_data(data['user_id'], data['secret_key'])
    
    if "error" in resp:
        bot.edit_message_text(f"❌ Lỗi: {resp['error']}", call.message.chat.id, call.message.message_id)
        return
    if resp.get('code') == 1004:
        bot.edit_message_text("❌ Sai User ID hoặc Secret Key", call.message.chat.id, call.message.message_id)
        return
    
    history = resp.get('data', {}).get('history', [])
    if not history:
        bot.edit_message_text("⚠️ Chưa có dữ liệu lịch sử", call.message.chat.id, call.message.message_id)
        return
    
    result = analyze_and_predict(history, algo)
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🎲 RANDOM", callback_data="RANDOM"),
        types.InlineKeyboardButton("🔥 HOT", callback_data="HOT"),
        types.InlineKeyboardButton("❄️ COLD", callback_data="COLD"),
        types.InlineKeyboardButton("📈 TREND", callback_data="TREND"),
        types.InlineKeyboardButton("🧠 ENSEMBLE", callback_data="ENSEMBLE"),
    )
    
    bot.edit_message_text(
        f"🔮 **DỰ ĐOÁN LUCKY HASH**\n\n"
        f"🎯 Số: `{result['prediction']}`\n"
        f"📊 Độ tin cậy: {result['confidence']}\n"
        f"⚙️ Thuật toán: *{result['algo']}*\n\n"
        f"🔄 Chọn thuật toán khác:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown',
        reply_markup=markup)

@bot.message_handler(commands=['status'])
def status_cmd(message):
    uid = message.from_user.id
    data = user_data_store.get(uid, {})
    msg = "📋 **TRẠNG THÁI**\n"
    msg += f"User ID: {data.get('user_id', '❌ Chưa set')}\n"
    msg += f"Secret Key: {'✅ Đã set' if data.get('secret_key') else '❌ Chưa set'}"
    bot.reply_to(message, msg, parse_mode='Markdown')

@bot.message_handler(commands=['algos'])
def algos_cmd(message):
    bot.reply_to(message,
        "📚 **DANH SÁCH THUẬT TOÁN**\n\n"
        "🎲 RANDOM - Random\n"
        "🔥 HOT - Số xuất hiện nhiều nhất\n"
        "❄️ COLD - Số xuất hiện ít nhất\n"
        "📈 TREND - Phân tích xu hướng\n"
        "🧠 ENSEMBLE - Tổng hợp (mặc định)",
        parse_mode='Markdown')

# === MAIN ===
if __name__ == "__main__":
    # Chạy Flask giữ cổng trong thread riêng
    threading.Thread(target=keep_alive, daemon=True).start()
    
    print("🚀 Bot đang chạy...")
    bot.infinity_polling()
