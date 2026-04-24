import datetime
from odoo import fields, api, models, _
from odoo.exceptions import ValidationError
from dateutil import relativedelta
from datetime import date
import datetime

class CreateBankLettersWizard(models.TransientModel):
    _inherit = "create.bank.letters.wizard"
   
    bank_id = fields.Many2one('bank.list', string="From Bank Account",)