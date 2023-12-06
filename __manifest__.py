# -*- coding: utf-8 -*-
{
    'name': "jt_stock_portal",

    'summary': "",

    'description': "",

    'author': "jaco tech",
    'website': "https://jaco.tech",
    "license": "AGPL-3",


    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.9',

    # any module necessary for this one to work correctly
    'depends': ['base','stock','portal','jt_stock_subcontracting','purchase_stock','jt_product_vendorcodes'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/portal.xml',
    ],
    # only loaded in demonstration mode
    # 'demo': [
    #     'demo/demo.xml',
    # ],
}
