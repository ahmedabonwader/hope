# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
from markupsafe import Markup


class HrContract(models.Model):
    _inherit = 'hr.contract'

    revision = 1
    contract_line_ids = fields.One2many('contract.line', 'contract_id')
    contract_type = fields.Selection([
        ('project', 'By Project'),
        ('contract', 'By Operation'),
        ('hybrid', 'Hybrid')], default='contract', string="Contract Format Type",
        compute='_compute_project_lines', store=True, readonly=False)
    project_taxes = fields.Float(string='Taxes')
    project_insurance = fields.Float(string='Insurance')
    first_contract_date = fields.Date(string="First Contract Start Date", readonly=False)
    basic_monthly_salary = fields.Monetary(string='Basic Salary (36.5%)', store=True,
                                           compute='_compute_salary_of_employee', tracking=4)
    cola = fields.Monetary(string='COLA (23.5%%)  ', compute='_compute_salary_of_employee',
                           store=True, tracking=4)
    transportation_allowance = fields.Monetary(string='Transport (LTA) (20%)',
                                               compute='_compute_salary_of_employee', store=True, tracking=4)
    housing_allowance = fields.Monetary(string='Housing  (10%)', compute='_compute_salary_of_employee',
                                        store=True, tracking=4)
    hazard = fields.Monetary(string='Hazard (10%%)', store=True, tracking=4, compute='_compute_salary_of_employee')

    total_gross_salary = fields.Monetary(string='Gross Salary', store=True, tracking=4,
                                         compute='_compute_salary_of_employee')

    social_insurance = fields.Monetary(string='Social Insurance  (8%)',
                                       compute='_compute_salary_of_employee', store=True, tracking=4)
    staff_income_taxes = fields.Monetary(string='taxes (20%)', compute='_compute_salary_of_employee', store=True,
                                         tracking=4)
    taxes = fields.Boolean(string='Taxes')
    insurance = fields.Boolean(string='Social Insurance')
    deduction = fields.Monetary(string='Total Deduction', compute='_compute_salary_of_employee', store=True, tracking=4)
    wage = fields.Monetary('Gross Salary', compute='_compute_project_lines', store=True, readonly=False)
    curr_id = fields.Many2one('res.currency', string="Currency", default=lambda self: self.env['res.currency'].search([('name', '=', 'USD')], limit=1), readonly=False)
    total_salary = fields.Monetary(string='Net  Salary', compute='_compute_salary_of_employee', store=True, tracking=4)
    sequence = fields.Char(string='Sequence', tracking=True)
    actual_salary = fields.Float(string="Actual Salary")
    active_project_line_ids = fields.One2many('contract.line', compute='_compute_project_lines', string='Active Projects', inverse='_inverse_active_project_lines',)
    history_project_line_ids = fields.One2many('contract.line', compute='_compute_project_lines', string='Projects History')

    def action_print_contract_wizard(self):
        for rec in self:
            vals = {
                'employee_id': rec.employee_id.id,
                'contract_id': rec.id,
            }
            new = self.env['contract.template.wizard'].create(vals)
            return {
                'name': "Contract Template Wizard",
                'type': 'ir.actions.act_window',
                'res_model': 'contract.template.wizard',
                'res_id': new.id,
                'view_id': self.env.ref('hop_hr_payroll.contract_template_wizard_form', False).id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new'
            }

    @api.depends('contract_line_ids', 'contract_line_ids.state', 'actual_salary', 'curr_id')
    def _compute_project_lines(self):
        for record in self:
            # 1. توزيع الأسطر بين الأكتيف والهيستوري
            active_lines = record.contract_line_ids.filtered(lambda l: l.state != 'done')
            record.active_project_line_ids = active_lines
            record.history_project_line_ids = record.contract_line_ids.filtered(lambda l: l.state == 'done')

            # 2. حساب مساهمة المشاريع (منطق الـ Hybrid)
            total_contribution = 0.0
            for line in active_lines:
                if line.state == 'run':
                    if line.curr_id.name == 'SDG':
                        # تحويل السوداني لدولار
                        total_contribution += line.curr_id._convert(
                            line.project_salary, record.curr_id, record.company_id, fields.Date.today()
                        )
                    else:
                        total_contribution += line.project_salary

            # 3. تحديث نوع العقد والراتب (Wage) تلقائياً
            if record.actual_salary > 0:
                if total_contribution < record.actual_salary:
                    record.contract_type = 'hybrid'
                    record.wage = record.actual_salary - total_contribution
                else:
                    record.contract_type = 'project'
                    record.wage = 0.0

    def _inverse_active_project_lines(self):
        for record in self:
            # 1. نجلب أسطر الهيستوري (الحالية اللي في الداتابيز وحالتها Done)
            history_lines = record.contract_line_ids.filtered(lambda l: l.state == 'done')
            
            # 2. نجلب الأسطر النشطة (اللي قدامك في الشاشة حالياً)
            active_lines = record.active_project_line_ids
            
            # 3. ندمجهم مع بعض (عملية دمج Recordsets)
            # أودو بيعرف يتعامل مع السطور الجديدة (NewId) في الخطوة دي
            all_lines = history_lines | active_lines
            
            # 4. نحدث الحقل الرئيسي بكل السطور
            record.contract_line_ids = all_lines
            
    # @api.depends('actual_salary', 'active_project_line_ids', 'active_project_line_ids.project_salary', 'active_project_line_ids.state', 'curr_id')
    # def _compute_contract_settings(self):
    #     for contract in self:
    #         total_contribution = 0.0
            
    #         for line in contract.active_project_line_ids:
    #             if line.state == 'run':
    #                 # إذا كانت العملة سوداني، نحولها لدولار (أو عملة العقد)
    #                 if line.curr_id.name == 'SDG':
    #                     amount_to_add = line.curr_id._convert(
    #                         line.project_salary, 
    #                         contract.curr_id, 
    #                         contract.company_id, 
    #                         fields.Date.today()
    #                     )
    #                 else:
    #                     # أي عملة أخرى (يورو، دولار، إلخ) تجمع كرقم مجرد حسب طلبك
    #                     amount_to_add = line.project_salary
                    
    #                 total_contribution += amount_to_add

    #         # المقارنة مع الراتب الفعلي (Actual Salary)
    #         if contract.actual_salary > 0:
    #             if total_contribution < contract.actual_salary:
    #                 # عجز -> تحويل لـ Hybrid وحساب الفرق الذي ستدفعه المنظمة
    #                 contract.contract_type = 'hybrid'
    #                 contract.wage = contract.actual_salary - total_contribution
    #             else:
    #                 # تغطية كاملة أو زيادة -> العقد Project والمنظمة تدفع 0
    #                 contract.contract_type = 'project'
    #                 contract.wage = 0.0
    #         else:
    #             # في حال عدم وجود راتب فعلي محدد
    #             contract.wage = contract.wage

    @api.model
    def create(self, vals):
        vals['sequence'] = self.env['ir.sequence'].next_by_code('hr.contract')
        return super(HrContract, self).create(vals)

    def write(self, vals):
        if not self.sequence:
            vals['sequence'] = self.env['ir.sequence'].next_by_code('hr.contract')
        return super(HrContract, self).write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        # Handle both single-record and multi-record cases
        if isinstance(vals_list, dict):
            vals_list = [vals_list]  # Convert single dict to list of dicts

        for vals in vals_list:  # Loop through each contract being created
            employee_id = vals.get('employee_id')
            if employee_id:
                active_contract = self.env['hr.contract'].search([
                    ('employee_id', '=', employee_id),
                    ('state', 'in', ['open', 'draft']),  # Check both open and draft contracts
                ], limit=1)

                if active_contract:
                    raise ValidationError(_(
                        "⛔ Cannot Create Contract - Employee Has Active Contract\n\n"
                        f"Employee: {active_contract.employee_id.name}\n"
                        f"Active Contract: {active_contract.name}\n"
                        f"Start Date: {active_contract.date_start}\n"
                        f"Status: {active_contract.state}\n\n"
                        "Action Required: Close or cancel the current contract first."
                    ))

        return super(HrContract, self).create(vals_list)

    @api.depends('currency_id', 'company_id', 'wage', 'insurance', 'taxes')
    def _compute_salary_of_employee(self):
        for request in self:
            request.basic_monthly_salary = (request.wage * 36.5) / 100
            request.cola = (request.wage * 23.5) / 100
            request.housing_allowance = (request.wage * 10) / 100
            request.transportation_allowance = (request.wage * 20) / 100
            request.hazard = (request.wage * 10) / 100
            request.social_insurance = (request.wage * 8) / 100
            if request.taxes == True:
                request.staff_income_taxes = (request.basic_monthly_salary * 20) / 100
            elif request.taxes != True:
                request.staff_income_taxes = 0
            if request.insurance == True:
                request.social_insurance = (request.wage * 8) / 100
            elif request.insurance != True:
                request.social_insurance = 0
            request.total_gross_salary = (
                    request.basic_monthly_salary + request.cola + request.housing_allowance + request.transportation_allowance + request.hazard)
            request.deduction = (request.social_insurance + request.staff_income_taxes)
            request.total_salary = (
                                           request.basic_monthly_salary + request.cola + request.housing_allowance + request.transportation_allowance + request.hazard) - (
                                           request.social_insurance + request.staff_income_taxes)


class HrContractLine(models.Model):
    _name = 'contract.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'project_id'
    _order = 'create_date desc, id desc'

    salary = fields.Float(string="Salary")  # or whatever field type it should be
    sequence = fields.Integer(string='sequence', default=10)
    contract_id = fields.Many2one('hr.contract', string='Contract')
    project_id = fields.Many2one('project.project', domain="[('state','=','running')]", string='Project')
    currency_id = fields.Many2one('res.currency', string="Currency", readonly=True,
                                  default=lambda self: self.env['res.currency'].search([('name', '=', 'USD')],
                                                                                     limit=1))
    project_salary = fields.Monetary(string='Gross Salary', tracking=True)
    employee_id = fields.Many2one(related="contract_id.employee_id", string="Employee", tracking=True)
    project_basic_salary = fields.Monetary(string='Basic Salary (36.5%)', store=True,
                                           compute='_compute_project_salary_of_employee', tracking=4)
    project_cola = fields.Monetary(string='COLA (23.5%)  ', compute='_compute_project_salary_of_employee',
                                   store=True, tracking=4)
    project_transportation = fields.Monetary(string='Transport (LTA) (20%)',
                                             compute='_compute_project_salary_of_employee', store=True, tracking=4)
    project_housing = fields.Monetary(string='Housing  (10%)', compute='_compute_project_salary_of_employee',
                                      store=True, tracking=4)
    project_hazard = fields.Monetary(string='Hazard (10%)', store=True, tracking=4,
                                     compute='_compute_project_salary_of_employee')

    p_total_salary = fields.Monetary(string='Net Salary', store=True, tracking=4,
                                     compute='_compute_project_salary_of_employee')

    project_insurance = fields.Monetary(string='Social Insurance  (8%)',
                                        compute='_compute_project_salary_of_employee', store=True, tracking=4)
    project_taxes = fields.Monetary(string='taxes (20%)', compute='_compute_project_salary_of_employee', store=True,
                                    tracking=4)
    state = fields.Selection([
        ('stop', 'Stop'),
        ('run', 'Running'),
        ('cancel', 'Cancel'),
        ('done', 'Done')
    ], 'Status', default='stop', tracking=True)
    taxes_include = fields.Boolean(string='Taxes', tracking=True)
    insurance_include = fields.Boolean(string='Social Insurance', tracking=True)
    curr_id = fields.Many2one('res.currency', string="Currency",
                              default=lambda self: self.env['res.currency'].search([('name', '=', 'USD')], limit=1),
                              readonly=False, tracking=True)
    loan_subtract = fields.Boolean(string="Loan Deduction?", tracking=True)
    advance_subtract = fields.Boolean(string="Advance Deduction?", tracking=True)
    start_date = fields.Date(string='Start Date', required=False)
    end_date = fields.Date(required=False, tracking=True, string="End Date")
    number_of_months = fields.Char(string='Duration', compute='_compute_number_of_months', store=True)

    def _cron_update_project_status(self):
        today = date.today()
        # هنا استهدفنا فقط المشاريع اللي حالتها 'run' وتاريخها انتهى
        expired_records = self.search([
            ('end_date', '<', today),
            ('state', '=', 'run')
        ])
        
        if expired_records:
            expired_records.write({'state': 'done'})

    @api.onchange('end_date')
    def _onchange_end_date(self):
        if self.end_date and self.end_date < fields.Date.today():
            if self.state == 'run':
                self.state = 'done'


    @api.depends('start_date', 'end_date')
    def _compute_number_of_months(self):
        for rec in self:
            if rec.start_date and rec.end_date:
                # حساب الفرق بين التاريخين
                diff = relativedelta(rec.end_date, rec.start_date)
                
                # تحويل السنين لشهور وإضافتها لفرق الشهور
                # +1 عشان نحسب الشهر الحالي (مثلاً من شهر 1 لـ شهر 4 هي 4 شهور حسابياً في بيئة العمل)
                total_months = (diff.years * 12) + diff.months + 1
                
                # وضع النتيجة في نص
                rec.number_of_months = f"{total_months} Months"
            else:
                rec.number_of_months = "0 Months"

    @api.onchange('state')
    def _onchange_state_update_contract(self):
        """
        عند تغيير الحالة يدوياً من القائمة المنسدلة، نقوم بتحديث 
        الحقول المحسوبة في العقد الأب فوراً قبل الحفظ.
        """
        for line in self:
            if line.contract_id:
                # استدعاء دالة الحساب لضمان إعادة توزيع الأسطر (Active/History)
                # وتحديث مبالغ الـ Hybrid والـ Wage لحظياً
                line.contract_id._compute_project_lines()

    def button_start(self):
        for line in self:
            salary_line = self.env['project.salary.line'].search(
                [('contract_line_id', '=', line.id), ('employee_id', '=', line.contract_id.employee_id.id)])
            salary_line.write({'state': 'run'})
            line.write({'state': 'run'})

    def button_pending(self):
        for line in self:
            salary_line = self.env['project.salary.line'].search(
                [('contract_line_id', '=', line.id), ('employee_id', '=', line.contract_id.employee_id.id)])
            salary_line.write({'state': 'stop'})
            line.write({'state': 'stop'})

    def button_block(self):
        for line in self:
            salary_line = self.env['project.salary.line'].search(
                [('contract_line_id', '=', line.id), ('employee_id', '=', line.contract_id.employee_id.id)])
            salary_line.write({'state': 'cancel'})
            line.write({'state': 'cancel'})

    def button_finish(self):
        for line in self:
            salary_line = self.env['project.salary.line'].search(
                [('contract_line_id', '=', line.id), ('employee_id', '=', line.contract_id.employee_id.id)])
            if salary_line:
                salary_line.write({'state': 'done'})
            line.write({'state': 'done'})
            
        # أهم سطر: إعادة تحميل الصفحة لضمان ظهور السطر في الهيستوري وتحديث الراتب
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.depends('project_salary', 'taxes_include', 'insurance_include')
    def _compute_project_salary_of_employee(self):
        for request in self:
            request.project_basic_salary = (request.project_salary * 36.5) / 100
            request.project_cola = (request.project_salary * 23.5) / 100
            request.project_housing = (request.project_salary * 10) / 100
            request.project_transportation = (request.project_salary * 20) / 100
            request.project_hazard = (request.project_salary * 10) / 100
            if request.taxes_include == True:
                request.project_taxes = (request.project_basic_salary * 20) / 100
            elif request.taxes_include != True:
                request.project_taxes = 0
            if request.insurance_include == True:
                request.project_insurance = (request.project_salary * 8) / 100
            elif request.insurance_include != True:
                request.project_insurance = 0
            request.p_total_salary = (
                                                 request.project_basic_salary + request.project_cola + request.project_housing + request.project_transportation + request.project_hazard) - (
                                             request.project_taxes + request.project_insurance)

    @api.model_create_multi
    def create(self, vals_list):
        lines = super(HrContractLine, self).create(vals_list)
        for line in lines:
            if line.contract_id:
                # رسالة عند إضافة سطر جديد
                msg = _("New project line added: %s with salary %s") % (line.project_id.display_name, line.project_salary)
                line.contract_id.message_post(body=msg)
        return lines

    def write(self, vals):
        # 1. جلب المسميات البرمجية للحقول التي نريد مراقبتها
        # يمكنك إضافة أو حذف أي حقل من هذه القائمة
        tracked_fields = [
            'project_salary', 'project_id', 'state', 'taxes_include', 
            'insurance_include', 'curr_id', 'loan_subtract', 'advance_subtract'
        ]
        
        for line in self:
            changes = []
            for field in vals:
                if field in tracked_fields:
                    # جلب المسمى الظاهر للحقل (String)
                    field_string = self._fields[field].string
                    # جلب القيمة القديمة والقيمة الجديدة
                    old_value = line[field].display_name if hasattr(line[field], 'display_name') else line[field]
                    new_value = vals[field] # في حالة Many2one قد تحتاج لمعالجة إضافية للاسم
                    
                    changes.append(_("<li><b>%s</b>: %s &rarr; %s</li>") % (field_string, old_value, new_value))
            
            # إذا وجدت تغييرات، أرسلها في رسالة واحدة منظمة
            if changes and line.contract_id:
                msg = _("Update in Project Line (%s):<ul>%s</ul>") % (line.project_id.display_name, "".join(changes))
                line.contract_id.message_post(body=msg)
                
        return super(HrContractLine, self).write(vals)

    def unlink(self):
        for line in self:
            if line.contract_id:
                # رسالة عند حذف السطر
                msg = _("Project line deleted: %s") % (line.project_id.display_name)
                line.contract_id.message_post(body=msg)
        return super(HrContractLine, self).unlink()