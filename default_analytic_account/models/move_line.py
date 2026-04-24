from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    project_id = fields.Many2one(
        'project.project',
        string='Project',
        tracking=True,
        domain="[('state', '=', 'running' )]" )

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.depends('product_id', 'move_id.project_id', 'move_id.partner_id')
    def _compute_analytic_distribution(self):
        """Compute analytic distribution based on project or product's default analytic account."""

        super()._compute_analytic_distribution()
        ProjectProject = self.env['project.project']
        for line in self:
            if line.analytic_distribution:
                continue
            project_id = line._context.get('project_id')
            project = ProjectProject.browse(project_id) if project_id else line.move_id.project_id
            if project:
                line.analytic_distribution = project._get_analytic_distribution()

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to recompute analytic distribution."""
        moves = super().create(vals_list)
        moves._compute_analytic_distribution()
        return moves

