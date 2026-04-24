# -*- coding: utf-8 -*-

from odoo import fields, api, models, _
import datetime
from dateutil.relativedelta import relativedelta

class ContractTemplateWizard(models.TransientModel):
    _name = "contract.template.wizard"
    _description = "Contract Template Wizard"

    employee_id = fields.Many2one('hr.employee', string="Employee")
    department_id = fields.Many2one(related='employee_id.department_id', string="Department")
    job_id = fields.Many2one(related='employee_id.job_id', string="Job Title")
    contract_id = fields.Many2one('hr.contract', string="Contract")
    contract_type = fields.Selection(related="contract_id.contract_type")
    office_location_id = fields.Many2one('hope.office', string="HQ Office Location")
    employee_office_location_id = fields.Many2one('hope.office', string="Employee Office Location")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, readonly=True)
    salary_payment_type = fields.Selection([
        ('bank_rate', 'Paid in SDG (Bank Rate)'),
        ('direct_usd', 'Paid in USD directly')
    ], string="Salary Payment Method")
    
    printing_type = fields.Selection([
        ('main', 'Main Contract (Operation)'),
        ('project', 'Project Specific Contract')
    ], string="Printing Type")
    
    contract_line_id = fields.Many2one(
        'contract.line', 
        string="Select Project",
        domain="[('contract_id', '=', contract_id), ('state', '=', 'run')]"
    )
    
    work_location_id = fields.Many2one('hr.work.location', string="Work Location")
    has_field_visits = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No')
    ], string="Field Visits?", default='no')
    
    # الحقل المحسوب الذي يظهر في الويزارد ويُستخدم في التقرير
    duration_text_field = fields.Char(string="Duration Text", compute="_compute_duration_text", store=True)

    @api.depends('printing_type', 'contract_line_id', 'contract_id')
    def _compute_duration_text(self):
        for rec in self:
            d_start, d_end = False, False
            if rec.printing_type == 'project' and rec.contract_line_id:
                d_start = rec.contract_line_id.start_date
                d_end = rec.contract_line_id.end_date
            elif rec.contract_id:
                d_start = rec.contract_id.date_start
                d_end = rec.contract_id.date_end

            if d_start and d_end:
                diff = relativedelta(d_end + datetime.timedelta(days=1), d_start)
                total_months = (diff.years * 12) + diff.months
                
                def get_suffix(d):
                    return 'th' if 11 <= d <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(d % 10, 'th')

                fmt_start = d_start.strftime(f'%B %d{get_suffix(d_start.day)} %Y')
                fmt_end = d_end.strftime(f'%B %d{get_suffix(d_end.day)} %Y')
                
                rec.duration_text_field = f"{total_months:02d} months, starting from {fmt_start} to {fmt_end}"
            else:
                rec.duration_text_field = "Not Specified"

    def action_validate(self):
        self.ensure_one()
        report_data = []
        
        # 1. المسمى الوظيفي (فصل الوظيفة عن المشروع للتحكم في الـ Bold)
        job_title = self.job_id.name or ""
        project_suffix = ""
        if self.printing_type == 'project' and self.contract_line_id:
            project_code = self.contract_line_id.project_id.project_code or self.contract_line_id.project_id.name
            project_suffix = f" for {project_code}"

        # 2. الموقع (فصل اسم الموقع عن جملة الزيارات)
        main_location = self.work_location_id.name or ""
        location_suffix = " with frequent visit to project field." if self.has_field_visits == 'yes' else ""

        # 3. المدير المباشر (Reports to)
        manager_name = self.employee_id.parent_id.job_id.name or "N/A"

        hq = self.office_location_id
        state = self.employee_office_location_id
        director_name = f"Mr. {hq.country_director.name}" if hq and hq.country_director else ""

        if self.printing_type == 'project' and self.contract_line_id:
            # البيانات تُسحب من سطر المشروع (HrContractLine)
            line = self.contract_line_id
            salary_data = {
                'basic': line.project_basic_salary,
                'cola': line.project_cola,
                'transport': line.project_transportation,
                'housing': line.project_housing,
                'hazard': line.project_hazard,
                'total_gross': line.project_salary,
            }
            pos_title = f"{self.job_id.name} for {line.project_id.project_code or line.project_id.name}"
            curr_name = line.curr_id.name or "USD"
        else:
            # البيانات تُسحب من العقد الأساسي (HrContract)
            contract = self.contract_id
            salary_data = {
                'basic': contract.basic_monthly_salary,
                'cola': contract.cola,
                'transport': contract.transportation_allowance,
                'housing': contract.housing_allowance,
                'hazard': contract.hazard,
                'total_gross': contract.wage,
            }
            pos_title = self.job_id.name
            curr_name = contract.curr_id.name or "USD"

        if self.salary_payment_type == 'bank_rate':
            salary_text = "The monthly gross salary will be paid in local currency (SDG) equivalent to a bank rate for the monthly payment, the details are below:"
        else:
            salary_text = "The monthly gross salary will be paid in United States Dollars (USD) directly, the details are below:"

        report_data.append({
            'employee': self.employee_id.name,
            'gender': self.employee_id.gender,
            'employee_address': self.employee_id.private_street or "",
            'employee_mobile': self.employee_id.phone or "",
            'employee_email': self.employee_id.private_email or "",
            'report_logo': self.company_id.logo.decode('utf-8') if self.company_id.logo else False,
            'has_offices': True if hq and state else False,
            'hq_address': hq.address if hq else "",
            'hq_mobile': hq.mobile if hq else "",
            'hq_email': hq.email if hq else "",
            'hq_director': director_name,
            'state_address': state.address if state else "",

            # البيانات الجديدة والمحدثة
            'job_title': job_title,
            'project_suffix': project_suffix,
            'duration_val': self.duration_text_field,
            'main_location': main_location,
            'location_suffix': location_suffix,
            'manager_val': manager_name,
            'salary_payment_text': salary_text,
            'payment_method': self.salary_payment_type,
            'salary': salary_data,
            'currency': curr_name,
            'currency': self.contract_id.curr_id.name if self.contract_id.curr_id else ""
        })
        
        return self.env.ref('hop_hr_payroll.contract_template_reports').report_action(self, data={"data": report_data})