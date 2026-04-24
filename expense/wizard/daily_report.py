from odoo import api, fields, models, _
from datetime import datetime


class DailyExpenseReport(models.TransientModel):
    _name = 'daily.expense.report'
    _description = "Print Expense Daily Report"

    date_from = fields.Date(string="Date From")
    date_to = fields.Date(string="Date To")
    report_type = fields.Selection([
        ('expense', 'Expense'),
        # ('salary', 'Salary'),
        ('loan', 'Loan'),
    ], string="Report Type", required=True, default="expense")
    user_id = fields.Many2one('res.users', string="Operation Person")
    employee_ids = fields.Many2many('hr.employee', string="Employee")
    allowed_user_ids = fields.Many2many(
        'res.users',
        store=True,
        string='Allowed Users',
    )

    @api.onchange('user_id')
    def onchange_allowed_users(self):
        for wizard in self:
            # اجلب كل user_id الفريدة دفعة واحدة
            user_ids = self.env['hms.expense.request'].search([]).mapped('user_id.id')
            print("User IDs: ", user_ids)  # طباعة للتأكد من القيم
            wizard.allowed_user_ids = [(6, 0, user_ids)]

    def action_print_report(self):
        for rec in self:
            domain = []
            report_data = {}

            # إضافة شرط التواريخ
            if rec.date_from:
                domain.append(('time', '>=', rec.date_from))
            if rec.date_to:
                domain.append(('time', '<=', rec.date_to))

            if rec.report_type == 'expense':
                domain += [
                    ('state', '=', 'done'),
                    ('payment_status', '=', 'paid'),
                    ('expense_type', '=', 'expense'),
                ]

                # فلترة حسب المستخدم إذا تم تحديده
                if rec.user_id:
                    domain.append(('user_id', '=', rec.user_id.id))

                expenses = self.env['hms.expense.request'].search(domain)

                report_data = [{
                    'description': exp.description,
                    'date': exp.time,
                    'recipient': exp.partner_id.name,
                    'user': exp.user_id.name,
                    'amount': line.total_amount,
                    'payment_method': exp.payment_method.name,
                } for exp in expenses for line in exp.expense_line_ids]

            elif rec.report_type in ['salary', 'loan']:
                expense_type = 'salary' if rec.report_type == 'salary' else 'loan'
                domain += [('state', '=', 'done'), ('expense_type', '=', expense_type)]

                records = self.env['hms.expense.request'].search(domain)

                for record in records:
                    employee_name = record.employee_id.name or "Unknown"
                    if rec.employee_ids and record.employee_id not in rec.employee_ids:
                        continue  # تخطي الموظفين غير المختارين

                    if employee_name not in report_data:
                        report_data[employee_name] = []

                    report_data[employee_name].append({
                        'description': record.expense.name,
                        'date': record.time,
                        'payment_status': record.payment_status,
                        'user': record.user_id.name,
                        'amount': record.amount,
                        'payment_method': record.payment_method.type,
                    })

            # إرسال البيانات إلى التقرير
            vals = {
                "data": report_data,
                "domain": domain,
                "form_data": self.read()[0],
            }
            return self.env.ref('expense.expense_payment_daily_reports').report_action(self, data=vals)
