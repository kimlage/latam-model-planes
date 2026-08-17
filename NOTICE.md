# Avisos legais e de terceiros

## Como este repositório é licenciado

O projeto tem duas licenças, porque tem dois tipos de conteúdo:

| Conteúdo | Licença |
|---|---|
| Código — `*.py`, `*.sh`, skills em `.claude/skills/` | [MIT](LICENSE) |
| Dados de engenharia — `spec_*.json`, `*_curves.json`, `*_planform.json` | [MIT](LICENSE) |
| Modelos 3D (`*.blend`), renders (`*.png`), animações (`*.gif`) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |

Atribuição sugerida para os modelos e imagens:

> Réplicas 3D da frota LATAM — Kim Lage — CC BY 4.0

## Marcas registradas

**LATAM**, o símbolo LATAM, **Airbus**, **A320neo**, **Boeing**, **787** e
**Dreamliner** são marcas registradas de seus respectivos titulares. Este é um
projeto **independente, não comercial e sem qualquer vínculo, patrocínio ou
endosso** da LATAM Airlines Group, da Airbus S.A.S. ou da The Boeing Company.

As licenças acima cobrem **a expressão autoral deste projeto** (a malha, os
scripts, as medições). Elas **não concedem** direito algum sobre as marcas
representadas. Uso comercial da livery ou das marcas depende de autorização dos
titulares — a licença CC BY 4.0 não substitui essa autorização.

## Material de terceiros que NÃO está neste repositório

Estes arquivos fazem parte do fluxo de trabalho mas foram deliberadamente
excluídos (ver [.gitignore](.gitignore)), porque não podem ser redistribuídos
sob as licenças acima. Para reproduzir o pipeline do zero, obtenha-os
diretamente na fonte:

| Arquivo | O que é | Onde obter |
|---|---|---|
| `A320_ACAP_airbus.pdf` | *Aircraft Characteristics — Airport & Maintenance Planning* do A320 | Página **Aircraft Characteristics** no site da Airbus (gratuito) |
| `boeing 787-9/B787_APR_boeing.pdf` | *Airplane Characteristics* D6-58333 do 787 | Boeing, seção **Airport Compatibility / ACAPs** (gratuito) |
| `latam_logo_indigo.svg` | Lockup oficial LATAM (símbolo + wordmark) | Wikimedia Commons |
| `airbus_a320neo_logo.svg`, `dreamliner_logo.svg` | Títulos de fabricante | Wikimedia Commons |
| `ref_CC-BGP_wikimedia.jpg`, `ref_PT-TMN_wikimedia.jpg` | Fotos de referência das matrículas | Wikimedia Commons / JetPhotos / Planespotters |

Os documentos dos fabricantes são de download livre, mas **livre para baixar não
é livre para redistribuir**: os direitos continuam com Airbus e Boeing.

As fotos de referência foram excluídas por um motivo diferente e igualmente
simples: o projeto não registrou autor e licença de cada uma no momento em que
foram baixadas, e sem isso não é possível cumprir a atribuição que as licenças
Creative Commons exigem. **Lição incorporada ao pipeline:** toda foto nova deve
entrar com URL, autor e licença anotados no `spec_*.json` da aeronave.

## O que os modelos contêm

Os arquivos `.blend` trazem as texturas de livery empacotadas, incluindo as
marcas descritas acima. Elas foram geradas neste projeto a partir dos vetores
oficiais e de medições em foto. A geometria da aeronave é **inteiramente
original**, construída a partir das cotas dos documentos dos fabricantes —
nenhuma malha de terceiros foi usada como base (ver a skill `fontes-aeronave`,
seção *Licenças*).
