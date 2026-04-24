from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class JournalTransfer(models.Model):
    _name = 'journal.transfer'
    _description = 'Journal Transfer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Reference', required=True, copy=False,
                      readonly=True, default=lambda self: _('New'))
    description = fields.Char(string='Description')
    date = fields.Date(string='Date', required=True, default=fields.Date.today,
                      tracking=True)
    from_journal_id = fields.Many2one('account.journal', string='From Journal',
                                     required=True, tracking=True,
                                     domain="[('type', 'in', ['bank', 'cash'])]")
    to_journal_id = fields.Many2one('account.journal', string='To Journal',
                                   required=True, tracking=True,
                                   domain="[('type', 'in', ['bank', 'cash'])]")
    
    currency_id = fields.Many2one('res.currency', string='Currency',
                                 default=lambda self: self.env.company.currency_id)
    amount = fields.Monetary(string='Amount', currency_field='currency_id', required=True, tracking=True)
    rate = fields.Float(string='Rate', digits='Currency Rate',
                    help="Specify the exchange rate if source and destination currencies differ. "
                    "If left empty, Default exchange rate will be used.",tracking=True)
    to_journal_currency_id = fields.Many2one(related='to_journal_id.currency_id', string='To Journal Currency')
    transfer_amount = fields.Monetary(string='Transfer Amount', compute='_compute_transfer_amount',  currency_field='to_journal_currency_id', required=True, tracking=True)
    
    # This is the crucial account for inter-journal transfers.
    # It should be an "Internal Transfer" or "Suspense" account.
    # It gets debited by the outbound payment and credited by the inbound payment, netting to zero.
    # It should be a non-reconcilable account, typically of type 'Current Assets' or 'Other Current Liabilities'.
    # Ensure this account does NOT have a 'Secondary Currency' set.
    interim_transfer_account_id = fields.Many2one(
        'account.account',
        string="Interim Transfer Account",
        required=True,
        domain="[('reconcile', '=', False)]",
        default=lambda self: self._default_interim_transfer_account(),
        help="This account is used to temporarily hold the transfer amount. "
             "It should be a non-reconcilable account, typically of type 'Current Assets' or 'Other Current Liabilities'."
             "Ensure this account does NOT have a 'Secondary Currency' set."
    )
    transfer_date = fields.Date(string='Transfer Date' , default=fields.Date.today())
    outbound_payment_id = fields.Many2one('account.payment', string='Outbound Payment')
    inbound_payment_id = fields.Many2one('account.payment', string='Inbound Payment')

    notes = fields.Text(string='Notes', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    
    
    @api.model
    def _default_interim_transfer_account(self):
        """Get the default interim transfer account from company settings"""
        transfer_account = self.env.company.transfer_account_id
        if not transfer_account:
            raise ValidationError(_(
                "No 'Transfer Account' is configured in your company settings. "
                "Please go to Accounting -> Configuration -> Settings -> Bank & Cash "
                "and set a 'Transfer Account' (typically a non-reconcilable Current Assets/Liabilities account)."
            ))
        
        # Ensure the transfer account does not have a secondary currency set
        if transfer_account.currency_id:
             raise ValidationError(_(
                "The configured 'Transfer Account' (%s) has a secondary currency set. "
                "Please remove the secondary currency from this account in your Chart of Accounts "
                "for proper inter-journal transfers."
            ) % transfer_account.display_name)

        if transfer_account:
            return transfer_account
        else:
            return self.env['account.account'].search([('reconcile', '=', False)], limit=1)
        
        
    @api.onchange('from_journal_id')
    def _onchange_from_journal(self):
        if self.from_journal_id:
            self.currency_id = self.from_journal_id.currency_id or self.env.company.currency_id
    
    @api.onchange('to_journal_id')
    def _onchange_to_journal(self):
        if self.to_journal_id:
            self.to_journal_currency_id = self.to_journal_id.currency_id or self.env.company.currency_id
    
    @api.depends('amount', 'currency_id', 'to_journal_currency_id', 'date', 'rate')
    def _compute_transfer_amount(self):
        """
        Computes the transfer amount for the destination journal, handling currency conversion.
        If a manual rate is provided, it will be used; otherwise, Odoo's default conversion applies.
        """
        for record in self:
            # Set default transfer amount to 0.0
            record.transfer_amount = 0.0
            
            # Only proceed if we have all required values
            if record.currency_id != record.to_journal_currency_id and record.rate > 0:
                record.transfer_amount = record.amount * record.rate
                return
                
            # No conversion needed if currencies match
            if record.currency_id == record.to_journal_currency_id:
                record.transfer_amount = record.amount
                return
                
            # Use default currency conversion rate
            record.transfer_amount = record.currency_id._convert(
                record.amount,
                record.to_journal_currency_id,
                record.env.company,
                record.date or fields.Date.today()
            )
        
    def action_view_payments(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payments',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'domain': [('id', 'in', (self.outbound_payment_id.id, self.inbound_payment_id.id))],
            'context': {'active_test': False}
        }


    def action_post(self):
        self.ensure_one()
        if self.from_journal_id == self.to_journal_id:
            raise ValidationError(_("Cannot transfer to the same journal"))
        if self.currency_id != self.to_journal_currency_id and self.rate and self.rate > 0:
            # Update the currency rate in the system for future reference
            rate_env = self.env['res.currency.rate']
            existing_rate = rate_env.search([
                ('currency_id', '=', self.currency_id.id),
                ('company_id', '=', self.env.company.id),
                ('name', '=', self.date)
            ], limit=1)
            
            if existing_rate:
                existing_rate.write({'rate': 1 / self.rate})
            else:
                rate_env.create({
                    'currency_id': self.currency_id.id,
                    'rate': 1 / self.rate,
                    'name': self.date,
                    'company_id': self.env.company.id
                })
        """
        Executes the inter-journal transfer by creating and posting two payments.
        """
        self.ensure_one()

        if not self.interim_transfer_account_id:
            raise ValidationError(_("Please select an Interim Transfer Account to proceed."))

        # --- Create Outbound Payment (from_journal_id) ---
        # This payment moves money OUT of the source journal's bank/cash account
        # and INTO the interim transfer account.
        self.write({
            'name': self.env['ir.sequence'].next_by_code('internal.transfer') or _('New'),
        })
        try:
            outbound_payment = self.env['account.payment'].create({
                'date': self.date,
                'payment_type': 'outbound',
                'journal_id': self.from_journal_id.id,
                'amount': self.amount,
                'currency_id': self.currency_id.id, # Currency of the source journal
                'amount_signed': self.amount, # Amount in payment currency
                'memo': f'{self.description} , {self.name} - Transfer to {self.to_journal_id.name}',
                # The destination_account_id for an outbound internal transfer
                # should be the interim clearing account.
                'destination_account_id': self.interim_transfer_account_id.id,
            })
            # Post the outbound payment to generate its journal entries
            outbound_payment.action_post()
            self.outbound_payment_id = outbound_payment.id
            self.env.cr.commit() # Commit after first payment to avoid issues if second fails
            
        except Exception as e:
            self.env.cr.rollback() # Rollback if first payment fails
            raise ValidationError(_(f"Error creating/posting outbound payment: {e}"))

        # --- Create Inbound Payment (to_journal_id) ---
        # This payment moves money OUT of the interim transfer account
        # and INTO the destination journal's bank/cash account.
        try:
            inbound_payment = self.env['account.payment'].create({
                'date': self.date,
                'payment_type': 'inbound',
                'journal_id': self.to_journal_id.id,
                'amount': self.transfer_amount,
                'currency_id': self.to_journal_currency_id.id, # Currency of the destination journal
                'amount_signed': self.transfer_amount, # Amount in payment currency
                'memo': f' {self.description} , {self.name} - Transfer from {self.from_journal_id.name}',
                # The destination_account_id for an inbound internal transfer
                # should also be the interim clearing account.
                'destination_account_id': self.interim_transfer_account_id.id,
            })
            # Post the inbound payment to generate its journal entries
            inbound_payment.action_post()
            self.inbound_payment_id = inbound_payment.id
            self.env.cr.commit() # Commit after second payment
            
        except Exception as e:
            self.env.cr.rollback() # Rollback if second payment fails
            # If the inbound payment fails, you might want to reverse the outbound payment
            # to keep the books clean. This is an advanced error handling scenario.
            if self.outbound_payment_id:
                try:
                    self.outbound_payment_id.action_cancel() # Or action_draft, then unlink
                    self.outbound_payment_id.unlink()
                except Exception as cancel_e:
                    _logger.error(f"Failed to cancel/unlink outbound payment after inbound payment failure: {cancel_e}")
                    raise ValidationError(_(f"Error creating/posting inbound payment: {e}\n"
                                      f"Also failed to clean up the outbound payment. Please manually review payment {self.outbound_payment_id.name}."))
            raise ValidationError(_(f"Error creating/posting inbound payment: {e}"))

        self.write({
            'state': 'posted',
            # 'transfer_date': self.date,
        })
        # Log message in chatter about the transfer details
        self.message_post(
            body=_(
                'Transfer completed:\n'
                '- From: %(from_journal)s\n'
                '- To: %(to_journal)s\n' 
                '- Amount: %(amount)s %(currency)s\n'
                '- Transfer Amount: %(transfer_amount)s %(to_currency)s'
            ) % {
                'from_journal': self.from_journal_id.name,
                'to_journal': self.to_journal_id.name,
                'amount': self.amount,
                'currency': self.currency_id.name,
                'transfer_amount': self.transfer_amount,
                'to_currency': self.to_journal_currency_id.name,
            }
        )

    def action_draft(self):
         # Reset payments
        if self.outbound_payment_id:
            self.outbound_payment_id.action_draft()
            self.outbound_payment_id.unlink()
        if self.inbound_payment_id:
            self.inbound_payment_id.action_draft() 
            self.inbound_payment_id.unlink()
        # Reset transfer state
        self.write({
            'state': 'draft',
            'outbound_payment_id': False,
            'inbound_payment_id': False
        })

    def action_cancel(self):
        # if self.move_id:
        #     self.move_id.button_cancel()
        self.write({'state': 'cancelled'})

    def unlink(self):
        if any(record.state != 'draft' for record in self):
            raise ValidationError(_("You can only delete transfers in draft state"))
        return super().unlink()
