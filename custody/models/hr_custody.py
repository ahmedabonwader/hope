from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime

class HrContract(models.Model):
    _inherit = 'hr.contract'

    def write(self, vals):
        if 'state' in vals and vals['state'] in ['cancel', 'close']:
            for contract in self:
                employee = contract.employee_id
                if employee:
                    # Check for active custodies
                    active_custodies = self.env['hr.custody'].search([
                        ('employee_id', '=', employee.id),
                        ('state', '=', 'assigned')
                    ])
                    
                    # Check for active finance custodies
                    active_finance_custodies = self.env['account.journal'].search([
                        ('custody_employee_id', '=', employee.id),
                        ('custody_status', '=', 'active')
                    ])

                    if active_custodies or active_finance_custodies:
                        message = _("Warning: Employee has active custodies:\n")
                        if active_custodies:
                            message += _("- %s Item Custody Records\n") % len(active_custodies)
                        if active_finance_custodies:
                            message += _("- %s Finance Custody Records\n") % len(active_finance_custodies)
                        message += _("\nPlease handle these custodies before %s the contract.") % (
                            'canceling' if vals['state'] == 'cancel' else 'closing'
                        )
                        raise ValidationError(message)

        return super().write(vals)

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    custody_ids = fields.One2many('hr.custody', 'employee_id', string='Custody Records')
    finance_custody_ids = fields.One2many('account.journal', 'custody_employee_id', string='Finance Custody Records')
    finance_custody_count = fields.Integer(string='Custody Count', compute='_compute_custody_count')

    def _compute_custody_count(self):
        for employee in self:
            employee.finance_custody_count = len(employee.finance_custody_ids)
class HrCustody(models.Model):
    _name = 'hr.custody'
    _description = 'HR Custody'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'
    
    name = fields.Char(string='Reference', required=True, copy=False, 
                       readonly=True, default=lambda self: _('New'))
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, 
                                  tracking=True,)
    department_id = fields.Many2one('hr.department', string='Department', 
                                   related='employee_id.department_id', 
                                   store=True,)
    date = fields.Datetime(string='Date', required=True, default=fields.Datetime.now,
                          tracking=True,)
    custody_item_id = fields.Many2one('custody.item', string='Custody Item', 
                                      required=True, tracking=True,domain="[('employee_id', '=', False)]")


    notes = fields.Text(string='Notes', tracking=True,
                       readonly=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('assigned', 'Assigned'),
        ('returned', 'Returned'),
        ('lost', 'Lost')
    ], string='Status', default='draft', tracking=True)
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.custody') or _('New')
            
        return super(HrCustody, self).create(vals_list)
    # override unlink method to prevent deleting non-draft records
    def unlink(self):   
        for record in self:
            if record.state != 'draft':
                raise ValidationError(_('You can only delete custody records in draft state.'))
        return super(HrCustody, self).unlink()
    def action_assign(self):
        self.write({'state': 'assigned'})
        self.custody_item_id.employee_id = self.employee_id
        self.custody_item_id.employee_history.create({
            'employee_id': self.employee_id.id,
            'assign_date': self.date,
            'custody_item_id': self.custody_item_id.id
        })
    def action_return(self):
        self.write({'state': 'returned'})
        self.custody_item_id.employee_id = False
        history = self.env['hr.employee.history'].search([
            ('employee_id', '=', self.employee_id.id),
            ('custody_item_id', '=', self.custody_item_id.id),
            ('assign_date', '=', self.date),
            ('return_date', '=', False),
            ('lost_date', '=', False)
        ], limit=1)
        if history:
            history.write({
                'return_date': fields.Date.today()
            })
        else:
            self.custody_item_id.employee_history.create({
                'employee_id': self.employee_id.id,
                'assign_date': self.date,
                'return_date': fields.Date.today(),
                'custody_item_id': self.custody_item_id.id
            })
            
    def action_lost(self):
        self.write({'state': 'lost'}) 
        self.custody_item_id.employee_id = False
        self.custody_item_id.active = False
        history = self.env['hr.employee.history'].search([
            ('employee_id', '=', self.employee_id.id),
            ('custody_item_id', '=', self.custody_item_id.id),
            ('assign_date', '=', self.date),
            ('return_date', '=', False),
            ('lost_date', '=', False)
        ], limit=1)
        
        if history:
            history.write({
                'lost_date': fields.Date.today()
            })
        else:
            self.custody_item_id.employee_history.create({
                'employee_id': self.employee_id.id,
                'assign_date': self.date,
                'lost_date': fields.Date.today(),
                'custody_item_id': self.custody_item_id.id
            })