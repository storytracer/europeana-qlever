# qlever-control

[qlever-control](https://github.com/qlever-dev/qlever-control) is a tool for running QLever instances. qlever-control can do the following for you

- download datasets
- create QLever indices
- manage (start, stop and inspect) QLever instances
- launch a UI for running SPARQL operations

## Installation

=== "pip"
    ``` bash
    pip install --break-system-packages qlever
    ```
=== "pipx"
    ``` bash
    pipx install qlever
    ```
=== "uv"
    ```bash
    uv tool install qlever
    ```

## Usage

A Qleverfile[^1] is required for using qlever-control. In an empty folder create a sample[^2] Qleverfile. See also the [Qleverfile reference](qleverfile.md).

=== "pip"
    ``` bash 
    qlever setup-config olympics
    ```
=== "pipx"
    ``` bash
    qlever setup-config olympics
    ```
=== "uv"
    ```bash
    uv tool run qlever setup-config olympics
    ```

Download the dataset and create an index for QLever.

=== "pip"
    ``` bash
    qlever get-data
    qlever index
    ```
=== "pipx"
    ``` bash
    qlever get-data
    qlever index
    ```
=== "uv"
    ```bash
    uv tool run qlever get-data
    uv tool run qlever index
    ```

Start the Qlever server.

=== "pip"
    ``` bash
    qlever start
    ```
=== "pipx"
    ``` bash
    qlever start
    ```
=== "uv"
    ```bash
    uv tool run qlever start
    ```

The QLever server is now running and ready to accept SPARQL operations.

Launch a UI for running SPARQL operations against the QLever server.

=== "pip"
    ``` bash
    qlever ui
    ```
=== "pipx"
    ``` bash
    qlever ui
    ```
=== "uv"
    ```bash
    uv tool run qlever ui
    ```

[^1]: Qleverfile are the config files used qlever-control. They specify the configuration for the dataset, the QLever server and the UI.
[^2]: Sample Qleverfiles are among others available for IMDB, OSM and Wikidata. See `qlever setup-config -h` for all full list.
