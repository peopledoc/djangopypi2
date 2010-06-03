import os
from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils import simplejson as json
from django.utils.datastructures import MultiValueDict
from django.contrib.auth.models import User


class PackageInfoField(models.Field):
    description = u'Python Package Information Field'
    __metaclass__ = models.SubfieldBase
    
    def __init__(self, *args, **kwargs):
        kwargs['editable'] = False
        super(PackageInfoField,self).__init__(*args, **kwargs)
    
    def to_python(self, value):
        if isinstance(value, basestring):
            if value:
                return MultiValueDict(json.loads(self.package_info))
            else:
                return MultiValueDict()
        if isinstance(value, dict):
            return MultiValueDict(value)
        if isinstance(value,MultiValueDict):
            return value
        raise ValueError('Unexpected value encountered when converting data to python')
    
    def get_prep_value(self, value):
        if isinstance(value,MultiValueDict):
            return json.dumps(dict(value.iterlists()))
        if isinstance(value, dict):
            return json.dumps(value)
        if isinstance(value, basestring) or value is None:
            return value
        
        raise ValueError('Unexpected value encountered when preparing for database')
    
    def get_internal_type(self):
        return 'TextField'



class Classifier(models.Model):
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        verbose_name = _(u"classifier")
        verbose_name_plural = _(u"classifiers")

    def __unicode__(self):
        return self.name


class Package(models.Model):
    name = models.CharField(max_length=255, unique=True, primary_key=True)
    auto_hide = models.BooleanField(default=True, blank=False)
    allow_comments = models.BooleanField(default=True, blank=False)
    owners = models.ManyToManyField(User, blank=True,
                                    related_name="packages_owned")
    maintainers = models.ManyToManyField(User, blank=True,
                                         related_name="packages_maintained")
    
    class Meta:
        verbose_name = _(u"package")
        verbose_name_plural = _(u"packages")

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('djangopypi-package-details', (), {'package': self.name})
    
    @property
    def latest(self):
        try:
            return self.releases.latest()
        except Release.DoesNotExist:
            return None
    
    def get_release(self, version):
        """Return the release object for version, or None"""
        try:
            return self.releases.get(version=version)
        except Release.DoesNotExist:
            return None

class Release(models.Model):
    package = models.ForeignKey(Package, related_name="releases")
    version = models.CharField(max_length=128)
    metadata_version = models.CharField(max_length=64, default='1.0')
    package_info = PackageInfoField(blank=False)
    hidden = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    
    class Meta:
        verbose_name = _(u"release")
        verbose_name_plural = _(u"releases")
        unique_together = ("package", "version")
        get_latest_by = 'created'
        ordering = ['-created']

    def __unicode__(self):
        return self.release_name
    
    @property
    def release_name(self):
        return u"%s-%s" % (self.package.name, self.version)
    
    @property
    def summary(self):
        return self.package_info.get('summary',u'')
    
    @property
    def description(self):
        return self.package_info.get('description',u'')
    
    @models.permalink
    def get_absolute_url(self):
        return ('djangopypi-show_version', (), {'package': self.package.name,
                                                'version': self.version})


class File(models.Model):
    release = models.ForeignKey(Release, related_name="files")
    distribution = models.FileField(upload_to=settings.DJANGOPYPI_RELEASE_UPLOAD_TO)
    md5_digest = models.CharField(max_length=32, blank=True)
    filetype = models.CharField(max_length=32, blank=False,
                                choices=settings.DJANGOPYPI_DIST_FILE_TYPES)
    pyversion = models.CharField(max_length=16, blank=True,
                                 choices=settings.DJANGOPYPI_PYTHON_VERSIONS)
    comment = models.CharField(max_length=255, blank=True)
    signature = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    uploader = models.ForeignKey(User)
    
    @property
    def filename(self):
        return os.path.basename(self.distribution.name)
    
    @property
    def path(self):
        return self.distribution.name
    
    def get_absolute_url(self):
        return "%s#md5=%s" % (self.distribution.url, self.md5_digest)

    
    class Meta:
        verbose_name = _(u"file")
        verbose_name_plural = _(u"files")
        unique_together = ("release", "filetype", "pyversion")
    
    def __unicode__(self):
        return self.distribution.name

class Review(models.Model):
    release = models.ForeignKey(Release, related_name="reviews")
    rating = models.PositiveSmallIntegerField(blank=True)
    comment = models.TextField(blank=True)
    
    class Meta:
        verbose_name = _(u'release review')
        verbose_name_plural = _(u'release reviews')
