import tornado.web


class PyPIHandler(tornado.web.RequestHandler):
    """
    This will handle the browser-based package browsing functionality.

    """

    def get(self, package=None, version=None):
        """
        From the Package Index API Doc:

        Individual project version pages' URLs must be of the form
        base/projectname/version, where base is the package index's
        base URL.

        Omitting the /version part of a project page's URL
        (but keeping the trailing /) should result in a page that is
        either:

        a) The single active version of that project, as though the
           version had been explicitly included, OR

        b) A page with links to all of the active version pages for that
           project.

        ALSO OF NOTE:

        The root URL of the index, if retrieved with a trailing /, must
        result in a page containing links to all projects' active version
        pages.

        (Note: This requirement is a workaround for the absence of
        case-insensitive safe_name() matching of project names in URL paths.
        If project names are matched in this fashion (e.g. via the PyPI
        server, mod_rewrite, or a similar mechanism), then it is not necessary
        to include this all-packages listing page.)

        """
        self.write("Welcome to the Ministry of Packages")
