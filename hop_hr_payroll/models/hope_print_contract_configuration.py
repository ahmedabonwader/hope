from odoo import models, fields, api

class HopeOffice(models.Model):
    _name = 'hope.office'
    _description = 'HOPE Office Locations'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(string='Office Name', required=True, help="e.g. HQ Office, North Darfur Office", tracking=True,)
    address = fields.Text(string='Full Address', required=True, tracking=True,)
    mobile = fields.Char(string='Mobile Number', tracking=True,)
    email = fields.Char(string='Email', tracking=True,)
    code = fields.Char(string='Office Code', tracking=True,)
    country_director = fields.Many2one('res.users', string='Represented by (Director Name)', tracking=True,)
    type = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive')
    ], string='Status', default='active', help="Set the office as active or inactive.", tracking=True,)