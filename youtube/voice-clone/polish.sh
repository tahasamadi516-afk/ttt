#!/bin/bash
# Studio-mic polish for a cloned line: sh polish.sh in.wav out.wav
ffmpeg -loglevel error -y -i "$1" -af "highpass=f=80,equalizer=f=140:t=q:w=1:g=2.5,equalizer=f=300:t=q:w=1.2:g=-2,equalizer=f=3500:t=q:w=1:g=2,adeclick,acompressor=threshold=-22dB:ratio=3:attack=8:release=120:makeup=4,deesser=i=0.3,aresample=48000,loudnorm=I=-16:TP=-2" "$2"
