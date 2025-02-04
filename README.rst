lscl -- Logstash configuration language handling
================================================

lscl is a Python module for parsing and rendering Logstash_ configurations
in its own language, named LSCL for "LogStash Configuration Language".

The project is present at the following locations:

* `Official website and documentation at
  lscl.touhey.pro <lscl website_>`_;
* `lscl repository on Gitlab <lscl on Gitlab_>`_;
* `lscl project on PyPI <lscl on PyPI_>`_.

As described in `Reading Logstash configurations`_ and `Rendering
Logstash configurations`_, you can use this module to create, parse, update
and render Logstash pipelines. Here is an example where lscl is used to add
an ``add_field`` operation on an existing pipeline:

.. code-block:: python

    from lscl.lang import LsclAttribute, LsclBlock
    from lscl.parser import parse_lscl
    from lscl.renderer import render_as_lscl


    SOURCE = """
    input {
        stdin { }
    }
    filter {
        dissect {
            mapping => {
                "message" => "[%{ts}] %{message}"
            }
        }
    }
    output {
        elasticsearch { codec => rubydebug }
    }
    """

    content = parse_lscl(SOURCE)

    # Find the 'filter' block at top level.
    # If the block is not found, create it.
    for el in content:
        if isinstance(el, LsclBlock) and el.name == "filter":
            break
    else:
        el = LsclBlock(name="filter")
        content.append(el)

    # Add the add_field filter.
    el.content.append(
        LsclBlock(
            name="mutate",
            content=[
                LsclAttribute(name="add_field", content={"mytag": "myvalue"}),
            ],
        )
    )

    print(render_as_lscl(content), end="")

The script will output the following:

.. code-block:: text

    input {
      stdin {}
    }
    filter {
      dissect {
        mapping => {
          message => "[%{ts}] %{message}"
        }
      }
      mutate {
        add_field => {
          mytag => myvalue
        }
      }
    }
    output {
      elasticsearch {
        codec => rubydebug
      }
    }

.. _Logstash: https://www.elastic.co/fr/logstash
.. _lscl website: https://lscl.touhey.pro/
.. _lscl on Gitlab: https://gitlab.com/kaquel/lscl
.. _lscl on PyPI: https://pypi.org/project/lscl
.. _Reading Logstash configurations:
    https://lscl.touhey.pro/developer-guides/read.html
.. _Rendering Logstash configurations:
    https://lscl.touhey.pro/developer-guides/render.html
