# -*- coding: utf-8 -*-
{
    'name': "Default analytic account",

    'summary': """
        Set default analytic account based on project in bills
        """,

    'description': """
        This module adds functionality to automatically set default analytic accounts based on projects in bills and accounting entries.
        
        Key Features:
        * Automatically sets analytic account from project in accounting entries 
        * Ensures consistent analytic account tracking across modules
        * Reduces manual entry and potential errors
    """,

    'author': "Softclass",
    'version': '18.1',

    'depends': ['base','mail','project','purchase','account'],
    
    'data': [
        'views/move_line.xml',
        'views/purchase_line.xml',
        'views/project_project.xml',
    ],
    
}
