#!/bin/bash

set -e

backend_pyenv() {
    if hash pyenv 2>/dev/null;
    then
        echo "using pyenv wrapper"
        pyenv install --skip-existing
        pyenv exec python -m venv env
    else
        echo "using 'python -m venv env'"
        python -m venv env
    fi
}

wait_for_bg_jobs_to_end() {
    FAIL=0
    for job in `jobs -p`
    do
        echo $job
        wait $job || let "FAIL+=1"
    done

    echo $FAIL

    if [ "$FAIL" == "0" ];
    then
        echo "All BG jobs ok"
    else
        echo "Some BG jobs failed! ($FAIL)"
        exit 1
    fi
}

backend_pip() {
    env/bin/pip install -r requirements.txt
    env/bin/pip install -r tests/requirements.txt
}


backend() {
    backend_pyenv
    backend_pip
}

if [ "$PARALLEL_BUILD_AND_TEST" == "true" ]
then
    backend &
    wait_for_bg_jobs_to_end
else
    backend
fi
