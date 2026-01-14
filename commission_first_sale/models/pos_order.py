# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class PosOrder(models.Model):
    _inherit = 'pos.order'

    # no new fields here, logic on creation of backend orders

    @api.model
    def create(self, vals):
        # when pos.order is created in backend, assign commission for each line
        order = super(PosOrder, self).create(vals)
        commission_model = self.env['commission.product.link']
        # determine user who should be owner for new links: prefer user_id on order or create_uid
        order_user = order.user_id or order.create_uid or self.env.user
        # order.lines may be list of tuples until reloaded; ensure recordset
        order_lines = order.lines
        for line in order_lines:
            product = line.product_id
            partner = order.partner_id
            if partner and product:
                owner = commission_model.get_or_create_owner(partner, product, order_user)
                if hasattr(line, 'commission_agent_id'):
                    line.commission_agent_id = owner
        return order


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    commission_agent_id = fields.Many2one('res.users', string='Commission agent', readonly=True)
