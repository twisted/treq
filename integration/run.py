"""This is a runner for treq integration tests against webzoo.

It scans the active images of webzoo in docker and executes the same
tests against each one of those.

"""
import subprocess
import re

RE_MAPPING = re.compile(r"(\d+)->\d")


def get_image_and_port(string):
    if "webzoo" in string:
        values = string.split()
        image, mapping = values[1], values[-1]
        m = RE_MAPPING.search(mapping)
        if m:
            return image, m.group(1)
    return None, None


def images():
    out = subprocess.check_output("docker ps", shell=True)
    for process in out.splitlines():
        image, port = get_image_and_port(process)
        if port:
            yield image, port


for image, port in images():
    print "-"*100
    print "Testing ", image, "at", port
    print "-"*100
    subprocess.call(
        "TREQ_PORT={} trial test_treq.py".format(port), shell=True)
