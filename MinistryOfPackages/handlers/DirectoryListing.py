import tornado.web
import os
from os.path import normpath, join, isdir, islink, exists, basename
import mimetypes
import logging
import time

class DirectoryListingHandler(tornado.web.RequestHandler):
    """
    This handler wouldn't be hard to plug into any old Tornado app.
    Here's what you need:

    The application needs to have a settings['PackageDirs'] setting which is
    a list of paths relative to your app directory
    (e.g. ['tmp/tarballs', 'tmp/source']. Incoming requests will be checked
    to insure the paths exist AND that they live under one of these
    directories. For testing I've been symlinking other dirs under my app
    directory and that's worked fine.

    If the incoming request is for a file, mimetypes is used to make a guess
    at filetype. In the future I'll try to import the python-magic module or
    similar & fall back to mimetypes. Patches welcome :)

    """

    def get(self, directory):
        """
        If the requested path isn't under one of the directories in
        our config's PackageDirs list, or doesn't exist, we return a 404.

        If the requested path is a directory but lives *under* a config'd
        package directory, we provide a parent directory link.

        If it's a file, we just return the file.

        We error out if a request resolves to a symlink.

        """

        valid_request = self.checkpath(directory)
        uri_path = directory
        disk_path = self.get_fullpath(directory)
        if valid_request:
            # If the path didn't exist or wasn't under PackageDirs, we would've
            # already returned an HTTPError from checkpath.
            if not isdir(disk_path):
                self.return_file(disk_path)
            else:
                # it's a directory. Try to provide a basic directory listing.

                # Full paths to each PackageDir, used to see if we need a
                # 'parent directory' link in the browser output.
                root_dirs = [self.get_fullpath(d) for d in \
                             self.application.settings['PackageDirs']]
                allentries = os.listdir(disk_path)
                dlist = [(x, os.lstat(normpath(join(disk_path, x)))) for x in \
                                                                    allentries]
                pardir = None

                # if we're not requesting a base root_dir, there's a parent
                # directory link.
                if normpath(disk_path) not in root_dirs:
                    parent_directory = normpath(join(uri_path, '..'))
                    parent_fullpath = self.get_fullpath(parent_directory)
                    parent_stat = time.asctime(time.localtime(
                                            os.stat(parent_fullpath).st_mtime))
                    pardir = [(parent_directory, parent_stat)]

                # filter statinfo to only (name, mtime) for each dir entry.
                output_entries = [(x, time.asctime(time.localtime(
                                                y.st_mtime))) for x,y in dlist]
                page_title = "Listing of directory '%s'" % uri_path
                self.render("dlist.html", title=page_title,
                            entries=output_entries, directory=uri_path,
                            pardir=pardir)

    def checkpath(self, requested_path):
        """
        Check that the requested path lives under one of the configured 
        PackageDirs, that it exists, and that it's not a symlink.

        """
        valid = [normpath(requested_path).startswith(i) for i in \
                 self.application.settings['PackageDirs']]
        fullpath = self.get_fullpath(requested_path)
        logging.debug("Full path on disk for request: %s", fullpath)

        if not any(valid):
            logging.error("No matching PkgDirs for '%s'", requested_path)
            raise tornado.web.HTTPError(404)
        elif not exists(fullpath):
            logging.error("NO SUCH PATH: %s", fullpath)
            raise tornado.web.HTTPError(404)
        elif islink(fullpath):
            logging.error("Requested path is a symlink: %s", fullpath)
            raise tornado.web.HTTPError
        else:
            return True

    def get_fullpath(self, req):
        fullpath = join(self.application.settings['base_path'], req)
        return fullpath

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
        self.set_header('Content-Disposition',
                        'attachment; filename=%s' % basename(requested_file))

        f = open(requested_file, 'r').read()
        self.write(f)

