# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class Users(models.Model):
    _inherit = "res.users"

    digital_signature = fields.Binary(string="Signature")
    signature_image = fields.Binary(string="Signature (Image Upload)")
    check_image = fields.Boolean(string="Check Image", compute="_compute_check_image")

    @api.depends('signature_image')
    def _compute_check_image(self):
        for rec in self:
            if rec.signature_image:
                rec.check_image = True
            else:
                rec.check_image = False
