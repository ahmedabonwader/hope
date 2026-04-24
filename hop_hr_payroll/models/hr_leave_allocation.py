from odoo import models, fields, api, _

class HrLeaveAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    allocation_mode = fields.Selection([
        ('employee', 'By Employee'),
        ('company', 'By Company'),
        ('department', 'By Department'),
        ('category', 'By Employee Tag')
    ], string='Allocation Mode', readonly=False, required=True, default='employee')

    # حقول إضافية لتحديد الوجهة بناءً على الوضع المختار
    mode_company_id = fields.Many2one('res.company', string='Company')
    mode_department_id = fields.Many2one('hr.department', string='Department')
    category_id = fields.Many2one('hr.employee.category', string='Employee Tag')

    @api.model_create_multi
    def create(self, vals_list):
        """
        وراثة دالة الإنشاء: إذا تم اختيار وضع غير 'employee'، 
        نقوم بإنشاء سجلات منفصلة لكل موظف ينتمي للشركة أو القسم المختار.
        """
        new_vals_list = []
        for vals in vals_list:
            mode = vals.get('allocation_mode', 'employee')
            if mode == 'employee':
                new_vals_list.append(vals)
                continue

            # تحديد الموظفين بناءً على الوضع
            employees = self.env['hr.employee']
            if mode == 'company':
                employees = employees.search([('company_id', '=', vals.get('mode_company_id'))])
            elif mode == 'department':
                employees = employees.search([('department_id', '=', vals.get('mode_department_id'))])
            elif mode == 'category':
                employees = employees.search([('category_ids', 'in', [vals.get('category_id')])])

            # إنشاء نسخة من البيانات لكل موظف
            for emp in employees:
                new_vals = vals.copy()
                new_vals.update({
                    'employee_id': emp.id,
                    'allocation_mode': 'employee', # تحويله لفردي عند الإنشاء الفعلي
                })
                new_vals_list.append(new_vals)
        
        return super(HrLeaveAllocation, self).create(new_vals_list)