from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import date
import datetime


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'
    _description = "register wizard"

    @api.model
    def default_get(self, fields):
        res = super(AccountPaymentRegister, self).default_get(fields)
        # res['move_id'] = self.env.context.get('active_id')
        active_id = self._context.get('active_id')
        brw_id = self.env['account.move'].browse(int(active_id))

        if active_id:
            res['expense_id'] = brw_id.expense_id.id
            res['salary_payslips_id'] = brw_id.salary_payslips_id.id
            res['bill_type'] = brw_id.bill_type
            res['project_id'] = brw_id.project_id.id
            res['move_id'] = brw_id.id
        return res

    expense_id = fields.Many2one('hms.expense.request', 'Expense')
    salary_payslips_id = fields.Many2one('payslips.batches', string="Salary Payslips")
    move_id = fields.Many2one('account.move', string="Move ID", tracking=True, readonly=True)
    bank_transfer_ref = fields.Char(string="Bank Transfer Reference")
    project_id = fields.Many2one('project.project', string="Project")
    journal_id = fields.Many2one('account.journal', string="Journal",
                                 domain="[('type', 'in', ('bank','cash')), ('user_id', '=', uid)]")
    bill_type = fields.Selection([
        ('normal', 'Normal'),
        ('purchase', 'Purchase'),
        ('salary', 'Salary'),
        ('tor', 'TOR'),
    ], string="Bill Type")

    # This Function create and write values of specific field to another model
    def action_create_payments(self):
        res = super(AccountPaymentRegister, self).action_create_payments()
        for rec in self:
            account_payment = self.env['account.payment'].search([])
            for payment in account_payment:
                if payment.memo == rec.communication:
                    payment.bank_transfer_ref = rec.bank_transfer_ref
                    rec.move_id.bank_transfer_ref = rec.bank_transfer_ref
                    payment.project_id = rec.project_id.id
                    if payment.move_id and payment.move_id.move_type == 'entry':
                        payment.move_id.project_id = rec.project_id.id or rec.move_id.project_id.id

            rec.expense_id.payment_status = 'paid'
            rec.expense_id.payment_method = rec.journal_id.id

            hr_contract = self.env['hr.contract'].search([
                ('employee_id', '=', rec.expense_id.employee_id.id),
                ('state', '=', 'open'),
                ('contract_type', 'in', ('project', 'hybrid')),
            ], limit=1)
            if hr_contract:
                for contract in hr_contract:
                    for line in contract.contract_line_ids:
                        if line.state == 'run':
                            rec.project_id = line.project_id.id
            if rec.expense_id.expense_type == 'advance':
                advance_vals = {
                    'operation_type': 'advance',
                    'date': datetime.date.today(),
                    'payment_method': rec.journal_id.id,
                    'amount': rec.amount,
                    'rate': rec.expense_id.rate,
                    'currency_id': rec.currency_id.id,
                    'project_id': rec.expense_id.project_select.id,
                    'employee_id': rec.expense_id.employee_id.id,
                    'contract_type': rec.expense_id.contract_type,
                }
                advance_payment = self.env['hms.expense.request.advance.line'].create(advance_vals)

            elif rec.expense_id.expense_type == 'loan':
                loan_vals = {
                    'operation_type': 'loan',
                    'date': datetime.date.today(),
                    'payment_method': rec.journal_id.id,
                    'amount': rec.amount,
                    'rate': rec.expense_id.rate,
                    'deduct': rec.expense_id.how_much_deduct,
                    'currency_id': rec.currency_id.id,
                    'loan_duration': rec.expense_id.loan_duration,
                    'project_id': rec.expense_id.project_select.id,
                    'employee_id': rec.expense_id.employee_id.id,
                    'contract_type': rec.expense_id.contract_type,
                }
                loan_payment = self.env['hms.expense.request.loan.line'].create(loan_vals)

            if rec.bill_type == 'salary':
                for emp_id in rec.move_id.salary_payslips_id:
                    for line in emp_id.batches_line_ids:
                        salary_vals = {
                            'operation_type': 'salary',
                            'date': rec.move_id.invoice_date,
                            'payment_method': rec.journal_id.id,
                            'amount': rec.amount,
                            'employee_id': line.employee_id.id,
                        }
                        salary_payment = self.env['hms.expense.request.salary.line'].create(salary_vals)
                emp_loan = self.env['hms.expense.request.loan.line'].search([
                    ('operation_type', '=', 'loan'),
                    ('check_loan', '=', True),
                    ('employee_id', 'ilike', rec.move_id.partner_id.name),
                ], limit=1)
                if emp_loan:
                    for emp_id in emp_loan:
                        # emp_id.loan_count = emp_id.loan_count + 1
                        if emp_id.loan_count == emp_id.loan_duration:
                            contract = self.env['hr.contract'].search([
                                ('employee_id', 'ilike', rec.move_id.partner_id.name),
                                ('state', '=', 'open'),
                                ('contract_type', 'in', ('project', 'hybrid')),
                            ], limit=1)
                            if contract:
                                for contract_id in contract:
                                    for line in contract_id.contract_line_ids:
                                        if line.loan_subtract == True:
                                            line.loan_subtract = False
                emp_advance = self.env['hms.expense.request.advance.line'].search([
                    ('operation_type', '=', 'advance'),
                    ('check_advance', '=', True),
                    ('employee_id', 'ilike', rec.move_id.partner_id.name),
                ], limit=1)
                if emp_advance:
                    for emp_id in emp_advance:
                        # emp_id.advance_count = emp_id.advance_count + 1

                        if emp_id.advance_count == emp_id.advance_duration:
                            contract = self.env['hr.contract'].search([
                                ('employee_id', 'ilike', rec.move_id.partner_id.name),
                                ('state', '=', 'open'),
                                ('contract_type', 'in', ('project', 'hybrid')),
                            ], limit=1)
                            for contract_id in contract:
                                for line in contract_id.contract_line_ids:
                                    if line.advance_subtract == True:
                                        line.advance_subtract = False
            elif rec.bill_type == 'tor':
                for tor_advance in rec.move_id.tor_advance_id:
                    if tor_advance.request_type == 'tor_advance':
                        tor_advance.payment_status = rec.move_id.payment_state
            elif rec.bill_type == 'purchase':
                for prs in rec.move_id.prs:
                    if prs.request_type == 'purchase_request':
                        prs.payment_status = rec.move_id.payment_state
        return res
