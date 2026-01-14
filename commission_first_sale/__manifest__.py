# -*- coding: utf-8 -*-
{
    'name': 'Commission First Sale',
    'version': '19.0.1.0.0',
    'summary': 'Assign commission to the first seller who sold a product to a partner (Sales & POS backend)',
    'description': """
Module to track the first seller (user) who sold a specific product to a specific customer.
Once recorded, future sales of that product to the same customer attribute commission to that original user.
Works for Sales and POS backend (pos.order create in backend).
""",
    'author': 'Guillermo Bárcena',
    'category': 'Sales',
    'depends': ['base', 'sale_management', 'point_of_sale', 'xtendoo_pos_conventional' if False else 'pos_conventional'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
    'license': 'AGPL-3',
}
