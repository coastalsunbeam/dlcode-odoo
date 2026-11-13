from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    dlcode_api_key = fields.Char(
        string="DLCode API key",
        config_parameter="dlcode_gs1_qr.api_key",
        groups="base.group_system",
    )
    dlcode_auto_sync = fields.Boolean(
        string="Sync when a barcode changes",
        config_parameter="dlcode_gs1_qr.auto_sync",
        groups="base.group_system",
    )
