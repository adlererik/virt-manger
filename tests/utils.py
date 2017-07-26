# Copyright (C) 2013, 2014 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301 USA.

import difflib
import os

import virtinst
import virtinst.cli
import virtinst.uri

# DON'T EDIT THIS. Use 'setup.py test --regenerate-output'
REGENERATE_OUTPUT = False

# pylint: disable=protected-access
# Access to protected member, needed to unittest stuff

_capsprefix  = ",caps=%s/tests/capabilities-xml/" % os.getcwd()
_domcapsprefix  = ",domcaps=%s/tests/capabilities-xml/" % os.getcwd()

uri_test_default = "__virtinst_test__test:///default,predictable"
uri_test = "__virtinst_test__test:///%s/tests/testdriver.xml,predictable" % os.getcwd()
uri_test_remote = uri_test + ",remote"

_uri_qemu = "%s,qemu" % uri_test
_uri_kvm_domcaps = (_uri_qemu + _domcapsprefix + "kvm-x86_64-domcaps.xml")
_uri_kvm_aarch64_domcaps = (_uri_qemu + _domcapsprefix + "kvm-aarch64-domcaps.xml")
uri_kvm_nodomcaps = (_uri_qemu + _capsprefix + "kvm-x86_64.xml")
uri_kvm_rhel = (_uri_kvm_domcaps + _capsprefix + "kvm-x86_64-rhel7.xml")
uri_kvm = (_uri_kvm_domcaps + _capsprefix + "kvm-x86_64.xml")
uri_kvm_session = uri_kvm + ",session"

uri_kvm_armv7l = (_uri_kvm_domcaps + _capsprefix + "kvm-armv7l.xml")
uri_kvm_aarch64 = (_uri_kvm_aarch64_domcaps + _capsprefix + "kvm-aarch64.xml")
uri_kvm_ppc64le = (_uri_kvm_domcaps + _capsprefix + "kvm-ppc64le.xml")
uri_kvm_s390x = (_uri_kvm_domcaps + _capsprefix + "kvm-s390x.xml")
uri_kvm_s390x_KVMIBM = (_uri_kvm_domcaps + _capsprefix + "kvm-s390x-KVMIBM.xml")

uri_xen = uri_test + _capsprefix + "xen-rhel5.4.xml,xen"
uri_lxc = uri_test + _capsprefix + "lxc.xml,lxc"
uri_vz = uri_test + _capsprefix + "vz.xml,vz"


def get_debug():
    return ("DEBUG_TESTS" in os.environ and
            os.environ["DEBUG_TESTS"] == "1")


def _make_uri(base, connver=None, libver=None):
    if connver:
        base += ",connver=%s" % connver
    if libver:
        base += ",libver=%s" % libver
    return base


_conn_cache = {}


def openconn(uri):
    """
    Extra super caching to speed up the test suite. We basically
    cache the first guest/pool/vol poll attempt for each URI, and save it
    across multiple reopenings of that connection. We aren't caching
    libvirt objects, just parsed XML objects. This works fine since
    generally every test uses a fresh virConnect, or undoes the
    persistent changes it makes.
    """
    virtinst.util.register_libvirt_error_handler()
    conn = virtinst.cli.getConnection(uri)

    if uri not in _conn_cache:
        _conn_cache[uri] = {}
        _conn_cache[uri]["vms"] = conn._fetch_all_guests_cached()
        _conn_cache[uri]["pools"] = conn._fetch_all_pools_cached()
        _conn_cache[uri]["vols"] = conn._fetch_all_vols_cached()
        _conn_cache[uri]["nodedevs"] = conn._fetch_all_nodedevs_cached()
    cache = _conn_cache[uri].copy()

    def cb_fetch_all_guests():
        return cache["vms"]

    def cb_fetch_all_nodedevs():
        return cache["nodedevs"]

    def cb_fetch_all_pools():
        if "pools" not in cache:
            cache["pools"] = conn._fetch_all_pools_cached()
        return cache["pools"]

    def cb_fetch_all_vols():
        if "vols" not in cache:
            cache["vols"] = conn._fetch_all_vols_cached()
        return cache["vols"]

    def cb_clear_cache(pools=False):
        if pools:
            cache.pop("pools", None)
            cache.pop("vols", None)

    conn.cb_fetch_all_guests = cb_fetch_all_guests
    conn.cb_fetch_all_pools = cb_fetch_all_pools
    conn.cb_fetch_all_vols = cb_fetch_all_vols
    conn.cb_fetch_all_nodedevs = cb_fetch_all_nodedevs
    conn.cb_clear_cache = cb_clear_cache

    return conn


def open_testdefault():
    return openconn(uri_test_default)


def open_testdriver():
    return openconn(uri_test)


def open_kvm(connver=None, libver=None):
    return openconn(_make_uri(uri_kvm, connver, libver))


def open_kvm_rhel(connver=None):
    return openconn(_make_uri(uri_kvm_rhel, connver))


def open_test_remote():
    return openconn(uri_test_remote)


def test_create(testconn, xml, define_func="defineXML"):
    xml = virtinst.uri.sanitize_xml_for_test_define(xml)

    try:
        func = getattr(testconn, define_func)
        obj = func(xml)
    except Exception, e:
        raise RuntimeError(str(e) + "\n" + xml)

    try:
        obj.create()
        obj.destroy()
        obj.undefine()
    except:
        try:
            obj.destroy()
        except:
            pass
        try:
            obj.undefine()
        except:
            pass


def read_file(filename):
    """Helper function to read a files contents and return them"""
    f = open(filename, "r")
    out = f.read()
    f.close()

    return out


def diff_compare(actual_out, filename=None, expect_out=None):
    """Compare passed string output to contents of filename"""
    if not expect_out:
        if not os.path.exists(filename) or REGENERATE_OUTPUT:
            file(filename, "w").write(actual_out)
        expect_out = read_file(filename)

    diff = "".join(difflib.unified_diff(expect_out.splitlines(1),
                                        actual_out.splitlines(1),
                                        fromfile=filename,
                                        tofile="Generated Output"))
    if diff:
        raise AssertionError("Conversion outputs did not match.\n%s" % diff)
