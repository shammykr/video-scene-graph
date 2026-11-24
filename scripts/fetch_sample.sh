#!/usr/bin/env sh
# Downloads the sample traffic clip (Intel IoT DevKit sample-videos) used for the demo and benchmark.
set -e
mkdir -p data
curl -sSL -o data/sample.mp4 \
  https://github.com/intel-iot-devkit/sample-videos/raw/master/person-bicycle-car-detection.mp4
echo "saved data/sample.mp4"
