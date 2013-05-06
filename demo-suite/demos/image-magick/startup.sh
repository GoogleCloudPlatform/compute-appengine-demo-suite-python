#!/bin/bash

set -o xtrace

IMAGE_VERSION=1
IMAGE_MARK=/var/image-magick.image.$IMAGE_VERSION
if [ ! -e $IMAGE_MARK ];
then
  echo Installing Image Magick
  apt-get update
  apt-get install -y imagemagick
  touch $IMAGE_MARK
fi
BASE_URL=http://metadata/0.1/meta-data/attributes
IMAGE=$(curl $BASE_URL/image)
MACHINE_NUM=$(curl $BASE_URL/machine-num)
TAG=$(curl $BASE_URL/tag)
SEQ=$(curl $BASE_URL/seq)
GCS_PATH=$(curl $BASE_URL/gcs-path)
gsutil cp gs://gce-quick-start-demo/input/$IMAGE.png .
echo downloaded image
command='convert -delay 10 $IMAGE.png'
for i in `seq $SEQ`; do
  command="$command \\( -clone 0 -distort SRT $i \\)"
done
command="$command -set dispose Background  -delete 0 -loop 0 $TAG-$MACHINE_NUM.gif"
eval $command
echo processed image
gsutil cp -a public-read $TAG-$MACHINE_NUM.gif \
    gs://$GCS_PATH/$TAG-$MACHINE_NUM.gif
echo copied to cloud storage
echo finished
