import tornado.web
import logging
import os

# This needs to be uncommented and the 'return True'
# later on removed in order to enable the data model and
# redis support.
#from MinistryOfPackages.core import dao
from ..core import dao

db = dao.PyPIData()

__author__ = 'jonesy'


class SetupPyHandler(tornado.web.RequestHandler):
    """
    This should handle the setup.py 'register' and 'upload' sub-commands.

    """

    def initialize(self):
        # attributes that are likely to be unique per-package, or unique enough
        # that storing a 'metadata:<attr>:<val> = [pkg1, pkg2, pkg3...pkgN]'
        # set would be useless.
        self.nolist_keys = [
            'md5_digest',
            'long_description',
            'description',
            'summary',
            ':action',
            'filecontent',
            'name',
            'home_page',
            'metadata_version',
            'protcol_version',
            'protocol_version',
            'filetype',
            'filename',
            'version',
            'comment',
            ]

    def post(self):
        """
        Incoming requests come from the setup.py 'register' or 'upload'
        sub-commands. Both pass in package metadata, but one includes a
        file upload.

        Note that current versions of distutils don't properly terminate HTTP
        Content-Disposition headers, and Tornado isn't tolerant of that, see:

        http://www.w3.org/Protocols/rfc2616/rfc2616-sec19.html#sec19.3

        ...which is why we parse our own body (after double-checking that
        self.request.arguments is empty)

        Distutils is aware that it's a problem:

        http://bugs.python.org/issue10510

        """

        logging.debug("WE'RE INSIDE THE UPDATED POST")
        #logging.debug("ARGUMENTS: %s", self.request.arguments)
        if not self.request.arguments:
            args = self.parse_args_from_body()
        else:
            args = self.request.arguments

        logging.debug("ARGS INSIDE POST: %s", args)

        if 'filename' in args.keys():
            try:
                logging.debug("CALLING upload")
                self.upload(self.request, args)
                # this return should be removed if an option to store data
                # and/or use the web UI is enabled.
                #return True
            except Exception as out:
                raise tornado.web.HTTPError(500, 'Problem with upload() --> %s'
                    % out)
        self.dbstore(args)

    def dbstore(self, args):
        """
        Don't take this function too seriously. It's a prototype while I
        iterate on the data model. This will all go into core.dao later.

        """
        p_name = args['name']
        p_vers = args['version']

        # creates pkg:<name>:<version> set
        db.store_pkg_data(p_name, p_vers, args)

        # pkg:<name>:all_versions
        db.add_version_for_pkg(p_name, p_vers)

        if args.get('filetype'):
            db.add_filetype_for_dist(p_name, p_vers,
                                     args['filetype'],
                                     args['filename'])

        for req in args.get('requires', []):
            db.update_dependency(req, p_name)

        # For each k,v in args, make a set
        for arg, val in args.items():
            if not val:
                continue
            if arg == 'classifiers':
                db.update_all_classifiers(p_name, val)
            elif arg == 'requires':
                db.update_all_dependencies(p_name, val)
            elif arg not in self.nolist_keys:
                db.update_pkg_metadata(p_name, arg, val)
        return

    def upload(self, req, args):
        # TODO: this line is going to cause brokenness someday. Planning to
        # clean it up and let users define different base paths for
        # different file types or maybe other arbitrary conditions.
        logging.debug("INSIDE upload()")
        base_pkgdir = os.path.join(self.application.settings['base_path'],
            self.application.settings['PackageDirs'][0])

        pkgname = args['name']
        fname = args['filename']
        fcontent = args['filecontent']

        if fname.startswith('"') and fname.endswith('"'):
            fname = fname[1:-1]
            logging.debug("FILENAME: %s", fname)

        filepath = os.path.join(base_pkgdir, pkgname, fname)
        try:
            with open(filepath, 'w') as f:
                f.write(fcontent)
        except IOError as ioerr:
            logging.debug("Error writing uploaded file: %s - %s",
                ioerr.errno,
                ioerr.strerror)
            try:
                os.makedirs(os.path.dirname(filepath))
                logging.debug("Path created: %s", os.path.dirname(filepath))
                with open(filepath, 'w') as f:
                    f.write(fcontent)
            except OSError as out:
                logging.debug("Error creating path %s (%s - %s)",
                    filepath,
                    out.errno,
                    out.strerror)
                raise tornado.web.HTTPError(500)

    def parse_args_from_body(self):
        """
        current distutils versions don't use proper line terminators for HTTP
        headers, so we can't lean on Tornado's nicely-populated
        self.request.arguments, and self.request.files. We have to do it
        manually.

        """
        logging.debug("Inside parse_args_from_body")
        logging.debug(self.request)
        try:
            ctfields = self.request.headers['Content-Type'].split(';')
            logging.debug("ctfields: %s", ctfields)

            boundary = [field.split('=')[1] for field in ctfields
                if 'boundary=' in field][0]
            logging.debug("boundary: %s", boundary)

            chunks = self.request.body.split(boundary)
            logging.debug("chunks: %s", chunks)

            args = {}
            for i in chunks:
                logging.debug("Current chunk: %s", i)
                if 'filename' in i:
                    hdrs, file_contents = i.split('\n\n', 1)
                    #logging.debug("HEADERS RAW: %s", hdrs)
                    hdr_dict = dict([(h.split('=')) for h in hdrs.split(';')
                        if '=' in h])
                    #logging.debug("HEADER DICT: %s", hdr_dict)
                    if 'filename' in hdr_dict.keys():
                        file_name = hdr_dict['filename']
                        args['filename'] = file_name
                        args['filecontent'] = file_contents
                        continue

                if 'form-data' in i:
                    argbit = i.split(';', 1)[1]
                    #logging.debug("Argbit: %s", argbit)

                    prename, preval = argbit.split('\n\n', 1)
                    #logging.debug("prename, preval == %s, %s", prename, preval)

                    k = prename.split('=')[1]
                    if k.startswith('"') and k.endswith('"'):
                        k = k[1:-1]
                    v = preval.rstrip('\n--')
                    logging.debug("K, V = %s, %s", k, v)

                    if k == 'classifiers' or k == 'requires':
                        if k in args:
                            # there can be >1 of these.
                            args[k].append(v)
                        else:
                            #first classifier we're adding.
                            args[k] = [v]
                    else:
                        args[k] = v

            #logging.debug("ARGS: %s", args)
            return args
        except Exception as out:
            logging.error("Whoops --> %s (%s)", type(out), out)
