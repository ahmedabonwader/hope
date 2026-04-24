# -*- coding: utf-8 -*-
# from odoo import http


# class AccountingReport(http.Controller):
#     @http.route('/accounting_report/accounting_report', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/accounting_report/accounting_report/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('accounting_report.listing', {
#             'root': '/accounting_report/accounting_report',
#             'objects': http.request.env['accounting_report.accounting_report'].search([]),
#         })

#     @http.route('/accounting_report/accounting_report/objects/<model("accounting_report.accounting_report"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('accounting_report.object', {
#             'object': obj
#         })

