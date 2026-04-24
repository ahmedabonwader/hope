from odoo import models, fields, api
from datetime import date
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from dateutil import relativedelta
from datetime import date
import datetime
from deep_translator import GoogleTranslator
from babel.dates import format_date


class BankLitters(models.Model):
    _name = 'bank.letters'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Bank Litters'
    _rec_name = 'description'
    _order = 'id desc'

    description = fields.Char(string="Description", required=True, tracking=True)
    bank = fields.Selection([
        ('bok', 'Bank Of Khartoum'),
        ('bnmb', 'Blue Nile Masherg Bank'),
    ], string="Bank", required=True, tracking=True)
    bank_name_letter = fields.Char(string="The letter is addressed to the bank", required=True, tracking=True)
    bank_branch = fields.Char(string="Bank Branch", tracking=True)
    bank_letters_type = fields.Selection([
        ('internal_transfer', 'Internal Transfer'),
        ('salary_letters', 'Salary Letters'),
        ('normal_letters', 'Normal Letters')
    ], string="Bank Letters Type", required=True, tracking=True)
    received_by = fields.Selection([
        ('vendor', 'Vendor'),
        ('employee', 'Employee'),
    ], string="Received By", tracking=True)
    partner_id = fields.Many2one('res.partner', string='Vendor', tracking=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", tracking=True)
    the_authorized_person = fields.Char(string="The Authorized Person", tracking=True)
    id_number = fields.Char(string="Id Number", tracking=True)
    phone_numer = fields.Char(string="Phone Number", tracking=True)
    bank_id_account_from = fields.Many2one('bank.list', string="From Bank Account", required=True, tracking=True)
    bank_id_account_to = fields.Many2one('bank.list', string="To Bank Account", tracking=True)
    bank_name_from = fields.Char(string="Bank Name", related="bank_id_account_from.bank_name", tracking=True)
    branch_from = fields.Char(string="Branch", related="bank_id_account_from.branch", tracking=True)
    bank_name_to = fields.Char(string="Bank Name", tracking=True)
    branch_to = fields.Char(string="Branch", tracking=True)
    number_from = fields.Char(string="Account Number", related="bank_id_account_from.number", tracking=True)
    number_to = fields.Char(string="Account Number", tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('post', 'Approved'),
        ('cancel', 'Cancel'),
    ], default="draft", string="State", tracking=True)
    amount = fields.Float(string="Amount", tracking=True)
    month_type = fields.Selection([
        ('multi_month', 'Multi Month'),
        ('one_month', 'One Month'),
    ], string="Month Type", default="one_month", tracking=True)
    ref = fields.Char(string='Reference', tracking=True)
    user_id = fields.Many2one('res.users', String="User", tracking=True, readonly=True,
                              default=lambda self: self.env.user.id)
    date = fields.Date(string="Date", default=fields.Date.context_today, tracking=True)
    date_from = fields.Date(string="Date From", tracking=True)
    month_date = fields.Date(string="Month Date", tracking=True)
    date_to = fields.Date(string="Date To", tracking=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, readonly=True)
    currency_id = fields.Many2one('res.currency', string="Currency", tracking=True,
                                  default=lambda self: self.env['res.currency'].search([('name', '=', 'SDG')], limit=1))
    bank_letters_line_ids = fields.One2many('bank.letters.line', 'bank_letters_id', string="Bank Line", tracking=True)

    amount_in_words = fields.Char(String="Amount in words", compute="_compute_amount_total_words", store=True, tracking=True)
    line_total_amount = fields.Float(string="Line Total Amount", compute="_compute_line_total_amount", tracking=True, store=True)
    project_id = fields.Many2one('project.project', string="Project", required=True, tracking=True, domain="[('state', '=', 'running')]")
    budget_line_code = fields.Many2one('budget.iteme.line', string="Budget Line", required=True, tracking=True)
    payment_number = fields.Char(string="Payment Number", tracking=True)
    bill_id = fields.Many2one('account.move', string="Bill")
    salary_id = fields.Many2one('payslips.batches', string="Payslips Salary")
    received_name_in_arabic = fields.Char(string="The Receved Name In Arabic")
    bank_account_id = fields.Many2one('res.partner.bank', string="Receive Bank Account", compute="_compute_bank_account_id", store=True,)

    @api.depends('received_by', 'partner_id', 'employee_id', 'bank_id_account_to')
    def _compute_bank_account_id(self):
        for rec in self:
            rec.bank_account_id = False
            if rec.bank_letters_type == 'normal_letters':
                if rec.received_by == 'vendor' and rec.partner_id:
                    bank_account = self.env['res.partner.bank'].search(
                        [('partner_id', '=', rec.partner_id.id)],
                        limit=1
                    )
                    rec.bank_account_id = bank_account
                    rec.bank_name_to = bank_account.bank_name_arabic
                    rec.branch_to = bank_account.bank_branch
                    rec.number_to = bank_account.acc_number
                    rec.received_name_in_arabic = bank_account.holder_arabic_name
                elif rec.received_by == 'employee' and rec.employee_id:
                    rec.bank_account_id = rec.employee_id.bank_account_id.id
                    rec.bank_name_to = rec.employee_id.bank_account_id.bank_name_arabic
                    rec.branch_to = rec.employee_id.bank_account_id.bank_branch
                    rec.number_to = rec.employee_id.bank_account_id.acc_number
            elif rec.bank_letters_type == 'internal_transfer':
                rec.bank_name_to = rec.bank_id_account_to.bank_name
                rec.branch_to = rec.bank_id_account_to.branch
                rec.number_to = rec.bank_id_account_to.number


    @api.depends('bank_letters_line_ids')
    def _compute_line_total_amount(self):
        for rec in self:
            total = 0
            for line in rec.bank_letters_line_ids:
                total += line.amount
                rec.line_total_amount = total

    @api.depends("amount", "currency_id")
    def _compute_amount_total_words(self):
        for rec in self:
            rec.amount_in_words = rec.currency_id.with_context(lang='ar_001').amount_to_text(rec.amount).replace(',', '')

    def get_month_name_ar(self, date, with_year=False):
        if date:
            if with_year:
                return format_date(date, format='MMMM y', locale='ar')  # مثال: نوفمبر 2025
            return format_date(date, format='MMMM', locale='ar')  # مثال: نوفمبر
        return ''

    @api.model
    def create(self, vals):
        vals['ref'] = self.env['ir.sequence'].next_by_code('bank.letters')
        return super(BankLitters, self).create(vals)

    def write(self, vals):
        if not self.ref:
            vals['ref'] = self.env['ir.sequence'].next_by_code('bank.letters')
        return super(BankLitters, self).write(vals)

    def action_post(self):
        for rec in self:
            if rec.amount == 0:
                raise ValidationError(_('The Amount can not be zero !!!'))
            if rec.bank_letters_type == 'salary_letters' and len(rec.bank_letters_line_ids) < 1:
                raise ValidationError(_('Add Information off Employees Salary in Line'))
            for line in rec.bank_letters_line_ids:
                if line.amount == 0:
                    raise ValidationError(_('The Amount can not be zero !!!'))
            rec.state = 'post'

    def action_reset_to_draft(self):
        for rec in self:
            rec.state = 'draft'

    def action_confirm(self):
        # إعداد المترجم من الإنجليزية إلى العربية
        translator = GoogleTranslator(source='en', target='ar')
        
        for rec in self:
            name_to_translate = ""
            
            # # 1. تحديد الاسم المطلوب ترجمته بناءً على نوع المستلم
            # if rec.received_by == 'vendor' and rec.partner_id:
            #     name_to_translate = rec.partner_id.name
            if rec.received_by == 'employee' and rec.employee_id:
                name_to_translate = rec.employee_id.name
            
            # 2. تنفيذ عملية الترجمة
            if name_to_translate:
                try:
                    # نرسل الاسم للمترجم
                    translated_name = translator.translate(name_to_translate)
                    rec.received_name_in_arabic = translated_name
                except Exception as e:
                    # في حال فشل الاتصال بالإنترنت أو أي خطأ آخر، نضع الاسم الأصلي مؤقتاً
                    rec.received_name_in_arabic = name_to_translate
            
            # 3. تحديث حالة السجل
            rec.state = 'confirm'

    def action_print(self):
        action = self.env.ref('inherit_account_move.action_bank_letters_report_print').read()[0]
        return action


class BankLettersLine(models.Model):
    _name = 'bank.letters.line'
    _description = 'Bank Letters Line'

    bank_letters_id = fields.Many2one('bank.letters', string="Bank Letters")
    currency_id = fields.Many2one(related="bank_letters_id.currency_id", string="Currency")
    employee_id = fields.Many2one('hr.employee', string="Employee")
    employee = fields.Char(string="Employee")
    bank_name = fields.Char(string="Bank Name")
    branch = fields.Char(string="Branch")
    account_number = fields.Char(string="Account Number")
    amount = fields.Float(string="Amount")
    s = fields.Char()


class BankList(models.Model):
    _name = 'bank.list'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Bank List'
    _rec_name = 'name'

    name = fields.Char(string="Name")
    branch = fields.Char(string="Branch")
    number = fields.Char(string="Number")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('suspend', 'Suspended'),
        ('close', 'Closed'),
    ], string="State", default="draft")
    ref = fields.Char(string='Reference', tracking=True)
    date = fields.Date(string="Date", default=fields.Date.context_today)
    bank_name = fields.Char(string="Bank Name")

    @api.model
    def create(self, vals):
        vals['ref'] = self.env['ir.sequence'].next_by_code('bank.letters')
        return super(BankList, self).create(vals)

    def write(self, vals):
        if not self.ref:
            vals['ref'] = self.env['ir.sequence'].next_by_code('bank.letters')
        return super(BankList, self).write(vals)

    def action_active(self):
        for rec in self:
            rec.state = 'active'

    def action_suspend(self):
        for rec in self:
            rec.state = 'suspend'

    def action_close(self):
        for rec in self:
            rec.state = 'close'

    def action_reset_to_draft(self):
        for rec in self:
            rec.state = 'draft'
