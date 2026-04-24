# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from dateutil import relativedelta
from datetime import date
import datetime


class OmsBranch(models.Model):
    _name = 'oms.branch'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'OMS Branch'

    name = fields.Char(string="Name")
    code = fields.Char(string="Code")
    date = fields.Date(string="Date", default=fields.Date.context_today)
    branch_line_ids = fields.One2many('oms.branch.line', 'branch_id', string="Branch Line")
    project_in_branch_ids = fields.One2many('oms.branch.project', 'branch_id', string="Branch Project Line")
    seq = fields.Integer('Sequence', required=False, copy=False, readonly=True, index=True)


class OMSBranchLine(models.Model):
    _name = 'oms.branch.line'
    _description = 'OMS Branch Line'

    branch_id = fields.Many2one('oms.branch', string="Branch")
    emp_id = fields.Many2one('hr.employee', string="Employee")
    currency_id = fields.Many2one('res.currency', string="Currency",
                                  default=lambda self: self.env['res.currency'].search([('name', '=', 'USD')], limit=1))
    department = fields.Many2one(related="emp_id.department_id", string="Department")
    amount = fields.Monetary(string="Amount")
    is_admin = fields.Boolean(string="Is Admin?")

    @api.constrains('amount')
    def _check_amount_positive(self):
        for record in self:
            if record.amount is not None and record.amount <= 0:
                raise ValidationError("The 'Amount' field must be greater than zero.")


class ProjectInBranch(models.Model):
    _name = 'oms.branch.project'
    _description = 'OMS Branch Project'

    branch_id = fields.Many2one('oms.branch', string="Branch")
    project_id = fields.Many2one('project.project', string="Project")
    state = fields.Selection([
        ('stop', 'Stop'),
        ('run', 'Running'),
        ('finsh', 'Finished'),
    ], default="stop", string="Status")


class ResUser(models.Model):
    _inherit = 'res.users'

    branch_ids = fields.Many2many('oms.branch', string='Branch')
    project_ids = fields.Many2many('project.project', string="Project")
    job_title = fields.Char(string="Job Title")


class InheritPurchaseOrder(models.Model):
    _inherit = 'purchase.order'

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
