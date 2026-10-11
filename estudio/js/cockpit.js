// EXPERIMENT RETIRED: intentionally absent from the runtime import graph.
// User requested external cameras until a type-faithful cockpit exists.
import * as THREE from 'three';
/** Authored cinematic cockpit, not an avionics simulator or a surveyed type replica.
 * Local frame: camera at (0,0,0), forward -Z. Never cut holes in source aircraft. */
function display(kind,family){
 const c=document.createElement('canvas');c.width=512;c.height=384;const x=c.getContext('2d');
 x.fillStyle='#04090d';x.fillRect(0,0,512,384);x.font='20px monospace';
 if(kind==='PFD'){
  x.fillStyle='#347cb1';x.fillRect(76,38,360,145);x.fillStyle='#855c31';x.fillRect(76,183,360,145);
  x.strokeStyle='#fff';x.lineWidth=2;x.beginPath();x.moveTo(76,183);x.lineTo(436,183);x.stroke();
  for(let i=-3;i<=3;i++){x.beginPath();x.moveTo(224,183+i*24);x.lineTo(288,183+i*24);x.stroke()}
  x.strokeStyle='#e9d441';x.lineWidth=5;x.beginPath();x.moveTo(160,190);x.lineTo(230,190);x.lineTo(230,203);x.moveTo(282,203);x.lineTo(282,190);x.lineTo(352,190);x.stroke();
  x.fillStyle='#b0efb7';x.fillText('SPD  HDG  ALT',126,26);x.fillStyle='#0d131a';x.fillRect(6,148,64,56);x.fillRect(442,148,68,56);x.fillStyle='white';x.fillText('310',16,183);x.fillText('1200',444,183);
 }else if(kind==='ND'){
  x.strokeStyle='#648677';x.lineWidth=2;for(const r of [72,144,214]){x.beginPath();x.arc(256,312,r,Math.PI,2*Math.PI);x.stroke()}
  x.strokeStyle='#e367d5';x.lineWidth=3;x.beginPath();x.moveTo(256,312);x.lineTo(240,210);x.lineTo(300,90);x.stroke();
  x.fillStyle='#ecf8fa';x.fillText('TRK  180',185,30);x.fillText('BASE',302,85);x.fillText('MAP  10 NM',14,366);
  x.beginPath();x.moveTo(256,275);x.lineTo(245,317);x.lineTo(267,317);x.closePath();x.fill();
 }else{
  x.fillStyle='#b7efce';x.fillText('ENGINE',20,32);
  for(let i=0;i<2;i++){const px=140+i*230;x.strokeStyle='#7bb99a';x.lineWidth=4;for(let j=0;j<2;j++){x.beginPath();x.arc(px,118+j*135,57,Math.PI*.8,Math.PI*2.2);x.stroke();x.fillText(j?' 620':' 89.2',px-28,125+j*135)}}
 }
 x.fillStyle='#9badbd';x.font='13px monospace';x.fillText('CINEMATIC / '+family.toUpperCase(),12,380);
 const tex=new THREE.CanvasTexture(c);tex.colorSpace=THREE.SRGBColorSpace;return tex;
}
function build(family){
 const g=new THREE.Group();g.name='Cockpit-cinematografico-'+family;
 const shell=new THREE.MeshStandardMaterial({color:family==='767'?0x77685d:0x626e79,roughness:.82});
 const dark=new THREE.MeshStandardMaterial({color:0x161d24,roughness:.7});const metal=new THREE.MeshStandardMaterial({color:0x35414a,metalness:.4,roughness:.55});
 function box(name,p,s,mat=shell){const m=new THREE.Mesh(new THREE.BoxGeometry(...s),mat);m.name=name;m.position.set(...p);g.add(m);return m}
 box('glareshield',[0,-.54,-1.42],[3.1,.16,.72],dark);
 box('instrument-panel',[0,-1.0,-1.48],[3.0,.8,.26]);
 box('forward-bulkhead',[0,-1.42,-1.75],[3.1,1.35,.1]);
 box('pedestal',[.5,-1.32,-.2],[.55,.64,1.7],dark);
 box('left-sidewall',[-1.42,-.67,-.05],[.2,1.5,3]);box('right-sidewall',[1.52,-.67,-.05],[.2,1.5,3]);
 box('roof',[0,.95,-.08],[3.2,.14,2.2]);box('overhead-console',[.42,.83,-.05],[.7,.15,1.3],dark);
 // Windshield posts are outside the central view; no opaque polygon fills a window.
 const rod=(name,a,b,r)=>{const A=new THREE.Vector3(...a),B=new THREE.Vector3(...b),m=new THREE.Mesh(new THREE.CylinderGeometry(r,r,A.distanceTo(B),8),metal);m.name=name;m.position.copy(A).add(B).multiplyScalar(.5);m.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),B.sub(A).normalize());g.add(m)};
 for(const side of [-1,1])rod('windshield-pillar',[side*1.44,-.48,-1.68],[side*1.05,.91,-1.07],.065);
 rod('center-windshield-post',[.58,-.48,-1.8],[.52,.95,-1.05],.045);
 rod('windshield-header',[-1.05,.91,-1.07],[1.05,.91,-1.07],.065);
 for(const [i,kind] of ['PFD','ND','ENGINE','PFD'].entries()){
  const x=-1.1+i*.72;box('display-bezel',[x,-.95,-1.325],[.68,.59,.05],dark);
  const screen=new THREE.Mesh(new THREE.PlaneGeometry(.61,.47),new THREE.MeshBasicMaterial({map:display(kind,family),toneMapped:false}));screen.position.set(x,-.94,-1.293);g.add(screen);
 }
 for(let i=0;i<14;i++)box('autopilot-button',[-1.28+i*.19,-.48,-1.035],[.09,.05,.025],i%3===0?metal:dark);
 for(let i=0;i<8;i++)box('overhead-switch',[.18+(i%4)*.14,.72,-.42+Math.floor(i/4)*.3],[.045,.07,.09],metal);
 box('floor',[0,-1.75,.1],[2.8,.08,3],dark);
 for(const child of g.children)child.position.y-=.28;
 const light=new THREE.PointLight(0xd1e4ff,3,5,2);light.position.set(0,.3,.1);g.add(light);
 return g;
}
export function atualizarCockpit(m,estado,t){
 const spec=estado.producao?.cockpit;const active=!!spec&&t>=spec.inicio;
 m._cockpitAtivo=active;
 if(m.cockpit)m.cockpit.visible=false;
 if(!active)return;
 const a=m.objetos.get(spec.ref);if(!a)return;
 if(m._cockpitFamilia!==spec.familia){
  if(m.cockpit){m.cena.remove(m.cockpit);m.cockpit.traverse(o=>{o.geometry?.dispose();if(o.material){o.material.map?.dispose();o.material.dispose()}})}
  m.cockpit=build(spec.familia);m._cockpitFamilia=spec.familia;m.cena.add(m.cockpit);
 }
 const g=m.cockpit;g.visible=true;
 g.position.copy(a.localToWorld(new THREE.Vector3(...spec.olho)));
 g.quaternion.copy(a.getWorldQuaternion(new THREE.Quaternion())).multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,1,0),Math.PI/2));
 // Swap the exterior only after the editorial entry cut; source meshes stay intact.
 a.visible=false;
 m.camP.up.set(0,1,0).applyQuaternion(a.quaternion);m.camP.lookAt(m.controles.target);
}
