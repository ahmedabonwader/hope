from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    project_id = fields.Many2one(related='move_id.project_id', string="project")
    budget_item_line_id = fields.Many2one(
        'budget.iteme.line',
        string='Budget Code',
        domain="[('account_id', '=', account_id),('budget_iteme_id.state', '=', 'validate'), ('budget_iteme_id.project_id', '=', project_id)]"
    )
    quarter_id = fields.Many2one(
        'crossovered.budget.lines',
        string='Quarter',
    )
    check_quarter = fields.Boolean(string="Check Quarter", compute="_compute_check_quarter")

    # price_subtotal = fields.Monetary(string="Amount", compute="_compute_price_subtotal", store=True,)

    # @api.depends('frequency', 'price_unit', 'quantity')
    # def _compute_price_subtotal(self):
    #     for rec in self:
    #         frequency = rec.frequency or 1.0
    #         quantity = rec.quantity or 1.0
    #         price_unit = rec.price_unit or 0.0
    #         rec.price_subtotal = price_unit * quantity * frequency

    @api.depends('project_id')
    def _compute_check_quarter(self):
        for rec in self:
            if rec.project_id:
                rec.check_quarter = True
            elif not rec.project_id:
                rec.check_quarter = False