import functools
import logging
import os
import random
import socket
import string
import time
import uuid

from six.moves import xrange
from . import unittest

from kafka import KafkaClient
from kafka.common import OffsetRequestPayload

__all__ = [
    'random_string',
    'get_open_port',
    'kafka_versions',
    'KafkaIntegrationTestCase',
    'Timer',
]

def random_string(l):
    return "".join(random.choice(string.ascii_letters) for i in xrange(l))

def kafka_versions(*versions):
    def kafka_versions(func):
        @functools.wraps(func)
        def wrapper(self):
            kafka_version = os.environ.get('KAFKA_VERSION')

            if not kafka_version:
                self.skipTest("no kafka version specified")
            elif 'all' not in versions and kafka_version not in versions:
                self.skipTest("unsupported kafka version")

            return func(self)
        return wrapper
    return kafka_versions

def get_open_port():
    sock = socket.socket()
    sock.bind(("", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port

class KafkaIntegrationTestCase(unittest.TestCase):
    create_client = True
    topic = None
    zk = None
    server = None

    def setUp(self):
        super(KafkaIntegrationTestCase, self).setUp()
        if not os.environ.get('KAFKA_VERSION'):
            return

        if not self.topic:
            topic = "%s-%s" % (self.id()[self.id().rindex(".") + 1:], random_string(10))
            self.topic = topic

        if self.create_client:
            self.client = KafkaClient('%s:%d' % (self.server.host, self.server.port))

        self.client.ensure_topic_exists(self.topic)

        self._messages = {}

    def tearDown(self):
        super(KafkaIntegrationTestCase, self).tearDown()
        if not os.environ.get('KAFKA_VERSION'):
            return

        if self.create_client:
            self.client.close()

    def current_offset(self, topic, partition):
        try:
            offsets, = self.client.send_offset_request([OffsetRequestPayload(topic, partition, -1, 1)])
        except:
            # XXX: We've seen some UnknownErrors here and cant debug w/o server logs
            self.zk.child.dump_logs()
            self.server.child.dump_logs()
            raise
        else:
            return offsets.offsets[0]

    def msgs(self, iterable):
        return [ self.msg(x) for x in iterable ]

    def msg(self, s):
        if s not in self._messages:
            self._messages[s] = '%s-%s-%s' % (s, self.id(), str(uuid.uuid4()))

        return self._messages[s].encode('utf-8')

    def key(self, k):
        return k.encode('utf-8')


class Timer(object):
    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        self.end = time.time()
        self.interval = self.end - self.start

logging.basicConfig(level=logging.DEBUG)
logging.getLogger('test.fixtures').setLevel(logging.ERROR)
logging.getLogger('test.service').setLevel(logging.ERROR)

# kafka.conn debug logging is verbose, disable in tests by default
logging.getLogger('kafka.conn').setLevel(logging.INFO)
