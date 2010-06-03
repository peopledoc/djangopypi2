import os

from django.conf import settings
from django.http import (HttpResponse, HttpResponseForbidden,
                         HttpResponseBadRequest)
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import login

from djangopypi.decorators import basic_auth
from djangopypi.forms import PackageForm, ReleaseForm
from djangopypi.models import Package, Release, Classifier

ALREADY_EXISTS_FMT = _(
    "A file named '%s' already exists for %s. Please create a new release.")


def submit_package_or_release(user, post_data, files):
    """Registers/updates a package or release"""
    try:
        package = Package.objects.get(name=post_data['name'])
        if package.owner != user:
            return HttpResponseForbidden(
                    "That package is owned by someone else!")
    except Package.DoesNotExist:
        package = None

    package_form = PackageForm(post_data, instance=package)
    if package_form.is_valid():
        package = package_form.save(commit=False)
        package.owner = user
        package.save()
        for c in post_data.getlist('classifiers'):
            classifier, created = Classifier.objects.get_or_create(name=c)
            package.classifiers.add(classifier)
        if files:
            allow_overwrite = getattr(settings,
                "DJANGOPYPI_ALLOW_VERSION_OVERWRITE", False)
            try:
                release = Release.objects.get(version=post_data['version'],
                                              package=package,
                                              distribution=UPLOAD_TO + '/' +
                                              files['distribution']._name)
                if not allow_overwrite:
                    return HttpResponseForbidden(ALREADY_EXISTS_FMT % (
                                release.filename, release))
            except Release.DoesNotExist:
                release = None

            # If the old file already exists, django will append a _ after the
            # filename, however with .tar.gz files django does the "wrong"
            # thing and saves it as package-0.1.2.tar_.gz. So remove it before
            # django sees anything.
            release_form = ReleaseForm(post_data, files, instance=release)
            if release_form.is_valid():
                if release and os.path.exists(release.distribution.path):
                    os.remove(release.distribution.path)
                release = release_form.save(commit=False)
                release.package = package
                release.save()
            else:
                return HttpResponseBadRequest(
                        "ERRORS: %s" % release_form.errors)
    else:
        return HttpResponseBadRequest("ERRORS: %s" % package_form.errors)

    return HttpResponse()

@basic_auth
def register_or_upload(request, post_data, files):
    user = login_basic_auth(request)
    if not user:
        return HttpResponseUnauthorized('pypi')

    login(request, user)
    if not request.user.is_authenticated():
        return HttpResponseForbidden(
                "Not logged in, or invalid username/password.")

    return submit_package_or_release(user, post_data, files)
