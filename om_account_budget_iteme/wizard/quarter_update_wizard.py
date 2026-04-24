from odoo import api, fields, models, _
from datetime import datetime

class QuarterUpdateWizard(models.TransientModel):
    _name = 'quarter.update.wizard'
    _description = "Quarter Update Wizard"

    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account', readonly=True)
    planned_amount = fields.Float(string="Planned Amount", readonly=True)
    new_amount = fields.Float(string="New Amount", compute="_compute_new_amount", store=True)
    amount = fields.Float(string="Amount")
    crossovered_budget_id = fields.Many2one('crossovered.budget.lines', string="Crossovered Budget#")
    quarter_id = fields.Many2one('budget.quarte.line', 'Quarter Line#')
    quarter_type = fields.Selection([
        ('basic_quarter', 'Basic'),
        ('quarter_plan', 'Plan'),
    ], string='Quarter Type', readonly=True)

    @api.depends('planned_amount', 'amount')
    def _compute_new_amount(self):
        for record in self:
            if record.planned_amount:
                record.new_amount = record.amount + record.planned_amount
            elif record.planned_amount == 0:
                record.new_amount = record.amount + record.planned_amount

    def action_validate(self):
        for rec in self:
            if rec.quarter_type == "quarter_plan":
                rec.quarter_id.planned_amount = rec.new_amount
            elif rec.quarter_type == 'basic_quarter':
                rec.crossovered_budget_id.planned_amount = rec.new_amount