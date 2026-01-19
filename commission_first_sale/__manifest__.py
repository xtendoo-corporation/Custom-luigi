{
    "name": "Comisión Primera Venta",
    "version": "19.0.1.0.0",
    "category": "Sales/Commission",
    "summary": "Asigna comisiones permanentes al primer vendedor que vende un producto a un cliente",
    "description": """
        Módulo de comisiones basado en la regla de "Primera Venta":
        - El primer vendedor que vende un producto a un cliente se convierte en su dueño permanente
        - Las futuras ventas del mismo producto al mismo cliente mantienen al agente original
        - Funciona tanto en Ventas (sale.order) como en TPV (pos.order)
        - Compatible con pos_conventional
    """,
    "author": "Guillermo Barcena López",
    "website": "https://www.xtendoo.es",
    "license": "AGPL-3",
    "depends": [
        "base",
        "sale",
        "point_of_sale",
        "pos_conventional",
    ],
    "data": [
        "views/commission_first_sale_views.xml",
        "views/res_partner_views.xml",
        "views/sale_order_views.xml",
        "views/pos_order_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
