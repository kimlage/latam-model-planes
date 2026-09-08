# Ambientes para produções web

Derivados dos masters locais de GRU e São Carlos, em metros, +Y para cima.
Compartilham a origem/datum das placas de campo; instancie cada contexto e seu
pavimento com posição e rotação zero. Não recentralize pela bounding box.

`manifest.json` contém fontes, dimensões, contagens e atribuições ODbL.
`conversao.json` registra os materiais simplificados. Revestimentos selecionados
são assados; o entorno usa materiais PBR representativos. O relevo de GRU está no asset separado `sbgr_relevo.glb`, derivado de Copernicus WorldDEM-30, com os avisos em `COPERNICUS.txt` e licença própria no manifesto.

Reprodução e limitações: [guia de produções](../../estudio/PRODUCOES.md).
Os exportadores preservam os masters e a biblioteca anterior de peças avulsas.

O interior interpretado do Hangar 9 está separado em `sdsc_hangar9_interior.glb` (CC BY 4.0), gerado por `estudio/tools/modelar_interior.py`. O contexto usa essa estrutura detalhada em lugar das barras maciças e luminárias antigas. A integração e as referências estão em `estudio/loading/INTERIORES.md`.

### Santiago — contexto completo e relevo

`scl_contexto.glb` e `scl_pavimentos_precisos.glb` registram terminais, base LATAM, equipamentos, pistas e pátios. `scl_relevo.glb` é um derivado separado dos heightfields locais Copernicus, com três níveis de amostragem e licença própria no manifesto. Reproduzir com `estudio/tools/exportar_ambientes.py -- --scl-only`, `exportar_pavimentos.py -- --scl-only` e `exportar_relevo_scl.py` dentro do Blender. Nenhum master foi sobrescrito.
