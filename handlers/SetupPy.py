import tornado.web
import logging
import os

__author__ = 'jonesy'
class SetupPyHandler(tornado.web.RequestHandler):
    """
    This should handle the setup.py 'register' and 'upload' sub-commands.

    """
    def initialize(self):
        self.nolist_keys = ['protocol_version', 'md5_digest', 'long_description', 'summary', ':action']


    def post(self):
        """
        Incoming requests come from the setup.py 'register' or 'upload' sub-commands.
        Both pass in package metadata, but one includes a file upload.

        Note that current versions of distutils don't properly terminate HTTP
        Content-Disposition headers, and Tornado isn't tolerant of that, see:

        http://www.w3.org/Protocols/rfc2616/rfc2616-sec19.html#sec19.3

        ...which is why we parse our own body (after double-checking that
        self.request.arguments is empty)

        Distutils is aware that it's a problem:

        http://bugs.python.org/issue10510

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
        else:
            raise tornado.web.HTTPError(401, "Unsupported file type")

        f.write(args['filecontent'])
        f.close()
        logging.debug("UPLOAD: args -> %s", args)
        logging.debug("UPLOAD: files -> %s", req.files)


    def parse_args_from_body(self):
        """
        current distutils versions don't use proper line terminators for HTTP headers,
        so we can't lean on Tornado's nicely-populated self.request.arguments, and
        self.request.files. We have to do it manually.

        """
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

  