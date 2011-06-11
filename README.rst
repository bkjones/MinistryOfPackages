What is MinistryOfPackages?
=============================

A simple Python package index server implementation, meant for internal use
(at least for now). It requires Tornado (http://www.tornadoweb.org), and
it's tested with pip and Python 2.7 It is not tested with easy_install, and
easy_install support is not a near-term goal or priority (Please use pip)

What Works Now?
===================

Right now, MinistryOfPackages is usable for simple use cases: 

1. It has DirectoryListing support, and that's completely generic. It's
   meant to be used by command line tools, but the browser presentation
   works -- it just doesn't have all the fancy icons :)

2. You can do, for example, 'python setup.py sdist upload -r
   http://localhost:8080/dist', and then leverage the directory listing
   capability to go to http://localhost/packages and browse to confirm your
   package made it into the repository. 

3. You can 'pip install -i http://localhost:8080 <pkg>' on the package you
   uploaded in point 2 above.

These features still need more testing and a little polish, but they
generally work.

What's Up Next?
====================

1. Completion of a data model (using Redis) to support
   more of the CLI and browser UI features (like 'register').

2. Fleshing out a proper browser interface. 

What's After That?
====================

1. Proxying requests to PyPI for easy_install, so MinistryOfPackages can be
   your primary index server for everything.

2. Package caching. 

3. PyPI Mirroring (this can technically be done now, but it's not a good
   solution as it stands). 

Feature requests, new ideas, and pull requests are welcome. 

Why are you doing this?
=======================

I'm after a few different things with this project: 

1.  I want something that's blindingly easy to deploy. I don't want to muck
    with WSGI, CGI, FCGI, whatever. I want to write code and run it, and
    have something that works. Having used Tornado for numerous other
    projects (some 'web scale'), I can tell you it works :) 

2.  I want some enterprise-y features like proxy requests and package
    caching.  Those will come later, but I didn't want to start this using a
    huge multi-headed framework because I want to get to them sooner than
    later :)

3.  I want to understand distutils, Python package distribution, and all
    that stuff better.

