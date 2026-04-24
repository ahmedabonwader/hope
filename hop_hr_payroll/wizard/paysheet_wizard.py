from odoo import api, fields, models, _
from datetime import datetime
from datetime import date


class PaysheetWizard(models.TransientModel):
    _name = 'paysheet.wizard'
    _description = "Paysheet Wizard"

    payslip_id = fields.Many2one('payslips.batches', string='Payslip')
    print_type = fields.Selection([('with_signature', 'With Signature'), ('without_signature', 'Without Signature')], string='Print Type')


    def action_print_report(self):
        for rec in self:
            rec.payslip_id.print_type = rec.print_type

            action = self.env.ref('hop_hr_payroll.report_payslips_batches').report_action(rec.payslip_id)

            action['context'] = {
                'active_model': 'payslips.batches',
                'active_ids': [rec.payslip_id.id],
                'active_id': rec.payslip_id.id,
            }

            return action