from odoo import api, fields, models, _


class ResPartner(models.Model):
    """
    Herencia de res.partner para añadir acceso a vínculos de primera venta.
    """

    _inherit = "res.partner"

    first_sale_commission_ids = fields.One2many(
        "commission.first.sale",
        "partner_id",
        string="Vínculos de Primera Venta",
        help="Productos para los cuales este cliente tiene un agente de comisión asignado",
    )

    first_sale_commission_count = fields.Integer(
        string="Nº Vínculos de Comisión", compute="_compute_first_sale_commission_count"
    )

    @api.depends("first_sale_commission_ids")
    def _compute_first_sale_commission_count(self):
        """Calcula el número de vínculos de primera venta del cliente."""
        for partner in self:
            partner.first_sale_commission_count = len(partner.first_sale_commission_ids)

    def action_view_first_sale_commissions(self):
        """
        Acción para ver los vínculos de primera venta del cliente.
        Se usa desde el smart button.
        """
        self.ensure_one()
        return {
            "name": _("Vínculos de Primera Venta"),
            "type": "ir.actions.act_window",
            "res_model": "commission.first.sale",
            "view_mode": "list,form",
            "domain": [("partner_id", "=", self.id)],
            "context": {
                "default_partner_id": self.id,
            },
        }
