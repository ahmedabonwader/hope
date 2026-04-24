# -*- coding: utf-8 -*-
{
    'name': "bid_tender",

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
    'depends': ['base', 'mail', 'product', 'contacts', 'purchase', 'spreadsheet_dashboard', 'project_todo', 'project', 'hr', 'oms_branch', 'stock', 'calendar', 'hr_holidays'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/ir.rule.xml',
        'data/sequence.xml',
        'wizard/bid_tender_supplier_wizard.xml',
        'wizard/grn_report_wizard.xml',
        'views/bid_tender_views.xml',
        'views/purchase_order.xml',
        'views/inherit_purchase_order_rule.xml',
        'views/stock_picking.xml',
        'views/bid_tender_conf.xml',
        'views/certificate_completion.xml',
        'views/menu.xml',
        'reports/inherit_purchase_order.xml',
        'reports/grn_report_template.xml',
        'reports/print_bid_tender_report.xml',
        'reports/custom_report_layout_template.xml',
        'reports/certificate_completion_template.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
