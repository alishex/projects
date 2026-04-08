from __future__ import annotations

import logging
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import get_settings
from database import Database
from keyboards import (
    account_keyboard,
    cancel_keyboard,
    category_keyboard,
    currency_keyboard,
    main_menu_keyboard,
)

logging.basicConfig(
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

ACCOUNT, CURRENCY, AMOUNT, CATEGORY, NOTE = range(5)
DELETE_PAGE_SIZE = 8
SKIP_NOTE = "⏭ O'tkazib yuborish"
CANCEL = '⬅️ Bekor qilish'
ACCOUNT_MAP = {'💵 Naqd': 'cash', '💳 Karta': 'card'}
CURRENCY_MAP = {'🇺🇿 So\'m': 'UZS', '🇺🇸 Dollar': 'USD', '🇪🇺 Yevro': 'EUR'}
ACCOUNT_LABELS = {'cash': 'Naqd', 'card': 'Karta'}
CURRENCY_LABELS = {'UZS': 'So\'m', 'USD': 'Dollar', 'EUR': 'Yevro'}


class FinanceBot:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.db = Database(self.settings.db_path)
        self.tz = self._build_timezone(self.settings.timezone)

    @staticmethod
    def _build_timezone(tz_name: str):
        try:
            return ZoneInfo(tz_name)
        except ZoneInfoNotFoundError:
            if tz_name == 'Asia/Tashkent':
                logger.warning(
                    'tzdata topilmadi. Asia/Tashkent uchun UTC+5 fallback ishlatildi.'
                )
                return timezone(timedelta(hours=5), name='Asia/Tashkent')
            logger.warning(
                "Timezone '%s' topilmadi. UTC ishlatiladi.",
                tz_name,
            )
            return timezone.utc

    def is_owner(self, update: Update) -> bool:
        user = update.effective_user
        return bool(user and user.id == self.settings.owner_telegram_id)

    async def require_owner(self, update: Update) -> bool:
        if self.is_owner(update):
            return True

        target = update.effective_message
        if target:
            await target.reply_text('Bu bot faqat egasi uchun ishlaydi.')
        return False

    def now(self) -> datetime:
        return datetime.now(self.tz)

    @staticmethod
    def format_money(value: float) -> str:
        if abs(value - round(value)) < 0.000001:
            return f"{int(round(value)):,}".replace(',', ' ')
        return f"{value:,.2f}".replace(',', ' ')

    @staticmethod
    def parse_amount(text: str) -> float | None:
        cleaned = text.strip().replace(' ', '').replace(',', '.')
        cleaned = re.sub(r'[^\d.]', '', cleaned)
        if not cleaned:
            return None
        try:
            value = float(cleaned)
        except ValueError:
            return None
        if value <= 0:
            return None
        return round(value, 2)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self.require_owner(update):
            return
        context.user_data.clear()
        await update.message.reply_text(
            'Assalomu alaykum. Pul nazorati botingiz tayyor. Kerakli bo‘limni tanlang.',
            reply_markup=main_menu_keyboard(),
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self.require_owner(update):
            return
        await update.message.reply_text(
            'Foydalanish juda oddiy:\n'
            '1) Kirim yoki chiqim qo‘shing\n'
            '2) Naqd/Karta va valyutani tanlang\n'
            '3) Balans va hisobotlarni valyuta bo‘yicha ko‘ring\n'
            '4) Kerak bo‘lsa CSV yuklab oling',
            reply_markup=main_menu_keyboard(),
        )

    async def start_income(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        return await self._start_transaction(update, context, 'income')

    async def start_expense(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        return await self._start_transaction(update, context, 'expense')

    async def _start_transaction(self, update: Update, context: ContextTypes.DEFAULT_TYPE, tx_type: str) -> int:
        if not await self.require_owner(update):
            return ConversationHandler.END

        context.user_data.clear()
        context.user_data['tx_type'] = tx_type
        label = 'kirim' if tx_type == 'income' else 'chiqim'
        await update.message.reply_text(
            f"{label.title()} qaysi turga yoziladi?",
            reply_markup=account_keyboard(),
        )
        return ACCOUNT

    async def receive_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        if not await self.require_owner(update):
            return ConversationHandler.END

        text = (update.message.text or '').strip()
        if text == CANCEL:
            return await self.cancel(update, context)
        if text not in ACCOUNT_MAP:
            await update.message.reply_text(
                'Naqd yoki Karta tanlang.',
                reply_markup=account_keyboard(),
            )
            return ACCOUNT

        context.user_data['account_type'] = ACCOUNT_MAP[text]
        await update.message.reply_text(
            'Valyutani tanlang.',
            reply_markup=currency_keyboard(),
        )
        return CURRENCY

    async def receive_currency(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        if not await self.require_owner(update):
            return ConversationHandler.END

        text = (update.message.text or '').strip()
        if text == CANCEL:
            return await self.cancel(update, context)
        if text not in CURRENCY_MAP:
            await update.message.reply_text(
                'So‘m, Dollar yoki Yevro tanlang.',
                reply_markup=currency_keyboard(),
            )
            return CURRENCY

        context.user_data['currency'] = CURRENCY_MAP[text]
        await update.message.reply_text(
            'Summani yuboring. Masalan: 150000 yoki 120.50',
            reply_markup=cancel_keyboard(),
        )
        return AMOUNT

    async def receive_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        if not await self.require_owner(update):
            return ConversationHandler.END

        text = (update.message.text or '').strip()
        if text == CANCEL:
            return await self.cancel(update, context)

        amount = self.parse_amount(text)
        if amount is None:
            await update.message.reply_text(
                'Summa noto‘g‘ri. Qaytadan yuboring. Masalan: 150000 yoki 120.50',
                reply_markup=cancel_keyboard(),
            )
            return AMOUNT

        context.user_data['amount'] = amount
        tx_type = context.user_data['tx_type']
        title = 'Kirim kategoriyasini tanlang' if tx_type == 'income' else 'Chiqim kategoriyasini tanlang'
        await update.message.reply_text(title, reply_markup=category_keyboard(tx_type))
        return CATEGORY

    async def receive_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        if not await self.require_owner(update):
            return ConversationHandler.END

        text = (update.message.text or '').strip()
        if text == CANCEL:
            return await self.cancel(update, context)

        context.user_data['category'] = text
        await update.message.reply_text(
            'Izoh yozing yoki o‘tkazib yuboring.',
            reply_markup=ReplyKeyboardMarkup([[SKIP_NOTE], [CANCEL]], resize_keyboard=True, one_time_keyboard=True),
        )
        return NOTE

    async def receive_note(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        if not await self.require_owner(update):
            return ConversationHandler.END

        text = (update.message.text or '').strip()
        if text == CANCEL:
            return await self.cancel(update, context)

        note = '' if text == SKIP_NOTE else text
        tx_type = str(context.user_data['tx_type'])
        account_type = str(context.user_data['account_type'])
        currency = str(context.user_data['currency'])
        amount = float(context.user_data['amount'])
        category = str(context.user_data['category'])

        created_at = self.now().isoformat(timespec='seconds')
        tx_id = self.db.add_transaction(
            tx_type=tx_type,
            account_type=account_type,
            currency=currency,
            amount=amount,
            category=category,
            note=note,
            created_at=created_at,
        )
        balances = self.db.get_balance_by_currency_account()
        currency_total = balances[currency]['cash'] + balances[currency]['card']

        tx_label = 'Kirim' if tx_type == 'income' else 'Chiqim'
        message = (
            f"✅ Saqlandi\n\n"
            f"ID: {tx_id}\n"
            f"Turi: {tx_label}\n"
            f"Hisob: {ACCOUNT_LABELS[account_type]}\n"
            f"Valyuta: {CURRENCY_LABELS[currency]}\n"
            f"Summa: {self.format_money(amount)}\n"
            f"Kategoriya: {category}\n"
            f"Izoh: {note or '-'}\n"
            f"{CURRENCY_LABELS[currency]} jami balans: {self.format_money(currency_total)}"
        )
        await update.message.reply_text(message, reply_markup=main_menu_keyboard())
        context.user_data.clear()
        return ConversationHandler.END

    async def show_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self.require_owner(update):
            return
        balances = self.db.get_balance_by_currency_account()
        lines = ['💰 Joriy balans']
        for currency in ['UZS', 'USD', 'EUR']:
            cash = balances[currency]['cash']
            card = balances[currency]['card']
            total = cash + card
            if abs(total) < 0.000001 and abs(cash) < 0.000001 and abs(card) < 0.000001:
                continue
            lines.extend([
                '',
                f"{CURRENCY_LABELS[currency]}:",
                f"• Naqd: {self.format_money(cash)}",
                f"• Karta: {self.format_money(card)}",
                f"• Jami: {self.format_money(total)}",
            ])
        if len(lines) == 1:
            lines.append('Hali yozuv yo‘q.')
        await update.message.reply_text('\n'.join(lines), reply_markup=main_menu_keyboard())

    async def today_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self.require_owner(update):
            return
        now = self.now()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        await update.message.reply_text(
            self.build_report_text('📊 Bugungi hisobot', start, end),
            reply_markup=main_menu_keyboard(),
        )

    async def month_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self.require_owner(update):
            return
        now = self.now()
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
        await update.message.reply_text(
            self.build_report_text('🗓 Oylik hisobot', start, end),
            reply_markup=main_menu_keyboard(),
        )

    def build_report_text(self, title: str, start: datetime, end: datetime) -> str:
        start_iso = start.isoformat(timespec='seconds')
        end_iso = end.isoformat(timespec='seconds')
        summary = self.db.get_period_summary(start_iso, end_iso)

        lines = [title]
        if not summary:
            lines.extend(['', 'Bu davr uchun yozuv topilmadi.'])
            return '\n'.join(lines)

        for currency in ['UZS', 'USD', 'EUR']:
            if currency not in summary:
                continue
            item = summary[currency]
            lines.extend([
                '',
                f"{CURRENCY_LABELS[currency]}:",
                f"Kirim: {self.format_money(item['income'])}",
                f"Chiqim: {self.format_money(item['expense'])}",
                f"Farq: {self.format_money(item['balance'])}",
                f"Yozuvlar soni: {item['tx_count']}",
                'Hisob kesimida:',
                f"• Naqd — Kirim: {self.format_money(item['accounts']['cash']['income'])}, Chiqim: {self.format_money(item['accounts']['cash']['expense'])}, Farq: {self.format_money(item['accounts']['cash']['balance'])}",
                f"• Karta — Kirim: {self.format_money(item['accounts']['card']['income'])}, Chiqim: {self.format_money(item['accounts']['card']['expense'])}, Farq: {self.format_money(item['accounts']['card']['balance'])}",
            ])

            expense_breakdown = self.db.get_category_breakdown(start_iso, end_iso, 'expense', currency)
            income_breakdown = self.db.get_category_breakdown(start_iso, end_iso, 'income', currency)

            if expense_breakdown:
                lines.append('Top chiqim kategoriyalar:')
                for category, total in expense_breakdown[:5]:
                    lines.append(f"• {category}: {self.format_money(total)}")

            if income_breakdown:
                lines.append('Top kirim kategoriyalar:')
                for category, total in income_breakdown[:5]:
                    lines.append(f"• {category}: {self.format_money(total)}")

        return '\n'.join(lines)

    async def recent_transactions(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self.require_owner(update):
            return
        rows = self.db.get_recent_transactions(limit=10)
        if not rows:
            await update.message.reply_text('Hali yozuv yo‘q.', reply_markup=main_menu_keyboard())
            return

        lines = ['📋 Oxirgi 10 ta yozuv', '']
        for row in rows:
            icon = '🟢' if row.tx_type == 'income' else '🔴'
            label = 'Kirim' if row.tx_type == 'income' else 'Chiqim'
            timestamp = datetime.fromisoformat(row.created_at).astimezone(self.tz).strftime('%d.%m %H:%M')
            lines.append(
                f"{icon} {label} | {ACCOUNT_LABELS[row.account_type]} | {CURRENCY_LABELS[row.currency]} | {self.format_money(row.amount)} | {row.category} | {timestamp}"
            )
            if row.note:
                lines.append(f"   Izoh: {row.note}")

        await update.message.reply_text('\n'.join(lines), reply_markup=main_menu_keyboard())

    def build_delete_keyboard(self, rows, offset: int, total: int) -> InlineKeyboardMarkup:
        keyboard = []
        for row in rows:
            icon = '🟢' if row.tx_type == 'income' else '🔴'
            label = 'Kirim' if row.tx_type == 'income' else 'Chiqim'
            amount = self.format_money(row.amount)
            button_text = f"{icon} {label} | {ACCOUNT_LABELS[row.account_type]} | {CURRENCY_LABELS[row.currency]} | {amount}"
            keyboard.append([InlineKeyboardButton(button_text[:60], callback_data=f"del:{row.id}:{offset}")])

        nav_row = []
        if offset > 0:
            prev_offset = max(0, offset - DELETE_PAGE_SIZE)
            nav_row.append(InlineKeyboardButton('⬅️ Oldingi', callback_data=f"page:{prev_offset}"))
        if offset + DELETE_PAGE_SIZE < total:
            next_offset = offset + DELETE_PAGE_SIZE
            nav_row.append(InlineKeyboardButton('Keyingi ➡️', callback_data=f"page:{next_offset}"))
        if nav_row:
            keyboard.append(nav_row)
        keyboard.append([InlineKeyboardButton('❌ Yopish', callback_data='delete_close')])
        return InlineKeyboardMarkup(keyboard)

    def build_delete_text(self, rows, offset: int, total: int) -> str:
        lines = ['🗑 O‘chirish uchun yozuvni tanlang', '']
        if not rows:
            lines.append('Yozuv topilmadi.')
            return '\n'.join(lines)

        for idx, row in enumerate(rows, start=offset + 1):
            icon = '🟢' if row.tx_type == 'income' else '🔴'
            label = 'Kirim' if row.tx_type == 'income' else 'Chiqim'
            timestamp = datetime.fromisoformat(row.created_at).astimezone(self.tz).strftime('%d.%m %H:%M')
            lines.append(
                f"{idx}. {icon} {label} | {ACCOUNT_LABELS[row.account_type]} | {CURRENCY_LABELS[row.currency]} | {self.format_money(row.amount)} | {row.category} | {timestamp}"
            )
            if row.note:
                lines.append(f"   Izoh: {row.note}")

        current_page = (offset // DELETE_PAGE_SIZE) + 1
        total_pages = max(1, (total + DELETE_PAGE_SIZE - 1) // DELETE_PAGE_SIZE)
        lines.extend(['', f"Sahifa: {current_page}/{total_pages}", 'Kerakli yozuvni pastdagi knopkadan tanlang.'])
        return '\n'.join(lines)

    async def show_delete_picker(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self.require_owner(update):
            return
        await self._send_delete_picker_message(update, offset=0)

    async def _send_delete_picker_message(self, update: Update, offset: int) -> None:
        total = self.db.count_transactions()
        rows = self.db.get_transactions_page(limit=DELETE_PAGE_SIZE, offset=offset)
        text = self.build_delete_text(rows, offset, total)
        reply_markup = self.build_delete_keyboard(rows, offset, total) if rows else None
        if update.message:
            await update.message.reply_text(text, reply_markup=reply_markup)
            await update.message.reply_text('Bosh menyu.', reply_markup=main_menu_keyboard())
        elif update.callback_query:
            await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup)

    async def handle_delete_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if query is None:
            return
        if not self.is_owner(update):
            await query.answer('Ruxsat yo‘q.', show_alert=True)
            return

        data = query.data or ''
        if data == 'delete_close':
            await query.answer()
            await query.edit_message_text('O‘chirish oynasi yopildi.')
            if query.message:
                await query.message.reply_text('Bosh menyu.', reply_markup=main_menu_keyboard())
            return

        if data.startswith('page:'):
            await query.answer()
            try:
                offset = max(0, int(data.split(':', 1)[1]))
            except ValueError:
                offset = 0
            total = self.db.count_transactions()
            if total > 0 and offset >= total:
                offset = max(0, ((total - 1) // DELETE_PAGE_SIZE) * DELETE_PAGE_SIZE)
            rows = self.db.get_transactions_page(limit=DELETE_PAGE_SIZE, offset=offset)
            text = self.build_delete_text(rows, offset, total)
            markup = self.build_delete_keyboard(rows, offset, total) if rows else None
            await query.edit_message_text(text=text, reply_markup=markup)
            return

        if data.startswith('del:'):
            await query.answer()
            parts = data.split(':')
            if len(parts) != 3:
                await query.edit_message_text('Xatolik yuz berdi. Qaytadan urinib ko‘ring.')
                return
            try:
                tx_id = int(parts[1])
                offset = max(0, int(parts[2]))
            except ValueError:
                await query.edit_message_text('Xatolik yuz berdi. Qaytadan urinib ko‘ring.')
                return

            deleted = self.db.delete_transaction_by_id(tx_id)
            total = self.db.count_transactions()
            if total > 0 and offset >= total:
                offset = max(0, ((total - 1) // DELETE_PAGE_SIZE) * DELETE_PAGE_SIZE)
            rows = self.db.get_transactions_page(limit=DELETE_PAGE_SIZE, offset=offset)
            if deleted is None:
                text = 'Bu yozuv allaqachon o‘chirilgan yoki topilmadi.\n\n' + self.build_delete_text(rows, offset, total)
            else:
                label = 'Kirim' if deleted.tx_type == 'income' else 'Chiqim'
                deleted_line = (
                    f"✅ O‘chirildi: {label} | {ACCOUNT_LABELS[deleted.account_type]} | {CURRENCY_LABELS[deleted.currency]} | {self.format_money(deleted.amount)} | {deleted.category}"
                )
                text = deleted_line + '\n\n' + self.build_delete_text(rows, offset, total)
            markup = self.build_delete_keyboard(rows, offset, total) if rows else None
            await query.edit_message_text(text=text, reply_markup=markup)

    async def export_csv(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self.require_owner(update):
            return

        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = str(Path(tmp_dir) / 'finance_history.csv')
            self.db.export_csv(file_path)
            with open(file_path, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename='finance_history.csv',
                    caption='CSV tayyor.',
                    reply_markup=main_menu_keyboard(),
                )

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        context.user_data.clear()
        if update.effective_message:
            await update.effective_message.reply_text(
                'Amal bekor qilindi.',
                reply_markup=main_menu_keyboard(),
            )
        return ConversationHandler.END

    async def fallback_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self.require_owner(update):
            return
        await update.message.reply_text(
            'Pastdagi knopkalardan foydalaning yoki /start bosing.',
            reply_markup=main_menu_keyboard(),
        )

    def build_app(self) -> Application:
        application = Application.builder().token(self.settings.bot_token).build()

        conv_handler = ConversationHandler(
            entry_points=[
                MessageHandler(filters.Regex(r"^➕ Kirim qo'shish$"), self.start_income),
                MessageHandler(filters.Regex(r"^➖ Chiqim qo'shish$"), self.start_expense),
            ],
            states={
                ACCOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_account)],
                CURRENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_currency)],
                AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_amount)],
                CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_category)],
                NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_note)],
            },
            fallbacks=[
                CommandHandler('cancel', self.cancel),
                MessageHandler(filters.Regex(r'^⬅️ Bekor qilish$'), self.cancel),
            ],
            per_chat=True,
            per_user=True,
            per_message=False,
            allow_reentry=True,
        )

        application.add_handler(CommandHandler('start', self.start))
        application.add_handler(CommandHandler('help', self.help_command))
        application.add_handler(conv_handler)
        application.add_handler(MessageHandler(filters.Regex(r'^💰 Balans$'), self.show_balance))
        application.add_handler(MessageHandler(filters.Regex(r'^📊 Bugungi hisobot$'), self.today_report))
        application.add_handler(MessageHandler(filters.Regex(r'^🗓 Oylik hisobot$'), self.month_report))
        application.add_handler(MessageHandler(filters.Regex(r'^📋 Oxirgi yozuvlar$'), self.recent_transactions))
        application.add_handler(MessageHandler(filters.Regex(r"^🗑 Yozuvni o'chirish$"), self.show_delete_picker))
        application.add_handler(CallbackQueryHandler(self.handle_delete_callback, pattern=r'^(page:\d+|del:\d+:\d+|delete_close)$'))
        application.add_handler(MessageHandler(filters.Regex(r'^⬇️ CSV yuklab olish$'), self.export_csv))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.fallback_text))

        return application

    def run(self) -> None:
        app = self.build_app()
        logger.info('Finance bot ishga tushmoqda...')
        app.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    FinanceBot().run()
