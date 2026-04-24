from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
from pytz import timezone
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError


class SalaryConfiguration(models.Model):
    _name = 'project.salary.configuration'
    _description = 'Project Salary Configuration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'
    _rec_name = 'reference'

    name = fields.Char(string="Description", required=True)
    project_id = fields.Many2one('project.project', string='Project')
    reference = fields.Char(string='Reference', readonly=True, index=True, copy=False, default=lambda self: _('New'))
    date = fields.Date(default=fields.Date.context_today, required=True, tracking=True, string="Date From")
    date_to = fields.Date(string="Date To", required=True, tracking=True)
    payment_no = fields.Float(string='Payment No#')
    salary_type = fields.Selection([
        ('by_project', 'By Project'),
        ('by_contract', 'By Contract'),
    ], default='by_project')
    month = fields.Selection([
        ('january', 'January'),
        ('february', 'February'),
        ('march', 'March'),
        ('april', 'April'),
        ('may', 'May'),
        ('june', 'June'),
        ('july', 'July'),
        ('august', 'August'),
        ('september', 'September'),
        ('october', 'October'),
        ('november', 'November'),
        ('december', 'December'),
    ])
    salary_check = fields.Boolean(string="Salary Check")
    number_of_month = fields.Integer(Sting="Months", default=1)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)  # One2one
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('review', 'Reviews'),
        ('validate', 'Validated'),
        ('cancel', 'Cancelled'),
        ('done', 'Done')
    ], 'Status', default='draft', index=True, required=True, readonly=True, copy=False, tracking=True)
    project_salary_ids = fields.One2many(
        'project.salary.line',
        'salary_id',
        string='Project Salary'
    )
    user_id = fields.Many2one('res.users', string="User", default=lambda self: self.env.user.id)
    project_salary_state = fields.Selection([
        ('run', 'Running'),
        ('finsh', 'Finished'),
    ], string="Project Salary Status", compute="_compute_project_salary_state", store=True)
    payslips_batches_line_ids = fields.One2many('payslips.batches', 'salary_conf_id', string="Batches Line")
    state_id = fields.Many2one('hr.state.location', string="State")

    @api.depends('payment_no', 'number_of_month')
    def _compute_project_salary_state(self):
        for rec in self:
            if rec.number_of_month == rec.payment_no:
                rec.project_salary_state = 'finsh'
            elif rec.number_of_month > rec.payment_no:
                rec.project_salary_state = 'run'

    def action_back_to_review(self):
        for rec in self:
            rec.state = 'review'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', _('New')) == _('New'):
                vals['reference'] = self.env['ir.sequence'].next_by_code('salary.configuration') or _('New')
        return super().create(vals_list)

    @api.onchange('project_id.state_ids')
    def _onchange_state_id(self):
        for rec in self:
            if rec.project_id:
                state_ids = rec.project_id.state_ids.ids
                rec.state_id = False  # تفريغ القيمة السابقة
                return {'domain': {'state_id': [('id', 'in', state_ids)]}}
            else:
                rec.state_id = False
                return {'domain': {'state_id': []}}

    @api.onchange('project_id', 'state_id')
    def _onchange_project_id(self):
        if not self.project_id:
            self.project_salary_ids = [(5, 0, 0)]
            return

        # Search for active contracts (exclude type = 'contract')
        contracts = self.env['hr.contract'].search([
            ('contract_type', '!=', 'contract'),
            ('state', '=', 'open'),
        ])

        employee_list = []
        for line in contracts.contract_line_ids.filtered(lambda x: x.state == 'run'):
            if self.state_id:
                if line.project_id.id == self.project_id.id and line.employee_id.state_id == self.state_id:
                    employee_list.append((0, 0, {
                        'contract_line_id': line.id,
                        'employee_id': line.contract_id.employee_id.id,
                        'state': line.state,
                        'currency_id': line.curr_id.id,
                        'project_id': line.project_id.id,
                        'basic_monthly_salary': line.project_basic_salary,
                        'gross_salary_usd': line.project_salary,
                        'cola': line.project_cola,
                        'transportation': line.project_transportation,
                        'hazard': line.project_hazard,
                        'housing': line.project_housing,
                        'social_insurance': line.project_insurance,
                        'staff_income_taxes': line.project_taxes,
                        'net_salary': line.p_total_salary
                    }))
            else:
                if line.project_id.id == self.project_id.id:
                    employee_list.append((0, 0, {
                        'contract_line_id': line.id,
                        'employee_id': line.contract_id.employee_id.id,
                        'state': line.state,
                        'currency_id': line.curr_id.id,
                        'project_id': line.project_id.id,
                        'basic_monthly_salary': line.project_basic_salary,
                        'gross_salary_usd': line.project_salary,
                        'cola': line.project_cola,
                        'transportation': line.project_transportation,
                        'hazard': line.project_hazard,
                        'housing': line.project_housing,
                        'social_insurance': line.project_insurance,
                        'staff_income_taxes': line.project_taxes,
                        'net_salary': line.p_total_salary
                    }))

        # Clear table and refill it with the new list
        self.project_salary_ids = [(5, 0, 0)] + employee_list

    def action_create_sheet(self):
        if self.date and self.number_of_month:
            month_map = {
                1: 'january', 2: 'february', 3: 'march', 4: 'april',
                5: 'may', 6: 'june', 7: 'july', 8: 'august',
                9: 'september', 10: 'october', 11: 'november', 12: 'december'
            }

            target_date = self.date + relativedelta(months=int(self.payment_no))
            self.month = month_map.get(target_date.month)

        for rec in self:
            if rec.salary_type == 'by_project':
                if rec.payment_no == rec.number_of_month:
                    raise UserError(_('Number of times the salary calculation is completed'))
            elif rec.salary_type != 'by_project':
                rec.salary_check = True
            rec.write({'payment_no': rec.payment_no + +1})
            invoice = rec.env['payslips.batches'].create({
                'name': rec.name,
                'project_salary_id': rec.id,
                'project_id': rec.project_id.id,
                'date_from': rec.date,
                'date_to': rec.date_to,
                'date': date.today().strftime('%Y-%m-%d'),
                'created_by': rec.user_id.id,
                'date_prepared': date.today().strftime('%Y-%m-%d'),
                'salary_conf_id': rec.id,
                'salary_type': rec.salary_type,
                'month': rec.month,
                'batches_line_ids': [(0, 0, {
                    'project_salary_id': line.id,
                    'employee_id': line.employee_id.id,
                    'state': line.state,
                    'curr_id': line.currency_id.id,
                    'analytic_account_id': rec.project_id.account_id.id,
                    'project_id': line.project_id.id,
                    'advance': sum(
                        line.employee_id.advance_line_ids.filtered(
                            lambda x: not x.check_advance and x.project_id.id == line.project_id.id
                        ).mapped('amount')
                    ),
                    'advance_rate': sum(
                        line.employee_id.advance_line_ids.filtered(lambda x: x.check_advance == False).mapped('rate')),
                    'loan_rate': sum(
                        line.employee_id.loan_line_ids.filtered(lambda x: x.check_loan == False).mapped('rate')),
                    'loan': sum(
                        line.employee_id.loan_line_ids.filtered(
                            lambda x: not x.check_loan and x.project_id.id == line.project_id.id
                        ).mapped('deduct')
                    ),
                    'basic_monthly_salary': line.basic_monthly_salary,
                    'cola': line.cola,
                    'taxes_usd': line.staff_income_taxes,
                    'transportation': line.transportation,
                    'hazard': line.hazard,
                    'housing': line.housing,
                    'insurance_usd': line.social_insurance,
                    'gross_salary_usd': line.gross_salary_usd,
                    'net_salary': line.net_salary,

                }) for line in rec.project_salary_ids.filtered(lambda x: x.state == 'run')
                                     ],
            })
            if rec.project_salary_state == 'finsh':
                for line in rec.project_salary_ids:
                    contract_line = self.env['contract.line'].search([
                        ('employee_id', '=', line.employee_id.id),
                        ('project_id', '=', line.project_id.id),
                        ('state', '=', line.state),
                    ], limit=1)
                    if contract_line:
                        for contract in contract_line:
                            contract.state = 'done'

            self.write({'state': 'done'})

    def action_set_employee_confirm(self):
        for rec in self:
            if rec.project_salary_state == 'finsh':
                raise UserError(
                    _('Employees cannot be added after the salary is approved. Please contact the administration.')
                )

            contracts = rec.env['hr.contract'].search([
                ('state', '=', 'open'),
                ('contract_type', 'in', ('project', 'hybrid'))
            ])

            val_list = []
            rec.write({'project_salary_ids': [(5, 0, 0)]})

            if contracts:
                for contract in contracts:
                    for contract_line in contract.contract_line_ids:
                        if rec.state_id:
                            condition = (contract_line.project_id == rec.project_id and
                                         contract.employee_id.state_id == rec.state_id and contract_line.state == 'run')
                        else:
                            condition = (contract_line.project_id == rec.project_id and contract_line.state == 'run')

                        if condition:
                            val_list.append((0, 0, {
                                'state': 'run',
                                'employee_id': contract.employee_id.id,
                                'currency_id': contract_line.curr_id.id,
                                'gross_salary_usd': contract_line.project_salary,
                                'basic_monthly_salary': contract_line.project_basic_salary,
                                'cola': contract_line.project_cola,
                                'transportation': contract_line.project_transportation,
                                'housing': contract_line.project_housing,
                                'hazard': contract_line.project_hazard,
                                'social_insurance': contract_line.project_insurance,
                                'staff_income_taxes': contract_line.project_taxes,
                                'net_salary': contract_line.p_total_salary,
                            }))

                if val_list:
                    rec.write({'project_salary_ids': [(5, 0, 0)] + val_list})

    def action_payslip_to_confirm(self):
        self.write({'state': 'confirm'})

    def action_payslip_review(self):
        self.write({'state': 'validate'})

    def action_payslip_to_draft(self):
        self.write({'state': 'draft'})

    def action_payslip_to_review(self):
        self.write({'state': 'review'})

    def action_payslip_validate(self):
        self.write({'state': 'done'})

    def action_payslip_cancel(self):
        self.write({'state': 'cancel'})


class ProjectSalaryLine(models.Model):
    _name = 'project.salary.line'

    sequence = fields.Char(string='Budget Line', default=10)
    salary_id = fields.Many2one('project.salary.configuration', string='configuration')
    contract_line_id = fields.Many2one('contract.line')
    employee_id = fields.Many2one('hr.employee', string='Staff Name')
    project_id = fields.Many2one('project.project', string='Project')
    job_title = fields.Char(related='employee_id.job_title')
    basic_monthly_salary = fields.Monetary(string='Basic Salary (36.5%)', tracking=4)
    cola = fields.Monetary(string='COLA (23.5%)', tracking=4)
    transportation = fields.Monetary(string='Transport (LTA) (20%)')
    housing = fields.Monetary(string='Housing  (10%)', tracking=4)
    hazard = fields.Monetary(string='Hazard (10%)')
    social_insurance = fields.Monetary(string='Social Insurance  (8%)')
    staff_income_taxes = fields.Monetary(string='taxes (20%)')
    currency_id = fields.Many2one('res.currency', string="Currency", readonly=True, )
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)  # One2one
    state = fields.Selection([
        ('stop', 'Stop'),
        ('run', 'Running'),
        ('cancel', 'Cancel'),
        ('done', 'Done')
    ], string='Salary State')
    taxes_include = fields.Boolean(string='Taxes include')
    insurance_include = fields.Boolean(string='Insurance include')
    gross_salary_usd = fields.Monetary(string='Gross Salary')
    # net_salary = fields.Monetary(string='Net Salary'  ,compute="_compute_net_salary", store=True)
    net_salary = fields.Monetary(string='Net Salary', store=True)
    line_number = fields.Integer(string="NO", compute="_compute_line_number", store=True)

    @api.depends('salary_id.project_salary_ids')
    def _compute_line_number(self):
        for rec in self:
            if rec.salary_id:
                for index, line in enumerate(rec.salary_id.project_salary_ids, start=1):
                    line.line_number = index

    def button_pending(self):
        for line in self:
            if not self.env.user.has_group('hop_hr_payroll.group_hr_payroll_manager'):
                raise UserError(_('Please contact your accountant to To use this feature.'))
            batches_line = self.env['payslips.batches.line'].search(
                [('project_salary_id', '=', line.id), ('employee_id', '=', line.employee_id.id)])
            batches_line.write({'state': 'stop'})
            line.write({'state': 'stop'})

    def button_start(self):
        for line in self:
            if not self.env.user.has_group('hop_hr_payroll.group_hr_payroll_manager'):
                raise UserError(_('Please contact your accountant to To use this feature.'))
            batches_line = self.env['payslips.batches.line'].search(
                [('project_salary_id', '=', line.id), ('employee_id', '=', line.employee_id.id)])
            batches_line.write({'state': 'run'})
            line.write({'state': 'run'})
