# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from dateutil import relativedelta
from datetime import date
import datetime


class BidAnalysisTender(models.Model):
    _name = 'oms.bid.tender.conf'
    _description = 'OMS Bid Analysis Tender Configuration'

    name = fields.Char(string="Name", required=True)
    operation_type = fields.Selection([
        ('bid_analysis', 'Bid Analysis'),
        ('tender', 'Open Tender'),
    ], string="Operation Type", required=True, tracking=True,)
    amount = fields.Float(string="Amount")
    currency_id = fields.Many2one('res.currency', string="Currency", default=lambda self: self.env['res.currency'].search([('name', '=', 'USD')], limit=1))

    @api.constrains('amount')
    def _check_amount(self):
        for record in self:
            if record.amount == 0:
                raise ValidationError(_("The amount cannot be zero. Please provide a valid amount."))