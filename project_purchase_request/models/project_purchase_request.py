from odoo import models, fields, api, _
from datetime import date
import datetime
from odoo.exceptions import UserError, ValidationError


class PurchaseRequest(models.Model):
    _name = 'project.purchase.request'
    _description = 'Project Purchase Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'request_date desc, id desc'

    @api.model
    def _default_requester(self):
        return self.env.user

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

    name = fields.Char(string="Description", required=True, tracking=True)
    ref = fields.Char(string='Reference', tracking=True)
    branch_id = fields.Many2one('oms.branch', string='Branch', default=_get_default_branch, domain=_get_user_branch)
    request_date = fields.Date(
        string=' Confirmation Date',
        default=fields.Date.context_today,
        tracking=True
    )
    requester_id = fields.Many2one(
        'res.users',
        string='Requester',
        default=_default_requester,
        tracking=True,
        readonly=True
    )
    move_id = fields.Many2one('account.move', string="Bill#")
    project_id = fields.Many2one(
        'project.project',
        string='Project',
        required=True,
        tracking=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('review', '  Reviewed'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancel', 'Cancel'),
        ('done', 'Done')],
        string=' State',
        default='draft',
        tracking=True,
        # group_expand='_expand_states'
    )
    line_ids = fields.One2many(
        'purchase.request.line',
        'request_id',
        string='Order items',
        copy=True
    )
    notes = fields.Text('Comments', tracking=True)
    request_type = fields.Selection([
        ('tor_advance', 'TOR \ Advance Payment'),
        ('purchase_request', 'PRS'),
        # ('purchase_request_service', 'PRS'),
    ], string='Request Type', required=True, readonly=True)
    product_type = fields.Selection([
        ('goods', 'Goods'),
        ('services', 'Services'),
    ], string='Product Type', tracking=True)
    received_by = fields.Selection([
        ('vendor', 'Vendor'),
        ('employee', 'Employees')
    ], string="Received by", tracking=True)
    payment_status = fields.Selection([
        ('not_paid', 'Not Paid'),
        ('in_payment', 'In Payment'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('reversed', 'Reversed'),
        ('blocked', 'Blocked'),
        ('invoicing_legacy', 'Invoicing App Legacy'),
    ], default="not_paid", string="Payment Status", tracking=True, compute="_compute_payment_status", store=False)
    partner_id = fields.Many2one('res.partner', string='Vendor', tracking=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", tracking=True)
    service_line_ids = fields.One2many('purchase.request.service', 'request_id', string='Service Items')
    attachment_line_ids = fields.One2many('request.attachment', 'request_id', string='Service Items')
    task_ids = fields.Many2one('project.task', string="Activity", tracking=True)
    check_task_ids = fields.Boolean(string="Check Activity", store=True, tracking=True,)
    date_from = fields.Date('Start Date', tracking=True)
    date_to = fields.Date('End Date', tracking=True)
    location = fields.Text('Location', tracking=True)
    rate = fields.Float(string="Rate")
    general_objective = fields.Text('General Objective', tracking=True)
    specific_objectives = fields.Text('Specific Objectives:', tracking=True)
    sign_reviewed = fields.Char(string="Sign Reviewed")
    sign_approved = fields.Char(string="Sign Approved")
    sign_prepared = fields.Char(string="Sign Prepared")
    date_approve = fields.Date()
    date_review = fields.Date()
    date_prepared = fields.Date()
    prepared_job_title = fields.Char(string="Prepared Job Title", compute="_compute_prepared_job_title", store=True)
    reviewed_job_title = fields.Char(string="Reviewed Job Title", compute="_compute_reviewed_job_title", store=True)
    approved_job_title = fields.Char(string="Approved Job Title", compute="_compute_approved_job_title", store=True)
    signature_reviewed = fields.Many2one('res.users', string="Signature Reviewed", )
    signature_approved = fields.Many2one('res.users', string="Signature Approved")
    project_code = fields.Char(string="Project Code", related="project_id.project_code")
    number_of_beneficiaries = fields.Char(string="Number OF Beneficiaries", tracking=True)
    total_amount = fields.Float(string="Total Amount", compute="_compute_total_amount", store=True)
    amount_in_currency = fields.Float(string="Amount In Currency", compute="_compute_amount_in_currency", store=True)
    currency_id = fields.Many2one('res.currency', string="Currency",
                                  default=lambda self: self.env['res.currency'].search([('name', '=', 'SDG')], limit=1),
                                  readonly=False, tracking=True)
    approval_currency_id = fields.Many2one('res.currency', string="Approval Currency",
                                           compute="_compute_approval_currency_id", store=True)
    sum_line_total_price = fields.Float(string="Sum Total Price", compute="_compute_sum_line_total_price", store=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, readonly=True)

    tor_bill_count = fields.Integer(string="Bill Count", compute='_compute_tor_bill_count', tracking=True)
    prs_bill_count = fields.Integer(string="Bill Count", compute='_compute_prs_bill_count', tracking=True)
    tender_count = fields.Integer(string="Bid/Tender Count", compute="compute_tender_count", tracking=True)
    purchase_count = fields.Integer(string="Purchase Count", compute="_compute_purchase_count")
    activity_issue = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'NO'),
    ], string="Activity Issue?", default="no")
    avtivity_char = fields.Char(string="Activity")
    created_bill = fields.Boolean(string="Created Bill?")

    def action_create_bill(self):
        for rec in self:
            if rec.received_by == 'vendor':
                vendor_vals = {
                    'partner_id': rec.partner_id.id,
                    'ref': str(rec.request_type + "/" + rec.name),
                    'project_id': rec.project_id.id,
                    'tor_bill': True,
                    'tor_check': True,
                    'bill_type': 'tor',
                    'project_type': 'new_project',
                    'tor_advance_id': rec.id,
                    # 'task_id': rec.task_ids.id,
                    'move_type': 'in_invoice',
                    'currency_id': rec.currency_id.id,
                }
                vendor = self.env['account.move'].create(vendor_vals)
                line_data = vendor.action_set_tor_data()

            elif rec.received_by == 'employee':
                employee_partner = self.env['res.partner'].search([
                    ('name', '=', rec.employee_id.name),
                ], limit=1)
                if employee_partner:
                    employee_vals = {
                        'partner_id': employee_partner.id,
                        'ref': str(rec.request_type + "/" + rec.name),
                        'project_id': rec.project_id.id,
                        'tor_bill': True,
                        'tor_check': True,
                        'bill_type': 'tor',
                        'project_type': 'new_project',
                        'tor_advance_id': rec.id,
                        # 'task_id': rec.task_ids.id,
                        'move_type': 'in_invoice',
                        'currency_id': rec.currency_id.id,
                    }
                    employee = self.env['account.move'].create(employee_vals)
                    line_data = employee.action_set_tor_data()

                elif not employee_partner:
                    vals = {
                        'name': rec.employee_id.name,
                    }
                    partner_value = self.env['res.partner'].create(vals)
                    employee_vals = {
                        'partner_id': partner_value.id,
                        'ref': str(rec.request_type + "/" + rec.name),
                        'project_id': rec.project_id.id,
                        'tor_bill': True,
                        'tor_check': True,
                        'bill_type': 'tor',
                        'project_type': 'new_project',
                        'tor_advance_id': rec.id,
                        # 'task_id': rec.task_ids.id,
                        'move_type': 'in_invoice',
                        'currency_id': rec.currency_id.id,
                    }
                    employee = self.env['account.move'].create(employee_vals)
                    line_data = employee.action_set_tor_data()

            rec.created_bill = True

                # for line in rec.service_line_ids:
                #     vendor_line_vals = {
                #         'move_id': vendor.id,
                #         'name': line.description_of_activities,
                #         'budget_item_line_id': line.budget_line_code.id,
                #         'qty': line.quantity,
                #         'frequency': line.frequency,
                #         'product_uom_id': line.unit_uom.id,
                #         'price_unit': line.unit_price,
                #         'quantity': line.quantity * line.frequency,
                #         'account_id': line.account_id.id,
                #     }
                #     vendor_line = self.env['account.move.line'].create(vendor_line_vals)
                # rec.move_id = vendor.id

    def _compute_payment_status(self):
        for rec in self:
            rec.payment_status = 'not_paid'
            if rec.request_type == 'tor_advance':
                account_move = self.env['account.move'].search([
                    ('move_type', '=', 'in_invoice'),
                    ('tor_advance_id', '=', rec.id),
                ], limit=1)

                if account_move:
                    rec.payment_status = account_move.payment_state
            elif rec.request_type == 'purchase_request':
                account_move = self.env['account.move'].search([
                    ('move_type', '=', 'in_invoice'),
                    ('prs', '=', rec.id),
                ], limit=1)

                if account_move:
                    rec.payment_status = account_move.payment_state



    def unlink(self):
        if self.state != 'draft':
            raise ValidationError(_("You can delete PRS Or TOR record only in draft state"))
        else:
            return super(PurchaseRequest, self).unlink()

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

    # This Function Calculates The Number of TOR Bills
    def _compute_tor_bill_count(self):
        for rec in self:
            bill_count = self.env['account.move'].search_count([('tor_advance_id', '=', rec.id)])
            rec.tor_bill_count = bill_count

    # This Function Calculates The Number of PRS Bills
    def _compute_prs_bill_count(self):
        for rec in self:
            bill_count = self.env['account.move'].search_count([('prs', '=', rec.id)])
            rec.prs_bill_count = bill_count

    # This Function Calculates The Number of Bid/Tender
    def compute_tender_count(self):
        for rec in self:
            tender_count = self.env['oms.bid.tender'].search_count([('prs', '=', rec.id)])
            rec.tender_count = tender_count

    # This Function Calculates The Number of Purchase Order
    def _compute_purchase_count(self):
        for rec in self:
            purchase_count = self.env['purchase.order'].search_count([('prs', '=', rec.id)])
            rec.purchase_count = purchase_count

    # This Function of Smart Button TOR Payment Count
    def action_tor_bill_count(self):
        result = self.env['ir.actions.act_window']._for_xml_id('account.action_move_in_invoice_type')
        result['domain'] = [('tor_advance_id', '=', self.id)]
        return result

    # This Function of Smart Button TOR Payment Count
    def action_prs_bill_count(self):
        result = self.env['ir.actions.act_window']._for_xml_id('account.action_move_in_invoice_type')
        result['domain'] = [('prs', '=', self.id)]
        return result

    # This Function of Smart Button Bid/Tender Count
    def action_bid_tender_count(self):
        for rec in self:
            domain = [('prs', '=', rec.id)]
            return {
                'type': 'ir.actions.act_window',
                'name': 'bid_tender',
                'res_model': 'oms.bid.tender',
                'domain': domain,
                'view_mode': 'list,form',
                'target': 'current',
            }

    # This Function of Smart Button Purchase Order Count
    def action_purchase_order_count(self):
        for rec in self:
            domain = [('prs', '=', rec.id)]
            return {
                'type': 'ir.actions.act_window',
                'name': 'purchase_order',
                'res_model': 'purchase.order',
                'domain': domain,
                'view_mode': 'list,form',
                'target': 'current',
            }

    @api.depends('service_line_ids.total_price')
    def _compute_sum_line_total_price(self):
        for rec in self:
            total = 0
            for line in rec.service_line_ids:
                total += line.total_price
                rec.sum_line_total_price = total

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

    @api.depends('service_line_ids.total_price')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = 0.0
            if rec.request_type == 'tor_advance':
                for line_service in rec.service_line_ids:
                    rec.total_amount += line_service.total_price

    @api.depends('total_amount', 'rate')
    def _compute_amount_in_currency(self):
        """
        Calculate the equivalent amount in the approval currency 
        using the manual rate provided in the record.
        """
        for rec in self:
            # Check if there is a total amount and the exchange rate is valid (greater than zero)
            if rec.total_amount > 0 and rec.rate > 0:
                # Convert the amount by dividing total_amount by the manual rate
                # Example: 1,300,000 SDG / 1,300 Rate = 1,000 USD
                rec.amount_in_currency = rec.total_amount / rec.rate
            else:
                # Default to 0.0 if no amount or rate is provided to avoid calculation errors
                rec.amount_in_currency = 0.0

    @api.onchange('task_ids')
    def onchange_check_task_ids(self):
        for rec in self:
            if rec.task_ids:
                rec.check_task_ids = True
            elif not rec.task_ids:
                rec.check_task_ids = False

    # @api.depends('line_ids.subtotal')
    # def _compute_total_amount(self):
    #     for request in self:
    #         request.total_amount = sum(line.subtotal for line in request.line_ids)

    @api.model
    def create(self, vals):
        vals['ref'] = self.env['ir.sequence'].next_by_code('project.purchase.request')
        return super(PurchaseRequest, self).create(vals)

    def write(self, vals):
        for rec in self:
            if not rec.ref:
                vals['ref'] = self.env['ir.sequence'].next_by_code('project.purchase.request')
            return super(PurchaseRequest, self).write(vals)

    def action_confirm(self):
        for rec in self:
            if rec.request_type == 'purchase_request':
                if len(rec.line_ids) < 1:
                    raise ValidationError(_('Please enter the product you want to purchase !!!'))
            elif rec.request_type == 'tor_advance':
                if len(rec.service_line_ids) < 1:
                    raise ValidationError(_('Please enter the service you want to purchase !!!'))
            rec.sign_prepared = rec.requester_id.name
            rec.date_prepared = date.today().strftime('%Y-%m-%d')
            rec.state = 'confirm'

    def action_reviwe(self):
        for rec in self:
            # 1. Validation for Exchange Rate (Rate)
            if rec.rate <= 0:
                raise ValidationError(_('Please Enter Your Project Rate !!!'))
            
            # --- START BUDGET CHECK LOGIC FOR TOR ONLY ---
            if rec.request_type == "tor_advance":
                if not rec.service_line_ids:
                    raise ValidationError(_('Please enter the services you want to purchase !!!'))
                
                budget_totals = {}
                rate = rec.rate

                for line in rec.service_line_ids:
                    if not line.budget_line_code:
                        raise ValidationError(_('Please enter the budget line code for all service lines !!!'))
                    
                    # Calculate amount (Quantity * Frequency * Unit Price)
                    line_amount = line.total_price
                    
                    # Currency conversion logic
                    if line.currency_id != line.budget_line_code.currency_id:
                        converted_amount = line_amount * (1 / rate)
                    else:
                        converted_amount = line_amount
                    
                    # Grouping amounts by budget line to handle multiple lines for the same code
                    if line.budget_line_code in budget_totals:
                        budget_totals[line.budget_line_code] += converted_amount
                    else:
                        budget_totals[line.budget_line_code] = converted_amount

                # Perform the Shield Validation for the grouped totals
                for budget, total_requested in budget_totals.items():
                    symbol = budget.currency_id.symbol if budget.currency_id else ""
                    
                    # The Formula: (Current Request + Existing Theoretical) > (Planned + Allowed)
                    if (total_requested + budget.budget_line_theoritical_amount) > (budget.budget_line_planned_amount + budget.allowed_increase):
                        raise ValidationError(_(
                            "⛔ Budget Alert (TOR)\n\n"
                            f"Financial Code: {budget.line_code}\n"
                            f"Account: {budget.account_id.name}\n"
                            f"Total Requested in This TOR: {total_requested:,.2f} {symbol}\n"
                            f"Already Spent/Reserved: {budget.budget_line_theoritical_amount:,.2f} {symbol}\n"
                            f"Allowed Budget: {(budget.budget_line_planned_amount + budget.allowed_increase):,.2f} {symbol}\n\n"
                            "The Total Sum of Services For This Budget Line Exceeds The Available Balance!"
                        ))
            # --- END BUDGET CHECK LOGIC ---

            # Standard validation for PRS (Checking only if code exists)
            elif rec.request_type == "purchase_request":
                for line in rec.line_ids:
                    if not line.budget_line_code:
                        raise ValidationError(_('Please enter the budget line code !!!'))

            # Finalizing the record status and signature
            rec.sign_reviewed = str(self.env.user.name)
            rec.signature_reviewed = self.env.user.id
            rec.date_review = date.today().strftime('%Y-%m-%d')
            rec.state = 'review'

    def action_approve(self):
        for rec in self:
            if rec.request_type == 'tor_advance':
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
            rec.state = 'approved'

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'

    def action_done(self):
        self.write({'state': 'done'})

    def action_procurement_done(self):
        for rec in self:
            if not rec.product_type:
                raise ValidationError(_('Please Select the Product Type for This Request.'))
            rec.state = 'done'

    def action_procurement_draft(self):
        for rec in self:
            rec.state = 'draft'

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})
        self.sign_approved = False
        self.sign_reviewed = False
        self.sign_prepared = False

    def print_tor_advance_payment(self):
        action = self.env.ref('project_purchase_request.tor_advance_print_reports').read()[0]
        return action

    def print_prs_request(self):
        action = self.env.ref('project_purchase_request.prs_request_print_reports').read()[0]
        return action


class PurchaseRequestLine(models.Model):
    _name = 'purchase.request.line'
    _description = ' purchase request  line'
    _order = 'request_id, sequence, id'

    request_id = fields.Many2one(
        'project.purchase.request',
        string=' purchase request',
        ondelete='cascade',
        required=True,
        index=True
    )
    sequence = fields.Integer(string='sequence', default=10)
    state = fields.Selection(related="request_id.state", string="State")
    request_type = fields.Selection(related="request_id.request_type")
    product_id = fields.Char(string="Description")
    description = fields.Text(string='Technical Specification')
    product_uom = fields.Many2one('uom.uom', string='Unit', required=True,
                                  default=lambda self: self.env['uom.uom'].search([('name', '=', 'Units')], limit=1), )
    quantity = fields.Float(string='Quantity', required=True, default=1.0, digits='Product Unit of Measure')
    budget_line_code = fields.Many2one('budget.iteme.line', string="Budget Line Code")
    project_id = fields.Many2one(related="request_id.project_id", string='Project')
    document = fields.Binary(string='Document')
    account_id = fields.Many2one(related="budget_line_code.account_id", string="Account")
    currency_id = fields.Many2one(related="request_id.currency_id")

    @api.model_create_multi
    def create(self, vals_list):
        lines = super(PurchaseRequestLine, self).create(vals_list)
        for line in lines:
            if line.request_id:
                # Message when adding a new item line
                msg = _("New item added: %s (Qty: %s)") % (
                    line.product_id or 'No Description', 
                    line.quantity
                )
                line.request_id.message_post(body=msg)
        return lines

    def write(self, vals):
        # Fields to monitor for changes
        tracked_fields = ['product_id', 'description', 'quantity', 'budget_line_code']
        
        # Capture old values before the write operation
        pre_values = {
            line.id: {
                f: (line[f].display_name if hasattr(line[f], 'display_name') else line[f]) 
                for f in tracked_fields if f in line
            } for line in self
        }
        
        res = super(PurchaseRequestLine, self).write(vals)
        
        for line in self:
            changes = []
            for field in vals:
                if field in tracked_fields:
                    field_string = self._fields[field].string
                    old_val = pre_values.get(line.id, {}).get(field)
                    new_val = line[field].display_name if hasattr(line[field], 'display_name') else line[field]
                    
                    if old_val != new_val:
                        changes.append("<li><b>%s</b>: %s &rarr; %s</li>" % (field_string, old_val, new_val))
            
            if changes and line.request_id:
                # Log the changes in the parent Purchase Request Chatter
                body = _("Update in Item Details (<b>%s</b>):<ul>%s</ul>") % (
                    line.product_id or 'Item Line', 
                    "".join(changes)
                )
                line.request_id.message_post(body=body)
        return res

    def unlink(self):
        for line in self:
            if line.request_id:
                # Message when deleting an item line
                msg = _("🗑️ Item line deleted: %s") % (line.product_id or 'No Description')
                line.request_id.message_post(body=msg)
        return super(PurchaseRequestLine, self).unlink()

    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_('The quantity must be greater than zero.'))


class PurchaseRequestLineService(models.Model):
    _name = 'purchase.request.service'
    _description = ' Purchase Request Service'
    _order = 'request_id, sequence, id'

    sequence = fields.Integer(string='sequence', default=10)
    request_id = fields.Many2one('project.purchase.request', string="Purchase Request")
    state = fields.Selection(related="request_id.state", string="State")
    request_type = fields.Selection(related="request_id.request_type")
    quantity = fields.Float(string='Quantity', required=True, default=1.0, digits='Product Unit of Measure')
    frequency = fields.Float(string="Frequency", default=1.0, )
    unit_price = fields.Float(string="Unint Price")
    total_price = fields.Float(string="Total Price", compute='_compute_total_price')
    description_of_activities = fields.Text('Description of Activities')
    budget_line_code = fields.Many2one('budget.iteme.line', string="Budget Line Code")
    account_id = fields.Many2one(related="budget_line_code.account_id", string="Account")
    project_id = fields.Many2one(related="request_id.project_id", string='Project')
    document = fields.Binary(string='Document')
    currency_id = fields.Many2one(related="request_id.currency_id")
    unit_uom = fields.Many2one('uom.uom', string='Unit', required=True,
                               default=lambda self: self.env['uom.uom'].search([('name', '=', 'Units')], limit=1), )

    @api.depends('unit_price', 'quantity', 'frequency')
    def _compute_total_price(self):
        for rec in self:
            rec.total_price = rec.unit_price * rec.quantity * rec.frequency

    

    @api.model_create_multi
    def create(self, vals_list):
        lines = super(PurchaseRequestLineService, self).create(vals_list)
        for line in lines:
            if line.request_id:
                # Message when adding a new service line
                msg = _("New service line added: %s (Qty: %s)") % (
                    line.description_of_activities or 'No Description', 
                    line.quantity
                )
                line.request_id.message_post(body=msg)
        return lines

    def write(self, vals):
        # Fields to monitor in the purchase request
        tracked_fields = ['quantity', 'frequency', 'unit_price', 'budget_line_code', 'description_of_activities']
        
        # Store old values before update for comparison
        pre_values = {
            line.id: {
                f: (line[f].display_name if hasattr(line[f], 'display_name') else line[f]) 
                for f in tracked_fields if f in line
            } for line in self
        }
        
        res = super(PurchaseRequestLineService, self).write(vals)
        
        for line in self:
            changes = []
            for field in vals:
                if field in tracked_fields:
                    field_string = self._fields[field].string
                    old_val = pre_values.get(line.id, {}).get(field)
                    new_val = line[field].display_name if hasattr(line[field], 'display_name') else line[field]
                    
                    if old_val != new_val:
                        changes.append("<li><b>%s</b>: %s &rarr; %s</li>" % (field_string, old_val, new_val))
            
            if changes and line.request_id:
                # Header in English
                body = _("Update in Service Details (<b>%s</b>):<ul>%s</ul>") % (
                    line.description_of_activities or 'Service Line', 
                    "".join(changes)
                )
                line.request_id.message_post(body=body)
        return res

    def unlink(self):
        for line in self:
            if line.request_id:
                # Message when deleting a service line
                msg = _("🗑️ Service line deleted: %s") % (line.description_of_activities or 'No Description')
                line.request_id.message_post(body=msg)
        return super(PurchaseRequestLineService, self).unlink()



class PurchaseAttachment(models.Model):
    _name = 'request.attachment'
    _description = 'Request Attachment'

    request_id = fields.Many2one('project.purchase.request', string="Purchase Request")
    document = fields.Binary(string='Document', attachment=True)
    document_filename = fields.Char("Description")
