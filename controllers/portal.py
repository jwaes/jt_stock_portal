import base64
import logging
from collections import OrderedDict
from datetime import datetime

from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request, Response
from odoo.tools import image_process
from odoo.tools.translate import _
from odoo.addons.portal.controllers import portal
from odoo.addons.portal.controllers.portal import pager as portal_pager, get_records_pager

_logger = logging.getLogger(__name__)

class CustomerPortal(portal.CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)

        partner = request.env.user.partner_id

        StockPicking = request.env['stock.picking']

        if 'transfer_count'  in counters:
            values['transfer_count'] = StockPicking.sudo().search_count(self._prepare_stockpicking_domain(partner)) \
                if StockPicking.check_access_rights('read', raise_exception=False) else 0

        return values

    def _prepare_stockpicking_domain(self, partner):
        _logger.info("commercial partner: %s", partner.commercial_partner_id.name)
        return [
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
        ]

    def _get_stockpicking_searchbar_sortings(self):
        return {
            'date': {'label': _('Sheduled Date'), 'transfer': 'scheduled_date  desc'},
            # 'name': {'label': _('Reference'), 'order': 'name'},
            'stage': {'label': _('Stage'), 'transfer': 'state'},
        }

    def _stockpicking_get_page_view_values(self, transfer, access_token, **kwargs):
        #
        def resize_to_48(b64source):
            if not b64source:
                b64source = base64.b64encode(request.env['ir.http']._placeholder())
            return image_process(b64source, size=(48, 48))

        values = {
            'transfer': transfer,
            'resize_to_48': resize_to_48,
            'report_type': 'html',
        }
        # if order.state in ('sent'):
        #     history = 'my_rfqs_history'
        # else:
        #     history = 'my_purchases_history'
        history = 'my_transfers_history'
        return self._get_page_view_values(transfer, access_token, values, history, False, **kwargs)        


    @http.route(['/my/transfers', '/my/transfers/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_transfers(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):        
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        StockPicking = request.env['stock.picking']

        domain = self._prepare_stockpicking_domain(partner)

        searchbar_sortings = self._get_stockpicking_searchbar_sortings()

        searchbar_filters =  {
                'all': {'label': _('All'), 'domain': [('state', 'in', ['done', 'cancel', 'draft', 'waiting', 'confirmed', 'assigned'])]},
                'preparation': {'label': _('Preparation'), 'domain': [('state', 'in', ['draft', 'waiting', 'confirmed', 'assigned'])]},
                'cancel': {'label': _('Cancelled'), 'domain': [('state', '=', 'cancel')]},
                'done': {'label': _('Done'), 'domain': [('state', '=', 'done')]},
            }

        # default sortby order
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['transfer']

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]        


        product_variant = kw.get('product_variant')

        if searchbar_filters:
            # default filter
            if not filterby:
                filterby = 'preparation'
            elif filterby == 'product_variant' and product_variant:
                searchbar_filters.update({
                    filterby: {'label': 'Product variant', 'domain': [('move_line_ids.product_id.id', '=', product_variant), 
                        ('state', 'in', ['draft', 'waiting', 'confirmed', 'assigned'])]},
                })

            domain += searchbar_filters[filterby]['domain']

        # count for pager
        transfer_count = StockPicking.sudo().search_count(domain)

        # make pager
        pager = portal_pager(
            url="/my/transfers",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby},
            total=transfer_count,
            page=page,
            step=self._items_per_page
        )

        # search the count to display, according to the pager data
        transfers = StockPicking.sudo().search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_transfers_history'] = transfers.ids[:100]

        values.update({
            'date': date_begin,
            'transfers': transfers.sudo(),
            'page_name': 'transfers',
            'pager': pager,
            'default_url': '/my/transfers',
            'searchbar_sortings': searchbar_sortings,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
            'sortby': sortby,
        })
        return request.render("jt_stock_portal.portal_my_transfers", values)    

    @http.route(['/my/transfers/<int:transfer_id>'], type='http', auth="public", website=True)
    def portal_transfer_page(self, transfer_id, report_type=None, access_token=None, message=False, download=False, **kw):
        try:
            transfer_id = self._document_check_access('stock.picking', transfer_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        # report_type = kw.get('report_type')
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=transfer_id, report_type=report_type, report_ref='stock.action_report_delivery', download=download)

        # confirm_type = kw.get('confirm')
        # if confirm_type == 'reminder':
        #     order_sudo.confirm_reminder_mail(kw.get('confirmed_date'))
        # if confirm_type == 'reception':
        #     order_sudo._confirm_reception_mail()

        values = self._stockpicking_get_page_view_values(transfer_id, access_token, **kw)
        values.update({
            'commercial_partner': request.env.user.partner_id.commercial_partner_id,
        })            
        # update_date = kw.get('update')
        # if order_sudo.company_id:
        #     values['res_company'] = order_sudo.company_id
        # if update_date == 'True':
        #     return request.render("purchase.portal_my_purchase_order_update_date", values)

        history = request.session.get('my_transfers_history', [])
        values.update(get_records_pager(history, transfer_id))     
        return request.render("jt_stock_portal.portal_my_transfer", values)



    @http.route(['/my/purchase', '/my/purchase/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_purchase_orders(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        return self._render_portal(
            "purchase.portal_my_purchase_orders",
            page, date_begin, date_end, sortby, filterby,
            [],
            {
                'all': {'label': _('All'), 'domain': [('state', 'in', ['purchase', 'done', 'cancel'])]},
                'purchase': {'label': _('Purchase Order'), 'domain': [('state', '=', 'purchase')]},
                'cancel': {'label': _('Cancelled'), 'domain': [('state', '=', 'cancel')]},
                # 'done': {'label': _('Locked'), 'domain': [('state', '=', 'done')]},
                'notshipped': {'label': _('Not Shipped'), 'domain': [('is_shipped', '=', False)]},
            },
            'notshipped',
            "/my/purchase",
            'my_purchases_history',
            'purchase',
            'orders'
        )            
