from tokenize import String

from odoo import models, fields, api
from datetime import date
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from dateutil import relativedelta
from datetime import date
import datetime


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    purchase_type = fields.Selection([
        ('purchase_order', 'Dirct Purchase'),
        ('bid_analysis', 'Bid Analysis'),
        ('tender', 'Tender'),
    ], default="purchase_order", string="Purchase Type", tracking=True)
    reason = fields.Text(string="Reason", related="bid_tender_id.reason")
    date_pur = fields.Date(string="Date")
    # fields.Date.context_today
    # partner_id = fields.Many2one(related="bid_tender_id.chosen_id")
    users_id = fields.Many2one('res.users', String="User", tracking=True, readonly=True,
                               related="bid_tender_id.user_id")
    requester_id = fields.Many2one('res.users', String="Requester", default=lambda self: self.env.user.id)
    bid_tender_id = fields.Many2one('oms.bid.tender', string="Bid/Tender")
    total_amount = fields.Float(string="Total Amount", compute="_compute_total_amount", store=True)
    check = fields.Boolean(string="Check", compute="_compute_check", store=True)
    project_id = fields.Many2one('project.project', string="Project")
    task_id = fields.Many2many('project.task', string="Activity")
    location_id = fields.Many2one('oms.base.location', string="Office Base Location")
    # replace state field with new state field
    state = fields.Selection([
        ('draft', 'RFQ'),
        ('review', 'Reviewed'),
        ('approve', 'Approved'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)
    purchase_status = fields.Selection([
        ('review', 'Reviewed'),
        ('approve', 'Approved'),
    ], string="Purchase Status")
    purchase_check = fields.Boolean(string="Confirm Check", compute="_compute_purchase_check")
    check_3 = fields.Boolean(string="Check 3", compute="_compute_check_3")
    sign_reviewed = fields.Char(string="Sign Reviewed")
    sign_approved = fields.Char(string="Sign Approved")
    signature_reviewed = fields.Many2one('res.users', string="Signature Reviewed")
    signature_approved = fields.Many2one('res.users', string="Signature Approved")
    amount_in_currency = fields.Float(string="Amount In Currency", compute="_compute_amount_in_currency", store=True)
    approval_currency_id = fields.Many2one('res.currency', string="Approval Currency",
                                           compute="_compute_approval_currency_id", store=True)
    prepared_job_title = fields.Char(string="Prepared Job Title", compute="_compute_prepared_job_title", store=True)
    reviewed_job_title = fields.Char(string="Reviewed Job Title", compute="_compute_reviewed_job_title", store=True)
    approved_job_title = fields.Char(string="Approved Job Title", compute="_compute_approved_job_title", store=True)
    prs = fields.Many2one('project.purchase.request', string="PRS")
    check_project = fields.Boolean(string="Check Project", compute="_check_project", store=True)
    is_donor = fields.Boolean(compute='_compute_is_donor', store=False)
    is_service = fields.Boolean(String="Is Services")
    certificate_completion_count = fields.Integer(string="Certificate Completion Count", compute="_certificate_completion_count", tracking=True)

    # This Function Calculates The Number of Certificate Completion
    def _certificate_completion_count(self):
        for rec in self:
            certificate_completion_count = self.env['certificate.completion'].search_count([('purchase_order', '=', rec.id)])
            rec.certificate_completion_count = certificate_completion_count

    # This Function of Certificate Completion Count
    def action_certificate_completion_count(self):
        for rec in self:
            domain = [('purchase_order', '=', rec.id)]
            return {
                'type': 'ir.actions.act_window',
                'name': 'certificate_completion',
                'res_model': 'certificate.completion',
                'domain': domain,
                'view_mode': 'list,form',
                'target': 'current',
            }

    @api.depends_context('uid')
    def _compute_is_donor(self):
        # نتحقق مرة واحدة خارج الحلقة لتحسين الأداء
        is_group = self.env.user.has_group('bid_tender.group_oms_purchase_doner')
        for order in self:
            order.is_donor = is_group

    @api.depends('project_id')
    def _check_project(self):
        for rec in self:
            if rec.project_id:
                rec.check_project = True
            else:
                rec.check_project = False

    def custom_send_picking_data(self):
        for rec in self:
            stock_picking = self.env['stock.picking'].search([
                ('partner_id', '=', rec.partner_id.id),
                ('origin', '=', rec.name),
            ], limit=1)
            if stock_picking:
                for stock in stock_picking:
                    stock.project_id = rec.project_id.id
                    stock.prs = rec.prs.id
                    stock.user_id = self.env.user.id

    @api.depends('requester_id')
    def _compute_prepared_job_title(self):
        for rec in self:
            if rec.requester_id:
                emp_search = self.env['hr.employee'].search([
                    ('user_id', '=', rec.requester_id.id)
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

    @api.onchange('prs')
    def onchange_prs(self):
        for rec in self:
            if not rec.prs:
                continue
                
            rec.branch_id = rec.prs.branch_id.id
            request_vals = []
            
            # تحديد نوع الطلب من الرأس (Header)
            is_service_request = rec.prs.product_type == 'services'

            for prs_id in rec.prs:
                for line in prs_id.line_ids:
                    product_template = False
                    
                    if is_service_request:
                        # في حالة الخدمات: نبحث عن منتج بنفس الاسم ونوعه خدمة حصراً
                        product_template = self.env['product.template'].search([
                            ('name', '=', line.product_id),
                            ('type', '=', 'service')
                        ], limit=1)
                    else:
                        # في حالة البضائع: نستخدم بحثك القديم
                        product_template = self.env['product.template'].search([
                            ('name', '=', line.product_id),
                        ], limit=1)

                    if product_template:
                        request_vals.append((0, 0, {
                            'product_id': product_template.id,
                            'budged_line_code': line.budget_line_code.id,
                            'product_qty': line.quantity,
                            'product_uom': product_template.uom_id.id,
                        }))
                    else:
                        # إذا لم يجد منتج (سواء كان الطلب خدمة أو بضاعة) ننشئ واحد جديد
                        product_vals = {
                            'name': line.product_id,
                            'uom_id': line.product_uom.id,
                        }
                        
                        # إذا كان الطلب خدمة، نجبر المنتج الجديد يكون نوعه خدمة
                        if is_service_request:
                            product_vals['type'] = 'service'
                        
                        product = self.env['product.template'].create(product_vals)
                        
                        request_vals.append((0, 0, {
                            'product_id': product.id,
                            'budged_line_code': line.budget_line_code.id,
                            'product_qty': line.quantity,
                            'product_uom': line.product_uom.id,
                        }))
            
            if request_vals:
                rec.order_line = [(5, 0, 0)] + request_vals # استخدمت (5,0,0) لتصفير الجدول قبل الإضافة الجديدة

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

    @api.depends('total_amount', 'currency_id')
    def _compute_amount_in_currency(self):
        for rec in self:
            if rec.total_amount > 0 and rec.currency_id != rec.approval_currency_id:
                rec.amount_in_currency = rec.total_amount * rec.approval_currency_id.rate_ids.company_rate
            elif rec.total_amount > 0 and rec.currency_id == rec.approval_currency_id:
                rec.amount_in_currency = rec.total_amount

    # def action_create_invoice(self):
    #     res = super(PurchaseOrder, self).action_create_invoice()
    #     for rec in self:
    #         for line in rec.order_line:
    #             account_move = self.env['account.move'].search([
    #                 ('move_type', '=', 'in_invoice'),
    #                 ('partner_id', '=', rec.partner_id.id),
    #                 ('date', '=', rec.date_approve),
    #             ], limit=1)
    #             if account_move:
    #                 for move in account_move:
    #                     move.project_id = rec.project_id.id
    #                     move.branch_id = rec.branch_id.id
    #                     move.bill_type = 'purchase'
    #                     move.purchase_order = rec.id
    #                     move.prs = rec.prs.id

    #                     # تحديث فقط سطر الفاتورة المرتبط بسطر أمر الشراء
    #                     related_invoice_lines = move.invoice_line_ids.filtered(
    #                         lambda l: l.purchase_line_id.id == line.id)
    #                     for inv_line in related_invoice_lines:
    #                         inv_line.budget_item_line_id = line.budged_line_code.id
                        

    #     return res

    def action_create_invoice(self):
        res = super(PurchaseOrder, self).action_create_invoice()
        for rec in self:
            for request in rec.prs:
                if request.product_type == 'services' and not rec.is_service:
                    raise ValidationError(_("You cannot create an invoice before certificate completion."))

            account_move = self.env['account.move'].search([
                ('move_type', '=', 'in_invoice'),
                ('partner_id', '=', rec.partner_id.id),
                ('date', '=', rec.date_approve),
            ], limit=1)

            if not account_move:
                continue

            for move in account_move:
                move.project_id = rec.project_id.id
                move.branch_id = rec.branch_id.id
                move.bill_type = 'purchase'
                move.purchase_order = rec.id
                move.prs = rec.prs.id
                move.rate = rec.prs.rate
                move.project_type = 'new_project'

                for inv_line in move.invoice_line_ids:
                    purchase_line = inv_line.purchase_line_id
                    if not purchase_line:
                        continue

                    budget_line = purchase_line.budged_line_code
                    if budget_line and budget_line.account_id:
                        inv_line.budget_item_line_id = budget_line.id
                        inv_line.account_id = budget_line.account_id.id

        return res


    def button_confirm(self):
        for order in self:
            if order.state not in ['draft', 'sent', 'approve']:
                continue

            order.order_line._validate_analytic_distribution()
            order._add_supplier_to_product()

            for request in order.prs:
                if request.product_type == 'services':
                    vals = {
                        'branch_id': order.branch_id.id,
                        'user_id': self.env.user.id,
                        'project_id': order.project_id.id,
                        'suppliers': order.partner_id.id,
                        'purchase_order': order.id,
                        'prs': order.prs.id,
                        'task_id': order.task_id.ids,
                    }
                    certificate_completion = self.env['certificate.completion'].create(vals)

            if order.purchase_type == 'purchase_order':

                # ----- التحقق من جميع سجلات التندر -----
                tender_confs = self.env['oms.bid.tender.conf'].search([
                    ('operation_type', '=', 'tender'),
                ])
                for tender in tender_confs:
                    if order.currency_id == tender.currency_id:
                        if order.total_amount >= tender.amount:
                            raise ValidationError(_("The amount is big. Please create a tender!"))
                    else:
                        converted_amount = order.currency_id._convert(
                            order.total_amount,
                            tender.currency_id,
                            order.company_id,
                            order.date_order or fields.Date.today()
                        )
                        if converted_amount >= tender.amount:
                            raise ValidationError(_("The amount is big. Please create a tender!"))

                # ----- التحقق من جميع سجلات تحليل العطاء (bid analysis) -----
                bid_confs = self.env['oms.bid.tender.conf'].search([
                    ('operation_type', '=', 'bid_analysis'),
                ])
                for bid in bid_confs:
                    if order.currency_id == bid.currency_id:
                        if order.total_amount >= bid.amount:
                            raise ValidationError(_("The amount is big. Please create a bid analysis!"))
                    else:
                        converted_amount = order.currency_id._convert(
                            order.total_amount,
                            bid.currency_id,
                            order.company_id,
                            order.date_order or fields.Date.today()
                        )
                        if converted_amount >= bid.amount:
                            raise ValidationError(_("The amount is big. Please create a bid analysis!"))

            # الموافقة الثنائية
            if order._approval_allowed():
                order.button_approve()
            else:
                order.write({'state': 'to approve'})

            if order.partner_id not in order.message_partner_ids:
                order.message_subscribe([order.partner_id.id])

            order.custom_send_picking_data()

        return True

    # def button_confirm(self):
    #     res = super(PurchaseOrder, self).button_confirm()
    #     for rec in self:
    #         tender = self.env['oms.bid.tender.conf'].search([
    #             ('operation_type', '=', 'tender'),
    #             ('amount', '<=', rec.total_amount),
    #         ], limit=1)
    #         bid_analysis = self.env['oms.bid.tender.conf'].search([
    #             ('operation_type', '=', 'bid_analysis'),
    #             ('amount', '<=', rec.total_amount),
    #         ], limit=1)
    #         if tender:
    #             raise ValidationError(_("The amount it big .Please create a tender.!!!"))
    #         if bid_analysis:
    #             raise ValidationError(_("The amount it big .Please create a bid analysis.!!!"))
    #     return res

    @api.depends('reason', 'purchase_type')
    def _compute_check_3(self):
        for rec in self:
            if rec.purchase_type != 'purchase_order' and not rec.reason:
                rec.check_3 = True
            else:
                rec.check_3 = False

    @api.depends('state')
    def _compute_purchase_check(self):
        for rec in self:
            if rec.state == 'approve':
                rec.purchase_check = True
            else:
                rec.purchase_check = False

    @api.depends('reason', 'bid_tender_id')
    def _compute_check(self):
        for rec in self:
            if rec.reason and rec.bid_tender_id:
                rec.check = True
            else:
                rec.check = False

    @api.depends('order_line', 'order_line.price_subtotal')
    def _compute_total_amount(self):
        for rec in self:
            total = 0
            for line in rec.order_line:
                total += line.price_subtotal
            rec.total_amount = total

    @api.onchange('total_amount')
    def _onchange_total_amount(self):
        # البحث عن سجلات "bid_analysis" و "tender" في "oms.bid.tender.conf"
        bid_analysis = self.env['oms.bid.tender.conf'].search([
            ('operation_type', '=', 'bid_analysis'),
        ], limit=1)
        tender = self.env['oms.bid.tender.conf'].search([
            ('operation_type', '=', 'tender'),
        ], limit=1)
        # if self.total_amount >= tender.amount:
        #     self.purchase_type = 'tender'
        # elif self.total_amount >= bid_analysis.amount:
        #     self.purchase_type = 'bid_analysis'
        # else:
        #     self.purchase_type = 'purchase_order'
        if not bid_analysis or not tender:
            raise ValidationError(_("Tender or Bid Analysis configuration records are missing!"))

    def action_done(self):
        for rec in self:
            tender = self.env['oms.bid.tender.conf'].search([
                ('operation_type', '=', 'tender'),
                ('amount', '<=', rec.total_amount),
            ], limit=1)
            bid_analysis = self.env['oms.bid.tender.conf'].search([
                ('operation_type', '=', 'bid_analysis'),
                ('amount', '<=', rec.total_amount),
            ], limit=1)
            if tender:
                raise ValidationError(_("The amount it big .Please create a tender.!!!"))
            if bid_analysis:
                raise ValidationError(_("The amount it big .Please create a bid analysis.!!!"))

    def action_review(self):
        for rec in self:
            # 1. Validation for Exchange Rate (Rate)
            if not rec.prs or rec.prs.rate <= 0:
                raise ValidationError(_(
                    "⚠️ Alert\n\n"
                    "Please enter the exchange rate (Rate) in the Purchase Request (PRS) first to proceed!"
                ))

            rate = rec.prs.rate
            
            # 2. Dictionary to group amounts by budget line
            budget_totals = {}

            for line in rec.order_line:
                if not line.budged_line_code:
                    continue
                
                amount = line.price_subtotal
                if line.currency_id != line.budged_line_code.currency_id:
                    amount = amount * (1 / rate)
                
                if line.budged_line_code in budget_totals:
                    budget_totals[line.budged_line_code] += amount
                else:
                    budget_totals[line.budged_line_code] = amount

            # 3. Perform validation on the aggregated totals per budget line
            for budget, total_po_amount in budget_totals.items():
                # Correct way to define symbol BEFORE using it in ValidationError
                # We access the symbol from the budget line's currency
                symbol = budget.currency_id.symbol if budget.currency_id else ""
                
                # Formula check
                if (total_po_amount + budget.budget_line_theoritical_amount) > (budget.budget_line_planned_amount + budget.allowed_increase):
                    raise ValidationError(_(
                        "⛔ Budget Alert\n\n"
                        f"Financial Code: {budget.line_code}\n"
                        f"Account: {budget.account_id.name}\n"
                        f"Total Requested in This PO: {total_po_amount:,.2f} {symbol}\n"
                        f"Already Spent/Reserved: {budget.budget_line_theoritical_amount:,.2f} {symbol}\n"
                        f"Allowed Budget: {(budget.budget_line_planned_amount + budget.allowed_increase):,.2f} {symbol}\n\n"
                        "The Total Sum of Products For This Budget Line Exceeds The Available Balance!"
                    ))

            rec.state = 'review'
            rec.purchase_status = 'review'
            rec.sign_reviewed = str(self.env.user.name)
            rec.signature_reviewed = self.env.user.id
            rec.date_pur = fields.Date.context_today(self)

    def action_reset_to_draft(self):
        for rec in self:
            rec.state = 'draft'
            rec.purchase_status = False
            rec.sign_approved = False
            rec.sign_reviewed = False

    def action_approved(self):
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
            rec.purchase_status = 'approve'
            rec.sign_approved = str(self.env.user.name)
            rec.signature_approved = self.env.user.id
            rec.date_pur = fields.Date.context_today(self)

    def action_print_report(self):
        action = self.env.ref('purchase.action_report_purchase_order').read()[0]
        return action


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    budged_line_code = fields.Many2one('budget.iteme.line', string="Budget Line Code")
    project_id = fields.Many2one(related="order_id.project_id")

