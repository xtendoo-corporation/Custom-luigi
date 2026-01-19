from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    commission_first_sale_count = fields.Integer(
        string="Comisiones", compute="_compute_commission_first_sale_count"
    )

    def _compute_commission_first_sale_count(self):
        Commission = self.env["commission.first.sale"]
        # Optimización: hacerlo en batch si es posible, pero con search_count es simple
        for employee in self:
            employee.commission_first_sale_count = Commission.search_count(
                [("agent_id", "=", employee.id)]
            )

    def action_view_first_sale_commissions(self):
        self.ensure_one()
        return {
            "name": "Comisiones Primera Venta",
            "type": "ir.actions.act_window",
            "res_model": "commission.first.sale",
            "view_mode": "list,form",
            "domain": [("agent_id", "=", self.id)],
            "context": {"default_agent_id": self.id},
        }
