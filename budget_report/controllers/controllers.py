# -*- coding: utf-8 -*-
# from odoo import http


# class BudgetReport(http.Controller):
#     @http.route('/budget_report/budget_report', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/budget_report/budget_report/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('budget_report.listing', {
#             'root': '/budget_report/budget_report',
#             'objects': http.request.env['budget_report.budget_report'].search([]),
#         })

#     @http.route('/budget_report/budget_report/objects/<model("budget_report.budget_report"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('budget_report.object', {
#             'object': obj
#         })

