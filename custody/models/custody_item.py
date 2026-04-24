from odoo import models, fields, api, _

class CustodyItem(models.Model):
    _name = 'custody.item'
    _description = 'Custody Item'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(string='Name', required=True, tracking=True)
    description = fields.Text(string='Description', tracking=True)
    serial_number = fields.Char(string='Serial Number', required=True, tracking=True)
    active = fields.Boolean(default=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', tracking=True)
    employee_history = fields.One2many('hr.employee.history', 'custody_item_id', string='Employee History')
    _sql_constraints = [
        ('serial_number_uniq', 'unique(serial_number)', 
         'The Serial Number must be unique!')
    ] 

class HrEmployeeHistory(models.Model):
    _name = 'hr.employee.history'
    _description = 'Employee History'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    employee_id = fields.Many2one('hr.employee', string='Employee', tracking=True)
    assign_date = fields.Date(string='Assign Date', required=True, tracking=True)
    return_date = fields.Date(string='Return Date', tracking=True)
    lost_date = fields.Date(string='Lost Date', tracking=True)
    custody_item_id = fields.Many2one('custody.item', string='Custody Item', tracking=True)