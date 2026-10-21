import {build} from 'esbuild';
await build({entryPoints:['submission-src/app.js'],bundle:true,format:'esm',platform:'browser',target:['es2022'],alias:{'@huggingface/hub':process.cwd()+'/node_modules/@huggingface/hub/dist/browser/index.mjs'},outfile:'site/submission.js',legalComments:'eof',minify:true});
