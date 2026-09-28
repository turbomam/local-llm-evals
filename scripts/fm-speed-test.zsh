#!/bin/zsh
# fm photosynthesis speed test. Paste-able: zsh fm_speed.zsh (or pipe into zsh -s).
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
