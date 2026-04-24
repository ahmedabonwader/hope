# -*- coding: utf-8 -*-
{
    'name': "om_account_budget_iteme",

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
    'depends': ['base','om_account_budget',],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/ir.rule.xml',
        'data/sequnece.xml',
        'wizard/account_move_reversal_view.xml',
        'wizard/budget_update_planned_amount.xml',
        'wizard/quarter_update_wizard.xml',
        'wizard/quarter_plan_update_wizard.xml',
        'views/account_move.xml',
        'views/analytic_account.xml',
        'views/budget_item.xml',
        'views/account_move_line.xml',
        'views/budget_quarter.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

