Reading Logstash configurations
===============================

There are multiple ways to use the module to actually read a Logstash
configuration: decode the configuration file directly, and evaluate the
configuration file in order to decode specific elements of the configuration.

Only decode a Logstash configuration
------------------------------------

.. py:currentmodule:: lscl.parser

In order to decode a Logstash configuration, you can use :py:func:`parse_lscl`:

.. code-block:: python

    from lscl.parser import parse_lscl

    with open("/path/to/logstash.yaml") as fp:
        parsed_result = parse_lscl(fp.read())

.. py:currentmodule:: lscl.lang

The result will be expressed using a list of :py:class:`LsclBlock`,
:py:class:`LsclData` and :py:class:`LsclConditions` you can explore
recursively.

Decode Logstash filters
-----------------------

.. py:currentmodule:: lscl.filters

In order to decode raw Logstash filters, you can use
:py:func:`parse_logstash_filters`:

.. code-block:: python

    from lscl.filters import parse_logstash_filters

    with open("/path/to/logstash.yaml") as fp:
        parsed_result = parse_logstash_filters(fp.read())

The result will be expressed using a list of :py:class:`LogstashFilter`
and :py:class:`LogstashFilterBranching` you can explore recursively.
