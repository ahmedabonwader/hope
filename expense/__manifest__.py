# -*- coding: utf-8 -*-
{
    'name': "Expense",

    'summary': """manage expenses in your company""",

    'description': """
        Manage Expenses operations in your Company and make change
    """,

    'author': "softclass",
    'license': 'LGPL-3',
    'category': 'Accounting',
    'version': '16.1',
    'application': True,
    'depends': ['base', 'mail', 'account', 'product', 'hr_contract', 'oms_branch', 'hop_hr_payroll'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequnece.xml',
        'wizard/daily_report.xml',
        'wizard/custody_report.xml',
        'wizard/select_contract_wizard.xml',
        'views/expense_view.xml',
        'views/loan_advance_conf.xml',
        'views/operation_person.xml',
        'views/menu.xml',
        'views/hr_employee.xml',
        'reports/daily_expense_report.xml',
        'reports/print_custody_report_template.xml',
        'reports/print_petty_cash_report.xml',
        'reports/print_advance_loan_payment_report.xml',
    ],
}
