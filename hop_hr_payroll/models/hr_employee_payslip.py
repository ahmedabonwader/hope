from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
from pytz import timezone
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError


class EmployeeSalaryPayslip(models.Model):
    _name = 'hr.employee.payslip'
    _description = 'Salary employee payslip Distribution'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'


    name = fields.Char(string='Reference', readonly=True, index=True, copy=False, default=lambda self: _('New'))
    date_from = fields.Date(string='Date From', required=True,
                            default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    date_to = fields.Date(string='Date To', required=True,
                          default=lambda self: fields.Date.to_string(
                              (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    currency_id = fields.Many2one('res.currency', string="Currency", readonly=True,
                                  default=lambda self: self.env['res.currency'].search([('name', '=', 'USD')], limit=1))
    date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    salary_type = fields.Selection([
        ('by_project', 'By Project'),
        ('by_contract', 'By Contract'),
    ], default='by_contract', readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)  # One2one
    month = fields.Selection(
        [('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'), ('5', 'May'), ('6', 'June'),
         ('7', 'July'), ('8', 'August'), ('9', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December'),
         ], required=True, string='Months')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('review', 'Reviews'),
        ('validate', 'Validated'),
        ('cancel', 'Cancelled'),
        ('done', 'Done')
    ], 'Status', default='draft', index=True, required=True, readonly=True, copy=False, tracking=True)
    social_ins_percentage = fields.Float(string='Social Insurance')
    taxes_percentage = fields.Float(string='Taxes')
    note = fields.Text(string='Internal Note')
    employee_salary_ids = fields.One2many(
        'hr.employee.payslip.line',
        'employee_payslip_id',
        string='Salary'
    )



    def action_payslip_to_draft(self):
        print('------------------',self.env.user.login)

    def action_payslip_to_confirm(self):
            self.env['payslips.batches'].create({
            'project_salary_id': self.id,
            'salary_type': self.salary_type,
            'month': self.month,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'social_ins_percentage': self.social_ins_percentage,
            'taxes_percentage': self.taxes_percentage,

            'batches_line_ids': [(0, 0, {
                'employee_id': line.employee_id.id,
                # 'insurance': line.social_insurance,
                'taxes_usd': line.taxes_usd,
                'insurance_usd': line.insurance_usd,
                'gross_salary_usd': line.gross_salary_usd,
                'net_salary_usd': line.net_salary,

            }) for line in self.employee_salary_ids
                                 ],
        })






    def action_payslip_to_approved(self):
        pass



    def action_payslip_to_review(self):
        pass
    def action_payslip_review(self):
        print('--------------------')
    def action_payslip_validate(self):
        print('----------')
    def action_payslip_cancel(self):
        print('---------------')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('employee.payslip') or _('New')
        return super().create(vals_list)



class EmployeeSalaryLine(models.Model):
    _name = 'hr.employee.payslip.line'

    def _employee_ids_domain(self):
        emp_list = []
        contract = self.env['hr.contract'].search([('state', '=', 'open')])
        if contract:
            for emp in contract:
                emp_list.append(emp.employee_id.id)
        return [('id', 'in', emp_list)]

    sequence = fields.Integer(string='sequence', default=10)
    employee_id = fields.Many2one('hr.employee', string='Employee', domain=_employee_ids_domain)
    employee_payslip_id = fields.Many2one('hr.employee.payslip', string='Employee Salary')
    contract_id = fields.Many2one('hr.contract', string='Requested Signatures')
    job_title = fields.Char(related='employee_id.job_title')
    date_from = fields.Date('Start Date', required=True)
    date_to = fields.Date('End Date', required=True)
    insurance_usd = fields.Monetary(string='Insurance  USD', store=True, compute='_compute_insurance_usd', )
    taxes_usd = fields.Monetary(string='Taxes USD', store=True, compute='_compute_insurance_usd', )
    currency_id = fields.Many2one('res.currency', string="Currency", readonly=True,
                                  default=lambda self: self.env['res.currency'].search([('name', '=', 'USD')], limit=1))
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)  # One2one
    taxes_include = fields.Boolean(string='Taxes include')
    insurance_include = fields.Boolean(string='Insurance include')
    gross_salary_usd = fields.Monetary(string='Gross Salary USD')
    net_salary = fields.Monetary(string='Net Salary', store=True, compute='_compute_net_salary', )
    state = fields.Selection([
        ('stop', 'Stop'),
        ('run', 'Running'),
        ('cancel', 'Cancel'),
        ('done', 'Done')
    ], 'Status')

    @api.depends('gross_salary_usd', 'taxes_include', 'insurance_include')
    def _compute_insurance_usd(self):
        for record in self:
            if record.taxes_include == True and record.insurance_include == True:
                if record.employee_payslip_id.taxes_percentage == 0.0 or record.employee_payslip_id.social_ins_percentage == 0.0:
                    raise UserError(_("Insurance and Taxes Percentage is required!"))
                record.insurance_usd = record.gross_salary_usd * (record.employee_payslip_id.social_ins_percentage / 100)
                record.taxes_usd = record.gross_salary_usd * (record.employee_payslip_id.taxes_percentage / 100)
            elif record.taxes_include == True and record.insurance_include == False:
                if record.employee_payslip_id.taxes_percentage == 0.0:
                    raise UserError(_("Taxes Percentage is required!"))
                record.taxes_usd = record.gross_salary_usd * (record.employee_payslip_id.taxes_percentage / 100)
                record.insurance_usd = 0.0
            elif record.taxes_include == False and record.insurance_include == True:
                if record.employee_payslip_id.social_ins_percentage == 0.0:
                    raise UserError(_("Insurance Percentage is required!"))
                record.taxes_usd = 0.0
                record.insurance_usd = record.gross_salary_usd * (record.employee_payslip_id.social_ins_percentage / 100)
            elif record.taxes_include == False and record.insurance_include == False:
                record.taxes_usd = 0.0
                record.insurance_usd = 0.0

    @api.depends('gross_salary_usd', 'taxes_include', 'insurance_include')
    def _compute_net_salary(self):
        for line in self:
            line.net_salary = line.gross_salary_usd - (line.insurance_usd + line.taxes_usd)

    @api.onchange('employee_id')
    def _set_date(self):
        for rec in self:
            rec.date_from = rec.employee_payslip_id.date_from
            rec.date_to = rec.employee_payslip_id.date_to





