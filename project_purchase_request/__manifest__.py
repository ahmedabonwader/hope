# -*- coding: utf-8 -*-
{
    'name': "project_purchase_request",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'project', 'mail', 'purchase', 'uom'],  # أضف 'mail' هنا
    # always loaded
    'data': ['security/security.xml',
             'security/ir.model.access.csv',
             'security/ir.rule.xml',
             'data/seqence.xml',
             'wizard/old_data.xml',
             'views/project_purchase_request.xml',
             'views/project_prs_request.xml',
             'views/menu.xml',
             'report/print_tor_advance_report.xml',
             'report/print_prs_request_report.xml',
             ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
