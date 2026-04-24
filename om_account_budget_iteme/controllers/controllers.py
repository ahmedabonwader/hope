# -*- coding: utf-8 -*-
# from odoo import http


# class OmAccountBudgetIteme(http.Controller):
#     @http.route('/om_account_budget_iteme/om_account_budget_iteme', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/om_account_budget_iteme/om_account_budget_iteme/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('om_account_budget_iteme.listing', {
#             'root': '/om_account_budget_iteme/om_account_budget_iteme',
#             'objects': http.request.env['om_account_budget_iteme.om_account_budget_iteme'].search([]),
#         })

#     @http.route('/om_account_budget_iteme/om_account_budget_iteme/objects/<model("om_account_budget_iteme.om_account_budget_iteme"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('om_account_budget_iteme.object', {
#             'object': obj
#         })

