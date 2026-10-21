# Radar PSG

Web app installable sur iPhone : les matchs de Ligue des champions du PSG au Parc des Princes, notés selon des critères réglables, avec les alertes d'ouverture de billetterie.

**App :** https://artuschr.github.io/radar-psg/
**Calendrier d'alertes :** https://artuschr.github.io/radar-psg/alertes.ics

## Installer sur iPhone
1. Ouvrir l'app dans Safari.
2. Partager → « Sur l'écran d'accueil ».
3. Dans l'app, appuyer sur « S'abonner aux alertes ».

## Fonctionnement
- `data.json` : matchs, statuts et dates de vente. Mis à jour chaque jour automatiquement.
- `build_ics.py` : régénère `alertes.ics` à partir de `data.json`.
- Les réglages (poids des critères, seuil, gros clubs) restent sur chaque téléphone.

Achat uniquement sur la billetterie officielle : https://billetterie.psg.fr/
