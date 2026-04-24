from odoo import api, fields, models , _
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError, ValidationError




class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'
    _description = "register wizard"



    def action_create_payments(self):
        res = super(AccountPaymentRegister, self).action_create_payments()
        move_ids = self.env['account.move'].browse(self.env.context.get('active_id'))
        if move_ids:
            move_ids.write({'pay_state':True})
        return  res
