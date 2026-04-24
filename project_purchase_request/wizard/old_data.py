from odoo import models, fields, api, _
from datetime import datetime

class OldDataWizard(models.TransientModel):
    _name = 'old.data.wizard'
    _description = "Old Data Wizard"

    model = fields.Selection([
        ('account_move', 'Account Move'),
        ('tor_prs', 'Tor/PRS'),
        ('expense', 'Expense'),
        ('bid/tender', 'Bid Tender'),
        ('purchase_order', 'Purchase Order'),
        ('budget', 'Budget'),
    ], string="For Model?", required=True)

    def action_update(self):
        for rec in self:
            if rec.model == 'tor_prs':
                # 1. جلب كل الـ TORs التي حالتها Done
                prs_tor = self.env['project.purchase.request'].search([
                    ('state', '=', 'done'),
                    ('created_bill', '=', False) # بحث فقط عن غير المحدثة لتوفير الوقت
                ])
                
                if prs_tor:
                    # 2. جلب كل الفواتير المرتبطة بهذه الطلبات دفعة واحدة
                    account_moves = self.env['account.move'].search([
                        ('move_type', '=', 'in_invoice'),
                        ('tor_advance_id', 'in', prs_tor.ids), # استخدام 'in' بدلاً من البحث الفردي
                    ])
                    
                    # 3. استخراج معرفات الـ TOR التي لها فواتير فعلاً
                    tor_ids_with_bills = account_moves.mapped('tor_advance_id').ids
                    
                    # 4. تحديث الكل بضغطة واحدة (Bulk Update)
                    if tor_ids_with_bills:
                        self.env['project.purchase.request'].browse(tor_ids_with_bills).write({
                            'created_bill': True
                        })

    def get_old_data(self):
        for rec in self:
            if rec.model == 'tor_prs':
                prs_tor = self.env['project.purchase.request'].search([
                    ('state', 'in', ('approved', 'done'))
                ])
                if prs_tor:
                    for data in prs_tor:
                        if not data.prepared_job_title:
                            emp_search = self.env['hr.employee'].search([
                                ('user_id', '=', data.requester_id.id)
                            ], limit=1)
                            if emp_search:
                                data.prepared_job_title = emp_search.job_id.name
                        if not data.reviewed_job_title:
                            emp_search = self.env['hr.employee'].search([
                                ('user_id', '=', data.signature_reviewed.id)
                            ], limit=1)
                            if emp_search:
                                data.reviewed_job_title = emp_search.job_id.name
                        if not data.approved_job_title:
                            emp_search = self.env['hr.employee'].search([
                                ('user_id', '=', data.signature_approved.id)
                            ], limit=1)
                            if emp_search:
                                data.approved_job_title = emp_search.job_id.name
            elif rec.model == 'budget':
                budget = self.env['crossovered.budget'].search([
                    ('state', 'in', ('validate', 'done'))
                ])
                if budget:
                    for data in budget:
                        if not data.prepared_job_title:
                            emp_search = self.env['hr.employee'].search([
                                ('user_id', '=', data.user_id.id)
                            ], limit=1)
                            if emp_search:
                                data.prepared_job_title = emp_search.job_id.name
                        if not data.reviewed_job_title:
                            emp_search = self.env['hr.employee'].search([
                                ('user_id', '=', data.signature_reviewed.id)
                            ], limit=1)
                            if emp_search:
                                data.reviewed_job_title = emp_search.job_id.name
                        if not data.approved_job_title:
                            emp_search = self.env['hr.employee'].search([
                                ('user_id', '', data.signature_approved.id)
                            ], limit=1)
                            if emp_search:
                                data.approved_job_title = emp_search.job_id.name