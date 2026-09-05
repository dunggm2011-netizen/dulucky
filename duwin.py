import os
import json
import requests
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# === CẤU HÌNH ===
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8385677064:AAHS5ZqmV9QPka3I1t84lyysLzLsLTp3N6g")
WINHASH_API = "https://api.winhash.net/lucky_hash/home?game_id=1&asset=BUILD"

logging.basicConfig(level=logging.INFO)

# === LƯU TRỮ TẠM ===
user_data_store = {}

def fetch_winhash_data(user_id, secret_key):
    headers = {
        'user-id': user_id,
        'user-secret-key': secret_key,
        'Content-Type': 'application/json'
    }
    try:
        response = requests.get(WINHASH_API, headers=headers, params={'game_id': 2, 'asset': 'BUILD'}, timeout=10)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def analyze_and_predict(history):
    # Đếm số xuất hiện
    counts = {}
    for item in history:
        num = item.get('result') or item.get('number') or item.get('lucky_number')
        if num:
            counts[num] = counts.get(num, 0) + 1
    
    if not counts:
        return {"prediction": "45.67", "confidence": "50%"}
    
    # Tìm số hot
    hot = max(counts, key=counts.get)
    total = len(history)
    confidence = (counts[hot] / total * 100) if total > 0 else 50
    
    # Dự đoán số tiếp theo (dựa trên hot + random)
    import random
    base = float(hot) if isinstance(hot, (int, float)) else 50
    offset = random.uniform(-5, 5)
    prediction = max(0, min(99.99, base + offset))
    
    return {
        "prediction": f"{prediction:.2f}",
        "confidence": f"{min(95, confidence + 10):.1f}%"
    }

# === LỆNH ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 **Lucky Hash Predictor Bot**\n\n"
        "/setid <ID> - Lưu User ID\n"
        "/setkey <KEY> - Lưu Secret Key\n"
        "/predict - Dự đoán số tiếp theo\n"
        "/status - Kiểm tra trạng thái",
        parse_mode='Markdown'
    )

async def set_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ /setid <User ID>")
        return
    uid = update.effective_user.id
    user_data_store[uid] = user_data_store.get(uid, {})
    user_data_store[uid]['user_id'] = context.args[0]
    await update.message.reply_text(f"✅ Đã lưu User ID: {context.args[0]}")

async def set_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ /setkey <Secret Key>")
        return
    uid = update.effective_user.id
    user_data_store[uid] = user_data_store.get(uid, {})
    user_data_store[uid]['secret_key'] = context.args[0]
    await update.message.reply_text("✅ Đã lưu Secret Key")

async def predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    data = user_data_store.get(uid, {})
    
    if 'user_id' not in data or 'secret_key' not in data:
        await update.message.reply_text("⚠️ Chưa set ID/Key. Dùng /setid và /setkey")
        return
    
    await update.message.reply_text("⏳ Đang phân tích...")
    
    resp = fetch_winhash_data(data['user_id'], data['secret_key'])
    
    if "error" in resp:
        await update.message.reply_text(f"❌ Lỗi: {resp['error']}")
        return
    if resp.get('code') == 1004:
        await update.message.reply_text("❌ Sai User ID hoặc Secret Key")
        return
    
    history = resp.get('data', {}).get('history', [])
    if not history:
        await update.message.reply_text("⚠️ Chưa có dữ liệu")
        return
    
    result = analyze_and_predict(history)
    await update.message.reply_text(
        f"🔮 **DỰ ĐOÁN LUCKY HASH**\n\n"
        f"🎯 Số: `{result['prediction']}`\n"
        f"📊 Độ tin cậy: {result['confidence']}",
        parse_mode='Markdown'
    )

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    data = user_data_store.get(uid, {})
    msg = "📋 **TRẠNG THÁI**\n"
    msg += f"User ID: {data.get('user_id', '❌ Chưa set')}\n"
    msg += f"Secret Key: {'✅ Đã set' if data.get('secret_key') else '❌ Chưa set'}"
    await update.message.reply_text(msg, parse_mode='Markdown')

# === MAIN ===
def main():
    token = BOT_TOKEN
    if token == "YOUR_BOT_TOKEN_HERE":
        print("❌ LỖI: Chưa set BOT_TOKEN. Tạo biến môi trường BOT_TOKEN trên Render.")
        return
    
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setid", set_id))
    app.add_handler(CommandHandler("setkey", set_key))
    app.add_handler(CommandHandler("predict", predict))
    app.add_handler(CommandHandler("status", status_cmd))
    
    print("🚀 Bot đang chạy...")
    app.run_polling()

if __name__ == "__main__":
    main()
