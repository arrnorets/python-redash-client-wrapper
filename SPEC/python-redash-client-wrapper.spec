#
# spec file for python-redash-client-wrapper
#

Name:           python-redash-client-wrapper
Version:        0.1
Release:        1%{?dist}
Url:            https://asgardahost.ru
Summary:        A package that provides a wrapper over console Redash client written in Python.
License:        GPL
Group:          Misc

BuildArch:      noarch
BuildRoot:      %(mktemp -ud %{_tmppath}/%{name}-%{version}-XXXXXX)

Provides:       redash-client.py
Requires:       python3, python3-redash-api-client
Prefix:		/opt/redash-client

%description
This package provides a wrapper over console Redash client written in Python.
- Redash - https://redash.io 
- https://pypi.org/project/redash-api-client - console Redash API client written in Python .

%prep
%if %{get_src_method} == "git_clone"
    rm -fr %{builddir}
    mkdir %{builddir}
    cd %{builddir}
    git clone %{source_url} %{name}
    cd %{name}
    git checkout %{branch_or_tag}
%else
    rm -fr %{builddir}
    mkdir %{builddir}
    cd %{builddir}
    curl -o archive.tar.gz -K %{config_file} "%{source_url}/archive.tar.gz?sha=%{branch_or_tag}"
    tar -xvzf archive.tar.gz
    rm -f archive.tar.gz
    SRC_DIR=`ls`
    mv ${SRC_DIR} %{name}
    cd %{name}
%endif

%build

%install
# Turn off the brp-python-bytecompile script
%global __os_install_post %(echo '%{__os_install_post}' | sed -e 's!/usr/lib[^[:space:]]*/brp-python-bytecompile[[:space:]].*$!!g')

cd %{builddir}/python-redash-client-wrapper
mkdir -p ${RPM_BUILD_ROOT}/%{prefix}
mkdir -p ${RPM_BUILD_ROOT}/%{_docdir}/python-redash-client-wrapper

install -m 755 src/redash-client.py ${RPM_BUILD_ROOT}/%{prefix}/redash-client.py
install -m 644 conf/redash-client.ini ${RPM_BUILD_ROOT}/%{_docdir}/python-redash-client-wrapper/redash-client.ini

%files
%defattr(755,root,root,755)
%{prefix}/redash-client.py
%{_docdir}/python-redash-client-wrapper/redash-client.ini

%post

%clean
rm -fr ${RPM_BUILD_ROOT}
rm -fr %{builddir}

%changelog
* Sun Sep 26 2021 Roman A. Chukov <r.chukov@asgardahost.ru>
- An initial version 0.1

