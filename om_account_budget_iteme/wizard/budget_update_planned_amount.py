# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.fields import Date
from datetime import datetime

from dateutil.relativedelta import relativedelta


class BudgetUpdateAmount(models.TransientModel):
    _name = "update.amount.wizard"
    account_id = fields.Many2one('account.account', string='account', readonly=True)
    currency_id = fields.Many2one('res.currency', string="Currency",
                                  default=lambda self: self.env['res.currency'].search([('name', '=', 'USD')], limit=1),
                                  readonly=False)
    planned_amount = fields.Monetary(
        'Planned Amount', readonly=True)
    new_amount = fields.Monetary(
        'Amount', required=True)
    theoritical_amount = fields.Monetary(
        'theoritical_amount', required=True)
    new_planned_amount = fields.Monetary(
        'New Amount', store=True, compute='_compute_update_planned_amount', tracking=4)

    @api.depends('new_amount')
    def _compute_update_planned_amount(self):
        for order in self:
            if order.new_amount > 0.0:
                order.new_planned_amount = (order.planned_amount + order.new_amount)
            elif order.new_amount <= 0.0:
                order.new_planned_amount = (order.planned_amount + order.new_amount)

    def action_applay(self):
        model = self.env.context.get('active_model')
        obj = self.env[model].browse(self.env.context.get('active_ids', []))
        if obj:
            if self.theoritical_amount >  self.new_planned_amount:
                raise UserError(_('Please review the values  entered and ensure that the amount to be deducted is less than or equal to the total available.'))
            else:
                obj.write({
                    'budget_line_planned_amount': self.new_planned_amount
                })
