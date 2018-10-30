#!/usr/bin/env bash

zimdir="~/.local/share/zim"
zimdir="${zimdir/#\~/$HOME}"
plugdir=${zimdir}/plugins
siteexdir=${plugdir}/siteexporter

if [ ! -d ${zimdir} ]; then
   echo "Local Zim directory not found. Is Zim installed?"
   exit 1
fi

if [ ! -d ${siteexdir} ]; then
   mkdir -p ${siteexdir}
fi

echo "Copying to ${siteexdir}"
cp *.py ${siteexdir}/
