import os
import json
import requests
import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext

# === CẤU HÌNH ===
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8385677064:AAHS5ZqmV9QPka3I1t84lyysLzLsLTp3N6g")
WINHASH_API = "https://api.winhash.net/lucky_hash/home?game_id=1&asset=BUILD"

logging.basicConfig(level=logging.INFO)

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

# === 5 THUẬT TOÁN DỰ ĐOÁN ===

# 1. RANDOM
def algo_random(history):
    return random.uniform(0, 99.99)

# 2. HOT - Số xuất hiện nhiều nhất
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
    # Random nhẹ xung quanh số hot
    return max(0, min(99.99, hot + random.uniform(-3, 3)))

# 3. COLD - Số xuất hiện ít nhất
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

# 4. TREND - Phân tích xu hướng
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
    
    # Tính xu hướng
    diff_sum = 0
    for i in range(1, len(numbers)):
        diff_sum += numbers[i] - numbers[i-1]
    avg_diff = diff_sum / (len(numbers) - 1)
    
    last = numbers[-1]
    prediction = last + avg_diff * 1.5
    # Thêm random nhẹ
    prediction += random.uniform(-2, 2)
    return max(0, min(99.99, prediction))

# 5. ENSEMBLE - Tổng hợp
def algo_ensemble(history):
    results = [
        algo_random(history),
        algo_hot(history),
        algo_cold(history),
        algo_trend(history)
    ]
    # Trung bình có trọng số (hot và trend nặng hơn)
    weights = [0.1, 0.35, 0.2, 0.35]
    weighted_sum = sum(r * w for r, w in zip(results, weights))
    return max(0, min(99.99, weighted_sum))

# === MAP THUẬT TOÁN ===
ALGO_MAP = {
    "RANDOM": algo_random,
    "HOT": algo_hot,
    "COLD": algo_cold,
    "TREND": algo_trend,
    "ENSEMBLE": algo_ensemble,
}

# === PHÂN TÍCH VÀ DỰ ĐOÁN ===
def analyze_and_predict(history, algo_name="ENSEMBLE"):
    if not history:
        return {
            "prediction": f"{random.uniform(0, 99.99):.2f}",
            "confidence": "30.0%",
            "algo": algo_name
        }
    
    func = ALGO_MAP.get(algo_name, algo_ensemble)
    prediction = func(history)
    
    # Tính độ tin cậy dựa trên lịch sử
    numbers = []
    for item in history:
        num = item.get('result') or item.get('number') or item.get('lucky_number')
        if num:
            try:
                numbers.append(float(num))
            except:
                pass
    
    if len(numbers) > 1:
        # Độ lệch chuẩn càng cao → độ tin cậy càng thấp
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

# === LỆNH /PREDICT ===
def predict(update, context):
    uid = update.effective_user.id
    data = user_data_store.get(uid, {})
    
    if 'user_id' not in data or 'secret_key' not in data:
        update.message.reply_text("⚠️ Chưa set ID/Key. Dùng /setid và /setkey")
        return
    
    # Lấy thuật toán từ args, mặc định ENSEMBLE
    algo = context.args[0].upper() if context.args else "ENSEMBLE"
    if algo not in ALGO_MAP:
        algo = "ENSEMBLE"
    
    update.message.reply_text(f"⏳ Đang phân tích với thuật toán *{algo}*...", parse_mode='Markdown')
    
    resp = fetch_winhash_data(data['user_id'], data['secret_key'])
    
    if "error" in resp:
        update.message.reply_text(f"❌ Lỗi: {resp['error']}")
        return
    if resp.get('code') == 1004:
        update.message.reply_text("❌ Sai User ID hoặc Secret Key")
        return
    
    history = resp.get('data', {}).get('history', [])
    if not history:
        update.message.reply_text("⚠️ Chưa có dữ liệu lịch sử")
        return
    
    result = analyze_and_predict(history, algo)
    
    keyboard = [
        [
            InlineKeyboardButton("🎲 RANDOM", callback_data="RANDOM"),
            InlineKeyboardButton("🔥 HOT", callback_data="HOT"),
        ],
        [
            InlineKeyboardButton("❄️ COLD", callback_data="COLD"),
            InlineKeyboardButton("📈 TREND", callback_data="TREND"),
        ],
        [
            InlineKeyboardButton("🧠 ENSEMBLE", callback_data="ENSEMBLE"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        f"🔮 **DỰ ĐOÁN LUCKY HASH**\n\n"
        f"🎯 Số: `{result['prediction']}`\n"
        f"📊 Độ tin cậy: {result['confidence']}\n"
        f"⚙️ Thuật toán: *{result['algo']}*\n\n"
        f"🔄 Chọn thuật toán khác bên dưới:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

# === CALLBACK CHO NÚT BẤM ===
def button_callback(update, context):
    query = update.callback_query
    query.answer()
    
    uid = update.effective_user.id
    data = user_data_store.get(uid, {})
    
    if 'user_id' not in data or 'secret_key' not in data:
        query.edit_message_text("⚠️ Chưa set ID/Key. Dùng /setid và /setkey")
        return
    
    algo = query.data
    query.edit_message_text(f"⏳ Đang phân tích với *{algo}*...", parse_mode='Markdown')
    
    resp = fetch_winhash_data(data['user_id'], data['secret_key'])
    
    if "error" in resp:
        query.edit_message_text(f"❌ Lỗi: {resp['error']}")
        return
    if resp.get('code') == 1004:
        query.edit_message_text("❌ Sai User ID hoặc Secret Key")
        return
    
    history = resp.get('data', {}).get('history', [])
    if not history:
        query.edit_message_text("⚠️ Chưa có dữ liệu lịch sử")
        return
    
    result = analyze_and_predict(history, algo)
    
    keyboard = [
        [
            InlineKeyboardButton("🎲 RANDOM", callback_data="RANDOM"),
            InlineKeyboardButton("🔥 HOT", callback_data="HOT"),
        ],
        [
            InlineKeyboardButton("❄️ COLD", callback_data="COLD"),
            InlineKeyboardButton("📈 TREND", callback_data="TREND"),
        ],
        [
            InlineKeyboardButton("🧠 ENSEMBLE", callback_data="ENSEMBLE"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        f"🔮 **DỰ ĐOÁN LUCKY HASH**\n\n"
        f"🎯 Số: `{result['prediction']}`\n"
        f"📊 Độ tin cậy: {result['confidence']}\n"
        f"⚙️ Thuật toán: *{result['algo']}*\n\n"
        f"🔄 Chọn thuật toán khác bên dưới:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

# === LỆNH CƠ BẢN ===
def start(update, context):
    update.message.reply_text(
        "🤖 **Lucky Hash Predictor Bot**\n\n"
        "/setid <ID> - Lưu User ID\n"
        "/setkey <KEY> - Lưu Secret Key\n"
        "/predict [algo] - Dự đoán (algo: RANDOM/HOT/COLD/TREND/ENSEMBLE)\n"
        "/status - Kiểm tra trạng thái\n"
        "/algos - Xem danh sách thuật toán\n\n"
        "Ví dụ: /predict HOT",
        parse_mode='Markdown'
    )

def set_id(update, context):
    if not context.args:
        update.message.reply_text("⚠️ /setid <User ID>")
        return
    uid = update.effective_user.id
    user_data_store[uid] = user_data_store.get(uid, {})
    user_data_store[uid]['user_id'] = context.args[0]
    update.message.reply_text(f"✅ Đã lưu User ID: {context.args[0]}")

def set_key(update, context):
    if not context.args:
        update.message.reply_text("⚠️ /setkey <Secret Key>")
        return
    uid = update.effective_user.id
    user_data_store[uid] = user_data_store.get(uid, {})
    user_data_store[uid]['secret_key'] = context.args[0]
    update.message.reply_text("✅ Đã lưu Secret Key")

def status_cmd(update, context):
    uid = update.effective_user.id
    data = user_data_store.get(uid, {})
    msg = "📋 **TRẠNG THÁI**\n"
    msg += f"User ID: {data.get('user_id', '❌ Chưa set')}\n"
    msg += f"Secret Key: {'✅ Đã set' if data.get('secret_key') else '❌ Chưa set'}\n"
    msg += f"Thuật toán mặc định: ENSEMBLE"
    update.message.reply_text(msg, parse_mode='Markdown')

def algos_cmd(update, context):
    update.message.reply_text(
        "📚 **DANH SÁCH THUẬT TOÁN**\n\n"
        "🎲 RANDOM - Random số 00.00-99.99\n"
        "🔥 HOT - Chọn số xuất hiện nhiều nhất\n"
        "❄️ COLD - Chọn số xuất hiện ít nhất\n"
        "📈 TREND - Phân tích xu hướng tăng/giảm\n"
        "🧠 ENSEMBLE - Tổng hợp tất cả thuật toán (mặc định)\n\n"
        "Dùng: /predict [TÊN]",
        parse_mode='Markdown'
    )

# === MAIN ===
def main():
    token = BOT_TOKEN
    if not token:
        print("❌ LỖI: Chưa set BOT_TOKEN")
        return
    
    updater = Updater(token, use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("setid", set_id))
    dp.add_handler(CommandHandler("setkey", set_key))
    dp.add_handler(CommandHandler("predict", predict))
    dp.add_handler(CommandHandler("status", status_cmd))
    dp.add_handler(CommandHandler("algos", algos_cmd))
    dp.add_handler(CallbackQueryHandler(button_callback))
    
    print("🚀 Bot đang chạy với 5 thuật toán...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
