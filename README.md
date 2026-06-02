# fec_parser

## Installation

Installer avec pip:
```python
pip install fec-parser
```

## Exemple

```python

from fec_parser.analyzer import FECAnalyzer

fec_analyzer = FECAnalyzer(pc_definition_filepath="fichier_definition.csv")
fec_analyzer.parse(open("mon_fec.csv", "rb"))

print(fec_analyzer.get_compte_resultat())
print(fec_analyzer.get_indicateurs())
```

## Fichier "définition"

Pour calculer un compte de résultat, il faut fournir en entrée un fichier "définition".
Un exemple est fourni (voir `definition_file.csv`).

C'est un csv sans en-tête contenant les champs suivants:
- `compte_pattern`: à remplir avec un identifiant unique ou un pattern
- `num`: non utilisé
- `label`: label permettant de reconnaître la ligne
- `opposite`: à remplir avec `-` si la ligne doit être comptée négativement
- `parent`: `compte_pattern` de la ligne parent
- `to_sum`: à remplir avec `SOMME` pour être additionnée dans la ligne parent
- `plan_comptable`: si vous utilisez un même fichier pour plusieurs plan comptables (ex: sociétés commerciales & associations), vous pouvez définir pour chaque le ou les plans comptables associées (liste séparée par un `;`)
- `formula`: dans ce champ, vous pouvez spécifier une "formule" avec des `compte_pattern` & des opérateurs (`+` ou `-`)

Dans le champ `compte_pattern`, vous pouvez également spécifier un champ custom : le compte doit commencer par `CUSTOM#`.
En fournissant la définition de ce champ custom, vous pouvez alors définir des lignes spéciales :
```python
{
    'CUSTOM#73': ('73', {'731', '732'}),
}
```
Avec ceci, la ligne avec le compte_pattern `CUSTOM#73` correspondra à la somme des numéros de compte commençant par `73`, mais pas par `731` ou `732`.


## Contact

En cas de difficultés, n'hésitez pas à nous contacter via `notrexp@etcld.fr` ou `si@etcld.fr`.

## Crédits

Ce package Python est basé sur l'outil interne du fonds ETCLD (Expérimentation Territoriale contre le Chômage de Longue Durée), NotreXP, développé en collaboration avec la société Spirkop.
Pour plus d'informations :
* [Spirkop](https://www.spirkop.com/fr/)
* [ETCLD](https://etcld.fr/)
* [Bilan ETCLD](https://bilan.etcld.fr/)
