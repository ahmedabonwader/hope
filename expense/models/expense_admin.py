from odoo import models, fields, api

class ExpenseAdmin(models.Model):
    _name = 'expense.admin'
    _description = 'Expense Admin Configuration'

    user_id = fields.Many2one('res.users', string='User', required=True)
    admin_ids = fields.Many2many('res.users', string='Admins', required=True) 