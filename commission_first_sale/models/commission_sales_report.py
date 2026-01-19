from odoo import fields, models, tools


class CommissionSalesReport(models.Model):
    _name = "commission.sales.report"
    _description = "Conteo de Comisiones"
    _auto = False
    _rec_name = "date"
    _order = "date desc"

    date = fields.Datetime("Fecha", readonly=True)
    agent_id = fields.Many2one("hr.employee", "Agente", readonly=True)
    product_id = fields.Many2one("product.product", "Producto", readonly=True)
    partner_id = fields.Many2one("res.partner", "Cliente", readonly=True)
    amount = fields.Float("Monto Total", readonly=True)
    qty = fields.Float("Cantidad", readonly=True)
    origin = fields.Char("Origen", readonly=True)
    source = fields.Selection(
        [("sale", "Ventas"), ("pos", "Punto de Venta")], "Fuente", readonly=True
    )
    company_id = fields.Many2one("res.company", "Compañía", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
            CREATE or REPLACE VIEW %s as (
                -- Ventas (Sale Order Line)
                SELECT
                    sol.id as id,
                    so.date_order as date,
                    sol.agent_id as agent_id,
                    sol.product_id as product_id,
                    so.partner_id as partner_id,
                    sol.price_subtotal as amount,
                    sol.product_uom_qty as qty,
                    so.name as origin,
                    'sale' as source,
                    so.company_id as company_id
                FROM sale_order_line sol
                JOIN sale_order so ON (sol.order_id = so.id)
                WHERE sol.agent_id IS NOT NULL
                  AND so.state IN ('sale', 'done')

                UNION ALL

                -- POS (Pos Order Line)
                SELECT
                    pol.id * -1 as id, -- ID negativo para evitar colisiones
                    po.date_order as date,
                    pol.agent_id as agent_id,
                    pol.product_id as product_id,
                    po.partner_id as partner_id,
                    pol.price_subtotal_incl as amount, -- POS suele usar incl, pero subtotal mejor para comparar
                    pol.qty as qty,
                    po.pos_reference as origin,
                    'pos' as source,
                    po.company_id as company_id
                FROM pos_order_line pol
                JOIN pos_order po ON (pol.order_id = po.id)
                WHERE pol.agent_id IS NOT NULL
                  AND po.state IN ('paid', 'done', 'invoiced')
            )
        """
            % self._table
        )
