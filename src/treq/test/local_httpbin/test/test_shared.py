"""
Tests for :py:mod:`treq.test.local_httpbin.shared`
"""
from twisted.trial import unittest

from .. import shared


class HTTPBinDescriptionTests(unittest.SynchronousTestCase):
    """
    Tests for :py:class:`shared._HTTPBinDescription`
    """

    def test_round_trip(self):
        """
        :py:class:`shared._HTTPBinDescription.from_json_bytes` can
        deserialize the output of
        :py:class:`shared._HTTPBinDescription.to_json_bytes`
        """
        original = shared._HTTPBinDescription(host="host", port=123)
        round_tripped = shared._HTTPBinDescription.from_json_bytes(
            original.to_json_bytes(),
        )

        self.assertEqual(original, round_tripped)

    def test_round_trip_cacert(self):
        """
        :py:class:`shared._HTTPBinDescription.from_json_bytes` can
        deserialize the output of
        :py:class:`shared._HTTPBinDescription.to_json_bytes` when
        ``cacert`` is set.
        """
        original = shared._HTTPBinDescription(host="host",
                                              port=123,
                                              cacert='cacert')
        round_tripped = shared._HTTPBinDescription.from_json_bytes(
            original.to_json_bytes(),
        )

        self.assertEqual(original, round_tripped)
