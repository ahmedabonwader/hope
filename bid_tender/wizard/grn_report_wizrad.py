import datetime
from odoo import fields, api, models, _
from odoo.exceptions import ValidationError
from dateutil import relativedelta
from datetime import date
import datetime


class GrnReportWizard(models.TransientModel):
    _name = "qrn.report.wizard"
    _description = "Grn Report Wizard"

    stock_picking_id = fields.Many2one('stock.picking', string="Picking")
    project_id = fields.Many2one('project.project', string="Project")
    prs_id = fields.Many2one('project.purchase.request', string="Prs")
    date = fields.Date(string="Received Date")
    received_by = fields.Many2one('hr.employee', string="Goods Received By")
    received_title = fields.Char(string="Title", compute="_compute_received_title", store=True)
    received_signature = fields.Many2one('res.users', string="Signature", compute="_compute_received_signature", store=True)
    received_location = fields.Char(string="Received Location")
    purchase_id = fields.Many2one('purchase.order', string="PO")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, readonly=True)

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

    def action_validate(self):
        for rec in self:
            rec.stock_picking_id.received_by = rec.received_by.id
            rec.stock_picking_id.received_title = rec.received_title
            rec.stock_picking_id.received_signature = rec.received_signature.id
            rec.stock_picking_id.date_received = rec.date
            rec.stock_picking_id.received_location = rec.received_location
            report_data = []
            report_line_data = []
            logo = rec.company_id.logo.decode('utf-8') if rec.company_id.logo else False
            report_data.append({
                'project': rec.project_id.name,
                'date': rec.date,
                'prs_id': rec.prs_id.ref,
                'stock_picking_id': rec.stock_picking_id.id,
                'po': rec.stock_picking_id.origin,
                'project_code': rec.project_id.project_code,
                'received_location': rec.received_location,
                'supplier': rec.stock_picking_id.partner_id.name,
                'supplier_ref': rec.purchase_id.partner_ref,
                'company_name': rec.company_id.name,
                'report_logo': logo,
                'received_location': rec.received_location,
                'delivered_by': rec.stock_picking_id.delivered_by,
                'title': rec.stock_picking_id.title,
                'date_de': rec.stock_picking_id.date_de,
                'received_by': rec.received_by.name,
                'received_title': rec.received_title,
                'received_signature': rec.received_signature.digital_signature,
            })
            for line in rec.stock_picking_id.move_ids_without_package:
                report_line_data.append({
                    'product_id': line.product_id.name,
                    'product_uom_qty': line.product_uom_qty,
                    'quantity': line.quantity,
                    'unit': line.product_uom.name,
                })
            
            vals = {
                
                "data": report_data,
                "line_data": report_line_data,
            }
            return self.env.ref('bid_tender.print_grn_reports').report_action(self, data=vals)