Rendering Logstash configurations
=================================

There are multiple ways to use the module to actually render a Logstash
configuration: render the parsed configuration file directly, and render
more specific resources, such as filters.

.. warning::

    As described in `logstash.yml`_, since the parsing of the pipeline in
    Logstash Configuration Language depends on settings provided aside,
    these settings must be provided aside to the rendering functions:

    * The value from ``config.support_escapes`` in the target environment
      must be mirrored to the ``escapes_supported`` kwarg;
    * The value from ``config.field_reference.escape_style`` in the
      target environment must be mirrored to the
      ``field_reference_escape_style`` kwarg.

    By default, these will be considered undefined in the target environment,
    and as such, are defined to the same default value as in Logstash.

    Note however that the default values (both string and field reference
    escapes being disabled) do not allow all strings and field selectors
    to be represented, and such, you should consider enabling these on
    both your target environment and your usage of lscl.

Render a Logstash configuration
-------------------------------

.. py:currentmodule:: lscl.renderer

In order to render a Logstash configuration represented using
:py:class:`lscl.lang.LsclContent`, using string escape sequences if relevant,
you must use :py:class:`render_as_lscl`:

.. code-block:: python

    from lscl.lang import LsclAttribute, LsclBlock
    from lscl.renderer import render_as_lscl

    content = [
        LsclBlock(
            name="filter",
            content=[
                LsclBlock(
                    name="mutate",
                    content=[
                        LsclAttribute(
                            name="add_field",
                            content={
                                "new.field": "something",
                                "new.field.bis": 42,
                            },
                        )
                    ]
                )
            ],
        )
    ]

    print(render_as_lscl(content, escapes_supported=True))

The example above displays the following:

.. code-block:: text

    filter {
      mutate {
        add_field => {
          "new.field" => something
          "new.field.bis" => 42
        }
      }
    }

Render Logstash filters
-----------------------

.. py:currentmodule:: lscl.filters

In order to render Logstash filters represented using
:py:class:`LogstashFilter` and :py:class:`LogstashFilterBranching`,
using string escape sequences if relevant, you must
use :py:class:`render_logstash_filters`:

.. code-block:: python

    from lscl.filters import LogstashFilter, render_logstash_filters

    filters = [
        LogstashFilter(
            name="mutate",
            config={
                "add_field": {
                    "new.field": "something",
                    "new.field.bis": 42,
                },
            },
        )
    ]

    print(render_logstash_filters(filters, escapes_supported=True))

The example above displays the following:

.. code-block:: text

    mutate {
      add_field => {
        "new.field" => something
        "new.field.bis" => 42
      }
    }

.. _logstash.yml:
    https://www.elastic.co/guide/en/logstash/current/
    logstash-settings-file.html
