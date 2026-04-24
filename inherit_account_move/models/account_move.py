# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date
import datetime


class AccountMoveInherit(models.Model):
    _inherit = 'account.move'

    def _get_default_branch(self):
        users = self.env.user
        if len(users.branch_ids) == 1:
            return users.branch_ids[0]
        elif len(users.branch_ids) > 1:
            return self.env['oms.branch'].search([('id', 'in', [item.id for item in users.branch_ids])])
        return False

    def _get_user_branch(self):
        user = self.env.user
        branch_ids = user.branch_ids.ids
        return [('id', 'in', branch_ids)]

    branch_id = fields.Many2one('oms.branch', string='Branch', default=_get_default_branch, domain=_get_user_branch)
    project_id = fields.Many2one('project.project', string="Project")
    task_id = fields.Many2many('project.task', string="Activity")
    expense_id = fields.Many2one('hms.expense.request', 'Expense')
    comment = fields.Text(string="Comment")
    bank_transfer_ref = fields.Char(string="Bank Transfer Reference")
    comment_check = fields.Boolean(string="Comment Check")
    sign_prepared = fields.Many2one('res.users', string="Prepared By")
    signs_prepared = fields.Char(string="Prepared By")
    sign_reviewed = fields.Char(string="Sign Reviewed")
    sign_approved = fields.Char(string="Sign Approved")
    signature_reviewed = fields.Many2one('res.users', string="Signature Reviewed")
    signature_approved = fields.Many2one('res.users', string="Signature Approved")
    date_approve = fields.Date()
    date_review = fields.Date()
    date_prepared = fields.Date(default=fields.Date.context_today)
    users_id_ = fields.Many2one('res.users', String="User", tracking=True, readonly=True,
                                default=lambda self: self.env.user.id)
    state = fields.Selection(
        [('draft', 'Draft'), ('review', 'Reviewed'), ('approve', 'Approve'), ('posted', 'Posted'),
         ('cancel', 'Canceled'), ], default='draft')
    total_amount = fields.Float(string="Total Amount", compute="_compute_total_amount", store=True, )
    amount_in_currency = fields.Float(string="Amount In Currency", compute="_compute_amount_in_currency", store=True)
    approval_currency_id = fields.Many2one('res.currency', string="Approval Currency",
                                           compute="_compute_approval_currency_id", store=True, )
    project_type = fields.Selection([
        ('old_project', 'Old Data'),
        ('new_project', 'New Data'),
    ], string="Project Type")
    bill_type = fields.Selection([
        ('normal', 'Normal'),
        ('purchase', 'Purchase'),
        ('salary', 'Salary'),
        ('tor', 'TOR'),
    ], string="Bill Type", default="normal", compute="_compute_bill_type", store=True)
    purchase_order = fields.Many2one('purchase.order', string="Purchase Order ##")
    tor_advance_id = fields.Many2one('project.purchase.request', string="TOR/Advance##")
    old_approve = fields.Many2one('res.users', string="Old Approve")
    salary_payslips_id = fields.Many2one('payslips.batches', string="Salary Payslips")
    employee_id = fields.Many2one('hr.employee', string="Employee")
    prs = fields.Many2one('project.purchase.request', string="PRS")
    loan_advance_project = fields.Many2one('project.project', string="Loan Advance Project")
    tor_bill = fields.Boolean(string="TOR Bill?")
    tor_check = fields.Boolean(string="Tor Check")
    salary_check = fields.Boolean(string="Salary Check")
    prepared_job_title = fields.Char(string="Prepared Job Title", compute="_compute_prepared_job_title", store=True)
    reviewed_job_title = fields.Char(string="Reviewed Job Title", compute="_compute_reviewed_job_title", store=True)
    approved_job_title = fields.Char(string="Approved Job Title", compute="_compute_approved_job_title", store=True)
    bank_letter_count = fields.Integer(string="Bank Litter Count", compute='_compute_bank_letter_count', tracking=True)
    insurance_payment_id = fields.Many2one('social.insurance.payment', string="Insurance Payment")
    name_placeholder = fields.Char(string="Placeholder", store=False)

    def action_print_pdf(self):
        return self.action_invoice_print()

    # ودي برضه احتياطي لو ضربت معاك في الزرار التاني
    def action_invoice_sent(self):
        return super(AccountMoveInherit, self).action_invoice_sent()

    def _compute_bank_letter_count(self):
        for rec in self:
            bank_letter_count = self.env['bank.letters'].search_count([('bill_id', '=', rec.id)])
            rec.bank_letter_count = bank_letter_count

    def action_bank_letter_count(self):
        for rec in self:
            domain = [('bill_id', '=', rec.id)]
            return {
                'type': 'ir.actions.act_window',
                'name': 'bank_letter',
                'res_model': 'bank.letters',
                'domain': domain,
                'view_mode': 'list,form',
                'target': 'current',
            }

    @api.depends('users_id_')
    def _compute_prepared_job_title(self):
        for rec in self:
            if rec.users_id_:
                emp_search = self.env['hr.employee'].search([
                    ('user_id', '=', rec.users_id_.id)
                ], limit=1)
                if emp_search and emp_search.job_id:
                    rec.prepared_job_title = emp_search.job_id.name
                else:
                    rec.prepared_job_title = False
            else:
                rec.prepared_job_title = False

    @api.depends('signature_reviewed')
    def _compute_reviewed_job_title(self):
        for rec in self:
            if rec.signature_reviewed:
                emp_search = self.env['hr.employee'].search([
                    ('user_id', '=', rec.signature_reviewed.id)
                ], limit=1)
                if emp_search and emp_search.job_id:
                    rec.reviewed_job_title = emp_search.job_id.name
                else:
                    rec.reviewed_job_title = False
            else:
                rec.reviewed_job_title = False

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

    # @api.onchange('tor_advance_id')
    # def onchange_tor_advance_id(self):
    def action_set_tor_data(self):
        for rec in self:
            request_vals = []  # Initialize the list to store new invoice lines
            if not rec.tor_advance_id:
                raise ValidationError(_('Sorry Select The TOR Record First.'))
                # Clear existing invoice lines before populating new ones
            elif rec.tor_advance_id:
                rec.invoice_line_ids = False

                # Collect unique invoice lines from all TORs
                for tor in rec.tor_advance_id:
                    for line in tor.service_line_ids:
                        # Append a new invoice line to the request_vals list
                        request_vals.append((0, 0, {
                            'name': line.description_of_activities,
                            'budget_item_line_id': line.budget_line_code.id,
                            'qty': line.quantity,
                            'frequency': line.frequency,
                            'product_uom_id': line.unit_uom.id,
                            'price_unit': line.unit_price,
                            'quantity': line.quantity * line.frequency,
                            'account_id': line.account_id.id,
                        }))

                # Update invoice_line_ids only once after processing all TORs
                rec.invoice_line_ids = request_vals
            rec.tor_check = True

    @api.depends('tor_bill', 'salary_check')
    def _compute_bill_type(self):
        for rec in self:
            if rec.tor_bill == True:
                rec.bill_type = 'tor'
            else:
                rec.bill_type = 'normal'
            if rec.salary_check == True:
                rec.bill_type = 'salary'

    @api.depends('branch_id')
    def _compute_approval_currency_id(self):
        for rec in self:
            if rec.branch_id:
                branch_line = self.env['oms.branch.line'].search([
                    ('branch_id', '=', rec.branch_id.id),
                    ('emp_id', '=', self.env.user.name),
                ], limit=1)
                if branch_line:
                    rec.approval_currency_id = branch_line.currency_id.id

    @api.depends('invoice_line_ids.price_subtotal')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = 0.0
            for line_service in rec.invoice_line_ids:
                rec.total_amount += line_service.price_subtotal

    @api.depends('total_amount')
    def _compute_amount_in_currency(self):
        for rec in self:
            if rec.total_amount > 0 and rec.currency_id != rec.approval_currency_id:
                rec.amount_in_currency = rec.total_amount * rec.approval_currency_id.rate_ids.company_rate

    def action_review(self):
        for rec in self:
            if not rec.invoice_date:
                raise ValidationError(_('The Bill/Refund date is required to validate and review this document.'))
            if rec.tor_bill == True and not rec.tor_advance_id:
                raise ValidationError(_('Sorry Select The TOR Record First and you can review.######'))
            if rec.tor_check == False and rec.tor_bill == True:
                raise ValidationError(_('Sorry Add The TOR Record First and you can review.@@@@'))
            for line in rec.invoice_line_ids:
                if rec.project_id:
                    if not line.quarter_id:
                        raise ValidationError(_('Please add Quarter !!!'))
            rec.sign_reviewed = str(self.env.user.name)
            rec.signature_reviewed = self.env.user.id
            rec.date_review = date.today().strftime('%Y-%m-%d')
            rec.state = 'review'
            # if rec.tor_bill == True:
            #     rec.bill_type = 'tor'

    def action_approve(self):
        for rec in self:
            if rec.move_type == 'in_invoice':
                # action = self.env.ref('inherit_account_move.view_authorized_wizard_wizard_action').read()[0]
                if rec.project_id and rec.project_type == "old_project":
                    rec.sign_approved = str(self.env.user.name)
                    rec.signature_approved = self.env.user.id
                    rec.date_approve = date.today().strftime('%Y-%m-%d')
                    rec.state = 'approve'
                    # return action
                elif rec.project_id and rec.project_type == "new_project":
                    if rec.branch_id:
                        matched = False
                        for branch in rec.branch_id:
                            for line in branch.branch_line_ids:
                                if line.emp_id.name == self.env.user.name:
                                    matched = True
                                    if line.currency_id.id == rec.currency_id.id:
                                        if line.amount < rec.total_amount and line.is_admin == False:
                                            raise ValidationError(_(
                                                "You are not authorized to approve this.\n"
                                                "Your approval limit is %.2f %s, but the total amount is %.2f %s.\n"
                                                "Please ask your manager to approve this transaction."
                                            ) % (
                                                                      line.amount,
                                                                      line.currency_id.name,
                                                                      rec.total_amount,
                                                                      rec.currency_id.name
                                                                  ))
                                    elif line.currency_id.id != rec.currency_id.id:
                                        if line.amount < rec.amount_in_currency and line.is_admin == False:
                                            raise ValidationError(_(
                                                "You are not authorized to approve this.\n"
                                                "Your approval limit is %.2f %s, but the total amount (converted) is %.2f %s.\n"
                                                "Please ask your manager to approve this transaction."
                                            ) % (
                                                                      line.amount,
                                                                      line.currency_id.name,
                                                                      rec.amount_in_currency,
                                                                      line.currency_id.name
                                                                  ))
                        if not matched:
                            raise ValidationError(_("You are not assigned to approve this operation."))

                    rec.sign_approved = str(self.env.user.name)
                    rec.signature_approved = self.env.user.id
                    rec.date_approve = date.today().strftime('%Y-%m-%d')
                    rec.state = 'approve'
                elif not rec.project_id:
                    rec.sign_approved = str(self.env.user.name)
                    rec.signature_approved = self.env.user.id
                    rec.date_approve = date.today().strftime('%Y-%m-%d')
                    rec.state = 'approve'
            elif rec.move_type == 'in_refund':
                rec.state = 'approve'

    def actions_button_cancel(self):
        for rec in self:
            rec.state = 'cancel'

    def action_post(self):
        res = super(AccountMoveInherit, self).action_post()
        for rec in self:
            rec.signs_prepared = self.users_id_.name
            rec.sign_prepared = self.users_id_.id
        return res

    def action_back(self):
        for rec in self:
            if not rec.comment:
                if rec.project_id:
                    raise ValidationError(_('Please add Comment !!!'))
            self.sign_approved = False
            self.sign_reviewed = False
            rec.date_approve = False
            rec.date_review = False
            rec.date_prepared = False
            rec.state = 'draft'

    def action_print(self):
        action = self.env.ref('inherit_account_move.print_vendors_bills_reports').read()[0]
        return action


class AccountMoveInheritLine(models.Model):
    _inherit = 'account.move.line'

    # project_id = fields.Many2one(
    #     'project.project',
    #     string="Project",
    #     related='payment_id.project_id',
    #     store=True
    # )

    frequency = fields.Float(string="Frequency", default=1)
    qty = fields.Float(string="Quantity", default=1)
    bill_type = fields.Selection(related="move_id.bill_type")

    # @api.depends('payment_id.project_id', 'move_id.project_id')
    # def _compute_project_id(self):
    #     for rec in self:
    #         project = False
    #         if rec.payment_id and rec.payment_id.project_id:
    #             project = rec.payment_id.project_id.id
    #         elif rec.move_id and rec.move_id.project_id:
    #             project = rec.move_id.project_id.id
    #         rec.project_id = project
