#!/bin/bash
IMAGE_VERSION=2
IMAGE_MARK=/var/fractal.image.$IMAGE_VERSION
if [ ! -e $IMAGE_MARK ];
then
  curl -O https://go.googlecode.com/files/go1.1rc3.linux-amd64.tar.gz
  tar -C /usr/local -xzf go1.1rc3.linux-amd64.tar.gz
  touch $IMAGE_MARK
fi

export PATH=$PATH:/usr/local/go/bin
GMV=/usr/share/google/get_metadata_value

# Restart the server in the background if it fails.
function runServer {
  while :
  do
    $GMV attributes/goprog > ./program.go
    PROG_ARGS=$($GMV attributes/goargs)
    CMDLINE="go run ./program.go $PROG_ARGS"
    echo "Running $CMDLINE"
    $CMDLINE
  done
}
runServer &
