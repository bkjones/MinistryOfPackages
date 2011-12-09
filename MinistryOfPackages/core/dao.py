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

    def update_classifier(self, classifier, pkg):
        """
        There's a set for each classifier a la:

        classifier:<cls_name> = [<pkg1>, <pkg2>, ...]

        This adds pkg to the classifier set.

        :param str classifier: Trove classifier to add pkg to.
        :param str pkg: The name of the package.
        """
        db.sadd(':'.join(('classifier', classifier)), pkg.lower())

    def store_pkg_data(self, pkg, version, alldata):
        """

        :param str pkg: name of package to store data for
        :param version:  version of pkg to store data for.
        :param alldata: the request args containing all data sent w/ upload or
                register request.
        :return:
        """
        db.hmset('pkg:%s:%s' % (pkg.lower(), version.lower()), alldata)

    def add_version_for_pkg(self, pkg, version):
        """
        Add the current version to the list of versions available for a package

        :param str pkg: Name of package
        :param version: package version
        :return:
        """
        db.sadd('pkg:%s:all_versions' % pkg.lower(), version.lower())

    def update_dependency(self, req, pkg):
        """
        For each uploaded package, we get (possibly) a list of dependencies.
        For each dependency, we track the packages which have this dependency.

        So, 'metadata:requires:pyyaml [Tinman, MinistryOfPackages, ...]'

        The key points to a set containing packages dependent on the pkg in the
        key.

        :param req:
        :param pkg:
        :return:
        """
        db.sadd('metadata:requires:%s' % req, pkg.lower())

    def update_all_classifiers(self, pkg, vals):
        for classifier in vals:
            self.update_classifier(classifier, pkg)

    def update_all_dependencies(self, pkg, deps):
        for dep in deps:
            self.update_dependency(dep, pkg)

    def add_filetype_for_dist(self, pkg, vers, ftype, fname):
        """
        Makes it easy to search & see if version x of pkg y has an available
        tarball, or an rpm, or whatever.

        Ex:
        pkg:ministryofpackages:0.9.7:tarball [MinistryOfPackages-0.9.7.tar.gz]

        :param pkg:
        :param vers:
        :param ftype:
        :param fname:
        :return:
        """
        db.sadd('pkg:%s:%s:%s' % (pkg.lower(), vers.lower(), ftype), fname)

    def update_pkg_metadata(self, pkg, metafield, metaval):
        """
        Set the metadata fields specified by **kwargs for the record
        indicated by pkg and version. To protect against overwriting unintended
        metadata in this case, version is required, and does NOT default to
        'latest'.

        """
        db.sadd('metadata:%s:%s' % (metafield, metaval), pkg.lower())

