# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from dateutil import relativedelta
from datetime import date
import datetime


class BidAnalysisTender(models.Model):
    _name = 'oms.bid.tender'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Bid Analysis / Tender'
    # _rec_name = 'ref'
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

    branch_id = fields.Many2one('oms.branch', string='Branch', default=_get_default_branch, domain=_get_user_branch)
    name = fields.Char(string="Name", required=True)
    date = fields.Date(string="Created Date", default=fields.Date.context_today)
    opening_date = fields.Date(string="Opening Date")
    closing_date = fields.Date(string="Closing Date")
    confirmed_date = fields.Date(string="Approved Date", readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('review', 'Reviewed'),
        ('approve', 'Approved'),
        ('done', 'Done'),
        ('cancel', 'Canceled'),
    ], default='draft', required=True, tracking=True, string="Status")
    operation_type = fields.Selection([
        ('bid_analysis', 'Bid Analysis'),
        ('tender', 'Open Tender'),
    ], string="Operation Type", required=True, tracking=True, )
    ref = fields.Char(string='Reference', tracking=True)
    tender_ref = fields.Char(string='Tender Reference', tracking=True)
    rate = fields.Float(string="Rate", related="prs.rate")
    reason = fields.Text(string="Reason")
    bid_tender_line_ids = fields.One2many('oms.bid.tender.line', 'bid_tender_id', string="Bid Tender Line")
    committee_line_ids = fields.One2many('bid.tender.committee', 'bid_tender_id', string="Committee Line")
    offer_line_ids = fields.One2many('offers.scores.line', 'bid_tender_id', string="Offer Line")
    bid_tender_line_restrictions_ids = fields.One2many('oms.bid.tender.line.restrictions', 'bid_tender_id',
                                                       string="Bid Tender Line Restrictions")
    user_id = fields.Many2one('res.users', String="User", tracking=True, readonly=True,
                              default=lambda self: self.env.user.id)
    chosen_id = fields.Many2one('res.partner', string="Supplier Chosen")
    suppliers = fields.Many2many('res.partner', string="Suppliers", store=True)
    total_amount = fields.Float(string="Total Amount", store=True, compute="_compute_total_amount")
    amount_in_currency = fields.Float(string="Amount In Currency", compute="_compute_amount_in_currency", store=True)
    approval_currency_id = fields.Many2one('res.currency', string="Approval Currency",
                                           compute="_compute_approval_currency_id", store=True, )
    location_id = fields.Many2one('oms.base.location', string="Office Base Location")
    project_id = fields.Many2one('project.project', string="Project")
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company.id
    )
    where_announced = fields.Char(string="Where Announced")
    purchase_order = fields.Many2one('purchase.order', string="Purchase Order#")
    bid_tender_currency_id = fields.Many2one('res.currency', string="Bid/Tender Currency", store=True, related="project_id.curr_id")
    sign_reviewed = fields.Char(string="Sign Reviewed")
    signature_reviewed = fields.Many2one('res.users', string="Reviewed by")
    sign_approved = fields.Char(string="Sign Approved")
    signature_approved = fields.Many2one('res.users', string="Approved by")
    date_approve = fields.Date(string="Approved Date", readonly=True)
    date_review = fields.Date(string="Reviewed Date", readonly=True)
    prs = fields.Many2one('project.purchase.request', string="PRS")
    prepared_job_title = fields.Char(string="Prepared Job Title", compute="_compute_prepared_job_title", store=True)
    reviewed_job_title = fields.Char(string="Reviewed Job Title", compute="_compute_reviewed_job_title", store=True)
    approved_job_title = fields.Char(string="Approved Job Title", compute="_compute_approved_job_title", store=True)
    note = fields.Text(string="Note")
    number_of_competing_bidders = fields.Integer(string="Number of Competing Bidders")
    number_of_excluded_bidders = fields.Integer(string="Number of Excluded bidders")
    number_of_nominated_companies = fields.Integer(string="Number of Nominated Companies")

    # company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, readonly=True)

    def unlink(self):
        if self.state != 'draft':
            raise ValidationError(_("You can delete Bid or Tender record only in draft state"))
        else:
            return super(BidAnalysisTender, self).unlink()

    @api.onchange('prs')
    def onchange_prs(self):
        for rec in self:
            rec.branch_id = rec.prs.branch_id.id
            request_vals = []
            rec.bid_tender_line_ids = [(5, 0, 0)] 
            if rec.prs:
                for prs_id in rec.prs:
                    for line in prs_id.line_ids:

                        product_template = self.env['product.template'].search([
                            ('name', '=', line.product_id),
                        ], limit=1)

                        partner = self.env['res.partner'].search([
                            ('name', '=', 'X'),
                        ], limit=1)

                        if not partner:
                            partner = self.env['res.partner'].create({'name': 'X'})

                        
                        if product_template:
                            request_vals.append((0, 0, {
                                'product_id': product_template.id,
                                'supplier_id': partner.id,
                                'qty': line.quantity,
                                'description': line.description,
                                'unut_id': product_template.uom_id.id,
                            }))
                        else:
                            product = self.env['product.template'].create({
                                'name': line.product_id,
                                'uom_id': line.product_uom.id,
                            })
                            request_vals.append((0, 0, {
                                'product_id': product.id,
                                'supplier_id': partner.id,
                                'description': line.description,
                                'qty': line.quantity,
                                'unut_id': line.product_uom.id,
                            }))

                if request_vals:
                    rec.bid_tender_line_ids = request_vals

    def action_suppler(self):
        for rec in self:
            vals = {
                'bid_tender_id': rec.id,
            }
            new = self.env['bid.tender.supplier.wizard'].create(vals)
            return {
                'name': "Suppler",
                'type': 'ir.actions.act_window',
                'res_model': 'bid.tender.supplier.wizard',
                'res_id': new.id,
                'view_id': self.env.ref('bid_tender.view_bid_tender_supplier_wizard_form', False).id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new'
            }

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

    # @api.depends('currency_id', 'operation_type')
    # def _compute_bid_tender_currency_id(self):
    #     for rec in self:
    #         if rec.operation_type == 'bid_analysis':
    #             bid_conf = self.env['oms.bid.tender.conf'].search([
    #                 ('operation_type', '=', rec.operation_type),
    #             ], limit=1)
    #             if bid_conf:
    #                 for bid in bid_conf:
    #                     rec.bid_tender_currency_id = bid.currency_id.id
    #         elif rec.operation_type == 'tender':
    #             tender_conf = self.env['oms.bid.tender.conf'].search([
    #                 ('operation_type', '=', rec.operation_type),
    #             ], limit=1)
    #             if tender_conf:
    #                 for tender in tender_conf:
    #                     rec.bid_tender_currency_id = tender.currency_id.id

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

    def print_bid_tender(self):
        action = self.env.ref('bid_tender.action_report_bid_tender_print').read()[0]
        return action

    currency_id = fields.Many2one('res.currency', string="Currency",
                                  default=lambda self: self.env['res.currency'].search([('name', '=', 'SDG')], limit=1))

    @api.depends('total_amount', 'rate')
    def _compute_amount_in_currency(self):
        for rec in self:
            if rec.prs and rec.prs.rate > 0:
                rec.amount_in_currency = rec.total_amount/rec.rate

    # @api.depends('operation_type')
    # def _compute_currency_id(self):
    #     for rec in self:
    #         conf_ = self.env['oms.bid.tender.conf'].search([
    #             ('operation_type', '=', rec.operation_type),
    #         ], limit=1)
    #         if conf_:
    #             rec.currency_id = conf_.currency_id

    @api.depends('bid_tender_line_ids', 'chosen_id')
    def _compute_total_amount(self):
        for rec in self:
            total = 0
            if len(rec.bid_tender_line_ids) > 1:
                for line in rec.bid_tender_line_ids:
                    if rec.chosen_id == line.supplier_id:
                        total += line.total_price
                        rec.total_amount = total

    @api.onchange('bid_tender_line_ids')  # Trigger when bid_tender_line_ids is changed
    def _onchange_suppliers(self):
        for rec in self:
            # Collect all supplier_ids from bid_tender_line_ids
            supplier_ids = rec.bid_tender_line_ids.mapped('supplier_id.id')
            # Assign supplier_ids to the suppliers Many2many field
            rec.suppliers = [(6, 0, supplier_ids)]  # (6, 0, ids) is the command for adding ids in Many2many field

    @api.model
    def create(self, vals):
        operation_type = vals.get('operation_type')
        
        if operation_type == 'tender':
            # سحب الرقم من تسلسل العطاءات الخاص (HOPE-TENDER/2026/01)
            new_ref = self.env['ir.sequence'].next_by_code('oms.tender.special') or _('New')
            vals['tender_ref'] = new_ref # نضع الرقم في حقل العطاء
        else:
            # سحب الرقم من التسلسل العادي للمناقصات (BAT00001)
            new_ref = self.env['ir.sequence'].next_by_code('oms.bid.tender') or _('New')

        vals['ref'] = new_ref # المرجع الأساسي يأخذ القيمة المولدة أيّاً كانت
        
        return super(BidAnalysisTender, self).create(vals)


    def write(self, vals):
        # إذا تم تغيير النوع إلى tender ولم يكن له مرجع عطاء سابق
        if vals.get('operation_type') == 'tender' and not self.tender_ref:
            vals['tender_ref'] = self.env['ir.sequence'].next_by_code('oms.tender.special')
            # اختياري: هل تريد تحديث الـ ref أيضاً ليكون متطابقاً؟
            vals['ref'] = vals['tender_ref']
            
        return super(BidAnalysisTender, self).write(vals)

    def action_back(self):
        for rec in self:
            rec.state = 'draft'

    def action_review(self):
        for rec in self:
            rec.sign_reviewed = str(self.env.user.name)
            rec.signature_reviewed = self.env.user.id
            rec.date_review = date.today().strftime('%Y-%m-%d')
            rec.state = 'review'

    def action_confirm(self):
        for rec in self:
            total_amount = 0
            if not rec.chosen_id:
                raise ValidationError(_('Please chose a supplier  !!!'))
            for line in rec.bid_tender_line_ids:
                restrictions_line = self.env['oms.bid.tender.line.restrictions'].search([
                    ('supplier_id', '=', line.supplier_id.id)
                ], limit=1)
                if not restrictions_line:
                    restrictions_vals = {
                        'supplier_id': line.supplier_id.id,
                        'bid_tender_id': rec.id,
                        'bid_line_id': line.id,
                    }
                    rec.bid_tender_line_restrictions_ids.create(restrictions_vals)
                total_amount += line.unit_price
                if len(line) < 1:
                    raise ValidationError(_('Please add the supplier and it product !!!'))
                if line.unit_price == 0:
                    raise ValidationError(_('The price can not be zero !!!'))
                if line.chosen == True:
                    rec.chosen_id = line.supplier_id.id
                # if not rec.reason:
                #     raise ValidationError(_('Please add the reason !!!'))

                # 🔹 جلب التهيئة لكل من العطاء (Tender) والمناقصة (Bid Analysis)
                bid_conf = self.env['oms.bid.tender.conf'].search([('operation_type', '=', 'bid_analysis')], limit=1)
                tender_conf = self.env['oms.bid.tender.conf'].search([('operation_type', '=', 'tender')], limit=1)

                # 🔹 تحقق من العمليات
                if rec.operation_type == 'bid_analysis':
                    # تحقق أن المبلغ مناسب لتحليل العطاءات
                    if bid_conf:
                        if rec.amount_in_currency < bid_conf.amount:
                            raise ValidationError(
                                _('For Bid Analysis, the amount must be at least %s %s') %
                                (bid_conf.amount, bid_conf.currency_id.symbol)
                            )
                    # لو المبلغ أكبر من حد العطاء (Tender) → خطأ (المبلغ كبير جداً لتحليل عروض)
                    if tender_conf and rec.amount_in_currency > tender_conf.amount:
                        raise ValidationError(_(
                            'The amount you entered (%s %s) exceeds the maximum allowed for Bid Analysis (%s %s), '
                            'and falls within the range that requires a Tender (Open Tender), which starts from %s %s. '
                            'Please switch the operation type to Tender.'
                        ) % (
                            rec.amount_in_currency, rec.bid_tender_currency_id.symbol,
                            bid_conf.amount, bid_conf.currency_id.symbol,
                            tender_conf.amount, tender_conf.currency_id.symbol
                        ))


                elif rec.operation_type == 'tender':
                    # تحقق أن المبلغ مناسب للعطاءات
                    if tender_conf:
                        if rec.amount_in_currency < tender_conf.amount:
                            raise ValidationError(
                                _('For Tender, the amount must be at least %s %s') %
                                (tender_conf.amount, tender_conf.currency_id.symbol)
                            )
                    # لو المبلغ أقل من حد المناقصة → خطأ (المبلغ صغير جداً لعطاء)
                    if bid_conf and rec.amount_in_currency < bid_conf.amount:
                        raise ValidationError(
                            _('This amount is too low for Tender. It seems like a Bid Analysis amount.'
                            ' Minimum allowed for Tender is %s %s') %
                            (tender_conf.amount, tender_conf.currency_id.symbol)
                        )
                        
            rec.offer_line_ids = [(5, 0, 0)]
            
            supplier_totals = {}
            for line in rec.bid_tender_line_ids:
                if line.supplier_id:
                    sid = line.supplier_id.id
                    supplier_totals[sid] = supplier_totals.get(sid, 0.0) + line.total_price
            
            offer_vals = []
            for supplier_id, total in supplier_totals.items():
                offer_vals.append((0, 0, {
                    'supplier_id': supplier_id,
                    'offer': total,
                }))
            
            if offer_vals:
                rec.offer_line_ids = offer_vals

            rec.state = 'confirm'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'
            purchase_order = self.env['purchase.order'].search([
                ('bid_tender_id', '=', rec.id)
            ], limit=1)
            if purchase_order:
                purchase_order.state = 'cancel'

    def action_done(self):
        for rec in self:
            if not rec.purchase_order:
                # Create the purchase order
                # prs_line = rec.prs.line_ids[:1]
                purchase_order_vals = {
                    'partner_id': rec.chosen_id.id,
                    'purchase_type': rec.operation_type,
                    'reason': rec.reason,
                    'branch_id': rec.branch_id.id,
                    'requester_id': rec.user_id.id,
                    # 'location_id': rec.location_id.id,
                    'project_id': rec.project_id.id,
                    'bid_tender_id': rec.id,
                    'user_id': rec.user_id.id,
                    'prs': rec.prs.id,
                    'currency_id': rec.currency_id.id,
                    'state': 'draft'
                }
                purchase_order = self.env['purchase.order'].create(purchase_order_vals)
                for line in rec.bid_tender_line_ids:
                    if rec.chosen_id == line.supplier_id:
                        prs_line = rec.prs.line_ids.filtered(
                            lambda l: l.product_id == line.product_id.name
                        )[:1]
                        product_template = self.env['product.template'].search([
                            ('name', '=', line.product_id.name),
                        ], limit=1)
                        if product_template:
                            purchase_order_line_vals = {
                                'product_id': line.product_id.id,
                                'product_qty': line.qty,
                                'budged_line_code': prs_line.budget_line_code.id if prs_line else False,
                                'price_unit': line.unit_price,
                                'product_uom': product_template.uom_id.id,
                                'order_id': purchase_order.id,
                            }
                            self.env['purchase.order.line'].create(purchase_order_line_vals)
                        elif not product_template:
                            product_vals = {
                                'name': line.product_id,
                                'uom_id': line.unut_id.id
                            }
                            product = self.env['product.template'].create(product_vals)
                            
                            purchase_order_line_vals = {
                                'product_id': line.product_id.id,
                                'product_qty': line.qty,
                                'budged_line_code': prs_line.budget_line_code.id if prs_line else False,
                                'price_unit': line.unit_price,
                                'product_uom': line.unut_id.id,
                                'order_id': purchase_order.id,
                            }
                            self.env['purchase.order.line'].create(purchase_order_line_vals)
                rec.purchase_order = purchase_order.id
            rec.state = 'done'

    def action_approve(self):
        for rec in self:
            for restrictions in rec.bid_tender_line_restrictions_ids:
                if rec.chosen_id == restrictions.supplier_id:
                    rec.reason = (
                            "Reason Of Selection : " + str(restrictions.reason_off_selection or '') + "\n" +
                            "Payment Means : " + str(restrictions.payment_means or '') + "\n" +
                            "Payment Terms : " + str(restrictions.payment_terms or '') + "\n" +
                            "Guarantee Duration : " + str(restrictions.guarantee_duration or '') + "\n" +
                            "Validity of Offer : " + str(restrictions.validity_of_offer or '')
                    )
            if not rec.reason:
                raise ValidationError(_('Please add the reason !!!'))
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
            
            rec.signature_approved = self.env.user.id
            rec.sign_approved = str(self.env.user.name)
            rec.date_approve = date.today().strftime('%Y-%m-%d')
            rec.state = 'approve'


class BidAnalysisTenderLine(models.Model):
    _name = 'oms.bid.tender.line'
    _description = 'OMS Bid Analysis Tender Line'

    bid_tender_id = fields.Many2one('oms.bid.tender', string="Bid Tender")
    supplier_id = fields.Many2one('res.partner', string="Supplier", required=True, )
    product_id = fields.Many2one('product.product', string="Product", required=True)
    description = fields.Char(string="Description")
    qty = fields.Float(string="Quantity", default=1)
    unut_id = fields.Many2one('uom.uom', string="Unit",
                              default=lambda self: self.env['uom.uom'].search([('name', '=', 'Units')]))
    unit_price = fields.Float(string="Unit Price")
    total_price = fields.Float(string="Total Price", compute="_compute_total_price", store=True)
    chosen = fields.Boolean(string="Chose?")
    check_c = fields.Boolean('Check', compute="_compute_check_c", store=True)
    state = fields.Selection(related="bid_tender_id.state")
    currency_id = fields.Many2one(related="bid_tender_id.currency_id")

    @api.depends('unit_price', 'qty')
    def _compute_total_price(self):
        for rec in self:
            if rec.unit_price > 0:
                rec.total_price = rec.unit_price * rec.qty

    @api.depends('chosen')
    def _compute_check_c(self):
        for rec in self:
            if rec.chosen == True:
                rec.check_c = True
            else:
                rec.check_c = False


class BidAnalysisTenderLineRestrictions(models.Model):
    _name = 'oms.bid.tender.line.restrictions'
    _description = 'OMS Bid Analysis Tender Line Restrictions'

    bid_line_id = fields.Many2one('oms.bid.tender.line', string="Bid Line")
    bid_tender_id = fields.Many2one('oms.bid.tender', string="Bid Tender")
    supplier_id = fields.Many2one('res.partner', string="Supplier")
    state = fields.Selection(related="bid_tender_id.state")

    currency_id = fields.Many2one('res.currency', string="Currency")
    payment_means = fields.Text(string="Payment Means")
    payment_terms = fields.Text(string="Payment Terms")
    delivery_time = fields.Date(string="Date")
    guarantee_duration = fields.Text(string="Guarantee Duration And Condition")
    validity_of_offer = fields.Text(string="Validity Of The Offer")
    reason_off_selection = fields.Text(string="Reason Of Selection")
    check_reason = fields.Boolean(string="check reason?", compute="_compute_check_reason", store=True)

    @api.depends('bid_tender_id.chosen_id')
    def _compute_check_reason(self):
        for rec in self:
            for record in rec.bid_tender_id:
                if record.chosen_id == rec.supplier_id:
                    print('!!!!!!!!!')


class BidTenderCommittee(models.Model):
    _name = 'bid.tender.committee'
    _description = 'Bid Tender Committee'

    emp_id = fields.Many2one('hr.employee', string="Member of Committee")
    bid_tender_id = fields.Many2one('oms.bid.tender', string="Tender")
    department = fields.Many2one(related="emp_id.department_id", string="Department")
    phone = fields.Char(string="Phone", related="emp_id.work_phone")
    note = fields.Text(string="Note")
    signature = fields.Many2one('res.users', string="Signature", compute="_compute_signature", store=True)

    @api.depends('emp_id')
    def _compute_signature(self):
        for rec in self:
            for seg in rec.emp_id:
                rec.signature = seg.user_id.id



class OffersScoresLine(models.Model):
    _name = 'offers.scores.line'
    _description = 'Offers Scores Line'

    bid_tender_id = fields.Many2one('oms.bid.tender', string="Tender")
    supplier_id = fields.Many2one('res.partner', string="Supplier")
    offer = fields.Float(string="Offer")
    price_percentage = fields.Float(string="Price Percentager %")
    relevant_experience = fields.Float(string="Relevant Experience")
    certificates = fields.Float(string="Certificates")
    other_point = fields.Float(string="Other Point")
    total_score = fields.Float(string="Total Score %", compute="_compute_total_score", store=True)
    currency_id = fields.Many2one(related="bid_tender_id.currency_id")

    @api.depends('price_percentage', 'relevant_experience', 'certificates', 'other_point')
    def _compute_total_score(self):
        """
        Triggered automatically whenever any evaluation metric is modified.
        Sums up the individual weights to provide a final score.
        """
        for rec in self:
            # Calculate the aggregate sum of all evaluation criteria
            total = (rec.price_percentage + 
                     rec.relevant_experience + 
                     rec.certificates + 
                     rec.other_point)
            
            # Validation check to ensure the score logic remains within 100% boundary
            if total > 100:
                raise ValidationError(_(
                    "Error: The total score for '%s' cannot exceed 100%%. "
                    "The current sum is: %s%%. Please adjust the weights."
                ) % (rec.supplier_id.name, total))
            
            rec.total_score = total

    @api.constrains('price_percentage', 'relevant_experience', 'certificates', 'other_point')
    def _check_max_score_constrain(self):
        """
        Database-level constraint to prevent saving invalid records.
        Ensures the total score is mathematically consistent.
        """
        for rec in self:
            total = (rec.price_percentage + 
                     rec.relevant_experience + 
                     rec.certificates + 
                     rec.other_point)
            if total > 100:
                raise ValidationError(_(
                    "Constraint Violation: Cumulative score exceeds 100%%."
                ))
