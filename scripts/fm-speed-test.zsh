#!/bin/zsh
# fm photosynthesis speed test, as run by hand on 2026-09-28. Usage: zsh fm-speed-test.zsh
# (or pipe it into `zsh -s` over ssh).
#
# Superseded by the runner (`just run photosynthesis`), kept because it produced the speed table
# in results/2026-09-28-photosynthesis/. It does not detect a failed `fm respond`: stderr is merged
# into the stream and the exit status is not checked, so an error message would be timed and
# counted as if it were an answer. The runner records failures separately.
zmodload zsh/datetime
P='Explain in about 300 words how photosynthesis works.'
out=$(mktemp -t fmspeed)
print "host=$(scutil --get ComputerName) chip=$(sysctl -n machdep.cpu.brand_string) ram_gb=$(( $(sysctl -n hw.memsize) / 1073741824 )) macos=$(sw_vers -productVersion) power=$(pmset -g batt | head -1 | sed "s/.*'\(.*\)'.*/\1/")"
for i in 1 2 3; do
  t0=$EPOCHREALTIME
  { IFS= read -r -u0 -k1 c; t1=$EPOCHREALTIME; print -rn -- "$c" > $out; cat >> $out } < <(fm respond "$P" 2>&1)
  t2=$EPOCHREALTIME
  text=$(sed $'s/\x1b\\[[0-9;]*m//g' $out)
  n=$(fm count-tokens --quiet "$text" 2>/dev/null)
  printf 'run=%d out_tok=%s first_token_s=%.2f gen_s=%.2f total_s=%.2f decode_tok_s=%.1f words=%d\n' \
    $i $n $((t1-t0)) $((t2-t1)) $((t2-t0)) $(( n / (t2-t1) )) $(wc -w < $out)
done
rm -f $out
