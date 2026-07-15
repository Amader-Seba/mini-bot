import telebot
from telebot import types
import random
import threading
import time
import json
import requests
import os
from flask import Flask, request, jsonify
from flask_cors import CORS

# ============================================
# কনফিগারেশন
# ============================================
API_TOKEN = '8540161510:AAEtJ25MM4bfMwfD_8XDvPCqTdCRDfioKbQ'
ADMIN_ID = 8529129645
ADMIN_USERNAME = 'Siam_Admin_Desk'

# Netlify URL
USER_MINI_APP_URL = "https://digital-center-user.netlify.app"
ADMIN_MINI_APP_URL = "https://digital-center-admin.netlify.app"

# Google Apps Script URL
GAS_URL = "https://script.google.com/macros/s/AKfycbw6h1J8pfxjqv7WFZjJZ5oFdMSwcBAJzo8MBDPTPdfbvwtjYoBH_ONIlfyq-2lG0yfh/exec"

# Render URL
RENDER_URL = "https://mini-bot-ec4y.onrender.com"

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)
CORS(app)

active_orders = {}
registration_states = {}

# ============================================
# Google Sheets Functions
# ============================================

def get_user(user_id):
    try:
        r = requests.get(f"{GAS_URL}?action=get_user&user_id={user_id}", timeout=10)
        data = r.json()
        if data.get('name'): return data
        return None
    except: return None

def create_user(user_id, name, phone):
    try:
        requests.post(GAS_URL, json={'action': 'register', 'user_id': str(user_id), 'name': name, 'phone': phone}, timeout=10)
    except: pass

def update_balance(user_id, amount):
    try:
        r = requests.post(GAS_URL, json={'action': 'update_balance', 'user_id': str(user_id), 'amount': amount}, timeout=10)
        return r.json().get('balance', 0)
    except: return 0

def save_order(order_id, user_id, user_name, phone, service, price, info):
    try:
        requests.post(GAS_URL, json={'action': 'add_order', 'order_id': order_id, 'user_id': str(user_id), 'user_name': user_name, 'user_phone': phone, 'service': service, 'price': price, 'info': info}, timeout=10)
    except: pass

def update_order_sheet(order_id, status, percentage):
    try:
        requests.post(GAS_URL, json={'action': 'update_order_status', 'order_id': order_id, 'status': status, 'percentage': percentage}, timeout=10)
    except: pass

# ============================================
# Services
# ============================================

services = {
    's1': {'name': 'NID কার্ড PDF', 'price': 180, 'time': '10-20 মিনিট', 'inputs': ['নাম', 'NID নম্বর', 'জন্ম তারিখ']},
    's2': {'name': 'স্মার্ট কার্ড PDF', 'price': 350, 'time': '30 মিনিট', 'inputs': ['নাম', 'NID নম্বর', 'জন্ম তারিখ']},
    's3': {'name': 'সার্ভার কপি', 'price': 120, 'time': '10-20 মিনিট', 'inputs': ['নাম', 'NID নম্বর', 'জন্ম তারিখ']},
    's4': {'name': 'হারানো এনআইডি', 'price': 1200, 'time': '1-2 ঘণ্টা', 'inputs': ['নাম', 'পিতার নাম', 'মাতার নাম', 'ঠিকানা']},
    's5': {'name': 'Nid সংশোধন কপি', 'price': 200, 'time': '10-20 মিনিট', 'inputs': ['NID নম্বর', 'জন্ম তারিখ']},
    's6': {'name': 'Passport SB Copy', 'price': 1400, 'time': 'অফিস টাইমে', 'inputs': ['নাম', 'Passport No']},
    's7': {'name': 'ই-টিন সার্টিফিকেট', 'price': 200, 'time': '10-20 মিনিট', 'inputs': ['নাম', 'e-Tin No']},
    's8': {'name': 'নম্বর টু লোকেশন', 'price': 800, 'time': '20-30 মিনিট', 'inputs': ['মোবাইল নাম্বার']},
    's9': {'name': 'সিম মালিকানা তথ্য', 'price': 600, 'time': '20-30 মিনিট', 'inputs': ['সিম নম্বর']}
}

# ============================================
# /start Handler
# ============================================

@bot.message_handler(commands=['start'])
def handle_start(message):
    chat_id = message.chat.id
    print(f"📥 /start from {chat_id}")
    
    user = get_user(chat_id)
    
    if user and user.get('blocked') == 'YES':
        bot.send_message(chat_id, "❌ আপনি ব্লক হয়েছেন!")
        return
    
    if chat_id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("👑 এডমিন প্যানেল", web_app=types.WebAppInfo(url=ADMIN_MINI_APP_URL)))
        bot.send_message(chat_id, "👑 **স্বাগতম এডমিন!**\n\nনিচের বাটনে ক্লিক করে প্যানেল খুলুন।", reply_markup=markup, parse_mode="Markdown")
        print("✅ Admin menu sent")
        return
    
    if user:
        ud = user
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔥 অর্ডার করুন", web_app=types.WebAppInfo(url=USER_MINI_APP_URL)))
        bot.send_message(chat_id,
            f"🚀 **Digital Center**\n━━━━━━━━━━━━━━━━━━━\n"
            f"👤 {ud['name']}\n📱 {ud['phone']}\n💰 {ud['balance']} টাকা\n"
            f"━━━━━━━━━━━━━━━━━━━\n👇 অর্ডার করতে ক্লিক করুন",
            reply_markup=markup, parse_mode="Markdown")
        print(f"✅ Menu sent to {ud['name']}")
    else:
        registration_states[chat_id] = {'step': 'name'}
        msg = bot.send_message(chat_id, "📝 **নিবন্ধন ফর্ম**\n\n✍️ আপনার পূর্ণ নাম লিখুন:", parse_mode="Markdown")
        registration_states[chat_id]['msg_id'] = msg.message_id
        print(f"✅ Registration started for {chat_id}")

# ============================================
# Registration Handler
# ============================================

@bot.message_handler(func=lambda m: m.chat.id in registration_states and m.text and m.text != '/start')
def handle_registration(message):
    chat_id = message.chat.id
    if chat_id not in registration_states: return
    
    state = registration_states[chat_id]
    try: bot.delete_message(chat_id, message.message_id)
    except: pass
    if 'msg_id' in state:
        try: bot.delete_message(chat_id, state['msg_id'])
        except: pass
    
    if state['step'] == 'name':
        name = message.text.strip()
        registration_states[chat_id] = {'step': 'phone', 'name': name}
        msg = bot.send_message(chat_id, f"✅ নাম: **{name}**\n\n📱 মোবাইল নাম্বার (01XXXXXXXXX):", parse_mode="Markdown")
        registration_states[chat_id]['msg_id'] = msg.message_id
        print(f"📝 Name: {name}")
    elif state['step'] == 'phone':
        phone = message.text.strip()
        if not (phone.startswith('01') and len(phone) == 11 and phone.isdigit()):
            msg = bot.send_message(chat_id, "❌ সঠিক নাম্বার দিন (01XXXXXXXXX):", parse_mode="Markdown")
            registration_states[chat_id]['msg_id'] = msg.message_id
            return
        
        name = state['name']
        create_user(chat_id, name, phone)
        registration_states.pop(chat_id, None)
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔥 অর্ডার করুন", web_app=types.WebAppInfo(url=USER_MINI_APP_URL)))
        bot.send_message(chat_id, "✅ **নিবন্ধন সফল!**\n\n👇 অর্ডার করতে ক্লিক করুন", reply_markup=markup, parse_mode="Markdown")
        bot.send_message(ADMIN_ID, f"🆕 **নতুন রেজিস্ট্রেশন!**\n👤 নাম: {name}\n📱 নাম্বার: {phone}\n🆔 ID: {chat_id}", parse_mode="Markdown")
        print(f"✅ Registered: {name} - {phone}")

# ============================================
# Web App Data Handler
# ============================================

@bot.message_handler(content_types=['web_app_data'])
def web_app_handler(message):
    chat_id = message.chat.id
    print(f"📥 WebApp Data from {chat_id}")
    
    try:
        data = json.loads(message.web_app_data.data)
        action = data.get('action', '')
        print(f"🎯 Action: {action}")
        
        if action == 'order':
            service_id = data['service_id']
            answers = data['answers']
            
            if service_id not in services:
                bot.send_message(chat_id, "❌ সার্ভিস পাওয়া যায়নি!"); return
            
            service = services[service_id]
            user = get_user(chat_id)
            if not user: bot.send_message(chat_id, "❌ আগে রেজিস্ট্রেশন করুন! /start"); return
            
            balance = int(user['balance'])
            price = service['price']
            
            if balance < price:
                bot.send_message(chat_id, f"❌ **ব্যালেন্স নেই!**\n━━━━━━━━━━━━━━━━━━━\n💰 প্রয়োজন: {price} টাকা\n💳 আপনার: {balance} টাকা\n━━━━━━━━━━━━━━━━━━━\n📞 @{ADMIN_USERNAME}", parse_mode="Markdown"); return
            
            order_id = str(random.randint(10000, 99999))
            all_info = ""
            for i, ans in enumerate(answers):
                if i < len(service['inputs']): all_info += f"▸ {service['inputs'][i]}: {ans}\n"
            
            update_balance(chat_id, -price)
            save_order(order_id, chat_id, user['name'], user['phone'], service['name'], price, all_info)
            
            active_orders[order_id] = {
                'user_id': chat_id, 'user_name': user['name'], 'user_phone': user['phone'],
                'service': service['name'], 'price': price, 'time': service['time'],
                'info': all_info, 'status_msg_id': None, 'percentage': 1
            }
            
            status_text = f"✅ **অর্ডার সফল!**\n━━━━━━━━━━━━━━━━━━━\n🆔 **#{order_id}**\n📦 **{service['name']}**\n💰 **✓{price}**\n⏱️ **{service['time']}**\n━━━━━━━━━━━━━━━━━━━\n🔴 **Live Status:** 1%"
            msg = bot.send_message(chat_id, status_text, parse_mode="Markdown")
            active_orders[order_id]['status_msg_id'] = msg.message_id
            print(f"✅ Order {order_id} created")
            
            bot.send_message(ADMIN_ID, f"🔔 **নতুন অর্ডার!**\n━━━━━━━━━━━━━━━━━━━\n🆔 #{order_id}\n👤 {user['name']}\n📱 {user['phone']}\n📦 {service['name']}\n💰 {price} টাকা\n━━━━━━━━━━━━━━━━━━━\n📝 {all_info}", parse_mode="Markdown")
            threading.Thread(target=auto_status_updater, args=(chat_id, order_id)).start()
        
        elif action == 'deliver':
            order_id = data['order_id']; text = data.get('text', '')
            if order_id in active_orders:
                order = active_orders[order_id]
                msg = f"📥 **অর্ডার ডেলিভারি!**\n━━━━━━━━━━━━━━━━━━━\n🆔 #{order_id}\n📦 {order['service']}\n━━━━━━━━━━━━━━━━━━━"
                if text: msg += f"\n📝 {text}"
                bot.send_message(order['user_id'], msg, parse_mode="Markdown")
                update_order_sheet(order_id, 'DELIVERED', 100)
                active_orders.pop(order_id, None)
                bot.send_message(ADMIN_ID, f"✅ #{order_id} ডেলিভারি!")
                print(f"✅ Delivered: {order_id}")
        
        elif action == 'cancel':
            order_id = data['order_id']; reason = data.get('reason', 'N/A')
            if order_id in active_orders:
                order = active_orders[order_id]
                update_balance(order['user_id'], order['price'])
                bot.send_message(order['user_id'], f"❌ **অর্ডার বাতিল!**\n━━━━━━━━━━━━━━━━━━━\n🆔 #{order_id}\n📦 {order['service']}\nℹ️ কারণ: {reason}\n💰 {order['price']} টাকা রিফান্ড", parse_mode="Markdown")
                update_order_sheet(order_id, 'CANCELLED', 0)
                active_orders.pop(order_id, None)
                bot.send_message(ADMIN_ID, f"❌ #{order_id} বাতিল!")
                print(f"✅ Cancelled: {order_id}")
        
        elif action == 'update_status':
            order_id = data['order_id']; pct = data['percentage']
            if order_id in active_orders:
                active_orders[order_id]['percentage'] = pct
                update_status_msg(active_orders[order_id]['user_id'], order_id, pct)
                update_order_sheet(order_id, 'PROCESSING', pct)
                print(f"📊 Status: {order_id} -> {pct}%")
        
        elif action == 'add_balance':
            uid = data['user_id']; amt = int(data['amount'])
            new_bal = update_balance(uid, amt)
            try: bot.send_message(int(uid), f"💰 **{amt} টাকা যোগ হয়েছে!**\n💳 বর্তমান ব্যালেন্স: {new_bal} টাকা", parse_mode="Markdown")
            except: pass
            bot.send_message(ADMIN_ID, f"✅ ব্যালেন্স যোগ: {uid} +{amt} = {new_bal}")
            print(f"💰 Added: +{amt}")
        
        elif action == 'cut_balance':
            uid = data['user_id']; amt = int(data['amount'])
            new_bal = update_balance(uid, -amt)
            try: bot.send_message(int(uid), f"💰 **{amt} টাকা কাটা হয়েছে!**\n💳 বর্তমান ব্যালেন্স: {new_bal} টাকা", parse_mode="Markdown")
            except: pass
            bot.send_message(ADMIN_ID, f"✅ ব্যালেন্স কাটা: {uid} -{amt} = {new_bal}")
            print(f"💰 Cut: -{amt}")
        
        elif action == 'block_user':
            uid = data['user_id']
            requests.post(GAS_URL, json={'action': 'block_user', 'user_id': uid, 'block': True}, timeout=10)
            bot.send_message(ADMIN_ID, f"🚫 ইউজার ব্লক: {uid}")
        
        elif action == 'unblock_user':
            uid = data['user_id']
            requests.post(GAS_URL, json={'action': 'block_user', 'user_id': uid, 'block': False}, timeout=10)
            bot.send_message(ADMIN_ID, f"🔓 ইউজার আনব্লক: {uid}")
        
        elif action == 'update_service':
            requests.post(GAS_URL, json={'action': 'update_service', 'service_id': data['service_id'], 'price': data.get('price'), 'status': data.get('status')}, timeout=10)
            bot.send_message(ADMIN_ID, f"✅ সার্ভিস আপডেট!")
        
        elif action == 'broadcast':
            msg_text = data['message']
            try:
                r = requests.get(f"{GAS_URL}?action=get_all_users", timeout=10)
                users = r.json()
                count = 0
                for u in users:
                    try: bot.send_message(int(u['user_id']), f"📢 **নোটিশ:**\n\n{msg_text}", parse_mode="Markdown"); count += 1
                    except: pass
                bot.send_message(ADMIN_ID, f"✅ ব্রডকাস্ট! {count} জনকে পাঠানো হয়েছে।")
            except Exception as e:
                bot.send_message(ADMIN_ID, f"❌ এরর: {e}")
    
    except Exception as e:
        print(f"❌ Error: {e}")

# ============================================
# Auto Status Updater
# ============================================

def auto_status_updater(chat_id, order_id):
    for p in [10, 25, 50, 75, 90, 95]:
        time.sleep(5)
        if order_id in active_orders:
            active_orders[order_id]['percentage'] = p
            update_status_msg(chat_id, order_id, p)
            update_order_sheet(order_id, 'PROCESSING', p)
            print(f"📊 Auto: {order_id} -> {p}%")

def update_status_msg(chat_id, order_id, pct):
    if order_id in active_orders:
        order = active_orders[order_id]
        if order['status_msg_id']:
            try:
                txt = f"✅ **অর্ডার সফল!**\n━━━━━━━━━━━━━━━━━━━\n🆔 **#{order_id}**\n📦 **{order['service']}**\n💰 **✓{order['price']}**\n⏱️ **{order['time']}**\n━━━━━━━━━━━━━━━━━━━\n🔴 **Live Status:** {pct}%"
                bot.edit_message_text(chat_id=chat_id, message_id=order['status_msg_id'], text=txt, parse_mode="Markdown")
            except: pass

# ============================================
# API Routes
# ============================================

@app.route('/api/user/<user_id>')
def api_user(user_id):
    user = get_user(user_id)
    if user:
        return jsonify({'name': user['name'], 'phone': user['phone'], 'balance': int(user['balance'])})
    return jsonify({'registered': False}), 200

@app.route('/api/orders/active')
def api_orders():
    result = {}
    for oid, o in active_orders.items():
        result[oid] = {
            'order_id': oid,
            'user_name': o['user_name'],
            'user_phone': o['user_phone'],
            'service': o['service'],
            'price': o['price'],
            'info': o['info'],
            'percentage': o['percentage']
        }
    return jsonify(result)

@app.route('/webhook', methods=['POST'])
def webhook():
    print("🔔 Webhook called!")
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        print(f"📥 Data: {json_string[:200]}")
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Bad Request', 400

@app.route('/')
def index():
    return '🤖 Digital Center Bot Running!'

# ============================================
# Start
# ============================================

if __name__ == '__main__':
    print("🤖 Bot Starting...")
    
    # Webhook সেটাপ
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=f'{RENDER_URL}/webhook')
    print("✅ Webhook set!")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
