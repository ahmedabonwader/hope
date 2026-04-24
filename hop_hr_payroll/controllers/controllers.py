# -*- coding: utf-8 -*-
# from odoo import http


# class HopHrPayroll(http.Controller):
#     @http.route('/hop_hr_payroll/hop_hr_payroll', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hop_hr_payroll/hop_hr_payroll/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('hop_hr_payroll.listing', {
#             'root': '/hop_hr_payroll/hop_hr_payroll',
#             'objects': http.request.env['hop_hr_payroll.hop_hr_payroll'].search([]),
#         })

#     @http.route('/hop_hr_payroll/hop_hr_payroll/objects/<model("hop_hr_payroll.hop_hr_payroll"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hop_hr_payroll.object', {
#             'object': obj
#         })

