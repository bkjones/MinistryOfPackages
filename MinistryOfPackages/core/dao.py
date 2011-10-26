#import redis

#db = redis.Redis()

class PyPIData(object):

    def find_pkg(self, pkg):
        """
        The idea here is to define a relatively efficient method of
        finding packages in a case-insensitive way. This will probably
        return the proper package name as stored in redis.

        """
        pass

    def get_pkg_meta(self, pkg):
        """
        Return all metadata for a package. Don't forget to
        make the search case-insensitive.

        """
        pass

    def get_most_recent_tarball(self, pkg):
        """
        Get the name of the most recent tarball for package named 'pkg'.

        """
        pass

    def get_pkg_meta_field(self, pkg, field, version=None):
        """
        If version is None, return value for 'field' in latest version.

        """
        pass

    def get_pkg_download_url(self, pkg, version=None):
        """
        If version is None, get url for most recent version. Otherwise,
        return the url for the specified version.

        """
        pass

    def store_pkg_metadata(self, pkg, version):
        """
        Store all metadata for package. Should be called in the
        'upload' and 'register' setup.py commands, which both
        pass package metadata.

        """
        pass

    def update_pkg_metadata(self, pkg, version=None, **kwargs):
        """
        Set the metadata fields specified by **kwargs for the record
        indicated by pkg and version. If version is None, update the
        most recent version of the package.

        """
        pass

    def populate_initial_valid_metadata(self):
        """
        If we find an empty data store upon startup, we'll populate a
        redis list containing the metadata fields recognized by distutils.

        """
        pass

    def populate_initial_valid_classifiers(self):
        """
        If we find an empty data store upon startup, we'll populate a list
        of valid classifiers as published at:

        http://pypi.python.org/pypi?:action=list_classifiers

        I intend to actuall call that url in the setup, so while pypi *does*
        need to be available to do the initial population, it won't be
        necessary in a running service. The alternative is to check the url
        on an ongoing basis, which is clearly worse :)

        """
        pass
