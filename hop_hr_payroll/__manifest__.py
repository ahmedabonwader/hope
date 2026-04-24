# -*- coding: utf-8 -*-
{
    'name': "hop_hr_payroll",

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
    'depends': ['base','hr_contract', 'project', 'om_account_budget_iteme','mail', 'hr',],  # أضف 'mail' هنا

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/ir.rule.xml',
        'data/seqence.xml',
        'wizard/salary_payment_sheet.xml',
        'wizard/social_insurance_and_tax_wizard.xml',
        'wizard/create_bank_letters_wizard.xml',
        'wizard/contract_template_wizard.xml',
        'wizard/paysheet_wizard.xml',
        
        # 'views/res_config_settings.xml',
        'report/payslip_project_templates.xml',
        'report/salary_payment_sheet_template.xml',
        'report/payslip_report.xml',
        'report/print_social_insurance_report.xml',
        'report/print_taxes_report.xml',
        'report/contrcat_template_report.xml',
        'report/staff_basic_information_template.xml',
        # 'views/hr_payslip_project.xml',
        'views/salary_payslips.xml',
        'views/hr_leave_allocation.xml',
        'views/salary_configuration.xml',
        'views/hr_contract.xml',
        'views/hr_employee.xml',
        'views/project.xml',
        'views/social_insurance_payment.xml',
        'views/hope_print_contract_configuration.xml',
        'views/menu.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

