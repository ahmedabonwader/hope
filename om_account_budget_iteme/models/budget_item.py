from email.policy import default

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError
from odoo.osv import expression
from datetime import date
import datetime

import re


class AccountBudget(models.Model):
    _inherit = "crossovered.budget"
    _order = 'id desc'
    _description = "Budgetary Iteme"

    project_id = fields.Many2one('project.project', string='Project', domain="[('state', '=', 'validate' )]",
                                 required=True)
    account_id = fields.Many2one('account.move', string='account')
    budget_iteme_lines = fields.One2many(
        'budget.iteme.line', 'budget_iteme_id',
        'Budget Iteme Lines', copy=True
    )
    note = fields.Text(string='note')
    budget_total_amount = fields.Float(string=" Budget Total Amount", required=True)
    allowed_increase = fields.Float(string="Allowed Increase (%)", store=True)
    amount_total = fields.Float(string="Total", store=True, compute='_compute_buget_amounts', tracking=4)
    is_increase = fields.Boolean(store=True, tracking=4, compute='onchange_is_increase')
    create_by = fields.Many2one('res.users', default=lambda self: self.env.user)
    create_date = fields.Date(
        string='Date To', required=True,
        default=lambda self: fields.Date.to_string(date.today())
    )
    approve_by = fields.Many2one('res.users', )
    approve_date = fields.Date()
    date_prepared = fields.Date(string="Date", default=fields.Date.context_today)
    validate_bay = fields.Many2one('res.users')
    validate_date = fields.Date()
    reviewed_by = fields.Many2one('res.users', 'Reviewed')
    review_date = fields.Date(string="Reviewed Date")
    signature_reviewed = fields.Many2one('res.users', string="Signature Reviewed")
    signature_approved = fields.Many2one('res.users', string="Signature Approved")
    more_details = fields.Boolean(string="More Details", store=True, )
    curr_id = fields.Many2one(related="project_id.curr_id", string="Currency")
    prepared_job_title = fields.Char(string="Prepared Job Title", compute="_compute_prepared_job_title", store=True)
    reviewed_job_title = fields.Char(string="Reviewed Job Title", compute="_compute_reviewed_job_title", store=True)
    approved_job_title = fields.Char(string="Approved Job Title", compute="_compute_approved_job_title", store=True)
    quarter_count = fields.Integer(string="Quarter Count", compute="_compute_quarter_count")

    def _compute_quarter_count(self):
        for rec in self:
            quarter_count = self.env['budget.quarte'].search_count([('budget_id', '=', rec.id)])
            rec.quarter_count = quarter_count

    def action_quarter_count(self):
        for rec in self:
            domain = [('budget_id', '=', rec.id)]
            return {
                'type': 'ir.actions.act_window',
                'name': 'budget_quarte',
                'res_model': 'budget.quarte',
                'domain': domain,
                'view_mode': 'list,form',
                'target': 'current',
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

    @api.depends('allowed_increase')
    def onchange_is_increase(self):
        for record in self:
            if record.allowed_increase > 0.0:
                record.is_increase = True
            else:
                record.is_increase = False

    @api.depends('budget_iteme_lines.budget_line_planned_amount', 'company_id')
    def _compute_buget_amounts(self):
        total = [0.0]
        for order in self.budget_iteme_lines:
            total.append((order.budget_line_planned_amount))
        self.amount_total = sum(total)

    def write(self, vals):
        res = super(AccountBudget, self).write(vals)
        index = 0
        for record in self.crossovered_budget_line:
            index = index + 1
            record.write({'quarter': 'quarter : ' + str(index)})
        return res

    def create(self, values):
        res = super(AccountBudget, self).create(values)
        if res:
            index = 0
            for record in res['crossovered_budget_line']:
                index = index + 1
                record.write({'quarter': 'quarter : ' + str(index)})
        return res

    @api.onchange('amount_total')
    def check_amount(self):
        for record in self:
            if record.amount_total > record.budget_total_amount:
                message = f"The amount {record.amount_total} is greater than project budget."
                raise UserError(_(message))

    def action_budget_confirm(self):
        if any(record.rate <= 0.0 for record in self.crossovered_budget_line):
            raise UserError(_('Please enter the rate'))
        for rec in self:
            if len(rec.crossovered_budget_line) < 1:
                raise ValidationError(_('Please enter the project Budgets !!!'))
            if len(rec.budget_iteme_lines) < 1:
                raise ValidationError(_('Please enter the project Budgets  Line!!!'))
            rec.validate_bay = self.env.user.id
            rec.validate_date = fields.Date.to_string(date.today())
            rec.review_date = fields.Date.to_string(date.today())
            rec.reviewed_by = self.env.user.id
            rec.signature_reviewed = self.env.user.id
            # get job title for users
            # emp_search_confirm = self.env['hr.employee'].search([
            #     ('name', '=', rec.user_id.name)
            # ], limit=1)
            # if emp_search_confirm:
            #     rec.prepared_job_title = emp_search_confirm.job_id.name
            # emp_search_review = self.env['hr.employee'].search([
            #     ('name', '=', rec.signature_reviewed.name)
            # ], limit=1)
            # if emp_search_review:
            #     rec.reviewed_job_title = emp_search_review.job_id.name
            rec.write({'state': 'confirm'})

    def action_budget_draft(self):
        self.write({'state': 'draft'})

    def action_budget_validate(self):
        for rec in self:
            rec.validate_bay = self.env.user.id
            rec.signature_approved = self.env.user.id
            rec.approve_by = self.env.user.id
            rec.approve_date = fields.Date.to_string(date.today())
            rec.validate_date = fields.Date.to_string(date.today())

            # emp_search = self.env['hr.employee'].search([
            #     ('name', '=', rec.signature_approved.name)
            # ], limit=1)
            # if emp_search:
            #     rec.approved_job_title = emp_search.job_id.name
            rec.write({'state': 'validate'})
            rec.project_id.write({'state': 'running'})

    def action_budget_cancel(self):
        for rec in self:
            rec.write({'state': 'cancel'})
            rec.project_id.write({'state': 'cancel'})

    def action_budget_done(self):
        for rec in self:
            rec.project_id.write({'state': 'done'})
            rec.write({'state': 'done'})

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError('sorry you cannot delete record if it is not in draft state..')
            else:
                super().unlink()

    @api.constrains('budget_total_amount')
    def _check_amount(self):
        for record in self:
            if record.budget_total_amount <= 0:
                raise ValidationError(_("The  budget total amount cannot be zero. Please provide a valid amount."))


class BudgetLine(models.Model):
    _inherit = "crossovered.budget.lines"
    _rec_name = 'quarter'

    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account', required=True)
    quarter = fields.Char(string='Quarter')
    budget_line_theoritical_amount = fields.Float(string='Theoretical Amount', readonly=False, )
    remaining_amount = fields.Float(string='Remaining Amount', store=True, compute="_compute_remaining_amount")
    project_id = fields.Many2one(related="crossovered_budget_id.project_id")
    rate = fields.Float(string="Rate", required=True)
    quarter_id = fields.Many2one('budget.quarte')
    quarter_type = fields.Selection([
        ('basic_quarter', 'Basic'),
        ('quarter_plan', 'Plan'),
    ], string='Quarter Type', default="basic_quarter", readonly=True)
    currency_id = fields.Many2one('res.currency', string="Currency",
                                  default=lambda self: self.env['res.currency'].search([('name', '=', 'USD')], limit=1),
                                  readonly=False)

    def action_open_budget_quarter(self):

        return {
            'type': 'ir.actions.act_window',
            'name': 'Table Title',
            'res_model': 'budget.quarte',
            'view_mode': 'list,form',
            'target': 'current',
            'context': {
                'create': False
            },
            'domain': [('budget_line_id', '=', self.id)],
        }

    @api.depends('planned_amount', 'budget_line_theoritical_amount')
    def _compute_remaining_amount(self):
        for rec in self:
            rec.remaining_amount = rec.planned_amount - rec.budget_line_theoritical_amount

    @api.onchange('crossovered_budget_id')
    def _onchange_crossovered_budget_id(self):
        ProjectProject = self.env['project.project']
        for line in self:
            if line.analytic_account_id:
                continue
            project_id = line._context.get('project_id')
            project = ProjectProject.browse(project_id) if project_id else line.crossovered_budget_id.project_id
            if project:
                line.analytic_account_id = project.account_id

    def action_update_quarter(self):
        for rec in self:
            vals = {
                'analytic_account_id': rec.analytic_account_id.id,
                'planned_amount': rec.planned_amount,
                'crossovered_budget_id': rec.id,
                'quarter_type': self.quarter_type,
            }
            new = self.env['quarter.update.wizard'].create(vals)
            return {
                'name': "Quarter Update Wizard",
                'type': 'ir.actions.act_window',
                'res_model': 'quarter.update.wizard',
                'res_id': new.id,
                'view_id': self.env.ref('om_account_budget_iteme.view_quarter_update_wizard_form', False).id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new'
            }


class accountBudgetItemLine(models.Model):
    _name = "budget.iteme.line"
    _description = "Budget Line Iteme"
    _rec_name = "line_code"

    line_code = fields.Char(string='Budget Line Code', required=True)
    budget_iteme_id = fields.Many2one('crossovered.budget', 'Budget', ondelete='cascade', index=True, required=True)
    account_id = fields.Many2one(
        comodel_name='account.account', check_company=True,
        string='Expense Account',
        domain="[('deprecated', '=', False), \
                    ('account_type', '=', 'expense')]", required=True)
    currency_id = fields.Many2one('res.currency', string="Currency",
                                  default=lambda self: self.env['res.currency'].search([('name', '=', 'USD')], limit=1),
                                  readonly=False)
    budget_line_planned_amount = fields.Monetary('Planned Amount', required=True)
    budget_line_theoritical_amount = fields.Monetary(string='Theoretical Amount', readonly=False, )
    remaining_amount = fields.Monetary(string='Remaining Amount', store=True, compute='_compute_budget_amount',
                                       tracking=4)

    project_id = fields.Many2one(related="budget_iteme_id.project_id", string="Project", store=True, )
    # state = fields.Selection(related='budget_iteme_id.state')
    company_id = fields.Many2one(related='budget_iteme_id.company_id', comodel_name='res.company',
                                 string='Company', store=True, readonly=True)
    description = fields.Text(string='Description')
    burn_rate = fields.Integer(string="Burn Rate", compute='_compute_burn_rate', store=True)
    allowed_increase = fields.Float(string="Allowed Increase", store=True, compute="_compute_allowed_increase",
                                    digits=(16, 2))
    check = fields.Boolean(string='Check', default=False, compute="_compute_check")
    budget_state = fields.Many2one('budget.project.state', string="State")
    budget_account = fields.Many2one('budget.project.account', string="Project Account")
    more_details = fields.Boolean(string="More Details", related="budget_iteme_id.more_details")
    seq = fields.Integer('Sequence', default=10, index=True)

    @api.onchange('budget_state', 'budget_account')
    def onchange_line_code(self):
        for rec in self:
            base = rec.line_code or ''
            if '-' in base:
                parts = base.split('-')
                if len(parts) >= 3:
                    base = parts[1]
                elif len(parts) == 2:
                    base = parts[1]

            state_name = rec.budget_state.name if rec.budget_state else ''
            account_name = rec.budget_account.name if rec.budget_account else ''

            if state_name and account_name:
                rec.line_code = f"{state_name}-{base}-{account_name}"
            elif state_name:
                rec.line_code = f"{state_name}-{base}"
            elif account_name:
                rec.line_code = f"{base}-{account_name}"
            else:
                rec.line_code = base

    @api.depends('budget_line_planned_amount', 'budget_iteme_id.allowed_increase')
    def _compute_allowed_increase(self):
        for rec in self:
            rec.allowed_increase = rec.budget_line_planned_amount * (rec.budget_iteme_id.allowed_increase / 100)

    @api.depends('budget_line_theoritical_amount', 'budget_line_planned_amount')
    def _compute_burn_rate(self):
        for rec in self:
            if rec.budget_line_planned_amount and rec.budget_line_planned_amount != 0.0:
                rec.burn_rate = (rec.budget_line_theoritical_amount / rec.budget_line_planned_amount) * 100
            else:
                rec.burn_rate = 0.0

    @api.depends('budget_iteme_id')
    def _compute_check(self):
        for rec in self:
            if rec.budget_iteme_id:
                if rec.budget_iteme_id.state in ('validate', 'done'):
                    rec.check = True
                else:
                    rec.check = False

    @api.depends('budget_line_theoritical_amount', 'budget_line_planned_amount', 'allowed_increase')
    def _compute_budget_amount(self):
        for order in self:
            order.remaining_amount = (
                                                 order.budget_line_planned_amount + order.allowed_increase) - order.budget_line_theoritical_amount

    # def unlink(self):
    # # Agregar codigo de validacionaca
    #     for record in self.budget_iteme_id:
    #         if record.state != 'draft':
    #             raise UserError('sorry you cannot delete record if it is not in draft state..')

    def action_update_planned_amount(self):
        self.ensure_one()
        return {
            'name': _('Update Planned Amount'),
            'res_model': 'update.amount.wizard',
            'view_mode': 'form',
            'context': {
                'active_model': 'budget.iteme.line',
                'active_ids': self.id,
                'default_account_id': self.account_id.id,
                'default_planned_amount': self.budget_line_planned_amount,
                'default_theoritical_amount': self.budget_line_theoritical_amount,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }


class BudgetProjectState(models.Model):
    _name = 'budget.project.state'
    _description = 'Budget Project State'

    name = fields.Char(string="Name")


class BudgetProjectAccount(models.Model):
    _name = 'budget.project.account'
    _description = 'Budget Project Account'

    name = fields.Char(string="Name")
    state_id = fields.Many2one('budget.project.state', 'State')

# for quarter in line.quarter_id:
#     print('###########')
#     for qu in quarter.quarter_id:
#         print('$$$$$$$$$$$$')
#         for qu_line in qu.quarter_line_ids:
#             if qu_line.currency_id != rec.currency_id:
#                 print('@@@@@@@@@@@@@@@@@@')
#                 if qu_line.theoritical_amount + (line.price_unit * (
#                         1 / rec.rate)) > qu_line.planned_amount + qu_line.allowed_increase_line:
#                     raise ValidationError(_(
#                         "⛔ alert\n\n"
#                         f"Code: {line.budget_item_line_id.line_code}\n"
#                         f"Account:   {line.account_id.name}\n"
#                         "The invoice amount is greater than the Planned balance in the quarter.."
#                     ))
#                 qu_line.theoritical_amount = line.price_unit * (1 / rec.rate)
#             elif qu_line.currency_id == rec.currency_id:
#                 if qu_line.theoritical_amount + (line.price_unit * (
#                         1 / rec.rate)) > qu_line.planned_amount + qu_line.allowed_increase_line:
#                     raise ValidationError(_(
#                         "⛔ alert\n\n"
#                         f"Code: {line.budget_item_line_id.line_code}\n"
#                         f"Account:   {line.account_id.name}\n"
#                         "The invoice amount is greater than the Planned balance in the quarter.."
#                     ))
#                 qu_line.theoritical_amount = line.price_unit * (1 / rec.rate)
