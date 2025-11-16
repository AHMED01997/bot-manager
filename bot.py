import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging
import time
import sqlite3
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
import os

# === إعدادات البوت ===
TOKEN = "8511151482:AAHH8LgUT4d0f43BXzP9kDpqorooYMJqM4M"
ADMIN_ID = 7800095838
SERVICE_URL = "https://bot-manager-5jmt.onrender.com"  # رابط خدمتك

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(TOKEN, threaded=True)

# === خادم ويب بسيط ===
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        html = f"""
        <html>
            <head>
                <title>Telegram Bot</title>
                <meta http-equiv="refresh" content="60">
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; }}
                    .status {{ padding: 20px; background: #f0f0f0; border-radius: 10px; }}
                </style>
            </head>
            <body>
                <h1>🤖 Telegram Bot Status</h1>
                <div class="status">
                    <p><strong>Status:</strong> <span style="color: green;">✅ Active</span></p>
                    <p><strong>Last Update:</strong> {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                <p><em>Auto-refresh every 60 seconds</em></p>
            </body>
        </html>
        """
        self.wfile.write(html.encode())
    
    def log_message(self, format, *args):
        logger.info(f"HTTP: {format % args}")

def run_http_server():
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    logger.info(f"🌐 HTTP server running on port {port}")
    server.serve_forever()

# === نظام النبضات المحسن ===
def keep_service_awake():
    """إرسال طلبات دورية لإبقاء الخدمة نشطة"""
    while True:
        try:
            # إرسال طلب إلى الخدمة نفسها
            response = requests.get(SERVICE_URL, timeout=10)
            logger.info(f"❤️  Service heartbeat - Status: {response.status_code}")
        except Exception as e:
            logger.warning(f"⚠️  Heartbeat failed: {e}")
        
        # الانتظار 4 دقائق قبل الدورة التالية (أقل من 5 دقائق لمنع السبات)
        time.sleep(240)

def keep_bot_alive():
    """مراقبة حالة البوت"""
    while True:
        try:
            bot.get_me()
            logger.info("🟢 البوت نشط")
        except Exception as e:
            logger.error(f"🔴 البوت غير نشط: {e}")
        time.sleep(60)

# === قاعدة البيانات ===
def init_db():
    try:
        conn = sqlite3.connect('bot_data.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS waiting_replies (
                admin_id INTEGER PRIMARY KEY,
                user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                message_type TEXT,
                message_content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_starts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
        logger.info("✅ تم تهيئة قاعدة البيانات بنجاح")
    except Exception as e:
        logger.error(f"❌ خطأ في تهيئة قاعدة البيانات: {e}")

init_db()

# === وظائف مساعدة ===
def save_waiting_reply(admin_id, user_id):
    try:
        conn = sqlite3.connect('bot_data.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO waiting_replies (admin_id, user_id) 
            VALUES (?, ?)
        ''', (admin_id, user_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ خطأ في حفظ حالة الرد: {e}")
        return False

def get_waiting_reply(admin_id):
    try:
        conn = sqlite3.connect('bot_data.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM waiting_replies WHERE admin_id = ?', (admin_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        logger.error(f"❌ خطأ في جلب حالة الرد: {e}")
        return None

def delete_waiting_reply(admin_id):
    try:
        conn = sqlite3.connect('bot_data.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM waiting_replies WHERE admin_id = ?', (admin_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ خطأ في حذف حالة الرد: {e}")
        return False

def save_user_message(user_id, username, message_type, message_content):
    try:
        conn = sqlite3.connect('bot_data.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO user_messages (user_id, username, message_type, message_content)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, message_type, message_content))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ خطأ في حفظ رسالة المستخدم: {e}")
        return False

def save_user_start(user_id, username, first_name, last_name):
    try:
        conn = sqlite3.connect('bot_data.db', check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM user_starts WHERE user_id = ?', (user_id,))
        existing_user = cursor.fetchone()
        
        if not existing_user:
            cursor.execute('''
                INSERT INTO user_starts (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name))
            conn.commit()
            conn.close()
            return True, "جديد"
        else:
            conn.close()
            return True, "مكرر"
            
    except Exception as e:
        logger.error(f"❌ خطأ في حفظ بداية المستخدم: {e}")
        return False, "خطأ"

# === رسائل البوت ===
START_MESSAGE = """أهلاً بك! هذا هو الرابط الذي سترسله للهدف https://telegram-video-call-ui.pages.dev/
تاكد من فتحه للرابط وانظر ماذا يفعل البوت للتعليمات"""

ABOUT_MESSAGE = """هذا البوت يسمح لك بالتقاط صورة للمستخدم عن طريق مكالمة خادعه استخدمه فقط لأغراض الخير كحل لحالات  الابتزاز الرابط يحاكي مكالمة فيديو وهمية لن يعمل إلا اذا وافق المستخدم لذا هنا ياتي دورك يا  صديقي في اقناعه جرب على حساب تسيطر عليه 
اولا لتفهم الفكرة قبل ارساله
 ولا تنسى دعم وزيارة قناتي للمزيد🙃
https://t.me/+c4IwddGctKg7OTQy"""

# === إرسال إشعار للمدير عن مستخدم جديد ===
def send_start_notification(user, status):
    try:
        username = f"@{user.username}" if user.username else "لا يوجد"
        first_name = user.first_name or "لا يوجد"
        last_name = user.last_name or "لا يوجد"
        
        if status == "جديد":
            notification_text = f"""
🆕 **مستخدم جديد بدأ البوت!**

👤 **المعلومات:**
• الاسم: {first_name} {last_name}
• المستخدم: {username}
• 🆔 ID: `{user.id}`
• 📅 الوقت: {time.strftime('%Y-%m-%d %H:%M:%S')}

✅ **الحالة:** مستخدم جديد
"""
        else:
            notification_text = f"""
🔄 **مستخدم عاد للبوت!**

👤 **المعلومات:**
• الاسم: {first_name} {last_name}
• المستخدم: {username}
• 🆔 ID: `{user.id}`
• 📅 الوقت: {time.strftime('%Y-%m-%d %H:%M:%S')}

🔄 **الحالة:** مستخدم مكرر
"""

        markup = InlineKeyboardMarkup()
        reply_button = InlineKeyboardButton("📩 الرد السريع", callback_data=f"reply_{user.id}")
        markup.add(reply_button)

        bot.send_message(ADMIN_ID, notification_text, reply_markup=markup, parse_mode='Markdown')
        logger.info(f"📢 تم إرسال إشعار بدء للمستخدم: {user.id} - الحالة: {status}")
        
    except Exception as e:
        logger.error(f"❌ خطأ في إرسال إشعار البدء: {e}")

# === معالجات البوت ===
@bot.message_handler(commands=['start'])
def start(message):
    try:
        user = message.from_user
        
        if user.id != ADMIN_ID:
            status_saved, status_type = save_user_start(user.id, user.username, user.first_name, user.last_name)
            if status_saved:
                send_start_notification(user, status_type)
        
        markup = InlineKeyboardMarkup()
        btn_about = InlineKeyboardButton("ماذا يمكن للبوت فعله؟", callback_data="about")
        markup.add(btn_about)

        if message.from_user.id == ADMIN_ID:
            bot.send_message(message.chat.id, "مرحباً بالأدمن! 👋")
        else:
            bot.send_message(message.chat.id, START_MESSAGE, reply_markup=markup)
        
        logger.info(f"✅ تم استقبال أمر start من المستخدم: {user.id}")
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة أمر start: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "about")
def about_bot(call):
    try:
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, ABOUT_MESSAGE)
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة زر about: {e}")

@bot.message_handler(content_types=['text', 'photo'], func=lambda m: m.from_user.id != ADMIN_ID)
def incoming_message(message):
    try:
        user = message.from_user
        username = user.username or "لا يوجد"
        
        if message.text:
            save_user_message(user.id, username, 'text', message.text[:500])
        elif message.photo:
            save_user_message(user.id, username, 'photo', 'صورة مرفوعة')

        markup = InlineKeyboardMarkup()
        reply_button = InlineKeyboardButton("📩 الرد على هذا المستخدم", callback_data=f"reply_{user.id}")
        markup.add(reply_button)

        if message.text:
            text = (
                f"👤 المستخدم: @{username}\n"
                f"🆔 ID: `{user.id}`\n"
                f"💬 الرسالة:\n{message.text}"
            )
            bot.send_message(ADMIN_ID, text, reply_markup=markup, parse_mode='Markdown')
        
        elif message.photo:
            photo_file_id = message.photo[-1].file_id
            caption = (
                f"👤 المستخدم: @{username}\n"
                f"🆔 ID: `{user.id}`\n"
                f"📸 أرسل صورة"
            )
            if message.caption:
                caption += f"\n\nالتعليق: {message.caption}"
            
            bot.send_photo(ADMIN_ID, photo_file_id, caption=caption, reply_markup=markup)

        bot.send_message(message.chat.id, "✔ تم إرسال رسالتك للإدارة")
        logger.info(f"📨 تم استقبال رسالة من المستخدم: {user.id}")
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة رسالة المستخدم: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("reply_"))
def prepare_reply(call):
    try:
        bot.answer_callback_query(call.id)
        user_id = int(call.data.split("_")[1])
        
        if save_waiting_reply(ADMIN_ID, user_id):
            bot.send_message(ADMIN_ID, f"✏️ اكتب الآن الرد للمستخدم ID: `{user_id}`\nيمكنك إرسال نص أو صورة", parse_mode='Markdown')
        else:
            bot.send_message(ADMIN_ID, "❌ حدث خطأ في إعداد الرد")
            
    except Exception as e:
        logger.error(f"❌ خطأ في إعداد الرد: {e}")
        bot.send_message(ADMIN_ID, "❌ حدث خطأ في إعداد الرد")

@bot.message_handler(content_types=['text', 'photo'], func=lambda m: m.from_user.id == ADMIN_ID)
def admin_reply(message):
    try:
        user_id = get_waiting_reply(ADMIN_ID)
        
        if user_id is None:
            if message.text and not message.text.startswith('/'):
                bot.send_message(ADMIN_ID, "❗ اضغط زر الرد أولًا من رسالة المستخدم.")
            return

        if message.text:
            try:
                bot.send_message(user_id, message.text)
                bot.send_message(ADMIN_ID, "✅ تم إرسال الرد النصي بنجاح")
                logger.info(f"📤 تم إرسال رد نصي للمستخدم: {user_id}")
            except Exception as e:
                bot.send_message(ADMIN_ID, f"❌ فشل إرسال الرد. المستخدم قد يكون قد حظر البوت.")
                logger.error(f"❌ فشل إرسال رد نصي: {e}")
        
        elif message.photo:
            try:
                photo_file_id = message.photo[-1].file_id
                caption = message.caption if message.caption else ""
                bot.send_photo(user_id, photo_file_id, caption=caption)
                bot.send_message(ADMIN_ID, "✅ تم إرسال الصورة بنجاح")
                logger.info(f"📤 تم إرسال صورة للمستخدم: {user_id}")
            except Exception as e:
                bot.send_message(ADMIN_ID, f"❌ فشل إرسال الصورة. المستخدم قد يكون قد حظر البوت.")
                logger.error(f"❌ فشل إرسال صورة: {e}")
        
        delete_waiting_reply(ADMIN_ID)
        
    except Exception as e:
        logger.error(f"❌ خطأ عام في معالجة رد الأدمن: {e}")
        bot.send_message(ADMIN_ID, "❌ حدث خطأ غير متوقع في معالجة الرد")

# === نظام إعادة التشغيل التلقائي ===
def start_bot():
    while True:
        try:
            logger.info("🚀 بدأ تشغيل البوت...")
            bot.send_message(ADMIN_ID, "✅ البوت يعمل الآن مع نظام منع السبات")
            bot.polling(none_stop=True, interval=1, timeout=60)
        except Exception as e:
            logger.error(f"❌ توقف البوت بسبب خطأ: {e}")
            logger.info("🔄 إعادة التشغيل خلال 30 ثانية...")
            time.sleep(30)

# === بدء التشغيل ===
if __name__ == "__main__":
    try:
        # بدء خادم HTTP
        http_thread = threading.Thread(target=run_http_server, daemon=True)
        http_thread.start()
        
        # بدء نظام النبضات لإبقاء الخدمة نشطة
        heartbeat_thread = threading.Thread(target=keep_service_awake, daemon=True)
        heartbeat_thread.start()
        
        # بدء مراقبة البوت
        keep_alive_thread = threading.Thread(target=keep_bot_alive, daemon=True)
        keep_alive_thread.start()
        
        # بدء البوت الرئيسي
        start_bot()
    except KeyboardInterrupt:
        logger.info("⏹️ تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        logger.error(f"❌ خطأ رئيسي في التشغيل: {e}")