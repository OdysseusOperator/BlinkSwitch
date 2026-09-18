{
  description = "BlinkSwitch COSMIC Wayland development shell";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" ];
      forEachSystem = f:
        builtins.listToAttrs (map (system: {
          name = system;
          value = f system;
        }) systems);
    in {
      devShells = forEachSystem (system:
        let
          pkgs = import nixpkgs { inherit system; };
          pythonRuntime = pkgs.python3.withPackages (pythonPackages: [
            pythonPackages.tkinter
          ]);
        in {
          default = pkgs.mkShell {
            packages = with pkgs; [
              cargo
              rustc
              pythonRuntime
              pkg-config
              libxkbcommon
              wayland
              libx11
              libglvnd
            ];

            # Lets smithay-client-toolkit find libxkbcommon through pkg-config.
            PKG_CONFIG_PATH = "${pkgs.libxkbcommon}/lib/pkgconfig:${pkgs.wayland}/lib/pkgconfig";

            # The current Python Raylib wheel is linked against libX11.
            LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
              pkgs.libx11
              pkgs.libxkbcommon
              pkgs.wayland
              pkgs.libglvnd
            ];

            # Raylib needs positionable X11 windows for the multi-monitor overlay.
            GLFW_PLATFORM = "x11";

            # Make Tk available to venvs created from the system Python.
            PYTHONPATH = "${pythonRuntime}/lib/python${pkgs.python3.pythonVersion}/site-packages:${pythonRuntime}/lib/python${pkgs.python3.pythonVersion}";
          };
        });
    };
}
