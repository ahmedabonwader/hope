# -*- coding: utf-8 -*-
{
    'name': "Inherit Accounting",

    'summary': "Inherit Accounting multi features",

    'description': """
        Inherit Accounting multi features for accounting module:
        - Inherit account.journal model to add user_ids field
        - Inherit account.payment.register wizard to add multiple features
        - Inherit account.payment.method.line model to add multiple features
        - Inherit account.move model to add multiple features
            
    """,

    'author': "Softclass / Ahmed Yahya , Muslim Alfadel",
    'website': "https://www.softclasssd.com",

    'category': 'Accounting',
    'version': '18.0.1.0',

    'depends': ['base', 'account', 'project', 'om_account_budget_iteme', 'purchase', 'bid_tender', 'oms_branch',
                'expense', 'project', 'budget_report'],

    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/ir.rule.xml',
        'data/sequnece.xml',
        # 'wizard/budget_report_wizard.xml',
        'wizard/account_payment_register.xml',
        'wizard/authorized_wizard.xml',
        'wizard/bank_statement_wizard.xml',
        'wizard/inherit_create_bank_letter_wizard.xml',
        'views/account_move.xml',
        'views/account_payment.xml',
        'views/base_location.xml',
        'views/account_journal.xml',
        'views/bank_letters.xml',
        'views/bank_list.xml',
        'views/menu.xml',
        'report/vendor_bills_report.xml',
        'report/bank_letters_report_template.xml',
        'report/bank_statement_report_template.xml',
        # 'report/budget_report.xml'
    ],
}
