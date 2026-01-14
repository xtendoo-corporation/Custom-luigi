# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CommissionProductLink(models.Model):
    _name = 'commission.product.link'
    _description = 'Commission by first sale: product - partner - user'

    partner_id = fields.Many2one('res.partner', string='Partner', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='Owner (agent)', ondelete='set null')
    date_first_sale = fields.Datetime(string='Date first sale', default=fields.Datetime.now)

    _sql_constraints = [
        ('partner_product_unique', 'unique(partner_id, product_id)', 'There is already a commission owner for this product and partner.')
    ]

    @api.model
    def get_or_create_owner(self, partner, product, user):
        """Return the owner user for given partner+product. If not exists, create it with provided user."""
        # operate with sudo to ensure creation when called from various users
        link = self.sudo().search([('partner_id', '=', partner.id), ('product_id', '=', product.id)], limit=1)
        if link:
            return link.user_id
        # create
        try:
            link = self.sudo().create({
                'partner_id': partner.id,
                'product_id': product.id,
                'user_id': user.id,
            })
        except Exception:
            # in concurrent case another process could have created it
            link = self.sudo().search([('partner_id', '=', partner.id), ('product_id', '=', product.id)], limit=1)
        return link.user_id
