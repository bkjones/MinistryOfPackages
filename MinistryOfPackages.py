#!/usr/local/bin/python
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

__author__ = 'Brian K. Jones' 
__email__ = 'bkjones@gmail.com' 
__since__ = '2010-11-18'

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import os
import time
import logging
import redis
import mimetypes

from tornado.options import define, options
define("port", default=8888, help="run on the given port", type=int)

# global db handle
db = redis.Redis()


class DirectoryListingHandler(tornado.web.RequestHandler):
    def get(self, directory):
        if not os.path.exists(directory):
            raise tornado.web.HTTPError(404)
        if not os.path.isdir(directory):
            ftype_enc = mimetypes.guess_type(directory)

            if None not in ftype_enc:
                ftype, encoding = ftype_enc
                content_type = ftype
            else:
                content_type = 'application/octet-stream'

            self.set_header('Content-Type', content_type)
            self.set_header('Content-Disposition', 'attachment; filename=%s' % os.path.basename(directory))
            
            f = open(directory, 'r').read()
            self.write(f)
        else:
            basedir = os.path.normpath('tarballs')
            # Now add all of the other directory entries.
            allentries = os.listdir(directory)
            logging.debug("ALL ENTRIES IN %s: %s", directory, allentries)
            dlist = [(x, os.stat(os.path.normpath(os.path.join(directory,x)))) for x in allentries]
            pardir = None
            if basedir != os.path.normpath(directory):
                parent_directory = os.path.normpath(os.path.join(directory, '..'))
                parent_dir_stat = time.asctime(time.localtime(os.stat(parent_directory).st_mtime))
                pardir = [(parent_directory, parent_dir_stat)]
            
            logging.debug("DLIST: %s", dlist)

            # filtering statinfo so you just have (name, mtime) for each directory entry.
            output_entries = [(x, time.asctime(time.localtime(y.st_mtime))) for x,y in dlist]
            logging.debug("OUTPUT ENTRIES: %s", output_entries)
            logging.debug("DIRECTORY WE'RE LISTING: %s", directory)
            page_title = "Listing of directory '%s'" % directory
            self.render("dlist.html", title=page_title, entries=output_entries, directory=directory, pardir=pardir)

class SetupPyHandler(tornado.web.RequestHandler):
    def initialize(self):
        self.nolist_keys = ['protocol_version', 'md5_digest', 'long_description', 'summary', ':action']

    def get(self):
        self.write("Welcome to MyPI")
        
    def post(self):
        """
        Incoming requests come from the setup.py 'register' or 'upload' sub-commands. 
        Both pass in package metadata, but one includes a file upload. Note 
        that current versions of distutils don't properly terminate HTTP 
        Content-Disposition headers, and Tornado isn't tolerant of that, 
        which is why we parse our own body (after double-checking that 
        self.request.arguments is empty)

        """

        logging.debug("ARGUMENTS: %s", self.request.arguments)
        if not self.request.arguments:
            args = self.parse_args_from_body()
        else:
            args = self.request.arguments

        if 'filename' in args.keys():
            try:
                self.upload(self.request, args)
                return True
            except Exception as out:
                raise tornado.web.HTTPError(500, 'Problem with upload() --> %s' % out)

        logging.debug("ARGS: %s", args)

        # store all the args we got in the main lookup hash for the pkg. 
        db.hmset('pkg:%s' % args['name'], args)

        # For each k,v in args, make a set
        for arg, val in args.items():
            if arg == 'classifiers':
                for classifier in val:
                    logging.debug("Adding classifier '%s' for pkg %s", classifier, args['name'])
                    db.sadd(':'.join((arg, classifier)), args['name'])
            else:
                if arg not in self.nolist_keys:
                    logging.debug("Adding %s for pkg %s", 'metadata:%s' % arg, args['name'])
                    db.sadd('metadata:%s' % arg, val)


    def upload(self, req, args):
        tarball_dir = '/tmp/tarballs'
        rpm_dir = '/tmp/rpmz'

        fname = args['filename']
        if fname.startswith('"') and fname.endswith('"'):
            fname = fname[1:-1]
            logging.debug("FILENAME: %s", fname)

        if args['filetype'] == 'sdist':
            # it's a tarball
            f = open(os.path.join(tarball_dir, fname), 'w')
        elif args['filetype'] == 'rpm':
            f = open(os.path.join(rpm_dir, fname), 'w')

        f.write(args['filecontent'])
        f.close()
        logging.debug("UPLOAD: args -> %s", args)
        logging.debug("UPLOAD: files -> %s", req.files)


    def parse_args_from_body(self):
        try:
            ctfields = self.request.headers['Content-Type'].split(';')
            logging.debug("ctfields: %s" , ctfields)

            boundary = [field.split('=')[1] for field in ctfields if 'boundary=' in field][0]
            logging.debug("boundary: %s", boundary)

            chunks = self.request.body.split(boundary)
            logging.debug("chunks: %s", chunks)

            args = {}
            for i in chunks:
                logging.debug("Current chunk: %s", i)
                if 'filename' in i:
                    hdrs, file_contents = i.split('\n\n')
                    logging.debug("HEADERS RAW: %s", hdrs)
                    hdr_dict = dict([(h.split('=')) for h in hdrs.split(';') if '=' in h])
                    logging.debug("HEADER DICT: %s", hdr_dict)
                    if 'filename' in hdr_dict.keys():
                        file_name = hdr_dict['filename']
                        args['filename'] = file_name
                        args['filecontent'] = file_contents
                        continue

                if 'form-data' in i:
                    argbit = i.split(';')[1]
                    logging.debug("Argbit: %s", argbit)
                    
                    prename, preval = argbit.split('\n\n')
                    logging.debug("prename, preval == %s, %s", prename, preval)

                    k = prename.split('=')[1]
                    if k.startswith('"') and k.endswith('"'):
                        k = k[1:-1]
                    v = preval.rstrip('\n--')
                    logging.debug("K, V = %s, %s", k, v)

                    if k == 'classifiers':
                        if k in args:
                            # there can be >1 of these.
                            args[k].append(v)
                        else:
                            #first classifier we're adding.
                            args[k] = [v]
                    else:
                        args[k] = v

            logging.debug("ARGS: %s", args)
            return args
        except Exception as out:
            logging.error("Whoops --> %s (%s)", type(out), out)

class PyPIHandler(tornado.web.RequestHandler):
    def get(self, package=None, version=None):
        """
        From the Package Index API Doc: 

        Individual project version pages' URLs must be of the form base/projectname/version, 
        where base is the package index's base URL.

        Omitting the /version part of a project page's URL (but keeping the trailing /) 
        should result in a page that is either:

        a) The single active version of that project, as though the version had been 
        explicitly included, OR

        b) A page with links to all of the active version pages for that project.

        ALSO OF NOTE:

        The root URL of the index, if retrieved with a trailing /, must result in a page 
        containing links to all projects' active version pages.

        (Note: This requirement is a workaround for the absence of case-insensitive safe_name() 
        matching of project names in URL paths. If project names are matched in this fashion 
        (e.g. via the PyPI server, mod_rewrite, or a similar mechanism), then it is not necessary 
        to include this all-packages listing page.)

        """

        pass


def main():
    tornado.options.parse_command_line()
    application = tornado.web.Application([
        (r"/dist", SetupPyHandler),
        (r"/pypi/(?P<package>.*)/(?P<version>.*)", PyPIHandler),
        (r"/(?P<directory>.*)", DirectoryListingHandler),
        (r"/simple/(?P<package>.*/(?P<version>.*)", EasyInstallHandler)
    ])
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.bind(8888)
    http_server.start(2)
#    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    #cProfile.run('main()', 'profile_stats')
    main()
