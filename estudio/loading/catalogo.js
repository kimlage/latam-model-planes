/** Supported productions; dependent controls never imply an uncalibrated tug fit. */
export const AEROPORTOS={sbgr:'GRU · Guarulhos',sdsc:'SDSC · São Carlos',scl:'SCL · Santiago'};
export const AERONAVES={A319:'Airbus A319',A320ceo:'Airbus A320ceo',A320neo:'Airbus A320neo',A321ceo:'Airbus A321ceo',A321neo:'Airbus A321neo',B763:'Boeing 767-300ER',B77W:'Boeing 777-300ER',B788:'Boeing 787-8',B789:'Boeing 787-9',B763F:'Boeing 767-300F',B763BCF:'Boeing 767-300BCF'};
export const SITUACOES={sobrevoo:'Sobrevoo · acompanhamento aéreo',aproximacao:'Passagem próxima · exterior da aeronave',decolagem:'Decolagem · pista 10L',patio:'Pátio · apresentação da aeronave',reboque:'Hangar 9 · entrada em manutenção',manutencao:'Hangar 9 · interior e manutenção'};
export function situacoes(aeroporto){return ['patio','sobrevoo','aproximacao',...(aeroporto==='sbgr'?['decolagem']:aeroporto==='sdsc'?['reboque','manutencao']:[])];}
export function aeronaves(aeroporto,situacao){return situacao==='reboque'?['B789']:Object.keys(AERONAVES);}
export function validar(c){
 // Old shared links now resolve to an entirely external camera sequence.
 if(c.situacao==='cockpit')c={...c,situacao:'aproximacao'};
 if(!AEROPORTOS[c.aeroporto]||!situacoes(c.aeroporto).includes(c.situacao)||!aeronaves(c.aeroporto,c.situacao).includes(c.aeronave))throw Error('Combinação ainda não disponível nesta série.');
 return c;
}
export function parametros(c){return new URLSearchParams({airport:c.aeroporto,aircraft:c.aeronave,situation:c.situacao});}
export function lerParametros(search=location.search){const p=new URLSearchParams(search);return validar({aeroporto:p.get('airport')||'sdsc',aeronave:p.get('aircraft')||'B789',situacao:p.get('situation')||'reboque'});}
export function renderPronto(c){
 if(c.aeroporto==='sbgr'&&c.situacao==='aproximacao'&&c.aeronave==='B77W')return 'gru-b77w-aproximacao';
 if(c.aeroporto==='scl'&&c.situacao==='aproximacao'&&c.aeronave==='B789')return 'scl-b789-aproximacao';
 if(c.aeroporto==='sdsc'&&c.situacao==='sobrevoo'&&c.aeronave==='A320neo')return 'sdsc-a320-sobrevoo';
 if(c.aeroporto==='sdsc'&&c.situacao==='manutencao'&&c.aeronave==='B789')return 'sdsc-b789-interior';
 if(c.aeroporto==='sbgr'&&c.situacao==='patio'&&c.aeronave==='A320neo')return 'gru-a320-patio';
 if(c.aeroporto==='sdsc'&&c.situacao==='reboque'&&c.aeronave==='B789')return 'sdsc-reboque';
 if(c.aeroporto==='sbgr'&&c.situacao==='decolagem'&&c.aeronave==='B77W')return 'gru-decolagem';
 return null;
}
export function nome(c){return `${AEROPORTOS[c.aeroporto]} · ${AERONAVES[c.aeronave]} · ${SITUACOES[c.situacao]}`;}
