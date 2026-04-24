odoo.define('hms_optics_center.AccountingDashboard', function (require) {
    'use strict';
    var AbstractAction = require('web.AbstractAction');
    var ajax = require('web.ajax');
    var core = require('web.core');
    var rpc = require('web.rpc');
    var web_client = require('web.web_client');
    var _t = core._t;
    var QWeb = core.qweb;
    var self = this;
    const { loadBundle } = require("@web/core/assets");
    var currency;
    var ActionMenu = AbstractAction.extend({
        template: 'CMSFinancedashboard',
        renderElement: function (ev) {
            var self = this;
            $.when(this._super())
                .then(function (ev) {

                     rpc.query({
                        model: "hms.dashboard",
                        method: "get_currency",
                    }).then(function(result) {
                        currency = result;
                    })
                    rpc.query({
                        model: "hms.dashboard",
                        method: "get_today_income",
                        
                    }).then(function (result) {
                            var today_income_list = result['today_income_list'];
                            var amount = self.format_currency(currency, 0.00);
                            var balance = result['balance'];
                            for (var k = 0; k < today_income_list.length; k++) {
                                 if(balance[k] >=0 ){
                                    amount = self.format_currency(currency, balance[k]);
                                }
                                $('#today_income').append('<li><div>' + today_income_list[k] + ' : ' + amount + '</div></li>');
                            }
                            if (today_income_list.length <=0) {
                                $('#today_income').append('<span>' + self.format_currency(currency, 0.00)  + '</span> <div class="title"></div>')
                            }
                    })
                    rpc.query({
                        model: "hms.dashboard",
                        method: "get_today_expense",
                        
                    }).then(function (result) {
                           var today_expense_list = result['today_expense_list'];
                            var amount = self.format_currency(currency, 0.00);
                            var balance = result['balance'];
                            for (var k = 0; k < today_expense_list.length; k++) {
                                 if(balance[k] >=0 ){
                                    amount = self.format_currency(currency, balance[k]);
                                }
                                $('#today_expense').append('<li><div>' + today_expense_list[k] + ' : ' + amount + '</div></li>');
                            }
                            if (today_expense_list.length <=0) {
                                $('#today_expense').append('<span>' + self.format_currency(currency, 0.00)  + '</span> <div class="title"></div>')
                            }
                    })
                    rpc.query({
                        model: "hms.dashboard",
                        method: "get_net_income_today",
                        
                    }).then(function (result) {
                            var today_net_list = result['today_net_list'];
                            var amount = self.format_currency(currency, 0.00);
                            var balance = result['balance'];
                            for (var k = 0; k < today_net_list.length; k++) {
                                 if(balance[k] >=0 ){
                                    amount = self.format_currency(currency, balance[k]);
                                }
                                $('#net_income_today').append('<li><div>' + today_net_list[k] + ' : ' + amount + '</div></li>');
                            }
                            if (today_net_list.length <=0) {
                                $('#net_income_today').append('<span>' + self.format_currency(currency, 0.00)  + '</span> <div class="title"></div>')
                            }
                    })

                    rpc.query({
                        model: "hms.dashboard",
                        method: "get_cash_today",

                    }).then(function (result) {
                            var cash_list = result['cash_names'];
                            var amount = self.format_currency(currency, 0.00);
                            var balance = result['balance'];
                            var acc_ids = result['account_ids'];
                            for (var k = 0; k < cash_list.length; k++) {
                                 if(balance[k] >=0 ){
                                    amount = self.format_currency(currency, balance[k]);
                                }
                                $('#today_cash').append('<li><div val="' + acc_ids[k] + '"id="b_' + acc_ids[k] + '">' + cash_list[k] + ' : ' + amount + '</div></li>');
                            }
                            if (cash_list.length <=0) {
                                $('#today_cash').append('<span>' + self.format_currency(currency, 0.00)  + '</span> <div class="title"></div>')
                            }
                    })
                    rpc.query({
                        model: "hms.dashboard",
                        method: "get_bank_today",

                    }).then(function (result) {
                            var bank_list = result['banks_names'];
                            var amount = self.format_currency(currency, 0.00);
                            var balance = result['balance'];
                            var acc_ids = result['account_ids'];
                            for (var k = 0; k < bank_list.length; k++) {
                                if(balance[k] >=0 ){
                                    amount = self.format_currency(currency, balance[k]);
                                }
                                $('#today_bank').append('<li><div val="' + acc_ids[k] + '"id="b_' + acc_ids[k] + '">' + bank_list[k] + ' : ' + amount + '</div></li>');
                            }
                            if (bank_list.length <=0) {
                                $('#today_bank').append('<span>' + self.format_currency(currency, 0.00)  + '</span> <div class="title"></div>')
                            }
                    })
                    rpc.query({
                        model: "hms.dashboard",
                        method: "get_cash_bank_today",

                    }).then(function (result) {
                            var amount = result;
//                            var csh_bnk_list = result['csh_bnk_names'];
//                            var balance = result['balance'];
//                            var acc_ids = result['account_ids'];
//                            for (var k = 0; k < csh_bnk_list.length; k++) {
//
//                            amount = self.format_currency(currency, balance[k]);
//                            }
                            if (amount) {
                                $('#today_cash_bank').append('<span>' + self.format_currency(currency, amount) + '</span> <div class="title"></div>')
                            }
                            else {
                                $('#today_cash_bank').append('<span>' + self.format_currency(currency, 0.00)  + '</span> <div class="title"></div>');
                                }
                    })
                     rpc.query({
                        model: "hms.dashboard",
                        method: "get_total_cash",

                    }).then(function (result) {
                            var cash_list = result['cash_names'];
                            var amount = self.format_currency(currency, 0.00);
                            var balance = result['balance'];
                            var acc_ids = result['account_ids'];
                            for (var k = 0; k < cash_list.length; k++) {
                               if(balance[k] >=0 ){
                                    amount = self.format_currency(currency, balance[k]);
                                }
                                $('#total_cash').append('<li><div val="' + acc_ids[k] + '"id="b_' + acc_ids[k] + '">' + cash_list[k] + ' : ' + amount + '</div></li>');
                            }
                            if (cash_list.length <=0) {
                                $('#total_cash').append('<span>' + self.format_currency(currency, 0.00)  + '</span> <div class="title"></div>')
                            }
                    })
                    rpc.query({
                        model: "hms.dashboard",
                        method: "get_total_bank",

                    }).then(function (result) {
                            var bank_list = result['banks_names'];
                            var amount = self.format_currency(currency, 0.00);
                            var balance = result['balance'];
                            var acc_ids = result['account_ids'];
                            for (var k = 0; k < bank_list.length; k++) {
                                if(balance[k] >=0 ){
                                    amount = self.format_currency(currency, balance[k]);
                                }
                                $('#total_bank').append('<li><div val="' + acc_ids[k] + '"id="b_' + acc_ids[k] + '">' + bank_list[k] + ' : ' + amount + '</div></li>');
                            }
                            if (bank_list.length <=0) {
                                $('#total_bank').append('<span>' + self.format_currency(currency, 0.00)  + '</span> <div class="title"></div>')
                            }
                    })
                    rpc.query({
                        model: "hms.dashboard",
                        method: "get_total_cash_bank",

                    }).then(function (result) {
                            var amount = result ;
//                            var csh_bnk_list = result['csh_bnk_names'];
//                            var balance = result['balance'];
//                            var acc_ids = result['account_ids'];
//                            for (var k = 0; k < csh_bnk_list.length; k++) {
//
//                            amount = self.format_currency(currency, balance);
//                            }
                            if (amount) {
                                $('#total_cash_bank').append('<span>' + self.format_currency(currency, amount) + '</span> <div class="title"></div>')
                            }
                            else {
                                $('#total_cash_bank').append('<span>' + self.format_currency(currency, 0.00) + '</span> <div class="title"></div>');
                                }
                    })
                });
        },
       format_currency: function(currency, amount) {
            if (typeof(amount) != 'number') {
                amount = parseFloat(amount);
            }
            var formatted_value = (amount).toLocaleString(currency.language, {
                minimumFractionDigits: 2
            })
            if (currency.position === "after") {
                return formatted_value += ' ' + currency.symbol;
            } else {
                return currency.symbol + ' ' + formatted_value;
            }
        },
        willStart: function() {
            var self = this;
            self.drpdn_show = false;
            return Promise.all([loadBundle(this), this._super()]);
        },
    });
    core.action_registry.add('cms_finance_dashboard', ActionMenu);

});