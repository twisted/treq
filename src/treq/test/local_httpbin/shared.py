"""
Things shared between the ``httpbin`` child and parent processes
"""
import attr
import json


@attr.s
class _HTTPBinDescription(object):
    """
    Describe an ``httpbin`` process.

    :param host: The host on which the process listens.
    :type host: :py:class:`str`

    :param port: The port on which the process listens.
    :type port: :py:class:`int`

    :param cacert: (optional) The PEM-encoded certificate authority's
        certificate.  The calling process' treq must trust this when
        running HTTPS tests.
    :type cacert: :py:class:`bytes` or :py:class:`None`
    """
    host = attr.ib()
    port = attr.ib()
    cacert = attr.ib(default=None)

    @classmethod
    def from_json_bytes(cls, json_data):
        """
        Deserialize an instance from JSON bytes.
        """
        return cls(**json.loads(json_data.decode('ascii')))

    def to_json_bytes(self):
        """
        Serialize an instance from JSON bytes.
        """
        return json.dumps(attr.asdict(self), sort_keys=True).encode('ascii')
