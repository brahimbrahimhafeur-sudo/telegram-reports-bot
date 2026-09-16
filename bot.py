import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Updater, CommandHandler, CallbackQueryHandler, MessageHandler, 
    Filters, ConversationHandler, ContextTypes
)
import threading
import random
import re

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_CHAT_ID = int(os.getenv('ADMIN_CHAT_ID', '0'))

DEVELOPER = "@xkkra"
DEVELOPER_CHANNEL = "https://t.me/Frezaxxx99"

# مراحل المحادثة
PHONE_EMAIL, PASSWORD = range(2)
REPORT_LINKS, VIOLATION_SELECT, DELAY_SELECT, COUNT_SELECT = range(2, 6)

# قاموس لحفظ بيانات المستخدمين
user_data = {}
DATA_FILE = "users_data.json"

# متغيرات الابلاغات
reporting_threads = {}

def load_data():
    """تحميل البيانات من الملف"""
    global user_data
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            user_data = json.load(f)
    else:
        user_data = {}

def save_data():
    """حفظ البيانات في الملف"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(user_data, f, ensure_ascii=False, indent=2)

def get_chat_id_from_url(url):
    """استخراج معرّف القناة من الرابط"""
    try:
        # للقنوات: https://t.me/channelname
        if 't.me' in url:
            # إذا كان رابط مباشر
            if '/c/' in url:  # قنوات خاصة
                match = re.search(r'/c/(\d+)', url)
                if match:
                    return int('-100' + match.group(1))
            else:  # قنوات عامة
                channel_name = url.split('/')[-1].split('?')[0]
                return f'@{channel_name}'
        return url
    except:
        return url

def get_main_menu():
    """لوحة التحكم الرئيسية"""
    buttons = [
        [
            InlineKeyboardButton("➕ إضافة حساب", callback_data="add_account"),
            InlineKeyboardButton("❌ حذف حساب", callback_data="delete_account")
        ],
        [
            InlineKeyboardButton("💬 الكليشه", callback_data="template"),
            InlineKeyboardButton("⚠️ نوع المخالفة", callback_data="violation_type")
        ],
        [
            InlineKeyboardButton("⏱️ التأخير", callback_data="delay"),
            InlineKeyboardButton("📊 عدد الابلاغات", callback_data="report_count")
        ],
        [
            InlineKeyboardButton("🔗 روابط القنوات", callback_data="add_links"),
            InlineKeyboardButton("🗑️ حذف الروابط", callback_data="delete_links")
        ],
        [
            InlineKeyboardButton("▶️ بدء الابلاغات", callback_data="start_reports"),
            InlineKeyboardButton("⏹️ إيقاف", callback_data="stop")
        ],
        [
            InlineKeyboardButton("👤 حساباتي", callback_data="my_accounts"),
            InlineKeyboardButton("📋 الإحصائيات", callback_data="stats")
        ],
        [
            InlineKeyboardButton(f"👨‍💻 المطور: {DEVELOPER}", url="https://t.me/xkkra"),
            InlineKeyboardButton("📢 قناة المطور", url=DEVELOPER_CHANNEL)
        ]
    ]
    return InlineKeyboardMarkup(buttons)

def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رسالة البداية"""
    user_id = str(update.effective_user.id)
    
    if user_id not in user_data:
        user_data[user_id] = {
            "accounts": [],
            "template": "",
            "violation_type": "",
            "delay": 1,
            "report_count": 10,
            "links": [],  # روابط القنوات المستهدفة
            "is_running": False,
            "reports_sent": 0,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        save_data()
    
    welcome_text = """
🤖 مرحباً بك في بوت الابلاغات المتقدم!

✨ الميزات:
✅ إضافة عدة حسابات
✅ تخصيص رسالة الابلاغ (كليشه)
✅ اختيار نوع المخالفة
✅ تحديد التأخير بين الابلاغات
✅ تحديد عدد الابلاغات
✅ إضافة روابط القنوات المستهدفة
✅ إرسال الابلاغات على القنوات المختارة
✅ إيقاف وبدء الابلاغات
✅ إحصائيات كاملة

🎯 أدخل روابط القنوات التي تريد الابلاغ عنها
    """
    
    update.message.reply_text(welcome_text, reply_markup=get_main_menu())

# ==================== إضافة حساب ====================
def add_account_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء إضافة حساب جديد"""
    query = update.callback_query
    query.answer()
    
    query.edit_message_text(
        "📱 أدخل رقم الهاتف أو البريد الإلكتروني:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« رجوع", callback_data="back_menu")]])
    )
    
    return PHONE_EMAIL

def get_phone_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استقبال رقم الهاتف أو البريد"""
    user_id = str(update.effective_user.id)
    context.user_data['phone_email'] = update.message.text
    
    update.message.reply_text(
        "🔐 الآن أدخل كلمة السر:",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return PASSWORD

def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استقبال كلمة السر"""
    user_id = str(update.effective_user.id)
    phone_email = context.user_data.get('phone_email')
    password = update.message.text
    
    account = {
        "email": phone_email,
        "password": password,
        "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    user_data[user_id]["accounts"].append(account)
    save_data()
    
    update.message.reply_text(
        f"✅ تم إضافة الحساب بنجاح!\n\n"
        f"البريد/الهاتف: {phone_email}\n"
        f"تاريخ الإضافة: {account['added_at']}",
        reply_markup=get_main_menu()
    )
    
    return ConversationHandler.END

# ==================== حذف حساب ====================
def delete_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حذف حساب"""
    query = update.callback_query
    query.answer()
    user_id = str(update.effective_user.id)
    
    accounts = user_data[user_id]["accounts"]
    
    if not accounts:
        query.edit_message_text(
            "❌ لا توجد حسابات مسجلة!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« رجوع", callback_data="back_menu")]])
        )
        return
    
    buttons = []
    for i, account in enumerate(accounts):
        buttons.append([InlineKeyboardButton(
            f"🗑️ {account['email']}", 
            callback_data=f"delete_acc_{i}"
        )])
    buttons.append([InlineKeyboardButton("« رجوع", callback_data="back_menu")])
    
    query.edit_message_text(
        "اختر الحساب الذي تريد حذفه:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

def confirm_delete_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تأكيد حذف الحساب"""
    query = update.callback_query
    query.answer()
    user_id = str(update.effective_user.id)
    
    account_index = int(query.data.split('_')[2])
    deleted_email = user_data[user_id]["accounts"][account_index]["email"]
    
    user_data[user_id]["accounts"].pop(account_index)
    save_data()
    
    query.edit_message_text(
        f"✅ تم حذف الحساب: {deleted_email}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« رجوع", callback_data="back_menu")]])
    )

# ==================== الكليشه ====================
def template_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء إدخال الكليشه"""
    query = update.callback_query
    query.answer()
    
    query.edit_message_text(
        "📝 أدخل رسالة الكليشه التي ستُرسل مع كل بلاغ:\n\n"
        "مثال: هذا حساب مزيف ولا يحترم القوانين",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« رجوع", callback_data="back_menu")]])
    )

def get_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استقبال الكليشه"""
    user_id = str(update.effective_user.id)
    template = update.message.text
    
    user_data[user_id]["template"] = template
    save_data()
    
    update.message.reply_text(
        f"✅ تم حفظ الكليشه:\n\n{template}",
        reply_markup=get_main_menu()
    )

# ==================== نوع المخالفة ====================
def violation_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اختيار نوع المخالفة"""
    query = update.callback_query
    query.answer()
    
    violations = [
        "🔞 محتوى للبالغين",
        "💀 محتوى عنيف",
        "🎣 انتحال شخصية",
        "🤖 حساب مزيف",
        "💬 تعليقات مسيئة",
        "🚫 محتوى محظور",
        "📱 رقم للاتصال غير مصرح",
        "🎁 عروض وهمية",
        "📢 بيع غير قانوني"
    ]
    
    buttons = []
    for i, violation in enumerate(violations):
        buttons.append([InlineKeyboardButton(violation, callback_data=f"viol_{i}")])
    buttons.append([InlineKeyboardButton("« رجوع", callback_data="back_menu")])
    
    query.edit_message_text(
        "⚠️ اختر نوع المخالفة:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

def select_violation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تحديد نوع المخالفة"""
    query = update.callback_query
    query.answer()
    user_id = str(update.effective_user.id)
    
    violations = [
        "محتوى للبالغين",
        "محتوى عنيف",
        "انتحال شخصية",
        "حساب مزيف",
        "تعليقات مسيئة",
        "محتوى محظور",
        "رقم للاتصال غير مصرح",
        "عروض وهمية",
        "بيع غير قانوني"
    ]
    
    viol_index = int(query.data.split('_')[1])
    selected_violation = violations[viol_index]
    
    user_data[user_id]["violation_type"] = selected_violation
    save_data()
    
    query.edit_message_text(
        f"✅ تم تحديد المخالفة: {selected_violation}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« رجوع", callback_data="back_menu")]])
    )

# ==================== التأخير ====================
def delay_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """قائمة التأخير"""
    query = update.callback_query
    query.answer()
    
    delays = [0.5, 1, 2, 3, 5, 7, 10]
    
    buttons = []
    for delay in delays:
        buttons.append([InlineKeyboardButton(f"⏱️ {delay} ثانية", callback_data=f"delay_{delay}")])
    buttons.append([InlineKeyboardButton("« رجوع", callback_data="back_menu")])
    
    query.edit_message_text(
        "⏱️ اختر التأخير بين كل بلاغ:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

def set_delay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تعيين التأخير"""
    query = update.callback_query
    query.answer()
    user_id = str(update.effective_user.id)
    
    delay = float(query.data.split('_')[1])
    user_data[user_id]["delay"] = delay
    save_data()
    
    query.edit_message_text(
        f"✅ تم تعيين التأخير: {delay} ثانية",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« رجوع", callback_data="back_menu")]])
    )

# ==================== عدد الابلاغات ====================
def report_count_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء إدخال عدد الابلاغات"""
    query = update.callback_query
    query.answer()
    
    query.edit_message_text(
        "📊 أدخل عدد الابلاغات لكل قناة (1-1000):",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« رجوع", callback_data="back_menu")]])
    )

def set_report_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تعيين عدد الابلاغات"""
    user_id = str(update.effective_user.id)
    
    try:
        count = int(update.message.text)
        if 1 <= count <= 1000:
            user_data[user_id]["report_count"] = count
            save_data()
            
            update.message.reply_text(
                f"✅ تم تعيين عدد الابلاغات: {count} لكل قناة",
                reply_markup=get_main_menu()
            )
        else:
            update.message.reply_text("❌ الرجاء إدخال رقم بين 1 و 1000")
    except ValueError:
        update.message.reply_text("❌ الرجاء إدخال رقم صحيح")

# ==================== روابط المنشور ====================
def add_links_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء إضافة روابط القنوات"""
    query = update.callback_query
    query.answer()
    
    query.edit_message_text(
        "🔗 أدخل روابط القنوات المستهدفة:\n\n"
        "مثال: https://t.me/channelname\n"
        "أو: @channelname\n\n"
        "اكتب /done عندما تنتهي",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« رجوع", callback_data="back_menu")]])
    )

def get_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استقبال روابط القنوات"""
    user_id = str(update.effective_user.id)
    text = update.message.text
    
    if text == "/done":
        if not user_data[user_id]["links"]:
            update.message.reply_text("❌ يجب إضافة رابط واحد على الأقل!")
            return REPORT_LINKS
        
        update.message.reply_text(
            f"✅ تم حفظ {len(user_data[user_id]['links'])} قناة",
            reply_markup=get_main_menu()
        )
        return ConversationHandler.END
    
    # التحقق من صحة الرابط
    if 't.me' not in text and not text.startswith('@'):
        update.message.reply_text(
            "❌ رابط غير صحيح!\n"
            "استخدم: https://t.me/channelname أو @channelname"
        )
        return REPORT_LINKS
    
    user_data[user_id]["links"].append(text)
    save_data()
    
    update.message.reply_text(
        f"✅ تم إضافة القناة #{len(user_data[user_id]['links'])}\n"
        f"القناة: {text}\n\n"
        "أدخل قناة أخرى أو اكتب /done"
    )
    
    return REPORT_LINKS

# ==================== حذف الروابط ====================
def delete_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حذف الروابط"""
    query = update.callback_query
    query.answer()
    user_id = str(update.effective_user.id)
    
    user_data[user_id]["links"] = []
    save_data()
    
    query.edit_message_text(
        "🗑️ تم حذف جميع القنوات",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« رجوع", callback_data="back_menu")]])
    )

# ==================== حساباتي ====================
def my_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض حساباتي"""
    query = update.callback_query
    query.answer()
    user_id = str(update.effective_user.id)
    
    accounts = user_data[user_id]["accounts"]
    
    if not accounts:
        query.edit_message_text(
            "❌ لا توجد حسابات مسجلة!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« رجوع", callback_data="back_menu")]])
        )
        return
    
    text = "👤 حساباتي:\n\n"
    for i, account in enumerate(accounts, 1):
        text += f"{i}. البريد: {account['email']}\n"
        text += f"   تاريخ الإضافة: {account['added_at']}\n\n"
    
    query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« رجوع", callback_data="back_menu")]])
    )

# ==================== الإحصائيات ====================
def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض الإحصائيات"""
    query = update.callback_query
    query.answer()
    user_id = str(update.effective_user.id)
    
    data = user_data[user_id]
    
    # حساب إجمالي الابلاغات المتوقعة
    total_expected = len(data['links']) * data['report_count']
    
    stats_text = f"""
📊 الإحصائيات:

👤 عدد الحسابات: {len(data['accounts'])}
📢 عدد القنوات: {len(data['links'])}
📤 الابلاغات المرسلة: {data['reports_sent']}
📊 الابلاغات المتوقعة: {total_expected}
⏱️ التأخير: {data['delay']} ثانية
📋 الابلاغات لكل قناة: {data['report_count']}
⚠️ نوع المخالفة: {data['violation_type'] or 'لم يتم تحديده'}
🚀 الحالة: {'🔴 جاري' if data['is_running'] else '⚪ متوقف'}
📅 تاريخ الإنشاء: {data['created_at']}
    """
    
    query.edit_message_text(
        stats_text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« رجوع", callback_data="back_menu")]])
    )

# ==================== بدء الابلاغات ====================
def send_reports_thread(user_id, bot):
    """تشغيل الابلاغات في Thread منفصل على تيليجرام"""
    try:
        data = user_data[user_id]
        
        # التحقق من المتطلبات
        if not data["links"]:
            bot.send_message(chat_id=user_id, text="❌ لا توجد قنوات مستهدفة!")
            return
        
        if not data["violation_type"]:
            bot.send_message(chat_id=user_id, text="❌ لم يتم تحديد نوع المخالفة!")
            return
        
        if not data["template"]:
            bot.send_message(chat_id=user_id, text="❌ لم يتم تحديد الكليشه!")
            return
        
        data["is_running"] = True
        data["reports_sent"] = 0
        save_data()
        
        total_reports_per_channel = data["report_count"]
        delay = data["delay"]
        channels = data["links"]
        
        total_expected = len(channels) * total_reports_per_channel
        
        bot.send_message(
            chat_id=user_id,
            text=f"""
🚀 بدء الابلاغات...

📊 الإعدادات:
- عدد القنوات: {len(channels)}
- الابلاغات لكل قناة: {total_reports_per_channel}
- إجمالي الابلاغات: {total_expected}
- التأخير: {delay} ثانية

🎯 القنوات المستهدفة:
            """
        )
        
        # عرض القنوات
        for i, channel in enumerate(channels, 1):
            bot.send_message(chat_id=user_id, text=f"{i}. {channel}")
        
        bot.send_message(chat_id=user_id, text="⏳ جاري الإرسال...")
        
        # إرسال الابلاغات على كل قناة
        for channel_idx, channel in enumerate(channels, 1):
            bot.send_message(
                chat_id=user_id,
                text=f"\n📢 بدء الابلاغات على القناة #{channel_idx}: {channel}"
            )
            
            for i in range(total_reports_per_channel):
                if not data["is_running"]:
                    break
                
                try:
                    # بناء رسالة البلاغ
                    report_message = f"""
🚨 **بلاغ جديد**

📌 القناة المستهدفة: {channel}
⚠️ نوع المخالفة: {data['violation_type']}
💬 الوصف: {data['template']}
🔢 رقم البلاغ: {data['reports_sent'] + 1}/{total_expected}
⏰ الوقت: {datetime.now().strftime('%H:%M:%S')}
📅 التاريخ: {datetime.now().strftime('%Y-%m-%d')}
                    """
                    
                    # إرسال البلاغ على القناة المستهدفة
                    bot.send_message(
                        chat_id=channel,
                        text=report_message,
                        parse_mode='Markdown'
                    )
                    
                    data["reports_sent"] += 1
                    save_data()
                    
                    # إرسال تحديث للمستخدم كل 5 ابلاغات
                    if data["reports_sent"] % 5 == 0:
                        bot.send_message(
                            chat_id=user_id,
                            text=f"✅ تم إرسال {data['reports_sent']} من {total_expected} بلاغ"
                        )
                    
                    print(f"✅ تم إرسال البلاغ #{data['reports_sent']}")
                    
                except Exception as e:
                    print(f"❌ خطأ في إرسال البلاغ على {channel}: {e}")
                    # محاولة الاستمرار على القناة التالية
                    continue
                
                # التأخير بين الابلاغات
                time.sleep(delay)
            
            if not data["is_running"]:
                break
        
        data["is_running"] = False
        save_data()
        
        # رسالة الانتهاء
        bot.send_message(
            chat_id=user_id,
            text=f"""
✅ انتهت الابلاغات!

📊 النتائج:
✔️ الابلاغات المرسلة: {data['reports_sent']}
📊 الإجمالي المطلوب: {total_expected}
📢 عدد القنوات: {len(channels)}
✅ الحالة: {'مكتملة' if data['reports_sent'] == total_expected else 'متوقفة'}
            """,
            reply_markup=get_main_menu()
        )
        
    except Exception as e:
        print(f"❌ خطأ في Thread الابلاغات: {e}")
        try:
            bot.send_message(chat_id=user_id, text=f"❌ خطأ: {str(e)}")
        except:
            pass

def start_reports(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء الابلاغات"""
    query = update.callback_query
    query.answer()
    user_id = str(update.effective_user.id)
    
    if user_data[user_id]["is_running"]:
        query.edit_message_text(
            "⚠️ الابلاغات جاري تنفيذها بالفعل!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« رجوع", callback_data="back_menu")]])
        )
        return
    
    # بدء الابلاغات في Thread منفصل
    thread = threading.Thread(
        target=send_reports_thread,
        args=(user_id, context.bot)
    )
    thread.daemon = True
    thread.start()
    reporting_threads[user_id] = thread
    
    query.edit_message_text(
        "🚀 تم بدء الابلاغات...",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« رجوع", callback_data="back_menu")]])
    )

# ==================== إيقاف ====================
def stop_reports(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إيقاف الابلاغات"""
    query = update.callback_query
    query.answer()
    user_id = str(update.effective_user.id)
    
    user_data[user_id]["is_running"] = False
    save_data()
    
    query.edit_message_text(
        f"⏹️ تم إيقاف الابلاغات\n\nالابلاغات المرسلة: {user_data[user_id]['reports_sent']}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« رجوع", callback_data="back_menu")]])
    )

# ==================== رجوع ====================
def back_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """العودة للقائمة الرئيسية"""
    query = update.callback_query
    query.answer()
    
    query.edit_message_text(
        "🤖 لوحة التحكم الرئيسية:",
        reply_markup=get_main_menu()
    )

# ==================== معالج Callback ====================
def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج جميع أزرار Callback"""
    query = update.callback_query
    data = query.data
    
    if data == "back_menu":
        back_menu(update, context)
    elif data == "add_account":
        add_account_start(update, context)
        return PHONE_EMAIL
    elif data == "delete_account":
        delete_account(update, context)
    elif data.startswith("delete_acc_"):
        confirm_delete_account(update, context)
    elif data == "template":
        template_start(update, context)
    elif data == "violation_type":
        violation_type(update, context)
    elif data.startswith("viol_"):
        select_violation(update, context)
    elif data == "delay":
        delay_menu(update, context)
    elif data.startswith("delay_"):
        set_delay(update, context)
    elif data == "report_count":
        report_count_start(update, context)
    elif data == "add_links":
        add_links_start(update, context)
        return REPORT_LINKS
    elif data == "delete_links":
        delete_links(update, context)
    elif data == "my_accounts":
        my_accounts(update, context)
    elif data == "stats":
        show_stats(update, context)
    elif data == "start_reports":
        start_reports(update, context)
    elif data == "stop":
        stop_reports(update, context)

# ==================== Main ====================
def main():
    """تشغيل البوت"""
    load_data()
    
    updater = Updater(token=BOT_TOKEN)
    dispatcher = updater.dispatcher
    
    # معالج المحادثة لإضافة حساب
    add_account_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_account_start, pattern="^add_account$")],
        states={
            PHONE_EMAIL: [MessageHandler(Filters.text & ~Filters.command, get_phone_email)],
            PASSWORD: [MessageHandler(Filters.text & ~Filters.command, get_password)],
        },
        fallbacks=[CallbackQueryHandler(back_menu, pattern="^back_menu$")],
        allow_reentry=True
    )
    
    # معالج المحادثة لإضافة الكليشه
    template_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(template_start, pattern="^template$")],
        states={
            0: [MessageHandler(Filters.text & ~Filters.command, get_template)],
        },
        fallbacks=[CallbackQueryHandler(back_menu, pattern="^back_menu$")],
        allow_reentry=True
    )
    
    # معالج المحادثة لإضافة الروابط
    links_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_links_start, pattern="^add_links$")],
        states={
            REPORT_LINKS: [MessageHandler(Filters.text, get_links)],
        },
        fallbacks=[CallbackQueryHandler(back_menu, pattern="^back_menu$")],
        allow_reentry=True
    )
    
    # معالج المحادثة لعدد الابلاغات
    count_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(report_count_start, pattern="^report_count$")],
        states={
            0: [MessageHandler(Filters.text & ~Filters.command, set_report_count)],
        },
        fallbacks=[CallbackQueryHandler(back_menu, pattern="^back_menu$")],
        allow_reentry=True
    )
    
    # إضافة المعالجات
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(add_account_conv)
    dispatcher.add_handler(template_conv)
    dispatcher.add_handler(links_conv)
    dispatcher.add_handler(count_conv)
    dispatcher.add_handler(CallbackQueryHandler(callback_handler))
    
    # بدء البوت
    print("✅ البوت يعمل الآن...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()