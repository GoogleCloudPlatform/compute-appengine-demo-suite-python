#!/bin/bash
IMAGE_VERSION=2
IMAGE_MARK=/var/fractal.image.$IMAGE_VERSION
if [ ! -e $IMAGE_MARK ];
then
  apt-get update
  apt-get install -y golang
  touch $IMAGE_MARK
fi

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
