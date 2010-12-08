import tornado.web
import os
import mimetypes
import logging
import time

class DirectoryListingHandler(tornado.web.RequestHandler):
    def get(self, directory):
        """
        If the requested path isn't under one of the directories in
        our config's PackageDirs list, we return a 404.

        """
        if not os.path.exists(directory):
            raise tornado.web.HTTPError(404)

        if not os.path.isdir(directory):
            # the requested path is a file, not a dir.
            # Make a best effort at figuring out what kind
            # of package it is, and send it along.
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
            # it's a directory. Try to provide a basic directory listing.
            # All paths need to exist under the basedir.
            basedir = os.path.normpath('/Users/jonesy/Downloads')
            allentries = os.listdir(directory)
            logging.debug("ALL ENTRIES IN %s: %s", directory, allentries)
            dlist = [(x, os.lstat(os.path.normpath(os.path.join(directory,x)))) for x in allentries]
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
