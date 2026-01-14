# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    commission_agent_id = fields.Many2one('res.users', string='Commission agent', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        lines = super(SaleOrderLine, self).create(vals_list)
        commission_model = self.env['commission.product.link']
        for line in lines:
            # only if partner and product set
            partner = line.order_id.partner_id
            product = line.product_id
            if partner and product:
                seller = line.order_id.user_id or self.env.user
                owner = commission_model.get_or_create_owner(partner, product, seller)
                line.commission_agent_id = owner
        return lines

    def write(self, vals):
        # if product/partner changes, ensure commission assigned
        res = super(SaleOrderLine, self).write(vals)
        commission_model = self.env['commission.product.link']
        for line in self:
            partner = line.order_id.partner_id
            product = line.product_id
            if partner and product and not line.commission_agent_id:
                seller = line.order_id.user_id or self.env.user
                owner = commission_model.get_or_create_owner(partner, product, seller)
                line.commission_agent_id = owner
        return res
