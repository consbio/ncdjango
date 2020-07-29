Getting Started
===============

Requirements
------------

* Python 2.7, Python 3.5+
* Django 1.8 - 1.11
* ``trefoil`` 0.3.0 (https://github.com/consbio/trefoil)
* ``numpy`` (http://www.numpy.org)
* ``django-tastypie`` 0.13.x (https://django-tastypie.readthedocs.io)
* ``djangorestframework`` (http://www.django-rest-framework.org)
* ``netCDF4-python`` (http://unidata.github.io/netcdf4-python)
* ``pyproj`` (https://github.com/jswhit/pyproj)
* ``fiona`` (http://toblerity.org/fiona/README.html)
* ``shapely`` (https://pypi.python.org/pypi/Shapely)
* ``ply`` (https://pypi.python.org/pypi/ply)
* ``celery`` (http://www.celeryproject.org)
* ``Pillow`` (https://pypi.python.org/pypi/Pillow)


Installation
------------

Once the dependencies are installed, you can install ncdjango with::

   $ pip install ncdjango

Setup
-----

   1. Create a new Django project if you don't already have one.

   2. Add ``ncdjango``, ``tastypie``, and ``rest_framework`` to your ``INSTALLED_APPS`` setting.

   3. Modify your ``settings.py`` to specify the root location of your datasets:

   .. code-block:: python

      NC_SERVICE_DATA_ROOT = '/var/ncdjango/services/'

   4. Modify your ``settings.py`` to specify the location to store temporary files (uploads):

   .. code-block:: python

      NC_TEMPORARY_FILE_LOCATION = '/tmp'

   5. See :doc:`reference/settings` for additional options.

   6. Add the following to your project's ``urlpatterns``:

   .. code-block:: python

      url(r'^', include('ncdjango.urls'))

   .. note::

      You can modify this URL pattern if you want all the ncdjango and web interface URLs grouped under a common path.


Publishing Services
-------------------

Todo
