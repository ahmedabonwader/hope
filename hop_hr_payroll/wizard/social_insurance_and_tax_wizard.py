from odoo import fields, api, models, _
from odoo.exceptions import ValidationError
from dateutil import relativedelta
from datetime import date
import datetime


class SocialInsuranceAndTaxWizard(models.TransientModel):
    _name = "social.insurance.tax.wizard"
    _description = "Social Insurance Wizard"

    operation_type = fields.Selection([
        ('social_insurance_report', 'Social Insurance Report'),
        ('tax_report', 'Tax Report'),
    ], string="Operation Type")
    payslip_id = fields.Many2one('payslips.batches', string="Payslips")
    signature_reviewed = fields.Many2one('res.users', string="Reviewed by")
    signature_approved = fields.Many2one('res.users', string="Approved by")
    signature_prepared = fields.Many2one('res.users', string="Prepared by")

    def action_validate(self):
        for rec in self:
            slip = rec.payslip_id
            if not slip:
                raise ValidationError(_("Please select Payslip"))

            if rec.operation_type == 'social_insurance_report':
                slip.signature_insuranse_tax_prepared = rec.signature_prepared.id
                slip.signature_insuranse_tax_reviewed = rec.signature_reviewed.id
                slip.signature_insuranse_tax_approved = rec.signature_approved.id
                slip.date_insuranse_tax_prepared = date.today()
                slip.date_insuranse_tax_review = date.today()
                slip.date_insuranse_tax_approve = date.today()

                action = self.env.ref(
                    'hop_hr_payroll.action_print_social_insurance_report'
                ).read()[0]

                action['context'] = {
                    'active_model': 'payslips.batches',
                    'active_ids': [slip.id],
                    'active_id': slip.id,
                }

                return action


            elif rec.operation_type == 'tax_report':
                slip.signature_insuranse_tax_prepared = rec.signature_prepared.id
                slip.signature_insuranse_tax_reviewed = rec.signature_reviewed.id
                slip.signature_insuranse_tax_approved = rec.signature_approved.id
                slip.date_insuranse_tax_prepared = date.today()
                slip.date_insuranse_tax_review = date.today()
                slip.date_insuranse_tax_approve = date.today()

                action = self.env.ref(
                    'hop_hr_payroll.action_print_taxes_report'
                ).read()[0]

                action['context'] = {
                    'active_model': 'payslips.batches',
                    'active_ids': [slip.id],
                    'active_id': slip.id,
                }

                return action

