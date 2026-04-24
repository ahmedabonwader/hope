from odoo import models, fields, api
from datetime import date
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from dateutil import relativedelta
from datetime import date
import datetime


class CertificateCompletion(models.Model):
    _name = 'certificate.completion'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Certificate Completion'
    _rec_name = 'ref'
    _order = 'id desc'

    branch_id = fields.Many2one('oms.branch', string='Branch', tracking=True)
    ref = fields.Char(string='Reference', tracking=True)
    user_id = fields.Many2one('res.users', String="User", tracking=True, default=lambda self: self.env.user.id)
    suppliers = fields.Many2one('res.partner', string="Suppliers", tracking=True)
    project_id = fields.Many2one('project.project', string="Project", tracking=True)
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company.id, tracking=True
    )
    time = fields.Date(string="Time", default=fields.Date.context_today, readonly=False, tracking=True)
    purchase_order = fields.Many2one('purchase.order', string="Purchase Order", tracking=True)
    prs = fields.Many2one('project.purchase.request', string="PRS", tracking=True)
    task_id = fields.Many2many('project.task', string="Activity")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('complete', 'Completed'),
    ], string='Status', default='draft', tracking=True)
    sign_approved = fields.Char(string="Sign Approved")
    signature_approved = fields.Many2one('res.users', string="Approved by")
    date_approve = fields.Date(string="Approved Date", readonly=True)
    note = fields.Text(string="Note")
    prepared_job_title = fields.Char(string="Prepared Job Title", compute="_compute_prepared_job_title", store=True)
    approved_job_title = fields.Char(string="Approved Job Title", compute="_compute_approved_job_title", store=True)

    @api.depends('signature_approved')
    def _compute_approved_job_title(self):
        for rec in self:
            if rec.signature_approved:
                emp_search = self.env['hr.employee'].search([
                    ('user_id', '=', rec.signature_approved.id)
                ], limit=1)
                if emp_search and emp_search.job_id:
                    rec.approved_job_title = emp_search.job_id.name
                else:
                    rec.approved_job_title = False
            else:
                rec.approved_job_title = False

    @api.depends('user_id')
    def _compute_prepared_job_title(self):
        for rec in self:
            if rec.user_id:
                emp_search = self.env['hr.employee'].search([
                    ('user_id', '=', rec.user_id.id)
                ], limit=1)
                if emp_search and emp_search.job_id:
                    rec.prepared_job_title = emp_search.job_id.name
                else:
                    rec.prepared_job_title = False
            else:
                rec.prepared_job_title = False

    def action_confirm(self):
        for record in self:
            if not record.note:
                raise ValidationError(_("Please Enter the Certificate Note before confirming."))
            record.state = 'confirm'

    def action_approve(self):
        for rec in self:
            rec.sign_approved = str(self.env.user.name)
            rec.signature_approved = self.env.user.id
            rec.date_approve = fields.Date.context_today(self)
            rec.purchase_order.is_service = True
            rec.state = 'complete'

    def action_reset_to_draft(self):
        for record in self:
            record.state = 'draft'

    def action_print_certificate_completion_report(self):
        action = self.env.ref('bid_tender.action_prints_certificate_completion_report_template').read()[0]
        return action

    @api.model
    def create(self, vals):
        vals['ref'] = self.env['ir.sequence'].next_by_code('certificate.completion')
        return super(CertificateCompletion, self).create(vals)