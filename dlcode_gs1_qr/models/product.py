import base64
import logging

import requests

from odoo import _, fields, models
from odoo.exceptions import UserError

from .gtin import valid_gtin

_logger = logging.getLogger(__name__)

API = "https://dlcode.org/api/v1"
TIMEOUT = 20


class ProductProduct(models.Model):
    _inherit = "product.product"

    dlcode_code_url = fields.Char(string="DLCode link", readonly=True, copy=False)
    dlcode_qr_svg = fields.Binary(string="DLCode QR label", readonly=True, copy=False, attachment=False)
    dlcode_synced_at = fields.Datetime(string="Last DLCode sync", readonly=True, copy=False)

    def write(self, vals):
        res = super().write(vals)
        if "barcode" in vals and self.env["ir.config_parameter"].sudo().get_param("dlcode_gs1_qr.auto_sync"):
            products = self.filtered(lambda p: valid_gtin(p.barcode))
            try:
                session = products._dlcode_session() if products else None
            except UserError as e:
                _logger.warning("DLCode auto-sync skipped: %s", e)
                products = self.browse()
            for product in products:
                try:
                    product._dlcode_sync(session)
                except (UserError, ValueError, KeyError) as e:
                    _logger.warning("DLCode sync failed for %s: %s", product.display_name, e)
        return res

    def _dlcode_session(self):
        key = self.env["ir.config_parameter"].sudo().get_param("dlcode_gs1_qr.api_key")
        if not key:
            raise UserError(_("Add your DLCode API key in Settings first."))
        session = requests.Session()
        session.headers["Authorization"] = "Bearer %s" % key.strip()
        return session

    def _dlcode_url(self):
        self.ensure_one()
        if "website_url" not in self._fields or not self.is_published:
            return None
        return self.get_base_url() + self.website_url

    def _dlcode_call(self, session, method, url, payload=None):
        try:
            res = session.request(method, url, json=payload, timeout=TIMEOUT)
        except requests.RequestException as e:
            raise UserError(_("Could not reach DLCode: %s", e)) from e
        if res.status_code >= 400:
            try:
                message = res.json().get("error") or res.reason
            except ValueError:
                message = res.reason
            raise (_Conflict if res.status_code == 409 else UserError)(message)
        return res

    def _dlcode_sync(self, session):
        self.ensure_one()
        gtin = valid_gtin(self.barcode)
        if not gtin:
            raise UserError(_("%s has no valid GTIN barcode.", self.display_name))
        payload = {"gtin": gtin, "name": self.with_context(display_default_code=False).display_name[:200]}
        url = self._dlcode_url()
        if url:
            payload["url"] = url
        try:
            data = self._dlcode_call(session, "POST", API + "/products", payload).json()
        except _Conflict as conflict:
            payload.pop("gtin")
            try:
                data = self._dlcode_call(session, "PATCH", "%s/products/%s" % (API, gtin), payload).json()
            except UserError:
                raise UserError(str(conflict)) from None
        svg = self._dlcode_call(session, "GET", "%s/products/%s/label.svg" % (API, gtin))
        self.write({
            "dlcode_code_url": data["codeUrl"],
            "dlcode_qr_svg": base64.b64encode(svg.content),
            "dlcode_synced_at": fields.Datetime.now(),
        })

    def action_dlcode_sync(self):
        session = self._dlcode_session()
        done, skipped, failed = 0, 0, []
        for product in self:
            if not valid_gtin(product.barcode):
                skipped += 1
                continue
            try:
                product._dlcode_sync(session)
                done += 1
            except (UserError, ValueError, KeyError) as e:
                failed.append("%s: %s" % (product.display_name, e))
        message = _("%(done)s synced, %(skipped)s skipped (no valid GTIN barcode).", done=done, skipped=skipped)
        if failed:
            message += "\n" + "\n".join(failed[:10])
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("DLCode"),
                "message": message,
                "type": "warning" if failed or not done else "success",
                "sticky": bool(failed),
                "next": {"type": "ir.actions.client", "tag": "soft_reload"},
            },
        }


class _Conflict(UserError):
    pass


class ProductTemplate(models.Model):
    _inherit = "product.template"

    dlcode_code_url = fields.Char(related="product_variant_id.dlcode_code_url")
    dlcode_qr_svg = fields.Binary(related="product_variant_id.dlcode_qr_svg")
    dlcode_synced_at = fields.Datetime(related="product_variant_id.dlcode_synced_at")

    def action_dlcode_sync(self):
        return self.product_variant_ids.action_dlcode_sync()
