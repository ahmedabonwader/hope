from odoo import api, fields, models, _
import io
import base64
import xlsxwriter

class CustodyReport(models.TransientModel):
    _name = 'bank.statement.wizard'
    _description = "Bank Statement Wizard"

    account_id = fields.Many2one('account.account', string="Account", required=True)
    journal_ids = fields.Many2many('account.journal', string="Journal")
    project_id = fields.Many2one('project.project', string="Project")
    date_from = fields.Date(string="Date From")
    date_to = fields.Date(string="Date To")
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company.id
    )

    file_name = fields.Char(string="File Name", readonly=True)
    file_data = fields.Binary(string="File", readonly=True)
    
    # def get_project_id_in_journal_entry(self):
    #     vendor_bills = self.env['account.move'].search([
    #         ('move_type', '=', 'in_invoice'),
    #         ('payment_state', '=', 'paid'),
    #         ('project_id', '!=', False)
    #     ])
    #
    #     for bill in vendor_bills:
    #         payments = bill._get_reconciled_payments()
    #         for payment in payments:
    #             if payment.move_id and not payment.move_id.project_id:
    #                 payment.move_id.project_id = bill.project_id.id

    def action_print_excel_report(self):
        for rec in self:
            # Determine the Analytic Account ID linked to the selected Project
            analytic_id_str = False
            if rec.project_id:
                analytic_account = getattr(rec.project_id, 'account_id', False) or getattr(rec.project_id, 'analytic_account_id', False)
                if analytic_account:
                    analytic_id_str = str(analytic_account.id)

            # --------------------------------------------------
            # 1) Calculate Opening Balance
            # --------------------------------------------------
            opening_balance = 0

            if rec.date_from:
                opening_sql = """
                    SELECT
                        COALESCE(SUM(aml.debit), 0) AS debit,
                        COALESCE(SUM(aml.credit), 0) AS credit
                    FROM account_move_line aml
                    JOIN account_move m ON aml.move_id = m.id
                    WHERE aml.account_id = %s
                      AND m.move_type = 'entry'
                      AND m.state = 'posted'
                      AND aml.date < %s
                """
                opening_params = [rec.account_id.id, rec.date_from]

                if analytic_id_str:
                    opening_sql += " AND aml.analytic_distribution ? %s"
                    opening_params.append(analytic_id_str)

                if rec.journal_ids and len(rec.journal_ids) > 0:
                    opening_sql += " AND aml.journal_id IN %s"
                    opening_params.append(tuple(rec.journal_ids.ids))

                self.env.cr.execute(opening_sql, opening_params)
                result = self.env.cr.fetchone()
                if result:
                    opening_balance = (result[0] or 0) - (result[1] or 0)

            running_balance = opening_balance
            ob_debit = opening_balance if opening_balance > 0 else 0.0
            ob_credit = abs(opening_balance) if opening_balance < 0 else 0.0

            # --------------------------------------------------
            # 2) Main SQL for report lines 
            # --------------------------------------------------
            sql = """
                SELECT aml.date,
                       c.name AS company_name,
                       p.name AS partner,
                       COALESCE(aml.ref, aml.name) AS reference,
                       m.name AS transaction_id,
                       
                       -- UPDATED: Using the exact technical name you provided
                       m.bank_transfer_ref AS bank_reference, 
                       
                       aml.debit,
                       aml.credit,
                       aml.name AS label,
                       cur.symbol AS currency_symbol,
                       cur.name   AS currency_name,
                       cur.id     AS currency_id,
                       m.move_type AS move_type,
                       
                       (SELECT name FROM account_analytic_account WHERE id::text = (SELECT k FROM jsonb_object_keys(aml.analytic_distribution) AS k LIMIT 1)) AS project,
                       
                       (
                           SELECT string_agg(DISTINCT inv.name, ', ')
                           FROM account_move_line pay_line
                           LEFT JOIN account_partial_reconcile apr_dr ON apr_dr.credit_move_id = pay_line.id
                           LEFT JOIN account_partial_reconcile apr_cr ON apr_cr.debit_move_id = pay_line.id
                           INNER JOIN account_move_line inv_line ON inv_line.id = COALESCE(apr_dr.debit_move_id, apr_cr.credit_move_id)
                           INNER JOIN account_move inv ON inv.id = inv_line.move_id
                           WHERE pay_line.move_id = m.id
                             AND inv.move_type IN ('out_invoice', 'in_invoice', 'out_refund', 'in_refund', 'out_receipt', 'in_receipt')
                             AND inv.id != m.id
                       ) AS related_invoices
                FROM account_move_line aml
                JOIN account_move m ON aml.move_id = m.id
                LEFT JOIN res_partner p ON aml.partner_id = p.id
                JOIN res_company c ON aml.company_id = c.id
                LEFT JOIN res_currency cur ON aml.currency_id = cur.id
                WHERE aml.account_id = %s
                  AND m.move_type = 'entry'
                  AND m.state = 'posted'
            """

            params = [rec.account_id.id]

            if rec.date_from:
                sql += " AND aml.date >= %s"
                params.append(rec.date_from)

            if rec.date_to:
                sql += " AND aml.date <= %s"
                params.append(rec.date_to)

            if analytic_id_str:
                sql += " AND aml.analytic_distribution ? %s"
                params.append(analytic_id_str)

            if rec.journal_ids and len(rec.journal_ids) > 0:
                sql += " AND aml.journal_id IN %s"
                params.append(tuple(rec.journal_ids.ids))

            sql += " ORDER BY aml.date ASC"

            self.env.cr.execute(sql, params)
            rows = self.env.cr.dictfetchall()

            # --------------------------------------------------
            # 3) Prepare XLSX Workbook & Formatting
            # --------------------------------------------------
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            sheet = workbook.add_worksheet('Bank Statement')

            # Column widths
            # NO, Date, Trans ID, Bank Ref, Partner, Reference/Label, Related Bill, Debit, Credit, Balance
            col_widths = [5, 12, 18, 20, 20, 25, 20, 15, 15, 15]
            for i, w in enumerate(col_widths):
                sheet.set_column(i, i, w)

            # Formats
            merge_bold_font = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#D3D3D3'})
            bold_font = workbook.add_format({'bold': True, 'align': 'left'})
            border = workbook.add_format({'border': 1, 'align': 'center'})
            border_left = workbook.add_format({'border': 1, 'align': 'left'})
            border_num = workbook.add_format({'border': 1, 'align': 'right', 'num_format': '#,##0.00'})
            border_date = workbook.add_format({'border': 1, 'align': 'center', 'num_format': 'yyyy-mm-dd'})
            total_format = workbook.add_format({'bold': True, 'border': 1, 'align': 'right', 'num_format': '#,##0.00', 'bg_color': '#D3D3D3'})

            # --------------------------------------------------
            # 4) Header Section
            # --------------------------------------------------
            journal_names = ', '.join(rec.journal_ids.mapped('name')) if rec.journal_ids else 'All Journals'
            project_name = rec.project_id.name if rec.project_id else 'All Projects'

            sheet.write('A1', 'Report:', bold_font)
            sheet.write('B1', 'Bank Statement Report', bold_font)

            sheet.write('A2', 'Journal:', bold_font)
            sheet.write('B2', journal_names, bold_font)

            sheet.write('A3', 'Account Name:', bold_font)
            sheet.write('B3', rec.account_id.name, bold_font)
            
            sheet.write('A4', 'Project:', bold_font)
            sheet.write('B4', project_name, bold_font)
            
            period_str = f"From {rec.date_from or 'Start'} To {rec.date_to or 'End'}"
            sheet.write('A5', 'Period:', bold_font)
            sheet.write('B5', period_str, bold_font)

            # Table Headers (Updated column title)
            headers = [
                'NO', 'Date', 'Trans ID', 'Bank Transfer Ref', 'Partner', 
                'Reference/Label', 'Related Bill/Invoice', 'Debit', 'Credit', 'Balance'
            ]
            current_row = 6
            sheet.write_row(current_row, 0, headers, merge_bold_font)
            current_row += 1

            # --------------------------------------------------
            # 5) Write Opening Balance Row
            # --------------------------------------------------
            sheet.merge_range(f'A{current_row+1}:G{current_row+1}', 'Balance Before Period', merge_bold_font)
            
            sheet.write(current_row, 7, ob_debit, total_format)
            sheet.write(current_row, 8, ob_credit, total_format)
            sheet.write(current_row, 9, running_balance, total_format)
            current_row += 1

            # --------------------------------------------------
            # 6) Iterate and Write Data Lines
            # --------------------------------------------------
            line_no = 1
            total_debit = ob_debit
            total_credit = ob_credit

            for item in rows:
                running_balance += item['debit']
                running_balance -= item['credit']
                total_debit += item['debit']
                total_credit += item['credit']

                ref_str = item['reference'] if item['reference'] else item['label']

                # Write line 
                sheet.write(current_row, 0, line_no, border)
                sheet.write(current_row, 1, item['date'], border_date)
                sheet.write(current_row, 2, item['transaction_id'] or '', border_left) 
                sheet.write(current_row, 3, item['bank_reference'] or '', border_left) # Pulls from m.bank_transfer_ref
                sheet.write(current_row, 4, item['partner'] or '', border_left)
                sheet.write(current_row, 5, ref_str or '', border_left)
                sheet.write(current_row, 6, item['related_invoices'] or '', border_left) 
                sheet.write(current_row, 7, item['debit'] or 0, border_num)
                sheet.write(current_row, 8, item['credit'] or 0, border_num)
                sheet.write(current_row, 9, running_balance, border_num)

                line_no += 1
                current_row += 1

            # --------------------------------------------------
            # 7) Footer / Totals
            # --------------------------------------------------
            sheet.merge_range(f'A{current_row+1}:G{current_row+1}', 'Total', merge_bold_font)
            sheet.write(current_row, 7, total_debit, total_format)
            sheet.write(current_row, 8, total_credit, total_format)
            sheet.write(current_row, 9, running_balance, total_format)

            
            workbook.close()
            output.seek(0)
            
            rec.file_name = 'Bank_Statement_Report.xlsx'
            rec.file_data = base64.b64encode(output.read())
            output.close()

            return {
                'type': 'ir.actions.act_window',
                'res_model': self._name,
                'view_mode': 'form',
                'res_id': rec.id,
                'target': 'new',
            }
    
    def action_print_report(self):
        for rec in self:
            report_data = []

            # Determine the Analytic Account ID linked to the selected Project
            analytic_id_str = False
            if rec.project_id:
                analytic_account = getattr(rec.project_id, 'account_id', False) or getattr(rec.project_id, 'analytic_account_id', False)
                if analytic_account:
                    analytic_id_str = str(analytic_account.id)

            # --------------------------------------------------
            # 1) Calculate Opening Balance (before date_from)
            # --------------------------------------------------
            opening_balance = 0

            if rec.date_from:
                opening_sql = """
                    SELECT
                        COALESCE(SUM(aml.debit), 0) AS debit,
                        COALESCE(SUM(aml.credit), 0) AS credit
                    FROM account_move_line aml
                    JOIN account_move m ON aml.move_id = m.id
                    WHERE aml.account_id = %s
                      AND m.move_type = 'entry'
                      AND m.state = 'posted'
                      AND aml.date < %s
                """
                opening_params = [rec.account_id.id, rec.date_from]

                if analytic_id_str:
                    opening_sql += " AND aml.analytic_distribution ? %s"
                    opening_params.append(analytic_id_str)

                if rec.journal_ids and len(rec.journal_ids) > 0:
                    opening_sql += " AND aml.journal_id IN %s"
                    opening_params.append(tuple(rec.journal_ids.ids))

                self.env.cr.execute(opening_sql, opening_params)
                result = self.env.cr.fetchone()
                if result:
                    opening_balance = (result[0] or 0) - (result[1] or 0)

            running_balance = opening_balance

            ob_debit = opening_balance if opening_balance > 0 else 0.0
            ob_credit = abs(opening_balance) if opening_balance < 0 else 0.0

            # --------------------------------------------------
            # 2) Main SQL for report lines
            # --------------------------------------------------
            sql = """
                SELECT aml.date,
                       c.name AS company_name,
                       p.name AS partner,
                       COALESCE(aml.ref, aml.name) AS reference,
                       m.name AS transaction_id,
                       
                       -- ADDED: Bank Transfer Ref Field
                       m.bank_transfer_ref AS bank_reference,
                       
                       aml.debit,
                       aml.credit,
                       aml.name AS label,
                       cur.symbol AS currency_symbol,
                       cur.name   AS currency_name,
                       cur.id     AS currency_id,
                       m.move_type AS move_type,
                       
                       (SELECT name FROM account_analytic_account WHERE id::text = (SELECT k FROM jsonb_object_keys(aml.analytic_distribution) AS k LIMIT 1)) AS project,

                       (
                           SELECT string_agg(DISTINCT inv.name, ', ')
                           FROM account_move_line pay_line
                           LEFT JOIN account_partial_reconcile apr_dr ON apr_dr.credit_move_id = pay_line.id
                           LEFT JOIN account_partial_reconcile apr_cr ON apr_cr.debit_move_id = pay_line.id
                           INNER JOIN account_move_line inv_line ON inv_line.id = COALESCE(apr_dr.debit_move_id, apr_cr.credit_move_id)
                           INNER JOIN account_move inv ON inv.id = inv_line.move_id
                           WHERE pay_line.move_id = m.id
                             AND inv.move_type IN ('out_invoice', 'in_invoice', 'out_refund', 'in_refund', 'out_receipt', 'in_receipt')
                             AND inv.id != m.id
                       ) AS related_invoices
                FROM account_move_line aml
                JOIN account_move m ON aml.move_id = m.id
                LEFT JOIN res_partner p ON aml.partner_id = p.id
                JOIN res_company c ON aml.company_id = c.id
                LEFT JOIN res_currency cur ON aml.currency_id = cur.id
                WHERE aml.account_id = %s
                  AND m.move_type = 'entry'
                  AND m.state = 'posted'
            """

            params = [rec.account_id.id]

            if rec.date_from:
                sql += " AND aml.date >= %s"
                params.append(rec.date_from)
            if rec.date_to:
                sql += " AND aml.date <= %s"
                params.append(rec.date_to)
                
            if analytic_id_str:
                sql += " AND aml.analytic_distribution ? %s"
                params.append(analytic_id_str)
                
            if rec.journal_ids and len(rec.journal_ids) > 0:
                sql += " AND aml.journal_id IN %s"
                params.append(tuple(rec.journal_ids.ids))

            sql += " ORDER BY aml.date ASC"

            self.env.cr.execute(sql, params)
            rows = self.env.cr.dictfetchall()

            total_debit = ob_debit
            total_credit = ob_credit

            for item in rows:
                running_balance += item['debit']
                running_balance -= item['credit']
                total_debit += item['debit']
                total_credit += item['credit']

                ref_str = item['reference'] if item['reference'] else item['label']

                project_name = item['project']
                if isinstance(project_name, dict):
                    project_name = project_name.get(self.env.lang) or project_name.get('en_US') or next(iter(project_name.values()), '')

                line = {
                    'date': item['date'],
                    'company_name': item['company_name'],
                    'partner': item['partner'],
                    'reference': ref_str,
                    'transaction_id': item['transaction_id'] or '',
                    'bank_reference': item['bank_reference'] or '',
                    'related_invoices': item['related_invoices'] or '',
                    'project': project_name or '', 
                    'debit': item['debit'],
                    'credit': item['credit'],
                    'balance': running_balance,
                    'currency_symbol': item['currency_symbol'] or '',
                    'currency_name': item['currency_name'] or '',
                    'currency_id': item['currency_id'],
                    'move_type': item['move_type'],
                }
                report_data.append(line)

            journal_names = ', '.join(rec.journal_ids.mapped('name')) if rec.journal_ids else 'All Journals'
            project_name = rec.project_id.name if rec.project_id else 'All Projects'

            finance_data = {
                'form_data': rec.read()[0],
                'lines': report_data,
                'account_name': rec.account_id.name,
                'journal_names': journal_names,
                'project_name': project_name,
                'opening_balance': opening_balance,
                'ob_debit': ob_debit,
                'ob_credit': ob_credit,
                'total_balance': running_balance,
                'total_debit': total_debit,
                'total_credit': total_credit,
                'report_logo': rec.company_id.logo.decode('utf-8') if rec.company_id.logo else False,
            }

            return self.env.ref('inherit_account_move.action_print_bank_statement_reports').report_action(
                self, data=finance_data
            )