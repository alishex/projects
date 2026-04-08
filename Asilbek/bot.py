from __future__ import annotations

import logging
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from config import get_settings
from database import ActivityRecord, Database
from keyboards import account_keyboard, cancel_keyboard, category_keyboard, currency_keyboard, main_menu_keyboard

logging.basicConfig(format='%(asctime)s | %(levelname)s | %(name)s | %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TX_ACCOUNT, TX_CURRENCY, TX_AMOUNT, TX_CATEGORY, TX_NOTE = range(5)
TR_FROM_ACCOUNT, TR_FROM_CURRENCY, TR_TO_ACCOUNT, TR_TO_CURRENCY, TR_AMOUNT, TR_NOTE = range(10, 16)
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
                logger.warning('tzdata topilmadi. Asia/Tashkent uchun UTC+5 fallback ishlatildi.')
                return timezone(timedelta(hours=5), name='Asia/Tashkent')
            logger.warning("Timezone '%s' topilmadi. UTC ishlatiladi.", tz_name)
            return timezone.utc

    def is_owner(self, update: Update) -> bool:
        return bool(update.effective_user and update.effective_user.id == self.settings.owner_telegram_id)

    async def require_owner(self, update: Update) -> bool:
        if self.is_owner(update):
            return True
        if update.effective_message:
            await update.effective_message.reply_text('Bu bot faqat egasi uchun ishlaydi.')
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
        cleaned = re.sub(r'[^\d.]', '', text.strip().replace(' ', '').replace(',', '.'))
        if not cleaned:
            return None
        try:
            value = float(cleaned)
        except ValueError:
            return None
        return round(value, 2) if value > 0 else None

    def format_activity_short(self, row: ActivityRecord) -> str:
        if row.record_type == 'transaction':
            label = 'Kirim' if row.tx_type == 'income' else 'Chiqim'
            return f"{label} | {ACCOUNT_LABELS[row.account_type]} | {CURRENCY_LABELS[row.currency]} | {self.format_money(row.amount)} | {row.category}"
        return f"Transfer | {ACCOUNT_LABELS[row.account_type]} {CURRENCY_LABELS[row.currency]} → {ACCOUNT_LABELS[row.to_account_type]} {CURRENCY_LABELS[row.to_currency]} | {self.format_money(row.amount)}"

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self.require_owner(update):
            return
        context.user_data.clear()
        await update.message.reply_text('Assalomu alaykum. Pul nazorati botingiz tayyor. Kerakli bo‘limni tanlang.', reply_markup=main_menu_keyboard())

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self.require_owner(update):
            return
        await update.message.reply_text('Kirim/chiqim va transfer qo‘shishingiz mumkin. Transfer kirim/chiqimga aralashmaydi, lekin balansda hisoblanadi.', reply_markup=main_menu_keyboard())

    async def start_income(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        return await self._start_transaction(update, context, 'income')

    async def start_expense(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        return await self._start_transaction(update, context, 'expense')

    async def _start_transaction(self, update: Update, context: ContextTypes.DEFAULT_TYPE, tx_type: str) -> int:
        if not await self.require_owner(update):
            return ConversationHandler.END
        context.user_data.clear()
        context.user_data['tx_type'] = tx_type
        await update.message.reply_text(('Kirim' if tx_type == 'income' else 'Chiqim') + ' qaysi turga yoziladi?', reply_markup=account_keyboard())
        return TX_ACCOUNT

    async def tx_receive_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        text = (update.message.text or '').strip()
        if text == CANCEL:
            return await self.cancel(update, context)
        if text not in ACCOUNT_MAP:
            await update.message.reply_text('Naqd yoki Karta tanlang.', reply_markup=account_keyboard())
            return TX_ACCOUNT
        context.user_data['account_type'] = ACCOUNT_MAP[text]
        await update.message.reply_text('Valyutani tanlang.', reply_markup=currency_keyboard())
        return TX_CURRENCY

    async def tx_receive_currency(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        text = (update.message.text or '').strip()
        if text == CANCEL:
            return await self.cancel(update, context)
        if text not in CURRENCY_MAP:
            await update.message.reply_text('So‘m, Dollar yoki Yevro tanlang.', reply_markup=currency_keyboard())
            return TX_CURRENCY
        context.user_data['currency'] = CURRENCY_MAP[text]
        await update.message.reply_text('Summani yuboring. Masalan: 150000 yoki 120.50', reply_markup=cancel_keyboard())
        return TX_AMOUNT

    async def tx_receive_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        text = (update.message.text or '').strip()
        if text == CANCEL:
            return await self.cancel(update, context)
        amount = self.parse_amount(text)
        if amount is None:
            await update.message.reply_text('Summa noto‘g‘ri. Qaytadan yuboring.', reply_markup=cancel_keyboard())
            return TX_AMOUNT
        context.user_data['amount'] = amount
        await update.message.reply_text(('Kirim' if context.user_data['tx_type'] == 'income' else 'Chiqim') + ' kategoriyasini tanlang', reply_markup=category_keyboard(context.user_data['tx_type']))
        return TX_CATEGORY

    async def tx_receive_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        text = (update.message.text or '').strip()
        if text == CANCEL:
            return await self.cancel(update, context)
        context.user_data['category'] = text
        await update.message.reply_text('Izoh yozing yoki o‘tkazib yuboring.', reply_markup=ReplyKeyboardMarkup([[SKIP_NOTE], [CANCEL]], resize_keyboard=True, one_time_keyboard=True))
        return TX_NOTE

    async def tx_receive_note(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        text = (update.message.text or '').strip()
        if text == CANCEL:
            return await self.cancel(update, context)
        note = '' if text == SKIP_NOTE else text
        tx_id = self.db.add_transaction(
            str(context.user_data['tx_type']),
            str(context.user_data['account_type']),
            str(context.user_data['currency']),
            float(context.user_data['amount']),
            str(context.user_data['category']),
            note,
            self.now().isoformat(timespec='seconds'),
        )
        await update.message.reply_text(f"✅ Saqlandi\n\nID: {tx_id}\n{self.format_activity_short(self.db.get_activity_page(limit=1, offset=0, where_clause='record_type = ? AND id = ?', params=('transaction', tx_id))[0])}\nIzoh: {note or '-'}", reply_markup=main_menu_keyboard())
        context.user_data.clear()
        return ConversationHandler.END

    async def start_transfer(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        if not await self.require_owner(update):
            return ConversationHandler.END
        context.user_data.clear()
        await update.message.reply_text('Qayerdan transfer qilasiz?', reply_markup=account_keyboard())
        return TR_FROM_ACCOUNT

    async def tr_receive_from_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        text = (update.message.text or '').strip()
        if text == CANCEL:
            return await self.cancel(update, context)
        if text not in ACCOUNT_MAP:
            await update.message.reply_text('Naqd yoki Karta tanlang.', reply_markup=account_keyboard())
            return TR_FROM_ACCOUNT
        context.user_data['from_account_type'] = ACCOUNT_MAP[text]
        await update.message.reply_text('Qaysi valyutadan?', reply_markup=currency_keyboard())
        return TR_FROM_CURRENCY

    async def tr_receive_from_currency(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        text = (update.message.text or '').strip()
        if text == CANCEL:
            return await self.cancel(update, context)
        if text not in CURRENCY_MAP:
            await update.message.reply_text('So‘m, Dollar yoki Yevro tanlang.', reply_markup=currency_keyboard())
            return TR_FROM_CURRENCY
        context.user_data['from_currency'] = CURRENCY_MAP[text]
        await update.message.reply_text('Qayerga transfer qilasiz?', reply_markup=account_keyboard())
        return TR_TO_ACCOUNT

    async def tr_receive_to_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        text = (update.message.text or '').strip()
        if text == CANCEL:
            return await self.cancel(update, context)
        if text not in ACCOUNT_MAP:
            await update.message.reply_text('Naqd yoki Karta tanlang.', reply_markup=account_keyboard())
            return TR_TO_ACCOUNT
        context.user_data['to_account_type'] = ACCOUNT_MAP[text]
        await update.message.reply_text('Qaysi valyutaga?', reply_markup=currency_keyboard())
        return TR_TO_CURRENCY

    async def tr_receive_to_currency(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        text = (update.message.text or '').strip()
        if text == CANCEL:
            return await self.cancel(update, context)
        if text not in CURRENCY_MAP:
            await update.message.reply_text('So‘m, Dollar yoki Yevro tanlang.', reply_markup=currency_keyboard())
            return TR_TO_CURRENCY
        to_currency = CURRENCY_MAP[text]
        if (context.user_data['from_account_type'], context.user_data['from_currency']) == (context.user_data['to_account_type'], to_currency):
            await update.message.reply_text('Bir xil joyga transfer bo‘lmaydi. Manzilni boshqacha tanlang.', reply_markup=account_keyboard())
            return TR_TO_ACCOUNT
        context.user_data['to_currency'] = to_currency
        await update.message.reply_text('Transfer summasini yuboring.', reply_markup=cancel_keyboard())
        return TR_AMOUNT

    async def tr_receive_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        text = (update.message.text or '').strip()
        if text == CANCEL:
            return await self.cancel(update, context)
        amount = self.parse_amount(text)
        if amount is None:
            await update.message.reply_text('Summa noto‘g‘ri. Qaytadan yuboring.', reply_markup=cancel_keyboard())
            return TR_AMOUNT
        context.user_data['amount'] = amount
        await update.message.reply_text('Izoh yozing yoki o‘tkazib yuboring.', reply_markup=ReplyKeyboardMarkup([[SKIP_NOTE], [CANCEL]], resize_keyboard=True, one_time_keyboard=True))
        return TR_NOTE

    async def tr_receive_note(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        text = (update.message.text or '').strip()
        if text == CANCEL:
            return await self.cancel(update, context)
        note = '' if text == SKIP_NOTE else text
        transfer_id = self.db.add_transfer(
            str(context.user_data['from_account_type']),
            str(context.user_data['from_currency']),
            str(context.user_data['to_account_type']),
            str(context.user_data['to_currency']),
            float(context.user_data['amount']),
            note,
            self.now().isoformat(timespec='seconds'),
        )
        await update.message.reply_text(f"✅ Transfer saqlandi\n\nID: {transfer_id}\nQayerdan: {ACCOUNT_LABELS[context.user_data['from_account_type']]} | {CURRENCY_LABELS[context.user_data['from_currency']]}\nQayerga: {ACCOUNT_LABELS[context.user_data['to_account_type']]} | {CURRENCY_LABELS[context.user_data['to_currency']]}\nSumma: {self.format_money(float(context.user_data['amount']))}\nIzoh: {note or '-'}", reply_markup=main_menu_keyboard())
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
            lines.extend(['', f"{CURRENCY_LABELS[currency]}:", f"• Naqd: {self.format_money(cash)}", f"• Karta: {self.format_money(card)}", f"• Jami: {self.format_money(total)}"])
        if len(lines) == 1:
            lines.append('Hali yozuv yo‘q.')
        await update.message.reply_text('\n'.join(lines), reply_markup=main_menu_keyboard())

    async def today_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self.require_owner(update):
            return
        now = self.now()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        await update.message.reply_text(self.build_report_text('📊 Bugungi hisobot', start, end), reply_markup=main_menu_keyboard())

    async def month_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self.require_owner(update):
            return
        now = self.now()
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = start.replace(year=start.year + 1, month=1) if start.month == 12 else start.replace(month=start.month + 1)
        await update.message.reply_text(self.build_report_text('🗓 Oylik hisobot', start, end), reply_markup=main_menu_keyboard())

    def build_report_text(self, title: str, start: datetime, end: datetime) -> str:
        summary = self.db.get_period_summary(start.isoformat(timespec='seconds'), end.isoformat(timespec='seconds'))
        lines = [title]
        if not summary:
            return '\n'.join(lines + ['', 'Bu davr uchun yozuv topilmadi.'])
        for currency in ['UZS', 'USD', 'EUR']:
            if currency not in summary:
                continue
            item = summary[currency]
            lines.extend([
                '', f"{CURRENCY_LABELS[currency]}:",
                f"Kirim: {self.format_money(item['income'])}",
                f"Chiqim: {self.format_money(item['expense'])}",
                f"Transfer kirdi: {self.format_money(item['transfer_in'])}",
                f"Transfer chiqdi: {self.format_money(item['transfer_out'])}",
                f"Farq: {self.format_money(item['balance'])}",
                f"Tranzaksiyalar soni: {item['tx_count']}",
                f"Transferlar soni: {item['transfer_count']}",
                'Hisob kesimida:',
                f"• Naqd — Kirim: {self.format_money(item['accounts']['cash']['income'])}, Chiqim: {self.format_money(item['accounts']['cash']['expense'])}, Transfer kirdi: {self.format_money(item['accounts']['cash']['transfer_in'])}, Transfer chiqdi: {self.format_money(item['accounts']['cash']['transfer_out'])}, Farq: {self.format_money(item['accounts']['cash']['balance'])}",
                f"• Karta — Kirim: {self.format_money(item['accounts']['card']['income'])}, Chiqim: {self.format_money(item['accounts']['card']['expense'])}, Transfer kirdi: {self.format_money(item['accounts']['card']['transfer_in'])}, Transfer chiqdi: {self.format_money(item['accounts']['card']['transfer_out'])}, Farq: {self.format_money(item['accounts']['card']['balance'])}",
            ])
            for label, tx_type in [('Top chiqim kategoriyalar:', 'expense'), ('Top kirim kategoriyalar:', 'income')]:
                breakdown = self.db.get_category_breakdown(start.isoformat(timespec='seconds'), end.isoformat(timespec='seconds'), tx_type, currency)
                if breakdown:
                    lines.append(label)
                    for category, total in breakdown[:5]:
                        lines.append(f"• {category}: {self.format_money(total)}")
        return '\n'.join(lines)

    async def recent_records(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self.require_owner(update):
            return
        rows = self.db.get_activity_page(limit=10, offset=0)
        if not rows:
            await update.message.reply_text('Hali yozuv yo‘q.', reply_markup=main_menu_keyboard())
            return
        lines = ['📋 Oxirgi 10 ta yozuv', '']
        for row in rows:
            timestamp = datetime.fromisoformat(row.created_at).astimezone(self.tz).strftime('%d.%m %H:%M')
            prefix = '🔄' if row.record_type == 'transfer' else ('🟢' if row.tx_type == 'income' else '🔴')
            lines.append(f"{prefix} {self.format_activity_short(row)} | {timestamp}")
            if row.note:
                lines.append(f"   Izoh: {row.note}")
        await update.message.reply_text('\n'.join(lines), reply_markup=main_menu_keyboard())

    def build_delete_keyboard(self, rows: list[ActivityRecord], offset: int, total: int) -> InlineKeyboardMarkup:
        keyboard = []
        for row in rows:
            prefix = '🔄' if row.record_type == 'transfer' else ('🟢' if row.tx_type == 'income' else '🔴')
            rec_short = 'tr' if row.record_type == 'transaction' else 'tf'
            keyboard.append([InlineKeyboardButton((f"{prefix} {self.format_activity_short(row)}")[:60], callback_data=f"del:{rec_short}:{row.id}:{offset}")])
        nav = []
        if offset > 0:
            nav.append(InlineKeyboardButton('⬅️ Oldingi', callback_data=f"page:{max(0, offset - DELETE_PAGE_SIZE)}"))
        if offset + DELETE_PAGE_SIZE < total:
            nav.append(InlineKeyboardButton('Keyingi ➡️', callback_data=f"page:{offset + DELETE_PAGE_SIZE}"))
        if nav:
            keyboard.append(nav)
        keyboard.append([InlineKeyboardButton('❌ Yopish', callback_data='delete_close')])
        return InlineKeyboardMarkup(keyboard)

    def build_delete_text(self, rows: list[ActivityRecord], offset: int, total: int) -> str:
        if not rows:
            return '🗑 O‘chirish uchun yozuv topilmadi.'
        lines = ['🗑 O‘chirish uchun yozuvni tanlang', '']
        for idx, row in enumerate(rows, start=offset + 1):
            prefix = '🔄' if row.record_type == 'transfer' else ('🟢' if row.tx_type == 'income' else '🔴')
            timestamp = datetime.fromisoformat(row.created_at).astimezone(self.tz).strftime('%d.%m %H:%M')
            lines.append(f"{idx}. {prefix} {self.format_activity_short(row)} | {timestamp}")
            if row.note:
                lines.append(f"   Izoh: {row.note}")
        total_pages = max(1, (total + DELETE_PAGE_SIZE - 1) // DELETE_PAGE_SIZE)
        lines.extend(['', f"Sahifa: {(offset // DELETE_PAGE_SIZE) + 1}/{total_pages}", 'Kerakli yozuvni pastdagi knopkadan tanlang.'])
        return '\n'.join(lines)

    async def show_delete_picker(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self.require_owner(update):
            return
        total = self.db.count_records()
        rows = self.db.get_activity_page(limit=DELETE_PAGE_SIZE, offset=0)
        await update.message.reply_text(self.build_delete_text(rows, 0, total), reply_markup=self.build_delete_keyboard(rows, 0, total) if rows else None)
        await update.message.reply_text('Bosh menyu.', reply_markup=main_menu_keyboard())

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
            total = self.db.count_records()
            if total > 0 and offset >= total:
                offset = max(0, ((total - 1) // DELETE_PAGE_SIZE) * DELETE_PAGE_SIZE)
            rows = self.db.get_activity_page(limit=DELETE_PAGE_SIZE, offset=offset)
            await query.edit_message_text(self.build_delete_text(rows, offset, total), reply_markup=self.build_delete_keyboard(rows, offset, total) if rows else None)
            return
        if data.startswith('del:'):
            await query.answer()
            parts = data.split(':')
            if len(parts) != 4:
                await query.edit_message_text('Xatolik yuz berdi.')
                return
            record_type = 'transaction' if parts[1] == 'tr' else 'transfer'
            try:
                record_id = int(parts[2])
                offset = max(0, int(parts[3]))
            except ValueError:
                await query.edit_message_text('Xatolik yuz berdi.')
                return
            deleted = self.db.delete_record_by_id(record_type, record_id)
            total = self.db.count_records()
            if total > 0 and offset >= total:
                offset = max(0, ((total - 1) // DELETE_PAGE_SIZE) * DELETE_PAGE_SIZE)
            rows = self.db.get_activity_page(limit=DELETE_PAGE_SIZE, offset=offset)
            text = ('✅ O‘chirildi: ' + self.format_activity_short(deleted) + '\n\n' if deleted else 'Bu yozuv topilmadi.\n\n') + self.build_delete_text(rows, offset, total)
            await query.edit_message_text(text, reply_markup=self.build_delete_keyboard(rows, offset, total) if rows else None)

    async def export_csv(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self.require_owner(update):
            return
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = str(Path(tmp_dir) / 'finance_history.csv')
            self.db.export_csv(path)
            with open(path, 'rb') as f:
                await update.message.reply_document(document=f, filename='finance_history.csv', caption='CSV tayyor.', reply_markup=main_menu_keyboard())

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        context.user_data.clear()
        if update.effective_message:
            await update.effective_message.reply_text('Amal bekor qilindi.', reply_markup=main_menu_keyboard())
        return ConversationHandler.END

    async def fallback_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self.require_owner(update):
            return
        await update.message.reply_text('Pastdagi knopkalardan foydalaning yoki /start bosing.', reply_markup=main_menu_keyboard())

    def build_app(self) -> Application:
        app = Application.builder().token(self.settings.bot_token).build()
        tx_conv = ConversationHandler(
            entry_points=[MessageHandler(filters.Regex(r"^➕ Kirim qo'shish$"), self.start_income), MessageHandler(filters.Regex(r"^➖ Chiqim qo'shish$"), self.start_expense)],
            states={
                TX_ACCOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.tx_receive_account)],
                TX_CURRENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.tx_receive_currency)],
                TX_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.tx_receive_amount)],
                TX_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.tx_receive_category)],
                TX_NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.tx_receive_note)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel), MessageHandler(filters.Regex(r'^⬅️ Bekor qilish$'), self.cancel)],
            allow_reentry=True,
        )
        transfer_conv = ConversationHandler(
            entry_points=[MessageHandler(filters.Regex(r'^🔄 Transfer$'), self.start_transfer)],
            states={
                TR_FROM_ACCOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.tr_receive_from_account)],
                TR_FROM_CURRENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.tr_receive_from_currency)],
                TR_TO_ACCOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.tr_receive_to_account)],
                TR_TO_CURRENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.tr_receive_to_currency)],
                TR_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.tr_receive_amount)],
                TR_NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.tr_receive_note)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel), MessageHandler(filters.Regex(r'^⬅️ Bekor qilish$'), self.cancel)],
            allow_reentry=True,
        )
        app.add_handler(CommandHandler('start', self.start))
        app.add_handler(CommandHandler('help', self.help_command))
        app.add_handler(tx_conv)
        app.add_handler(transfer_conv)
        app.add_handler(MessageHandler(filters.Regex(r'^💰 Balans$'), self.show_balance))
        app.add_handler(MessageHandler(filters.Regex(r'^📊 Bugungi hisobot$'), self.today_report))
        app.add_handler(MessageHandler(filters.Regex(r'^🗓 Oylik hisobot$'), self.month_report))
        app.add_handler(MessageHandler(filters.Regex(r'^📋 Oxirgi yozuvlar$'), self.recent_records))
        app.add_handler(MessageHandler(filters.Regex(r"^🗑 Yozuvni o'chirish$"), self.show_delete_picker))
        app.add_handler(CallbackQueryHandler(self.handle_delete_callback, pattern=r'^(page:\d+|del:(tr|tf):\d+:\d+|delete_close)$'))
        app.add_handler(MessageHandler(filters.Regex(r'^⬇️ CSV yuklab olish$'), self.export_csv))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.fallback_text))
        return app

    def run(self) -> None:
        app = self.build_app()
        logger.info('Finance bot ishga tushmoqda...')
        app.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    FinanceBot().run()
