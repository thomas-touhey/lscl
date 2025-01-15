Reading Logstash configurations
===============================

.. py:currentmodule:: lscl.parser

In order to decode a Logstash configuration, you can
use :py:func:`parse_lscl`.

.. warning::

    As described in `logstash.yml`_, the parsing of the pipeline in
    Logstash Configuration Language depends on settings provided aside,
    which means the configuration you want to read has been made for a
    Logstash instance with the following settings:

    * ``config.support_escapes``, for which the value must be mirrored to the
      ``support_escapes`` kwarg;
    * ``config.field_reference.escape_style``, for which the value must be
      mirrored to the ``field_reference_escape_style`` kwarg.

    By default, these are considered undefined in the assumed Logstash
    instance, and as such, are defined to the same default value as
    in Logstash.

An example is the following:

.. code-block:: python

    from lscl.parser import parse_lscl

    with open("/path/to/logstash.yaml") as fp:
        parsed_result = parse_lscl(fp.read())

.. py:currentmodule:: lscl.lang

The result will be expressed using a list of :py:class:`LsclBlock`,
:py:class:`LsclData` and :py:class:`LsclConditions` you can explore
recursively.

.. _logstash.yml:
    https://www.elastic.co/guide/en/logstash/current/
    logstash-settings-file.html
