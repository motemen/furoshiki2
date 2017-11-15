# furoshiki2

furoshiki is a thin wrapper around CUI operation that records command execution results.

## Usage

    % furo2
    furo2 exec COMMAND [ARGS...]
    furo2 history [pull | show COMMIT | fix]
    furo2 version

## Installation

With homebrew:

    brew install --HEAD motemen/furoshiki2/furoshiki2

Or with pip:

    pip3 install git+https://github.com/motemen/furoshiki2

Or:

    git clone https://github.com/motemen/furoshiki2
    cd furoshiki2
    pip3 install .

## Configuration

Create a repository and set `FURO_LOGS_REPOSITORY` environment variable to the repo's pushable URL eg:

    export FURO_LOGS_REPOSITORY=git@github.com:motemen/logs
