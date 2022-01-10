#!/bin/bash
docker build -t pyindi-client .
docker run -t pyindi-client /bin/bash -c "indiserver indi_simulator_ccd indi_simulator_telescope & tox ."
