from odoo import api, fields, models, _
from datetime import datetime


class InheritResCompany(models.Model):
    _inherit = 'res.company'

    base_location_line_ids = fields.One2many('oms.base.location', 'company_id', string="location Line")


class BaseLocation(models.Model):
    _name = 'oms.base.location'
    _description = "Base Location"

    name = fields.Char(string="Office Base Location")
    company_id = fields.Many2one('res.company', string="Company")
