# Copyright (C) 2019 Brian McMaster
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    fsm_recurring_id = fields.Many2one(
        "fsm.recurring",
        "Recurring Order",
        index=True,
        copy=False,
        help="Field Service Recurring Order generated by the sale order line",
    )

    def _field_create_fsm_recurring_prepare_values(self):
        self.ensure_one()
        template = self.product_id.fsm_recurring_template_id
        product = self.product_id
        note = self.name
        if template.description:
            note += "\n " + template.description
        return {
            "location_id": self.order_id.fsm_location_id.id,
            "start_date": self.order_id.expected_date,
            "fsm_recurring_template_id": template.id,
            "description": note,
            "max_orders": template.max_orders,
            "fsm_frequency_set_id": template.fsm_frequency_set_id.id,
            "fsm_order_template_id": product.fsm_order_template_id.id
            or template.fsm_order_template_id.id,
            "sale_line_id": self.id,
            "company_id": self.company_id.id,
        }

    def _field_create_fsm_recurring(self):
        """Generate fsm_recurring for the given so line, and link it.
        :return a mapping with the so line id and its linked fsm_recurring
        :rtype dict
        """
        result = {}
        for so_line in self:
            # create fsm_recurring
            values = so_line._field_create_fsm_recurring_prepare_values()
            fsm_recurring = self.env["fsm.recurring"].sudo().create(values)
            so_line.write({"fsm_recurring_id": fsm_recurring.id})

            product_name = so_line.product_id.name

            # post message on SO
            msg_body = (
                _("Field Service recurring Created ({product_name}): ").format(
                    product_name=product_name
                )
                + fsm_recurring._get_html_link()
            )
            so_line.order_id.message_post(body=msg_body)

            # post message on fsm_recurring
            fsm_recurring_msg = (
                _("This recurring has been created ({product_name}) from: ").format(
                    product_name=product_name
                )
                + so_line.order_id._get_html_link()
            )
            fsm_recurring.message_post(body=fsm_recurring_msg)

            result[so_line.id] = fsm_recurring
        return result

    def _get_invoiceable_fsm_order_domain(self):
        """
        add  fsm_recurring_id to domain
        :return:
        """
        dom = super()._get_invoiceable_fsm_order_domain()
        if self.fsm_recurring_id:
            dom.append(("fsm_recurring_id", "=", self.fsm_recurring_id.id))
        return dom

    def _prepare_invoice_line(self, **optional_values):
        res = super()._prepare_invoice_line(**optional_values)
        if self.fsm_recurring_id:
            fsm_orders = self._get_invoiceable_fsm_order()
            if fsm_orders:
                res.update({"fsm_order_ids": [(6, 0, fsm_orders.ids)]})
        return res
