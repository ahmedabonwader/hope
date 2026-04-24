from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    user_ids = fields.Many2many(
        'res.users',
        string='Authorized Users',
        help='Users authorized to post entries in this journal'
    )
