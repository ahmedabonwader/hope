from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    custody_default_account_id = fields.Many2one(
        'account.account',
        string='Custody Default Account',
        domain=[('account_type', '=', 'asset_cash')],
        config_parameter='custody.custody_default_account_id',
        help='Default account used for custody management'
    ) 