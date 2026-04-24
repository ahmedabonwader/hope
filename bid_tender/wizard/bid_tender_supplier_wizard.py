import datetime
from odoo import fields, api, models, _
from odoo.exceptions import ValidationError
from dateutil import relativedelta
from datetime import date
import datetime


class BidTenderSupplier(models.TransientModel):
    _name = "bid.tender.supplier.wizard"
    _description = "Bid Tender Supplier Wizard"

    bid_tender_id = fields.Many2one('oms.bid.tender', string="Bid Tender", readonly=True)
    project_id = fields.Many2one(related="bid_tender_id.project_id", string="Project")
    operation_type = fields.Selection(related="bid_tender_id.operation_type")
    prs_id = fields.Many2one(related="bid_tender_id.prs", string="Prs")
    bid_tender_supplier_line_ids = fields.One2many('bid.tender.supplier.line.wizard', 'bid_tender_supplier_id',
                                                   string="Supplier Line")

    def validate_payment(self):
        for rec in self:
            supplier_ids = []
            for bid_tender in rec.bid_tender_id:
                # Group lines by supplier_id
                lines_by_supplier = {}
                for line in bid_tender.bid_tender_line_ids:
                    if line.supplier_id:
                        lines_by_supplier.setdefault(line.supplier_id.id, []).append(line)

                for supplier_id, lines in lines_by_supplier.items():
                    supplier_ids.append(supplier_id)
                    for supplier_line in rec.bid_tender_supplier_line_ids:
                        for line in lines:
                            vals = {
                                'supplier_id': supplier_line.supplier_id.id,
                                'product_id': line.product_id.id,
                                'description': line.description,
                                'qty': line.qty,
                                'unut_id': line.unut_id.id,
                                'bid_tender_id': rec.bid_tender_id.id,
                            }
                            self.env['oms.bid.tender.line'].create(vals)
                            supplier_ids.append(supplier_line.supplier_id.id)

            if supplier_ids:
                rec.bid_tender_id.suppliers = [(6, 0, list(set(supplier_ids)))]


class BidTenderSupplerLine(models.TransientModel):
    _name = 'bid.tender.supplier.line.wizard'
    _description = "Bid Tender Supplier Line Wizard"

    bid_tender_supplier_id = fields.Many2one('bid.tender.supplier.wizard', string="Bid Tender Supplier")
    supplier_id = fields.Many2one('res.partner', string="Supplier")
