# Quickstart

In a nutshell: There is a self-documenting command-line
tool `qlever`, which is controlled by a single configuration file, called
`Qleverfile`. For most applications, the `qlever` command-line tool is all you
need to use QLever. [See here for a complete reference of all the possible settings in a `Qleverfile`](qleverfile.md).

## Installing QLever

### Debian and Ubuntu

!!! warning "Uninstall old versions"
    Since 21.01.2026, there are official QLever packages for Debian, Ubuntu, and Ubuntu-derived distributions. Please uninstall any old versions of QLever that have been installed with other methods because they may conflict with the package.
    === "pip"
        ```bash
        pip uninstall qlever --break-system-packages
        ```
    === "pipx"
        ```bash
        pipx uninstall qlever
        ```
    === "uv"
        ```bash
        uv tool uninstall qlever
        ```

```bash title="Install QLever on Debian and Ubuntu"
sudo apt update && sudo apt install -y wget gpg ca-certificates
wget -qO - https://packages.qlever.dev/pub.asc | gpg --dearmor | sudo tee /usr/share/keyrings/qlever.gpg > /dev/null
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/qlever.gpg] https://packages.qlever.dev/ $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") main" | sudo tee /etc/apt/sources.list.d/qlever.list
sudo apt update
sudo apt install qlever
```

```bash title="Update QLever on Debian and Ubuntu"
sudo apt update
sudo apt upgrade qlever
```

=== "bash"
    ```bash title="Enable tab completion"
    sudo apt install bash-completion
    echo "source /etc/bash_completion" >> ~/.bashrc
    # restart your shell
    ```
=== "zsh"
    ```zsh title="Enable tab completion"
    echo "autoload -U compinit && compinit" >> ~/.zshrc
    # restart your shell
    ```
=== "fish"
    ```fish title="Enable tab completion"
    # Nothing to do
    ```

### macOS (Apple Silicon)

On macOS, we recommend installing QLever via [Homebrew](https://brew.sh/).

!!! note "Apple Silicon only"
    The QLever homebrew package is only available for ARM64 (M-series) Apple Silicon Macs. Intel-based Macs are not supported by this package. If you are on an Intel Mac, use the [platform-independent installation methods](#others) below.

!!! warning "Uninstall old versions"
    Since 21.01.2026, there is an official QLever package for macOS. Please uninstall any old versions of QLever that have been installed with other methods because they may conflict with the new package.
    === "pip"
        ```bash
        pip uninstall qlever --break-system-packages
        ```
    === "pipx"
        ```bash
        pipx uninstall qlever
        ```
    === "uv"
        ```bash
        uv tool uninstall qlever
        ```

```bash title="Install QLever via Homebrew"
brew tap qlever-dev/qlever
brew install qlever
```

```bash title="Update QLever via Homebrew"
brew update
brew upgrade qlever
```

=== "zsh"
    ```zsh title="Enable tab completion"
    echo "autoload -U compinit && compinit" >> ~/.zshrc
    # restart your shell
    ```
=== "bash"
    ```bash title="Enable tab completion"
    brew install bash-completion@2
    echo '[[ -r "$(brew --prefix)/etc/profile.d/bash_completion.sh" ]] && source "$(brew --prefix)/etc/profile.d/bash_completion.sh"' >> ~/.bashrc
    # restart your shell
    ```
=== "fish"
    ```fish title="Enable tab completion"
    # Nothing to do
    ```

### Others

For any of the platforms not listed above you can install the `qlever` CLI tool using system independent methods. Note: QLever will be executed in a container which will come with a performance penalty.

=== "pip"
    ``` bash title="Install QLever via pip"
    # inside a virtual environment
    pip install qlever
    ```
=== "pipx"
    ``` bash title="Install QLever via pipx"
    pipx install qlever
    ```
=== "uv"
    ```bash title="Install QLever via uv"
    uv tool install qlever
    ```

<!-- Dummy HTML comment to prevent MkDocs from glueing the previous and next code block together -->

=== "pip"
    ``` bash title="Update QLever via pip"
    # inside a virtual environment
    pip uninstall qlever && pip install qlever
    ```
=== "pipx"
    ``` bash title="Update QLever via pipx"
    pipx upgrade qlever
    ```
=== "uv"
    ```bash title="Install QLever via uv"
    uv tool upgrade qlever
    ```

## Using QLever

=== "pip"
    ``` bash
    # inside a virtual environment
    qlever setup-config olympics # Get Qleverfile (config file) for this dataset
    qlever get-data              # Download the dataset
    qlever index                 # Build index data structures for this dataset
    qlever start                 # Start a QLever server using that index
    qlever query                 # optional: Launch an example query
    qlever ui                    # optional: Launch the QLever UI
    ```
=== "pipx"
    ``` bash
    qlever setup-config olympics # Get Qleverfile (config file) for this dataset
    qlever get-data              # Download the dataset
    qlever index                 # Build index data structures for this dataset
    qlever start                 # Start a QLever server using that index
    qlever query                 # optional: Launch an example query
    qlever ui                    # optional: Launch the QLever UI
    ```
=== "uv"
    ```bash
    uvx qlever setup-config olympics # Get Qleverfile (config file) for this dataset
    uvx qlever get-data              # Download the dataset
    uvx qlever index                 # Build index data structures for this dataset
    uvx qlever start                 # Start a QLever server using that index
    uvx qlever query                 # optional: Launch an example query
    uvx qlever ui                    # optional: Launch the QLever UI
    ```

This will create a SPARQL endpoint for the 120 Years of Olympics dataset. It is a great dataset for getting started because it is small, but not trivial (around 2 million triples), and the downloading and indexing should only take a few seconds.

You can fetch any of a number of example `Qleverfile`s via `qlever setup-config <config-name>`.  In particular, a `Qleverfile` is available for each of the demos at <https://qlever.dev>: [list of all example `Qleverfile`s](https://github.com/qlever-dev/qlever-control/tree/main/src/qlever/Qleverfiles). To write a `Qleverfile` for your own data, pick one of these configurations as a starting point and edit the `Qleverfile` as you see fit. A detailed explanation of all `Qleverfile` options may also be found at [Qleverfile settings](qleverfile.md). 

Each command will also show you the command line it uses. That way you can learn, on the side, how QLever works internally. If you just want to know the command line for a particular command, without executing it, you can append `--show` like this:

```bash
qlever index --show
```

There are many more commands and options, see `qlever --help` for general help, `qlever <command> --help` for help on a specific command, or just use the autocompletion.

## Code and further documentation

The code for the `qlever` command-line tool can be found at
<https://github.com/qlever-dev/qlever-control>. There you also find more
information on the usage on macOS and Windows, for usage with your own dataset,
and for developers.
