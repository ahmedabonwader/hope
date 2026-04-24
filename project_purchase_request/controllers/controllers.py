# -*- coding: utf-8 -*-
# from odoo import http


# class ProjectPurchaseRequest(http.Controller):
#     @http.route('/project_purchase_request/project_purchase_request', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/project_purchase_request/project_purchase_request/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('project_purchase_request.listing', {
#             'root': '/project_purchase_request/project_purchase_request',
#             'objects': http.request.env['project_purchase_request.project_purchase_request'].search([]),
#         })

#     @http.route('/project_purchase_request/project_purchase_request/objects/<model("project_purchase_request.project_purchase_request"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('project_purchase_request.object', {
#             'object': obj
#         })

