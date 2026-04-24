from odoo import api, fields, models, _
from datetime import datetime
from datetime import date


class CustodyReport(models.TransientModel):
    _name = 'expense.custody.report'
    _description = "Print Expense Custody Report"

    account_id = fields.Many2one('account.account', string="Account", required=True)
    journal_ids = fields.Many2many('account.journal', string="Journal", required=True)
    date_from = fields.Date(string="Date From")
    date_to = fields.Date(string="Date To")
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company.id
    )
    date = fields.Date(string="Created Date", default=fields.Date.context_today)
    signature_reviewed = fields.Many2one('res.users', string="Reviewed By", required=True)
    signature_approved = fields.Many2one('res.users', string="Approved By", required=True)
    signature_prepared = fields.Many2one('res.users', string="Prepared By", required=True)

    def action_print_report(self):
        for rec in self:
            domain = []
            report_data = []
            authorized_data = []
            running_balance = 0
            authorized_data.append({
                'date': rec.date,
                'prepared': rec.signature_prepared.name,
                'reviewed': rec.signature_reviewed.name,
                'approved': rec.signature_approved.name,
                'signature_reviewed': rec.signature_reviewed.digital_signature,
                'signature_approved': rec.signature_approved.digital_signature,
                'signature_prepared': rec.signature_prepared.digital_signature,
            })
            if rec.date_from:
                domain.append(('date', '>=', rec.date_from))
            if rec.date_to:
                domain.append(('date', '<=', rec.date_to))

            account_move_line = self.env['account.move.line'].search([
                ('account_id', '=', rec.account_id.id),
                ('move_type', '=', 'entry'),
                ('journal_id', 'in', rec.journal_ids.ids),
                *domain,
            ], order='date asc')

            if account_move_line:
                for item in account_move_line:
                    running_balance += item.debit
                    running_balance -= item.credit

                    report_data.append({
                        'date': item.date,
                        'company_name': rec.company_id.name,
                        'partner': item.partner_id.name,
                        'reference': item.ref or item.name,
                        'debit': item.debit,
                        'credit': item.credit,
                        'balance': running_balance,
                        'journal': item.journal_id.name,
                        'label': item.name,
                    })

            vals = {
                "authorized": authorized_data,
                "data": report_data,
                "domain": domain,
                'total_balance': running_balance,
            }
            return self.env.ref('expense.print_expense_custody_reports').report_action(self, data=vals)
