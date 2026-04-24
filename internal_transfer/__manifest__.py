# -*- coding: utf-8 -*-
{
    'name': "Internal Transfer",

    'summary': "Internal Transfer between bank and cash journals",

    'description': """
        Internal Transfer between bank and cash journals model handle multi currency transfers
    """,

    'author': "Softclass / Ahmed Yahya , muslim alfadil",
    'website': "https://www.softclasssd.com",
    'category': 'Accounting',
    'version': '18.0.1.0',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'views/internal_transfer.xml',
    ],
}

