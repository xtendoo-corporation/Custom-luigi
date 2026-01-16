import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class PosOrderLine(models.Model):
    """
    Herencia de línea de pedido POS para añadir campo de agente de comisión.
    """

    _inherit = "pos.order.line"

    agent_id = fields.Many2one(
        "res.users",
        string="Agente de Comisión",
        help="Agente asignado para recibir la comisión de esta línea. "
        "Se asigna automáticamente si ya existe un vínculo de primera venta.",
    )


class PosOrder(models.Model):
    """
    Herencia de pedido POS para procesar vínculos de primera venta.
    Compatible con pos_conventional.
    """

    _inherit = "pos.order"

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create para procesar vínculos de primera venta después de crear el pedido.
        """
        orders = super().create(vals_list)
        for order in orders:
            order._process_first_sale_for_pos()
        return orders

    def write(self, vals):
        """
        Override write para procesar vínculos cuando se modifican las líneas.
        """
        result = super().write(vals)

        # Si se modificaron las líneas, reprocesar comisiones
        if "lines" in vals:
            for order in self:
                order._process_first_sale_for_pos()

        return result

    def _process_first_sale_for_pos(self):
        """
        Procesa las líneas del pedido POS para crear/asignar vínculos de primera venta.

        Para cada línea:
        - Si ya existe vínculo: asigna el agente original
        - Si no existe: crea el vínculo con el agente de la línea o el usuario del pedido
        """
        self.ensure_one()

        if not self.partner_id:
            return

        Commission = self.env["commission.first.sale"]

        for line in self.lines:
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
                source="pos",
            )

            if commission:
                # Si ya existía un vínculo, usar el agente original
                if not is_new and line.agent_id != commission.agent_id:
                    _logger.info(
                        "POS Order %s: Reasignando agente de '%s' a '%s' para producto %s",
                        self.name,
                        line.agent_id.name if line.agent_id else "Sin agente",
                        commission.agent_id.name,
                        line.product_id.display_name,
                    )
                    line.with_context(skip_commission_process=True).write(
                        {"agent_id": commission.agent_id.id}
                    )
                elif is_new:
                    # Asegurar que la línea tiene el agente correcto
                    line.with_context(skip_commission_process=True).write(
                        {"agent_id": commission.agent_id.id}
                    )

    def action_pay_account(self):
        """
        Override para procesar comisiones también cuando se crea albarán desde POS.
        (Herencia de pos_conventional)
        """
        # Procesar comisiones antes de crear el sale.order
        self._process_first_sale_for_pos()
        return super().action_pay_account()
