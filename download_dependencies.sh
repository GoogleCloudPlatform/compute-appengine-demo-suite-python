#! /bin/bash
set -o xtrace
set -o errexit

# Clean things out by deleting any current dependencies
rm -rf demo-suite/ext_lib || true
mkdir demo-suite/ext_lib

# Clean up any failed/aborted previous downloads
rm -rf temp_download || true
mkdir temp_download
cd temp_download

curl -O https://python-gflags.googlecode.com/files/python-gflags-2.0.tar.gz
tar -C ../demo-suite/ext_lib/ -xzf python-gflags-2.0.tar.gz

curl -O https://httplib2.googlecode.com/files/httplib2-0.8.tar.gz
tar -C ../demo-suite/ext_lib/ -xzf httplib2-0.8.tar.gz

curl -O https://google-api-python-client.googlecode.com/files/oauth2client-1.0.tar.gz
tar -C ../demo-suite/ext_lib/ -xzf oauth2client-1.0.tar.gz

curl -O https://google-api-python-client.googlecode.com/files/google-api-python-client-1.1.tar.gz
tar -C ../demo-suite/ext_lib/ -xzf google-api-python-client-1.1.tar.gz

# Clean up after ourselves
cd ..
rm -rf temp_download