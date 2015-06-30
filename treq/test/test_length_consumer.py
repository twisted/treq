# coding: utf-8
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

from twisted.trial import unittest

from treq.multipart import _LengthConsumer


class LengthConsumerTestCase(unittest.TestCase):

    """
    Tests for the _LengthConsumer, an L{IConsumer} which is used to compute
    the length of a produced content.
    """
    def test_LengthConsumerUnderstandsLongs(self):
        """
        When a long is wrote, _LengthConsumer use it to update its internal
        count
        """
        consumer = _LengthConsumer()
        self.assertEqual(consumer.length, 0)
        consumer.write(1L)
        self.assertEqual(consumer.length, 1)
        consumer.write(2147483647)
        self.assertEqual(consumer.length, 2147483648L)
