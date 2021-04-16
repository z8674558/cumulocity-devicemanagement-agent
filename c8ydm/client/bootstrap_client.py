#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import time

import paho.mqtt.client as mqtt


class Bootstrap():
    bootstrapped = False

    def __init__(self, serial, path, configuration):
        self.logger = logging.getLogger(__name__)
        self.serial = serial
        self.configuration = configuration
        self.url = self.configuration.getValue('mqtt', 'url')
        self.port = self.configuration.getValue('mqtt', 'port')
        self.ping = self.configuration.getValue('mqtt', 'ping.interval.seconds')
        self.tls = self.configuration.getBooleanValue('mqtt', 'tls')
        self.cacert = self.configuration.getValue('mqtt', 'cacert')

    def on_connect(self, client, userdata, flags, rc):
        self.logger.debug('Bootstrap connected with result code: ' + str(rc))
        client.subscribe('s/dcr')

    def on_disconnect(self, client, userdata, rc):
        self.logger.debug('Bootstrap disconnected with result code: ' + str(rc))

    def on_messageRegistration(self, client, userdata, msg):
        message = msg.payload.decode('utf-8')
        messageParts = message.split(',')
        self.logger.debug(messageParts)
        if messageParts[0] == '70':

            while not self.bootstrapped:
                try:
                    self.logger.debug('Storing credentials...')
                    self.configuration.writeCredentials(messageParts[1], messageParts[2], messageParts[3])
                    self.logger.debug('Storing credentials successful')
                    client.unsubscribe('s/dcr')
                    self.bootstrapped = True
                except Exception as e:
                    self.logger.debug('Storing credentials failed. Waiting 5 Sec. to retry..')
                    self.logger.exception(e)
                    time.sleep(5)

    def bootstrap(self):
        self.logger.info('Start bootstrap client')

        client = mqtt.Client(client_id=self.serial)
        client.on_message = self.on_messageRegistration
        client.on_connect = self.on_connect
        client.on_disconnect = self.on_disconnect

        credentials = self.configuration.getBootstrapCredentials()
        if self.tls:
             client.tls_set(self.cacert)
        client.username_pw_set(credentials[0] + '/' + credentials[1], credentials[2])
        client.connect(self.url, int(self.port), int(self.ping))

        client.loop_start()
        client.publish('s/ucr')

        while not self.bootstrapped:
            time.sleep(5)
            self.logger.debug('poll credentials')
            client.publish('s/ucr')

        client.on_message = None
        client.on_connect = None
        client.disconnect()
        client.loop_stop()
        client = None
        time.sleep(5)
        self.logger.info('Stop bootstrap client')
