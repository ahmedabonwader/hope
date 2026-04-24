from odoo import api, fields, models, _
from datetime import datetime


class BudgetReportWizard(models.TransientModel):
    _name = 'budget.report.wizard'
    _description = "Budget Report Wizard"

    budget_id = fields.Many2one('crossovered.budget', string="Budget", required=True)
    budget_state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('validate', 'Validated'),
        ('done', 'Done'),
    ], string="Budget State", default="validate")
    date_from = fields.Date(string="Date From")
    date_to = fields.Date(string="Date To")

    def _prepare_report_data(self):
        # Initialize variables
        report_data = []
        domain = []
        form_data = self.read()[0]

        # Build domain for account.move.line
        if self.date_from:
            domain += [('invoice_date', '>=', self.date_from)]
        if self.date_to:
            domain += [('invoice_date', '<=', self.date_to)]

        # Get analytic accounts from selected budget lines
        analytic_accounts = self.env['crossovered.budget.lines'].search([
            ('crossovered_budget_id', '=', self.budget_id.id),
            ('date_from', '>=', self.date_from),
            ('date_to', '<=', self.date_to)
        ]).mapped('analytic_account_id')

        # Add analytic distribution filter
        domain += [('analytic_distribution', 'in', analytic_accounts.ids)]

        # Search account move lines
        move_lines = self.env['account.move.line'].search(domain, order='invoice_date asc')

        # Calculate cumulative balance
        cumulative_balance = 0.0
        transaction_counter = 1

        for line in move_lines:
            # Get budget line code
            budget_item = self.env['budget.iteme.line'].search([
                ('account_id', '=', line.account_id.id)
            ], limit=1)
            line_code = budget_item.line_code if budget_item else ''

            # Calculate amounts
            debit = line.debit
            credit = line.credit
            balance = debit - credit
            cumulative_balance += balance

            # Prepare report line
            report_line = {
                'transaction_no': transaction_counter,
                'voucher_no': line.move_id.ref or '',
                'date': line.invoice_date,
                'payee': line.partner_id.name,
                'transaction_details': line.name,
                'credit_sdg': credit,
                'debit_sdg': debit,
                'balance_sdg': cumulative_balance,
                'amount_usd': line.amount_currency,
                'line_code': line_code
            }

            report_data.append(report_line)
            transaction_counter += 1

        # Prepare data for report
        report_values = {
            'report_data': report_data,
            'form_data': form_data,
            'exchange_rate': 1226.95  # Replace with dynamic calculation
        }
        return report_values

    def action_print(self):
        for rec in self:
            report_values = rec._prepare_report_data()

            # Return report action
            return self.env.ref('accounting_report.action_report_views').report_action(self, data=report_values)


    def action_print_excel(self):
        return {
            'type': 'ir.actions.act_url',
            'url': f'/export/budget_report_excel?wizard_id={self.id}',
            'target': 'self',
        }