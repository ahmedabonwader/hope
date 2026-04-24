# -*- coding: utf-8 -*-
# from odoo import http


# class SalaryRules(http.Controller):
#     @http.route('/salary_rules/salary_rules', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/salary_rules/salary_rules/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('salary_rules.listing', {
#             'root': '/salary_rules/salary_rules',
#             'objects': http.request.env['salary_rules.salary_rules'].search([]),
#         })

#     @http.route('/salary_rules/salary_rules/objects/<model("salary_rules.salary_rules"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('salary_rules.object', {
#             'object': obj
#         })

