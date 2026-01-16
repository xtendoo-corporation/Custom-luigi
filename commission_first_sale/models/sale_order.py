import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    """
    Herencia de línea de pedido de venta para añadir campo de agente de comisión.
    """

    _inherit = "sale.order.line"

    agent_id = fields.Many2one(
        "res.users",
        string="Agente de Comisión",
        help="Agente asignado para recibir la comisión de esta línea. "
        "Se asigna automáticamente si ya existe un vínculo de primera venta.",
    )

    @api.onchange("product_id", "order_id")
    def _onchange_product_check_agent(self):
        """
        Al cambiar el producto, buscar si existe un vínculo de primera venta
        y asignar automáticamente el agente.
        """
        if self.product_id and self.order_id.partner_id:
            Commission = self.env["commission.first.sale"]
            existing_agent = Commission.get_agent_for_product(
                self.order_id.partner_id.id, self.product_id.id
            )
            if existing_agent:
                self.agent_id = existing_agent
                return {
                    "warning": {
                        "title": _("Agente Asignado Automáticamente"),
                        "message": _(
                            'Se ha asignado el agente "%s" porque ya existe un vínculo de primera venta para este producto y cliente.'
                        )
                        % existing_agent.name,
                    }
                }


class SaleOrder(models.Model):
    """
    Herencia de pedido de venta para procesar vínculos de primera venta al confirmar.
    """

    _inherit = "sale.order"

    def action_confirm(self):
        """
        Override para procesar vínculos de primera venta antes de confirmar.
        """
        for order in self:
            order._process_first_sale_commissions()
        return super().action_confirm()

    def _process_first_sale_commissions(self):
        """
        Procesa las líneas del pedido para crear/asignar vínculos de primera venta.

        Para cada línea:
        - Si ya existe vínculo: asigna el agente original
        - Si no existe: crea el vínculo con el agente de la línea o el vendedor del pedido
        """
        self.ensure_one()

        if not self.partner_id:
            return

        Commission = self.env["commission.first.sale"]

        for line in self.order_line:
            if not line.product_id:
                continue

            # Buscar o crear vínculo
            agent_to_use = line.agent_id or self.user_id

            if not agent_to_use:
                continue

            commission, is_new = Commission.get_or_create_commission(
                partner_id=self.partner_id.id,
                product_id=line.product_id.id,
                agent_id=agent_to_use.id,
                origin=self.name,
                source="sale",
            )

            if commission:
                # Si ya existía un vínculo, usar el agente original
                if not is_new and line.agent_id != commission.agent_id:
                    _logger.info(
                        "Sale Order %s: Reasignando agente de '%s' a '%s' para producto %s",
                        self.name,
                        line.agent_id.name if line.agent_id else "Sin agente",
                        commission.agent_id.name,
                        line.product_id.display_name,
                    )
                    line.agent_id = commission.agent_id
                elif is_new:
                    # Asegurar que la línea tiene el agente correcto
                    line.agent_id = commission.agent_id
