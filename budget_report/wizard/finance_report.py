from odoo import models, fields, api, _
from datetime import datetime

class FinanceReport(models.TransientModel):
    _name = 'finance.report.wizard'
    _description = "Print Finance Report Wizard"

    budget_id = fields.Many2one('crossovered.budget', string="Budget", required=True)
    quarter_ids = fields.Many2many('crossovered.budget.lines', string="Quarters", domain="[('crossovered_budget_id' ,'=',budget_id)]", required=True)
    date_from = fields.Date(string="Date From")
    date_to = fields.Date(string="Date To")
    budget_state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('validate', 'Validated'),
        ('done', 'Done'),
    ], string="Budget State", default="validate")
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company.id
    )
    report_type = fields.Selection([
        ('summary', 'Summary'),
        ('detail', 'Details'),
    ], string="Report Type", default="detail")
    budget_line_id = fields.Many2one('budget.iteme.line', string="Budget Code")
    project_id = fields.Many2one(related="budget_id.project_id", string="Project")
    more_details = fields.Boolean(string="More Details")

    @api.onchange('budget_id')
    def onchange_more_details(self):
        for rec in self:
            if rec.budget_id:
                rec.more_details = rec.budget_id.more_details
   
    def action_print_report(self):
        for rec in self:
            header_data = []
            quarter_data = []
            has_more_details = False

            # Get budget quarters based on selected quarter_ids
            budget_quarters = self.env['budget.quarte'].search([
                ('budget_id', '=', rec.budget_id.id),
                ('project_id', '=', rec.budget_id.project_id.id),
                ('budget_line_id', 'in', rec.quarter_ids.ids)
            ])

            # Collect all selected quarters information
            quarters_info = {}
            selected_quarters = []
            
            if budget_quarters:
                for finance_report in budget_quarters:
                    quarter_name = finance_report.budget_line_id.quarter
                    if quarter_name not in selected_quarters:
                        selected_quarters.append(quarter_name)
                    
                    quarters_info[quarter_name] = {
                        'finance_report': finance_report,
                        'quarter_lines': finance_report.quarter_line_ids
                    }

                # Sort quarters
                selected_quarters.sort()

                # Determine if single or multiple quarters
                is_single_quarter = len(selected_quarters) == 1

                # Build header data with all selected quarters
                first_quarter_data = list(quarters_info.values())[0]['finance_report']
                header_data.append({
                    'project_title': first_quarter_data.project_id.name,
                    'company_name': rec.company_id.name,
                    'quarter': ', '.join(selected_quarters),  # Show all selected quarters
                    'start_date': first_quarter_data.budget_id.date_from,
                    'end_date': first_quarter_data.budget_id.date_to,
                    'approve_by': first_quarter_data.budget_id.signature_approved.name if first_quarter_data.budget_id.signature_approved else '',
                    'approve_date': first_quarter_data.budget_id.approve_date,
                    'validate_date': first_quarter_data.budget_id.review_date,
                    'reviewed_by': first_quarter_data.budget_id.signature_reviewed.name if first_quarter_data.budget_id.signature_reviewed else '',
                    'prepared': first_quarter_data.budget_id.create_by.name if first_quarter_data.budget_id.create_by else '',
                    'prepared_date': first_quarter_data.budget_id.create_date,
                    'prepared_signature': first_quarter_data.budget_id.create_by.digital_signature if first_quarter_data.budget_id.create_by else '',
                    'signature_reviewed': first_quarter_data.budget_id.signature_reviewed.digital_signature if first_quarter_data.budget_id.signature_reviewed else '',
                    'signature_approved': first_quarter_data.budget_id.signature_approved.digital_signature if first_quarter_data.budget_id.signature_approved else '',
                    'prepared_job_title': first_quarter_data.budget_id.prepared_job_title,
                    'reviewed_job_title': first_quarter_data.budget_id.reviewed_job_title,
                    'approved_job_title': first_quarter_data.budget_id.approved_job_title,
                    'budget_line_name': rec.budget_line_id.line_code if rec.budget_line_id else '',
                })

                # Process each quarter separately (keeping original structure)
                for quarter_name in selected_quarters:
                    quarter_info = quarters_info[quarter_name]
                    finance_report = quarter_info['finance_report']
                    quarter_details = []

                    # Get budget lines for this specific quarter
                    budget_lines = finance_report.budget_id.budget_iteme_lines
                    if rec.budget_line_id:
                        budget_lines = budget_lines.filtered(lambda l: l.id == rec.budget_line_id.id)

                    quarter_lines = quarter_info['quarter_lines']

                    for idx, budget_line in enumerate(budget_lines):
                        if budget_line.more_details:
                            has_more_details = True

                        # Get the corresponding quarter line data
                        quarter_amount = 0
                        actual_expenditure = 0
                        
                        if idx < len(quarter_lines):
                            quarter_amount = quarter_lines[idx].planned_amount or 0
                            actual_expenditure = quarter_lines[idx].theoritical_amount or 0

                        data = {
                            'budget_line': budget_line.line_code,
                            'description': budget_line.description,
                            'total_budget': budget_line.budget_line_planned_amount,
                            'actual_expenditure': actual_expenditure,
                            'allowed_increase': budget_line.allowed_increase,
                            'balance': (budget_line.budget_line_planned_amount or 0) - actual_expenditure,
                            'spent': budget_line.burn_rate,
                            'installment': quarter_amount,
                            'currency': budget_line.currency_id.symbol if budget_line.currency_id else '',
                            'quarter_name': quarter_name,
                        }

                        if budget_line.more_details:
                            data.update({
                                'state': budget_line.budget_state.name if budget_line.budget_state else '',
                                'budget_account': budget_line.budget_account.name if budget_line.budget_account else '',
                            })

                        quarter_details.append(data)

                    quarter_data.append({
                        'name': quarter_name,
                        'key': finance_report.name,
                        'data': quarter_details
                    })

            # Calculate totals across all quarters
            all_items = []
            for q in quarter_data:
                all_items.extend(q['data'])

            # Group by budget line to calculate proper totals
            budget_line_totals = {}
            for item in all_items:
                budget_line = item['budget_line']
                if budget_line not in budget_line_totals:
                    budget_line_totals[budget_line] = {
                        'total_budget': item['total_budget'],
                        'total_actual_expenditure': 0,
                        'total_installment': 0,
                        'allowed_increase': item['allowed_increase'],
                        'currency': item['currency']
                    }
                budget_line_totals[budget_line]['total_actual_expenditure'] += item['actual_expenditure']
                budget_line_totals[budget_line]['total_installment'] += item['installment']

            # Calculate final totals
            total_budget = sum(line_data['total_budget'] or 0 for line_data in budget_line_totals.values())
            total_actual_expenditure = sum(line_data['total_actual_expenditure'] for line_data in budget_line_totals.values())
            total_installment = sum(line_data['total_installment'] for line_data in budget_line_totals.values())
            total_allowed_increase = sum(line_data['allowed_increase'] or 0 for line_data in budget_line_totals.values())
            total_balance = total_budget - total_actual_expenditure
            spent_percent = (total_actual_expenditure / total_budget * 100) if total_budget else 0

            vals = {
                "data": all_items,
                "header": header_data,
                "quarter": quarter_data,
                "selected_quarters": selected_quarters,  # Add list of selected quarters
                "is_single_quarter": is_single_quarter,  # Add flag for single quarter display
                "summary": {
                    'sum_total_budget': total_budget,
                    'sum_installment': total_installment,
                    'sum_actual': total_actual_expenditure,
                    'sum_increase': total_allowed_increase,
                    'sum_balance': total_balance,
                    'spent_percent': spent_percent,
                },
                "has_more_details": has_more_details,
            }
            return self.env.ref('budget_report.budget_finance_report').report_action(self, data=vals)
