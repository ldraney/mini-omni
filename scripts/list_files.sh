#!/bin/bash

find . -type d \( -path ./.git -o -path ./.venv \) -prune -o -type f -not -name ".*" -print
