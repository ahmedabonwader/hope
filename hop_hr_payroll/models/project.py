# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date
import datetime


class InheritProject(models.Model):
    _inherit = 'project.project'

    state_ids = fields.Many2many('hr.state.location', string="States")