from odoo import models, fields, api, _
from datetime import date
import datetime
from odoo.exceptions import UserError, ValidationError

class AccountPaymentInherit(models.Model):
    _inherit = 'account.payment'

    bank_transfer_ref = fields.Char(string="Bank Transfer Reference")
    project_id = fields.Many2one('project.project', string="Project")
