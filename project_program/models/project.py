from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class Project(models.Model):
    _inherit = 'project.project'

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('cancel', 'Cancelled'),
        ('validate', 'Validated'),
        ('running', 'Running'),
        ('done', 'Done')
    ], 'Status', default='draft')

    total_expected_budget = fields.Float(
        string='Total Expected Budget',
        tracking=True,
        help='Total expected budget for this project'
    ) 
    curr_id = fields.Many2one('res.currency', string="Currency", default=lambda self: self.env['res.currency'].search([('name', '=', 'USD')], limit=1), readonly=False)
    followup_template_id = fields.Many2one('project.followup.template', string='Followup Template')
    followup_report = fields.Html('Followup Report', sanitize=True)
    project_code = fields.Char(string='Project Code')
    subtasks_expected_budget = fields.Float(
        string='Subtasks Expected Budget',
        compute='_compute_subtasks_expected_budget',
        store=True,
        help='Sum of expected budgets from all tasks and their subtasks'
    )
    staff_line_ids = fields.One2many('project.staff.line', 'project_id', string="Staff Line")

    def action_project_confirm(self):
        for lin in self:
            lin.write({'state': 'confirm'})

    def action_project_validate(self):
        for lin in self:
            if not lin.account_id:
                analytic = self.env['account.analytic.account'].create({'name': self.name,
                                                                        'plan_id': 1})
                if analytic:
                    lin.write({'account_id': analytic.id})
            lin.write({'state': 'validate'})

    def action_project_draft(self):
        for lin in self:
            lin.write({'state': 'draft'})

    def action_project_cancel(self):
        for lin in self:
            lin.write({'state': 'cancel'})

    def unlink(self):
        for line in self:
            if line.state != 'draft':
                raise UserError(_('The project cannot be deleted after confirmation.'))
        return super(Project, self).unlink()

    
    @api.depends('task_ids.expected_budget', 'task_ids.subtask_expected_budget')
    def _compute_subtasks_expected_budget(self):
        for project in self:
            project.subtasks_expected_budget = sum(project.task_ids.mapped('expected_budget')) + \
                                             sum(project.task_ids.mapped('subtask_expected_budget'))

    @api.onchange('followup_template_id')
    def _onchange_followup_template(self):
        if self.followup_template_id:
            self.followup_report = self.followup_template_id.template_content

class ProjectTask(models.Model):
    _inherit = 'project.task'

    expected_budget = fields.Monetary(string='Expected Budget', tracking=True)
    currency_id = fields.Many2one(
        'res.currency', 
        string='Currency',
        related='company_id.currency_id',
        readonly=True
    )

    @api.depends('child_ids.expected_budget')
    def _compute_subtask_expected_budget(self):
        for task in self:
            task.subtask_expected_budget = sum(task.child_ids.mapped('expected_budget'))

    subtask_expected_budget = fields.Monetary(
        string='Subtasks Expected Budget',
        compute='_compute_subtask_expected_budget',
        store=True,
        currency_field='currency_id'
    )

    followup_template_id = fields.Many2one('project.followup.template', string='Followup Template')
    followup_report = fields.Html('Followup Report', sanitize=True)

    @api.onchange('followup_template_id')
    def _onchange_followup_template(self):
        if self.followup_template_id:
            self.followup_report = self.followup_template_id.template_content



class ProjectStaffLine(models.Model):
    _name = 'project.staff.line'
    _description = 'Project Staff Line'

    emp_id = fields.Many2one('hr.employee', string="Employee")
    department = fields.Many2one(related="emp_id.department_id", string="Department")
    note = fields.Text(string="Note")
    project_id = fields.Many2one('project.project', string="Project")
    line_number = fields.Integer(string="NO", compute="_compute_line_number", store=True)

    @api.depends('project_id.staff_line_ids')
    def _compute_line_number(self):
        for rec in self:
            if rec.project_id:
                for index, line in enumerate(rec.project_id.staff_line_ids, start=1):
                    line.line_number = index