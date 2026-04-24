# -*- coding: utf-8 -*-
{
    'name': "budget_report",

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
    'depends': ['base', 'account',  'om_account_budget', 'om_account_budget_iteme'],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/budget_report_wizard.xml',
        'wizard/finance_report.xml',
        'report/budget_templates.xml',
        'report/finance_report_paper_format.xml',
        'report/budget_report.xml',
        'report/print_finance_report_template.xml',

        'views/menu.xml',
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

