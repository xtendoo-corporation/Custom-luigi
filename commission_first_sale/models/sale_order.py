import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    """
    Herencia de línea de pedido de venta para añadir campo de agente de comisión.
    """

    _inherit = "sale.order.line"

    agent_id = fields.Many2one(
        "hr.employee",
        string="Agente de Comisión",
        help="Empleado asignado para recibir la comisión de esta línea. "
        "Se asigna automáticamente si ya existe un vínculo de primera venta.",
    )
    is_commission_locked = fields.Boolean(
        string="Comisión Bloqueada",
        compute="_compute_is_commission_locked",
        store=True,
        help="Indica si el agente ya está fijado por un vínculo existente.",
    )

    @api.depends("product_id", "order_id.partner_id")
    def _compute_is_commission_locked(self):
        Commission = self.env["commission.first.sale"]
        for line in self:
            if line.product_id and line.order_id.partner_id:
                existing_agent = Commission.get_agent_for_product(
                    line.order_id.partner_id.id, line.product_id.id
                )
                line.is_commission_locked = bool(existing_agent)
                if existing_agent:
                    line.agent_id = existing_agent
            else:
                line.is_commission_locked = False

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
            # Si no existe, intentar asignar el empleado del usuario actual por defecto
            elif not self.agent_id and self.env.user.employee_id:
                self.agent_id = self.env.user.employee_id


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
            # Intentar usar el agente de la línea, o el empleado asociado al usuario del pedido
            agent_to_use = line.agent_id
            if not agent_to_use and self.user_id:
                # Buscar empleado del usuario del pedido
                employee = self.env["hr.employee"].search(
                    [("user_id", "=", self.user_id.id)], limit=1
                )
                agent_to_use = employee

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

    @api.onchange("partner_id")
    def _onchange_partner_id_update_commissions(self):
        """
        Al cambiar el cliente, re-evaluar todas las líneas para actualizar agentes.
        """
        if not self.partner_id:
            return

        Commission = self.env["commission.first.sale"]
        # Buscar empleado del usuario actual por si hay que resetear
        current_employee = self.env["hr.employee"].search(
            [("user_id", "=", self.env.user.id)], limit=1
        )

        for line in self.order_line:
            if not line.product_id:
                continue

            existing_agent = Commission.get_agent_for_product(
                self.partner_id.id, line.product_id.id
            )

            if existing_agent:
                line.agent_id = existing_agent
            else:
                # Si no existe vínculo con el nuevo cliente, asignar el agente por defecto (empleado actual)
                # O mantener el que estaba si no estaba bloqueado?
                # Mejor comportamiento: resetear para evitar datos del cliente anterior.
                line.agent_id = current_employee

            # Forzar recomputo de bloqueo
            line._compute_is_commission_locked()
