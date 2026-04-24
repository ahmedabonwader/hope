import io
import xlsxwriter
from odoo import http
from odoo.http import content_disposition, request

class BudgetReportExcel(http.Controller):
    @http.route('/export/budget_report_excel', type='http', auth='user')
    def export_budget_report(self, wizard_id, **kwargs):
        wizard = request.env['budget.report.wizard'].browse(int(wizard_id))
        data = wizard._prepare_report_data()  

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        sheet = workbook.add_worksheet('Budget Report')

        # Formats
        header_format = workbook.add_format({'bold': True, 'bg_color': '#dfdfdf'})
        number_format = workbook.add_format({'num_format': '#,##0.00'})

        # Headers
        headers = [
            'Transaction No', 'Date', 'Voucher No', 'Payee Name',
            'Transaction Details', 'Credit (+)', 'Debit (-)', 'Balance',
            'Amount USD', 'Budget Code'
        ]
        sheet.write_row(0, 0, headers, header_format)

        # Data
        for row, line in enumerate(data['report_data'], start=1):
            sheet.write(row, 0, line['transaction_no'])
            sheet.write(row, 1, line['date'])
            sheet.write(row, 2, line['voucher_no'])
            sheet.write(row, 3, line['payee'])
            sheet.write(row, 4, line['transaction_details'])
            sheet.write(row, 5, line['credit_sdg'], number_format)
            sheet.write(row, 6, line['debit_sdg'], number_format)
            sheet.write(row, 7, line['balance_sdg'], number_format)
            sheet.write(row, 8, line['amount_usd'], number_format)
            sheet.write(row, 9, line['line_code'])

        workbook.close()
        output.seek(0)

        # Return file
        filename = 'Budget_Report.xlsx'
        return request.make_response(
            output.read(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', content_disposition(filename))
            ]
        )