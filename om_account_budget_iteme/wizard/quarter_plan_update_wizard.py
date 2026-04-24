from odoo import api, fields, models, _
from datetime import datetime

class QuarterPlansUpdateWizard(models.TransientModel):
    _name = 'quarter.plan.update.wizard'
    _description = "Quarter Plans  Update Wizard"

    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account', readonly=True)
    planned_amount = fields.Float(string="Planned ", readonly=True)
    remaining_amount = fields.Float(string="Remaining", readonly=True)

    new_amount = fields.Float(string="New Amount", compute="_compute_new_amount", store=True)
    amount = fields.Float(string="Amount")

    @api.depends('planned_amount', 'amount')
    def _compute_new_amount(self):
        for record in self:
            if record.planned_amount:
                record.new_amount = record.amount + record.planned_amount

    def action_validate(self):
        pass
        # for rec in self:
        #     rec.crossovered_budget_id.planned_amount = rec.new_amount