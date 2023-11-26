===============================
justgiving_totaliser
===============================

Totaliser for JustGiving pages. Incredibly fragile! No idea how it will behave if your locale isn't English, for example.


Features
--------

* Scrapes a JustGiving page
* Displays windows showing:
  - a simple bar showing the progress towards the total
  - the most recent donor's name, donation amount and comment
  - recent donors' names and donation amounts in a list
  - recent donors' names, donation amounts, and comments in a marquee


Limitations
-----------

* Only works for JustGiving "pages", not for "campaigns", "crowdfundings", etc.


Installation
------------

::

   pip install git+https://github.com/homsar/justgiving_totaliser.git#egg=usgiving_totaliser

Usage
-----

To start the app::

  python -m justgiving_totaliser

Setting up:

1. Specify your JustGiving page via `Options > Set URL`. Paste in your URL and click OK.
2. Set the base length of your event via `Time > Set target length`
3. Set the event start time:

   * If you are starting the event live, use `Time > Start event NOW!` to start the countdown
   * Otherwise, set the start time via `Time > Set event start time`

Other things you can do:

* If you need to stop an announcement, hit `Audio > Stop announcement`, or press `Ctrl+K` (`Cmd+K` on Mac)
* If you are adding bonus time for hitting donation targets, specify these via `Time > Set bonuses`. (These stack, so if you want to add an extra hour at £250 and £500, then set `1` for each of those values, not `2` at `£500`!)
* If you need to manually add extra time for any reason (other than preset bonuses), this can be done via `Time > Add extra time`. (This can also be negative if you need to subtract time.)
* You can re-trigger announcements (e.g. if a good one got played while the audio was turned down) via `Audio > Play previous announcements`
* You can force an extra hour to be announced via `Audio > Force extra hour announcement`
* You can control the colours of almost everything via the `Colours` menu
* Depending on your OBS setup, `Options > Hide title bars` might help
* If you or your audience are impatient or hard of reading, look at `Options > Set marquee speed`
* If you have a vast amount of or not very much space on your stream layout, use `Options > Set number of donations`
* If you are impatient, you can use `Options > Set refresh time` to potentially get updates slightly faster

Credits
---------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
