from email.policy import default

from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    is_credit = fields.Boolean(string='Credit Note', default=False)
    pay_state = fields.Boolean(string='pay state', compute="_compute_pay_state", store=True)
    rate = fields.Float(string="Rate")
    required_rate = fields.Boolean(string="Required Rate", compute="_compute_required_rate")
    refund_case = fields.Selection([
        ('normal', 'Normal'),
        ('error', 'Error Refund'),
    ], string="Refund Case", default="normal")
    name_placeholder = fields.Char(string="Placeholder", store=False)

    def action_print_pdf(self):
        return self.action_invoice_print()

    # ودي برضه احتياطي لو ضربت معاك في الزرار التاني
    def action_invoice_sent(self):
        return super(AccountMoveInherit, self).action_invoice_sent()

    @api.depends('payment_state')
    def _compute_pay_state(self):
        for rec in self:
            if rec.payment_state == 'paid':
                rec.pay_state = True
            elif rec.payment_state == 'not_paid':
                rec.pay_state = False


    @api.depends('project_id')
    def _compute_required_rate(self):
        for rec in self:
            if rec.project_id:
                rec.required_rate = True
            elif not rec.project_id:
                rec.required_rate = False

    def action_post(self):
        res = super(AccountMove, self).action_post()
        crossovered = self.env['crossovered.budget']
        budget_quarters = self.env['budget.quarte']
        opj = self.env['crossovered.budget']
        if self.move_type == 'in_invoice':
            if self.project_id:
                crossovere_budget = crossovered.search([('project_id', '=', self.project_id.id)])
                if crossovere_budget and self.invoice_date > crossovere_budget.date_to or self.invoice_date < crossovere_budget.date_from:
                    raise ValidationError(_(
                        "⛔ alert\n\n"
                        "'The invoice date must be within the project period."
                        f"Project period: from  {crossovere_budget.date_from}\n"
                        f"to : {crossovere_budget.date_to}\n"
                    ))
            for rec in self:
                if rec.required_rate:
                    if rec.rate <= 0:
                        raise ValidationError(_('Please enter the rate'))
                    elif rec.rate > 0:
                        crossovered_budget = opj.search([('project_id', '=', self.project_id.id)])
                        for invoice_line in rec.invoice_line_ids:
                            for line in crossovered_budget.mapped('budget_iteme_lines'):
                                if invoice_line.account_id == line.account_id and invoice_line.budget_item_line_id.line_code == line.line_code:
                                    if invoice_line.currency_id == line.currency_id:
                                        if invoice_line.price_subtotal + line.budget_line_theoritical_amount > line.budget_line_planned_amount + line.allowed_increase:
                                            raise ValidationError(_(
                                                "⛔ alert\n\n"
                                                f"Code: {invoice_line.budget_item_line_id.line_code}\n"
                                                f"Account:   {invoice_line.account_id.name}\n"
                                                "The invoice amount is greater than  the  budget Planned balance in the account.."))
                                    else:
                                        amount = invoice_line.price_subtotal  * (1 / rec.rate)
                                        if amount + line.budget_line_theoritical_amount > line.budget_line_planned_amount + line.allowed_increase:
                                            raise ValidationError(_(
                                                "⛔ alert\n\n"
                                                f"Code: {invoice_line.budget_item_line_id.line_code}\n"
                                                f"Account:   {invoice_line.account_id.name}\n"
                                                "The invoice amount is greater than  the  budget Planned balance in the account.."))
                                    quarters= budget_quarters.search([('budget_id','=',crossovered_budget.id),('budget_line_id','=',invoice_line.quarter_id.id)])
                                    if quarters:
                                        invoice_amount = []
                                        for qua in quarters.mapped('quarter_line_ids'):
                                            if qua.account_id == invoice_line.account_id  and qua.line_code == invoice_line.budget_item_line_id.line_code:
                                                if invoice_line.currency_id == qua.currency_id:
                                                    if invoice_line.price_subtotal + qua.theoritical_amount > qua.planned_amount + qua.allowed_increase_line :
                                                        # raise ValidationError(_(
                                                        #     "⛔ alert\n\n"
                                                        #     f"Code: {invoice_line.budget_item_line_id.line_code}\n"
                                                        #     f"Account:   {invoice_line.account_id.name}\n"
                                                        #     "The invoice amount is greater than  the  quarters Planned balance in the account.."))
                                                        line.write({'budget_line_theoritical_amount': line.budget_line_theoritical_amount + invoice_line.price_subtotal})
                                                        qua.write({'theoritical_amount': qua.theoritical_amount + invoice_line.price_subtotal})
                                                    else:
                                                        line.write({'budget_line_theoritical_amount': line.budget_line_theoritical_amount + invoice_line.price_subtotal})
                                                        qua.write({'theoritical_amount': qua.theoritical_amount + invoice_line.price_subtotal})
                                                else:
                                                    amount = invoice_line.price_subtotal * (1 / rec.rate)
                                                    if amount + qua.theoritical_amount > qua.planned_amount + qua.allowed_increase_line:
                                                        # raise ValidationError(_(
                                                        #     "⛔ alert\n\n"
                                                        #     f"Code: {invoice_line.budget_item_line_id.line_code}\n"
                                                        #     f"Account:   {invoice_line.account_id.name}\n"
                                                        #     "The invoice amount is greater than  the  quarters Planned balance in the account.."))
                                                        line.write({'budget_line_theoritical_amount':line.budget_line_theoritical_amount + (invoice_line.price_subtotal  * (1/rec.rate))})
                                                        qua.write({'theoritical_amount': qua.theoritical_amount + (invoice_line.price_subtotal  * (1/rec.rate))})
                                                    else:
                                                        line.write({'budget_line_theoritical_amount':line.budget_line_theoritical_amount + (invoice_line.price_subtotal  * (1/rec.rate))})
                                                        qua.write({'theoritical_amount': qua.theoritical_amount + (invoice_line.price_subtotal  * (1/rec.rate))})

            return res
        elif self.move_type=='in_refund':
            for rec in self:
                if rec.rate == 0:
                    raise ValidationError(_('Please enter the rate'))
                elif rec.rate > 0:
                    crossovered_budget = opj.search([('project_id', '=', self.project_id.id)])
                    for invoice_line in self.invoice_line_ids:
                        for record in crossovered_budget.mapped('budget_iteme_lines'):
                            if invoice_line.account_id == record.account_id and invoice_line.budget_item_line_id.line_code == record.line_code:
                                if invoice_line.currency_id == record.currency_id:
                                    if rec.refund_case == 'error':
                                        record.write({
                                                        'budget_line_theoritical_amount': record.budget_line_theoritical_amount - invoice_line.price_unit})
                                    elif rec.refund_case == 'normal':
                                        record.write({
                                                        'budget_line_theoritical_amount': record.budget_line_theoritical_amount - invoice_line.price_subtotal})
                                else:
                                    if rec.refund_case == 'error':
                                        record.write({
                                                        'budget_line_theoritical_amount': record.budget_line_theoritical_amount - (
                                                                    invoice_line.price_unit * (1 / self.rate))})
                                    elif rec.refund_case == 'normal': 
                                        record.write({
                                                        'budget_line_theoritical_amount': record.budget_line_theoritical_amount - (
                                                                    invoice_line.price_subtotal * (1 / self.rate))})
                        quarters = budget_quarters.search([('budget_id', '=', crossovered_budget.id),
                                                           ('budget_line_id', '=', invoice_line.quarter_id.id)])
                        if quarters:
                            for qua in quarters.mapped('quarter_line_ids'):
                                if qua.account_id == invoice_line.account_id and qua.line_code == invoice_line.budget_item_line_id.line_code:
                                    if invoice_line.currency_id == qua.currency_id:
                                        if rec.refund_case == 'error':
                                            qua.write(
                                                {'theoritical_amount': qua.theoritical_amount - invoice_line.price_unit})
                                        elif rec.refund_case == 'normal':
                                            qua.write(
                                                {'theoritical_amount': qua.theoritical_amount - invoice_line.price_subtotal})
                                    else:
                                        if rec.refund_case == 'error':
                                            qua.write({'theoritical_amount': qua.theoritical_amount - (
                                                        invoice_line.price_unit * (1 / self.rate))})
                                        elif rec.refund_case == 'normal':
                                            qua.write({'theoritical_amount': qua.theoritical_amount - (
                                                        invoice_line.price_subtotal * (1 / self.rate))})
                return res

    def button_draft(self):
        res = super(AccountMove, self).button_draft()
        budget_quarters = self.env['budget.quarte']
        opj = self.env['crossovered.budget']
        if self.move_type=='in_invoice' and self.pay_state == True and self.project_id:
                    raise ValidationError(_(
                        "⛔ alert\n\n"
                        f"The invoice {self.name}  is pay."

                    ))
        elif  self.move_type=='in_invoice':
            if self.required_rate:
                if self.rate <= 0.0:
                    raise ValidationError(_('Please enter the rate'))
                crossovered_budget = opj.search([('project_id', '=', self.project_id.id)])
                for invoice_line in self.invoice_line_ids:
                    for record  in crossovered_budget.mapped('budget_iteme_lines'):
                        if invoice_line.account_id == record.account_id and invoice_line.budget_item_line_id.line_code == record.line_code:
                            if invoice_line.currency_id == record.currency_id:
                                record.write({'budget_line_theoritical_amount': record.budget_line_theoritical_amount - invoice_line.price_subtotal})
                            else:
                                record.write({'budget_line_theoritical_amount': record.budget_line_theoritical_amount -  (invoice_line.price_subtotal * (1 / self.rate))})
                    quarters = budget_quarters.search([('budget_id', '=', crossovered_budget.id),('budget_line_id', '=', invoice_line.quarter_id.id)])
                    if quarters:
                        for qua in quarters.mapped('quarter_line_ids'):
                            if qua.account_id == invoice_line.account_id and qua.line_code == invoice_line.budget_item_line_id.line_code:
                                if invoice_line.currency_id == qua.currency_id:
                                    qua.write({'theoritical_amount': qua.theoritical_amount -  invoice_line.price_subtotal})
                                else:
                                    qua.write({'theoritical_amount': qua.theoritical_amount - (invoice_line.price_subtotal * (1 / self.rate))})
            return res


        elif self.move_type == 'in_refund':
            raise ValidationError(_(
                "⛔ alert\n\n"
                "A refund has been issued for the current invoice. Please note that you can only receive a refund for the payment amount."
                f"Invoice number: {self.name}\n"
                f"Amount: {self.amount_total}\n"
                f"Bill Date: {self.invoice_date}\n"
            ))

    def action_reverse(self):

        res = super(AccountMove, self).action_reverse()

        if self.move_type=='in_invoice' and self.payment_state == 'not_paid':
            raise ValidationError(_(
                "⛔ alert\n\n"
                "This invoice has not been paid. You can collect the money or return the invoice. Any draft status."
                f"Invoice number: {self.name}\n"
            ))
        elif self.move_type=='in_refund' and self.payment_state == 'not_paid':
            raise ValidationError(_(
                "⛔ alert\n\n"
                "The invoice has already been refunded."
                f"Invoice number: {self.name}\n"
            ))
        elif self.move_type == 'in_refund' and self.payment_state == 'paid':
            raise ValidationError(_(
                "⛔ alert\n\n"
                "The invoice has already been refunded."
                f"Invoice number: {self.name}\n"
            ))
        return res
    # def action_post(self):
    #     res = super(AccountMove, self).action_post()
    #     count = 0
    #     if self.move_type == 'in_invoice':
    #         if self.project_id:
    #             crossovere_budget = self.env['crossovered.budget'].search([('project_id', '=', self.project_id.id)])
    #             if crossovere_budget and self.invoice_date > crossovere_budget.date_to or self.invoice_date < crossovere_budget.date_from:
    #                 raise ValidationError(_(
    #                     "⛔ alert\n\n"
    #                     "'The invoice date must be within the project period."
    #                     f"Project period: from  {crossovere_budget.date_from}\n"
    #                     f"to : {crossovere_budget.date_to}\n"
    #                 ))
    #         for rec in self:
    #             if rec.required_rate:
    #                 if rec.rate <= 0:
    #                     raise ValidationError(_('Please enter the rate'))
    #                 elif rec.rate > 0:
    #                     budget_item_amounts = {}

    #                     for line in rec.invoice_line_ids:
    #                         amount = line.price_unit * (1 / rec.rate)
    #                         for budget_item in line.budget_item_line_id:
    #                             key = (budget_item.id)
    #                             budget_item_amounts.setdefault(budget_item, 0.0)
    #                             budget_item_amounts[budget_item] += amount

    #                     for budget_item, total_amount in budget_item_amounts.items():
    #                         if budget_item.currency_id != rec.currency_id:
    #                             if budget_item.budget_line_theoritical_amount + total_amount > budget_item.budget_line_planned_amount + budget_item.allowed_increase:
    #                                 raise ValidationError(_(
    #                                     "⛔ alert\n\n"
    #                                     f"Code: {budget_item.line_code}\n"
    #                                     f"Account:   {budget_item.account_id.name}\n"
    #                                     "The invoice amount is greater than the Planned balance in the account.."
    #                                 ))
    #                         else:
    #                             if budget_item.budget_line_theoritical_amount + total_amount > budget_item.budget_line_planned_amount + budget_item.allowed_increase:
    #                                 raise ValidationError(_(
    #                                     "⛔ alert\n\n"
    #                                     f"Code: {budget_item.line_code}\n"
    #                                     f"Account:   {budget_item.account_id.name}\n"
    #                                     "The invoice amount is greater than the Planned balance in the account.."
    #                                 ))

    #                         budget_item.budget_line_theoritical_amount += total_amount
                            
                            # for line_id in rec.invoice_line_ids:
                            #     for quarter in line_id.quarter_id:
                            #         for qu in quarter.quarter_id:
                            #             for qu_line in qu.quarter_line_ids:
                            #                 if qu_line.currency_id == rec.currency_id and qu_line.line_code == line_id.budget_item_line_id.line_code and qu_line.account_id == line_id.account_id:
                            #                     print(qu_line.line_code)
                            #                     if (line_id.price_unit * (1/rec.rate)) + (qu_line.theoritical_amount) > qu_line.planned_amount + qu_line.allowed_increase_line:
                            #                         raise ValidationError(_(
                            #                             "⛔ alert\n\n"
                            #                             f"Code: {qu_line.line_code}\n"
                            #                             f"Project:   {line_id.project_id.name}\n"
                            #                             "The invoice amount is greater than the Planned balance in the quarter.."
                            #                         ))
                            #                     else:
                            #                         print("test",(line_id.price_unit * (1/rec.rate)) + qu_line.theoritical_amount)
                            #                         uptate_vals = {
                            #                             'theoritical_amount': (line_id.price_unit * (1/rec.rate)) + qu_line.theoritical_amount,
                            #                         }
                            #                         qu_line.write(uptate_vals)
                            #                 elif qu_line.currency_id != rec.currency_id and qu_line.line_code == line_id.budget_item_line_id.line_code and qu_line.account_id == line_id.account_id:
                            #                     if (line_id.price_unit * (1/rec.rate)) + (qu_line.theoritical_amount ) > qu_line.planned_amount + qu_line.allowed_increase_line:
                            #                         raise ValidationError(_(
                            #                             "⛔ alert\n\n"
                            #                             f"Code: {qu_line.line_code}\n"
                            #                             f"Project:   {line_id.project_id.name}\n"
                            #                             "The invoice amount is greater than the Planned balance in the quarter.."
                            #                         ))
                            #                     else:
                            #                         uptate_vals = {
                            #                             'theoritical_amount': (line_id.price_unit * (1/rec.rate)) + qu_line.theoritical_amount,
                            #                         }
                            #                         qu_line.write(uptate_vals)
                            # line_qu_amounts = {}
                            #
                            # for qu_budget in line.quarter_id:
                            #     for qu in qu_budget.quarter_id:
                            #         for line_qu in qu.quarter_line_ids:
                            #             if line_qu.line_code == line.budget_item_line_id.line_code and line_qu.account_id == line.account_id:
                            #                 key = (line_qu.id)
                            #                 line_qu_amounts.setdefault(line_qu, 0.0)
                            #                 line_qu_amounts[line_qu] += (line.price_unit * (1 / rec.rate))
                            #
                            # for line_qu, total_amount in line_qu_amounts.items():
                            #     print('$$$$$$$$$$$$$', line_qu.account_id)
                            #     if line_qu.currency_id == rec.currency_id:
                            #         if line_qu.theoritical_amount + total_amount > line_qu.planned_amount + line_qu.allowed_increase_line:
                            #             print('############', total_amount)
                            #             print('&&&&&&&&&&&&', line_qu.planned_amount + line_qu.allowed_increase_line)
                            #             raise ValidationError(_(
                            #                 "⛔ alert\n\n"
                            #                 f"Code: {line_qu.line_code}\n"
                            #                 f"Project:   {line.project_id.name}\n"
                            #                 "The invoice amount is greater than the Planned balance in the quarter.."
                            #             ))
                            #     else:
                            #         if line_qu.theoritical_amount + total_amount > line_qu.planned_amount + line_qu.allowed_increase_line:
                            #             raise ValidationError(_(
                            #                 "⛔ alert\n\n"
                            #                 f"Code: {line_qu.line_code}\n"
                            #                 f"Project:   {line.project_id.name}\n"
                            #                 "The invoice amount is greater than the Planned balance in the quarter.."
                            #             ))
                            #
                            #     line_qu.theoritical_amount += total_amount

        #     return res
        # elif self.move_type == 'in_refund':
        #     for rec in self:
        #         if rec.rate == 0:
        #             raise ValidationError(_('Please enter the rate'))
        #         elif rec.rate > 0:
        #             for line in rec.invoice_line_ids:
        #                 budget_line = self.env['budget.iteme.line'].search([
        #                     ('line_code', '=', line.budget_item_line_id.line_code),
        #                     ('account_id', '=', line.account_id.id),
        #                     ('currency_id', '!=', rec.currency_id.id),
        #                 ])
        #                 if budget_line:
        #                     for budget_line in budget_line:
        #                         new_theoretical_amount = budget_line.budget_line_theoritical_amount - (
        #                                 line.price_unit * (1 / rec.rate))
        #                         new_remaining_amount = budget_line.budget_line_planned_amount - new_theoretical_amount

        #                         vals = {
        #                             'budget_line_theoritical_amount': new_theoretical_amount,
        #                             'remaining_amount': new_remaining_amount,
        #                         }
        #                         budget_line.write(vals)

        #                 line_qu_amounts = {}
        #                 for qu_budget in line.quarter_id:
        #                     for qu in qu_budget.quarter_id:
        #                         for line_qu in qu.quarter_line_ids:
        #                             if line_qu.line_code == line.budget_item_line_id.line_code and line_qu.account_id == line.account_id:
        #                                 line_qu_amounts.setdefault(line_qu, 0.0)
        #                                 line_qu_amounts[line_qu] += (line.price_unit * (1 / rec.rate))

        #                 for line_qu, total_amount in line_qu_amounts.items():
        #                     line_qu.theoritical_amount -= total_amount
        #     return res

    def button_draft(self):
        res = super(AccountMove, self).button_draft()
        if self.move_type == 'in_invoice' and self.pay_state == True and self.project_id:
            raise ValidationError(_(
                "⛔ alert\n\n"
                f"The invoice  {self.name}  is pay."

            ))
        elif self.move_type == 'in_invoice':
            for rec in self:
                if rec.required_rate:
                    if rec.rate == 0:
                        raise ValidationError(_('Please enter the rate'))
                    elif rec.rate > 0:
                        for line in rec.invoice_line_ids:
                            invoice_amount = line.price_subtotal * (1 / rec.rate)

                            for budget_item in line.budget_item_line_id:
                                if budget_item.currency_id != rec.currency_id or budget_item.currency_id == rec.currency_id:
                                    new_theoretical = budget_item.budget_line_theoritical_amount - invoice_amount
                                    new_remaining = budget_item.budget_line_planned_amount - new_theoretical
                                    budget_item.budget_line_theoritical_amount = new_theoretical
                                    budget_item.remaining_amount = new_remaining

                            for qu_budget in line.quarter_id:
                                for qu in qu_budget.quarter_id:
                                    for line_qu in qu.quarter_line_ids:
                                        if line_qu.line_code == line.budget_item_line_id.line_code and line_qu.account_id == line.account_id:
                                            line_qu.theoritical_amount -= invoice_amount
            return res
        # elif self.move_type == 'in_refund':
        #     raise ValidationError(_(
        #         "⛔ alert\n\n"
        #         "A refund has been issued for the current invoice. Please note that you can only receive a refund for the payment amount."
        #         f"Invoice number: {self.name}\n"
        #         f"Amount: {self.amount_total}\n"
        #         f"Bill Date: {self.invoice_date}\n"
        #     ))

    def action_reverse(self):

        res = super(AccountMove, self).action_reverse()

        if self.move_type == 'in_invoice' and self.payment_state == 'not_paid':
            raise ValidationError(_(
                "⛔ alert\n\n"
                "This invoice has not been paid. You can collect the money or return the invoice. Any draft status."
                f"Invoice number: {self.name}\n"
            ))
        elif self.move_type == 'in_refund' and self.payment_state == 'not_paid':
            raise ValidationError(_(
                "⛔ alert\n\n"
                "The invoice has already been refunded."
                f"Invoice number: {self.name}\n"
            ))
        elif self.move_type == 'in_refund' and self.payment_state == 'paid':
            raise ValidationError(_(
                "⛔ alert\n\n"
                "The invoice has already been refunded."
                f"Invoice number: {self.name}\n"
            ))
        return res
