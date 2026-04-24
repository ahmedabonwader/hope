from odoo import models, fields, api

class FollowupTemplate(models.Model):
    _name = 'project.followup.template'
    _description = 'Project Followup Template'
    _order = 'name'

    name = fields.Char('Template Name', required=True)
    template_content = fields.Html('Template Content', required=True, sanitize=True)
    active = fields.Boolean(default=True) 