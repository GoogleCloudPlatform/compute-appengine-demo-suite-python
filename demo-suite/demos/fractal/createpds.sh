#! /bin/bash
set -o xtrace

PROJECT=your-project
ZONE=us-central1-a
GCUTIL="gcutil --project=$PROJECT"
IMAGE=projects/centos-cloud/global/images/centos-6-v20130515

# Create an array of PD images from an image.
set +o xtrace
PDS="boot-fractal-single-00"
for i in $(seq -f '%02g' 0 15); do
  PDS="$PDS boot-fractal-cluster-$i"
done
set -o xtrace

echo $PDS

#Delete any existing PDs
$GCUTIL deletedisk -f --zone=$ZONE $PDS

$GCUTIL adddisk --zone=$ZONE --source_image=$IMAGE $PDS
