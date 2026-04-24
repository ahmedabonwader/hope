from odoo import fields, models, _, api
import io
import base64
import xlsxwriter

class BudgetReportWizard(models.TransientModel):
    _name = 'budget.report.wizard'
    _description = "Budget Report Wizard"

    budget_id = fields.Many2one('crossovered.budget', string="Budget")
    quarter_ids = fields.Many2many('crossovered.budget.lines', string="quarter",
                                 domain="[('crossovered_budget_id' ,'=',budget_id)]")
    budget_state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('validate', 'Validated'),
        ('done', 'Done'),
    ], string="Budget State", default="validate")
    date_from = fields.Date(string="Date From")
    date_to = fields.Date(string="Date To")

    signature_prepared = fields.Many2one('res.users', string="Prepared By")
    signature_reviewed = fields.Many2one('res.users', string="Reviewed By")
    signature_approved = fields.Many2one('res.users', string="Approved By")
    is_donor = fields.Boolean(compute='_compute_is_donor', default=lambda self: self.env.user.has_group('om_account_budget_iteme.group_accounting_doner'))
    file_name = fields.Char(string="File Name", readonly=True)
    file_data = fields.Binary(string="File", readonly=True)

    @api.depends('budget_id') # أو أي حقل يخلي الدالة تشتغل
    def _compute_is_donor(self):
        for rec in self:
            # التحقق إذا كان المستخدم ينتمي لمجموعة المانح
            rec.is_donor = self.env.user.has_group('om_account_budget_iteme.group_accounting_doner')


    def get_paid_invoices(self):
        # الشروط الأساسية للفواتير المرحلة والمدفوعة
        domain = [
            ('payment_state', '=', 'paid'),
            ('move_type', 'in', ['in_invoice', 'in_refund']), 
            ('state', '=', 'posted')
        ]

        # الفلترة حسب المشروع المرتبط بالموازنة
        if self.budget_id and self.budget_id.project_id:
            domain.append(('project_id', '=', self.budget_id.project_id.id))

        # الفلترة حسب تاريخ البداية (إذا تم تحديده)
        if self.date_from:
            domain.append(('invoice_date', '>=', self.date_from))

        # الفلترة حسب تاريخ النهاية (إذا تم تحديده)
        if self.date_to:
            domain.append(('invoice_date', '<=', self.date_to))

        return self.env['account.move'].search(domain, order='invoice_date asc, name asc')

    def get_previous_spending(self, quarter):
        """حساب إجمالي المصروفات قبل تاريخ date_from لنفس الربع"""
        if not self.date_from:
            return 0.0
            
        domain = [
            ('payment_state', '=', 'paid'),
            ('move_type', 'in', ['in_invoice', 'in_refund']),
            ('state', '=', 'posted'),
            ('invoice_date', '<', self.date_from) # جلب ما قبل التاريخ المحدد فقط
        ]
        
        if self.budget_id:
            domain.append(('project_id', '=', self.budget_id.project_id.id))
            
        invoices = self.env['account.move'].search(domain)
        prev_total = 0.0
        
        for inv in invoices:
            # نفلتر الأسطر التي تنتمي لهذا الربع (Quarter) فقط
            lines = inv.invoice_line_ids.filtered(lambda l: l.quarter_id == quarter)
            for line in lines:
                if inv.move_type == 'in_invoice':
                    prev_total += line.price_subtotal
                else: # in_refund
                    prev_total -= line.price_subtotal
        return prev_total

    def action_print_report(self):
        invoices = self.get_paid_invoices()

        data = {
            'invoice_ids': invoices.ids,
            'date_from': self.date_from,
            'date_to': self.date_to,
            # 'quarter': self.quarter_id.id,
            'budget_id': self.budget_id.id,
            'quarter_ids': self.quarter_ids.ids,
            'project_id': self.budget_id.project_id,
            'signature_prepared': self.signature_prepared.id,
            'signature_reviewed': self.signature_reviewed.id,
            'signature_approved': self.signature_approved.id,
        }
        return self.env.ref('budget_report.report_budget').report_action(self, data=data)

    def action_generate_xlsx_report(self):
        def write_signature(sheet, row, title, user, date_format):
            """Helper to write signature blocks."""
            sheet.merge_range(f'A{row}:C{row+2}', title, bold_font)
            sheet.merge_range(f'D{row}:F{row+2}', user.name or '', bold_font)
            sig_data = user.digital_signature
            if sig_data:
                try:
                    if not isinstance(sig_data, bytes):
                        sig_data = sig_data.encode('utf-8')
                    sig_bytes = base64.b64decode(sig_data)
                    sheet.merge_range(f'G{row}:I{row+2}', '')
                    sheet.insert_image(f'G{row}', 'signature.png', {
                        'image_data': io.BytesIO(sig_bytes),
                        'x_scale': 0.23,
                        'y_scale': 0.18,
                        'positioning': 1
                    })
                except Exception:
                    sheet.write(f'G{row}', 'Invalid Signature')
            else:
                sheet.write(f'G{row}', 'No Signature')
            sheet.merge_range(f'J{row}:K{row+2}', fields.Date.today(), date_format)

        for record in self:
            budget = record.budget_id
            budget_quarters = record.quarter_ids

            # 1. جلب الفواتير ضمن الفترة المحددة فقط
            paid_invoices = record.get_paid_invoices()

            # 2. جلب كافة الفواتير السابقة (قبل date_from) لحساب الرصيد الافتتاحي
            previous_invoices_domain = [
                ('payment_state', '=', 'paid'),
                ('move_type', 'in', ['in_invoice', 'in_refund']),
                ('state', '=', 'posted'),
                ('invoice_date', '<', record.date_from)
            ] if record.date_from else []
            
            if previous_invoices_domain and budget.project_id:
                previous_invoices_domain.append(('project_id', '=', budget.project_id.id))
            
            previous_invoices = self.env['account.move'].search(previous_invoices_domain) if previous_invoices_domain else self.env['account.move']

            # تجميع أسطر الفواتير الحالية حسب الربع
            quarter_invoice_lines = {q: [] for q in budget_quarters}
            for inv in paid_invoices:
                for line in inv.invoice_line_ids:
                    if line.quarter_id in quarter_invoice_lines:
                        quarter_invoice_lines[line.quarter_id].append((inv, line))

            # تحضير ملف XLSX
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            sheet = workbook.add_worksheet('Transaction list')

            # Column widths & Formats
            col_widths = [5, 15, 20, 30, 12, 15, 12, 8, 15, 15, 15]
            for i, w in enumerate(col_widths): sheet.set_column(i, i, w)
            bold_font = workbook.add_format({'bold': True, 'align': 'center'})
            bold_date_font = workbook.add_format({'bold': True, 'align': 'center', 'num_format': 'dd/mm/yyyy'})
            border = workbook.add_format({'border': 1, 'align': 'center', 'num_format': '#,##0.00'})
            border_align_left = workbook.add_format({'border': 1, 'align': 'left'})
            border_date_format = workbook.add_format({'border': 1, 'num_format': 'dd/mm/yyyy'})
            merge_bold_font = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter', 'num_format': '#,##0.00'})

            # Header
            sheet.merge_range('C1:I1', f'Project Title: {budget.project_id.name}', merge_bold_font)
            sheet.merge_range('C2:I2', f'Donor: {budget.project_id.partner_id.name}', merge_bold_font)
            sheet.merge_range('C3:I3', f'Period: From: {record.date_from} To: {record.date_to}', merge_bold_font)

            headers = ['NO#', 'Budget Code', 'Payment Name', 'Transaction Details', 'Bill Date', 'Bill Reference', 'Bank Reference', f'Amount in {budget.project_id.curr_id.name}', 'Rate', 'Amount in SDG (Credit)', 'Amount in SDG (Debit)', 'Balance In SDG']
            current_row = 4
            sheet.write_row(current_row, 0, headers, merge_bold_font)
            current_row += 1

            for quarter in budget_quarters:
                # --- حساب الرصيد التراكمي السابق لهذا الربع ---
                previous_spent_sdg = 0.0
                for inv in previous_invoices:
                    lines = inv.invoice_line_ids.filtered(lambda l: l.quarter_id == quarter)
                    for line in lines:
                        if inv.move_type == 'in_invoice': previous_spent_sdg += line.price_subtotal
                        else: previous_spent_sdg -= line.price_subtotal
                
                planned_currency = quarter.get_foreign_exchange(price=quarter.planned_amount, rate=quarter.rate)
                # الرصيد يبدأ من (المخطط - المصروف سابقاً)
                balance_sdg = planned_currency - previous_spent_sdg
                
                sheet.merge_range(f'A{current_row+1}:F{current_row+1}', f"{quarter.quarter} (Opening Bal: {balance_sdg:,.2f})", merge_bold_font)
                sheet.write(current_row, 7, quarter.planned_amount, border)
                sheet.write(current_row, 8, quarter.rate, border)
                sheet.write(current_row, 9, planned_currency, border)
                sheet.write(current_row, 10, previous_spent_sdg, border) # وضعنا المصروف السابق هنا للتوضيح
                sheet.write(current_row, 11, balance_sdg, border)
                current_row += 1

                line_no, total_currency, total_sdg = 0, 0, 0
                for inv, line in quarter_invoice_lines[quarter]:
                    line_no += 1
                    amount_currency = inv.get_foreign_exchange(price=line.price_subtotal, rate=inv.rate)
                    sheet.write(current_row, 0, line_no, border)
                    sheet.write(current_row, 1, line.budget_item_line_id.line_code, border)
                    sheet.write(current_row, 2, inv.partner_id.name, border_align_left)
                    sheet.write(current_row, 3, line.name, border_align_left)
                    sheet.write(current_row, 4, inv.invoice_date, border_date_format)
                    sheet.write(current_row, 5, inv.name, border_align_left)
                    sheet.write(current_row, 6, inv.bank_transfer_ref, border_align_left)
                    sheet.write(current_row, 7, amount_currency, border)
                    sheet.write(current_row, 8, inv.rate, border)
                    
                    if inv.move_type == 'in_refund':
                        sheet.write(current_row, 9, round(line.price_subtotal,2), border)
                        balance_sdg += line.price_subtotal
                        total_currency -= amount_currency
                        total_sdg -= line.price_subtotal
                    else: sheet.write(current_row, 9, '', border)

                    if inv.move_type == 'in_invoice':
                        sheet.write(current_row, 10, round(line.price_subtotal,3), border)
                        balance_sdg -= line.price_subtotal
                        total_currency += amount_currency
                        total_sdg += line.price_subtotal
                    else: sheet.write(current_row, 10, '', border)
                    
                    sheet.write(current_row, 11, balance_sdg, border)
                    current_row += 1

                # Totals
                sheet.merge_range(f'A{current_row+1}:F{current_row+1}', 'Total', merge_bold_font)
                sheet.write(current_row, 7, total_currency, merge_bold_font)
                sheet.write(current_row, 8, '', merge_bold_font); sheet.write(current_row, 9, '', merge_bold_font)
                sheet.write(current_row, 10, total_sdg, merge_bold_font)
                sheet.write(current_row, 11, balance_sdg, merge_bold_font)
                current_row += 4

                # Remaining
                sheet.merge_range(f'A{current_row+1}:F{current_row+1}', 'Remaining', merge_bold_font)
                sheet.write(current_row, 7, (quarter.planned_amount - total_currency), merge_bold_font)
                sheet.write(current_row, 8, quarter.rate, merge_bold_font)
                sheet.write(current_row, 9, '', merge_bold_font); sheet.write(current_row, 10, '', merge_bold_font)
                sheet.write(current_row, 11, balance_sdg, merge_bold_font)
                current_row += 4

                # Quarter Details Summary
                sheet.merge_range(f'A{current_row}:B{current_row}', 'Quarter', merge_bold_font)
                sheet.merge_range(f'C{current_row}:D{current_row}', f'Amount in {budget.project_id.curr_id.name}', merge_bold_font)
                sheet.merge_range(f'E{current_row}:F{current_row}', 'Rate', merge_bold_font)
                sheet.merge_range(f'G{current_row}:H{current_row}', 'Amount in SDG', merge_bold_font)
                current_row += 1
                sheet.merge_range(f'A{current_row}:B{current_row}', quarter.quarter, border)
                sheet.merge_range(f'C{current_row}:D{current_row}', quarter.planned_amount, border)
                sheet.merge_range(f'E{current_row}:F{current_row}', quarter.rate, border)
                sheet.merge_range(f'G{current_row}:H{current_row}', quarter.get_foreign_exchange(price=quarter.planned_amount, rate=quarter.rate), border)
            
            # Signature section
            current_row += 2
            sheet.merge_range(f'A{current_row}:C{current_row}', 'Position',bold_font)
            sheet.merge_range(f'D{current_row}:F{current_row}', 'Name',bold_font)
            sheet.merge_range(f'G{current_row}:I{current_row}', 'Signature',bold_font)
            sheet.merge_range(f'J{current_row}:K{current_row}', 'Date',bold_font)
            current_row += 1
            write_signature(sheet, current_row, 'Prepared by', record.signature_prepared, bold_date_font)
            current_row += 3
            write_signature(sheet, current_row, 'Reviewed by', record.signature_reviewed, bold_date_font)
            current_row += 3
            write_signature(sheet, current_row, 'Approved by', record.signature_approved, bold_date_font)

            workbook.close()
            output.seek(0)
            self.file_name = 'budget_report.xlsx'
            self.file_data = base64.b64encode(output.read())
            output.close()

            return {
                'type': 'ir.actions.act_window',
                'res_model': 'budget.report.wizard',
                'view_mode': 'form',
                'res_id': self.id,
                'target': 'new',
            }

    class AccountBudgetReportPDF(models.AbstractModel):
        _name = 'report.budget_report.create_report_view'

        def _get_report_values(self, docids, data=None):
            budget = self.env['crossovered.budget'].browse(data['budget_id'])

            budget_quarter_ids = self.env['crossovered.budget.lines'].browse(data['quarter_ids'])
            docs = self.env['account.move'].browse(data['invoice_ids'])
            quarter_data = []
            quarter_details = False
            
            for quarter in budget_quarter_ids:
                quarter_details = self.env['budget.quarte'].search([('budget_line_id','=',quarter.id)],limit=1)
                found = False
                bills_data = []
                for account_move in docs:
                    invoice_lines = account_move.invoice_line_ids.filtered(lambda line: line.quarter_id == quarter)
                    for line in invoice_lines:
                        bills_line = {
                            'budget_item_line_id': line.budget_item_line_id.line_code,
                            'partner_name': account_move.partner_id.name,
                            'line_name': line.name,
                            'invoice_date': account_move.invoice_date,
                            'invoice_name': account_move.name,
                            'amount_usd': account_move.get_foreign_exchange(price=line.price_subtotal, rate=account_move.rate),
                            'rate': account_move.rate,
                            'price_subtotal': line.price_subtotal,
                        }
                        bills_data.append(bills_line)
                        found = True
                if found:
                    quarter_data.append(
                        
                        {
                            'quarter':quarter,
                            # 'rate':budget.get_foreign_exchange(price=quarter.planned_amount, rate=quarter.rate)
                            'bills':bills_data,
                           
                        }
                    )
            
            prepared = self.env['res.users'].browse(data['signature_prepared'])
            revision_review = self.env['res.users'].browse(data['signature_reviewed'])
            revision_approve = self.env['res.users'].browse(data['signature_approved'])
            return {
                'doc_ids': docs.ids,
                'doc_model': 'account.move',
                # 'budget': budget,
                'budgets': budget_quarter_ids,
                'docs': docs,
                'quarter_data':quarter_data,
                'bills_data':bills_data,
                'project_name': budget.project_id.name,
                'donor': budget.project_id.partner_id.name,
                'date_from': data['date_from'],
                'date_to': data['date_to'],
                'prepared': prepared.name,
                'prepared_signature': prepared.digital_signature.decode() if prepared.digital_signature else False,
                'prepared_date':fields.Date.today(), 
                'revision_review': revision_review.name,
                'revision_review_signature': revision_review.digital_signature.decode() if revision_review.digital_signature else False,    
                'revision_review_date':fields.Date.today(),
                'revision_approve': revision_approve.name,
                'revision_approve_signature': revision_approve.digital_signature.decode() if revision_approve.digital_signature else False, 
                'revision_approve_date':fields.Date.today(),
            }
