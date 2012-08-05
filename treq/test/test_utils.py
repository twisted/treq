from twisted.trial.unittest import TestCase

from treq import util


class TestCaseInsensitiveDict(TestCase):
    def test_len(self):
        d = util.CaseInsensitiveDict({"foo" : 2, "bar" : "Hey"})
        self.assertEqual(len(d), 2)

    def test_iter(self):
        d = util.CaseInsensitiveDict({"foo" : 2, "Bar" : "Hey"})
        self.assertEqual(list(d), ["foo", "bar"])

    def test_getitem(self):
        d = util.CaseInsensitiveDict({"foo" : 2, "bar" : "Hey"})

        self.assertEqual(d["foo"], 2)
        self.assertEqual(d["Foo"], 2)

        self.assertEqual(d["bar"], "Hey")
        self.assertEqual(d["BAR"], "Hey")

    def test_setitem(self):
        d = util.CaseInsensitiveDict()
        d["Foo"] = 12

        self.assertEqual(d["Foo"], 12)
        self.assertEqual(d["foo"], 12)

    def test_delitem(self):
        d = util.CaseInsensitiveDict({"foo" : 2, "bar" : "Hey"})
        del d["Foo"]
        self.assertEqual(d.keys(), ["bar"])

    def test_repr(self):
        c = {"foo" : 2, "Bar" : "Hey"}
        r = repr(util.CaseInsensitiveDict(c))
        self.assertEqual(r, "CaseInsensitiveDict({'foo': 2, 'bar': 'Hey'})")


class TestFindEncoding(TestCase):
    def test_get_encoding_from_content_type(self):
        h = {"Content-Type" : "text/html; charset=UTF-8"}
        headers = util.CaseInsensitiveDict(h)
        self.assertEqual(util.get_encoding_from_headers(headers), "UTF-8")
