from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError
from odoo.osv import expression
from datetime import date
import re


class AccountBudget(models.Model):
    _name = "budget.quarte"
    _order = 'id desc'

    _description = "Budget Quarter"

    name = fields.Char(string='Reference', readonly=True, index=True, copy=False, default=lambda self: _('New'))
    date = fields.Date(default=fields.Date.context_today, required=True, tracking=True, string='Date')
    budget_id = fields.Many2one('crossovered.budget', string='Budget Name', domain="[('state', '=', 'validate')]",
                                required=True)
    project_id = fields.Many2one(related='budget_id.project_id', string="project")
    budget_line_id = fields.Many2one('crossovered.budget.lines', string='Quarter',
                                     domain="[('crossovered_budget_id', '=', budget_id)]", required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('review', 'Reviewed'),
        ('done', 'Approved'),
        ('cancel', 'Canceled'),
    ], string="Status", default='draft', tracking=True)
    currency_id = fields.Many2one(related='budget_line_id.currency_id')
    quarter_line_ids = fields.One2many('budget.quarte.line', 'quarter_id')
    planned_amount = fields.Monetary(related='budget_line_id.planned_amount', string="Planned Amount")
    create_by = fields.Many2one('res.users', default=lambda self: self.env.user)
    allowed_increase = fields.Float(related='budget_id.allowed_increase', string="Allowed Increase (%)", store=True)
    total_line_amount = fields.Monetary(string='Total Line Amount', store=True, compute='_compute_total_line_amount',
                                        tracking=4)
    more_details = fields.Boolean(string="More Details", related="budget_id.more_details")
    approval_status = fields.Selection([
        ('review', 'Reviewed'),
        ('approve', 'Approved'),
        ('null', 'Null'),
    ], string="Approval State",  default="null")
    signature_approved = fields.Many2one('res.users', string="Signature Approveds")
    signature_reviewed = fields.Many2one('res.users', string="Signature Reviewed")
    date_approve = fields.Date()
    date_review = fields.Date()


    @api.depends('quarter_line_ids.planned_amount')
    def _compute_total_line_amount(self):
        for request in self:
            request.total_line_amount = sum(line.planned_amount for line in request.quarter_line_ids)
        if self.total_line_amount > self.planned_amount:
            raise UserError(_("The Quarter line  total amount is greater than  the planned budget .."))

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_review(self):
        for rec in self:
            if rec.state == 'confirm':
                rec.write({'state': 'review'})
            elif rec.state == 'done':
                rec.approval_status = 'review'
                rec.signature_reviewed = self.env.user.id
                rec.date_review = date.today().strftime('%Y-%m-%d')

    def action_confirm(self):
        for rec in self:
            for qu in rec.budget_line_id:
                qu.quarter_id = rec.id
        self.write({'state': 'confirm'})

    def action_done(self):
        for rec in self:
            if rec.state == 'review':
                rec.write({'state': 'done'})
                
    def action_approve(self):
        for rec in self:
            rec.approval_status = 'approve'
            rec.signature_approved = self.env.user.id
            rec.date_approve = date.today().strftime('%Y-%m-%d')

    def action_mm(self):
        self.write({'state': 'draft'})

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('budget.quart') or _('New')
        return super().create(vals_list)

    @api.onchange('budget_line_id')
    def onchange_quarter(self):
        chack_quarter = self.env["budget.quarte"].search(
            [('budget_id', '=', self.budget_id.id), ('budget_line_id', '=', self.budget_line_id.id)])
        if chack_quarter:
            raise UserError(_('The budget quarte settings have been made in advance.'))
        if self.quarter_line_ids:
            self.write({'quarter_line_ids': [(5, 0, 0)]})
        budget = self.env["crossovered.budget"].search([('id', '=', self.budget_id.id)])
        budget_vals = []
        if budget.budget_iteme_lines:
            for line in budget.budget_iteme_lines:
                if line:
                    budget_vals.append((0, 0, {
                        'line_code': line.line_code,
                        'budget_account': line.budget_account.id,
                        'budget_state': line.budget_state.id,
                        'account_id': line.account_id.id,
                        'description': line.description,
                        'burn_rate': line.burn_rate,
                    }))

            if budget_vals:
                self.quarter_line_ids = budget_vals

    def action_update_budget_lines(self):
        for rec in self:
            if not rec.budget_id:
                raise UserError(_("Please select a Budget Name first!"))

            # 1. جلب الأكواد الموجودة حالياً في الكوارتر (للبحث عن النواقص)
            # نستخدم التحويل لـ string و strip لضمان التطابق
            existing_codes = [line.line_code.strip() for line in rec.quarter_line_ids if line.line_code]

            new_lines_commands = []
            
            # 2. فحص أسطر الميزانية الأصلية (المصدر)
            if rec.budget_id.budget_iteme_lines:
                for line in rec.budget_id.budget_iteme_lines:
                    source_code = line.line_code.strip() if line.line_code else False
                    
                    # 3. الشرط: إذا كان الكود من الميزانية الكبيرة غير موجود في قائمة الكوارتر
                    if source_code and source_code not in existing_codes:
                        new_lines_commands.append((0, 0, {
                            'line_code': line.line_code,
                            'budget_account': line.budget_account.id,
                            'budget_state': line.budget_state.id,
                            'account_id': line.account_id.id,
                            'description': line.description,
                            'burn_rate': line.burn_rate,
                            'planned_amount': 0.0,
                        }))
                        # أضف الكود للقائمة فوراً لمنع التكرار في نفس الدورة
                        existing_codes.append(source_code)

            # 4. تنفيذ الإضافة للنواقص فقط
            if new_lines_commands:
                # نستخدم الحفظ المباشر لضمان تحديث قاعدة البيانات والواجهة
                rec.write({'quarter_line_ids': new_lines_commands})
            else:
                return {
                    'effect': {
                        'fadeout': 'slow',
                        'message': "Everything is already updated! No new lines to add.",
                        'type': 'rainbow_man',
                    }
                }

class BudgetQuarterLine(models.Model):
    _name = 'budget.quarte.line'
    _description = "Budget Quarter Line"

    line_code = fields.Char(string='Budget Line Code', )
    quarter_id = fields.Many2one('budget.quarte')
    account_id = fields.Many2one('account.account',
                                 string='Expense Account', )
    description = fields.Text(string='Description', )
    currency_id = fields.Many2one(related="quarter_id.currency_id", string="Currency", )
    planned_amount = fields.Monetary('Planned Amount')
    theoritical_amount = fields.Monetary(string='Theoretical Amount')
    remaining_amount = fields.Monetary(string='Remaining Amount', store=True, compute='_compute_remaining_amount',
                                       tracking=4)
    allowed_increase_line = fields.Float(string="Allowed Increase (%)", store=True,
                                         compute="_compute_allowed_increase_line")
    budget_account = fields.Many2one('budget.project.account', string="Project Account")
    budget_state = fields.Many2one('budget.project.state', string="State")
    burn_rate = fields.Integer(string="Burn Rate")
    quarter_type = fields.Selection([
        ('basic_quarter', 'Basic'),
        ('quarter_plan', 'Plan'),
    ], string='Quarter Type', default="quarter_plan",  readonly=True)
    seq = fields.Integer('Sequence', default=10, index=True)
    
    def action_update_quarter(self):
        vals = {
            'crossovered_budget_id': self.quarter_id.budget_line_id.id,
            'analytic_account_id': self.quarter_id.budget_line_id.analytic_account_id.id,
            'planned_amount': self.planned_amount,
            'quarter_id': self.id,
            'quarter_type': self.quarter_type,
        }
        new = self.env['quarter.update.wizard'].create(vals)
        return {
            'name': "Update Quarter",
            'type': 'ir.actions.act_window',
            'res_model': 'quarter.update.wizard',
            'res_id': new.id,
            'view_id': self.env.ref('om_account_budget_iteme.view_quarter_update_wizard_form', False).id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new'
        }

    @api.depends('quarter_id.allowed_increase', 'planned_amount')
    def _compute_allowed_increase_line(self):
        for rec in self:
            rec.allowed_increase_line = (rec.planned_amount * rec.quarter_id.allowed_increase) / 100

    @api.depends('theoritical_amount', 'planned_amount', 'allowed_increase_line')
    def _compute_remaining_amount(self):
        for order in self:
            order.remaining_amount = (order.planned_amount + order.allowed_increase_line) - order.theoritical_amount

    # @api.onchange('planned_amount')
    # def onchange_planned_amount(self):
    #     for record in self:
    #         if record.quarter_id.budget_id.budget_iteme_lines:
    #             for line in record.quarter_id.budget_id.budget_iteme_lines:
    #                 if line.account_id == record.account_id and line.line_code == record.line_code:
    #                     if record.planned_amount > line.budget_line_planned_amount:
    #                         raise UserError('----------&&&&&&&------------')

    def action_update_plan_quarter(self):
        self.ensure_one()
        return {
            'name': _('Update quarter Plan Amount'),
            'res_model': 'quarter.plan.update.wizard',
            'view_mode': 'form',
            'context': {
                'active_model': 'budget.quarte.line',
                'active_ids': self.id,
                'default_planned_amount': self.planned_amount,
                'default_remaining_amount': self.remaining_amount,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }
