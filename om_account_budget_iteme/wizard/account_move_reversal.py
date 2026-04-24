# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import UserError


class AccountMoveReversalInherit(models.TransientModel):
    """
    Account move reversal wizard, it cancel an account move by reversing it.
    """
    _inherit = 'account.move.reversal'
    _description = 'Account Move Reversal'
    _check_company_auto = True

    @api.model
    def default_get(self, fields):
        res = super(AccountMoveReversalInherit, self).default_get(fields)
        # res['move_id'] = self.env.context.get('active_id')
        active_id = self._context.get('active_id')
        brw_id = self.env['account.move'].browse(int(active_id))

        if active_id:
            res['move_id'] = brw_id.id
        return res

    move_id = fields.Many2one('account.move', 'Move#')

    def refund_moves(self):
        res = super(AccountMoveReversalInherit, self).refund_moves()
        for rec in self:
            rec.move_id.is_credit = True
        return res


