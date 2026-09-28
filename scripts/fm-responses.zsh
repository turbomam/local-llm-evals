#!/bin/zsh
# Runs the photosynthesis prompt 3 times through fm and prints each response with timing.
zmodload zsh/datetime
P='Explain in about 300 words how photosynthesis works.'
for i in 1 2 3; do
  t0=$EPOCHREALTIME; out=$(fm respond --no-stream "$P" 2>&1); t1=$EPOCHREALTIME
  print "=== run=$i total_s=$(printf %.2f $((t1-t0))) words=$(print -r -- $out | wc -w | tr -d ' ')"
  print -r -- "$out"
done
