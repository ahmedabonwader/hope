from odoo import api, fields, models, _
from datetime import datetime
from datetime import date


class SalaryPaymentSheet(models.TransientModel):
    _name = 'salary.payment.sheet.report'
    _description = "Print Salary Payment Sheet Report"

    project_id = fields.Many2one('project.project', string="Project")
    batches_id = fields.Many2one('payslips.batches', string='Batches')
    salary_type = fields.Selection([
        ('by_project', 'By Project'),
        ('by_contract', 'By Contract'),
    ], string="Salary type")
    employee_id = fields.Many2one('payslips.batches.line', string='Employee')
    employee_id_contract = fields.Many2one('payslips.batches.line', string='Employee')
    user_id = fields.Many2one('res.users', string="User", default=lambda self: self.env.user.id)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, readonly=True)

    def action_print_report(self):
        for rec in self:
            report_data = []
            employee_lines = rec.employee_id if rec.salary_type == 'by_project' else rec.employee_id_contract
            if employee_lines:
                for emp_id in employee_lines:
                    report_data.append({
                        'staff_name': emp_id.employee_id.name,
                        'title': emp_id.employee_id.job_id.name,
                        'salary_type': rec.salary_type,
                        'state': emp_id.employee_id.state_id.name,
                        'gross_monthly_salary': emp_id.gross_salary_usd,
                        'basic_monthly_salary': emp_id.basic_monthly_salary,
                        'cola': emp_id.cola,
                        'project_name': rec.batches_id.project_id.name or 'N/A',
                        'transportation': emp_id.transportation,
                        'hazard': emp_id.hazard,
                        'housing': emp_id.housing,
                        'social_insurance': emp_id.insurance_usd,
                        'taxes': emp_id.taxes_usd,
                        'loan': emp_id.loan,
                        'advance': emp_id.advance,
                        'disciplinary_deduction': emp_id.disciplinary_deduction,
                        'reason_of_disciplinary_deduction': emp_id.reason,
                        'total_deductions': emp_id.total_deductions,
                        'net_salary': emp_id.net_salary,
                        'rate': 1 if emp_id.curr_id.name == 'SDG' else rec.batches_id.rate,
                        'salary_in_sdg': emp_id.salary_in_sdg,
                        'company_name': rec.company_id.name,
                        'report_logo': rec.company_id.logo.decode('utf-8') if rec.company_id.logo else False,
                        'month': f"{rec.batches_id.month} / {rec.batches_id.date.year}" if rec.batches_id.date and rec.batches_id.month else rec.batches_id.month,
                        'currency': emp_id.curr_id.name if emp_id.curr_id else '',
                        'date_from': rec.batches_id.date_from,
                        'date_to': rec.batches_id.date_to,
                        'date': rec.batches_id.date,
                        'currency_symbol': emp_id.curr_id.symbol if emp_id.curr_id else '',
                        'basic_salary_in_sdg': (emp_id.basic_monthly_salary or 0) * (
                            1 if emp_id.curr_id.name == 'SDG' else (rec.batches_id.rate or 0)
                        ),
                    })

            vals = {
                "data": report_data,
                "company": rec.company_id,
            }
            return self.env.ref('hop_hr_payroll.print_salary_payment_sheet_reports').report_action(self, data=vals)
