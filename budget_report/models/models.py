
from odoo import models, fields, api


class AccountMoveInherit(models.Model):
    _inherit = 'account.move'

    def process_data(self, **kwargs):
        amount_usd = ( (1 / kwargs.get('rate', 0) ) * kwargs.get('price', 1))
        return round(amount_usd, 3)


    def get_foreign_exchange(self, **kwargs):
        amount_usd = ( (1 / kwargs.get('rate', 0) ) * kwargs.get('price', 1))
        return round(amount_usd, 3)


class CrossoveredBudgetLine(models.Model):
        _inherit = 'crossovered.budget.lines'


        def get_foreign_exchange(self, **kwargs):
            amount_usd = (kwargs.get('rate', 0) * kwargs.get('price', 1))
            return round(amount_usd, 3)




