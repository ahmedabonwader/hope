from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import ValidationError
import datetime
from datetime import date


class OMSOperationPerson(models.Model):
    _name = 'oms.operation.person'
    _description = 'Operation Person'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'user_id'
    _order = 'id desc'

    user_id = fields.Many2one('res.users', string="User")
    expense_department = fields.Selection([
        ('finance_expense', 'Finance'),
        ('hr_expense', 'HR'),
        ('hybird', 'Hybird'),
    ], steing="Operation Department",)