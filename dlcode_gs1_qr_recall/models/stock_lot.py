from urllib.parse import quote

from odoo import _, fields, models
from odoo.exceptions import UserError

from odoo.addons.dlcode_gs1_qr.models.gtin import valid_gtin
from odoo.addons.dlcode_gs1_qr.models.product import API


class StockLot(models.Model):
    _inherit = "stock.lot"

    dlcode_recalled = fields.Boolean(string="Recalled", copy=False, tracking=True,
                                     help="Shoppers who scan this lot's DLCode QR code see the recall note.")
    dlcode_recall_note = fields.Char(string="Note for shoppers", copy=False,
                                     help="For example: Do not eat. Return it to the store for a full refund.")

    def write(self, vals):
        res = super().write(vals)
        if "dlcode_recalled" in vals or "dlcode_recall_note" in vals:
            # A failed call raises, so Odoo rolls back the save and the box stays in sync with DLCode.
            for lot in self.filtered(lambda l: "dlcode_recalled" in vals or l.dlcode_recalled):
                lot._dlcode_push_recall()
        return res

    def _dlcode_push_recall(self):
        self.ensure_one()
        product = self.product_id
        gtin = valid_gtin(product.barcode)
        if not gtin:
            raise UserError(_("%s has no valid GTIN barcode, so DLCode cannot find it.", product.display_name))
        payload = {"recalled": self.dlcode_recalled}
        if self.dlcode_recall_note:
            payload["note"] = self.dlcode_recall_note
        url = "%s/products/%s/lots/%s/recall" % (API, gtin, quote(self.name, safe=""))
        product._dlcode_call(product._dlcode_session(), "PUT", url, payload)
