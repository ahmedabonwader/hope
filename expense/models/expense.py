from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import ValidationError
import datetime
from datetime import date


class HmsExpense(models.Model):
    _name = 'hms.expense.request'
    _description = 'request expenses'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'ref'
    _order = 'id desc'

    def get_default_journal(self):
        journal = self.env['account.journal'].search([('type', '=', 'bank')], limit=1)
        return journal.id

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
    expense = fields.Many2one('product.template', string="Description", tracking=True, required=False)
    move_id = fields.Many2one('account.move', string="Bill#")
    description = fields.Char(string="Description", required=True, tracking=True)
    expense_amount = fields.Float(string="Expense Amount", compute="compute_expense_amount", tracking=True, store=True)
    # expense_amount = fields.Float(string="Expense Amount", compute="compute_expense_amount", store=True, )
    time = fields.Date(string="Time", default=fields.Date.context_today, readonly=False, tracking=True)
    amount = fields.Float("Amount", tracking=True, required=True)
    sign_reviewed = fields.Char(string="Sign Reviewed")
    sign_hr_reviewed = fields.Char(string="Sign Reviewed")
    signature_reviewed = fields.Many2one('res.users', string="Signature Reviewed")
    sign_approved = fields.Char(string="Sign Approved")
    signature_approved = fields.Many2one('res.users', string="Signature Approved")
    signature_hr_approved = fields.Many2one('res.users', string="Signature HR Approved")
    date_approve = fields.Date()
    date_review = fields.Date()
    code = fields.Binary()
    # payment_method = fields.Many2one('account.journal', domain="[('type', 'in', ('bank','cash'))]",
    #                                  tracking=True, string="Payment Method", required=True, default=get_default_journal)
    payment_method = fields.Many2one('account.journal', tracking=True, string="Payment Method", required=False)
    ref = fields.Char(string='Reference', tracking=True)
    partner_id = fields.Many2one('res.partner', string="Recipient", tracking=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", tracking=True)
    user_id = fields.Many2one('res.users', string="User", tracking=True, default=lambda self: self.env.user.id, readonly=True)
    expense_type = fields.Selection([
        ('expense', 'Expense'),
        ('advance', 'Advance'),
        ('loan', 'Loan'),
    ], default="expense", string="Expense Type", tracking=True, required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('review', 'reviewed'),
        ('done', 'Approved'),
        ('cancel', 'Canceled'),
    ], string="Status", default='draft', tracking=True)
    payment_status = fields.Selection([
        ('not_paid', 'Not Paid'),
        ('paid', 'Paid'),
    ], string="Payment Status", default="not_paid", tracking=True)
    month = fields.Selection([
        ('01', 'January'),
        ('02', 'February'),
        ('03', 'March'),
        ('04', 'April'),
        ('05', 'May'),
        ('06', 'June'),
        ('07', 'July'),
        ('08', 'August'),
        ('09', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ], string="Month")
    hr_review_approval = fields.Selection([
        ('review', 'Reviewed'),
        ('approve', 'Approved'),
    ], string="Approval", tracking=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, readonly=True)
    loan_duration = fields.Integer(string="Loan Deduction")
    how_much_deduct = fields.Float(string="How Much Deduct?", compute="_compute_how_much_deduct", store=True)
    note = fields.Text(string="Note", tracking=True)
    currency_id = fields.Many2one('res.currency', string="Currency",
                                  default=lambda self: self.env['res.currency'].search([('name', '=', 'SDG')], limit=1))
    bank_account = fields.Char(string="Bank Account", tracking=True)
    account_id = fields.Many2one('account.account', string="Account", tracking=True)
    expense_line_ids = fields.One2many('expense.line', 'expense_id', string="xpense Line")
    rate = fields.Float(string="Rate", tracking=True)
    method_payment_check = fields.Boolean(string="Method Check", compute="_compute_method_payment_check", store=True)
    contract_type = fields.Selection([
        ('project', 'By Project'),
        ('contract', 'By Contract'),
        ('hybrid', 'Hybrid'),
    ], string="Contract Format Type", compute='_compute_contract_type', store=True,)
    operation_department = fields.Selection([
        ('finance_expense', 'Finance'),
        ('hr_expense', 'HR'),
        ('hybird', 'Hybird'),
    ], steing="Operation Department", compute="_compute_operation_department")
    check_contract = fields.Boolean(string="Contract Selected")
    check_invisible_confirm_button = fields.Boolean('Button Invisible', store=True)
    project_select = fields.Many2one('project.project', string="Project Select")
    budget_line = fields.Many2one('budget.iteme.line', string="Budget Line")
    
    @api.onchange('expense_type', 'contract_type', 'check_contract')
    def onchange_check_invisible_confirm_button(self):
        for rec in self:
            if rec.expense_type in ('advance', 'loan') and rec.contract_type in ('project', 'hybrid') and rec.check_contract == False:
                rec.check_invisible_confirm_button = True
            else:
                rec.check_invisible_confirm_button = False

    def action_select_contract(self):
        vals = {
                'employee_id': self.employee_id.id,
                'expense_type': self.expense_type,
                'contract_type': self.contract_type,
                'expense_id': self.id,
            }
        new = self.env['select.contract.wizard'].create(vals)
        return {
            'name': "Select Contract",
            'type': 'ir.actions.act_window',
            'res_model': 'select.contract.wizard',
            'res_id': new.id,
            'view_id': self.env.ref('expense.view_select_contract_wizard_form', False).id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new'
        }

    @api.depends('employee_id')
    def _compute_contract_type(self):
        for rec in self:
            contract = self.env['hr.contract'].search([
                ('employee_id', '=', rec.employee_id.id),
            ], limit=1)
            if contract:
                rec.contract_type = contract.contract_type

    @api.depends('user_id')
    def _compute_operation_department(self):
        for rec in self:
            operation_person = self.env['oms.operation.person'].search([
                ('user_id', '=', rec.user_id.id),
            ], limit=1)
            rec.operation_department = operation_person.expense_department

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        user = self.env.user
        operation_person = self.env['oms.operation.person'].search([
            ('user_id', '=', user.id),
        ], limit=1)
        if not operation_person:
            raise ValidationError(_(
                "You cannot create this record because you are not registered as an Operation Person.\n"
                "Please ask the administrator to create your Operation Person record first. Or Ask your Admin"
            ))
        return res

    def print_advance_payment(self):
        action = self.env.ref('expense.action_report_advance_loan_payment').read()[0]
        return action

    def action_print_petty_cash_payment(self):
        action = self.env.ref('expense.action_report_petty_cash_payment').read()[0]
        return action

    def action_hr_review(self):
        for rec in self:
            rec.sign_hr_reviewed = str(self.env.user.name)
            rec.hr_review_approval = 'review'

    def action_hr_approval(self):
        for rec in self:
            rec.hr_review_approval = 'approve'
            rec.signature_hr_approved = self.env.user.id

    @api.depends('expense_line_ids')
    def compute_expense_amount(self):
        for rec in self:
            total = 0
            for line in rec.expense_line_ids:
                total += line.total_amount
                rec.expense_amount = total

    @api.depends('payment_method')
    def _compute_method_payment_check(self):
        for rec in self:
            if rec.payment_method.type == 'cash':
                rec.method_payment_check = True
            elif rec.payment_method.type == 'bank':
                rec.method_payment_check = False

    @api.depends('amount', 'loan_duration')
    def _compute_how_much_deduct(self):
        for rec in self:
            if rec.expense_type == 'loan':
                if rec.amount > 0 and rec.loan_duration > 0:
                    rec.how_much_deduct = rec.amount / rec.loan_duration

    def action_review(self):
        for rec in self:
            if rec.rate == 0:
                    raise ValidationError(_('Sorry, Please Enter Rate'))
            if rec.expense_type == 'expense':
                for line in rec.expense_line_ids:
                    if not line.account_id:
                        raise ValidationError(_('Sorry, please select the account to complete your process'))
            elif rec.expense_type in ('loan', 'advance'):
                if rec.rate == 0:
                    raise ValidationError(_('Sorry, Please Enter Rate'))
                if not rec.account_id:
                    raise ValidationError(_('Sorry, please select the account to complete your process'))
                if rec.contract_type in ('project', 'hybrid'):
                    if not rec.budget_line:
                        raise ValidationError(_('Sorry, please select the budget line to complete your process'))
            rec.sign_reviewed = str(self.env.user.name)
            rec.signature_reviewed = self.env.user.id
            rec.date_review = date.today().strftime('%Y-%m-%d')
            rec.state = 'review'

    def action_rev(self):
        for rec in self:
            rec.action_review()

    def action_confirm(self):
        for rec in self:
            if rec.amount == 0 and rec.expense_type != 'expense':
                raise ValidationError(_("Sorry the amount can not be zero !!!"))
            if rec.expense_type == 'expense':
                if len(rec.expense_line_ids) < 1:
                    raise ValidationError(_('Sorry you can not confirm without adding some product in line'))
                for line in rec.expense_line_ids:
                    if line.unit_price == 0:
                        raise ValidationError(_('Sorry The Unit Price can not be zero in the line'))
                    if not line.pro_id:
                        raise ValidationError(_('Sorry Please add Product in the line'))
            elif rec.expense_type == 'loan':
                loan_payment = self.env['hms.expense.request.loan.line'].search([
                    ('operation_type', '=', 'loan'),
                    ('check_loan', '=', False),
                    ('employee_id', '=', rec.employee_id.id),
                ], limit=1)
                if loan_payment:
                    raise ValidationError(_('Sorry you can not pay another loan until you pay your last loan !!!'))
                
                contract = self.env['hr.contract'].search([
                    ('state', '=', 'open'),
                    ('employee_id', '=', rec.employee_id.id),
                ], limit=1)
                # if contract:       
                #     for contract_id in contract:
                #         if contract_id.contract_type == 'contract':
                #             if contract_id.curr_id != rec.currency_id:
                #                 if rec.how_much_deduct > (contract_id.wage * 50/100) * (contract_id.curr_id.rate_ids.inverse_company_rate):
                #                     raise ValidationError(_('The deducted amount is greater than 50%% of the Salary'))
                #             elif contract_id.curr_id == rec.currency_id:
                #                 if rec.how_much_deduct > (contract_id.wage * 50/100):
                #                     raise ValidationError(_('The deducted amount is greater than 50%% of the Salary'))
                #         elif contract_id.contract_type in ('project', 'hybrid'):
                #             for line in contract_id.contract_line_ids:
                #                 if line.curr_id != rec.currency_id and line.loan_subtract == True and line.state == 'run':
                #                     if rec.how_much_deduct > (line.p_total_salary * 50/100) * (line.curr_id.rate_ids.inverse_company_rate):
                #                         raise ValidationError(_('The deducted amount is greater than 50%% of the Salary'))
                #                 elif line.curr_id == rec.currency_id and line.loan_subtract == True and line.state == 'run':
                #                     if rec.how_much_deduct > (line.p_total_salary * 50/100):
                #                         raise ValidationError(_('The deducted amount is greater than 50%% of the Salary'))
                if not contract:
                    raise ValidationError(_('Sorry This employee dose not have a running contract'))
            
            elif rec.expense_type == 'advance':
                contract = self.env['hr.contract'].search([
                    ('state', '=', 'open'),
                    ('employee_id', '=', rec.employee_id.id),
                ], limit=1)
                if contract:
                    advance_conf = self.env['oms.advance.loan.conf'].search([
                        ('operation_type', '=', 'advance')
                    ], limit=1)
                    for contract_id in contract:
                        if contract_id.contract_type == 'contract':
                            advance_payment = self.env['hms.expense.request.advance.line'].search([
                                ('operation_type', '=', 'advance'),
                                ('check_advance', '=', False),
                                ('employee_id', '=', rec.employee_id.id),
                            ], limit=1)
                            if advance_payment:
                                raise ValidationError(_('Sorry you can not pay another advance until you pay your last advance !!!'))
                            if contract_id.curr_id != rec.currency_id:
                                if advance_conf:
                                    if rec.amount * contract.curr_id.rate_ids.company_rate > contract_id.wage * advance_conf.maximum_percentage / 100:
                                        raise ValidationError(_('Sorry The Amount you enter it too biger'))
                                elif not advance_conf:
                                    raise ValidationError(_('Sorry you are not set Configuration for advance role Pleast set it first or ask your admin to set it'))   
                            elif contract_id.curr_id == rec.currency_id:
                                advance_conf = self.env['oms.advance.loan.conf'].search([
                                    ('operation_type', '=', 'advance')
                                ], limit=1)
                                if advance_conf:
                                    if rec.amount > contract_id.wage * advance_conf.maximum_percentage / 100:
                                        raise ValidationError(_('Sorry The Amount you enter it too biger'))
                                elif not advance_conf:
                                    raise ValidationError(_('Sorry you are not set Configuration for loan role Pleast set it first or ask your admin to set it'))
                        elif contract_id.contract_type in ('project', 'hybrid'):
                            for line in contract_id.contract_line_ids:
                                if line.curr_id != rec.currency_id and line.advance_subtract == True and line.state == 'run' and line.project_id == rec.project_select:
                                    if rec.amount * line.curr_id.rate_ids.company_rate > line.p_total_salary * advance_conf.maximum_percentage / 100:
                                        raise ValidationError(_('Sorry The Amount you enter it too biger'))
                                elif line.curr_id == rec.currency_id and line.advance_subtract == True and line.state == 'run' and line.project_id == rec.project_select:
                                    if rec.amount > line.p_total_salary * advance_conf.maximum_percentage / 100:
                                        raise ValidationError(_('Sorry The Amount you enter it too biger'))
                                    
                elif not contract:
                    raise ValidationError(_('Sorry This employee dose not have a running contract'))
            rec.state = 'confirm'

    def action_approve(self):
        for rec in self:
            if rec.expense_type == 'expense':
                if rec.company_id.currency_id != rec.currency_id:
                    account_move_vals = {
                        'partner_id': rec.partner_id.id,
                        'ref': rec.description,
                        'move_type': 'in_invoice',
                        'expense_id': rec.id,
                        # 'currency_id': rec.currency_id.id,
                    }
                    account_move = self.env['account.move'].create(account_move_vals)
                    for line in rec.expense_line_ids:
                        account_move_line_vals = {
                            'move_id': account_move.id,
                            'name': str(line.pro_id.name),
                            'account_id': line.account_id.id,
                            'quantity': line.qty,
                            'price_unit': line.unit_price * rec.rate,
                            'price_subtotal': line.total_amount * rec.rate
                        }
                        account_move_line = self.env['account.move.line'].create(account_move_line_vals)
                        rec.move_id = account_move.id
                elif rec.company_id.currency_id == rec.currency_id:
                    account_move_vals = {
                        'partner_id': rec.partner_id.id,
                        'ref': rec.description,
                        'move_type': 'in_invoice',
                        'expense_id': rec.id,
                        # 'currency_id': rec.currency_id.id,
                    }
                    account_move = self.env['account.move'].create(account_move_vals)
                    for line in rec.expense_line_ids:
                        account_move_line_vals = {
                            'move_id': account_move.id,
                            'name': str(line.pro_id.name),
                            'account_id': line.account_id.id,
                            'quantity': line.qty,
                            'price_unit': line.unit_price * (1/rec.rate),
                            'price_subtotal': line.total_amount * (1/rec.rate)
                        }
                        account_move_line = self.env['account.move.line'].create(account_move_line_vals)
                        rec.move_id = account_move.id
            elif rec.expense_type in ('loan', 'advance'):
                if rec.amount == 0:
                    raise ValidationError(_("Sorry the amount can not be zero !!!"))
                if not rec.account_id:
                    raise ValidationError(_("Please select The account"))
                if not rec.project_select:
                    if rec.company_id.currency_id != rec.currency_id:
                        partner_id = self.env['res.partner'].search([
                            ('name', '=', rec.employee_id.name),
                        ], limit=1)
                        if partner_id:
                            account_move_vals = {
                                'partner_id': partner_id.id,
                                'move_type': 'in_invoice',
                                'expense_id': rec.id,
                                'ref': rec.description,
                                'loan_advance_project': rec.project_select.id,
                                # 'currency_id': rec.currency_id.id,
                            }
                            account_move = self.env['account.move'].create(account_move_vals)
                            account_move_line_vals = {
                                'name': rec.description,
                                'move_id': account_move.id,
                                'account_id': rec.account_id.id,
                                'price_unit': rec.amount * rec.rate,
                                'quantity': 1,
                            }
                            account_move_line = self.env['account.move.line'].create(account_move_line_vals)
                            rec.move_id = account_move.id
                        elif not partner_id:
                            partner_vals = {
                                'name': rec.employee_id.name,
                            }
                            partner = self.env['res.partner'].create(partner_vals)
                            account_move_vals = {
                                'partner_id': partner.id,
                                'move_type': 'in_invoice',
                                'expense_id': rec.id,
                                'ref': rec.description,
                                'loan_advance_project': rec.project_select.id,
                                # 'currency_id': rec.currency_id.id,
                            }
                            account_move = self.env['account.move'].create(account_move_vals)
                            account_move_line_vals = {
                                'name': rec.description,
                                'move_id': account_move.id,
                                'account_id': rec.account_id.id,
                                'price_unit': rec.amount * rec.rate,
                                'quantity': 1,
                            }
                            account_move_line = self.env['account.move.line'].create(account_move_line_vals)
                            rec.move_id = account_move.id
                    elif rec.company_id.currency_id == rec.currency_id:
                        partner_id = self.env['res.partner'].search([
                            ('name', '=', rec.employee_id.name),
                        ], limit=1)
                        if partner_id:
                            account_move_vals = {
                                'partner_id': partner_id.id,
                                'move_type': 'in_invoice',
                                'expense_id': rec.id,
                                'ref': rec.description,
                                'loan_advance_project': rec.project_select.id,
                                # 'currency_id': rec.currency_id.id,
                            }
                            account_move = self.env['account.move'].create(account_move_vals)
                            account_move_line_vals = {
                                'name': rec.description,
                                'move_id': account_move.id,
                                'account_id': rec.account_id.id,
                                'price_unit': rec.amount * (1/rec.rate),
                                'quantity': 1,
                            }
                            account_move_line = self.env['account.move.line'].create(account_move_line_vals)
                            rec.move_id = account_move.id
                        elif not partner_id:
                            partner_vals = {
                                'name': rec.employee_id.name,
                            }
                            partner = self.env['res.partner'].create(partner_vals)
                            account_move_vals = {
                                'partner_id': partner.id,
                                'move_type': 'in_invoice',
                                'expense_id': rec.id,
                                'ref': rec.description,
                                'loan_advance_project': rec.project_select.id,
                                # 'currency_id': rec.currency_id.id,
                            }
                            account_move = self.env['account.move'].create(account_move_vals)
                            account_move_line_vals = {
                                'name': rec.description,
                                'move_id': account_move.id,
                                'account_id': rec.account_id.id,
                                'price_unit': rec.amount * (1/rec.rate),
                                'quantity': 1,
                            }
                            account_move_line = self.env['account.move.line'].create(account_move_line_vals)
                            rec.move_id = account_move.id
                elif rec.project_select:
                    if rec.company_id.currency_id != rec.currency_id:
                        partner_id = self.env['res.partner'].search([
                            ('name', '=', rec.employee_id.name),
                        ], limit=1)
                        if partner_id:
                            account_move_vals = {
                                'partner_id': partner_id.id,
                                'move_type': 'in_invoice',
                                'expense_id': rec.id,
                                'ref': rec.description,
                                'loan_advance_project': rec.project_select.id,
                                'project_id': rec.project_select.id,
                                # 'currency_id': rec.currency_id.id,
                            }
                            account_move = self.env['account.move'].create(account_move_vals)
                            account_move_line_vals = {
                                'name': rec.description,
                                'move_id': account_move.id,
                                'account_id': rec.account_id.id,
                                'price_unit': rec.amount * rec.rate,
                                'quantity': 1,
                                'budget_item_line_id': rec.budget_line.id
                            }
                            account_move_line = self.env['account.move.line'].create(account_move_line_vals)
                            rec.move_id = account_move.id
                        elif not partner_id:
                            partner_vals = {
                                'name': rec.employee_id.name,
                            }
                            partner = self.env['res.partner'].create(partner_vals)
                            account_move_vals = {
                                'partner_id': partner.id,
                                'move_type': 'in_invoice',
                                'expense_id': rec.id,
                                'ref': rec.description,
                                'loan_advance_project': rec.project_select.id,
                                'project_id': rec.project_select.id,
                                # 'currency_id': rec.currency_id.id,
                            }
                            account_move = self.env['account.move'].create(account_move_vals)
                            account_move_line_vals = {
                                'name': rec.description,
                                'move_id': account_move.id,
                                'account_id': rec.account_id.id,
                                'price_unit': rec.amount * rec.rate,
                                'quantity': 1,
                                'budget_item_line_id': rec.budget_line.id
                            }
                            account_move_line = self.env['account.move.line'].create(account_move_line_vals)
                            rec.move_id = account_move.id
                    elif rec.company_id.currency_id == rec.currency_id:
                        partner_id = self.env['res.partner'].search([
                            ('name', '=', rec.employee_id.name),
                        ], limit=1)
                        if partner_id:
                            account_move_vals = {
                                'partner_id': partner_id.id,
                                'move_type': 'in_invoice',
                                'expense_id': rec.id,
                                'ref': rec.description,
                                'loan_advance_project': rec.project_select.id,
                                'project_id': rec.project_select.id,
                                # 'currency_id': rec.currency_id.id,
                            }
                            account_move = self.env['account.move'].create(account_move_vals)
                            account_move_line_vals = {
                                'name': rec.description,
                                'move_id': account_move.id,
                                'account_id': rec.account_id.id,
                                'price_unit': rec.amount * (1/rec.rate),
                                'quantity': 1,
                                'budget_item_line_id': rec.budget_line.id
                            }
                            account_move_line = self.env['account.move.line'].create(account_move_line_vals)
                            rec.move_id = account_move.id
                        elif not partner_id:
                            partner_vals = {
                                'name': rec.employee_id.name,
                            }
                            partner = self.env['res.partner'].create(partner_vals)
                            account_move_vals = {
                                'partner_id': partner.id,
                                'move_type': 'in_invoice',
                                'expense_id': rec.id,
                                'ref': rec.description,
                                'loan_advance_project': rec.project_select.id,
                                'project_id': rec.project_select.id,
                                # 'currency_id': rec.currency_id.id,
                            }
                            account_move = self.env['account.move'].create(account_move_vals)
                            account_move_line_vals = {
                                'name': rec.description,
                                'move_id': account_move.id,
                                'account_id': rec.account_id.id,
                                'price_unit': rec.amount * (1/rec.rate),
                                'quantity': 1,
                                'budget_item_line_id': rec.budget_line.id
                            }
                            account_move_line = self.env['account.move.line'].create(account_move_line_vals)
                            rec.move_id = account_move.id
            
            rec.signature_approved = self.env.user.id
            rec.sign_approved = str(self.env.user.name)
            rec.date_approve = date.today().strftime('%Y-%m-%d')
            rec.state = 'done'

    def action_reset_to_draft(self):
        for rec in self:
            rec.state = 'draft'
            rec.payment_status = 'not_paid'

    def action_back(self):
        for rec in self:
            rec.state = 'review'
            

    def action_cancel(self):
        for rec in self:
            account_move = self.env['account.move'].search([
                ('partner_id', '=', rec.partner_id.id),
                ('move_type', '=', 'in_invoice'),
                ('expense_id', '=', rec.id),
            ], limit=1)
            if account_move:
                account_move.state = 'cancel'
            rec.state = 'cancel'
            rec.payment_status = 'not_paid'

    @api.model
    def create(self, vals):
        vals['ref'] = self.env['ir.sequence'].next_by_code('hms.expense.request')
        return super(HmsExpense, self).create(vals)


class ExpenseLine(models.Model):
    _name = 'expense.line'
    _description = 'Expense Line'

    expense_id = fields.Many2one('hms.expense.request', string="Expense")
    product_id = fields.Many2one('product.product', string="Product")
    pro_id = fields.Many2one('expense.product', string="Product")
    account_id = fields.Many2one('account.account', string="Account")
    qty = fields.Float(string="Quantity", default=1.0)
    unit_price = fields.Float(string="Unit Price")
    total_amount = fields.Float(string="Total Amount", compute="_compute_total_amount")
    currency_id = fields.Many2one(related="expense_id.currency_id", string="Currency", )
    state = fields.Selection(related="expense_id.state")
    expense_type = fields.Selection(related="expense_id.expense_type")

    @api.depends('unit_price', 'qty')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = rec.unit_price * rec.qty


class CustomExpenseProduct(models.Model):
    _name = 'expense.product'
    _description = 'Expense Product'

    name = fields.Char(string="Name")


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    salary_line_ids = fields.One2many('hms.expense.request.salary.line', 'employee_id', string="Salary Line")
    loan_line_ids = fields.One2many('hms.expense.request.loan.line', 'employee_id', string="Loan Line")
    advance_line_ids = fields.One2many('hms.expense.request.advance.line', 'employee_id', string="Loan Line")


class HRContract(models.Model):
    _inherit = 'hr.contract'

    curr_id = fields.Many2one('res.currency', string="Currency", default=lambda self: self.env['res.currency'].search([('name', '=', 'USD')], limit=1), readonly=False)

class HmsExpenseLoanLine(models.Model):
    _name = 'hms.expense.request.loan.line'
    _description = 'request expenses Loan Line'
    _order = 'id desc'

    # expense_id = fields.Many2one('hms.expense.request', string="Expense")
    employee_id = fields.Many2one('hr.employee', string="Employee")
    partner_id = fields.Many2one('res.partner', string="Recipient")
    amount = fields.Float(string="Amount")
    date = fields.Date(string="Date")
    loan_duration = fields.Integer(string="Loan Deduction")
    operation_type = fields.Selection([
        ('expense', 'Expense'),
        ('salary', 'Salary'),
        ('loan', 'Loan'),
    ], string="Operation Type")
    currency_id = fields.Many2one('res.currency', string="Currency")
    check_loan = fields.Boolean(string="Loan Check", compute="_compute_check_loan", store=True)
    loan_count = fields.Integer(string="Loan Count")
    payment_method = fields.Many2one('account.journal', domain="[('type', 'in', ('bank','cash'))]",
                                     string="Payment Method", )
    deduct = fields.Float(string="How Much Deduct?")
    rate = fields.Float('Rate')
    project_id = fields.Many2one('project.project', string="Project")
    contract_type = fields.Selection([
        ('project', 'Project'),
        ('contract', 'Contract'),
        ('hybrid', 'hybrid'),
    ], string="Contract Type")

    @api.depends('loan_count', 'loan_duration')
    def _compute_check_loan(self):
        for rec in self:
            if rec.loan_count == rec.loan_duration:
                rec.check_loan = True
            else:
                rec.check_loan = False


class HmsExpenseSalaryLine(models.Model):
    _name = 'hms.expense.request.salary.line'
    _description = 'request expenses Salary Line'
    _order = 'id desc'

    expense_id = fields.Many2one('hms.expense.request', string="Expense")
    employee_id = fields.Many2one('hr.employee', string="Employee")
    partner_id = fields.Many2one('res.partner', string="Recipient")
    amount = fields.Float(string="Amount")
    date = fields.Date(string="Date")
    loan_duration = fields.Integer(string="Loan Deduction")
    operation_type = fields.Selection([
        ('expense', 'Expense'),
        ('salary', 'Salary'),
        ('loan', 'Loan'),
    ], string="Operation Type")
    check_loan = fields.Boolean(string="Loan Check", compute="_compute_check_loan", store=True)
    loan_count = fields.Integer(string="Loan Count")
    payment_method = fields.Many2one('account.journal', domain="[('type', 'in', ('bank','cash'))]",
                                     string="Payment Method", )
    month = fields.Selection([
        ('01', 'January'),
        ('02', 'February'),
        ('03', 'March'),
        ('04', 'April'),
        ('05', 'May'),
        ('06', 'June'),
        ('07', 'July'),
        ('08', 'August'),
        ('09', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ], string="Month")
    currency_id = fields.Many2one('res.currency', string="Currency")

    @api.depends('loan_count', 'loan_duration')
    def _compute_check_loan(self):
        for rec in self:
            if rec.loan_count == rec.loan_duration:
                rec.check_loan = True
            else:
                rec.check_loan = False



class HmsExpenseAdvanceLine(models.Model):
    _name = 'hms.expense.request.advance.line'
    _description = 'request expenses Advance Line'
    _order = 'id desc'

    employee_id = fields.Many2one('hr.employee', string="Employee")
    amount = fields.Float(string="Amount")
    date = fields.Date(string="Date")
    advance_duration = fields.Integer(string="Advance Deduction", default=1)
    operation_type = fields.Selection([
        ('expense', 'Expense'),
        ('advance', 'Advance'),
        ('loan', 'Loan'),
    ], string="Operation Type")
    rate = fields.Float('Rate')
    check_advance = fields.Boolean(string="Advance Check", compute="_compute_check_advance", store=True)
    advance_count = fields.Integer(string="Advance Count")
    currency_id = fields.Many2one('res.currency', string="Currency")
    payment_method = fields.Many2one('account.journal', domain="[('type', 'in', ('bank','cash'))]", string="Payment Method",)
    contract_type = fields.Selection([
        ('project', 'Project'),
        ('contract', 'Contract'),
        ('hybrid', 'hybrid'),
    ], string="Contract Type")
    project_id = fields.Many2one('project.project', string="Project")

    @api.depends('advance_count', 'advance_duration')
    def _compute_check_advance(self):
        for rec in self:
            if rec.advance_count == rec.advance_duration:
                rec.check_advance = True
            else:
                rec.check_advance = False

class InheritAccountJournal(models.Model):
    _inherit = 'account.journal'

    user_id = fields.Many2one('res.users', string="User")