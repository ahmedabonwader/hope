from odoo import api, fields, models, _
from datetime import datetime


class AuthorizedWizard(models.TransientModel):
    _name = 'authorized.wizard'
    _description = "Authorized Wizard"

    # @api.model
    # def default_get(self, fields):
    #     res = super(AuthorizedWizard, self).default_get(fields)
    #     active_id = self._context.get('active_id')
    #     brw_id = self.env['account.move'].browse(int(active_id))
    #
    #     if active_id:
    #         res['expense_id'] = brw_id.expense_id.id
    #         res['move_id'] = brw_id.id
    #     return res

    user_id = fields.Many2one('res.users', string="Employee")

    def action_validate(self):
        for rec in self:
            pass
