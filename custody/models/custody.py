from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import re

class AccountCustody(models.Model):
    _inherit = 'account.journal'

    def _get_default_account_id(self):
        default_account_id = int(self.env['ir.config_parameter'].get_param('custody.custody_default_account_id'))
        if default_account_id:
            return self.env['account.account'].search([('id', '=', default_account_id)], limit=1)
        else:
            return self.env['account.account'].search([('account_type', '=', 'asset_cash')], limit=1)

    is_custody = fields.Boolean(
        string='Is Custody Journal',
        tracking=True,
        help='Check this if this journal is used for custody management'
    )

    custody_employee_id = fields.Many2one(
        'hr.employee',
        string='Custody Employee',
        tracking=True,
        help='Employee responsible for this custody'
    )

    custody_status = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('closed', 'Closed')
    ], string='Custody Status',
       default='draft',
       tracking=True,
       help='Current status of the custody'
    )

    custody_balance = fields.Monetary(
        string='Custody Balance',
        store=True,
        tracking=True,
        help='Current balance of the custody journal'
    )


    balance = fields.Char(
        string='Balance',
        compute='_compute_balance',
    )


    @api.depends('currency_id')  # not required unless you store it
    def _compute_balance(self):
        journals_with_id = self.filtered(lambda j: j.id)
        if journals_with_id:
            result = journals_with_id._get_journal_dashboard_data_batched()
        else:
            result = {}
        for journal in self:
            if journal.id:
                data = result.get(journal.id, {})
                journal.balance = str(data.get('account_balance', 0.0))
            else:
                journal.balance = '0.0'

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        default_account = self._get_default_account_id()
        res['default_account_id'] = default_account.id
        res['type'] = 'bank'
        res['user_ids'] = self.env.user
        res['currency_id'] = self.env.company.currency_id.id
        return res

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            for payment_method in record.inbound_payment_method_line_ids:
                payment_method.payment_account_id = record.default_account_id
            for payment_method in record.outbound_payment_method_line_ids:
                payment_method.payment_account_id = record.default_account_id
        return records

    def unlink(self):
        """Prevent deletion of non-draft custodies and show warning message"""
        for custody in self:
            if custody.custody_status != 'draft':
                raise UserError(_('You cannot delete a custody that is not in draft state.'))
        return super().unlink()

    @api.onchange('is_custody')
    def _onchange_is_custody(self):
        """Set default values when is_custody is checked"""
        if self.is_custody and not self.custody_status:
            self.custody_status = 'draft'

    def action_activate_custody(self):
        """Activate the custody"""
        self.ensure_one()
        self.custody_status = 'active'
        self.message_post(body=_('Custody activated'))

    def action_suspend_custody(self):
        """Suspend the custody"""
        self.ensure_one()
        self.custody_status = 'suspended'
        self.message_post(body=_('Custody suspended'))

    def _get_balance_as_float(self):
        """
        Helper method to clean and convert the 'balance' char field to a float.
        Handles various currency symbols and formats.
        Returns 0.0 if the balance field is empty or cannot be converted.
        """
        self.ensure_one() # This method should be called on a single record
        
        if not self.balance:
            return 0.0

        # Remove all non-digit, non-decimal point, non-hyphen characters
        # This handles currency symbols, spaces, and other non-numeric parts
        cleaned_balance_str = re.sub(r'[^\d.-]', '', self.balance)

        # Handle cases where comma is used as a decimal separator (common in Europe)
        # This is a more complex scenario. For simplicity, we assume dot is the decimal.
        # If you expect '1.234,56' to be 1234.56, you'd need locale-aware parsing or
        # specific string replacement: cleaned_balance_str = cleaned_balance_str.replace(',', '.')
        # However, the current regex might turn '1.234,56' into '1.23456' which is incorrect if ',' is decimal.
        # If your data consistently uses a comma for decimal, you might add:
        # cleaned_balance_str = cleaned_balance_str.replace(',', '.')

        # Handle multiple decimal points if they accidentally remain
        if '.' in cleaned_balance_str:
            parts = cleaned_balance_str.split('.')
            if len(parts) > 2: # More than one decimal point after cleaning
                # Keep the first part and the joined subsequent parts
                cleaned_balance_str = parts[0] + '.' + ''.join(parts[1:])
            elif len(parts) == 2 and not parts[1]: # If it ends with a dot, e.g., '123.'
                cleaned_balance_str = parts[0]
        
        # Try to convert to float, return 0.0 if conversion fails
        try:
            return float(cleaned_balance_str)
        except ValueError:
            # Log the error or handle it as per your requirements
            self.env.cr.rollback() # Important in Odoo if an error prevents further processing
            raise UserError(_("Could not convert balance '%s' to a numeric value for journal %s. Please check the balance format.") % (self.balance, self.display_name))
            # Or simply return 0.0 if you want to silently fail:
            # return 0.0

    def action_close_custody(self):
        """Close the custody"""
        self.ensure_one()
        current_balance_float = self._get_balance_as_float()
        if abs(current_balance_float) > 0.0001: # Check if balance is significantly different from zero
            raise UserError(_('Cannot close custody with remaining balance (%.2f). Please transfer the balance before closing.') % current_balance_float)
        # if self.balance :
        #     balance = self.balance.replace('SDG', '').strip()
        #     if balance != 0.0:
        #         raise UserError(_('Cannot close custody with remaining balance. Please transfer the balance before closing.'))
        self.custody_status = 'closed'
        self.message_post(body=_('Custody closed'))

    def action_reset_to_draft(self):
        """Reset the custody to draft"""
        self.ensure_one()
        self.custody_status = 'draft'
        self.message_post(body=_('Custody reset to draft'))