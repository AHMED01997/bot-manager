import telebot

TOKEN = "8511151482:AAHH8LgUT4d0f43BXzP9kDpqorooYMJqM4M"
ADMIN_ID = 7800095838  # ضع ال ID الخاص بك هنا

bot = telebot.TeleBot(TOKEN)

users = {}

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    # إذا الرسالة من مدير البوت (أنت)
    if message.from_user.id == ADMIN_ID:
        try:
            user_id, reply = message.text.split(" ", 1)
            bot.send_message(int(user_id), reply)
            bot.send_message(ADMIN_ID, "✔ تم إرسال الرد للمستخدم.")
        except:
            bot.send_message(ADMIN_ID, "❌ الصيغة خطأ. استخدم: \n123456 رسالة الرد")
        return

    # إذا الرسالة من مستخدم عادي
    users[message.from_user.id] = message.from_user.username
    user_text = f"👤 مستخدم: @{message.from_user.username}\n🆔 ID: {message.from_user.id}\n\n💬 الرسالة:\n{message.text}"
    bot.send_message(ADMIN_ID, user_text)
    bot.send_message(message.chat.id, "تم إرسال رسالتك، سأرجع لك قريبًا 😊")


bot.polling()