import tornado.web
import os
import mimetypes
import logging
import time

class DirectoryListingHandler(tornado.web.RequestHandler):
    """
    This handler wouldn't be hard to plug into any old Tornado app. Here's what you need: 

    The application needs to have a settings['PackageDirs'] setting which is a list of 
    paths relative to your app directory (e.g. ['tmp/tarballs', 'tmp/source']. Incoming 
    requests will be checked to insure the paths exist AND that they live under one of 
    these directories. For testing I've been symlinking other dirs under my app directory
    and that's worked fine. 

    If the incoming request is for a file, mimetypes is used to make a guess at filetype. 
    In the future I'll try to import the python-magic module or similar & fall back to 
    mimetypes. Patches welcome :) 

    """


    def get(self, directory):
        """
        If the requested path isn't under one of the directories in
        our config's PackageDirs list, we return a 404.

        """

        # First things first: is the requested path under one of our 
        # configured PackageDirs, and does it actually exist? 
        valid_request = self.checkpath(directory)


        if valid_request:
            # At this point, if the path didn't exist or wasn't under PackageDirs, we would've 
            # already returned an HTTPError from checkpath.
            if not os.path.isdir(directory):
                # it's a file. 
                self.return_file(directory)
            else:
                # it's a directory. Try to provide a basic directory listing.
                root_dirs = [os.path.normpath(d) for d in self.application.settings['PackageDirs']]
                logging.debug("PackageDirs: %s", root_dirs)

                # Get a directory listing
                allentries = os.listdir(directory)
                logging.debug("ALL ENTRIES IN %s: %s", directory, allentries)

                # Get the stat info for each thing in the listing.
                dlist = [(x, os.lstat(os.path.normpath(os.path.join(directory,x)))) for x in allentries]
                pardir = None

                # if we're not requesting a base root_dir, there's a parent directory link. 
                if os.path.normpath(directory) not in root_dirs:
                    parent_directory = os.path.normpath(os.path.join(directory, '..'))
                    parent_dir_stat = time.asctime(time.localtime(os.stat(parent_directory).st_mtime))
                    pardir = [(parent_directory, parent_dir_stat)]

                # filtering statinfo so you just have (name, mtime) for each directory entry.
                output_entries = [(x, time.asctime(time.localtime(y.st_mtime))) for x,y in dlist]
                logging.debug("OUTPUT ENTRIES: %s", output_entries)
                logging.debug("DIRECTORY WE'RE LISTING: %s", directory)
                page_title = "Listing of directory '%s'" % directory 
                self.render("dlist.html", title=page_title, entries=output_entries, directory=directory, pardir=pardir)

    def checkpath(self, requested_path):
        """
        Check that the requested path lives under one of the configured 
        PackageDirs

        """
        logging.debug("Checking path: %s", requested_path)
        valid = [os.path.normpath(requested_path).startswith(i) for i in self.application.settings['PackageDirs']]
        if True in valid:
            logging.debug("Path is valid: %s", valid)
            # also check existence
            if os.path.exists(requested_path):
                logging.debug("Path exists - returning True")
                return True
            else:
                raise tornado.web.HTTPError(404)
        else:
            raise tornado.web.HTTPError(403)
                

    def return_file(self, requested_file):
        """
        The requested path is a file, not a dir.  Make a best effort at 
        figuring out what kind of file it is, and send it along.

        """
        ftype_enc = mimetypes.guess_type(requested_file)

        if None not in ftype_enc:
            ftype, encoding = ftype_enc
            content_type = ftype
        else:
            content_type = 'application/octet-stream'

        self.set_header('Content-Type', content_type)
        self.set_header('Content-Disposition', 'attachment; filename=%s' % os.path.basename(requested_file))

        f = open(requested_file, 'r').read()
        self.write(f)

