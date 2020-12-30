from django.db import models
from django.utils.translation import ugettext_lazy as _


class NamadDailyStat(models.Model):
    created_time = models.DateTimeField(_('created time'), auto_now_add=True)
    tmax = models.BigIntegerField(_("tmax"))
    tmin = models.BigIntegerField(_("tmin"))
    stock_number = models.BigIntegerField(_("stock_number"))
    base_volume = models.BigIntegerField(_("base volume"))
    floating_stock = models.FloatField(_("floating stock"))
    total_transaction_average = models.FloatField(_("total transaction average"))
    eps = models.IntegerField(_('EPS'), default=0)
    sector_pe = models.FloatField(_("Sector PE"), blank=True, null=True)

    namad = models.ForeignKey('namads.Namad', on_delete=models.CASCADE, verbose_name=_('namad'), related_name='daily_stats')

    class Meta:
        db_table = 'tsetmc_namaddailystats'


class NamadStat(models.Model):
    created_time = models.DateTimeField(_('Created Time'), auto_now_add=True)
    checksum_time = models.TimeField(_("Checksum Time"))

    status = models.CharField(_("Status"), max_length=10)
    pl = models.IntegerField(_("pl"))
    pc = models.IntegerField(_("pc"))
    pf = models.IntegerField(_("pf"))
    py = models.IntegerField(_("py"))
    pmax = models.IntegerField(_("pmax"))
    pmin = models.IntegerField(_("pmin"))
    tno = models.IntegerField(_("pmin"))
    tvol = models.IntegerField(_("tvol"))
    tval = models.BigIntegerField(_("tval"))
    buy_i_volume = models.IntegerField(_("Buy I Volume"))
    buy_n_volume = models.IntegerField(_("Buy N Volume"))
    sell_i_volume = models.IntegerField(_("Sell I Volume"))
    sell_n_volume = models.IntegerField(_("Sell N Volume"))
    buy_counti = models.IntegerField(_("Buy CountI"))
    buy_countn = models.IntegerField(_("Buy CountN"))
    sell_counti = models.IntegerField(_("Sell CountI"))
    sell_countn = models.IntegerField(_("Sell CountN"))
    mv = models.BigIntegerField(_("mv"))
    plc = models.IntegerField(_("plc"))
    plp = models.FloatField(_("plp"))
    pcc = models.IntegerField(_("pcc"))
    pcp = models.FloatField(_("pcp"))
    tmax = models.BigIntegerField(_("tmax"))
    tmin = models.BigIntegerField(_("tmin"))
    floating_stock = models.FloatField(_("floating stock"))
    total_transaction_average = models.FloatField(_("total transaction average"))

    stock_number = models.BigIntegerField(_("stock_number"))
    base_volume = models.BigIntegerField(_("base volume"))

    zd1 = models.IntegerField(_("zd1"))
    qd1 = models.IntegerField(_("qd1"))
    pd1 = models.IntegerField(_("pd1"))
    po1 = models.IntegerField(_("po1"))
    qo1 = models.IntegerField(_("qo1"))
    zo1 = models.IntegerField(_("zo1"))
    zd2 = models.IntegerField(_("zd1"))
    qd2 = models.IntegerField(_("qd2"))
    pd2 = models.IntegerField(_("pd2"))
    po2 = models.IntegerField(_("po2"))
    qo2 = models.IntegerField(_("qo2"))
    zo2 = models.IntegerField(_("zo2"))
    zd3 = models.IntegerField(_("zd3"))
    qd3 = models.IntegerField(_("qd3"))
    pd3 = models.IntegerField(_("pd3"))
    po3 = models.IntegerField(_("po3"))
    qo3 = models.IntegerField(_("qo3"))
    zo3 = models.IntegerField(_("zo3"))

    namad = models.ForeignKey('namads.Namad', on_delete=models.CASCADE, verbose_name=_('namad'), related_name='stats')

    class Meta:
        db_table = 'tsetmc_namadstats'

    def __str__(self):
        return self.namad.name


class NamadHistory(models.Model):
    created_time = models.DateTimeField(_('Created Time'), auto_now_add=True)
    stat_date = models.DateField(_("stat date"))

    status = models.CharField(_("Status"), max_length=10)
    pl = models.IntegerField(_("pl"))
    pc = models.IntegerField(_("pc"))
    pf = models.IntegerField(_("pf"))
    py = models.IntegerField(_("py"))
    pmax = models.IntegerField(_("pmax"))
    pmin = models.IntegerField(_("pmin"))
    tno = models.IntegerField(_("pmin"))
    tvol = models.IntegerField(_("tvol"))
    tval = models.BigIntegerField(_("tval"))
    buy_i_volume = models.IntegerField(_("Buy I Volume"))
    buy_n_volume = models.IntegerField(_("Buy N Volume"))
    sell_i_volume = models.IntegerField(_("Sell I Volume"))
    sell_n_volume = models.IntegerField(_("Sell N Volume"))
    buy_counti = models.IntegerField(_("Buy CountI"))
    buy_countn = models.IntegerField(_("Buy CountN"))
    sell_counti = models.IntegerField(_("Sell CountI"))
    sell_countn = models.IntegerField(_("Sell CountN"))
    mv = models.BigIntegerField(_("mv"))
    plc = models.IntegerField(_("plc"))
    plp = models.FloatField(_("plp"))
    pcc = models.IntegerField(_("pcc"))
    pcp = models.FloatField(_("pcp"))
    tmax = models.BigIntegerField(_("tmax"))
    tmin = models.BigIntegerField(_("tmin"))
    floating_stock = models.FloatField(_("floating stock"))
    total_transaction_average = models.FloatField(_("total transaction average"))

    b_closed = models.JSONField(blank=True, default=dict)
    a_closed = models.JSONField(blank=True, default=dict)

    namad = models.ForeignKey('namads.Namad', on_delete=models.CASCADE, verbose_name=_('namad'), related_name='histories')

    class Meta:
        db_table = 'tsetmc_namadhistories'
        verbose_name = _("Namad History")
        verbose_name_plural = _("Namad Histories")
        constraints = [
            models.UniqueConstraint(fields=['namad', 'stat_date'], name='Unique namad_stat_date')
        ]
