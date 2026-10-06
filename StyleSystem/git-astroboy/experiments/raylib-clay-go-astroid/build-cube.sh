#!/bin/bash

# Build script for the 3D Cube Experiment
# This builds on Windows but runs from WSL

echo "Building 3D Cube Experiment..."

# Set environment for Windows cross-compilation from WSL
export GOOS=windows
export GOARCH=amd64
export CGO_ENABLED=1

# Use x86_64-w64-mingw32-gcc for cross-compilation
export CC=x86_64-w64-mingw32-gcc
export CXX=x86_64-w64-mingw32-g++

# Build the cube experiment
cd /mnt/c/dev/testOpencode/experiments/raylib-clay-go-example

go build -o cube-experiment.exe -ldflags="-s -w" cube-experiment.go

if [ $? -eq 0 ]; then
    echo "Build successful! Run cube-experiment.exe to start."
else
    echo "Build failed!"
    exit 1
fi
