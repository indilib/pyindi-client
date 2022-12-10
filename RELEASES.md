---
title: Releases
---

-   v1.9.9: Support INDI 1.9.9.  Fix implicit conversion between types
-   v1.9.0: Change versioning convention. Major & minor reflects supported indilib 
-   v0.2.8: Support INDI 1.9.0
-   v0.2.7b: High-level INDI Property support (indi-core v1.9.0 dev).
-   v0.2.7a: Fix for INDI v1.8.9 on raspberry (ignore
    INDI::Property::apply and ::define)
-   v0.2.7: Fix for INDI v1.8.9 (tested with commitb6d4094)
-   v0.2.6:
    [indibase/refactoring](https://github.com/indilib/indi/pull/1302):
    INDI::Property::apply and ::define are ignored (varargs following
    optional arg issue in swig).
-   v0.2.5: Fix package build with newer setuptools.
-   v0.2.4: Corrections suggested by Radek Kaczorek (include stdind.i).
-   v0.2.3: Corrections suggested by Georg Viehoever and Marco Gulino
    ([StarQuew](https://github.com/GuLinux/StarQuew/)).
-   v0.2.2: Use std=c++11 flag for compiling the swig wrapper.
-   v0.2.1: Use default string wrapping in swig.
-   v0.2.0: Changed libraries flag in setup.cfg for libindi 1.4.1. Edit
    setup.cfg if you use an older libindi version.
-   v0.1.0a1: Added multiarch search
-   v0.1.0: Initial release. Tested on Ubuntu 15.10 (x86\_64, python2,
    hand compiled indi-svn) and Fedora 22 (x86\_64, python2, hand
    compiled indi-svn-2671)
