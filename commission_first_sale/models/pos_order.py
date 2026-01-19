import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class PosOrderLine(models.Model):
    """
    Herencia de línea de pedido POS para añadir campo de agente de comisión.
    """

    _inherit = "pos.order.line"

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

        for line in self.lines:
            if not line.product_id:
                continue

            existing_agent = Commission.get_agent_for_product(
                self.partner_id.id, line.product_id.id
            )

            if existing_agent:
                line.agent_id = existing_agent
            else:
                line.agent_id = current_employee

            # Forzar recomputo de bloqueo
            line._compute_is_commission_locked()

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

        # Buscar el empleado asociado al cajero/usuario
        current_employee = False
        if self.user_id:
            current_employee = self.env["hr.employee"].search(
                [("user_id", "=", self.user_id.id)], limit=1
            )

        for line in self.lines:
            if not line.product_id:
                continue

            # Buscar o crear vínculo
            agent_to_use = line.agent_id or current_employee

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
