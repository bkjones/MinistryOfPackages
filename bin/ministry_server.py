#!/usr/bin/env python
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# PYTHON BUILTIN MODULES
try:
    import importlib
except ImportError:
    # Python < 2.7
    importlib = None

import logging
import multiprocessing
import optparse
import os
from os.path import dirname, realpath
import signal
import sys
import yaml

# THIRD PARTY MODULES
# Redis will be implemented later & hopefully made optional
# import redis
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

# OUR OWN MODULES
from MinistryOfPackages.core.daemonize import daemonize

__appname__ = 'MinistryOfPackages'
__author__ = 'Brian K. Jones'
__email__ = 'bkjones@gmail.com'
__since__ = '2010-11-18'
__version__ = '0.5.3'

# for tracking tornado processes
children = []


class Application(tornado.web.Application):

    def __init__(self, config):

        # Our main handler list
        handlers = []

        # Loop through the configured request handlers
        logging.debug("RequestHandlers: %s", config['RequestHandlers'])
        for dispatch_def in config['RequestHandlers']:
            for handler, handler_config in dispatch_def.items():
                logging.debug(handler)
                modulename, classname = handler.rsplit('.', 1)
                if importlib:
                    module = importlib.import_module(modulename)
                else:
                    module = __import__(modulename, fromlist=classname)
                handler_class = getattr(module, classname)
                handler_class.whitelist = handler_config.get('whitelist', [])
                url = handler_config['url']
                handlers.append((url, handler_class))

        logging.debug("Handlers collection: %s", handlers)

        # We only pass on config from the Application section of our config
        settings = config['Application']

        # Set the app version from the version setting in this file
        settings['version'] = __version__

        # The base directory for the main application. By default,
        # should be /opt/MinistryOfPackages/
        settings['base_path'] = application_base

        # If we have a static_path
        if 'static_path' in settings:

            # Replace __base_path__ with the path this is running from
            settings['static_path'] = \
                settings['static_path'].replace('__base_path__',
                                                settings['base_path'])

        # If we have a template_path
        if 'template_path' in settings:
            settings['template_path'] = \
                settings['template_path'].replace('__base_path__',
                                                  settings['base_path'])

        # Create our Application for this process
        tornado.web.Application.__init__(self, handlers, **settings)


def runapp(port, config):
    """
    This is responsible for launching the service proper.

    """
    #create the app object that Tornado will run.
    app = Application(config)

    # Remember: runapp is called per port in the YAML config file. We set the
    # app's port explicitly so we can log the port a request came in on.
    app.port = port

    # Run it!
    http_server = tornado.httpserver.HTTPServer(app,
                      xheaders=config['HTTPServer']['xheaders'],
                      no_keep_alive=config['HTTPServer']['no_keep_alive'])

    http_server.listen(port)

    try:
        main_loop = tornado.ioloop.IOLoop.instance()
        logging.debug("MAIN IOLOOP: %s", main_loop)
        main_loop.start()
    except KeyboardInterrupt:
        shutdown()
    except Exception as out:
        logging.error(out)
        shutdown()


def shutdown():
    logging.debug('%s: shutting down' % __appname__)
    for child in children:
        try:
            if child.is_alive():
                logging.debug("%s: Terminating child: %s" %
                              (__appname__, child.name))
                child.terminate()
        except AssertionError:
            logging.error('%s: Dead child encountered' % __appname__)

    logging.debug('%s: shutdown complete' % __appname__)
    sys.exit(0)


def do_logging(config, options):
    if options.foreground:
        #logging.basicConfig(format=config['format'],
        #    filename=os.path.join(config['directory'], config['filename']),
        #    level=logging.DEBUG)
        logging.basicConfig(format=config['format'],
                            level=logging.DEBUG)
        #if config['HTTPServer']['debug']:
        #    logging.getLogger().setLevel(logging.DEBUG)
        return
    else:
        logging_levels = {'debug': logging.DEBUG,
                          'error': logging.ERROR,
                          'critical': logging.CRITICAL,
                          'info': logging.INFO,
                          'fatal': logging.FATAL}
        # Pass in our logging config
        logging.basicConfig(format=config['format'],
                            level=logging_levels[config['level']],
                            filename=os.path.join(config['directory'],
                                                  config['filename']))
        logging.info('Log level set to %s' % config['level'])

        # If we have supported handler
        if 'handler' in config.keys():

            # If we want to syslog
            if config['handler'] == 'syslog':

                facility = config['syslog']['facility']
                import logging.handlers as handlers

                # If we didn't type in the facility name
                if facility in handlers.SysLogHandler.facility_names.keys():

                    # Create the syslog handler
                    syslog = handlers.SysLogHandler(
                        address=config['syslog']['address'],
                        facility =
                            handlers.SysLogHandler.facility_names[facility])

                    # Get the default logger
                    default_logger = logging.getLogger('')

                    # Add the handler
                    default_logger.addHandler(syslog)

                    # Remove the default stream handler
                    for handler in default_logger.handlers:
                        if isinstance(handler, logging.StreamHandler):
                            default_logger.removeHandler(handler)

                else:
                    logging.error('%s: Invalid SysLog facility name',
                        'specified, syslog logging aborted' % __appname__)


def do_options():
    """
    We use optparse for this even though Tornado provides its own optparse-ish
    mechanism. Tornado's option parsing isn't as flexible or robust. It's more
    for simple apps. For example, it doesn't to my knowledge let you specify
    both '-c' and '--config' for the same option, and it doesn't have
    different actions like 'store_true' or flexible variable assignments like
    using optparse's 'destination'.

    """
    usage = "usage: %prog -c <configfile> [options]"
    version_string = "%%prog %s" % __version__
    description = "A PyPI-like service intended for use behind a firewall."

    parser = optparse.OptionParser(usage=usage,
                                   version=version_string,
                                   description=description)

    parser.add_option("-c", "--config",
                      action="store", dest="config",
                      help="Specify the configuration file for use")

    parser.add_option("-u", "--user",
                      action="store", dest="user", default=os.geteuid(),
                      help="Specify the numeric user ID to run as")

    parser.add_option("-p", "--pidfile",
                        action="store", dest="pidfile",
                        default="/tmp/subzero.pid",
                        help="Specify path to pidfile.")

    parser.add_option("-f", "--foreground",
        action="store_true", dest="foreground", default=False,
        help="Run interactively in console for debugging purposes")

    # Parse our options and arguments
    options, args = parser.parse_args()

    if options.config is None:
        sys.stderr.write('Missing configuration file\n')
        print usage
        sys.exit(1)

    return options


def do_config(options):
    """
    CLI options are really for specifying how the server daemon should start up
    & behave. Any info needed by the application proper comes from a YAML
    config file.

    """
    try:
        stream = file(options.config, 'r')
        config = yaml.load(stream)
        stream.close()
    except IOError as err:
        sys.stderr.write('Configuration file not found "%s"\n' %
            options.config)
        sys.exit(1)
    except yaml.scanner.ScannerError as err:
        sys.stderr.write('Invalid configuration file "%s":\n%s\n' %
            (options.config, err))
        sys.exit(1)
    else:
        return config


def signal_handler(sig, frame):
    shutdown()


def main(config):
    for port in config['HTTPServer']['ports']:
        logging.info('Spawning on port %i', port)
        proc = multiprocessing.Process(target=runapp, args=(port, config))
        proc.start()
        children.append(proc)

    # Handle signals. So if you kill the parent process, the children get
    # cleaned up.
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    # daemonization causes realpath(__file__) to return '/', so we get the real
    # one here before we daemonize.
    application_base = realpath(dirname(dirname(realpath(__file__))))
    options = do_options()
    config = do_config(options)
    if 'Logging' in config.keys():
        do_logging(config["Logging"], options)
    if not options.foreground:
        #logdir = os.path.join(os.path.abspath(os.path.curdir),
        #    config['HTTPServer']['logdir'])
        daemonize(pidfile=options.pidfile,
            user=int(options.user),
            stderr='/dev/null',
            stdout = '/dev/null')

    main(config)
