"""
This module contains the main functionality of a Telegram bot.
It includes functions for adding admins,
listing admins, setting special limits, and creating a config and more...
"""

# =========================
# Imports
# =========================
import asyncio
import os
import sys

try:
    from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
    from telegram.ext import (
        ApplicationBuilder,
        CommandHandler,
        ContextTypes,
        ConversationHandler,
        MessageHandler,
        filters,
    )
except ImportError:
    print(
        "Module 'python-telegram-bot' is not installed. Use:"
        + " 'pip install python-telegram-bot' to install it"
    )
    sys.exit()

# توجه: این import ها باید مطابق ساختار پروژه‌ی اصلی شما باشد.
from telegram_bot.utils import (
    add_admin_to_config,
    add_base_information,
    add_except_user,
    check_admin,
    get_special_limit_list,
    handel_special_limit,
    read_json_file,
    remove_admin_from_config,
    remove_except_user_from_config,
    save_check_interval,
    save_general_limit,
    save_time_to_active_users,
    show_except_users_handler,
    write_country_code_json,
)
from utils.read_config import read_config


# =========================
# Conversation States
# =========================
(
    GET_DOMAIN,
    GET_PORT,  # reserved (not used explicitly here, kept for compatibility)
    GET_USERNAME,
    GET_PASSWORD,
    GET_CONFIRMATION,
    GET_CHAT_ID,
    GET_SPECIAL_LIMIT,
    GET_LIMIT_NUMBER,
    GET_CHAT_ID_TO_REMOVE,
    SET_COUNTRY_CODE,
    SET_EXCEPT_USERS,
    REMOVE_EXCEPT_USER,
    GET_GENERAL_LIMIT_NUMBER,
    GET_CHECK_INTERVAL,
    GET_TIME_TO_ACTIVE_USERS,
) = range(15)


# =========================
# Load Config & Build Application
# =========================
# ایمن‌سازی خواندن کانفیگ در زمان import (سازگار با محیط‌هایی که هنوز loop ندارند)
try:
    _loop = asyncio.get_event_loop()
except RuntimeError:
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)

data = _loop.run_until_complete(read_config())
try:
    bot_token = data["BOT_TOKEN"]
except KeyError as exc:
    raise ValueError("BOT_TOKEN is missing in the config file.") from exc

application = ApplicationBuilder().token(bot_token).build()


# =========================
# Keyboards
# =========================
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🛡️ سپرنت")],  # ردیف تک‌دکمه‌ایِ پهن در بالا
        [KeyboardButton("⚙️ تنظیمات پنل"), KeyboardButton("🎯 محدودیت ویژه")],
        [KeyboardButton("👥 مدیریت ادمین"), KeyboardButton("🌍 تنظیمات کشور")],
        [KeyboardButton("📋 مدیریت استثناها"), KeyboardButton("📊 تنظیمات عمومی")],
        [KeyboardButton("💾 پشتیبان گیری"), KeyboardButton("📖 راهنما")],
    ],
    resize_keyboard=True,
    one_time_keyboard=False,
)

ADMIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("➕ افزودن ادمین"), KeyboardButton("👥 لیست ادمین‌ها")],
        [KeyboardButton("❌ حذف ادمین"), KeyboardButton("🔙 بازگشت")],
    ],
    resize_keyboard=True,
    one_time_keyboard=False,
)

EXCEPTION_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("✅ افزودن به استثنا"), KeyboardButton("📋 لیست استثناها")],
        [KeyboardButton("🚫 حذف از استثنا"), KeyboardButton("🔙 بازگشت")],
    ],
    resize_keyboard=True,
    one_time_keyboard=False,
)

SETTINGS_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("📈 محدودیت عمومی"), KeyboardButton("⏱️ فاصله بررسی")],
        [KeyboardButton("🕐 زمان فعالیت"), KeyboardButton("🔙 بازگشت")],
    ],
    resize_keyboard=True,
    one_time_keyboard=False,
)

CONFIRM_KEYBOARD = ReplyKeyboardMarkup(
    [[KeyboardButton("✅ بله"), KeyboardButton("❌ خیر")]],
    resize_keyboard=True,
    one_time_keyboard=True,
)


# =========================
# Static Messages
# =========================
START_MESSAGE = """
🌟 <b>به ربات مدیریت پنل خوش آمدید!</b> 🌟
🛡️ <b>سپرنت</b> — نسخه 1.0

<b>شروع کار با ربات</b>
🚀 /start

<b>تنظیمات پنل (نام کاربری، رمز عبور، ...)</b>
⚙️ /create_config

<b>تنظیم محدودیت ویژه برای کاربر خاص</b>
🎯 /set_special_limit
مثال: test_user حداکثر 5 IP

<b>نمایش لیست محدودیت‌های ویژه</b>
📊 /show_special_limit

<b>افزودن ادمین جدید برای ربات</b>
👤 /add_admin

<b>نمایش لیست ادمین‌های فعال</b>
👥 /admins_list

<b>حذف دسترسی ادمین از ربات</b>
❌ /remove_admin

<b>تنظیم کشور - فقط IP های همان کشور محاسبه می‌شود</b>
🌍 /country_code

<b>افزودن کاربر به لیست استثنا (بدون محدودیت)</b>
✅ /set_except_user

<b>حذف کاربر از لیست استثنا</b>
🚫 /remove_except_user

<b>نمایش لیست کاربران استثنا</b>
📋 /show_except_users

<b>تنظیم محدودیت عمومی (برای کاربران بدون محدودیت ویژه)</b>
📈 /set_general_limit_number

<b>تنظیم فاصله زمانی بررسی</b>
⏱️ /set_check_interval

<b>تنظیم زمان فعال بودن کاربران</b>
🕐 /set_time_to_active_users

<b>ارسال فایل 'config.json' به عنوان پشتیبان</b>
💾 /backup

━━━━━━━━━━━━━━━━━━━━━━━━
"""


# =========================
# Utilities
# =========================
async def send_logs(msg: str):
    """Send logs to all admins."""
    admins = await check_admin()
    for admin in admins:
        try:
            await application.bot.sendMessage(
                chat_id=admin, text=msg, parse_mode="HTML"
            )
        except Exception as error:  # pylint: disable=broad-except
            print(f"Failed to send message to admin {admin}: {error}")


async def check_admin_privilege(update: Update):
    """
    Checks if the user has admin privileges.
    - اگر هنوز ادمینی ثبت نشده باشد، اولین استارت‌کننده به عنوان ادمین اضافه می‌شود.
    - در صورت نداشتن دسترسی، پیام مناسب ارسال و کانورسیشن پایان می‌یابد.
    """
    admins = await check_admin()
    if not admins:
        await add_admin_to_config(update.effective_chat.id)
    admins = await check_admin()
    if update.effective_chat.id not in admins:
        await update.message.reply_html(
            text=(
                "🚫 <b>عدم دسترسی!</b>\n\n"
                "متأسفانه شما مجوز اجرای این دستور را ندارید.\n"
                "لطفاً با ادمین اصلی تماس بگیرید."
            ),
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END


# =========================
# Command Handlers
# =========================
async def start(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Start function for the bot."""
    check = await check_admin_privilege(update)
    if check:
        return check
    await update.message.reply_html(text=START_MESSAGE, reply_markup=MAIN_KEYBOARD)


async def spernet_info(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """نمایش کارت برند سپرنت (مینیمال و تمیز)."""
    await update.message.reply_html(
        text=(
            "🛡️ <b>سپرنت</b>\n"
            "راهکار مدیریت و پایش هوشمند کاربران.\n"
            "— نسخه‌ی ربات: <b>1.0</b>\n\n"
            "برای شروع: /start\n"
            "تنظیمات سریع: /create_config\n"
            "پشتیبان‌گیری: /backup\n"
        ),
        reply_markup=MAIN_KEYBOARD,
    )


async def create_config(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """
    Add panel domain, username, and password to add into the config file.
    """
    check = await check_admin_privilege(update)
    if check:
        return check

    if os.path.exists("config.json"):
        json_data = await read_json_file()
        domain = json_data.get("PANEL_DOMAIN")
        username = json_data.get("PANEL_USERNAME")
        password = json_data.get("PANEL_PASSWORD")
        if domain and username and password:
            masked = "*" * len(password) if password else ""
            await update.message.reply_html(
                text="⚙️ <b>تنظیمات موجود!</b>\n\nشما قبلاً تنظیمات پنل را انجام داده‌اید!"
            )
            await update.message.reply_html(
                text=(
                    "⚠️ <b>نکته مهم:</b>\n\n"
                    "پس از تغییر تنظیمات، نیاز به <b>راه‌اندازی مجدد</b> ربات دارید.\n"
                    "فقط این دستور نیاز به راه‌اندازی مجدد دارد، <b>سایر دستورات نیازی ندارند.</b>"
                )
            )
            await update.message.reply_html(
                text=(
                    "📋 <b>تنظیمات فعلی:</b>\n\n"
                    f"🌐 دامنه: <code>{domain}</code>\n"
                    f"👤 نام کاربری: <code>{username}</code>\n"
                    f"🔐 رمز عبور: <code>{masked}</code>\n\n"
                    "❓ آیا می‌خواهید این تنظیمات را تغییر دهید؟"
                ),
                reply_markup=CONFIRM_KEYBOARD,
            )
            return GET_CONFIRMATION

    await update.message.reply_html(
        text=(
            "⚙️ <b>تنظیم پنل مدیریت</b>\n\n"
            "🌐 <b>آدرس پنل خود را ارسال کنید!</b>\n\n"
            "📝 آدرس دامنه یا IP همراه با پورت ارسال کنید:\n"
            "مثال: <code>sub.domain.com:8333</code> یا <code>95.12.153.87:443</code>\n\n"
            "⚠️ <b>بدون</b> <code>https://</code> یا <code>http://</code> یا چیز دیگری"
        ),
        reply_markup=ReplyKeyboardRemove(),
    )
    return GET_DOMAIN


async def get_confirmation(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Get confirmation for changing panel information.
    پشتیبانی از yes/y/بله و همچنین دکمه‌های ✅ بله / ❌ خیر
    """
    if update.message.text.lower() in ["yes", "y", "بله"]:
        await update.message.reply_html(
            text=(
                "⚙️ <b>تنظیم مجدد پنل</b>\n\n"
                "🌐 <b>آدرس پنل جدید را ارسال کنید!</b>\n\n"
                "📝 آدرس دامنه یا IP همراه با پورت ارسال کنید:\n"
                "مثال: <code>sub.domain.com:8333</code> یا <code>95.12.153.87:443</code>\n\n"
                "⚠️ <b>بدون</b> <code>https://</code> یا <code>http://</code> یا چیز دیگری"
            ),
            reply_markup=ReplyKeyboardRemove(),
        )
        return GET_DOMAIN

    await update.message.reply_html(
        text=(
            "✅ <b>عملیات لغو شد.</b>\n\n"
            "زمانی که تصمیم به تغییر گرفتید، از دستور <b>/create_config</b> استفاده کنید."
        ),
        reply_markup=MAIN_KEYBOARD,
    )
    return ConversationHandler.END


async def get_domain(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get panel domain from user."""
    context.user_data["domain"] = update.message.text.strip()
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="👤 <b>نام کاربری پنل</b>\n\nلطفاً نام کاربری خود را ارسال کنید:\nمثال: <code>admin</code>",
        parse_mode="HTML",
    )
    return GET_USERNAME


async def get_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get panel username from user."""
    context.user_data["username"] = update.message.text.strip()
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="🔐 <b>رمز عبور پنل</b>\n\nلطفاً رمز عبور خود را ارسال کنید:\nمثال: <code>admin1234</code>",
        parse_mode="HTML",
    )
    return GET_PASSWORD


async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get panel password from user and save base information."""
    context.user_data["password"] = update.message.text.strip()
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="⏳ <b>در حال بررسی...</b>\n\nلطفاً صبر کنید تا آدرس پنل، نام کاربری و رمز عبور بررسی شود...",
        parse_mode="HTML",
    )
    try:
        await add_base_information(
            context.user_data["domain"],
            context.user_data["password"],
            context.user_data["username"],
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                "🎊 <b>تبریک!</b>\n\n"
                "✅ تنظیمات با موفقیت ذخیره شد!\n\n"
                "اکنون می‌توانید از تمام امکانات ربات استفاده کنید. 🚀"
            ),
            parse_mode="HTML",
            reply_markup=MAIN_KEYBOARD,
        )
    except ValueError:
        await update.message.reply_html(
            text=(
                "❌ <b>خطا در اتصال!</b>\n\n"
                "⚠️ مشکلی در اطلاعات وارد شده وجود دارد. لطفاً دوباره بررسی کنید!\n"
                "(همچنین مطمئن شوید که پنل در حال اجرا است)\n\n"
                "📋 <b>اطلاعات وارد شده:</b>\n"
                f"🌐 آدرس پنل: <code>{context.user_data['domain']}</code>\n"
                f"👤 نام کاربری: <code>{context.user_data['username']}</code>\n"
                "🔄 دوباره تلاش کنید: /create_config"
            ),
            reply_markup=MAIN_KEYBOARD,
        )

    return ConversationHandler.END


async def add_admin(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """
    Adds an admin to the bot.
    """
    check = await check_admin_privilege(update)
    if check:
        return check

    if len(await check_admin()) > 5:
        await update.message.reply_html(
            text=(
                "⚠️ <b>محدودیت تعداد ادمین!</b>\n\n"
                "شما بیش از '5' ادمین تعریف کرده‌اید. برای افزودن ادمین جدید، ابتدا یکی از ادمین‌های فعلی را حذف کنید.\n\n"
                "📋 لیست ادمین‌های فعال: /admins_list\n"
                "❌ حذف ادمین: /remove_admin"
            ),
            reply_markup=MAIN_KEYBOARD,
        )
        return ConversationHandler.END

    await update.message.reply_html(
        text="👤 <b>افزودن ادمین جدید</b>\n\n📱 لطفاً Chat ID ادمین جدید را ارسال کنید:",
        reply_markup=ReplyKeyboardRemove(),
    )
    return GET_CHAT_ID


async def get_chat_id(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """
    Adds a new admin if the provided chat ID is valid and not already an admin.
    """
    new_admin_id = update.message.text.strip()
    try:
        if await add_admin_to_config(new_admin_id):
            await update.message.reply_html(
                text=f"✅ <b>موفقیت‌آمیز!</b>\n\nادمین <code>{new_admin_id}</code> با موفقیت اضافه شد! 🎉",
                reply_markup=MAIN_KEYBOARD,
            )
        else:
            await update.message.reply_html(
                text=f"⚠️ <b>ادمین تکراری!</b>\n\nادمین <code>{new_admin_id}</code> از قبل وجود دارد!",
                reply_markup=MAIN_KEYBOARD,
            )
    except ValueError:
        await update.message.reply_html(
            text=(
                "❌ <b>ورودی نامعتبر!</b>\n\n"
                f"مقدار وارد شده: <code>{update.message.text.strip()}</code>\n"
                "لطفاً دوباره تلاش کنید: <b>/add_admin</b>"
            ),
            reply_markup=MAIN_KEYBOARD,
        )
    return ConversationHandler.END


async def admins_list(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """
    Sends a list of current admins.
    """
    check = await check_admin_privilege(update)
    if check:
        return check

    admins = await check_admin()
    if admins:
        admins_str = "\n📌 ".join(map(str, admins))
        await update.message.reply_html(
            text=f"👥 <b>لیست ادمین‌های فعال:</b>\n\n📌 {admins_str}\n\n🔢 تعداد کل: {len(admins)} ادمین",
            reply_markup=MAIN_KEYBOARD,
        )
    else:
        await update.message.reply_html(
            text="❌ <b>هیچ ادمینی یافت نشد!</b>",
            reply_markup=MAIN_KEYBOARD,
        )
    return ConversationHandler.END


async def remove_admin(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Removes an admin from admin list."""
    check = await check_admin_privilege(update)
    if check:
        return check

    admins_count = len(await check_admin())
    # جلوگیری قطعی از حذف آخرین ادمین
    if admins_count <= 1:
        await update.message.reply_html(
            text=(
                "⚠️ <b>هشدار!</b>\n\n"
                "فقط <b>1</b> ادمین فعال باقی مانده است. "
                "برای حذف، ابتدا یک ادمین جدید اضافه کنید."
            ),
            reply_markup=MAIN_KEYBOARD,
        )
        return ConversationHandler.END

    await update.message.reply_html(
        text="❌ <b>حذف ادمین</b>\n\n📱 Chat ID ادمینی که می‌خواهید حذف کنید را ارسال کنید:",
        reply_markup=ReplyKeyboardRemove(),
    )
    return GET_CHAT_ID_TO_REMOVE


async def get_chat_id_to_remove(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Get admin chat id to delete it from admin list."""
    try:
        admin_id_to_remove = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_html(
            text=(
                "❌ <b>ورودی نامعتبر!</b>\n\n"
                f"مقدار وارد شده: <code>{update.message.text.strip()}</code>\n"
                "لطفاً دوباره تلاش کنید: <b>/remove_admin</b>"
            ),
            reply_markup=MAIN_KEYBOARD,
        )
        return ConversationHandler.END

    if await remove_admin_from_config(admin_id_to_remove):
        await update.message.reply_html(
            text=f"✅ <b>حذف موفق!</b>\n\nادمین <code>{admin_id_to_remove}</code> با موفقیت حذف شد! 🗑️",
            reply_markup=MAIN_KEYBOARD,
        )
    else:
        await update.message.reply_html(
            text=f"❌ <b>ادمین یافت نشد!</b>\n\nادمین <code>{admin_id_to_remove}</code> وجود ندارد!",
            reply_markup=MAIN_KEYBOARD,
        )
    return ConversationHandler.END


async def set_special_limit(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """
    Set a special limit for a user.
    """
    check = await check_admin_privilege(update)
    if check:
        return check

    await update.message.reply_html(
        text=(
            "🎯 <b>تنظیم محدودیت ویژه</b>\n\n"
            "👤 لطفاً نام کاربری را وارد کنید.\nمثال: <code>Test_User</code>"
        ),
        reply_markup=ReplyKeyboardRemove(),
    )
    return GET_SPECIAL_LIMIT


async def get_special_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Get the number of limit for a user.
    """
    context.user_data["selected_user"] = update.message.text.strip()
    await update.message.reply_html(
        text=(
            "🔢 <b>تعداد محدودیت</b>\n\n"
            "لطفاً تعداد IP مجاز برای این کاربر را وارد کنید.\nمثال: <code>4</code> یا <code>2</code>"
        )
    )
    return GET_LIMIT_NUMBER


async def get_limit_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Sets the special limit for a user if the provided input is a valid number.
    """
    try:
        context.user_data["limit_number"] = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_html(
            text=(
                "❌ <b>ورودی نامعتبر!</b>\n\n"
                f"مقدار وارد شده: <code>{update.message.text.strip()}</code>\n"
                "لطفاً دوباره تلاش کنید: <b>/set_special_limit</b>"
            ),
            reply_markup=MAIN_KEYBOARD,
        )
        return ConversationHandler.END

    out_put = await handel_special_limit(
        context.user_data["selected_user"], context.user_data["limit_number"]
    )
    if out_put[0]:
        await update.message.reply_html(
            text=(
                f"⚠️ <b>بروزرسانی محدودیت</b>\n\n"
                f"کاربر <code>{context.user_data['selected_user']}</code> قبلاً محدودیت ویژه داشت.\n"
                "محدودیت با مقدار جدید بروزرسانی شد! ✅"
            )
        )

    await update.message.reply_html(
        text=(
            "✅ <b>تنظیم محدودیت موفق!</b>\n\n"
            f"👤 کاربر: <code>{context.user_data['selected_user']}</code>\n"
            f"🔢 محدودیت: <code>{out_put[1]}</code> IP\n\n"
            "محدودیت با موفقیت تنظیم شد! 🎉"
        ),
        reply_markup=MAIN_KEYBOARD,
    )
    return ConversationHandler.END


async def show_special_limit_function(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Show special limit list for all users."""
    check = await check_admin_privilege(update)
    if check:
        return check

    out_put = await get_special_limit_list()
    if out_put:
        await update.message.reply_html(
            text="📊 <b>لیست محدودیت‌های ویژه:</b>\n", reply_markup=MAIN_KEYBOARD
        )
        for user in out_put:
            await update.message.reply_html(text=f"🎯 {user}")
    else:
        await update.message.reply_html(
            text=(
                "❌ <b>هیچ محدودیت ویژه‌ای یافت نشد!</b>\n\n"
                "برای تنظیم محدودیت ویژه از دستور /set_special_limit استفاده کنید."
            ),
            reply_markup=MAIN_KEYBOARD,
        )


async def set_country_code(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Set the country code for the bot."""
    check = await check_admin_privilege(update)
    if check:
        return check

    await update.message.reply_html(
        text=(
            "🌍 <b>انتخاب کشور</b>\n\n"
            "لطفاً شماره کشور مورد نظر خود را انتخاب کنید:\n\n"
            "1️⃣ <code>IR</code> (ایران) 🇮🇷\n"
            "2️⃣ <code>RU</code> (روسیه) 🇷🇺\n"
            "3️⃣ <code>CN</code> (چین) 🇨🇳\n"
            "4️⃣ <code>None</code> - بررسی مکان انجام نشود 🌐\n\n"
            "📝 <b>فقط عدد مربوط به کشور را ارسال کنید:</b>\nمثال: <code>2</code> یا <code>1</code>"
        ),
        reply_markup=ReplyKeyboardRemove(),
    )
    return SET_COUNTRY_CODE


async def write_country_code(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Write the country code to the config file."""
    country_code = update.message.text.strip()
    country_codes = {"1": "IR 🇮🇷", "2": "RU 🇷🇺", "3": "CN 🇨🇳", "4": "None 🌐"}
    country_codes_save = {"1": "IR", "2": "RU", "3": "CN", "4": "None"}

    selected_country = country_codes.get(country_code, "None 🌐")
    selected_country_save = country_codes_save.get(country_code, "None")

    await write_country_code_json(selected_country_save)
    await update.message.reply_html(
        text=f"✅ <b>تنظیم کشور موفق!</b>\n\n🌍 کد کشور <code>{selected_country}</code> با موفقیت تنظیم شد!",
        reply_markup=MAIN_KEYBOARD,
    )
    return ConversationHandler.END


async def send_backup(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Send the backup file to the user."""
    check = await check_admin_privilege(update)
    if check:
        return check

    try:
        await update.message.reply_document(
            document=open("config.json", "rb"),  # pylint: disable=consider-using-with
            caption=(
                "💾 <b>فایل پشتیبان</b>\n\n"
                "✅ این فایل حاوی تمام تنظیمات ربات شماست!\n"
                "🔒 لطفاً آن را در مکان امنی نگهداری کنید."
            ),
            reply_markup=MAIN_KEYBOARD,
            parse_mode="HTML",
        )
    except FileNotFoundError:
        await update.message.reply_html(
            text="❌ <b>فایل config.json یافت نشد!</b>\n\nابتدا تنظیمات را با /create_config تکمیل کنید.",
            reply_markup=MAIN_KEYBOARD,
        )


async def set_except_users(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Set the except users for the bot."""
    check = await check_admin_privilege(update)
    if check:
        return check

    await update.message.reply_html(
        text=(
            "✅ <ب>افزودن کاربر استثنا</ب>\n\n"
            "👤 نام کاربری که می‌خواهید به لیست استثنا اضافه کنید را ارسال کنید:\n\n"
            "💡 <b>نکته:</b> کاربران موجود در این لیست هیچ محدودیتی نخواهند داشت."
        ).replace("<ب>", "<b>").replace("</ب>", "</b>"),
        reply_markup=ReplyKeyboardRemove(),
    )
    return SET_EXCEPT_USERS


async def set_except_users_handler(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Write the except users to the config file."""
    except_user = update.message.text.strip()
    await add_except_user(except_user)
    await update.message.reply_html(
        text=f"✅ <b>افزودن موفق!</b>\n\nکاربر <code>{except_user}</code> با موفقیت به لیست استثنا اضافه شد! 🎉",
        reply_markup=MAIN_KEYBOARD,
    )
    return ConversationHandler.END


async def remove_except_user(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Remove the except users for the bot."""
    check = await check_admin_privilege(update)
    if check:
        return check

    await update.message.reply_html(
        text=(
            "🚫 <b>حذف کاربر از استثنا</b>\n\n"
            "👤 نام کاربری که می‌خواهید از لیست استثنا حذف کنید را ارسال کنید:"
        ),
        reply_markup=ReplyKeyboardRemove(),
    )
    return REMOVE_EXCEPT_USER


async def remove_except_user_handler(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Remove the except users from the config file."""
    user_input = update.message.text.strip()
    except_user = await remove_except_user_from_config(user_input)
    if except_user:
        await update.message.reply_html(
            text=(
                "✅ <b>حذف موفق!</b>\n\n"
                f"کاربر <code>{user_input}</code> با موفقیت از لیست استثنا حذف شد! 🗑️"
            ),
            reply_markup=MAIN_KEYBOARD,
        )
    else:
        await update.message.reply_html(
            text=(
                "❌ <b>کاربر یافت نشد!</b>\n\n"
                f"کاربر <code>{user_input}</code> در لیست استثنا وجود ندارد!"
            ),
            reply_markup=MAIN_KEYBOARD,
        )
    return ConversationHandler.END


async def show_except_users(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Show the except users for the bot."""
    check = await check_admin_privilege(update)
    if check:
        return check

    messages = await show_except_users_handler()
    if messages:
        await update.message.reply_html(
            text="📋 <b>لیست کاربران استثنا:</b>\n\n✅ کاربران زیر هیچ محدودیتی ندارند:",
            reply_markup=MAIN_KEYBOARD,
        )
        for message in messages:
            await update.message.reply_html(text=f"👤 {message}")
    else:
        await update.message.reply_html(
            text=(
                "❌ <b>هیچ کاربر استثنایی یافت نشد!</b>\n\n"
                "برای افزودن کاربر به لیست استثنا از دستور /set_except_user استفاده کنید."
            ),
            reply_markup=MAIN_KEYBOARD,
        )
    return ConversationHandler.END


async def get_general_limit_number(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Get the general limit number for the bot."""
    check = await check_admin_privilege(update)
    if check:
        return check

    await update.message.reply_html(
        text=(
            "📈 <b>تنظیم محدودیت عمومی</b>\n\n"
            "🔢 لطفاً تعداد محدودیت عمومی را وارد کنید:\n\n"
            "💡 <b>نکته:</b> این محدودیت برای کاربرانی که در لیست محدودیت ویژه نیستند اعمال می‌شود."
        ),
        reply_markup=ReplyKeyboardRemove(),
    )
    return GET_GENERAL_LIMIT_NUMBER


async def get_general_limit_number_handler(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Write the general limit number to the config file."""
    try:
        limit_number = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_html(
            text=(
                "❌ <b>ورودی نامعتبر!</b>\n\n"
                f"مقدار وارد شده: <code>{update.message.text.strip()}</code>\n"
                "لطفاً دوباره تلاش کنید: <b>/set_general_limit_number</b>"
            ),
            reply_markup=MAIN_KEYBOARD,
        )
        return ConversationHandler.END

    await save_general_limit(limit_number)
    await update.message.reply_html(
        text=f"✅ <b>تنظیم محدودیت عمومی موفق!</b>\n\n📈 محدودیت عمومی روی <code>{limit_number}</code> تنظیم شد! 🎉",
        reply_markup=MAIN_KEYBOARD,
    )
    return ConversationHandler.END


async def get_check_interval(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Get the 'check_interval' value that handles how often the bot checks the users."""
    check = await check_admin_privilege(update)
    if check:
        return check

    await update.message.reply_html(
        text=(
            "⏱️ <b>تنظیم فاصله بررسی</b>\n\n"
            "🕐 لطفاً فاصله زمانی بررسی را وارد کنید:\nمثال: <code>240</code>\n\n"
            "💡 <b>توصیه:</b> مقدار 240 ثانیه پیشنهاد می‌شود."
        ),
        reply_markup=ReplyKeyboardRemove(),
    )
    return GET_CHECK_INTERVAL


async def get_check_interval_handler(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Save the 'check_interval' value."""
    try:
        check_interval = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_html(
            text=(
                "❌ <b>ورودی نامعتبر!</b>\n\n"
                f"مقدار وارد شده: <code>{update.message.text.strip()}</code>\n"
                "لطفاً دوباره تلاش کنید: <b>/set_check_interval</b>"
            ),
            reply_markup=MAIN_KEYBOARD,
        )
        return ConversationHandler.END

    await save_check_interval(check_interval)
    await update.message.reply_html(
        text=f"✅ <b>تنظیم فاصله بررسی موفق!</b>\n\n⏱️ فاصله بررسی روی <code>{check_interval}</code> ثانیه تنظیم شد! 🎉",
        reply_markup=MAIN_KEYBOARD,
    )
    return ConversationHandler.END


async def get_time_to_active_users(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Get the 'time_to_active_users' value controlling active window length."""
    check = await check_admin_privilege(update)
    if check:
        return check

    await update.message.reply_html(
        text=(
            "🕐 <b>تنظیم زمان فعالیت کاربران</b>\n\n"
            "⏳ لطفاً زمان فعال بودن کاربران را وارد کنید:\nمثال: <code>600</code>\n\n"
            "💡 <b>نکته:</b> این مقدار بر حسب ثانیه است."
        ),
        reply_markup=ReplyKeyboardRemove(),
    )
    return GET_TIME_TO_ACTIVE_USERS


async def get_time_to_active_users_handler(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Save the 'time_to_active_users' value."""
    try:
        time_to_active_users = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_html(
            text=(
                "❌ <b>ورودی نامعتبر!</b>\n\n"
                f"مقدار وارد شده: <code>{update.message.text.strip()}</code>\n"
                "لطفاً دوباره تلاش کنید: <b>/set_time_to_active_users</b>"
            ),
            reply_markup=MAIN_KEYBOARD,
        )
        return ConversationHandler.END

    await save_time_to_active_users(time_to_active_users)
    await update.message.reply_html(
        text=f"✅ <b>تنظیم زمان فعالیت موفق!</b>\n\n🕐 زمان فعالیت کاربران روی <code>{time_to_active_users}</code> ثانیه تنظیم شد! 🎉",
        reply_markup=MAIN_KEYBOARD,
    )
    return ConversationHandler.END


# =========================
# UI: Handle ReplyKeyboard Clicks
# =========================
async def handle_keyboard_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت دکمه‌های کیبورد"""
    if not update.message:
        return

    text = update.message.text

    if text == "📖 راهنما":
        await start(update, context)

    elif text == "⚙️ تنظیمات پنل":
        await create_config(update, context)

    elif text == "🛡️ سپرنت":
        await spernet_info(update, context)

    elif text == "🎯 محدودیت ویژه":
        await update.message.reply_html(
            "🎯 <b>مدیریت محدودیت‌های ویژه</b>\n\n"
            "📊 /show_special_limit - نمایش محدودیت‌های فعلی\n"
            "➕ /set_special_limit - تنظیم محدودیت جدید",
            reply_markup=MAIN_KEYBOARD,
        )

    elif text == "👥 مدیریت ادمین":
        await update.message.reply_html(
            "👥 <b>مدیریت ادمین‌ها</b>\n\nاز دکمه‌های زیر استفاده کنید:",
            reply_markup=ADMIN_KEYBOARD,
        )

    elif text == "➕ افزودن ادمین":
        await add_admin(update, context)

    elif text == "👥 لیست ادمین‌ها":
        await admins_list(update, context)

    elif text == "❌ حذف ادمین":
        await remove_admin(update, context)

    elif text == "🌍 تنظیمات کشور":
        await set_country_code(update, context)

    elif text == "📋 مدیریت استثناها":
        await update.message.reply_html(
            "📋 <b>مدیریت کاربران استثنا</b>\n\nاز دکمه‌های زیر استفاده کنید:",
            reply_markup=EXCEPTION_KEYBOARD,
        )

    elif text == "✅ افزودن به استثنا":
        await set_except_users(update, context)

    elif text == "📋 لیست استثناها":
        await show_except_users(update, context)

    elif text == "🚫 حذف از استثنا":
        await remove_except_user(update, context)

    elif text == "📊 تنظیمات عمومی":
        await update.message.reply_html(
            "📊 <b>تنظیمات عمومی سیستم</b>\n\nاز دکمه‌های زیر استفاده کنید:",
            reply_markup=SETTINGS_KEYBOARD,
        )

    elif text == "📈 محدودیت عمومی":
        await get_general_limit_number(update, context)

    elif text == "⏱️ فاصله بررسی":
        await get_check_interval(update, context)

    elif text == "🕐 زمان فعالیت":
        await get_time_to_active_users(update, context)

    elif text == "💾 پشتیبان گیری":
        await send_backup(update, context)

    elif text == "🔙 بازگشت":
        await update.message.reply_html(
            "🏠 <b>منوی اصلی</b>\n\nاز دکمه‌های زیر برای دسترسی سریع استفاده کنید:",
            reply_markup=MAIN_KEYBOARD,
        )

    elif text in ["✅ بله", "❌ خیر"]:
        # تبدیل به yes/no برای سازگاری با get_confirmation
        update.message.text = "yes" if text == "✅ بله" else "no"
        await get_confirmation(update, context)

    else:
        # اگر متن آزاد بود و با هیچ دکمه‌ای مچ نشد، راهنما را نشان بده
        await start(update, context)


# =========================
# Handlers Registration
# =========================
# اول: متن‌های غیر-فرمان به کیبورد هندلر می‌خورند
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_keyboard_commands))

# دستورات اصلی
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("admins_list", admins_list))
application.add_handler(CommandHandler("show_except_users", show_except_users))
application.add_handler(CommandHandler("spernet", spernet_info))

# محاوره‌های چندمرحله‌ای (با Regex برای ورودی‌های عددی)
application.add_handler(
    ConversationHandler(
        entry_points=[CommandHandler("create_config", create_config)],
        states={
            GET_CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_confirmation)],
            GET_DOMAIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_domain)],
            GET_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_username)],
            GET_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_password)],
        },
        fallbacks=[CommandHandler("start", start)],
    )
)

application.add_handler(
    ConversationHandler(
        entry_points=[CommandHandler("set_special_limit", set_special_limit)],
        states={
            GET_SPECIAL_LIMIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_special_limit)],
            GET_LIMIT_NUMBER: [MessageHandler(filters.Regex(r'^\d+$'), get_limit_number)],
        },
        fallbacks=[CommandHandler("start", start)],
    )
)

application.add_handler(
    ConversationHandler(
        entry_points=[CommandHandler("set_time_to_active_users", get_time_to_active_users)],
        states={
            GET_TIME_TO_ACTIVE_USERS: [MessageHandler(filters.Regex(r'^\d+$'), get_time_to_active_users_handler)],
        },
        fallbacks=[CommandHandler("start", start)],
    )
)

application.add_handler(
    ConversationHandler(
        entry_points=[CommandHandler("set_check_interval", get_check_interval)],
        states={
            GET_CHECK_INTERVAL: [MessageHandler(filters.Regex(r'^\d+$'), get_check_interval_handler)],
        },
        fallbacks=[CommandHandler("start", start)],
    )
)

application.add_handler(
    ConversationHandler(
        entry_points=[CommandHandler("set_general_limit_number", get_general_limit_number)],
        states={
            GET_GENERAL_LIMIT_NUMBER: [MessageHandler(filters.Regex(r'^\d+$'), get_general_limit_number_handler)],
        },
        fallbacks=[CommandHandler("start", start)],
    )
)

application.add_handler(
    ConversationHandler(
        entry_points=[CommandHandler("remove_except_user", remove_except_user)],
        states={
            REMOVE_EXCEPT_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_except_user_handler)],
        },
        fallbacks=[CommandHandler("start", start)],
    )
)

application.add_handler(
    ConversationHandler(
        entry_points=[CommandHandler("country_code", set_country_code)],
        states={
            SET_COUNTRY_CODE: [MessageHandler(filters.Regex(r'^[1-4]$'), write_country_code)],
        },
        fallbacks=[CommandHandler("start", start)],
    )
)

application.add_handler(
    ConversationHandler(
        entry_points=[CommandHandler("set_except_user", set_except_users)],
        states={
            SET_EXCEPT_USERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_except_users_handler)],
        },
        fallbacks=[CommandHandler("start", start)],
    )
)

application.add_handler(
    ConversationHandler(
        entry_points=[CommandHandler("show_special_limit", show_special_limit_function)],
        states={},
        fallbacks=[CommandHandler("start", start)],
    )
)

application.add_handler(
    ConversationHandler(
        entry_points=[CommandHandler("add_admin", add_admin)],
        states={GET_CHAT_ID: [MessageHandler(filters.Regex(r'^\d+$'), get_chat_id)]},
        fallbacks=[CommandHandler("start", start)],
    )
)

application.add_handler(
    ConversationHandler(
        entry_points=[CommandHandler("remove_admin", remove_admin)],
        states={GET_CHAT_ID_TO_REMOVE: [MessageHandler(filters.Regex(r'^\d+$'), get_chat_id_to_remove)]},
        fallbacks=[CommandHandler("start", start)],
    )
)

application.add_handler(
    ConversationHandler(
        entry_points=[CommandHandler("backup", send_backup)],
        states={},
        fallbacks=[CommandHandler("start", start)],
    )
)

# Unknown COMMAND → برگرد به راهنما
unknown_handler_command = MessageHandler(filters.COMMAND, start)
application.add_handler(unknown_handler_command)

if __name__ == "__main__":
    application.run_polling()
