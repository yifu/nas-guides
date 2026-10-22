# Guides NAS

Sources des guides PDF pour le NAS Synology. Chaque guide est un fichier
`guide.md` dans son dossier, et le PDF est généré par `common/build_guide.py`
(ReportLab).

| Dossier | PDF généré |
|---|---|
| `synology-ds225/` | `build/nas-synology-ds225.pdf` |

## Récupérer les PDF

À chaque push sur `main`, GitHub Actions régénère tous les PDF et les publie
dans la release **latest** du dépôt (onglet *Releases*).

## Générer en local

```sh
make            # build/nas-*.pdf
make clean
```

Dépendances :

- Arch Linux : `sudo pacman -S make python-reportlab python-pypdf ttf-dejavu`
- macOS : `brew install --cask font-dejavu`, puis dans le dépôt
  `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
  et `make PYTHON=.venv/bin/python`

Si les polices DejaVu sont ailleurs, indiquer leur dossier avec `DEJAVU_DIR=...`.

## Format des sources

Un bloc par paragraphe, blocs séparés par une ligne vide :

| Syntaxe | Rendu |
|---|---|
| `@header Texte` | en-tête de chaque page |
| `@title Texte` / `@subtitle Texte` | page de titre |
| `# 1. Titre` / `## 1.1 Titre` | sections numérotées (sommaire et signets) |
| `### Titre` | petit titre non numéroté |
| bloc entre ` ``` ` | bloc de code |
| `> **Titre :** texte` | encadré jaune (une ligne `> ` par paragraphe) |
| `!! **Titre :** texte` | encadré rouge : risque de machine qui ne démarre plus ou de perte de données |
| `- texte` | puce |
| `\|= 120 160 201.9 header` puis `\| a \| b \| c \|` | tableau (largeurs en points, total 481.9) |
| `!flow` puis `Étape \| description` | schéma vertical d'étapes (`*` devant une étape la met en avant) |
| `!todo Titre` | encadré final « à faire » ; `~ ` pour une note en petit |
| `::: Titre` … `:::` | encadré gris, avec paragraphes, puces et code |

Dans le texte : `` `code` `` et `**gras**`. Un paragraphe ou un encadré qui se
termine par « : » reste sur la même page que le bloc suivant.
