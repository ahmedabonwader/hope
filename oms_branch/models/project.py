# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date
import datetime


class InheritProject(models.Model):
    _inherit = 'project.project'

    branch_ids = fields.Many2many('oms.branch', string="Branches")
    authorizations_line_ids = fields.One2many('project.authorizations.line', 'project_id', string="Authorizations Line")


class ProjectAuthorizationsLine(models.Model):
    _name = 'project.authorizations.line'
    _description = 'Project Authorizations Line'

    project_id = fields.Many2one('project.project', string="Project")
    emp_id = fields.Many2one('hr.employee', string="Employee")
    currency_id = fields.Many2one('res.currency', string="Currency",
                                  default=lambda self: self.env['res.currency'].search([('name', '=', 'USD')], limit=1))
    department = fields.Many2one(related="emp_id.department_id", string="Department")
    amount = fields.Monetary(string="Amount")
    is_admin = fields.Boolean(string="Is Admin?")
