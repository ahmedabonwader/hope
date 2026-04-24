# -*- coding: utf-8 -*-
{
    'name': "Program",

    'summary': """
        Enhance Project Management with Program Organization Features
        """,

    'description': """
        This module extends the standard Odoo Project application to support program-level organization and management.
        
        Key Features:
        * Organize multiple projects under programs
        * Track program-level progress and metrics
        * Manage program objectives and deliverables
        * Enhanced reporting at program level
        * Hierarchical project structure within programs
    """,

    'author': "Softclass",
    'version': '18.1',

    'depends': ['base','mail','project'],
    
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/ir.rule.xml',
        'views/project.xml',
        'views/project_task.xml',
        'views/followup_template_views.xml',
    ],
    
}
