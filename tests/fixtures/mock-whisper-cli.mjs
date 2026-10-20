#!/usr/bin/env node
// CI fixture only. Simulates the whisper.cpp CLI protocol; not a speech model.
import fs from 'node:fs';
const args=process.argv.slice(2);
if(args.includes('--help'))process.exit(0);
if(!args.includes('-m')||!args.includes('-f')||!args.includes('-of')||!args.includes('-osrt'))process.exit(1);
const out=args[args.indexOf('-of')+1];
fs.writeFileSync(out+'.srt','1\n00:00:00,100 --> 00:00:01,500\nLegenda de teste gerada localmente.\n','utf8');
