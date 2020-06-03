# -*- coding: utf-8 -*-
# !/usr/bin/env python
"""
-------------------------------------------------
   File Name：     ProxyManager.py
   Description :
   Author :       JHao
   date：          2016/12/3
-------------------------------------------------
   Change Activity:
                   2016/12/3:
-------------------------------------------------
"""
__author__ = 'JHao'

import random

from ProxyHelper import Proxy
from DB.DbClient import DbClient
from Config.ConfigGetter import config
from Util.LogHandler import LogHandler
from Util.utilFunction import verifyProxyFormat
from ProxyGetter.getFreeProxy import GetFreeProxy
from datetime import datetime, timedelta


class ProxyManager(object):
    """
    ProxyManager
    """

    def __init__(self):
        self.db = DbClient()
        self.raw_proxy_queue = 'raw_proxy'
        self.log = LogHandler('proxy_manager')
        self.useful_proxy_queue = 'useful_proxy'

    def fetch(self):
        """
        fetch proxy into db by ProxyGetter
        :return:
        """
        self.db.changeTable(self.raw_proxy_queue)
        proxy_set = set()
        self.log.info("ProxyFetch : start")
        for proxyGetter in config.proxy_getter_functions:
            self.log.info("ProxyFetch - {func}: start".format(func=proxyGetter))
            try:
                for proxy in getattr(GetFreeProxy, proxyGetter.strip())():
                    proxy = proxy.strip()

                    if not proxy or not verifyProxyFormat(proxy):
                        self.log.error('ProxyFetch - {func}: '
                                       '{proxy} illegal'.format(func=proxyGetter, proxy=proxy.ljust(20)))
                        continue
                    elif proxy in proxy_set:
                        self.log.info('ProxyFetch - {func}: '
                                      '{proxy} exist'.format(func=proxyGetter, proxy=proxy.ljust(20)))
                        continue
                    else:
                        self.log.info('ProxyFetch - {func}: '
                                      '{proxy} success'.format(func=proxyGetter, proxy=proxy.ljust(20)))
                        self.db.put(Proxy(proxy, source=proxyGetter))
                        proxy_set.add(proxy)
            except Exception as e:
                self.log.error("ProxyFetch - {func}: error".format(func=proxyGetter))
                self.log.error(str(e))

    def get(self):
        """
        return a useful proxy
        :return:
        """
        self.db.changeTable(self.useful_proxy_queue)
        item_list = self.db.getAll()
        if item_list:
            random_choice = random.choice(item_list)
            return Proxy.newProxyFromJson(random_choice)
        return None

    def delete(self, proxy_str):
        """
        delete proxy from pool
        :param proxy_str:
        :return:
        """
        self.db.changeTable(self.useful_proxy_queue)
        self.db.delete(proxy_str)

    def getAll(self):
        """
        get all proxy from pool as list
        :return:
        """
        self.db.changeTable(self.useful_proxy_queue)
        item_list = self.db.getAll()
        return [Proxy.newProxyFromJson(_) for _ in item_list]

    def getNumber(self):
        self.db.changeTable(self.raw_proxy_queue)
        total_raw_proxy = self.db.getNumber()
        self.db.changeTable(self.useful_proxy_queue)
        total_useful_queue = self.db.getNumber()
        return {'raw_proxy': total_raw_proxy, 'useful_proxy': total_useful_queue}


    def getAllByName(self, name):
        all_proxies = self.getAll()

        self.db.changeTable(self.useful_proxy_queue + '_fail_' + name)
        fail_list = self.db.getAll()
        fail_proxies = [Proxy.newProxyFromJson(_) for _ in fail_list]

        # todo: 优化
        filter_proxies = []
        for proxy in all_proxies:
            isFailed = False
            for failed in fail_proxies:
                if failed.proxy == proxy.proxy:
                    failed_date = datetime.strptime(failed.last_time, "%Y-%m-%d %H:%M:%S")
                    if failed_date + timedelta(hours=24) > datetime.now():
                        isFailed = True
                    break
            if not isFailed:
                filter_proxies.append(proxy)

        return filter_proxies

    def deleteByName(self, name, proxy):
        failed_proxy = Proxy(proxy=proxy, last_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.db.changeTable(self.useful_proxy_queue + '_fail_' + name)
        self.db.put(failed_proxy)

    def getByName(self, name):
        proxies = self.getAllByName(name)
        if proxies:
            return random.choice(proxies)
        return None

if __name__ == '__main__':
    pp = ProxyManager()
    pp.fetch()
