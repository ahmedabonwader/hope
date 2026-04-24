from odoo import api, fields, models, _
from datetime import datetime


class SelectContractWizardExpense(models.TransientModel):
    _name = 'select.contract.wizard'
    _description = "Select Contract Wizard"

    employee_id = fields.Many2one('hr.employee', string="Employee")
    contract_id = fields.Many2one('contract.line', string='Contract')
    expense_type = fields.Selection([
        ('expense', 'Expense'),
        ('advance', 'Advance'),
        ('loan', 'Loan'),
    ], default="expense", string="Expense Type", readonly=True)
    contract_type = fields.Selection([
        ('project', 'By Project'),
        ('contract', 'By Contract'),
        ('hybrid', 'Hybrid'),
    ], string="Contract Format Type")
    expense_id = fields.Many2one('hms.expense.request', string="Expense")    

    def action_validate(self):
        for rec in self:
            if rec.contract_id:
                if rec.expense_type == 'loan':
                    for line in rec.contract_id:
                        line.loan_subtract = True
                elif rec.expense_type == 'advance':
                    for line in rec.contract_id:
                        line.advance_subtract = True
            rec.expense_id.check_contract = True
            rec.expense_id.check_invisible_confirm_button = False
            rec.expense_id.project_select = rec.contract_id.project_id.id