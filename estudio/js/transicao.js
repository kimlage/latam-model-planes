/** Editorial repeat: fade to black, reset the operation, then fade back in. */
export function opacidadeTransicao(estado,t){
 if(estado.producao?.transicao!=='fade-black')return 0;
 const d=estado.linha.duracao,s=Math.min(.55,d/4);
 return Math.min(1,Math.max(0,1-t/s,1-(d-t)/s));
}
