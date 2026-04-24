from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import ValidationError
import datetime


class OMSAdvanceLoanConf(models.Model):
    _name = 'oms.advance.loan.conf'
    _description = 'OMS Advance Loan Conf'
    _order = 'id desc'

    name = fields.Char(string="Name", required=True)
    operation_type = fields.Selection([
        ('advance', 'Advance'),
        ('loan', 'Loan'),
    ], string="Operation Type", required=True)
    maximum_percentage = fields.Float(string="Maximum Percentage")

    @api.constrains('maximum_percentage')
    def _check_maximum_percentage(self):
        for rec in self:
            if rec.maximum_percentage == 0:
                raise ValidationError("⛔ The Maximum Percentage must be greater than 0.")