from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
from pytz import timezone
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError


class StateLocation(models.Model):
    _name = 'hr.state.location'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'HR State Location'

    name = fields.Char(string="Name")
    code = fields.Char(string="Code")


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    state_id = fields.Many2one('hr.state.location', string="State", required=True)
    bank_account_id = fields.Many2one(
        'res.partner.bank', 'Bank Account',
        groups="hr.group_hr_user",
        tracking=True,
        help='Employee bank account to pay salaries')
    staff_file_line_ids = fields.One2many('staff.file.information', 'employee_id', string="Staff File")
    contract_id = fields.Many2one('hr.contract', string="Current Contract")

    def print_staff_information(self):
        self.ensure_one() 
        
        
        contract = self.env['hr.contract'].search([
            ('employee_id', '=', self.id),
            ('state', '=', 'open')
        ], limit=1)

        if not contract:
            contract = self.env['hr.contract'].search([
                ('employee_id', '=', self.id)
            ], order='date_start desc', limit=1)

        if contract:
            self.write({'contract_id': contract.id})

        return self.env.ref('hop_hr_payroll.staff_basic_information_reports').report_action(self)


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    state_id = fields.Many2one('hr.state.location', string="State")


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    bank_branch = fields.Char(string="Branch", required=True)
    bank_name_arabic = fields.Char(string="Bank Name In Arabuc", required=True)
    account_holder_type = fields.Selection([
        ('vendor', 'Vendor'),
        ('employee', 'Employee'),
    ], default="employee", string="Account Holder Type")
    holder_arabic_name = fields.Char(string="Holder Arabic Name")


class JobPosationInherit(models.Model):
    _inherit = 'hr.job'



class StaffFileInformation(models.Model):
    _name = 'staff.file.information'
    _description = 'Staff File Information'

    employee_id = fields.Many2one('hr.employee', string="Employee")
    description = fields.Char(string="File Description")
    document = fields.Binary(string='Document')

 


