# my_module/wizards/import_wizard.py
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class LinnworksImportWizard(models.TransientModel):
    _name = 'linnworks.import.wizard'
    _description = 'Linnworks Import Wizard'

    import_type = fields.Selection(
        selection='get_import_types',
        string='Import Type',
        # required=True
    )
    product_import_qty = fields.Integer(required=True)


    def get_import_types(self):
        # Initial options can be empty or predefined
        return self._get_base_import_types()


    @api.model
    def _get_base_import_types(self):
        additional_types = [
            ('import_product', 'Import Product'),
        ]
        return additional_types

    def action_import(self):
        if self.import_type == 'import_product':
            integration_model = self.env['linnworks.integration'].search([], limit=1)
            if not integration_model:
                raise UserError(_("No Linnworks integration record found."))
                # if self.product_import_qty < 0:
                # print("\n\n\n=================mishan sharma")
                integration_model.product_import_qty = self.product_import_qty
            return integration_model.import_products()
        return super().action_import()




