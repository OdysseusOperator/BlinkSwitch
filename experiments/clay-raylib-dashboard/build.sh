#!/usr/bin/env bash
set -euo pipefail

if ! command -v nix >/dev/null 2>&1; then
    printf 'Error: nix is required to build this experiment.\n' >&2
    exit 1
fi

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
wayland_dev=$(nix eval --raw nixpkgs#wayland.dev.outPath)
wayland=$(nix eval --raw nixpkgs#wayland.outPath)
libx11_dev=$(nix eval --raw nixpkgs#libx11.dev.outPath)
libxkbcommon_dev=$(nix eval --raw nixpkgs#libxkbcommon.dev.outPath)
libxkbcommon=$(nix eval --raw nixpkgs#libxkbcommon.outPath)
libxcursor_dev=$(nix eval --raw nixpkgs#libXcursor.dev.outPath)
libxinerama_dev=$(nix eval --raw nixpkgs#libXinerama.dev.outPath)
libxrandr_dev=$(nix eval --raw nixpkgs#libXrandr.dev.outPath)
libxi_dev=$(nix eval --raw nixpkgs#libXi.dev.outPath)
libxrender_dev=$(nix eval --raw nixpkgs#libXrender.dev.outPath)
libxfixes_dev=$(nix eval --raw nixpkgs#libXfixes.dev.outPath)
libxext_dev=$(nix eval --raw nixpkgs#libXext.dev.outPath)
libgl=$(nix eval --raw nixpkgs#libGL.outPath)
xorgproto=$(nix eval --raw nixpkgs#xorgproto.outPath)

cd "$script_dir"

nix shell \
    nixpkgs#go_1_25 \
    nixpkgs#pkg-config \
    nixpkgs#wayland \
    nixpkgs#wayland.dev \
    nixpkgs#wayland-protocols \
    nixpkgs#libxkbcommon \
    nixpkgs#libx11.dev \
    nixpkgs#libxkbcommon.dev \
    nixpkgs#libXcursor.dev \
    nixpkgs#libXinerama.dev \
    nixpkgs#libXrandr.dev \
    nixpkgs#libXi.dev \
    nixpkgs#libXrender.dev \
    nixpkgs#libXfixes.dev \
    nixpkgs#libXext.dev \
    nixpkgs#libGL \
    nixpkgs#libGL.dev \
    nixpkgs#xorgproto \
    --command env \
    "C_INCLUDE_PATH=$wayland_dev/include:$libx11_dev/include:$libxkbcommon_dev/include:$libxcursor_dev/include:$libxinerama_dev/include:$libxrandr_dev/include:$libxi_dev/include:$libxrender_dev/include:$libxfixes_dev/include:$libxext_dev/include:$xorgproto/include" \
    "CGO_LDFLAGS=-L$wayland/lib -L$libxkbcommon/lib -L$libgl/lib" \
    go build -o clay-raylib-dashboard .

printf 'Build successful: %s\n' "$script_dir/clay-raylib-dashboard"
