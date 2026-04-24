import datetime
from odoo import fields, api, models, _
from odoo.exceptions import ValidationError
from dateutil import relativedelta
from datetime import date
import datetime
from deep_translator import GoogleTranslator

class CreateBankLettersWizard(models.TransientModel):
    _name = "create.bank.letters.wizard"
    _description = "Create Bank Letters Wizard"

    batches_id = fields.Many2one('payslips.batches', string="Payslip Batches")
    date = fields.Date(string="Date")
    amount = fields.Float(string="Amount")
    currency_id = fields.Many2one('res.currency', string="Currency")
    project_id = fields.Many2one('project.project', string="Project")
    
    bank_branch = fields.Char(string="Bank Branch")
    bank_name_letter = fields.Char(string="The letter is addressed to the bank",)
    bank = fields.Selection([
        ('bok', 'Bank Of Khartoum'),
        ('bnmb', 'Blue Nile Masherg Bank'),
    ], string="Bank", )
    budget_code = fields.Many2one(
        'budget.iteme.line',
        string='Budget Code',
        
        domain="[('budget_iteme_id.project_id', '=', project_id)]"
    )
    payment_number = fields.Char(string="Payment Number")

    def action_validate(self):
        for rec in self:
            vals = {
                'description': rec.batches_id.name,
                'bank_name_letter': rec.bank_name_letter,
                'bank_letters_type': 'salary_letters',
                'salary_id': rec.batches_id.id,
                'bank_id_account_from': rec.bank_id.id,
                'project_id': rec.project_id.id,
                'amount': rec.amount,
                'budget_line_code': rec.budget_code.id,
                'payment_number': rec.payment_number,
                'bank': rec.bank,
                'bank_branch': rec.bank_branch,
                'month_type': 'one_month',
                'month_date': rec.date,
            }
            letters = self.env['bank.letters'].create(vals)
            
            # إعداد المترجم من الإنجليزية إلى العربية
            translator = GoogleTranslator(source='en', target='ar')

            for line in rec.batches_id.bank_account_line_ids:
                # ترجمة اسم الموظف
                original_name = line.employee_id.name
                try:
                    translated_name = translator.translate(original_name)
                except Exception:
                    translated_name = original_name  # في حال فشل الاتصال بالإنترنت نستخدم الاسم الأصلي

                line_vals = {
                    'bank_letters_id': letters.id,
                    'employee': translated_name, # الاسم المترجم
                    'bank_name': line.bank_account_id.bank_name_arabic,
                    'branch': line.branch,
                    'account_number': line.bank_account_id.acc_number,
                    'amount': line.amount,
                }
                self.env['bank.letters.line'].create(line_vals)

            rec.batches_id.letter_created = True