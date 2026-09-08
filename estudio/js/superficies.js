/** Metric-scale surface detail. Source textures and registrations are preserved.
 * Procedural variation is interpreted material finish, not aerial imagery. */
export function refinarSuperficie(material,asset,meshName){
 if(!material?.isMeshStandardMaterial||asset.categoria==='aeronave')return material;
 const name=material.name||'',identity=meshName+' '+name;
 let type=/Concrete|Concreto|Apron|Hangar9_Floor/.test(identity)?'concrete':/Asphalt|Runway|Taxiway|Roads|Streets/.test(identity)?'asphalt':/Terrain|FieldSurround|Farmland|Cropland|Soil|Grass|CaneSurround|Ground/.test(identity)?'earth':/Roof|Wall|HangarDoors|DoorPanels/.test(identity)?'building':null;
 if(/Marking|Safety|Joint|Glass|Window|Sign|Brand|Wordmark|Light|Lamp/.test(identity))type=null;
 if(!type)return material;
 const m=material.clone();m.name=name+' · surface';m.userData.surfaceDetail=type;
 m.roughness=type==='building'?.76:type==='concrete'?.84:.95;
 m.onBeforeCompile=s=>{
  s.vertexShader=s.vertexShader.replace('#include <common>','#include <common>\nvarying vec3 surfaceWorld;');
  s.vertexShader=s.vertexShader.replace('#include <worldpos_vertex>','#include <worldpos_vertex>\nsurfaceWorld=(modelMatrix*vec4(transformed,1.)).xyz;');
  s.fragmentShader=s.fragmentShader.replace('#include <common>',`#include <common>
 varying vec3 surfaceWorld;
 float surfHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
 float surfNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);return mix(mix(surfHash(i),surfHash(i+vec2(1,0)),f.x),mix(surfHash(i+vec2(0,1)),surfHash(i+vec2(1)),f.x),f.y);}
 float surfFilteredNoise(vec2 p){float footprint=max(length(dFdx(p)),length(dFdy(p)));return mix(surfNoise(p),.5,smoothstep(.35,1.,footprint));}
 float surfLine(float p,float width){float a=max(fwidth(p),.0001);return (1.-smoothstep(width,width+a,abs(fract(p+.5)-.5)))*(1.-smoothstep(.08,.5,a));}
 `);
  const detail=type==='earth'?`
 float broad=surfFilteredNoise(surfaceWorld.xz*.006),variation=surfFilteredNoise(surfaceWorld.xz*.04),grain=surfFilteredNoise(surfaceWorld.xz*.7);
 float detail=(broad-.5)*.27+(variation-.5)*.12+(grain-.5)*.05;
 diffuseColor.rgb*=.92+detail;
 diffuseColor.rgb=mix(diffuseColor.rgb,diffuseColor.rgb*vec3(1.06,1.015,.9),variation*.24);
 `:type==='concrete'?`
 float wear=surfFilteredNoise(surfaceWorld.xz*.11);
 float grain=surfFilteredNoise(surfaceWorld.xz*3.);
 diffuseColor.rgb*=.94+.10*(wear-.5)+.035*(grain-.5);
 `:type==='asphalt'?`
 float grain=surfFilteredNoise(surfaceWorld.xz*4.);
 diffuseColor.rgb*=.92+.13*(surfFilteredNoise(surfaceWorld.xz*.09)-.5)+.045*(grain-.5);
 `:`
 float grain=surfFilteredNoise(surfaceWorld.xz*.7+surfaceWorld.y*.12);
 float rib=surfLine(surfaceWorld.x*.8+surfaceWorld.z*.08,.012);
 diffuseColor.rgb*=.94+.09*(grain-.5)-.07*rib;
 `;
  s.fragmentShader=s.fragmentShader.replace('#include <color_fragment>','#include <color_fragment>\n'+detail);
  s.fragmentShader=s.fragmentShader.replace('#include <roughnessmap_fragment>','#include <roughnessmap_fragment>\nroughnessFactor=clamp(roughnessFactor+.035*(grain-.5),.3,1.);');
  if(type==='concrete'||type==='asphalt')s.fragmentShader=s.fragmentShader.replace('#include <normal_fragment_maps>',`#include <normal_fragment_maps>
   vec3 dp1=dFdx(-vViewPosition),dp2=dFdy(-vViewPosition);
   vec3 r1=cross(dp2,normal),r2=cross(normal,dp1);float determinant=dot(dp1,r1);
   float relief=surfFilteredNoise(surfaceWorld.xz*12.)*.0007;
   normal=normalize(abs(determinant)*normal-sign(determinant)*(dFdx(relief)*r1+dFdy(relief)*r2));
  `);

 };
 m.customProgramCacheKey=()=> 'latam-surface-v3-'+type;
 return m;
}
