===============================
justgiving_totaliser
===============================


.. image:: https://img.shields.io/travis/homsar/justgiving_totaliser.svg
        :target: https://travis-ci.org/homsar/justgiving_totaliser


Totaliser for JustGiving pages. Incredibly fragile! No idea how it will behave if your locale isn't English, for example.


Features
--------

* Scrapes a JustGiving page
* Displays a simple bar showing the progress towards the total
* Also shows the most recent donor's comment, and subsequent recent donations
  - This is capped at 5, because that's all JustGiving shows without pressing "show more", and untangling that would need me to switch to Selenium or understand GraphQL

Credits
---------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
