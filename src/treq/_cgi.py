# flake8: noqa: E501
#
# The contents of this file were vendored from cpython.git Lib/cgi.py
# commit 60edc70a9374f1cc6ecff5974e438d58fec29985 [1].
#
# Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
# 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023 Python Software Foundation;
# All Rights Reserved
#
# Subject to these license terms (from cpython.git LICENSE line 73) [2]:
#
#     PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2
#     --------------------------------------------
#
#     1. This LICENSE AGREEMENT is between the Python Software Foundation
#     ("PSF"), and the Individual or Organization ("Licensee") accessing and
#     otherwise using this software ("Python") in source or binary form and
#     its associated documentation.
#
#     2. Subject to the terms and conditions of this License Agreement, PSF hereby
#     grants Licensee a nonexclusive, royalty-free, world-wide license to reproduce,
#     analyze, test, perform and/or display publicly, prepare derivative works,
#     distribute, and otherwise use Python alone or in any derivative version,
#     provided, however, that PSF's License Agreement and PSF's notice of copyright,
#     i.e., "Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
#     2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023 Python Software Foundation;
#     All Rights Reserved" are retained in Python alone or in any derivative version
#     prepared by Licensee.
#
#     3. In the event Licensee prepares a derivative work that is based on
#     or incorporates Python or any part thereof, and wants to make
#     the derivative work available to others as provided herein, then
#     Licensee hereby agrees to include in any such work a brief summary of
#     the changes made to Python.
#
#     4. PSF is making Python available to Licensee on an "AS IS"
#     basis.  PSF MAKES NO REPRESENTATIONS OR WARRANTIES, EXPRESS OR
#     IMPLIED.  BY WAY OF EXAMPLE, BUT NOT LIMITATION, PSF MAKES NO AND
#     DISCLAIMS ANY REPRESENTATION OR WARRANTY OF MERCHANTABILITY OR FITNESS
#     FOR ANY PARTICULAR PURPOSE OR THAT THE USE OF PYTHON WILL NOT
#     INFRINGE ANY THIRD PARTY RIGHTS.
#
#     5. PSF SHALL NOT BE LIABLE TO LICENSEE OR ANY OTHER USERS OF PYTHON
#     FOR ANY INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES OR LOSS AS
#     A RESULT OF MODIFYING, DISTRIBUTING, OR OTHERWISE USING PYTHON,
#     OR ANY DERIVATIVE THEREOF, EVEN IF ADVISED OF THE POSSIBILITY THEREOF.
#
#     6. This License Agreement will automatically terminate upon a material
#     breach of its terms and conditions.
#
#     7. Nothing in this License Agreement shall be deemed to create any
#     relationship of agency, partnership, or joint venture between PSF and
#     Licensee.  This License Agreement does not grant permission to use PSF
#     trademarks or trade name in a trademark sense to endorse or promote
#     products or services of Licensee, or any third party.
#
#     8. By copying, installing or otherwise using Python, Licensee
#     agrees to be bound by the terms and conditions of this License
#     Agreement.
#
# [1]: https://github.com/python/cpython/blob/60edc70a9374f1cc6ecff5974e438d58fec29985/Lib/cgi.py
# [2]: https://github.com/python/cpython/blob/60edc70a9374f1cc6ecff5974e438d58fec29985/LICENSE#L73


def _parseparam(s):
    while s[:1] == ';':
        s = s[1:]
        end = s.find(';')
        while end > 0 and (s.count('"', 0, end) - s.count('\\"', 0, end)) % 2:
            end = s.find(';', end + 1)
        if end < 0:
            end = len(s)
        f = s[:end]
        yield f.strip()
        s = s[end:]


def parse_header(line):
    """Parse a Content-type like header.

    Return the main content-type and a dictionary of options.

    """
    parts = _parseparam(';' + line)
    key = parts.__next__()
    pdict = {}
    for p in parts:
        i = p.find('=')
        if i >= 0:
            name = p[:i].strip().lower()
            value = p[i+1:].strip()
            if len(value) >= 2 and value[0] == value[-1] == '"':
                value = value[1:-1]
                value = value.replace('\\\\', '\\').replace('\\"', '"')
            pdict[name] = value
    return key, pdict
