from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
import calendar

from docutils.frontend import store_multiple
from pytz import timezone
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression


class PayslipsBatches(models.Model):
    _name = 'payslips.batches'
    _description = 'Payslips Batches'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'
    _rec_name = 'reference'

    project_salary_id = fields.Many2one('project.salary.configuration', string='Project Salary')
    salary_type = fields.Selection([
        ('by_project', 'By Project'),
        ('by_contract', 'By Contract'),
    ])
    name = fields.Char(string="Description", required=True)
    created_by = fields.Many2one('res.users', string="Created By")
    user_id = fields.Many2one('res.users', string="User", default=lambda self: self.env.user.id)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, readonly=True)
    branch_ids = fields.Many2many(related='project_id.branch_ids', string='Branches')
    salary_conf_id = fields.Many2one('project.salary.configuration', string="Salary Configuration")
    date_from = fields.Date(string='Date From', required=False)
    date_to = fields.Date(required=False, tracking=True, string="Date To")
    date = fields.Date(string="Date", tracking=True, )
    project_id = fields.Many2one('project.project', string='Project')
    rate = fields.Float(string='Rates', digits=(16, 6))
    payment_no = fields.Float(string='Payment No#')
    reference = fields.Char(string='Reference', readonly=True, index=True, copy=False, default=lambda self: _('New'))
    social_ins_percentage = fields.Float(string='Insurance  % ')
    taxes_percentage = fields.Float(string='Taxes %', )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('review', 'Reviews'),
        ('approve', 'Approved'),
        ('done', 'Done')
    ], 'Status', default='draft', index=True, required=True, readonly=True, copy=False, tracking=True)
    date_approve = fields.Date()
    date_review = fields.Date()
    date_prepared = fields.Date()
    signature_reviewed = fields.Many2one('res.users', string="Signature Reviewed")
    signature_approved = fields.Many2one('res.users', string="Signature Approved")
    payslip_id = fields.Many2one('hr.payslip.project', string='payslip')
    currency_id = fields.Many2one('res.currency', string="Currency",
                                  default=lambda self: self.env['res.currency'].search([('name', '=', 'SDG')], limit=1))
    batches_line_ids = fields.One2many('payslips.batches.line', 'batches_id')
    create_bills = fields.Boolean(
        default=False
    )
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
    ], string="Month")
    check_set_employee = fields.Boolean(string="Check Employee")
    missing_one = fields.Boolean(string="Missing One?")
    salary_bill_count = fields.Integer(string="Salary Bill Count", compute='_compute_salary_bill_count', tracking=True)
    account_id = fields.Many2one(
        comodel_name='account.account', check_company=True,
        string='Salary Account',
        domain="[('deprecated', '=', False),('account_type', '=', 'expense')]")
    total_salary_in_sdg = fields.Float(string="Total Amount", compute="_compute_total_salary_in_sdg", store=True)
    state_id = fields.Many2one(related="salary_conf_id.state_id", string="State")
    insurance_payment = fields.Boolean(string="Insurance Payment")
    taxes_payment = fields.Boolean(string="Taxes Payment")
    total_social_insurance = fields.Float(string="Total Soical Insurance", compute="_compute_total_social_insurance", store=True)
    total_taxes = fields.Float(string="Total Taxes", compute="_compute_total_taxes", store=True)
    bank_letters_count = fields.Integer(string='Bank Letters Count', compute="_compute_bank_letters_count")
    bank_account_line_ids = fields.One2many('payslip.bank.account.line', 'batches_id', string="Bank Account Line",
                           compute='_compute_bank_account_lines', store=True,)
    letter_created = fields.Boolean(string="Letter Created?")
    print_type = fields.Selection([('with_signature', 'With Signature'), ('without_signature', 'Without Signature')], string='Print Type')

    def action_create_bank_letters(self):
        for rec in self:
            vals = {
                'amount': rec.total_salary_in_sdg,
                'date': rec.date,
                'currency_id': rec.currency_id.id,
                'project_id': rec.project_id.id,
                'batches_id': rec.id,
            }
            new = self.env['create.bank.letters.wizard'].create(vals)
            return {
                'name': "Bank Letters",
                'type': 'ir.actions.act_window',
                'res_model': 'create.bank.letters.wizard',
                'res_id': new.id,
                'view_id': self.env.ref('hop_hr_payroll.view_create_bank_letters_wizard_form', False).id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new'
            }

    @api.depends('batches_line_ids.employee_id', 'batches_line_ids.salary_in_sdg')
    def _compute_bank_account_lines(self):
        for rec in self:
            # 1. تجهيز الرواتب الحالية من خطوط البطاقة (Batches Lines)
            salary_map = {line.employee_id.id: line.salary_in_sdg for line in rec.batches_line_ids if line.employee_id}
            
            existing_lines = rec.bank_account_line_ids
            # استخراج الـ IDs الحالية للموظفين الموجودين في جدول البنك
            existing_employee_ids = existing_lines.mapped('employee_id.id')

            commands = []

            # 2. معالجة الموظفين الموجودين في جدول الرواتب
            for emp_id, salary_amount in salary_map.items():
                if emp_id not in existing_employee_ids:
                    # إضافة موظف جديد
                    commands.append((0, 0, {
                        'employee_id': emp_id,
                        'amount': salary_amount,
                    }))
                else:
                    # تحديث الموظف الموجود - نأخذ السجل الأول فقط لضمان الـ singleton
                    line = existing_lines.filtered(lambda l: l.employee_id.id == emp_id)[:1]
                    if line.amount != salary_amount:
                        commands.append((1, line.id, {'amount': salary_amount}))

            # 3. حذف الموظفين الذين تمت إزالتهم من جدول الرواتب
            for line in existing_lines:
                if line.employee_id.id not in salary_map:
                    commands.append((2, line.id, 0))

            # تنفيذ جميع العمليات دفعة واحدة
            rec.bank_account_line_ids = commands

    def _compute_bank_letters_count(self):
        for rec in self:
            bank_letters_count = self.env['bank.letters'].search_count([('salary_id', '=', rec.id)])
            rec.bank_letters_count = bank_letters_count

    def action_bank_letters_count(self):
        for rec in self:
            domain = [('salary_id', '=', rec.id)]
            return {
                'type': 'ir.actions.act_window',
                'name': 'bank_letters',
                'res_model': 'bank.letters',
                'domain': domain,
                'view_mode': 'list,form',
                'target': 'current',
            }

    def name_get(self):
        result = []
        for rec in self:
            # لو عايز يظهر reference + month
            name = "%s [%s]" % (rec.reference or '', rec.month.capitalize() if rec.month else '')
            result.append((rec.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            # البحث ممكن يكون في reference أو month
            domain = ['|',
                      ('reference', operator, name),
                      ('month', operator, name.lower())]  # month مخزن بالـ key
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

    @api.depends('batches_line_ids.insurance_usd', 'rate')
    def _compute_total_social_insurance(self):
        for rec in self:
            total = 0
            for line in rec.batches_line_ids:
                total += line.insurance_usd
                rec.total_social_insurance = total * rec.rate


    @api.depends('batches_line_ids.taxes_usd', 'rate')
    def _compute_total_taxes(self):
        for rec in self:
            total = 0
            for line in rec.batches_line_ids:
                total += line.taxes_usd
                rec.total_taxes = total * rec.rate

    # This Function Calculates The Number of Bills
    def _compute_salary_bill_count(self):
        for rec in self:
            count = self.env['account.move'].search_count([('salary_payslips_id', '=', rec.id)])
            rec.salary_bill_count = count

    # This Function of Smart Button Salary Bill Count
    def action_bill_count(self):
        result = self.env['ir.actions.act_window']._for_xml_id('account.action_move_in_invoice_type')
        result['domain'] = [('salary_payslips_id', '=', self.id)]
        return result
        
    @api.depends('total_salary_in_sdg', 'approval_currency_id')
    def _compute_amount_in_currency(self):
        for rec in self:
            if rec.total_salary_in_sdg > 0 and rec.currency_id != rec.approval_currency_id:
                rec.amount_in_currency = rec.total_salary_in_sdg * rec.approval_currency_id.rate_ids.company_rate

    @api.depends('batches_line_ids.salary_in_sdg')
    def _compute_total_salary_in_sdg(self):
        for rec in self:
            total = 0
            for line in rec.batches_line_ids:
                total += line.salary_in_sdg
                rec.total_salary_in_sdg = total
                    

    def action_set_employee(self):
        for rec in self:
            rec.check_set_employee = True

            if rec.salary_type == 'by_contract':
                hr_contracts = self.env['hr.contract'].search([
                    ('state', '=', 'open'),
                    ('contract_type', 'in', ('contract', 'hybrid')),
                ])

                for contract in hr_contracts:
                    loan = sum(
                        contract.employee_id.loan_line_ids.filtered(
                            lambda x: not x.check_loan and x.project_id.id == rec.project_id.id
                        ).mapped('deduct')
                    )
                    loan_rate = sum(
                        contract.employee_id.loan_line_ids.filtered(lambda x: not x.check_loan).mapped('rate'))
                    advance = sum(
                        contract.employee_id.advance_line_ids.filtered(
                            lambda x: not x.check_advance and x.project_id.id == rec.project_id.id
                        ).mapped('amount')
                    )
                    advance_rate = sum(
                        contract.employee_id.advance_line_ids.filtered(lambda x: not x.check_advance).mapped('rate'))

                    line_vals = {
                        'employee_id': contract.employee_id.id,
                        'batches_id': rec.id,
                        'curr_id': contract.curr_id.id,
                        'job_title': contract.job_id.name,
                        'gross_salary_usd': contract.total_gross_salary,
                        'basic_monthly_salary': contract.basic_monthly_salary,
                        'cola': contract.cola,
                        'transportation': contract.transportation_allowance,
                        'hazard': contract.hazard,
                        'housing': contract.housing_allowance,
                        'insurance_usd': contract.social_insurance,
                        'taxes_usd': contract.staff_income_taxes,
                        'net_salary': contract.total_salary,
                        'loan': loan,
                        'loan_rate': loan_rate,
                        'advance': advance,
                        'advance_rate': advance_rate,
                    }

                    # تحقق إذا الموظف موجود
                    existing_line = rec.batches_line_ids.filtered(
                        lambda l: l.employee_id.id == contract.employee_id.id
                    )
                    if existing_line:
                        existing_line.write(line_vals)  # تحديث
                    else:
                        rec.batches_line_ids.create(line_vals)  # إضافة جديد

            elif rec.salary_type == 'by_project':
                hr_contracts = self.env['hr.contract'].search([
                    ('state', '=', 'open'),
                    ('contract_type', '=', 'project'),
                ])

                for contract in hr_contracts:
                    loan = sum(
                        contract.employee_id.loan_line_ids.filtered(lambda x: not x.check_loan).mapped('deduct'))
                    loan_rate = sum(
                        contract.employee_id.loan_line_ids.filtered(lambda x: not x.check_loan).mapped('rate'))
                    advance = sum(
                        contract.employee_id.advance_line_ids.filtered(lambda x: not x.check_advance).mapped('amount'))
                    advance_rate = sum(
                        contract.employee_id.advance_line_ids.filtered(lambda x: not x.check_advance).mapped('rate'))

                    line_vals = {
                        'employee_id': contract.employee_id.id,
                        'batches_id': rec.id,
                        'job_title': contract.job_id.name,
                        'gross_salary_usd': contract.total_gross_salary,
                        'basic_monthly_salary': contract.basic_monthly_salary,
                        'cola': contract.cola,
                        'transportation': contract.transportation_allowance,
                        'hazard': contract.hazard,
                        'housing': contract.housing_allowance,
                        'insurance_usd': contract.social_insurance,
                        'taxes_usd': contract.staff_income_taxes,
                        'net_salary_usd': contract.total_salary,
                        'loan': loan,
                        'loan_rate': loan_rate,
                        'advance': advance,
                        'advance_rate': advance_rate,
                    }

                    # تحقق إذا الموظف موجود
                    existing_line = rec.batches_line_ids.filtered(
                        lambda l: l.employee_id.id == contract.employee_id.id
                    )
                    if existing_line:
                        existing_line.write(line_vals)  # تحديث
                    else:
                        rec.batches_line_ids.create(line_vals)  # إضافة جديد

    @api.onchange('account_id')
    def onchange_account_id(self):
        for record in self.batches_line_ids:
            record.write({'account_id': self.account_id.id})

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', _('New')) == _('New'):
                vals['reference'] = self.env['ir.sequence'].next_by_code('payslip.batche') or _('New')
        return super().create(vals_list)

    def action_payslip_to_confirm(self):
        self.write({'state': 'confirm'})
        for rec in self:
            if rec.rate == 0:
                raise ValidationError(_('Please Enter Rate'))
            elif rec.rate < 0:
                raise ValidationError(_('Sorry The Rate Can not be in Negative Value'))

    def action_payslip_review(self):
        for rec in self:
            for line in rec.batches_line_ids:
                if not line.account_id:
                    raise UserError(_('A separate payroll account must be defined for each employee.'))
                if rec.salary_type == 'by_project':
                    if not line.budget_line:
                        raise ValidationError(_('Sorry Enter Budget Line Code First'))
            rec.signature_reviewed = self.env.user.id
            rec.date_review = date.today().strftime('%Y-%m-%d')
            rec.write({'state': 'review'})

    def action_payslip_approve(self):
        """
        Approve the payslip batch after checking the user's authority 
        limits and converting amounts based on the provided exchange rate.
        """
        for rec in self:
            if not rec.project_id:
                raise ValidationError(_("This payslip batch must be linked to a project before approval."))

            matched = False
            current_user = self.env.user
            
            # 1. Determine the amount to compare against the approval limit
            # If currency is SDG, we divide the total by the rate to get the value in foreign currency (e.g., USD)
            # If the currency is already USD (Rate = 1), the amount remains unchanged.
            comparison_amount = 0
            if rec.rate > 0:
                comparison_amount = rec.total_salary_in_sdg / rec.rate
            else:
                raise ValidationError(_("Please ensure a valid exchange rate (Rate) is entered."))

            # 2. Check current user's authorizations in the linked project
            for line in rec.project_id.authorizations_line_ids:
                # Check match by User ID or Name
                if line.emp_id.id == current_user.id or line.emp_id.name == current_user.name:
                    matched = True
                    
                    # If the user is marked as Admin, bypass limit checks
                    if line.is_admin:
                        break
                    
                    # Compare the converted amount with the user's limit (line.amount)
                    if comparison_amount > line.amount:
                        raise ValidationError(_(
                            "You are not authorized to approve this amount.\n"
                            "Your approval limit is: %.2f %s\n"
                            "The batch total equals: %.2f %s\n"
                            "Please contact your direct manager for approval."
                        ) % (line.amount, line.currency_id.name, comparison_amount, line.currency_id.name))
                    
                    # If amount is within limit, exit the loop to proceed with approval
                    break 

            if not matched:
                raise ValidationError(_("You are not assigned to the authorization list for project: %s.") % rec.project_id.name)

            # Finalize approval and record the signature/date
            rec.signature_approved = current_user.id
            rec.date_approve = fields.Date.today()
            rec.state = 'approve'

    def action_print_salary_payment_sheet(self):
        vals = {
            'project_id': self.project_id.id,
            'batches_id': self.id,
            'salary_type': self.salary_type,
            'company_id': self.company_id.id
        }
        new = self.env['salary.payment.sheet.report'].create(vals)
        return {
            'name': "Salary Payment Sheet",
            'type': 'ir.actions.act_window',
            'res_model': 'salary.payment.sheet.report',
            'res_id': new.id,
            'view_id': self.env.ref('hop_hr_payroll.view_salary_payment_sheet_report_form', False).id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new'
        }

    def action_payslip_to_draft(self):
        self.write({'state': 'draft'})

    def action_payslip_done(self):
        if self.rate <= 0.0:
            raise ValidationError(_('Please enter the rate'))

        for line in self.batches_line_ids:
            if line.advance > 0.0:
                advances = line.employee_id.advance_line_ids.filtered(lambda x: not x.check_advance)
                for adv in advances:
                    adv.write({'advance_count': adv.advance_count + 1})

            if line.loan > 0.0:
                loans = line.employee_id.loan_line_ids.filtered(lambda x: not x.check_loan)
                for loan in loans:
                    loan.write({'loan_count': loan.loan_count + 1})

        self.write({'state': 'done'})

    def print_payslips(self):
        return self.env.ref('hop_hr_payroll.report_payslips_batches').report_action(self)

    def action_paysheet_wizard(self):
        for rec in self:
            vals = {
                'payslip_id': rec.id,
            }
            new = self.env['paysheet.wizard'].create(vals)
            return {
                'name': "Salary Payment Sheet",
                'type': 'ir.actions.act_window',
                'res_model': 'paysheet.wizard',
                'res_id': new.id,
                'view_id': self.env.ref('hop_hr_payroll.view_paysheet_wizard_form', False).id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new'
            }

    def action_create_bills(self):
        if self.create_bills:
            raise UserError(_('Salary payslips batche has been created.'))

        month_name = ''
        if self.date:
            month_name = calendar.month_name[self.date.month]  # 👈 استخراج اسم الشهر من date_from
        if self.salary_type == 'project':
            for line in self.batches_line_ids.filtered(lambda x: x.state == 'run'):
                self.write({'payment_no': self.payment_no + 1})

                partner_id = self.env['res.partner'].search([
                    ('name', '=', line.employee_id.name),
                ], limit=1)

                ref_text_project = f"{line.employee_id.name} {line.employee_id.job_id.name} Salary {str(line.salary_conf_id.month)}"
                ref_text = f"{line.employee_id.name} {line.employee_id.job_id.name} Salary {month_name}"

                if partner_id:
                    invoice = self.env['account.move'].create({
                        'move_type': 'in_invoice',
                        'rate': self.rate,
                        'partner_id': partner_id.id,
                        'ref': ref_text_project,
                        'project_id': line.project_id.id,
                        'salary_check': True,
                        'salary_payslips_id': self.id,
                        'currency_id': self.currency_id.id,
                        'invoice_line_ids': [(0, 0, {
                            'account_id': line.account_id.id,
                            'name': ref_text_project,
                            'budget_item_line_id': line.budget_line.id,
                            'quantity': 1,
                            'price_unit': line.salary_in_sdg,
                            'tax_ids': False,
                        })],
                    })
                else:
                    partner = self.env['res.partner'].create({'name': line.employee_id.name})
                    invoice = self.env['account.move'].create({
                        'move_type': 'in_invoice',
                        'rate': self.rate,
                        'required_rate': False,
                        'currency_id': self.currency_id.id,
                        'partner_id': partner.id,
                        'salary_check': True,
                        'salary_payslips_id': self.id,
                        'project_id': line.project_id.id,
                        'ref': ref_text_project,
                        'invoice_line_ids': [(0, 0, {
                            'account_id': line.account_id.id,
                            'name': ref_text_project,
                            'budget_item_line_id': line.budget_line.id,
                            'quantity': 1,
                            'price_unit': line.salary_in_sdg,
                            'tax_ids': False,
                        })],
                    })
        elif self.salary_type != 'project':
            for line in self.batches_line_ids:
                self.write({'payment_no': self.payment_no + 1})

                partner_id = self.env['res.partner'].search([
                    ('name', '=', line.employee_id.name),
                ], limit=1)

                ref_text = f"{line.employee_id.name} {line.employee_id.job_id.name} Salary {month_name}"

                if partner_id:
                    invoice = self.env['account.move'].create({
                        'move_type': 'in_invoice',
                        'rate': self.rate,
                        'salary_check': True,
                        'salary_payslips_id': self.id,
                        'partner_id': partner_id.id,
                        'ref': ref_text,
                        'project_id': line.project_id.id,
                        'currency_id': self.currency_id.id,
                        'invoice_line_ids': [(0, 0, {
                            'account_id': line.account_id.id,
                            'name': ref_text,
                            'budget_item_line_id': line.budget_line.id,
                            'quantity': 1,
                            'price_unit': line.salary_in_sdg,
                            'tax_ids': False,
                        })],
                    })
                else:
                    partner = self.env['res.partner'].create({'name': line.employee_id.name})
                    invoice = self.env['account.move'].create({
                        'move_type': 'in_invoice',
                        'rate': self.rate,
                        'salary_check': True,
                        'salary_payslips_id': self.id,
                        'required_rate': False,
                        'partner_id': partner.id,
                        'currency_id': self.currency_id.id,
                        'project_id': line.project_id.id,
                        'ref': ref_text,
                        'invoice_line_ids': [(0, 0, {
                            'account_id': line.account_id.id,
                            'name': ref_text,
                            'budget_item_line_id': line.budget_line.id,
                            'quantity': 1,
                            'price_unit': line.salary_in_sdg,
                            'tax_ids': False,
                        })],
                    })
        self.write({'create_bills': True})
        for rec in self:
            for line in rec.batches_line_ids:
                line.bill_created = True

    def action_get_update(self):
        for rec in self:
            if rec.salary_type == 'by_project':
                for line in rec.batches_line_ids:
                    contract_line = self.env['contract.line'].search([
                        ('employee_id', '=', line.employee_id.id),
                        ('project_id', '=', line.project_id.id),
                        ('state', '=', 'run'),
                    ], limit=1)
                    if contract_line:
                        line.housing = contract_line.project_housing
                        line.gross_salary_usd = contract_line.project_salary
                        line.basic_monthly_salary = contract_line.project_basic_salary
                        line.cola = contract_line.project_cola
                        line.transportation = contract_line.project_transportation
                        line.hazard = contract_line.project_hazard
                        line.insurance_usd = contract_line.project_insurance
                        line.taxes_usd = contract_line.project_taxes
                        line.net_salary = contract_line.p_total_salary
                        line.curr_id = contract_line.curr_id.id
            elif rec.salary_type == 'by_contract':
                for line in rec.batches_line_ids:
                    contract = self.env['hr.contract'].search([
                        ('employee_id', '=', line.employee_id.id),
                        ('state', '=', 'open'),
                    ], limit=1)
                    if contract:
                        line.housing = contract.housing_allowance
                        line.gross_salary_usd = contract.total_gross_salary
                        line.basic_monthly_salary = contract.basic_monthly_salary
                        line.cola = contract.cola
                        line.transportation = contract.transportation_allowance
                        line.hazard = contract.hazard
                        line.insurance_usd = contract.social_insurance
                        line.taxes_usd = contract.staff_income_taxes
                        line.net_salary = contract.total_salary
                        line.curr_id = contract.curr_id.id

    

    def action_print_social_insurance_and_tax_print_report(self):       
        vals = {
            'payslip_id': self.id,
        }
        new = self.env['social.insurance.tax.wizard'].create(vals)
        return {
            'name': "Social Insurance And Tax Report",
            'type': 'ir.actions.act_window',
            'res_model': 'social.insurance.tax.wizard',
            'res_id': new.id,
            'view_id': self.env.ref('hop_hr_payroll.social_insurance_tax_wizard_form', False).id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new'
        }

    signature_insuranse_tax_reviewed = fields.Many2one('res.users', string="Reviewed by")
    signature_insuranse_tax_approved = fields.Many2one('res.users', string="Approved by")
    signature_insuranse_tax_prepared = fields.Many2one('res.users', string="Prepared by")
    date_insuranse_tax_approve = fields.Date(string="Approved Date", readonly=True)
    date_insuranse_tax_review = fields.Date(string="Reviewed Date", readonly=True)
    date_insuranse_tax_prepared = fields.Date(string="Prepared Date", readonly=True)

    def action_print_social_insurance_report(self):
        action = self.env.ref('hop_hr_payroll.action_print_social_insurance_report').read()[0]
        return action

    def action_print_taxes_report(self):
        action = self.env.ref('hop_hr_payroll.action_print_taxes_report').read()[0]
        return action


class PayslipsBatchesLine(models.Model):
    _name = 'payslips.batches.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'

    batches_id = fields.Many2one('payslips.batches', string='Batches')
    currency_id = fields.Many2one(related='batches_id.currency_id')
    project_salary_id = fields.Many2one('project.salary.line')
    sequence = fields.Integer(string='sequence', default=10)
    account_id = fields.Many2one(
        comodel_name='account.account', check_company=True,
        string='Expense Account',
        domain="[('deprecated', '=', False),('account_type', '=', 'expense')]")
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    state = fields.Selection([
        ('stop', 'Stop'),
        ('run', 'Running'),
        ('cancel', 'Cancel'),
        ('done', 'Done')
    ], string='Salary State', store=True, readonly=True)
    budget_line = fields.Many2one(
        'budget.iteme.line',
        string='Budget Item Line',
        domain="[('account_id', '=', account_id),('budget_iteme_id.state', '=', 'validate'), ('budget_iteme_id.project_id', '=', project_id)]"
    )
    bill_created = fields.Boolean(string="Bill Created?")
    project_id = fields.Many2one(related="batches_id.project_id", string='Project')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)  # One2one
    employee_id = fields.Many2one('hr.employee', string='Staff Name')
    job_title = fields.Char(related='employee_id.job_title')
    gross_salary_usd = fields.Float(string='Gross Salary')
    basic_monthly_salary = fields.Float(string='Basic Salary USD(36.5%)', tracking=4)
    cola = fields.Float(string='COLA(23.5%)', tracking=4)
    transportation = fields.Float(string='Transport(LTA)(20%)')
    hazard = fields.Float(string='Hazard(10%)')
    housing = fields.Float(string='Housing(10%)', tracking=4)
    insurance_usd = fields.Float(string='Social Insurance(8%)')
    taxes_usd = fields.Float(string='taxes(20%)')
    loan = fields.Float(string='Loan')
    loan_currency = fields.Many2one('res.currency', string="Loan Currency", compute="_compute_loan_currency")
    loan_rate = fields.Float(string='Loan Rate')
    advance = fields.Float(string='Advance')
    advance_currency = fields.Many2one('res.currency', string="Advance Currency", compute="_compute_advance_currency")
    advance_rate = fields.Float(string='Advance Rate')
    total_deductions = fields.Float(string='Total Deductions', compute='_compute_total_deductions', stor=True,
                                    tracking=4)

    disciplinary_deduction = fields.Float(string="Disciplinary Deduction SDG")
    reason = fields.Text(string="Reason")
    curr_id = fields.Many2one('res.currency', string="Currency", readonly=False)
    reason_check = fields.Boolean(string="Reason Check", compute="_compute_reason_check")

    net_salary = fields.Float(string="Net Salary")
    salary_in_sdg = fields.Float(string="Total Amount", compute="_compute_salary_in_sdg")
    line_number = fields.Integer(string="NO", compute="_compute_line_number", store=True)

    @api.depends('batches_id.batches_line_ids')
    def _compute_line_number(self):
        for rec in self:
            if rec.batches_id:
                for index, line in enumerate(rec.batches_id.batches_line_ids, start=1):
                    line.line_number = index

    @api.depends('employee_id', 'project_id')
    def _compute_loan_currency(self):
        for rec in self:
            loan_id = self.env['hms.expense.request.loan.line'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('project_id', '=', rec.project_id.id),
                ('check_loan', '=', False)
            ], limit=1)
            rec.loan_currency = loan_id.currency_id.id if loan_id else False

    @api.depends('employee_id', 'project_id')
    def _compute_advance_currency(self):
        for rec in self:
            advance_id = self.env['hms.expense.request.advance.line'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('project_id', '=', rec.project_id.id),
                ('check_advance', '=', False)
            ], limit=1)
            
            rec.advance_currency = advance_id.currency_id.id if advance_id else False

    @api.depends('batches_id.rate', 'net_salary', 'disciplinary_deduction')
    def _compute_salary_in_sdg(self):
        for rec in self:
            if rec.curr_id.name == 'SDG':
                rec.salary_in_sdg = rec.net_salary - (rec.loan + rec.advance + rec.disciplinary_deduction)
            else:
                rec.salary_in_sdg = rec.net_salary * rec.batches_id.rate - (
                        rec.loan + rec.advance + rec.disciplinary_deduction)

    @api.depends('disciplinary_deduction')
    def _compute_reason_check(self):
        for rec in self:
            if rec.disciplinary_deduction > 0:
                rec.reason_check = True
            elif rec.disciplinary_deduction <= 0:
                rec.reason_check = False

    @api.depends('taxes_usd', 'insurance_usd', )
    def _compute_total_deductions(self):
        for record in self:
            record.total_deductions = (record.taxes_usd + record.insurance_usd)



class EmployeeBankAccountLine(models.Model):
    _name = 'payslip.bank.account.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'

    batches_id = fields.Many2one('payslips.batches', string='Batches')
    employee_id = fields.Many2one('hr.employee', string='Staff Name')
    job_title = fields.Char(related='employee_id.job_title')
    bank_account_id = fields.Many2one(related="employee_id.bank_account_id", string="Bank Account")
    branch = fields.Char(related="bank_account_id.bank_branch", string="Branch")
    amount = fields.Float(string="Amount")
    line_number = fields.Integer(string="NO", compute="_compute_line_number", store=True)

    @api.depends('batches_id.bank_account_line_ids')
    def _compute_line_number(self):
        for rec in self:
            if rec.batches_id:
                for index, line in enumerate(rec.batches_id.bank_account_line_ids, start=1):
                    line.line_number = index