from odoo import models, fields, api
from datetime import date
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from dateutil import relativedelta
from datetime import date
import datetime


class SocialInsurancePayment(models.Model):
    _name = 'social.insurance.payment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Social Insurance Payment'
    _order = 'id desc'

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

    name = fields.Char(string="Description", required=True)
    date = fields.Date(string="Created Date", default=fields.Date.context_today)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('review', 'Reviewed'),
        ('approve', 'Approved'),
        ('done', 'Done'),
        ('cancel', 'Canceled'),
    ], default='draft', required=True, tracking=True, string="Status")
    ref = fields.Char(string='Reference', tracking=True)
    user_id = fields.Many2one('res.users', String="User", tracking=True, readonly=True,
                              default=lambda self: self.env.user.id)
    project_id = fields.Many2one('project.project', string="Project")
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company.id
    )
    payslips_batches_ids = fields.Many2many('payslips.batches', string="Payslips")
    total_amount = fields.Float(string="Total Amount")
    operation_type = fields.Selection([
        ('social_insurance', 'Social Insurance'),
        ('taxes', 'Taxes'),
    ], string="Operation Type")
    salary_type = fields.Selection([
        ('by_project', 'By Project'),
        ('by_contract', 'By Contract'),
    ], default="by_project")
    currency_id = fields.Many2one('res.currency', string="Currency",
                                  default=lambda self: self.env['res.currency'].search([('name', '=', 'SDG')], limit=1))
    budget_line = fields.Many2one('budget.iteme.line', string="Budget Line")
    account_id = fields.Many2one('account.account', string="Account", tracking=True)
    branch_id = fields.Many2one('oms.branch', string='Branch', default=_get_default_branch, domain=_get_user_branch)
    approval_currency_id = fields.Many2one('res.currency', string="Approval Currency",
                                           compute="_compute_approval_currency_id", store=True)
    amount_in_currency = fields.Float(string="Amount In Currency", compute="_compute_amount_in_currency", store=True)
    bill_count = fields.Integer(string="Bill Count", compute='_compute_bill_count', tracking=True)
    craeted_bill = fields.Boolean(string="Created Bill")

    def _compute_bill_count(self):
        for rec in self:
            bill_count = self.env['account.move'].search_count([('insurance_payment_id', '=', rec.id)])
            rec.bill_count = bill_count

    def action_bill_count(self):
        result = self.env['ir.actions.act_window']._for_xml_id('account.action_move_in_invoice_type')
        result['domain'] = [('insurance_payment_id', '=', self.id)]
        return result

    @api.depends('total_amount', 'approval_currency_id')
    def _compute_amount_in_currency(self):
        for rec in self:
            if rec.total_amount > 0 and rec.currency_id != rec.approval_currency_id:
                rec.amount_in_currency = rec.total_amount * rec.approval_currency_id.rate_ids.company_rate                                        

    @api.onchange('payslips_batches_ids', 'operation_type')
    def onchange_total_amount(self):
        for rec in self:
            if rec.payslips_batches_ids:
                for payslips in rec.payslips_batches_ids:
                    if rec.operation_type == 'social_insurance':
                        if payslips.insurance_payment is True:
                            rec.payslips_batches_ids = [(6, 0, [])]  # ← مسح السجلات
                            raise ValidationError(_("Sorry You Already Paid Social Insurance Payment For This Month !!!"))

                        rec.total_amount = sum(rec.payslips_batches_ids.mapped('total_social_insurance'))

                    elif rec.operation_type == 'taxes':
                        if payslips.taxes_payment is True:
                            rec.payslips_batches_ids = [(6, 0, [])]  # ← مسح السجلات
                            raise ValidationError(_("Sorry You Already Paid Taxes Payment For This Month !!!"))

                        rec.total_amount = sum(rec.payslips_batches_ids.mapped('total_taxes'))

            else:
                rec.total_amount = 0.0


    def unlink(self):
        if self.state != 'draft':
            raise ValidationError(_("You can delete record only in draft state"))
        else:
            return super(SocialInsurancePayment, self).unlink()

    @api.model
    def create(self, vals):
        vals['ref'] = self.env['ir.sequence'].next_by_code('social.insurance.payment')
        return super(SocialInsurancePayment, self).create(vals)

    def write(self, vals):
        if not self.ref:
            vals['ref'] = self.env['ir.sequence'].next_by_code('social.insurance.payment')
        return super(SocialInsurancePayment, self).write(vals)

    def action_confirm(self):
        for rec in self:
            rec.state = 'confirm'

    def action_review(self):
        for rec in self:
            rec.state = 'review'

    def action_back(self):
        for rec in self:
            rec.state = 'draft'

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

    def action_approve(self):
        for rec in self:
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
                                        print('$$$$')
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
            rec.state = 'approve'

    def action_done(self):
        for rec in self:
            rec.state = 'done'

    def action_create_bill(self):
        for rec in self:

            # =============================
            # 1) اختيار الاسم حسب العملية
            # =============================
            if rec.operation_type == 'social_insurance':
                vendor_name = "Social Insurance"
                line_name = "Social Insurance Payment"

            elif rec.operation_type == 'taxes':
                vendor_name = "Taxes"
                line_name = "Taxes Payment"

            else:
                raise ValidationError("Operation Type is not defined!")

            # ========================================================
            # 2) التأكد هل توجد فاتورة مسبقًا لنفس العملية
            # ========================================================
            account_move_id = self.env['account.move'].search([
                ('insurance_payment_id', '=', rec.id),
                ('move_type', '=', 'in_invoice'),
            ], limit=1)

            if account_move_id:
                continue  # الفاتورة موجودة مسبقًا – لا ننشئ واحدة أخرى

            # ========================================================
            # 3) البحث عن المورد (Vendor)، وإذا غير موجود → إنشاءه
            # ========================================================
            partner = self.env['res.partner'].search([
                ('name', '=', vendor_name),
            ], limit=1)

            if not partner:
                partner = self.env['res.partner'].create({
                    'name': vendor_name,
                })

            # ========================================================
            # 4) إنشاء الفاتورة (Bill)
            # ========================================================
            bill_vals = {
                'partner_id': partner.id,
                'project_id': rec.project_id.id,
                'project_type': 'new_project',
                'branch_id': rec.branch_id.id,
                'move_type': 'in_invoice',
                'insurance_payment_id': rec.id,
                'invoice_line_ids': [(0, 0, {
                    'account_id': rec.account_id.id,
                    'name': line_name,                     # ← الاسم يعتمد على نوع العملية
                    'budget_item_line_id': rec.budget_line.id,
                    'quantity': 1,
                    'price_unit': rec.total_amount,
                    'tax_ids': False,
                })],
            }

            account_move = self.env['account.move'].create(bill_vals)

            # ========================================================
            # 5) تحديث الاستحقاق في الـ payslips
            # ========================================================
            for payslips in rec.payslips_batches_ids:
                if rec.operation_type == 'social_insurance':
                    payslips.insurance_payment = True
                elif rec.operation_type == 'taxes':
                    payslips.taxes_payment = True

            rec.craeted_bill = True

            