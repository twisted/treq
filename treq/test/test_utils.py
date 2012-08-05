from twisted.trial.unittest import TestCase

from treq.util import CaseInsensitiveDict


class TestCaseInsensitiveDict(TestCase):
    def test_len(self):
        d = CaseInsensitiveDict({"foo" : 2, "bar" : "Hey"})
        self.assertEqual(len(d), 2)

    def test_iter(self):
        d = CaseInsensitiveDict({"foo" : 2, "Bar" : "Hey"})
        self.assertEqual(list(d), ["foo", "bar"])

    def test_getitem(self):
        d = CaseInsensitiveDict({"foo" : 2, "bar" : "Hey"})

        self.assertEqual(d["foo"], 2)
        self.assertEqual(d["Foo"], 2)

        self.assertEqual(d["bar"], "Hey")
        self.assertEqual(d["BAR"], "Hey")

    def test_setitem(self):
        d = CaseInsensitiveDict()
        d["Foo"] = 12

        self.assertEqual(d["Foo"], 12)
        self.assertEqual(d["foo"], 12)

    def test_delitem(self):
        d = CaseInsensitiveDict({"foo" : 2, "bar" : "Hey"})
        del d["Foo"]
        self.assertEqual(d.keys(), ["bar"])

    def test_repr(self):
        c = {"foo" : 2, "Bar" : "Hey"}
        r = repr(CaseInsensitiveDict(c))
        self.assertEqual(r, "CaseInsensitiveDict({'foo': 2, 'bar': 'Hey'})")
