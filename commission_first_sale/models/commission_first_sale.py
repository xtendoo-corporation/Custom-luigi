import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class CommissionFirstSale(models.Model):
    """
    Modelo para almacenar vínculos permanentes de primera venta.

    Vincula un cliente (partner_id) con un producto (product_id) a un agente (agent_id).
    Este vínculo es permanente: una vez creado, todas las futuras ventas de ese
    producto a ese cliente asignarán la comisión al agente original.
    """

    _name = "commission.first.sale"
    _description = "Vínculo de Primera Venta"
    _rec_name = "display_name"
    _order = "first_sale_date desc"

    partner_id = fields.Many2one(
        "res.partner",
        string="Cliente",
        required=True,
        index=True,
        ondelete="cascade",
        help="Cliente al que se vendió el producto por primera vez",
    )
    product_id = fields.Many2one(
        "product.product",
        string="Producto",
        required=True,
        index=True,
        ondelete="cascade",
        help="Producto vendido",
    )
    agent_id = fields.Many2one(
        "res.users",
        string="Agente",
        required=True,
        index=True,
        ondelete="restrict",
        help="Vendedor dueño de la comisión para este producto-cliente",
    )
    first_sale_date = fields.Datetime(
        string="Fecha de Primera Venta",
        readonly=True,
        default=fields.Datetime.now,
        help="Fecha en que se registró la primera venta",
    )
    origin = fields.Char(
        string="Origen",
        readonly=True,
        help="Referencia al pedido original que creó este vínculo",
    )
    source = fields.Selection(
        [
            ("sale", "Venta"),
            ("pos", "Punto de Venta"),
            ("manual", "Manual"),
        ],
        string="Fuente",
        default="manual",
        readonly=True,
    )

    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        default=lambda self: self.env.company,
        required=True,
    )

    display_name = fields.Char(
        string="Nombre", compute="_compute_display_name", store=True
    )

    _sql_constraints = [
        (
            "unique_partner_product_company",
            "unique(partner_id, product_id, company_id)",
            "Ya existe un vínculo de primera venta para este cliente y producto en esta compañía.",
        )
    ]

    @api.depends("partner_id", "product_id", "agent_id")
    def _compute_display_name(self):
        for record in self:
            partner_name = record.partner_id.name or ""
            product_name = record.product_id.display_name or ""
            agent_name = record.agent_id.name or ""
            record.display_name = f"{partner_name} - {product_name} → {agent_name}"

    @api.model
    def get_or_create_commission(
        self, partner_id, product_id, agent_id, origin=None, source="manual"
    ):
        """
        Busca un vínculo existente o crea uno nuevo.

        Si ya existe un vínculo para partner+product, devuelve el agente existente.
        Si no existe, crea uno nuevo con el agente proporcionado.

        Args:
            partner_id: ID del cliente
            product_id: ID del producto
            agent_id: ID del agente a asignar si no existe vínculo
            origin: Referencia del documento origen
            source: Fuente del vínculo ('sale', 'pos', 'manual')

        Returns:
            tuple: (commission_record, is_new) donde is_new indica si se creó nuevo
        """
        if not partner_id or not product_id:
            return False, False

        domain = [
            ("partner_id", "=", partner_id),
            ("product_id", "=", product_id),
            ("company_id", "=", self.env.company.id),
        ]

        existing = self.search(domain, limit=1)

        if existing:
            _logger.info(
                "Vínculo existente encontrado: %s → Agente: %s",
                existing.display_name,
                existing.agent_id.name,
            )
            return existing, False

        # Crear nuevo vínculo
        if not agent_id:
            return False, False

        new_commission = self.create(
            {
                "partner_id": partner_id,
                "product_id": product_id,
                "agent_id": agent_id,
                "origin": origin,
                "source": source,
            }
        )

        _logger.info(
            "Nuevo vínculo de primera venta creado: %s", new_commission.display_name
        )

        return new_commission, True

    @api.model
    def get_agent_for_product(self, partner_id, product_id):
        """
        Obtiene el agente asignado para un par cliente-producto.

        Args:
            partner_id: ID del cliente
            product_id: ID del producto

        Returns:
            res.users record o False
        """
        if not partner_id or not product_id:
            return False

        domain = [
            ("partner_id", "=", partner_id),
            ("product_id", "=", product_id),
            ("company_id", "=", self.env.company.id),
        ]

        existing = self.search(domain, limit=1)
        return existing.agent_id if existing else False
