Rendering Lostash configurations
================================

There are multiple ways to use the module to actually render a Logstash
configuration: render the parsed configuration file directly, and render
more specific resources, such as filters.

Render a Logstash configuration
-------------------------------

.. py:currentmodule:: lscl.renderer

In order to render a Logstash configuration represented using
:py:class:`lscl.lang.LsclContent`, you must use :py:class:`render_as_lscl`:

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

    print(render_as_lscl(content))

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
:py:class:`LogstashFilter` and :py:class:`LogstashFilterBranching`, you must
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

    print(render_logstash_filters(filters))

The example above displays the following:

.. code-block:: text

    mutate {
      add_field => {
        "new.field" => something
        "new.field.bis" => 42
      }
    }
