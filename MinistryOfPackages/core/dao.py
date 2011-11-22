import redis

db = redis.Redis()

PKG_PREFIX = 'pkg'
PKG_NAME_INDEX = 'pkg:all_names'
class PyPIData(object):

    def find_pkg_key_byname(self, pkg):
        """
        Downcase the 'pkg' input, look up the value in PKG_NAME_INDEX, and
        if it exists, return the key that maps to the whole package.

        :param string pkg: Name of a package to find.
        :returns: key that maps to the package data (NOT the pkg data itself).

        """
        name = pkg.lower()
        exists = db.sismember(PKG_NAME_INDEX, name)
        if exists:
            pkgkey = ':'.join([PKG_PREFIX, name])
            return pkgkey
        else:
            return None

    def get_pkg_meta(self, pkg, version='latest'):
        """
        Return all metadata for a package.

        """
        pkgkey = self.find_pkg_key_byname(pkg)
        if pkgkey:
            pkgkey = ':'.join([pkgkey, version])
            meta = db.hgetall(pkgkey)
            return meta
        else:
            return None

    def get_distpkg_filename(self, pkg, version='latest'):
        """
        Get the filename (not path) of the distribution package
        (tarball, zip file, exe, dmg, whatever) at the given version.

        """
        #TODO: should have pkg:<pkg>:<version>:[sdist,bdist,rpm, etc] keys.
        # See the schema.txt file for expansion on this.
        return self.get_pkg_meta_field(pkg, 'filename', version)

    def get_pkg_meta_field(self, pkg, field, version='latest'):
        """
        If version is None, return value for 'field' in latest version, or None

        """
        pkgkey = self.find_pkg_key_byname(pkg)
        if pkgkey:
            pkgkey = ':'.join([pkgkey, version])
            val = db.hget(pkgkey, field)
            if val:
                return val
            else:
                return None
        else:
            return None

    def get_pkg_download_url(self, pkg, version='latest'):
        """
        If version is None, get 'download_url' for most recent version.
        Otherwise, return the url for the specified version.

        """
        return self.get_pkg_meta_field(pkg, 'dowload_url', version)

    def store_pkg_metadata(self, pkg, version='latest'):
        """
        Store all metadata for package. Should be called in the
        'upload' and 'register' setup.py commands, which both
        pass package metadata.

        """
        pass

    def update_pkg_metadata(self, pkg, version, **kwargs):
        """
        Set the metadata fields specified by **kwargs for the record
        indicated by pkg and version. To protect against overwriting unintended
        metadata in this case, version is required, and does NOT default to
        'latest'.

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
