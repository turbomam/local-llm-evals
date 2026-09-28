#!/bin/zsh
# Runs the photosynthesis prompt 3 times through fm and prints each response with timing.
# Superseded by the runner (`just run photosynthesis`); kept because it produced the responses in
# results/2026-09-28-photosynthesis/.
zmodload zsh/datetime
P='Explain in about 300 words how photosynthesis works.'
err=$(mktemp -t fmresponses)
for i in 1 2 3; do
  t0=$EPOCHREALTIME; out=$(fm respond --no-stream "$P" 2>$err); fm_status=$?; t1=$EPOCHREALTIME
  if (( fm_status != 0 )); then
    print "=== run=$i FAILED exit=$fm_status"
    cat $err
    continue
  fi
  print "=== run=$i total_s=$(printf %.2f $((t1-t0))) words=$(print -r -- $out | wc -w | tr -d ' ')"
  print -r -- "$out"
done
rm -f $err
