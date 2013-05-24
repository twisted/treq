#
# Treq Makefile
# ~~~~~~~~~~~~~~~~
# ~: make
#
TEST_OPTIONS = \
	-v

test:
	trial --cover trial/tests/test_multipart.py

clean:
	find -name *pyc -delete
	find -name *py~ -delete
