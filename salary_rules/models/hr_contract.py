# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError


class HrContract(models.Model):
    _inherit = 'hr.contract'

    basic_monthly_salary = fields.Monetary(string='Basic Monthly Salary (36%)', store=True,
                                           compute='_compute_salary_of_employee', tracking=4)
    living_allowance = fields.Monetary(string='Living Allowance (10%)  ', compute='_compute_salary_of_employee',
                                       store=True, tracking=4)
    housing_allowance = fields.Monetary(string='Housing Allowance (10%)', compute='_compute_salary_of_employee',
                                        store=True, tracking=4)
    transportation_allowance = fields.Monetary(string='Leaving transportation Allowances (LTA) (30%)',
                                               compute='_compute_salary_of_employee', store=True, tracking=4)
    hazard = fields.Monetary(string='Hazard (14%)', store=True, tracking=4, compute='_compute_salary_of_employee')
    social_insurance = fields.Monetary(string='Withholding Social Insurance Contribution (8%) from staff',
                                       compute='_compute_salary_of_employee', store=True, tracking=4)
    staff_income_taxes = fields.Monetary(string='Total Staff Income taxes',  compute='_compute_salary_of_employee', store=True, tracking=4)
    insurance = fields.Boolean(string="Insurance Included")
    taxes = fields.Boolean(string="Insurance taxes")
    total_salary = fields.Monetary(string='Sub-Total Salary of the Employee (Net  Salary)', store=True,

                                   tracking=4)

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
            request.basic_monthly_salary = (request.wage * 36) / 100
            request.living_allowance = (request.wage * 10) / 100
            request.housing_allowance = (request.wage * 10) / 100
            request.transportation_allowance = (request.wage * 30) / 100
            request.hazard = (request.wage * 14) / 100
            request.social_insurance = (request.wage * 8) / 100
            if request.taxes == True:
                request.staff_income_taxes = (request.basic_monthly_salary * 20) / 100
            elif request.taxes != True:
                request.staff_income_taxes = 0
            if request.insurance == True:
                request.social_insurance = (request.wage * 8) / 100
            elif request.insurance != True:
                request.social_insurance = 0
            request.total_salary = (request.basic_monthly_salary + request.living_allowance + request.housing_allowance + request.transportation_allowance + request.hazard  )  -(request.social_insurance + request.staff_income_taxes)


