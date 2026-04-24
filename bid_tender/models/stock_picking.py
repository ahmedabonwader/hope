from odoo import models, fields, api
from datetime import date
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from dateutil import relativedelta
from datetime import date
import datetime


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    project_id = fields.Many2one('project.project', string="Project")
    project_code = fields.Char(related="project_id.project_code", string="Project Code")
    prs = fields.Many2one('project.purchase.request', string="PRS")
    users_id = fields.Many2one('res.users', tracking=True)
    delivered_by = fields.Char(string="Goods Delivered By", tracking=True)
    title = fields.Char(string="Title", tracking=True)
    date_de = fields.Date(string="Date", tracking=True)
    purchase_id = fields.Many2one('purchase.order', string="PO")

    received_by = fields.Many2one('hr.employee', string="Goods Received By")
    received_title = fields.Char(string="Title", compute="_compute_received_title", store=True)
    received_signature = fields.Many2one('res.users', string="Signature", compute="_compute_received_signature", store=True)
    date_received = fields.Date(string="Received Date")
    received_location = fields.Char(string="Received Location")

    @api.depends('received_by')
    def _compute_received_signature(self):
        for rec in self:
            if rec.received_by:
                rec.received_signature = rec.received_by.user_id.id
    
    @api.depends('received_by')
    def _compute_received_title(self):
        for rec in self:
            if rec.received_by:
                rec.received_title = rec.received_by.job_id.name

    def action_print_grn(self):
        for rec in self:
            vals = {
                'stock_picking_id': rec.id,
                'project_id': rec.project_id.id,
                'prs_id': rec.prs.id,
                'received_by': rec.received_by.id,
                'received_title': rec.received_title,
                'received_signature': rec.received_signature.id,
                'purchase_id': rec.purchase_id.id,
                'date': rec.date_received,
                'received_location': rec.received_location,
            }
            new = self.env['qrn.report.wizard'].create(vals)
            return {
                'name': "QRN Wizard",
                'type': 'ir.actions.act_window',
                'res_model': 'qrn.report.wizard',
                'res_id': new.id,
                'view_id': self.env.ref('bid_tender.view_qrn_report_wizard_form', False).id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new'
            }

    