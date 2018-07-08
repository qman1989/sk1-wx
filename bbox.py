#!/usr/bin/env python
#
#   BuildBox for sK1/UniConvertor 2.x
#
# 	Copyright (C) 2018 by Igor E. Novikov
#
# 	This program is free software: you can redistribute it and/or modify
# 	it under the terms of the GNU General Public License as published by
# 	the Free Software Foundation, either version 3 of the License, or
# 	(at your option) any later version.
#
# 	This program is distributed in the hope that it will be useful,
# 	but WITHOUT ANY WARRANTY; without even the implied warranty of
# 	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# 	GNU General Public License for more details.
#
# 	You should have received a copy of the GNU General Public License
# 	along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Usage:
--------------------------------------------------------------------------
 to pull docker images:        python bbox.py pull
 to run build for all images:  python bbox.py build
 to build package:             python bbox.py
--------------------------------------------------------------------------
BuildBox is designed to be launched into Vagrant VM. To prepare environment
on Linux OS you need installing VirtualBox and Vagrant. After that initialize
environment from sk1-wx project folder:

>$vagrant up ubuntu
>$vagrant ssh ubuntu
>$cd /vagrant
>python bbox.py pull

To run build launcn BuildBox inside Vagrant VM:

>python bbox.py build
"""

import os
import platform
import shutil
import sys
from zipfile import ZIP_DEFLATED
from zipfile import ZipFile

from utils import bbox
from utils.bbox import is_path, command, echo_msg

# Output colors
STDOUT_MAGENTA = '\033[95m'
STDOUT_BLUE = '\033[94m'
STDOUT_GREEN = '\033[92m'
STDOUT_YELLOW = '\033[93m'
STDOUT_FAIL = '\033[91m'
STDOUT_ENDC = '\033[0m'
STDOUT_BOLD = '\033[1m'
STDOUT_UNDERLINE = '\033[4m'

# Build constants
IMAGE_PREFIX = 'sk1project/'
PROJECT_DIR = '/vagrant'
BUILD_DIR = os.path.join(PROJECT_DIR, 'build')
DIST_DIR = os.path.join(PROJECT_DIR, 'dist')
RELEASE_DIR = os.path.join(PROJECT_DIR, 'release')
PKGBUILD_DIR = os.path.join(PROJECT_DIR, 'pkgbuild')
ARCH_DIR = os.path.join(PROJECT_DIR, 'archlinux')

SCRIPT = 'setup-sk1.py'
APP_NAME = 'sk1'
APP_VER = '2.0rc4'
# SCRIPT = 'setup-uc2.py'
# APP_NAME = 'uc2'
# APP_VER = '2.0rc4'

RELEASE = False

IMAGES = [
    'ubuntu_14.04_32bit',
    'ubuntu_14.04_64bit',
    'ubuntu_16.04_32bit',
    'ubuntu_16.04_64bit',
    'ubuntu_18.04_64bit',
]


def clear_folders():
    # Clear build folders
    if is_path(BUILD_DIR):
        command('rm -rf %s' % BUILD_DIR)
    if is_path(DIST_DIR):
        command('rm -rf %s' % DIST_DIR)
    if not is_path(RELEASE_DIR):
        os.makedirs(RELEASE_DIR)


############################################################
# Main functions
############################################################


def pull_images():
    for image in IMAGES:
        echo_msg('Pulling %s%s image' % (IMAGE_PREFIX, image),
                 code=STDOUT_GREEN)
        command('docker pull %s%s' % (IMAGE_PREFIX, image))


def run_build(verbose=False):
    for image in IMAGES:
        os_name = image.capitalize().replace('_', ' ')
        echo_msg('Build on %s' % os_name, code=STDOUT_YELLOW)
        flag = '-d' if verbose else ''
        command('docker run %s -v %s:%s %s' %
                (flag, PROJECT_DIR, PROJECT_DIR, image))


def build_package():
    package_name2 = ''

    clear_folders()

    if bbox.is_deb():
        echo_msg("Building DEB package")
        command('cd %s;python2 %s bdist_deb 1> /dev/null' %
                (PROJECT_DIR, SCRIPT))

        old_name = bbox.get_package_name(DIST_DIR)
        prefix, suffix = old_name.split('_')
        new_name = prefix + bbox.get_marker(not RELEASE) + suffix
        if bbox.is_ubuntu():
            ts = ''
            if not RELEASE:
                ts = '_' + bbox.TIMESTAMP

            ver = platform.dist()[1]
            if ver == '14.04':
                package_name2 = prefix + ts + '_mint_17_' + suffix
            elif ver == '16.04':
                package_name2 = prefix + ts + '_mint_18_' + suffix
            elif ver == '18.04':
                package_name2 = prefix + ts + '_mint_19_' + suffix

    elif bbox.is_rpm():
        echo_msg("Building RPM package")
        command('cd %s;python2 %s bdist_rpm 1> /dev/null' %
                (PROJECT_DIR, SCRIPT))

        old_name = bbox.get_package_name(DIST_DIR)
        items = old_name.split('.')
        marker = bbox.get_marker(not RELEASE)
        new_name = '.'.join(items[:-2] + [marker, ] + items[-2:])
    else:
        echo_msg('Unsupported distro!', code=STDOUT_FAIL)
        sys.exit(1)

    old_name = os.path.join(DIST_DIR, old_name)
    package_name = os.path.join(RELEASE_DIR, new_name)
    command('cp %s %s' % (old_name, package_name))
    if package_name2:
        package_name2 = os.path.join(RELEASE_DIR, package_name2)
        command('cp %s %s' % (old_name, package_name2))

    if bbox.is_src():
        echo_msg("Creating source package")
        if os.path.isdir(DIST_DIR):
            shutil.rmtree(DIST_DIR, True)
        command('cd %s;python2 %s sdist 1> /dev/null' % (PROJECT_DIR, SCRIPT))
        old_name = bbox.get_package_name(DIST_DIR)
        marker = ''
        if not RELEASE:
            marker = '_%s' % bbox.TIMESTAMP
        new_name = old_name.replace('.tar.gz', '%s.tar.gz' % marker)
        old_name = os.path.join(DIST_DIR, old_name)
        package_name = os.path.join(RELEASE_DIR, new_name)
        command('cp %s %s' % (old_name, package_name))

        # ArchLinux PKGBUILD
        if os.path.isdir(PKGBUILD_DIR):
            shutil.rmtree(PKGBUILD_DIR, True)
        os.mkdir(PKGBUILD_DIR)
        os.chdir(PKGBUILD_DIR)

        tarball = os.path.join(PKGBUILD_DIR, new_name)
        command('cp %s %s' % (package_name, tarball))

        dest = 'PKGBUILD'
        src = os.path.join(ARCH_DIR, '%s-%s' % (dest, APP_NAME))
        command('cp %s %s' % (src, dest))
        command("sed -i 's/VERSION/%s/g' %s" % (APP_VER, dest))
        command("sed -i 's/TARBALL/%s/g' %s" % (new_name, dest))

        dest = 'README'
        src = os.path.join(ARCH_DIR, '%s-%s' % (dest, APP_NAME))
        command('cp %s %s' % (src, dest))

        pkg_name = new_name.replace('.tar.gz', '.archlinux.pkgbuild.zip')
        pkg_name = os.path.join(RELEASE_DIR, pkg_name)
        ziph = ZipFile(pkg_name, 'w', ZIP_DEFLATED)
        for item in [new_name, 'PKGBUILD', 'README']:
            path = os.path.join(PKGBUILD_DIR, item)
            ziph.write(path, item)
        ziph.close()
        shutil.rmtree(PKGBUILD_DIR, True)

    clear_folders()


############################################################
# Main build procedure
############################################################


if len(sys.argv) > 1:
    if sys.argv[1] == 'pull':
        pull_images()
    elif sys.argv[1] == 'build':
        run_build(len(sys.argv) > 2 and sys.argv[2] == 'verbose')
    else:
        build_package()
else:
    build_package()